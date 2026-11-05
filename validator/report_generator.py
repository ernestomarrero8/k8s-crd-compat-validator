"""Escaped standalone reports with explicit scope and evidence."""
from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import quote
from .models import STATES, SEVERITIES
from .platform_report import html as platform_html, markdown as platform_markdown
from . import __version__


def build_report(cluster, current, target, path, crds, global_findings, queries=0, target_context=None):
    all_findings = [f for c in crds for f in c["findings"]] + [f.to_dict() for f in global_findings]
    counts = Counter(c["status"] for c in crds)
    risk_counts = Counter(f["severity"] for f in all_findings if f["status"] in ("WARN", "FAIL", "ERROR"))
    states = [f["status"] for f in all_findings]
    return {"schema_version": "1.5", "tool": "k8s-crd-compat-validator", "tool_version": __version__,
            "analyzed_at": datetime.now(timezone.utc).isoformat(), "cluster": cluster,
            "current_version": str(current), "target_version": str(target), "upgrade_path": path,
            "target_context": target_context, "read_only": True, "kubectl_queries": queries,
            "overall_status": max(states, key=STATES.index, default="UNKNOWN"),
            "summary": {"total_crds": len(crds), "states": {s: counts[s] for s in STATES},
                        "risks_by_severity": {s: risk_counts[s] for s in reversed(SEVERITIES)},
                        "unknown_findings": sum(f["status"] == "UNKNOWN" for f in all_findings)},
            "limitations": ["PASS solo acredita las comprobaciones realizadas, no garantiza el upgrade.",
                            "La detección de APIs nativas se delega en Pluto; consultar su sección y estado.",
                            "No se prueban escrituras, reconciliación, CEL completo ni versiones persistidas por objeto.",
                            "La cobertura documental y los hashes del catálogo se registran en este informe.",
                            "No se exportan cuerpos de Custom Resources, annotations completas, kubeconfig, certificados ni stderr de kubectl."],
            "global_findings": [f.to_dict() for f in global_findings], "crds": crds}


def md(value):
    text = escape(str(value), quote=False)
    return re.sub(r"([\\`*_{}\[\]()#+.!|>-])", r"\\\1", text).replace("\r", " ").replace("\n", " ")


def markdown(report):
    lines = ["# Kubernetes CRD Compatibility Validator", "",
             f"Clúster: {md(report['cluster'])} · {md(report['current_version'])} → {md(report['target_version'])}", "",
             f"Fecha UTC: {md(report['analyzed_at'])} · Estado general: **{report['overall_status']}**", "",
             f"CRDs: {report['summary']['total_crds']} · Consultas kubectl: {report['kubectl_queries']}", "",
             "| Estado | CRDs |", "|---|---:|"]
    lines += [f"| {s} | {n} |" for s, n in report["summary"]["states"].items()]
    lines += ["", "| Severidad de riesgos | Hallazgos |", "|---|---:|"]
    lines += [f"| {s} | {n} |" for s, n in report["summary"]["risks_by_severity"].items()]
    lines += platform_markdown(report, md)
    lines += ["", "| CRD | Producto | Soporte producto | Riesgo upgrade |", "|---|---|---|---|"]
    lines += [f"| {md(c['name'])} | {md(c.get('product_compatibility', {}).get('product', '—'))} | {md(c.get('product_compatibility', {}).get('status', '—'))} | {md(c.get('upgrade_risk', c['severity']))} |" for c in report["crds"]]
    lines += ["", "## Alcance y limitaciones", ""] + ["- " + md(x) for x in report["limitations"]]
    lines += ["", "## Catálogos utilizados", "", md(json.dumps(report.get("knowledge", {}), ensure_ascii=False)), "", "## Pluto", ""]
    scan = report.get("pluto", {})
    lines += [md(scan.get("status", "UNKNOWN")) + ": " + md(scan.get("message", "Sin resultado")), "", "Comando: " + md(" ".join(scan.get("command", [])) or "No ejecutado"), "", "<pre>" + escape(scan.get("stdout", "")) + "</pre>", ""]
    groups = [("Hallazgos globales", report["global_findings"])] + [(f"{c['name']} — {c['status']} / {c['severity']}", c["findings"]) for c in report["crds"]]
    for title, findings in groups:
        lines += ["", "## " + md(title), ""]
        for f in findings:
            lines += [f"### {md(f['rule_id'])} · {f['status']} · {f['severity']}", "", md(f["description"]), "",
                      f"Categoría: {md(f['category'])} · Relación: {md(f['relation'])} · Método: {md(f['validation_type'])}", "",
                      "Evidencia: " + md(json.dumps(f["evidence"], ensure_ascii=False)), "",
                      "Recomendación: " + md(f["recommendation"]), "",
                      "Fuente: [Referencia técnica](<" + quote(f["source"], safe=":/?=#%&+@-._~") + ">)", ""]
            lines += ["- Límite: " + md(x) for x in f["limitations"]]
    return "\n".join(lines) + "\n"


def html(report):
    def esc(v):
        return escape(str(v), quote=True)
    rows = "".join(f"<tr><td>{esc(c['name'])}</td><td>{c['status']}</td><td>{c['severity']}</td>"
                   f"<td>{esc(c.get('product_compatibility', {}).get('product', '—'))}<br>{esc(', '.join(c.get('product_compatibility', {}).get('versions', [])))}</td>"
                   f"<td>{esc(c.get('product_compatibility', {}).get('status', '—'))}</td><td>{esc(c.get('upgrade_risk', c['severity']))}</td></tr>" for c in report["crds"])
    summary = " · ".join(f"{s}: {n}" for s, n in report["summary"]["states"].items())
    risks = " · ".join(f"{s}: {n}" for s, n in report["summary"]["risks_by_severity"].items())
    scan = report.get("pluto", {})
    content = ["<section><h2>Catálogos utilizados</h2><pre>" + esc(json.dumps(report.get("knowledge", {}), ensure_ascii=False, indent=2)) + "</pre></section>",
               "<section><h2>Pluto</h2><p>" + esc(scan.get("status", "UNKNOWN")) + ": " + esc(scan.get("message", "Sin resultado")) + "</p><p>Pluto exit: " + esc(scan.get("exit_code") if scan.get("exit_code") is not None else "No ejecutado / no disponible") + "</p><pre>" + esc(" ".join(scan.get("command", []))) + "</pre><pre>" + esc(scan.get("stdout", "")) + "</pre></section>"]
    if "validator" in report:
        content.insert(0, "<section><h2>Validador</h2><pre>" + esc(json.dumps(report["validator"], ensure_ascii=False, indent=2)) + "</pre></section>")
    groups = [("Hallazgos globales", report["global_findings"])] + [(c["name"], c["findings"]) for c in report["crds"]]
    for title, findings in groups:
        content.append(f"<section><h2>{esc(title)}</h2>")
        for f in findings:
            content.append(f"<details open><summary><b>{esc(f['rule_id'])}</b> <span class='{f['status']}'>{f['status']} / {f['severity']}</span></summary>"
                           f"<p>{esc(f['description'])}</p><p>{esc(f['category'])} · {esc(f['relation'])} · {esc(f['validation_type'])}</p>"
                           f"<pre>{esc(json.dumps(f['evidence'], ensure_ascii=False, indent=2))}</pre>"
                           f"<p><b>Recomendación:</b> {esc(f['recommendation'])}</p>"
                           f"<p><a href='{esc(f['source'])}' rel='noreferrer'>Fuente técnica</a></p>"
                           + "".join(f"<p class='limit'>Límite: {esc(x)}</p>" for x in f["limitations"]) + "</details>")
        content.append("</section>")
    return """<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'">
<title>CRD Compatibility Report</title><style>
body{font:16px/1.55 system-ui,sans-serif;max-width:1100px;margin:40px auto;padding:0 22px;color:#182c42;background:#f7f9fc}
h1,h2{line-height:1.25}table{border-collapse:collapse;width:100%;background:white}td,th{border:1px solid #b8c9d8;padding:10px;text-align:left}
details{background:white;border:1px solid #bccbdb;border-radius:6px;margin:12px 0;padding:14px}summary{cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eef3f8;padding:12px}
.FAIL,.ERROR{color:#a81818}.WARN{color:#805000}.UNKNOWN{color:#525b67}.PASS{color:#176232}.limit{color:#4e6073}a{color:#154f91}section{margin:32px 0}p{overflow-wrap:anywhere}
@media print{body{background:white;margin:0;max-width:none}details{break-inside:avoid}}</style><main>""" + (
        f"<h1>Kubernetes CRD Compatibility Validator</h1><p>{esc(report['cluster'])} · {report['current_version']} → {report['target_version']}</p>"
        f"<p>{esc(report['analyzed_at'])} · Estado general: <b>{report['overall_status']}</b></p>"
        f"<p>{report['summary']['total_crds']} CRDs · {esc(summary)}</p><p>Riesgos por severidad: {esc(risks)}</p>"
        + platform_html(report) +
        "<h2>Alcance y limitaciones</h2><ul>" + "".join(f"<li>{esc(x)}</li>" for x in report["limitations"]) + "</ul>"
        "<table><thead><tr><th>CRD afectado</th><th>Estado técnico / cobertura</th><th>Severidad</th><th>Producto / versiones</th><th>Soporte producto</th><th>Riesgo upgrade</th></tr></thead><tbody>" + rows + "</tbody></table>"
        + "".join(content) + "</main></html>")


def write_reports(report, directory, format_="all"):
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    formats = ("json", "markdown", "html") if format_ == "all" else (format_,)
    written = []
    for fmt in formats:
        ext = "md" if fmt == "markdown" else fmt
        target = path / f"report.{ext}"
        content = json.dumps(report, ensure_ascii=False, indent=2) + "\n" if fmt == "json" else markdown(report) if fmt == "markdown" else html(report)
        target.write_text(content, encoding="utf-8", newline="\n")
        written.append(target)
    return written
