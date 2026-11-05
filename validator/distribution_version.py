"""Repository-scoped packaging revisions; never coerce arbitrary SemVer prereleases."""
import re

REPOSITORIES = {
    "gatekeeper": {"mcr.microsoft.com/oss/open-policy-agent/gatekeeper", "mcr.microsoft.com/oss/v2/open-policy-agent/gatekeeper"},
    "tigera": {"mcr.microsoft.com/oss/tigera/operator", "mcr.microsoft.com/oss/v2/tigera/operator"},
}


def normalize(product_id, version, repository):
    if repository not in REPOSITORIES.get(product_id, set()):
        return None
    match = re.fullmatch(r"v?(\d+\.\d+\.\d+)-(\d+)", str(version))
    if not match:
        return None
    return {"raw_version": version, "upstream_version": match[1], "distribution_revision": match[2],
        "repository": repository, "normalization_rule": "microsoft_packaging_revision"}
