"""Bounded read-only inventory. Export only allowlisted identity/version fields."""
import json
import re
import subprocess
from .collector import CollectionError, read_json
from .platform_catalog import release, ROOT


def command_json(command, timeout):
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                check=False, shell=False, timeout=timeout)
        if result.returncode:
            return None, "command_failed"
        return json.loads(result.stdout), None
    except FileNotFoundError:
        return None, "binary_missing"
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except (OSError, ValueError):
        return None, "invalid_response"


def collect(collector, crds, limit=2000, definitions=None):
    data, errors = {"crds": crds}, []
    for resource in ("deployments.apps", "daemonsets.apps", "statefulsets.apps", "pods", "nodes"):
        try:
            response = collector.get(resource, all_namespaces=resource != "nodes")
            items = response.get("items", [])
            if not isinstance(items, list):
                raise CollectionError("invalid_response")
            data[resource] = items[:limit]
            if len(items) >= limit:
                errors.append({"source": resource, "reason": "inventory_limit"})
        except CollectionError as exc:
            errors.append({"source": resource, "reason": exc.code})
    helm, error = command_json(["helm", "list", "-A", "-o", "json", "--kube-context", collector.context, "--max", str(limit)], collector.timeout)
    if error or not isinstance(helm, list):
        errors.append({"source": "Helm", "reason": error or "invalid_response"})
    else:
        data["helm"] = helm[:limit]
        if len(helm) >= limit:
            errors.append({"source": "Helm", "reason": "inventory_limit"})
    names = {c.get("metadata", {}).get("name") for c in crds}
    # Only query custom APIs known to exist; no invented meshconfig or gatekeeper resource names.
    for crd in ("clusterinformations.crd.projectcalico.org", "tigerastatuses.operator.tigera.io", "installations.operator.tigera.io", "configurations.dapr.io"):
        if crd in names:
            try:
                data[crd] = collector.get(crd, all_namespaces=crd == "configurations.dapr.io").get("items", [])[:limit]
            except CollectionError as exc:
                errors.append({"source": crd, "reason": exc.code})
    definitions = definitions or read_json(ROOT / "detectors.json")["products"]
    if any(row["id"] == "istio" for row in detect(data, definitions)):
        data["istio"], error = command_json(["istioctl", "version", "--context", collector.context, "-o", "json"], collector.timeout)
        if not error and (not isinstance(data["istio"], dict) or not any(data["istio"].get(k) for k in ("meshVersion", "dataPlaneVersion"))):
            error = "remote_versions_unavailable"
        if error:
            errors.append({"source": "istioctl version", "reason": error})
    data["discovery_errors"] = errors
    return data


def detect(data, definitions):
    detected = {}
    def add(definition, namespace, version, evidence):
        key = (definition["id"], namespace)
        row = detected.setdefault(key, {"id": definition["id"], "product": definition["product"], "namespace": namespace,
            "category": definition.get("category", "operator"), "source": definition["source"], "versions": [], "evidence": [], "version_candidates": [], "unknown_version": False})
        version = str(version) if version is not None else "UNKNOWN"
        if not release(version) or (definition.get("component_versions") and evidence["from"] != "Helm"):
            if evidence["from"] not in ("Helm", "CRD") or not row["versions"]:
                row["unknown_version"] = True
            version = "UNKNOWN"
        elif row["evidence"] and all(e["from"] in ("CRD", "Helm") for e in row["evidence"]):
            row["unknown_version"] = False
        if version != "UNKNOWN" and version not in row["versions"]:
            row["versions"].append(version)
        if version != "UNKNOWN":
            candidate = {"version": version, "from": evidence["from"], "namespace": namespace, "revision": evidence.get("revision")}
            if candidate not in row["version_candidates"]:
                row["version_candidates"].append(candidate)
        # Bound report size independently from inventory size.
        if len(row["evidence"]) < 30 and evidence not in row["evidence"]:
            row["evidence"].append(evidence)
    for resource in ("deployments.apps", "daemonsets.apps", "statefulsets.apps", "pods"):
        for obj in data.get(resource, []):
            meta = obj.get("metadata", {})
            spec = obj.get("spec", {}) if resource == "pods" else obj.get("spec", {}).get("template", {}).get("spec", {})
            for container in spec.get("containers", []) + spec.get("initContainers", []):
                image = container.get("image", "")
                repository = image.split("@")[0]
                tail = repository.rsplit("/", 1)[-1]
                tag = tail.split(":", 1)[1] if ":" in tail else None
                repository = repository.rsplit(":", 1)[0] if tag else repository
                for definition in definitions:
                    if repository in definition["images"]:
                        evidence = {"from": resource, "namespace": meta.get("namespace", ""), "name": meta.get("name", ""),
                                    "repository": repository, "declared_tag": tag, "revision": meta.get("labels", {}).get("istio.io/rev"),
                                    "version_basis": "pod_image_tag" if resource == "pods" else "workload_template_image_tag"}
                        add(definition, meta.get("namespace", ""), tag, evidence)
    for helm in data.get("helm", []):
        for definition in definitions:
            # Exact chart identity followed by a chart version; never use chart version as app version.
            if any(re.fullmatch(re.escape(chart) + r"-\d[^/]*", helm.get("chart", "")) for chart in definition["charts"]):
                add(definition, helm.get("namespace", ""), helm.get("app_version") if definition.get("helm_version_is_product", True) else None,
                    {"from": "Helm", "name": helm.get("name"), "chart": helm.get("chart"), "app_version": helm.get("app_version")})
    for definition in definitions:
        if any(c.get("metadata", {}).get("name") in definition["crds"] or
               (isinstance(c.get("spec"), dict) and c["spec"].get("group") in definition.get("crd_groups", []))
               for c in data.get("crds", [])) and not any(k[0] == definition["id"] for k in detected):
            add(definition, "", None, {"from": "CRD", "note": "Presencia del CRD; no prueba que un controlador esté activo."})
    # Calico's clusterinformation has an explicit product version. Installation configuration does not.
    for obj in data.get("clusterinformations.crd.projectcalico.org", []):
        definition = next(d for d in definitions if d["id"] == "calico")
        add(definition, "", obj.get("spec", {}).get("calicoVersion"), {"from": "Calico ClusterInformation"})
    for resource, product_id in (("tigerastatuses.operator.tigera.io", "tigera"), ("installations.operator.tigera.io", "tigera"), ("configurations.dapr.io", "dapr")):
        if data.get(resource) and not any(k[0] == product_id for k in detected):
            definition = next(d for d in definitions if d["id"] == product_id)
            add(definition, "", None, {"from": resource, "note": "Configuración observada; no contiene una versión de binario verificable."})
    istio = data.get("istio") or {}
    definition = next(d for d in definitions if d["id"] == "istio")
    for obj in istio.get("meshVersion", []):
        add(definition, "istioctl", obj.get("Info", obj.get("info", {})).get("version"), {"from": "istioctl control plane", "component": obj.get("Component"), "revision": obj.get("Revision")})
    for obj in istio.get("dataPlaneVersion", []):
        add(definition, "istioctl", obj.get("IstioVersion"), {"from": "istioctl data plane", "count": obj.get("NumProxies")})
    return list(detected.values())
