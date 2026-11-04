"""Deterministic source precedence; client tools are never installed server versions."""
from .platform_catalog import release

PRIORITY = {"istioctl control plane": 0, "istioctl data plane": 0, "Helm": 1,
            "pods": 2, "deployments.apps": 2, "daemonsets.apps": 2, "statefulsets.apps": 2,
            "Calico ClusterInformation": 3}


def resolve(rows):
    registry = {}
    for row in rows:
        product = registry.setdefault(row["id"], row | {"namespaces": [], "evidence": [], "version_candidates": [], "versions": [], "detected_versions": []})
        if row["namespace"] not in product["namespaces"]:
            product["namespaces"].append(row["namespace"])
        product["evidence"].extend(row["evidence"])
        product["version_candidates"].extend(row.get("version_candidates", []))
        product["detected_versions"] = sorted(set(product["detected_versions"]) | set(row.get("detected_versions", [])))
    for row in registry.values():
        candidates = [c for c in row["version_candidates"] if release(c["version"], row["product"])]
        rank = min((PRIORITY.get(c["from"], 99) for c in candidates), default=99)
        canonical = lambda c: c["version"] if release(c["version"]) is None else ".".join(map(str, release(c["version"])))
        row["resolved_versions"] = sorted({canonical(c) for c in candidates if PRIORITY.get(c["from"], 99) == rank})
        # Keep known older versions: precedence must not conceal an incompatible data plane or rollout.
        row["versions"] = sorted({canonical(c) for c in candidates})
        row["resolution_sources"] = sorted({c["from"] for c in candidates if PRIORITY.get(c["from"], 99) == rank})
        row["unknown_version"] = not bool(candidates)
        row["version_conflict"] = len(set(row["versions"])) > 1
        row["normalized_versions"] = sorted({".".join(map(str, release(c["version"], row["product"]))) for c in candidates})
        row["namespace"] = ", ".join(n for n in row["namespaces"] if n) or "cluster"
        row["resolution_policy"] = "cluster-bound server CLI > Helm appVersion > exact image tags > explicit product resource; all known mixed versions evaluated"
    return list(registry.values())
