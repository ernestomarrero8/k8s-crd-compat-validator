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
from .context_diff import compare_contexts, diff_html, technical_causes, comparison_coverage


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
    volatile = {"cluster", "context", "analyzed_at", "analyzed_on", "kubectl_queries", "cluster_identity_evidence",
        "optional_sources_unavailable", "detection_sources", "version_candidates", "evidence_scope"}
    def canonical(value):
        if isinstance(value, dict):
            ignored = volatile
            if "id" in value and "product" in value and "findings" in value:
                ignored = volatile | {"evidence", "resolution_sources", "resolution_confidences", "resolved_versions", "confidence", "detected_versions", "detected_version"}
            return {k: canonical(v) for k, v in value.items() if k not in ignored and not (k == "limitations" and isinstance(v, list) and v == ["Helm inventory unavailable"])}
        if isinstance(value, list):
            value = [v for v in value if not (isinstance(v, dict) and (v.get("required") is False and "source" in v and "completed" in v or v.get("source") in ("Helm", "helm", "istioctl version") and "reason" in v))]
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
        difference = len({_fingerprint(r) for _, r in members if r}) > 1 or len({e["exit_code"] for e, _ in members}) > 1
        incomplete = comparison_coverage(members) if len(members) > 1 else None
        group["comparison_status"] = "SINGLE_CONTEXT" if len(members) == 1 else "CONTEXT_COMPARISON_INCONCLUSIVE" if incomplete else "CONTEXT_DATA_MISMATCH" if difference else "MATCH"
        group["comparison_evidence"] = incomplete
        group["data_difference_observed"] = difference
        group["data_mismatch"] = difference and not incomplete
    return list(groups.values())


def blocking_reasons(report):
    reasons = []
    seen = set()
    products = {p["product"]: p for p in report.get("platform", {}).get("products", [])}
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
            if f["rule_id"] == "NOT_COMPATIBLE" and products.get(product, {}).get("support_explanation"):
                description = products[product]["support_explanation"]
            key = (f["rule_id"], f["status"], description)
            if key in seen:
                continue
            seen.add(key)
            domain = evidence.get("failure_domain") or ("SUPPORT_POLICY" if f["category"] in ("operator", "operator_compatibility") and f["status"] == "FAIL" else "TECHNICAL")
            reasons.append({"rule_id": f["rule_id"], "status": f["status"], "severity": f["severity"], "description": description,
                "failure_domain": domain, "result_type": "FAIL_SUPPORT_POLICY" if domain == "SUPPORT_POLICY" and f["status"] == "FAIL" else "FAIL_TECHNICAL" if f["status"] == "FAIL" else f["status"]})
    severity = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4, "INFO": 4}
    return sorted(reasons, key=lambda r: (0 if r["status"] == "FAIL" else 1, severity.get(r["severity"], 4)))


def consolidate(entries, output):
    """Entries describe this run only; never discover potentially stale reports."""
    rows, details, statuses = [], [], []
    totals = Counter()
    clusters = []
    technical_errors = []
    grouped = _groups(entries)
    for index, group in enumerate(grouped, 1):
        entry, report = group["members"][0]
        context, code = entry["context"], entry["exit_code"]
        context_diff = compare_contexts(group["members"], _fingerprint) if group["comparison_status"] in ("CONTEXT_DATA_MISMATCH", "CONTEXT_COMPARISON_INCONCLUSIVE") else None
        code = 2 if context_diff or any(e["exit_code"] not in (0, 1) for e, _ in group["members"]) else max(e["exit_code"] for e, _ in group["members"])
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
        elif group["comparison_status"] == "CONTEXT_COMPARISON_INCONCLUSIVE":
            reasons.append({"rule_id": "CONTEXT_COMPARISON_INCONCLUSIVE", "status": "UNKNOWN", "severity": "INFO",
                "description": "Inventario incompleto: los contextos no pueden compararse de forma concluyente; no se afirma discrepancia del clúster."})
        if state == "ERROR":
            readiness = "BLOCKED" if any(r["status"] == "FAIL" for r in reasons) else "INCOMPLETE"
        failed = [p["product"] for p in report.get("platform", {}).get("products", []) if any(f["status"] == "FAIL" for f in p["findings"])] if report else []
        unknown = [p["product"] for p in report.get("platform", {}).get("products", []) if any(f["status"] == "UNKNOWN" for f in p["findings"])] if report else []
        managed_unknown = [p["product"] for p in report.get("platform", {}).get("products", []) if p.get("managed_by") == "AKS" and p["product"] in unknown] if report else []
        managed_unexposed = [p["product"] for p in report.get("platform", {}).get("products", []) if p["product"] in managed_unknown and (not p["versions"] or p["versions"] == ["MANAGED"])] if report else []
        third_party_unknown = [p for p in unknown if p not in managed_unknown]
        clusters.append({k: v for k, v in group.items() if k != "members"} | {"current_version": current, "target_version": target,
            "pluto": {"status": pluto, "exit_code": pluto_exit, "exit_code_origin": "pluto_report" if pluto_exit is not None else "unavailable"},
            "validator": {"status": state, "exit_code": code, "exit_code_origin": "consolidation" if context_diff else "validator_process"},
            "compatibility_score": score, "evidence_coverage": evidence_coverage, "decision": readiness,
            "context_diff": context_diff,
            "products_fail": failed, "products_unknown": unknown, "blocking_reasons": reasons,
            "third_party_unknown": third_party_unknown, "aks_managed_unknown": managed_unknown, "aks_managed_unexposed": managed_unexposed,
            "context_results": [{"context": e["context"], "validator_exit": e["exit_code"], "pluto": r.get("pluto", {}) if r else None} for e, r in group["members"]]})
        esc = lambda v: escape(str(v), quote=True)
        if state == "ERROR":
            causes = [cause for member, value in group["members"] for cause in technical_causes(member, value)]
            if context_diff:
                causes.append({"source": "context_comparison", "reason": group["comparison_status"], "context": context,
                    "action": "Revisar las diferencias de CRDs, productos, versiones y consultas que se muestran debajo."})
            technical_errors.append({"cluster": context, "contexts": group["contexts"], "causes": causes,
                "context_diff": context_diff, "detail_anchor": f"cluster-{index}"})
        rows.append(f'<tr><td><a href="#cluster-{index}">{esc(context)}</a></td><td>{esc(current)} → {esc(target)}</td>'
                    f'<td>{esc(count)}</td><td class="{state}">{state}</td><td>{esc(pluto)}</td><td>{esc(pluto_exit if pluto_exit is not None else "—")}</td>'
                    f'<td>{esc(state)}</td><td>{esc(code)}</td><td>{esc(score if score is not None else "—")}/100</td><td>{esc(evidence_coverage)}%</td><td>{esc(readiness)}</td>'
                    f'<td>{esc(reasons[0]["description"] if reasons else "Sin bloqueos documentados")}</td><td>{esc(", ".join(failed) or "—")}</td><td>{esc(", ".join(third_party_unknown) or "—")}</td>'
                    f'<td>{esc(", ".join(managed_unknown) or "—")}<br>Sin versión expuesta: {esc(", ".join(managed_unexposed) or "—")}</td>'
                    f'<td>Contextos asociados: {len(group["contexts"])}<br>{esc(", ".join(group["contexts"]))}</td></tr>')
        body = fragment if report else "<p>No se obtuvo un reporte JSON válido para este contexto. Consultar su archivo console.txt.</p>"
        if report and state == "ERROR":
            body = "<p class='ERROR'>El proceso terminó con error o timeout; el detalle disponible puede ser parcial.</p>" + body
        if context_diff:
            explanation = "Se observaron datos diferentes en inventarios completos." if group["data_mismatch"] else "Inventario incompleto: una diferencia de muestras no demuestra discrepancia del clúster."
            body = '<p><b>' + esc(group["comparison_status"]) + '</b>: ' + explanation + '</p>' + (('<pre>' + esc(json.dumps(group["comparison_evidence"], ensure_ascii=False, indent=2)) + '</pre>') if group["comparison_evidence"] else '') + diff_html(context_diff) + "".join(
                '<details open><summary>' + esc(e["context"]) + '</summary>' + (html(r).partition("<main>")[2].rpartition("</main>")[0] if r else "Sin reporte válido") + '</details>' for e, r in group["members"])
        context_codes = [{"context": v["context"], "validator_exit": v["validator_exit"], "pluto": {k: (v["pluto"] or {}).get(k) for k in ("status", "exit_code")}} for v in clusters[-1]["context_results"]]
        body = f'<p>Identidad: {esc(group["cluster_identity"])} · Contexto principal: {esc(context)}</p><pre>' + esc(json.dumps(context_codes, ensure_ascii=False, indent=2)) + '</pre>' + body
        details.append(f'<section id="cluster-{index}"><h2>{esc(context)}</h2><p><a href="#summary">Volver al resumen</a></p>{body}</section>')
    overall = max(statuses, key=STATES.index, default="UNKNOWN")
    # Reuse the individual report's styles; all report detail is regenerated from JSON.
    template = html({"cluster": "", "current_version": "", "target_version": "", "analyzed_at": "", "overall_status": "UNKNOWN",
                     "crds": [], "global_findings": [], "summary": {"states": {}, "risks_by_severity": {}, "total_crds": 0}, "limitations": []})
    head = template.partition("<main>")[0].replace("CRD Compatibility Report", "Consolidado de compatibilidad Kubernetes")
    verified_identities = sum(not g["cluster_identity"].startswith("context:") for g in grouped)
    error_summary = f'<section aria-label="Causas del estado global"><h2>Errores técnicos: {len(technical_errors)}</h2>'
    if technical_errors:
        error_summary += '<p>Causas accionables del estado global ERROR:</p><ol>'
        for error in technical_errors:
            error_summary += f'<li><b><a href="#{esc(error["detail_anchor"])}">{esc(error["cluster"])}</a></b><ul>'
            error_summary += "".join(f'<li>{esc(c["context"])} · {esc(c["source"])}: {esc(c["reason"])}'
                + (f' · examinados: {esc(c["items_scanned"])}' if c.get("items_scanned") is not None else "")
                + f'<br>{esc(c["action"])}</li>' for c in error["causes"])
            error_summary += '</ul>' + (diff_html(error["context_diff"]) if error["context_diff"] else '') + '</li>'
        error_summary += '</ol>'
    error_summary += '</section>'
    content = (f'<h1 id="summary">Compatibilidad Kubernetes — consolidado</h1><p>Fecha UTC: {datetime.now(timezone.utc).isoformat()}</p>'
               f'<p>Clústeres físicos identificados: {verified_identities} · Contextos sin identidad compartida verificable: {len(grouped) - verified_identities} · Contextos: {len(entries)} · Estado global: <b>{overall}</b> · CRDs analizados por contexto principal: {sum(totals.values())}</p>'
               + error_summary +
               '<p>Un resultado PASS acredita las comprobaciones realizadas. WARN y UNKNOWN requieren revisión; FAIL contiene bloqueos y ERROR indica una evaluación incompleta.</p>'
               '<div style="overflow-x:auto"><table><thead><tr><th>Clúster / Contexto</th><th>Upgrade</th><th>CRDs</th><th>Estado</th><th>Pluto</th><th>Pluto exit</th><th>Validador</th><th>Validator exit</th><th>Compatibility score</th><th>Evidence coverage</th><th>Decision</th><th>Bloqueo principal</th><th>Productos FAIL / política de soporte</th><th>Productos UNKNOWN — terceros / gestión no verificada</th><th>AKS administrados — evidencia pendiente</th><th>Contextos asociados</th></tr></thead><tbody>'
               + "".join(rows) + "</tbody></table></div>" + "".join(details))
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(head + "<main>" + content + "</main></html>", encoding="utf-8", newline="\n")
    output.with_suffix(".json").write_text(json.dumps({"clusters": clusters, "contexts": len(entries), "overall_status": overall,
        "technical_errors_count": len(technical_errors), "technical_errors": technical_errors}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return overall
