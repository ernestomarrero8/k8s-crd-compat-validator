"""Standalone multi-context report, including full detail without external files."""
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path
import hashlib
import json
from .collector import read_json
from .cluster_identity import identify
from .models import STATES, SEVERITIES
from .report_generator import html
from .rule_engine import safe_source
from .version import Version


def load_report(path, context):
    report = read_json(path)
    if report.get("cluster") != context or report.get("overall_status") not in STATES:
        raise ValueError("Contexto o estado del reporte inválido.")
    Version.parse(report["current_version"])
    Version.parse(report["target_version"])
    if type(report["summary"]["total_crds"]) is not int or report["summary"]["total_crds"] != len(report["crds"]):
        raise ValueError("Conteo de CRDs inválido.")
    for group, allowed in (("states", STATES), ("risks_by_severity", SEVERITIES)):
        if any(k not in allowed or type(v) is not int or v < 0 for k, v in report["summary"][group].items()):
            raise ValueError("Conteos de resumen inválidos.")
    for crd in report["crds"]:
        if crd["status"] not in STATES or crd["severity"] not in SEVERITIES:
            raise ValueError("Estado de CRD inválido.")
    for f in report["global_findings"] + [f for c in report["crds"] for f in c["findings"]]:
        if f["status"] not in STATES or f["severity"] not in SEVERITIES or not safe_source(f["source"]):
            raise ValueError("Hallazgo inválido.")
    return report


def _identity(report, context):
    value = report.get("cluster_identity") or ""
    if not isinstance(value, str):
        value = ""
    data = {"aks": report.get("platform", {}).get("aks", {})}
    if value.startswith("/subscriptions/"):
        data["aks"] = {"resource_id": value}
    elif value.startswith("kube-system:"):
        data["kube_system_uid"] = value.removeprefix("kube-system:")
    elif value.startswith("https://"):
        data["api_server"] = value
    return identify(data, context)["cluster_identity"]


def _fingerprint(report):
    volatile = {"cluster", "context", "analyzed_at", "analyzed_on", "kubectl_queries", "cluster_identity_evidence"}
    def canonical(value):
        if isinstance(value, dict):
            return {k: canonical(v) for k, v in value.items() if k not in volatile}
        if isinstance(value, list):
            if "--kube-context" in value:
                index = value.index("--kube-context")
                value = value[:index] + value[index + 2:]
            return sorted((canonical(v) for v in value), key=lambda v: json.dumps(v, sort_keys=True))
        return value
    selected = {k: report.get(k) for k in ("current_version", "target_version", "crds", "global_findings", "platform", "pluto", "readiness", "validator")}
    return hashlib.sha256(json.dumps(canonical(selected), sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _groups(entries):
    groups = {}
    for entry in entries:
        report = None
        try:
            report = load_report(entry["report_path"], entry["context"])
            if entry.get("target") and report["target_version"] != entry["target"]:
                raise ValueError("Objetivo diferente al de esta ejecución.")
            # Validate rendering before using this report to identify a physical cluster.
            html(report)
        except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError):
            report = None
        identity = _identity(report, entry["context"]) if report else identify({}, entry["context"])["cluster_identity"]
        group = groups.setdefault(identity, {"cluster_identity": identity, "primary_context": entry["context"], "members": []})
        group["members"].append((entry, report))
    for group in groups.values():
        members = group["members"]
        group["contexts"] = [e["context"] for e, _ in members]
        group["data_mismatch"] = len({_fingerprint(r) for _, r in members if r}) > 1 or len({e["exit_code"] for e, _ in members}) > 1
    return list(groups.values())


def blocking_reasons(report):
    reasons = []
    seen = set()
    groups = [(None, report["global_findings"])] + [(c["name"], c["findings"]) for c in report["crds"]]
    for owner, findings in groups:
        for f in findings:
            if f["status"] == "PASS" or f["rule_id"] == "PRODUCT_SUPPORT":
                continue
            evidence = f.get("evidence", {})
            product = evidence.get("product")
            version = evidence.get("installed_version", "")
            prefix = f"{product} {version}".strip() if product else owner
            description = (prefix + " — " if prefix else "") + f["description"]
            key = (f["rule_id"], f["status"], description)
            if key in seen:
                continue
            seen.add(key)
            reasons.append({"rule_id": f["rule_id"], "status": f["status"], "severity": f["severity"], "description": description})
    severity = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4, "INFO": 4}
    return sorted(reasons, key=lambda r: (0 if r["status"] == "FAIL" else 1, severity.get(r["severity"], 4)))


def consolidate(entries, output):
    """Entries describe this run only; never discover potentially stale reports."""
    rows, details, statuses = [], [], []
    totals = Counter()
    clusters = []
    grouped = _groups(entries)
    for index, group in enumerate(grouped, 1):
        entry, report = group["members"][0]
        context, code = entry["context"], entry["exit_code"]
        code = 2 if group["data_mismatch"] or any(e["exit_code"] not in (0, 1) for e, _ in group["members"]) else max(e["exit_code"] for e, _ in group["members"])
        fragment = html(report).partition("<main>")[2].rpartition("</main>")[0] if report else ""
        state = report["overall_status"] if report else "ERROR"
        if code not in (0, 1):
            state = "ERROR"
        statuses.append(state)
        readiness = {"PASS": "Sin bloqueos detectados; sujeto al alcance evaluado", "UNKNOWN": "Evidencia insuficiente",
                     "WARN": "Requiere revisión", "FAIL": "Resolver bloqueos antes del upgrade", "ERROR": "Evaluación incompleta"}[state]
        totals.update(report["summary"]["states"] if report else {})
        current = report["current_version"] if report else "—"
        target = report["target_version"] if report else entry.get("target", "—")
        count = report["summary"]["total_crds"] if report else "—"
        pluto = report.get("pluto", {}).get("status", "UNKNOWN") if report else "UNKNOWN"
        pluto_exit = report.get("pluto", {}).get("exit_code") if report else None
        score = report.get("readiness", {}).get("score", "—") if report else "—"
        evidence_coverage = report.get("readiness", {}).get("evidence_coverage", "—") if report else "—"
        if report and state != "ERROR" and "readiness" in report:
            readiness = report["readiness"]["decision"]
        reasons = blocking_reasons(report) if report else []
        if group["data_mismatch"]:
            position = next((i for i, r in enumerate(reasons) if r["status"] != "FAIL"), len(reasons))
            reasons.insert(position, {"rule_id": "CONTEXT_DATA_MISMATCH", "status": "ERROR", "severity": "HIGH",
                "description": "CONTEXT_DATA_MISMATCH: datos distintos entre contextos de una misma identidad; revisar todos los detalles."})
        if state == "ERROR":
            readiness = "BLOCKED" if any(r["status"] == "FAIL" for r in reasons) else "INCOMPLETE"
        failed = [p["product"] for p in report.get("platform", {}).get("products", []) if any(f["status"] == "FAIL" for f in p["findings"])] if report else []
        unknown = [p["product"] for p in report.get("platform", {}).get("products", []) if any(f["status"] == "UNKNOWN" for f in p["findings"])] if report else []
        clusters.append({k: v for k, v in group.items() if k != "members"} | {"current_version": current, "target_version": target,
            "pluto": {"status": pluto, "exit_code": pluto_exit, "exit_code_origin": "pluto_report" if pluto_exit is not None else "unavailable"},
            "validator": {"status": state, "exit_code": code, "exit_code_origin": "consolidation" if group["data_mismatch"] else "validator_process"},
            "compatibility_score": score, "evidence_coverage": evidence_coverage, "decision": readiness,
            "products_fail": failed, "products_unknown": unknown, "blocking_reasons": reasons,
            "context_results": [{"context": e["context"], "validator_exit": e["exit_code"], "pluto": r.get("pluto", {}) if r else None} for e, r in group["members"]]})
        esc = lambda v: escape(str(v), quote=True)
        rows.append(f'<tr><td><a href="#cluster-{index}">{esc(context)}</a></td><td>{esc(current)} → {esc(target)}</td>'
                    f'<td>{esc(count)}</td><td class="{state}">{state}</td><td>{esc(pluto)}</td><td>{esc(pluto_exit if pluto_exit is not None else "—")}</td>'
                    f'<td>{esc(state)}</td><td>{esc(code)}</td><td>{esc(score if score is not None else "—")}/100</td><td>{esc(evidence_coverage)}%</td><td>{esc(readiness)}</td>'
                    f'<td>{esc(reasons[0]["description"] if reasons else "Sin bloqueos documentados")}</td><td>{esc(", ".join(failed) or "—")}</td><td>{esc(", ".join(unknown) or "—")}</td>'
                    f'<td>Contextos asociados: {len(group["contexts"])}<br>{esc(", ".join(group["contexts"]))}</td></tr>')
        body = fragment if report else "<p>No se obtuvo un reporte JSON válido para este contexto. Consultar su archivo console.txt.</p>"
        if report and state == "ERROR":
            body = "<p class='ERROR'>El proceso terminó con error o timeout; el detalle disponible puede ser parcial.</p>" + body
        if group["data_mismatch"]:
            body = "<p class='ERROR'><b>CONTEXT_DATA_MISMATCH</b>: los contextos de este clúster entregaron datos diferentes; se conservan todos los resultados sin fusionarlos.</p>" + "".join(
                '<details open><summary>' + esc(e["context"]) + '</summary>' + (html(r).partition("<main>")[2].rpartition("</main>")[0] if r else "Sin reporte válido") + '</details>' for e, r in group["members"])
        body = f'<p>Identidad: {esc(group["cluster_identity"])} · Contexto principal: {esc(context)}</p><pre>' + esc(json.dumps(clusters[-1]["context_results"], ensure_ascii=False, indent=2)) + '</pre>' + body
        details.append(f'<section id="cluster-{index}"><h2>{esc(context)}</h2><p><a href="#summary">Volver al resumen</a></p>{body}</section>')
    overall = max(statuses, key=STATES.index, default="UNKNOWN")
    # Reuse the individual report's styles; all report detail is regenerated from JSON.
    template = html({"cluster": "", "current_version": "", "target_version": "", "analyzed_at": "", "overall_status": "UNKNOWN",
                     "crds": [], "global_findings": [], "summary": {"states": {}, "risks_by_severity": {}, "total_crds": 0}, "limitations": []})
    head = template.partition("<main>")[0].replace("CRD Compatibility Report", "Consolidado de compatibilidad Kubernetes")
    verified_identities = sum(not g["cluster_identity"].startswith("context:") for g in grouped)
    content = (f'<h1 id="summary">Compatibilidad Kubernetes — consolidado</h1><p>Fecha UTC: {datetime.now(timezone.utc).isoformat()}</p>'
               f'<p>Clústeres físicos identificados: {verified_identities} · Contextos sin identidad compartida verificable: {len(grouped) - verified_identities} · Contextos: {len(entries)} · Estado global: <b>{overall}</b> · CRDs analizados por contexto principal: {sum(totals.values())}</p>'
               '<p>Un resultado PASS acredita las comprobaciones realizadas. WARN y UNKNOWN requieren revisión; FAIL contiene bloqueos y ERROR indica una evaluación incompleta.</p>'
               '<div style="overflow-x:auto"><table><thead><tr><th>Clúster / Contexto</th><th>Upgrade</th><th>CRDs</th><th>Estado</th><th>Pluto</th><th>Pluto exit</th><th>Validador</th><th>Validator exit</th><th>Compatibility score</th><th>Evidence coverage</th><th>Decision</th><th>Bloqueo principal</th><th>Productos FAIL</th><th>Productos UNKNOWN</th><th>Contextos asociados</th></tr></thead><tbody>'
               + "".join(rows) + "</tbody></table></div>" + "".join(details))
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(head + "<main>" + content + "</main></html>", encoding="utf-8", newline="\n")
    output.with_suffix(".json").write_text(json.dumps({"clusters": clusters, "contexts": len(entries), "overall_status": overall}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return overall
