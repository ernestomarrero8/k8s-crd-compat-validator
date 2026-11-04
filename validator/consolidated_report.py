"""Standalone multi-context report, including full detail without external files."""
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from .collector import read_json
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


def consolidate(entries, output):
    """Entries describe this run only; never discover potentially stale reports."""
    rows, details, statuses = [], [], []
    totals = Counter()
    for index, entry in enumerate(entries, 1):
        context, code = entry["context"], entry["exit_code"]
        report = None
        try:
            report = load_report(entry["report_path"], context)
            if entry.get("target") and report["target_version"] != entry["target"]:
                raise ValueError("Objetivo diferente al de esta ejecución.")
            fragment = html(report).partition("<main>")[2].rpartition("</main>")[0]
        except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError):
            report = None
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
        score = report.get("readiness", {}).get("score", "—") if report else "—"
        evidence_coverage = report.get("readiness", {}).get("evidence_coverage", "—") if report else "—"
        if report and state != "ERROR" and "readiness" in report:
            readiness = report["readiness"]["decision"]
        esc = lambda v: escape(str(v), quote=True)
        rows.append(f'<tr><td><a href="#cluster-{index}">{esc(context)}</a></td><td>{esc(current)} → {esc(target)}</td>'
                    f'<td>{esc(count)}</td><td class="{state}">{state}</td><td>{esc(pluto)}</td><td>{esc(code)}</td><td>{esc(score)}/100</td><td>{esc(evidence_coverage)}%</td><td>{esc(readiness)}</td></tr>')
        body = fragment if report else "<p>No se obtuvo un reporte JSON válido para este contexto. Consultar su archivo console.txt.</p>"
        if report and state == "ERROR":
            body = "<p class='ERROR'>El proceso terminó con error o timeout; el detalle disponible puede ser parcial.</p>" + body
        details.append(f'<section id="cluster-{index}"><h2>{esc(context)}</h2><p><a href="#summary">Volver al resumen</a></p>{body}</section>')
    overall = max(statuses, key=STATES.index, default="UNKNOWN")
    # Reuse the individual report's styles; all report detail is regenerated from JSON.
    template = html({"cluster": "", "current_version": "", "target_version": "", "analyzed_at": "", "overall_status": "UNKNOWN",
                     "crds": [], "global_findings": [], "summary": {"states": {}, "risks_by_severity": {}, "total_crds": 0}, "limitations": []})
    head = template.partition("<main>")[0].replace("CRD Compatibility Report", "Consolidado de compatibilidad Kubernetes")
    content = (f'<h1 id="summary">Compatibilidad Kubernetes — consolidado</h1><p>Fecha UTC: {datetime.now(timezone.utc).isoformat()}</p>'
               f'<p>Contextos: {len(entries)} · Estado global: <b>{overall}</b> · CRDs analizados: {sum(totals.values())}</p>'
               '<p>Un resultado PASS acredita las comprobaciones realizadas. WARN y UNKNOWN requieren revisión; FAIL contiene bloqueos y ERROR indica una evaluación incompleta.</p>'
               '<table><thead><tr><th>Contexto</th><th>Upgrade</th><th>CRDs</th><th>Estado</th><th>Pluto</th><th>Exit code</th><th>Score</th><th>Cobertura</th><th>Decisión</th></tr></thead><tbody>'
               + "".join(rows) + "</tbody></table>" + "".join(details))
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(head + "<main>" + content + "</main></html>", encoding="utf-8")
    return overall
