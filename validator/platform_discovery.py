"""Bounded read-only inventory. Export only allowlisted identity/version fields."""
import json
import re
import subprocess
from .collector import CollectionError, read_json
from .platform_catalog import release, ROOT
from .detection_status import REQUIRED, OPTIONAL, inventory_sources, workload_activity
from .workload_evidence import containers as container_evidence, observed_status

WORKLOAD_NAMES = {"gatekeeper": {"gatekeeper-controller-manager", "gatekeeper-audit"},
    "tigera": {"tigera-operator"}, "snapshot": {"snapshot-controller", "csi-snapshot-controller"}}
WEBHOOK_NAMES = {"gatekeeper": {"gatekeeper-validating-webhook-configuration", "gatekeeper-mutating-webhook-configuration"}}


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
    for resource in REQUIRED:
        try:
            response = collector.get(resource, all_namespaces=resource != "nodes")
            items = response.get("items", [])
            if not isinstance(items, list) or any(not isinstance(i, dict) for i in items):
                raise CollectionError("invalid_response")
            data[resource] = items[:limit]
            if len(items) > limit or response.get("metadata", {}).get("continue"):
                errors.append({"source": resource, "reason": "inventory_limit"})
        except CollectionError as exc:
            errors.append({"source": resource, "reason": exc.code})
    helm, error = command_json(["helm", "list", "-A", "-o", "json", "--kube-context", collector.context, "--max", str(limit)], collector.timeout)
    if error or not isinstance(helm, list) or any(not isinstance(item, dict) for item in helm):
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
    for resource in OPTIONAL[2:]:
        try:
            response = collector.get(resource, all_namespaces=resource in ("services", "endpointslices.discovery.k8s.io"))
            items = response.get("items", [])
            if not isinstance(items, list) or any(not isinstance(i, dict) for i in items):
                raise CollectionError("invalid_response")
            data[resource] = items[:limit]
            if len(items) > limit or response.get("metadata", {}).get("continue"):
                errors.append({"source": resource, "reason": "inventory_limit"})
        except CollectionError as exc:
            errors.append({"source": resource, "reason": exc.code})
    if any(row["id"] == "istio" for row in safe_detect(data, definitions)[0]):
        data["istio"], error = command_json(["istioctl", "version", "--context", collector.context, "-o", "json"], collector.timeout)
        if not error and (not isinstance(data["istio"], dict) or not any(data["istio"].get(k) for k in ("meshVersion", "dataPlaneVersion"))):
            error = "remote_versions_unavailable"
        if error:
            errors.append({"source": "istioctl version", "reason": error})
    data["discovery_errors"] = errors
    data["inventory_sources"] = inventory_sources(data)
    return data


def safe_detect(data, definitions, full_evidence=False):
    rows, errors = [], []
    for definition in definitions:
        try:
            rows.extend(detect(data, [definition], full_evidence=full_evidence))
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
            errors.append({"product_id": definition["id"], "reason": "detector_parser_error"})
            if definition["id"] == "istio" and "istio" in data:
                try:
                    rows.extend(detect({k: v for k, v in data.items() if k != "istio"}, [definition], full_evidence=full_evidence))
                except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
                    pass
    return rows, errors


def detect(data, definitions, full_evidence=False):
    detected = {}
    def add(definition, namespace, version, evidence):
        key = (definition["id"], namespace)
        row = detected.setdefault(key, {"id": definition["id"], "product": definition["product"], "namespace": namespace,
            "category": definition.get("category", "operator"), "source": definition["source"], "versions": [], "detected_versions": [], "evidence": [], "version_candidates": [], "unknown_version": False})
        version = str(version) if version is not None else "UNKNOWN"
        component_version = definition.get("component_versions") and evidence["from"] != "Helm"
        if component_version:
            evidence["version_scope"] = "component_not_product_release"
        if version != "UNKNOWN" and not component_version and version not in row["detected_versions"]:
            row["detected_versions"].append(version)
        if not release(version, definition["product"]) or component_version:
            if evidence["from"] not in ("Helm", "CRD") or not row["versions"]:
                row["unknown_version"] = True
            version = "UNKNOWN"
        elif row["evidence"] and all(e["from"] in ("CRD", "Helm") for e in row["evidence"]):
            row["unknown_version"] = False
        if version != "UNKNOWN" and version not in row["versions"]:
            row["versions"].append(version)
        if version != "UNKNOWN":
            candidate = {"version": version, "from": evidence["from"], "namespace": namespace, "revision": evidence.get("revision"),
                "name": evidence.get("name"), "version_basis": evidence.get("version_basis"), "confidence": evidence.get("confidence")}
            if candidate not in row["version_candidates"]:
                row["version_candidates"].append(candidate)
        # Bound report size independently from inventory size.
        if (full_evidence or len(row["evidence"]) < 30) and evidence not in row["evidence"]:
            row["evidence"].append(evidence)
    for resource in ("deployments.apps", "daemonsets.apps", "statefulsets.apps", "pods"):
        for obj in data.get(resource, []):
            meta = obj.get("metadata", {})
            observed = container_evidence(resource, obj)
            labels = meta.get("labels", {}) | obj.get("spec", {}).get("template", {}).get("metadata", {}).get("labels", {})
            matched = set()
            for observation in observed:
                repository, tag = observation["repository"], observation["declared_tag"]
                for definition in definitions:
                    if repository in definition["images"]:
                        matched.add(definition["id"])
                        label_version = labels.get("app.kubernetes.io/version")
                        version = tag if release(tag, definition["product"]) else label_version or tag
                        evidence = {"from": resource, "namespace": meta.get("namespace", ""), "name": meta.get("name", ""),
                                    "repository": repository, "declared_tag": tag, "revision": meta.get("labels", {}).get("istio.io/rev"),
                                    "identity_basis": "configured_repository" if repository in definition.get("configured_images", []) else "catalog_repository",
                                    "confidence": "product_metadata" if version != tag else "image_tag",
                                    "activity": workload_activity(resource, obj), "observed_status": observed_status(obj),
                                    "version_label": label_version, "chart": labels.get("helm.sh/chart"), "imageID": observation["imageID"],
                                    "observed_containers": [observation],
                                    "pod_container_statuses": [{k: item[k] for k in ("container", "ready", "restartCount", "state")} for item in observed] if resource == "pods" else [],
                                    "version_basis": "version_label" if version != tag else "pod_image_tag" if resource == "pods" else "workload_template_image_tag"}
                        add(definition, meta.get("namespace", ""), version, evidence)
            for definition in definitions:
                if definition["id"] not in matched and meta.get("name") in WORKLOAD_NAMES.get(definition["id"], set()):
                    annotations = meta.get("annotations", {})
                    label_version = labels.get("app.kubernetes.io/version") or annotations.get("app.kubernetes.io/version")
                    # A named workload plus the exact controller image basename establishes a declared identity.
                    # Never take a helper/init image's unrelated SemVer or a Helm chart version as the product version.
                    basenames = {image.rsplit("/", 1)[-1] for image in definition["images"]}
                    selected = [o for o in observed if o["repository"].rsplit("/", 1)[-1] in basenames
                        and (definition["id"] != "tigera" or o["container"] in ("tigera-operator", "operator"))]
                    for observation in selected or [None]:
                        tag = observation["declared_tag"] if observation else None
                        version = tag if release(tag, definition["product"]) else label_version or tag
                        add(definition, meta.get("namespace", ""), version, {"from": resource, "name": meta.get("name"),
                            "identity_basis": "known_workload_and_controller_image" if observation else "known_workload_name",
                            "activity": workload_activity(resource, obj), "observed_status": observed_status(obj),
                            "repository": observation["repository"] if observation else None, "declared_tag": tag,
                            "imageID": observation["imageID"] if observation else None, "chart": labels.get("helm.sh/chart"),
                            "version_label": label_version, "version_basis": "workload_template_image_tag" if version == tag and tag else "version_label",
                            "confidence": "image_tag" if version == tag and tag else "product_metadata", "observed_containers": observed,
                            "note": "Identidad declarada del workload y su contenedor; no se verifica el binario por digest. Los tags de helpers y chart no determinan versión del producto."})
    for helm in data.get("helm", []):
        for definition in definitions:
            # Exact chart identity followed by a chart version; never use chart version as app version.
            if any(re.fullmatch(re.escape(chart) + r"-\d[^/]*", helm.get("chart", "")) for chart in definition["charts"]):
                add(definition, helm.get("namespace", ""), helm.get("app_version") if definition.get("helm_version_is_product", True) else None,
                    {"from": "Helm", "name": helm.get("name"), "chart": helm.get("chart"), "app_version": helm.get("app_version"),
                     "activity": "inactive" if helm.get("status") in ("failed", "uninstalled", "uninstalling", "pending-install", "pending-upgrade", "pending-rollback") else "active",
                     "release_status": helm.get("status")})
    for definition in definitions:
        if any(c.get("metadata", {}).get("name") in definition["crds"] or
               (isinstance(c.get("spec"), dict) and c["spec"].get("group") in definition.get("crd_groups", []))
               for c in data.get("crds", [])) and not any(k[0] == definition["id"] for k in detected):
            add(definition, "", None, {"from": "CRD", "note": "Presencia del CRD; no prueba que un controlador esté activo."})
    # Calico's clusterinformation has an explicit product version. Installation configuration does not.
    for obj in data.get("clusterinformations.crd.projectcalico.org", []):
        definition = next((d for d in definitions if d["id"] == "calico"), None)
        if definition:
            add(definition, "", obj.get("spec", {}).get("calicoVersion"), {"from": "Calico ClusterInformation", "activity": "active"})
    for resource, product_id in (("tigerastatuses.operator.tigera.io", "tigera"), ("installations.operator.tigera.io", "tigera"), ("configurations.dapr.io", "dapr")):
        if data.get(resource) and not any(k[0] == product_id for k in detected):
            definition = next((d for d in definitions if d["id"] == product_id), None)
            if definition:
                add(definition, "", None, {"from": resource, "note": "Configuración observada; no contiene una versión de binario verificable."})
    for definition in definitions:
        for api in data.get("apiservices.apiregistration.k8s.io", []):
            if api.get("spec", {}).get("group") in definition.get("crd_groups", []):
                add(definition, "", None, {"from": "APIService", "name": api.get("metadata", {}).get("name"), "activity": "artifact"})
        for kind in ("validatingwebhookconfigurations.admissionregistration.k8s.io", "mutatingwebhookconfigurations.admissionregistration.k8s.io"):
            for obj in data.get(kind, []):
                if obj.get("metadata", {}).get("name") not in WEBHOOK_NAMES.get(definition["id"], set()):
                    continue
                for webhook in obj.get("webhooks", []):
                    service = webhook.get("clientConfig", {}).get("service", {})
                    namespace, name = service.get("namespace"), service.get("name")
                    exists = any(s.get("metadata", {}).get("namespace") == namespace and s.get("metadata", {}).get("name") == name for s in data.get("services", []))
                    endpoints = any(s.get("metadata", {}).get("namespace") == namespace and s.get("metadata", {}).get("labels", {}).get("kubernetes.io/service-name") == name and
                        any(e.get("addresses") and e.get("conditions", {}).get("ready") is True for e in s.get("endpoints", [])) for s in data.get("endpointslices.discovery.k8s.io", []))
                    add(definition, namespace or "", None, {"from": kind, "name": obj.get("metadata", {}).get("name"),
                        "service": name, "namespace": namespace, "endpoints_confirmed": exists and endpoints,
                        "activity": "active" if exists and endpoints else "inactive" if exists else "artifact"})
    istio = data.get("istio") or {}
    definition = next((d for d in definitions if d["id"] == "istio"), None)
    if definition:
        for obj in istio.get("meshVersion", []):
            add(definition, "istioctl", obj.get("Info", obj.get("info", {})).get("version"), {"from": "istioctl control plane", "component": obj.get("Component"), "revision": obj.get("Revision"), "activity": "active"})
        for obj in istio.get("dataPlaneVersion", []):
            add(definition, "istioctl", obj.get("IstioVersion"), {"from": "istioctl data plane", "count": obj.get("NumProxies"), "activity": "active"})
    return list(detected.values())
