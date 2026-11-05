"""Link CRD ownership to the product registry, never to version guesses from CRDs."""
from .models import finding


def owner_result(crd, platform, ownership):
    names = {o["product_id"] for o in ownership if crd.get("spec", {}).get("group") in o["groups"] or crd.get("metadata", {}).get("name") in o["crds"]}
    if len(names) != 1:
        return None
    matches = [r for r in platform.get("products", []) if r["id"] in names]
    return matches[0] if len(matches) == 1 else None


def product_finding(product):
    return finding("PRODUCT_SUPPORT", "operator", product["status"], "Compatibilidad del producto propietario evaluada una vez en el registro de plataformas.",
        severity="INFO" if product["status"] == "PASS" else None,
        source=product["findings"][0]["source"], relation="documented",
        evidence={"product": product["product"], "installed_versions": product["versions"],
                  "resolved_versions": product.get("resolved_versions", []), "resolution_sources": product.get("resolution_sources", []),
                  "reviewed_on": sorted({f["evidence"]["reviewed_on"] for f in product["findings"] if f["evidence"].get("reviewed_on")}),
                  "target": product["findings"][0]["evidence"].get("target"), "product_registry_ref": product["id"],
                  "score_weight": 0, "counted_in": {"aks": "aks_addons", "storage": "storage"}.get(product.get("category"), "operators"),
                  "support_status": product["status"], "support_policy_status": product.get("support_status", product["status"]),
                  "technical_status": product.get("technical_status", "NOT_TESTED"),
                  "support_findings": [f["rule_id"] for f in product["findings"]]},
        recommendation="Consultar el detalle único de la matriz del producto; resolver por separado los defectos técnicos del CRD.",
        limitations=["El soporte del producto no prueba que la definición, conversión o datos persistidos del CRD sean correctos."])


def unmapped_finding():
    return finding("NO_PRODUCT_OWNER", "operator", "UNKNOWN", "No existe una asociación explícita entre este CRD y un producto detectado.",
        relation="limitation", recommendation="Registrar ownership documentado y detectar la versión del producto; no inferirla por labels o por la existencia del CRD.")


def annotate(result, product):
    if product is None:
        return result
    result["product_compatibility"] = {"product": product["product"], "versions": product["versions"], "status": product["status"],
                                      "sources": sorted({f["source"] for f in product["findings"]}),
                                      "support_status": product.get("support_status", product["status"]), "technical_status": product.get("technical_status", "NOT_TESTED")}
    # Risk concerns actual upgrade findings. Coverage limitations remain in findings/status.
    technical_risks = [f for f in result["findings"] if f["category"] != "operator" and f["status"] in ("WARN", "FAIL", "ERROR")]
    result["upgrade_risk"] = "INFO" if product["status"] == "PASS" and not technical_risks else result["severity"]
    return result
