"""Inventory coverage and controller presence, independent of support matrices."""
REQUIRED = ("deployments.apps", "daemonsets.apps", "statefulsets.apps", "pods", "nodes")
OPTIONAL = ("Helm", "istioctl version", "apiservices.apiregistration.k8s.io",
    "validatingwebhookconfigurations.admissionregistration.k8s.io",
    "mutatingwebhookconfigurations.admissionregistration.k8s.io", "services", "endpointslices.discovery.k8s.io")


def inventory_sources(data):
    errors = {e["source"]: e["reason"] for e in data.get("discovery_errors", [])}
    names = list(dict.fromkeys([*REQUIRED, "Helm", *errors,
        *(k for k in OPTIONAL if k in data)]))
    result = []
    for name in names:
        key = "helm" if name == "Helm" else name
        values = data.get(key)
        error = errors.get(name) or errors.get(key)
        if name in REQUIRED or name == "Helm":
            if not isinstance(values, list) or any(not isinstance(v, dict) for v in values):
                error = error or ("not_in_snapshot" if key not in data else "invalid_response")
        result.append({"source": name, "completed": not bool(error), "authorized": False if error in ("forbidden", "unauthorized") else None if error else True,
            "error": error, "items_scanned": len(values) if isinstance(values, list) else 0,
            "required": name in REQUIRED or name == "offline"})
    return result


def workload_activity(resource, obj):
    status = obj.get("status") or {}
    if resource == "pods":
        if status.get("phase") in ("Failed", "Pending", "Succeeded", "Unknown") or obj.get("metadata", {}).get("deletionTimestamp"):
            return "inactive"
        if any(c.get("type") == "Ready" and c.get("status") == "False" for c in status.get("conditions", [])):
            return "inactive"
        if any(s.get("state", {}).get("waiting", {}).get("reason") in ("CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull") for s in status.get("containerStatuses", [])):
            return "inactive"
    elif resource == "daemonsets.apps":
        if status.get("numberAvailable") == 0 or status.get("numberReady") == 0 or status.get("desiredNumberScheduled") == 0:
            return "inactive"
    elif status.get("availableReplicas") == 0 or status.get("readyReplicas") == 0 or status.get("replicas") == 0 or obj.get("spec", {}).get("replicas") == 0:
        return "inactive"
    # Workload existence is presence evidence; missing status is not fabricated health.
    return "active"


def presence(row):
    activities = {e.get("activity", "artifact") for e in row.get("evidence", [])}
    active = "active" in activities
    return {"detected": True, "legacy_status": "DETECTED",
        "detection_status": "DETECTED_ACTIVE" if active else "DETECTED_INACTIVE" if "inactive" in activities else "ARTIFACTS_ONLY",
        "active_controller_confirmed": active}
