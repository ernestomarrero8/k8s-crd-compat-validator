"""AKS identity from node provider metadata; never guess from a context name."""
import re
from .platform_discovery import command_json
from .models import finding

SOURCE = "https://learn.microsoft.com/en-us/azure/aks/supported-kubernetes-versions"
ADDONS = {"azurepolicy": "azure-policy", "omsagent": "ama", "azureKeyvaultSecretsProvider": "azure-keyvault", "ingressApplicationGateway": "agic"}


def collect_aks(data, timeout=30):
    providers = [n.get("spec", {}).get("providerID", "") for n in data.get("nodes", [])]
    identities = {tuple(m.groups()) for p in providers if (m := re.match(r"(?i)^azure:///subscriptions/([^/]+)/resourceGroups/([^/]+)/", p))}
    if len(identities) != 1 or not providers or any(not re.match(r"(?i)^azure:///subscriptions/([^/]+)/resourceGroups/([^/]+)/", p) for p in providers):
        return None, "No hay una identidad Azure única verificable mediante los nodos."
    subscription, node_group = next(iter(identities))
    clusters, error = command_json(["az", "aks", "list", "--subscription", subscription, "--query",
        "[].{name:name,resourceGroup:resourceGroup,nodeResourceGroup:nodeResourceGroup}", "-o", "json"], timeout)
    if error or not isinstance(clusters, list):
        return None, "Azure CLI no pudo obtener metadata de AKS; no se infiere identidad desde el contexto."
    matches = [c for c in clusters if str(c.get("nodeResourceGroup", "")).lower() == node_group.lower()]
    if len(matches) != 1:
        return None, "No se pudo asociar inequívocamente el node resource group a un AKS."
    cluster = matches[0]
    value, error = command_json(["az", "aks", "show", "--subscription", subscription, "--resource-group", cluster["resourceGroup"],
                                "--name", cluster["name"], "-o", "json"], timeout)
    if error or not isinstance(value, dict) or str(value.get("nodeResourceGroup", "")).lower() != node_group.lower():
        return None, "No se pudo verificar la metadata AKS del clúster de origen."
    return value, None


def analyze(data, current, target):
    nodes = data.get("nodes", [])
    azure = any(str(n.get("spec", {}).get("providerID", "")).lower().startswith("azure:") for n in nodes)
    aks = data.get("aks")
    info = {"detected": azure or bool(aks), "target_version": str(target), "current_version": None,
            "node_image_versions": sorted({str(n.get("metadata", {}).get("labels", {}).get("kubernetes.azure.com/node-image-version")) for n in nodes if n.get("metadata", {}).get("labels", {}).get("kubernetes.azure.com/node-image-version")}),
            "node_kubelet_versions": sorted({n.get("status", {}).get("nodeInfo", {}).get("kubeletVersion", "UNKNOWN") for n in nodes}),
            "addons": [], "limitations": []}
    if isinstance(aks, dict):
        info["current_version"] = aks.get("currentKubernetesVersion") or aks.get("kubernetesVersion")
        for key, value in (aks.get("addonProfiles") or {}).items():
            if isinstance(value, dict) and value.get("enabled") is True:
                info["addons"].append({"name": key, "detector_id": ADDONS.get(key)})
        security = aks.get("securityProfile") or {}
        if ((security.get("defender") or {}).get("securityMonitoring") or {}).get("enabled"):
            info["addons"].append({"name": "Defender for Containers", "detector_id": "defender"})
        for key, value in (aks.get("storageProfile") or {}).items():
            if isinstance(value, dict) and value.get("enabled"):
                info["addons"].append({"name": key, "detector_id": {"diskCSIDriver": "azure-disk", "fileCSIDriver": "azure-file", "snapshotController": "snapshot"}.get(key)})
        if any(p.get("enableAutoScaling") for p in aks.get("agentPoolProfiles", [])):
            info["addons"].append({"name": "Cluster Autoscaler", "detector_id": "autoscaler"})
    info["limitations"] = [data.get("aks_error") or "Metadata AKS observada; la versión efectiva y soporte de cada add-on se evalúan por separado.",
        "Una versión Kubernetes soportada upstream no acredita disponibilidad de upgrade, región, canal LTS ni soporte del add-on administrado en AKS.",
        "Node images se inventarían; no se infiere compatibilidad futura por su nombre."]
    observation = finding("AKS-SUPPORT-UNVERIFIED", "aks", "UNKNOWN", "Soporte de AKS y sus add-ons para el objetivo requiere evidencia específica de Microsoft.",
        source=SOURCE, relation="limitation", evidence=info,
        recommendation="Revisar versiones/región/canal AKS, imágenes de nodos y versiones administradas de add-ons antes del upgrade.")
    return info, observation
