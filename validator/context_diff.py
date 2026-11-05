"""Actionable, allowlisted differences between reports; does not decide cluster identity."""
from html import escape
import json


def comparison_coverage(members):
    affected, by_context, truncated = set(), {}, False
    for entry, report in members:
        sources = report.get("platform", {}).get("inventory_sources", []) if report else []
        required = [s for s in sources if s.get("required")]
        by_context[entry["context"]] = {s["source"]: s.get("items_scanned") for s in required}
        if not required:
            affected.add("inventory_metadata_unavailable")
        for source in required:
            if not source.get("completed") or source.get("inventory_complete") is False:
                affected.add(source["source"])
                truncated |= source.get("error") == "inventory_limit" or source.get("continuation_pending", False)
    if not affected:
        return None
    result = {"reason": "inventory_truncated" if truncated else "inventory_incomplete", "affected_sources": sorted(affected), "examined_by_context": by_context}
    if len(members) == 2 and len(affected) == 1:
        source = next(iter(affected))
        result["context_a_examined"] = by_context[members[0][0]["context"]].get(source)
        result["context_b_examined"] = by_context[members[1][0]["context"]].get(source)
    return result


def compare_contexts(members, fingerprint):
    reports = {e["context"]: r for e, r in members if r}
    crds = {c: {r["name"]: r for r in report["crds"]} for c, report in reports.items()}
    products = {c: {p["id"]: p for p in report.get("platform", {}).get("products", [])} for c, report in reports.items()}
    all_crds = set().union(*(set(v) for v in crds.values()))
    all_products = set().union(*(set(v) for v in products.values()))
    common_crds = set.intersection(*(set(v) for v in crds.values())) if crds else set()
    common_products = set.intersection(*(set(v) for v in products.values())) if products else set()
    names = {id_: next(p[id_]["product"] for p in products.values() if id_ in p) for id_ in all_products}
    crd_changes = sorted(n for n in common_crds if len({fingerprint({"crds": [v[n]]}) for v in crds.values()}) > 1)
    product_changes = sorted(names[n] for n in common_products if len({fingerprint({"platform": {"products": [v[n]]}}) for v in products.values()}) > 1)
    versions = {id_: {c: products[c][id_].get("versions") or ["UNKNOWN"] if id_ in products[c] else ["NOT_DETECTED"] for c in reports} for id_ in sorted(all_products)}
    versions = {id_: values for id_, values in versions.items() if len({tuple(v) for v in values.values()}) > 1}
    inventory = {c: report.get("platform", {}).get("inventory_sources", []) for c, report in reports.items()}
    errors = {c: [{k: s.get(k) for k in ("source", "error", "required", "items_scanned")} for s in sources if s.get("required") and not s.get("completed", True)] for c, sources in inventory.items()}
    sources = set().union(*({s["source"] for s in values if s.get("required")} for values in inventory.values()))
    changed_sources = sorted(source for source in sources if len({json.dumps(next((s for s in values if s["source"] == source), None), sort_keys=True) for values in inventory.values()}) > 1)
    result = {"crds": {"counts": {c: len(v) for c, v in crds.items()}, "only_in": {c: sorted(set(v) - common_crds) for c, v in crds.items()}, "changed": crd_changes},
        "products": {"counts": {c: len(v) for c, v in products.items()}, "only_in": {c: sorted(names[n] for n in set(v) - common_products) for c, v in products.items()}, "changed": product_changes},
        "inventory_errors": {"by_context": errors, "changed_sources": changed_sources}, "versions": versions,
        "kubernetes_versions": {c: {"current": r["current_version"], "target": r["target_version"]} for c, r in reports.items()}, "areas": []}
    if crd_changes or common_crds != all_crds:
        result["areas"].append("CRDs")
    if product_changes or common_products != all_products:
        result["areas"].append("Productos detectados / evidencia")
    if changed_sources:
        result["areas"].append("Consultas fallidas / cobertura del inventario")
    if versions or len({json.dumps(v, sort_keys=True) for v in result["kubernetes_versions"].values()}) > 1:
        result["areas"].append("Versiones")
    for field, label in (("global_findings", "Hallazgos globales"), ("pluto", "Pluto"), ("readiness", "Readiness"), ("validator", "Resultado del validador")):
        if len({fingerprint({field: r.get(field)}) for r in reports.values()}) > 1:
            result["areas"].append(label)
    if len({e["exit_code"] for e, _ in members}) > 1:
        result["areas"].append("Exit codes de ejecución")
    if not result["areas"]:
        result["areas"].append("Sin diferencias semánticas concluyentes; revisar cobertura antes de afirmar igualdad")
    return result


def diff_html(diff):
    esc = lambda value: escape(str(value), quote=True)
    def limited(values):
        return ", ".join(map(str, values[:20])) + (f" … (+{len(values) - 20}; detalle en JSON)" if len(values) > 20 else "")
    rows = []
    for context, count in diff["crds"]["counts"].items():
        rows.append(("CRDs", context, f'{count}; visibles fuera del conjunto común: {limited(diff["crds"]["only_in"][context]) or "—"}'))
    if diff["crds"]["changed"]:
        rows.append(("CRDs", "Definiciones/hallazgos diferentes", limited(diff["crds"]["changed"])))
    for context, count in diff["products"]["counts"].items():
        rows.append(("Productos", context, f'{count}; visibles fuera del conjunto común: {limited(diff["products"]["only_in"][context]) or "—"}'))
    if diff["products"]["changed"]:
        rows.append(("Productos", "Resultado/evidencia diferente", limited(diff["products"]["changed"])))
    for context, errors in diff["inventory_errors"]["by_context"].items():
        rows.append(("Consultas fallidas", context, "; ".join(f'{s["source"]}: {s["error"]}' for s in errors) or "Sin errores registrados"))
    if diff["inventory_errors"]["changed_sources"]:
        rows.append(("Cobertura del inventario", "Fuentes diferentes", limited(diff["inventory_errors"]["changed_sources"])))
    for product, values in diff["versions"].items():
        for context, versions in values.items():
            rows.append(("Versiones / " + product, context, ", ".join(versions)))
    return '<h3>Diferencias entre contextos</h3><p>' + esc("; ".join(diff["areas"])) + '</p><table><thead><tr><th>Área</th><th>Contexto</th><th>Diferencia observada</th></tr></thead><tbody>' + "".join(
        f'<tr><td>{esc(area)}</td><td>{esc(context)}</td><td>{esc(value)}</td></tr>' for area, context, value in rows) + '</tbody></table><p>El diff describe observaciones; por sí solo no prueba un error de identidad ni atribuye la causa a permisos o al momento de captura.</p>'


def technical_causes(entry, report):
    def cause(source, reason, scanned=None):
        action = {"inventory_limit": "Revisar --platform-limit y completar el inventario; no descartar los objetos que quedaron fuera.",
            "forbidden": "Revisar RBAC de lectura para esta fuente con el contexto indicado.",
            "unauthorized": "Revisar autenticación del contexto.", "timeout": "Revisar conectividad y --timeout.",
            "context_timeout": "Revisar --context-timeout y console.txt.", "report_unavailable": "Consultar console.txt y el JSON de este contexto.",
            "cluster_timeout": "Se agotó --cluster-timeout; revisar el presupuesto global y las consultas pendientes.",
            "coverage_below_threshold": "Completar la evidencia pendiente indicada por el reporte; no asumir incompatibilidad."}.get(reason, "Revisar la fuente y su diagnóstico en el detalle del contexto; no publicar stderr ni credenciales.")
        return {"context": entry["context"], "source": source, "reason": reason, "items_scanned": scanned, "action": action}
    if not report:
        return [cause("validator_process", "context_timeout" if entry["exit_code"] == 124 else "report_unavailable")]
    result = [cause(s["source"], s.get("error") or "incomplete", s.get("items_scanned")) for s in report.get("platform", {}).get("inventory_sources", []) if s.get("required") and not s.get("completed")]
    for diagnostic in report.get("platform", {}).get("detector_diagnostics", []):
        if diagnostic.get("detection_status") == "DETECTION_ERROR":
            result.append(cause("detector:" + diagnostic["id"], "detector_parser_error"))
    for f in report.get("global_findings", []) + [f for c in report["crds"] for f in c["findings"]]:
        if f["status"] == "ERROR":
            result.append(cause(f["rule_id"], f.get("evidence", {}).get("error_code") or "technical_check_error"))
    if entry["exit_code"] == 124:
        result.append(cause("validator_process", "context_timeout"))
    if not result and entry["exit_code"] == 2:
        result.append(cause("evidence_coverage", "coverage_below_threshold") if report.get("readiness", {}).get("decision") == "INCOMPLETE" else cause("validator_process", "technical_error_not_recorded"))
    return result
