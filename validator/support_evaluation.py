"""Product support policy and observed runtime are separate from technical validation."""
from .models import finding


def evaluate_versions(row, target, catalog):
    findings = []
    for version in row["versions"] or row.get("detected_versions", []) or ["UNKNOWN"]:
        details = [d for d in row.get("version_details", []) if d["upstream_version"] == version]
        for detail in details or [None]:
            evaluated = catalog.evaluate(row["product"], version, target, row["source"], raw_version=detail["raw_version"]) if detail else catalog.evaluate(row["product"], version, target, row["source"])
            for item in evaluated:
                if detail:
                    item.evidence.update(detail)
                    item.evidence["installed_version"] = detail["raw_version"]
                    item.evidence["detected_version"] = detail["raw_version"]
                if item.status == "FAIL":
                    item.evidence.update(failure_domain="SUPPORT_POLICY", support_status="FAIL_SUPPORT_POLICY", technical_status="NOT_TESTED")
            if detail:
                compatible = next((f for f in evaluated if f.rule_id == "COMPATIBLE" and f.status == "PASS"), None)
                if compatible and detail["raw_version"] not in compatible.evidence["matrix"].get("vendor_versions", []):
                    evaluated.append(finding("VENDOR_BUILD_UNVERIFIED", "operator_compatibility", "UNKNOWN",
                        "La matriz upstream fue evaluada; no acredita esta revisión de empaquetado de Microsoft.",
                        source=compatible.source, relation="limitation", evidence=compatible.evidence | {"distribution_support_status": "NOT_VERIFIED"}))
            findings.extend(evaluated)
    return findings


def summarize(version, findings):
    ids = {f.rule_id for f in findings}
    if "NOT_COMPATIBLE" in ids:
        status = "OUTSIDE_SUPPORT_MATRIX"
    elif "VENDOR_BUILD_UNVERIFIED" in ids:
        status = "UNKNOWN_DISTRIBUTION_SUPPORT"
    elif any(f.status == "UNKNOWN" for f in findings):
        status = "UNKNOWN"
    elif "COMPATIBLE" in ids:
        status = "WITHIN_SUPPORT_MATRIX"
    else:
        status = "UNKNOWN"
    return {"version": str(version), "support_status": status,
        "findings": [{"rule_id": f.rule_id, "status": f.status, "source": f.source, "reviewed_on": f.evidence.get("reviewed_on"),
            "selector": f.evidence.get("catalog_lookup", {}).get("selected_selector"),
            "matrix_type": f.evidence.get("matrix", {}).get("matrix_type"),
            "min_kubernetes": f.evidence.get("matrix", {}).get("min_kubernetes"),
            "max_kubernetes": f.evidence.get("matrix", {}).get("max_kubernetes")} for f in findings]}


def observed_runtime(row):
    if row.get("evidence_summary", {}).get("data_plane", {}).get("runtime_confirmed_active_pods", 0):
        return "ACTIVE"
    for e in row.get("evidence", []):
        status = e.get("observed_status", {})
        if e.get("from", "").startswith("istioctl ") or any((status.get(k) or 0) > 0 for k in ("availableReplicas", "readyReplicas", "numberAvailable")):
            return "ACTIVE"
        if status.get("phase") == "Running" and e.get("activity") == "active" and any(c.get("ready") is True for c in e.get("observed_containers", [])):
            return "ACTIVE"
    return "NOT_CONFIRMED"


def dimensions(row, current, target, catalog, target_findings):
    current_summary = summarize(current, evaluate_versions(row, current, catalog))
    target_summary = summarize(target, target_findings)
    runtime = observed_runtime(row)
    current_summary["observed_runtime"] = runtime
    outside_current = current_summary["support_status"] == "OUTSIDE_SUPPORT_MATRIX"
    outside_target = target_summary["support_status"] == "OUTSIDE_SUPPORT_MATRIX"
    current_assessed = current_summary["support_status"] in ("OUTSIDE_SUPPORT_MATRIX", "WITHIN_SUPPORT_MATRIX")
    target_assessed = target_summary["support_status"] in ("OUTSIDE_SUPPORT_MATRIX", "WITHIN_SUPPORT_MATRIX")
    states = {f.status for f in target_findings}
    support = "FAIL_SUPPORT_POLICY" if outside_target else "UNKNOWN" if "UNKNOWN" in states else "WARN_SUPPORT_POLICY" if "WARN" in states else "PASS_SUPPORT_POLICY"
    row.update(current_kubernetes_evaluation=current_summary, target_kubernetes_evaluation=target_summary,
        support_status=support, technical_status="NOT_TESTED", technical_incompatibility_demonstrated=False,
        operational_status="RUNNING_OUTSIDE_SUPPORT_MATRIX" if runtime == "ACTIVE" and outside_current else "RUNNING_WITHIN_SUPPORT_MATRIX" if runtime == "ACTIVE" and current_summary["support_status"] == "WITHIN_SUPPORT_MATRIX" else "RUNNING_SUPPORT_UNKNOWN" if runtime == "ACTIVE" else "NOT_CONFIRMED",
        preexisting_support_debt=outside_current if current_assessed else None,
        additional_upgrade_support_risk=outside_target and not outside_current if current_assessed and target_assessed else None,
        decision="BLOCKED" if outside_target else "ATTENTION_REQUIRED" if support != "PASS_SUPPORT_POLICY" else "READY")
    if outside_target:
        observed = f"está operativo observado en Kubernetes {current}" if runtime == "ACTIVE" else f"no tiene runtime confirmado en Kubernetes {current}"
        scope = f"la versión actual {current} y el objetivo {target} están fuera de la matriz oficial" if outside_current else f"el objetivo {target} está fuera de la matriz oficial"
        row["support_explanation"] = (f'{row["product"]} {", ".join(row["versions"])} {observed}, pero {scope}. '
            "La herramienta no ha demostrado una falla técnica del producto mediante esta matriz; el upgrade no puede aprobarse bajo una política de componentes soportados. Los defectos técnicos de CRDs se evalúan por separado.")
    else:
        row["support_explanation"] = "Soporte documental evaluado para Kubernetes actual y objetivo; no equivale a una prueba técnica del producto en el objetivo."
