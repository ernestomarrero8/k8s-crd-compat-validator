"""Allowlisted container observations and compact Istio evidence; no support decisions."""
from collections import Counter
from datetime import datetime, timezone
from .platform_catalog import release
from .detection_status import workload_activity
from .detection_status import OPTIONAL


def image_parts(image):
    repository = image.split("@", 1)[0]
    tail = repository.rsplit("/", 1)[-1]
    tag = tail.split(":", 1)[1] if ":" in tail else None
    return (repository.rsplit(":", 1)[0] if tag else repository), tag


def containers(resource, obj):
    spec = obj.get("spec", {}) if resource == "pods" else obj.get("spec", {}).get("template", {}).get("spec", {})
    statuses = {s.get("name"): s for key in ("containerStatuses", "initContainerStatuses") for s in obj.get("status", {}).get(key, [])}
    result = []
    for key in ("containers", "initContainers"):
        for container in spec.get(key, []):
            image = container.get("image", "")
            repository, tag = image_parts(image)
            observed = statuses.get(container.get("name"), {})
            # Never include termination/waiting messages, environment, args, annotations or logs.
            state = {kind: {k: v for k, v in value.items() if k in ("reason", "exitCode", "signal", "startedAt", "finishedAt")}
                for kind, value in observed.get("state", {}).items() if kind in ("waiting", "running", "terminated")}
            result.append({"container": container.get("name"), "container_type": key, "image": image,
                "repository": repository, "declared_tag": tag, "imageID": observed.get("imageID"),
                "ready": observed.get("ready"), "restartCount": observed.get("restartCount"), "state": state})
    return result


def observed_status(obj):
    status = obj.get("status", {})
    return {k: status[k] for k in ("phase", "availableReplicas", "readyReplicas", "numberAvailable") if k in status} | {
        "conditions": [{k: c[k] for k in ("type", "status", "reason") if k in c} for c in status.get("conditions", [])]}


def inactive_reason(obj, item, now):
    phase = obj.get("status", {}).get("phase")
    if phase == "Succeeded":
        return "Completed", None
    if obj.get("metadata", {}).get("deletionTimestamp"):
        return "Terminating", None
    if phase == "Failed":
        return "Failed", None
    waiting = item.get("state", {}).get("waiting", {}).get("reason")
    if waiting in ("CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"):
        key = "ImagePullBackOff" if waiting == "ErrImagePull" else waiting
        return key, key
    if phase == "Running" and item.get("ready") is False:
        return "Running_proxy_not_Ready", "Running_proxy_not_Ready"
    if phase == "Pending":
        start = obj.get("status", {}).get("startTime") or obj.get("metadata", {}).get("creationTimestamp")
        try:
            age = (now - datetime.fromisoformat(start.replace("Z", "+00:00"))).total_seconds()
        except (TypeError, ValueError, AttributeError):
            age = None
        return "Pending", "Pending_prolonged" if age is not None and age >= 300 else None
    return "Pod_not_Ready" if phase == "Running" else "Unknown", None


def istio_summary(data, definition, now=None):
    now = now or datetime.now(timezone.utc)
    control, helm, versions = [], [], set()
    by_version, inactive, pods_seen = {}, set(), set()
    control_pods, gateway_pods = Counter(), Counter()
    inactive_categories, operational = {}, {}
    runtime_active = set()
    for resource in ("deployments.apps", "daemonsets.apps", "statefulsets.apps", "pods"):
        for index, obj in enumerate(data.get(resource, [])):
            meta = obj.get("metadata", {})
            for item in containers(resource, obj):
                if item["repository"] not in definition["images"]:
                    continue
                numeric = release(item["declared_tag"], "Istio")
                version = ".".join(map(str, numeric)) if numeric else item["declared_tag"] or "UNKNOWN"
                component = item["repository"].rsplit("/", 1)[-1]
                gateway = component == "proxyv2" and "gateway" in meta.get("name", "")
                if component == "pilot" or gateway:
                    versions.add(version)
                    if resource == "pods":
                        (gateway_pods if gateway else control_pods)[version] += 1
                    else:
                        control.append({"component": "istiod" if component == "pilot" else "gateway", "name": meta.get("name"),
                            "namespace": meta.get("namespace"), "version": version, "from": resource})
                elif resource == "pods" and component == "proxyv2":
                    key = (meta.get("namespace"), meta.get("uid") or meta.get("name") or index)
                    entry = by_version.setdefault(version, {"pods": set(), "active": set(), "inactive": set()})
                    entry["pods"].add(key)
                    pods_seen.add(key)
                    state = workload_activity(resource, obj)
                    if item.get("ready") is False and obj.get("status", {}).get("phase") == "Running":
                        state = "inactive"
                    entry[state].add(key)
                    if state == "inactive":
                        inactive.add(key)
                        category, warning = inactive_reason(obj, item, now)
                        inactive_categories[key] = category
                        if warning:
                            operational[key] = warning
                    elif obj.get("status", {}).get("phase") == "Running" and item.get("ready") is True:
                        runtime_active.add(key)
    for release_ in data.get("helm", []):
        if any(release_.get("chart", "").startswith(chart + "-") for chart in definition["charts"]):
            helm.append({k: release_.get(k) for k in ("name", "namespace", "chart", "app_version")})
    optional_errors = [e for e in data.get("discovery_errors", []) if e["source"] in OPTIONAL or e["source"] == "helm"]
    known_version = any(release(v, "Istio") for v in versions | set(by_version)) or any(release(h.get("app_version"), "Istio") for h in helm)
    return {"scope": "Inventario examinado; sujeto a límites y errores de las fuentes.", "control_plane": control,
        "control_plane_pods_by_version": dict(sorted(control_pods.items())), "gateway_pods_by_version": dict(sorted(gateway_pods.items())), "helm_releases": helm,
        "data_plane": {"pods_observed": len(pods_seen), "active_pods": len(pods_seen - inactive), "inactive_pods": len(inactive),
            "runtime_confirmed_active_pods": len(runtime_active), "inactive_reasons": dict(sorted(Counter(inactive_categories.values()).items())),
            "operational_warnings": dict(sorted(Counter(operational.values()).items())), "pending_warning_after_seconds": 300,
            "other_active_versions": len(set().union(*(v["active"] for k, v in by_version.items() if versions and k not in versions))),
            "by_version": [{"version": k, "pods": len(v["pods"]), "active": len(v["active"]), "inactive": len(v["inactive"])} for k, v in sorted(by_version.items())]},
        "inventory_errors": [{"source": e["source"], "reason": e["reason"]} for e in data.get("discovery_errors", []) if e not in optional_errors],
        "optional_sources_unavailable": [{"source": e["source"], "reason": e["reason"], "status": "OPTIONAL_SOURCE_UNAVAILABLE",
            "impact": "none_for_version_detection" if known_version else "version_detection_incomplete"} for e in optional_errors]}


def html_evidence(evidence):
    """Copy only for rendering: JSON evidence and compatibility inputs stay unchanged."""
    result = dict(evidence)
    if result.get("product") == "Istio":
        raw = result.pop("detection_sources", [])
        result["detection_summary"] = result.get("detection_summary") or {
            "scope": "Muestra histórica; regenerar para obtener contadores completos.",
            "observations_available": len(raw), "versions": result.get("raw_detected_versions", [])}
    lookup = result.get("catalog_lookup")
    if isinstance(lookup, dict) and lookup.get("reason") == "no_numeric_rows":
        result["catalog_lookup"] = lookup | {"reason": "Sin matriz numérica oficial verificable para la versión instalada y el objetivo; consultar el hallazgo y su fuente."}
    return result
