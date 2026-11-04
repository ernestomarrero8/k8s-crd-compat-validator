"""Executive platform overview and transparent readiness scoring."""
from html import escape
import json
from .rule_engine import safe_source


def html(report):
    if "platform" not in report:
        return ""
    esc = lambda x: escape(str(x), quote=True)
    platform, readiness = report["platform"], report["readiness"]
    rows = []
    for product in platform["products"]:
        origins = ", ".join(sorted({e["from"] for e in product["evidence"]}))
        versions = ", ".join(product.get("resolved_versions", product["versions"])) or "UNKNOWN"
        if product["unknown_version"] and product["versions"]:
            versions += ", UNKNOWN"
        sources = sorted({f["source"] for f in product["findings"]})
        links = " ".join(f'<a href="{esc(source)}" rel="noreferrer">Fuente oficial</a>' for source in sources if safe_source(source))
        rows.append(f'<tr><td>{esc(product["product"])}<br>{esc(product["namespace"])}</td><td>{esc(versions)}</td><td>{esc(origins)}</td>'
                    f'<td>{esc(product["compatibility"])}</td><td>{esc(product["status"])}</td><td>{links}</td></tr>')
    categories = "".join(f'<tr><td>{esc(key)}</td><td>{esc(value["weight"])}%</td><td>{esc(value["status"])}</td><td>{esc(value["earned_points"])}</td></tr>'
                         for key, value in readiness["categories"].items())
    detail = "".join('<details><summary>' + esc(p["product"]) + ' — resolución y evidencia de detección</summary><pre>'
                     + esc(json.dumps({"resolved_versions": p.get("resolved_versions", []), "all_observed_versions": p["versions"],
                                       "resolution_sources": p.get("resolution_sources", []), "mixed_versions": p.get("version_conflict", False),
                                       "evidence": p["evidence"]}, ensure_ascii=False, indent=2)) + '</pre></details>' for p in platform["products"])
    return ('<section><h2>Upgrade Readiness Score</h2>'
        f'<p style="font-size:1.6em"><b>{esc(readiness["score"])}/100 · {esc(readiness["decision"])}</b></p>'
        '<table><thead><tr><th>Categoría</th><th>Peso</th><th>Estado</th><th>Puntos</th></tr></thead><tbody>' + categories + '</tbody></table>'
        f'<p>{esc(readiness["method"])}</p><p>{esc(readiness["limitation"])}</p></section>'
        '<section><h2>Cluster Platform Compatibility</h2><h3>OPERATOR COMPATIBILITY ANALYSIS</h3>'
        f'<p>Objetivo Kubernetes/AKS: {esc(report["target_version"])}. Una versión de imagen o Helm no demuestra el binario ejecutado ni soporte de la distribución administrada.</p>'
        '<div style="overflow-x:auto"><table><thead><tr><th>Producto / namespace</th><th>Versiones observadas</th><th>Detectado desde</th><th>Compatibilidad objetivo</th><th>Resultado</th><th>Evidencia</th></tr></thead><tbody>'
        + "".join(rows) + '</tbody></table></div>' + ('<p>Sin productos detectados dentro del inventario disponible; consultar cobertura y errores de descubrimiento.</p>' if not rows else '')
        + detail + '<h3>AKS Platform Compatibility</h3><pre>' + esc(json.dumps(platform["aks"], ensure_ascii=False, indent=2))
        + '</pre><h3>Cobertura de soporte por producto</h3><pre>' + esc(json.dumps(platform.get("support_coverage", {}), ensure_ascii=False, indent=2))
        + '</pre><h3>Catálogos de plataformas</h3><pre>' + esc(json.dumps(platform["catalog"], ensure_ascii=False, indent=2)) + '</pre></section>')


def markdown(report, md):
    if "platform" not in report:
        return []
    readiness = report["readiness"]
    lines = ["", "## Upgrade Readiness Score", "", f"{readiness['score']}/100 · {readiness['decision']}", "", md(readiness["method"]), "", md(readiness["limitation"]),
        "", "## Cluster Platform Compatibility — OPERATOR COMPATIBILITY ANALYSIS", "",
        "| Producto | Versiones | Origen | Compatibilidad | Resultado |", "|---|---|---|---|---|"]
    for row in report["platform"]["products"]:
        origins = ", ".join(sorted({e["from"] for e in row["evidence"]}))
        versions = ", ".join(row["versions"]) or "UNKNOWN"
        lines.append(f"| {md(row['product'])} | {md(versions)} | {md(origins)} | {md(row['compatibility'])} | {row['status']} |")
    lines += ["", "AKS: " + md(json.dumps(report["platform"]["aks"], ensure_ascii=False)), ""]
    return lines
