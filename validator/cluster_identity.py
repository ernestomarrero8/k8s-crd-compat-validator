"""Stable read-only cluster identity; never infer identity from an -admin suffix."""
import hashlib
import re
from urllib.parse import urlsplit
from .collector import CollectionError

RESOURCE_ID = re.compile(r"(?i)^/subscriptions/[^/?#]+/resourcegroups/[^/?#]+/providers/microsoft\.containerservice/managedclusters/[^/?#]+/?$")


def identify(data, context):
    azure = data.get("aks") or {}
    value = azure.get("resource_id") or azure.get("id")
    source = "azure_resource_id"
    if not value and all(azure.get(k) for k in ("subscription_id", "resource_group", "cluster_name")):
        value = f'/subscriptions/{azure["subscription_id"]}/resourceGroups/{azure["resource_group"]}/providers/Microsoft.ContainerService/managedClusters/{azure["cluster_name"]}'
        source = "azure_subscription_resource_group_name"
    if isinstance(value, str) and RESOURCE_ID.fullmatch(value):
        return {"cluster_identity": value.rstrip("/").lower(), "source": source}
    uid = data.get("kube_system_uid")
    if isinstance(uid, str) and re.fullmatch(r"[A-Za-z0-9-]{1,128}", uid):
        return {"cluster_identity": "kube-system:" + uid, "source": "kube_system_uid"}
    try:
        server = urlsplit(data.get("api_server", ""))
        if server.scheme == "https" and server.hostname and not server.username and not server.password and not server.query and not server.fragment:
            host = server.hostname.lower()
            host = f"[{host}]" if ":" in host else host
            port = ":" + str(server.port) if server.port and server.port != 443 else ""
            return {"cluster_identity": "https://" + host + port + server.path.rstrip("/"), "source": "api_server_url"}
    except (ValueError, TypeError):
        pass
    return {"cluster_identity": "context:" + hashlib.sha256(context.encode("utf-8")).hexdigest(), "source": "context_fallback",
        "limitation": "No se obtuvo identidad compartida verificable; no se agrupan contextos por nombre."}


def collect_identity(collector, platform, context):
    result = identify(platform, context)
    if result["source"].startswith("azure_") or not collector:
        return result
    data = {"aks": platform.get("aks", {})}
    try:
        data["kube_system_uid"] = collector.get("namespaces", name="kube-system").get("metadata", {}).get("uid")
    except CollectionError:
        pass
    if not data.get("kube_system_uid"):
        try:
            data["api_server"] = collector.api_server()
        except CollectionError:
            pass
    return identify(data, context)
