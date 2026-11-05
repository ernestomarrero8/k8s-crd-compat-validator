"""Orchestrate inventory, product support evidence and readiness without false PASS."""
from datetime import date
from .models import finding, aggregate
from .platform_discovery import collect, safe_detect
from .detection_status import inventory_sources, presence, product_inventory_errors
from .workload_evidence import istio_summary
from .azure_validator import collect_aks, analyze as analyze_aks
from .version_resolver import resolve


def analyze(collector, crds, current, target, catalog, snapshot=None, limit=2000, full_evidence=False):
    if snapshot is not None:
        if not isinstance(snapshot, dict) or snapshot.get("schema_version") != 1:
            raise ValueError("Snapshot de plataformas requiere schema_version: 1.")
        if collector and snapshot.get("context") != collector.context:
            raise ValueError("El snapshot no coincide con el contexto LIVE.")
        if snapshot.get("kubernetes_version") != str(current):
            raise ValueError("El snapshot debe declarar la versión actual de Kubernetes del análisis.")
        data = dict(snapshot)
        data["discovery_errors"] = list(data.get("discovery_errors", []))
        data["crds"] = crds
        for key in ("deployments.apps", "daemonsets.apps", "statefulsets.apps", "pods", "nodes", "helm"):
            if key not in data:
                data.setdefault("discovery_errors", []).append({"source": key, "reason": "not_in_snapshot"})
            elif not isinstance(data[key], list) or any(not isinstance(x, dict) for x in data[key]):
                data.setdefault("discovery_errors", []).append({"source": key, "reason": "invalid_response"})
                data[key] = []
            elif len(data[key]) > limit or (key == "helm" and len(data[key]) == limit):
                data[key] = data[key][:limit]
                data.setdefault("discovery_errors", []).append({"source": key, "reason": "inventory_limit"})
    elif collector:
        data = collect(collector, crds, limit, catalog.detectors)
        if any(str(n.get("spec", {}).get("providerID", "")).lower().startswith("azure:") for n in data.get("nodes", [])):
            data["aks"], data["aks_error"] = collect_aks(data, collector.timeout)
    else:
        data = {"crds": crds, "discovery_errors": [{"source": "offline", "reason": "No hay snapshot de plataformas; no se consultó el clúster."}]}
    if isinstance(data.get("aks"), dict):
        reported = data["aks"].get("currentKubernetesVersion") or data["aks"].get("kubernetesVersion")
        if reported != str(current):
            data["aks"] = None
            data["aks_error"] = "La versión AKS de Azure no coincide con el servidor consultado; metadata no utilizada para atribuir add-ons."
    azure, azure_finding = analyze_aks(data, current, target)
    detected, detector_errors = safe_detect(data, catalog.detectors, full_evidence=full_evidence)
    rows = resolve(detected)
    sources_inventory = inventory_sources(data)
    required_errors = [s for s in sources_inventory if s["required"] and not s["completed"]]
    limitations = ["Helm inventory unavailable"] if any(s["source"] == "Helm" and not s["completed"] for s in sources_inventory) else []
    for addon in azure["addons"]:
        definition = next((d for d in catalog.detectors if d["id"] == addon["detector_id"]), None)
        if definition and not any(r["id"] == definition["id"] for r in rows):
            rows.append({"id": definition["id"], "product": definition["product"], "namespace": "AKS managed",
                "category": definition.get("category", "operator"), "source": definition["source"], "versions": [], "unknown_version": True,
                "evidence": [{"from": "az aks show", "addon": addon["name"], "activity": "active", "note": "Habilitado no determina versión efectiva."}], "resolved_versions": [], "resolution_sources": ["az aks show"]})
        elif definition:
            row = next(r for r in rows if r["id"] == definition["id"])
            row["evidence"].append({"from": "az aks show", "addon": addon["name"], "activity": "active"})
    findings = []
    for row in rows:
        product_errors = product_inventory_errors(sources_inventory, row["category"])
        row.update(presence(row))
        row["presence_status"] = row["detection_status"]
        row["inventory_complete"] = not bool(product_errors)
        row["inventory_errors"] = product_errors
        row["limitations"] = list(limitations)
        row["evidence_scope"] = "full_examined_inventory" if full_evidence else "bounded_samples"
        if row["id"] == "istio":
            definition = next(d for d in catalog.detectors if d["id"] == "istio")
            row["evidence_summary"] = istio_summary(data, definition)
        if row["id"] == "azure-keyvault":
            row["legacy_product"] = "Azure Key Vault CSI Driver"
        row_findings = []
        for version in row["versions"] or row.get("detected_versions", []):
            row_findings.extend(catalog.evaluate(row["product"], version, target, row["source"]))
        if not row_findings:
            row_findings.extend(catalog.evaluate(row["product"], "UNKNOWN", target, row["source"]))
        if row["detection_status"] == "ARTIFACTS_ONLY":
            row_findings.append(finding("CONTROLLER_NOT_CONFIRMED", "operator_compatibility", "UNKNOWN",
                "Sólo se encontraron artefactos; no se confirmó un controlador activo.", source=row["source"], relation="limitation",
                evidence={"product": row["product"], "target": str(target), "detection_status": row["detection_status"]}))
        elif row["detection_status"] == "DETECTED_INACTIVE":
            row_findings.append(finding("CONTROLLER_INACTIVE", "operator_compatibility", "WARN",
                "Componente identificado con evidencia de que no está operacional; revisar antes del upgrade.", source=row["source"],
                evidence={"product": row["product"], "target": str(target), "detection_status": row["detection_status"]}))
        sources = row.get("resolution_sources", [])
        row["confidence"] = "server_cli" if any(s.startswith("istioctl") for s in sources) else "helm_app_version" if "Helm" in sources else "product_metadata" if row.get("resolution_confidences") == ["product_metadata"] else "image_tag" if any(s in ("pods", "deployments.apps", "daemonsets.apps", "statefulsets.apps") for s in sources) or any(e.get("confidence") == "image_tag" for e in row["evidence"]) else "product_metadata" if sources else "unknown"
        observed = row.get("detected_versions", row["versions"])
        row["detected_version"] = observed[0] if len(observed) == 1 else None
        managed_snapshot = row["id"] == "snapshot" and not row["versions"] and any(e["from"] == "az aks show" for e in row["evidence"])
        if managed_snapshot:
            row["detected_version"] = "MANAGED"
            row["detected_versions"] = ["MANAGED"]
            row["versions"] = ["MANAGED"]
            row["confidence"] = "managed_metadata"
            row["managed_by"] = "AKS"
            row["reason"] = "MANAGED_VERSION_NOT_EXPOSED"
            row_findings = [finding("MANAGED_VERSION_NOT_EXPOSED", "operator_compatibility", "UNKNOWN",
                "Snapshot Controller habilitado en metadata AKS; la versión efectiva y su soporte para el objetivo no están expuestos.",
                source=row["source"], relation="limitation", evidence={"product": row["product"], "target": str(target),
                    "installed_version": "MANAGED", "detected_version": "MANAGED", "managed_by": "AKS", "reason": row["reason"],
                    "legacy_rule_id": "MANAGED_VERSION_UNEXPOSED"})]
            observed = ["MANAGED"]
        for f in row_findings:
            f.evidence["detection_sources"] = row["evidence"]
            f.evidence["resolution_sources"] = row.get("resolution_sources", [])
            f.evidence["resolved_versions"] = row.get("resolved_versions", [])
            f.evidence["version_confidence"] = row["confidence"]
            f.evidence["raw_detected_versions"] = observed
            if "evidence_summary" in row:
                f.evidence["detection_summary"] = row["evidence_summary"]
        states = {f.status for f in row_findings}
        row["status"] = aggregate(row_findings)
        # WARN lifecycle and UNKNOWN coverage must both remain visible.
        row["compatibility"] = "No" if "FAIL" in states else "No verificada" if "UNKNOWN" in states else "Sí, según evidencia documentada"
        if managed_snapshot:
            row["compatibility"] = "UNKNOWN"
            row["compatibility_legacy"] = "MANAGED_BY_AKS"
        row["findings"] = [f.to_dict() for f in row_findings]
        if any(e["product_id"] == row["id"] for e in detector_errors):
            row["detection_status"] = "DETECTION_ERROR"
        elif product_errors:
            row["detection_status"] = "INVENTORY_INCOMPLETE"
        findings.extend(row_findings)
    errors = data.get("discovery_errors", [])
    inventory = finding("PLATFORM-DISCOVERY", "operator_compatibility", "ERROR" if detector_errors else "UNKNOWN" if required_errors else "PASS",
        "Cobertura del descubrimiento de plataformas.", evidence={"errors": errors, "required_errors": required_errors, "detector_errors": detector_errors,
            "inventory_sources": sources_inventory, "products_detected": len(rows)},
        relation="limitation" if required_errors or detector_errors else "tested", validation_type="live" if collector else "snapshot",
        limitations=["Detectores por repositorios y charts conocidos. Mirrors privados, productos no catalogados y planos administrados pueden no ser visibles.",
                     "La versión de tag/Helm es evidencia declarada, no una verificación del binario por digest.",
                     "Las listas de workloads se descargan completas dentro del timeout y se examinan hasta el límite configurado."])
    findings.append(inventory)
    # When not AKS and complete node inventory is available, the managed-addon category is N/A, not PASS.
    if azure["detected"] or required_errors:
        findings.append(azure_finding)
    unknown = sum(any(f["status"] == "UNKNOWN" for f in p["findings"]) for p in rows)
    diagnostics = []
    for d in catalog.detectors:
        row = next((r for r in rows if r["id"] == d["id"]), None)
        internal_error = any(e["product_id"] == d["id"] for e in detector_errors)
        product_errors = product_inventory_errors(sources_inventory, d.get("category", "operator"))
        failure_description = "; ".join(f'{s["source"]}: {s["error"]} (examinados: {s["items_scanned"]})' for s in product_errors)
        state = "DETECTION_ERROR" if internal_error else "INVENTORY_INCOMPLETE" if product_errors else row["detection_status"] if row else "NOT_DETECTED"
        diagnostics.append({"product": d["product"], "id": d["id"], "status": state, "detection_status": state,
            "detected": bool(row), "legacy_status": "DETECTED" if row else state,
            "active_controller_confirmed": row["active_controller_confirmed"] if row else False,
            "catalog_present": d["product"] in catalog.product_files, "limitations": limitations,
            "reason": "Error interno del detector; detalle sensible omitido." if internal_error else "Inventario obligatorio incompleto: " + failure_description if product_errors else "Consultar evidencia de presencia y operación." if row else "Sin coincidencias en el inventario completado; no prueba ausencia absoluta.",
            "inventory_errors": product_errors, "inventory_complete": not bool(product_errors)})
    return {"title": "OPERATOR COMPATIBILITY ANALYSIS", "products": rows, "discovery": inventory.to_dict(), "aks": azure,
            "detector_diagnostics": diagnostics, "inventory_sources": sources_inventory,
            "support_coverage": {"products": len(rows), "unknown_products": unknown, "unknown_percentage": round(100 * unknown / len(rows), 1) if rows else None,
                                 "note": "Métrica de productos, no promesa de menos de 10%; no se excluyen limitaciones técnicas reales."},
            "catalog": catalog.provenance(), "analyzed_on": date.today().isoformat()}, findings
