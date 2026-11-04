"""Orchestrate inventory, product support evidence and readiness without false PASS."""
from datetime import date
from .models import finding, aggregate
from .platform_discovery import collect, detect
from .azure_validator import collect_aks, analyze as analyze_aks


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
        data = collect(collector, crds, limit)
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
    rows = detect(data, catalog.detectors)
    for addon in azure["addons"]:
        definition = next((d for d in catalog.detectors if d["id"] == addon["detector_id"]), None)
        if definition and not any(r["id"] == definition["id"] for r in rows):
            rows.append({"id": definition["id"], "product": definition["product"], "namespace": "AKS managed",
                "category": definition.get("category", "operator"), "source": definition["source"], "versions": [], "unknown_version": True,
                "evidence": [{"from": "az aks show", "addon": addon["name"], "note": "Habilitado no determina versión efectiva."}]})
    findings = []
    for row in rows:
        row_findings = []
        for version in row["versions"]:
            row_findings.extend(catalog.evaluate(row["product"], version, target, row["source"]))
        if not row["versions"] or row["unknown_version"]:
            row_findings.extend(catalog.evaluate(row["product"], "UNKNOWN", target, row["source"]))
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
    return {"title": "OPERATOR COMPATIBILITY ANALYSIS", "products": rows, "discovery": inventory.to_dict(), "aks": azure,
            "catalog": catalog.provenance(), "analyzed_on": date.today().isoformat()}, findings
