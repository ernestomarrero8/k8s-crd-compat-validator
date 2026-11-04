"""Orchestrate inventory, product support evidence and readiness without false PASS."""
from datetime import date
from .models import finding, aggregate
from .platform_discovery import collect, detect
from .azure_validator import collect_aks, analyze as analyze_aks
from .version_resolver import resolve


def analyze(collector, crds, current, target, catalog, snapshot=None, limit=2000):
    if snapshot is not None:
        if not isinstance(snapshot, dict) or snapshot.get("schema_version") != 1:
            raise ValueError("Snapshot de plataformas requiere schema_version: 1.")
        if collector and snapshot.get("context") != collector.context:
            raise ValueError("El snapshot no coincide con el contexto LIVE.")
        if snapshot.get("kubernetes_version") != str(current):
            raise ValueError("El snapshot debe declarar la versión actual de Kubernetes del análisis.")
        data = dict(snapshot)
        data["crds"] = crds
        for key in ("deployments.apps", "daemonsets.apps", "statefulsets.apps", "pods", "nodes", "helm"):
            if key not in data:
                data.setdefault("discovery_errors", []).append({"source": key, "reason": "not_in_snapshot"})
            elif not isinstance(data[key], list) or any(not isinstance(x, dict) for x in data[key]):
                raise ValueError("Lista de inventario de plataformas inválida.")
            elif len(data[key]) >= limit:
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
    rows = resolve(detect(data, catalog.detectors))
    for addon in azure["addons"]:
        definition = next((d for d in catalog.detectors if d["id"] == addon["detector_id"]), None)
        if definition and not any(r["id"] == definition["id"] for r in rows):
            rows.append({"id": definition["id"], "product": definition["product"], "namespace": "AKS managed",
                "category": definition.get("category", "operator"), "source": definition["source"], "versions": [], "unknown_version": True,
                "evidence": [{"from": "az aks show", "addon": addon["name"], "note": "Habilitado no determina versión efectiva."}], "resolved_versions": [], "resolution_sources": ["az aks show"]})
    findings = []
    for row in rows:
        row_findings = []
        for version in row["versions"] or row.get("detected_versions", []):
            row_findings.extend(catalog.evaluate(row["product"], version, target, row["source"]))
        if not row_findings:
            row_findings.extend(catalog.evaluate(row["product"], "UNKNOWN", target, row["source"]))
        sources = row.get("resolution_sources", [])
        row["confidence"] = "server_cli" if any(s.startswith("istioctl") for s in sources) else "helm_app_version" if "Helm" in sources else "image_tag" if any(s in ("pods", "deployments.apps", "daemonsets.apps", "statefulsets.apps") for s in sources) or any(e.get("confidence") == "image_tag" for e in row["evidence"]) else "product_metadata" if sources else "unknown"
        observed = row.get("detected_versions", row["versions"])
        row["detected_version"] = observed[0] if len(observed) == 1 else None
        for f in row_findings:
            f.evidence["detection_sources"] = row["evidence"]
            f.evidence["resolution_sources"] = row.get("resolution_sources", [])
            f.evidence["resolved_versions"] = row.get("resolved_versions", [])
            f.evidence["version_confidence"] = row["confidence"]
            f.evidence["raw_detected_versions"] = observed
        states = {f.status for f in row_findings}
        row["status"] = aggregate(row_findings)
        # WARN lifecycle and UNKNOWN coverage must both remain visible.
        row["compatibility"] = "No" if "FAIL" in states else "No verificada" if "UNKNOWN" in states else "Sí, según evidencia documentada"
        row["findings"] = [f.to_dict() for f in row_findings]
        findings.extend(row_findings)
    errors = data.get("discovery_errors", [])
    inventory = finding("PLATFORM-DISCOVERY", "operator_compatibility", "UNKNOWN" if errors else "PASS",
        "Cobertura del descubrimiento de plataformas.", evidence={"errors": errors, "products_detected": len(rows)},
        relation="limitation" if errors else "tested", validation_type="live" if collector else "snapshot",
        limitations=["Detectores por repositorios y charts conocidos. Mirrors privados, productos no catalogados y planos administrados pueden no ser visibles.",
                     "La versión de tag/Helm es evidencia declarada, no una verificación del binario por digest.",
                     "Las listas de workloads se descargan completas dentro del timeout y se examinan hasta el límite configurado."])
    findings.append(inventory)
    # When not AKS and complete node inventory is available, the managed-addon category is N/A, not PASS.
    if azure["detected"] or errors:
        findings.append(azure_finding)
    unknown = sum(p["compatibility"] == "No verificada" for p in rows)
    return {"title": "OPERATOR COMPATIBILITY ANALYSIS", "products": rows, "discovery": inventory.to_dict(), "aks": azure,
            "detector_diagnostics": [{"product": d["product"], "id": d["id"], "status": "DETECTED" if any(r["id"] == d["id"] for r in rows) else "INVENTORY_INCOMPLETE" if errors else "NOT_DETECTED",
                "catalog_present": d["product"] in catalog.product_files,
                "reason": "Identidad exacta encontrada" if any(r["id"] == d["id"] for r in rows) else "Sin coincidencia en repositorios/charts/grupos configurados; no prueba ausencia absoluta.",
                "inventory_errors": errors} for d in catalog.detectors],
            "support_coverage": {"products": len(rows), "unknown_products": unknown, "unknown_percentage": round(100 * unknown / len(rows), 1) if rows else None,
                                 "note": "Métrica de productos, no promesa de menos de 10%; no se excluyen limitaciones técnicas reales."},
            "catalog": catalog.provenance(), "analyzed_on": date.today().isoformat()}, findings
