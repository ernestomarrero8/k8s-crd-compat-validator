"""Regressions for the incremental dev fixes; all inventories are synthetic."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

from validator.platform_analyzer import analyze
from validator.platform_catalog import PlatformCatalog
from validator.platform_discovery import collect
from validator.collector import CollectionError, read_json
from validator.readiness import score
from validator.product_link import product_finding
from validator.consolidated_report import consolidate
from validator.report_generator import write_reports

ROOT = Path(__file__).resolve().parents[1]


def inventory():
    return {"schema_version": 1, "kubernetes_version": "1.34.8", **{k: [] for k in
        ("deployments.apps", "daemonsets.apps", "statefulsets.apps", "pods", "nodes", "helm")}}


def workload(image, name="component", status=None):
    result = {"metadata": {"name": name, "namespace": "arbitrary-system"},
        "spec": {"template": {"spec": {"containers": [{"image": image}]}}}}
    if status is not None:
        result["status"] = status
    return result


def platform(data, crds=None):
    return analyze(None, crds or [], "1.34.8", "1.35.9", PlatformCatalog(), data)[0]


def diagnostic(data, id_, crds=None):
    return next(d for d in platform(data, crds)["detector_diagnostics"] if d["id"] == id_)


@pytest.mark.parametrize("id_,name,group", [
    ("gatekeeper", "constrainttemplates.templates.gatekeeper.sh", "templates.gatekeeper.sh"),
    ("tigera", "installations.operator.tigera.io", "operator.tigera.io"),
    ("secrets-store-csi", "secretproviderclasses.secrets-store.csi.x-k8s.io", "secrets-store.csi.x-k8s.io"),
    ("snapshot", "volumesnapshots.snapshot.storage.k8s.io", "snapshot.storage.k8s.io")])
def test_crds_are_artifacts_not_active(id_, name, group):
    data = platform(inventory(), [{"metadata": {"name": name}, "spec": {"group": group}}])
    row = next(p for p in data["products"] if p["id"] == id_)
    assert row["detection_status"] == "ARTIFACTS_ONLY"
    assert row["detected"] is True and row["active_controller_confirmed"] is False
    assert row["status"] == "UNKNOWN"
    assert "CONTROLLER_NOT_CONFIRMED" in {f["rule_id"] for f in row["findings"]}


@pytest.mark.parametrize("id_,image", [
    ("gatekeeper", "quay.io/open-policy-agent/gatekeeper:v3.18.0"),
    ("tigera", "tigera/operator:v1.38.0"),
    ("snapshot", "k8s.gcr.io/sig-storage/snapshot-controller:v8.2.0")])
def test_workloads_confirm_activity_and_version(id_, image):
    data = inventory()
    data["deployments.apps"] = [workload(image, status={"availableReplicas": 1})]
    row = next(p for p in platform(data)["products"] if p["id"] == id_)
    assert row["detection_status"] == "DETECTED_ACTIVE"
    assert row["active_controller_confirmed"] and row["versions"]


def test_gatekeeper_name_and_version_label_without_matching_image():
    data = inventory()
    obj = workload("private.example/controller@sha256:123", "gatekeeper-controller-manager")
    obj["metadata"]["labels"] = {"app.kubernetes.io/version": "v3.18.0"}
    data["deployments.apps"] = [obj]
    row = platform(data)["products"][0]
    assert row["id"] == "gatekeeper" and row["versions"] == ["3.18.0"]
    assert row["detection_status"] == "DETECTED_ACTIVE"


@pytest.mark.parametrize("resource,status", [
    ("deployments.apps", {"availableReplicas": 0}),
    ("daemonsets.apps", {"numberAvailable": 0}),
    ("pods", {"phase": "Failed"})])
def test_nonoperational_workload_is_inactive(resource, status):
    data = inventory()
    obj = workload("openpolicyagent/gatekeeper:v3.18.0", status=status)
    if resource == "pods":
        obj["spec"] = obj["spec"]["template"]["spec"]
    data[resource] = [obj]
    assert diagnostic(data, "gatekeeper")["detection_status"] == "DETECTED_INACTIVE"


def test_helm_missing_is_optional_but_rbac_source_is_not():
    data = inventory()
    data.pop("helm")
    row = diagnostic(data, "argocd")
    assert row["detection_status"] == "NOT_DETECTED"
    assert "Helm inventory unavailable" in row["limitations"]
    data.pop("deployments.apps")
    data["discovery_errors"] = [{"source": "deployments.apps", "reason": "forbidden"}]
    row = diagnostic(data, "argocd")
    assert row["detection_status"] == "INVENTORY_INCOMPLETE"
    assert any(e["source"] == "deployments.apps" for e in row["inventory_errors"])


def test_inventory_records_each_source(monkeypatch):
    class Live:
        context, timeout = "test", 1
        def get(self, resource, **kwargs):
            if resource == "deployments.apps":
                raise CollectionError("forbidden")
            return {"items": []}
    monkeypatch.setattr("validator.platform_discovery.command_json", lambda *a: (None, "binary_missing"))
    data = collect(Live(), [])
    sources = {s["source"]: s for s in data["inventory_sources"]}
    assert sources["pods"] == {"source": "pods", "completed": True, "authorized": True,
        "error": None, "items_scanned": 0, "required": True}
    assert not sources["deployments.apps"]["authorized"]
    assert sources["deployments.apps"]["error"] == "forbidden"
    assert not sources["Helm"]["required"]


def test_detector_parser_error_is_exposed_without_losing_other_products():
    data = inventory()
    data["istio"] = {"meshVersion": "invalid-parser-input"}
    assert diagnostic(data, "istio")["detection_status"] == "DETECTION_ERROR"


@pytest.mark.parametrize("repository", ["registry.k8s.io/csi-secrets-store/driver",
    "k8s.gcr.io/csi-secrets-store/driver", "mcr.microsoft.com/oss/kubernetes-csi/secrets-store/driver"])
def test_secrets_driver_and_azure_provider_are_separate(repository):
    data = inventory()
    data["daemonsets.apps"] = [workload(repository + ":v1.5.0"),
        workload("mcr.microsoft.com/oss/azure/secrets-store/provider-azure:v1.1.0")]
    rows = {r["id"]: r for r in platform(data)["products"]}
    assert rows["secrets-store-csi"]["versions"] == ["1.5.0"]
    assert rows["azure-keyvault"]["versions"] == ["1.1.0"]
    assert "Provider" in rows["azure-keyvault"]["product"]


def test_old_azure_provider_catalog_name_remains_usable(tmp_path):
    value = {"product": "Azure Key Vault CSI Driver", "versions": [{"version": "1.1.x",
        "supported_kubernetes": {"min": "1.30", "max": "1.36"}, "source": "https://example.com/synthetic",
        "reviewed_on": "2026-11-05", "evidence": "SYNTHETIC TEST ONLY"}]}
    file = tmp_path / "old-name.json"
    file.write_text(json.dumps(value), encoding="utf-8")
    result = PlatformCatalog(file).evaluate("Azure Key Vault Provider for Secrets Store CSI Driver", "1.1.0", "1.35.9", "https://example.com", date(2026, 11, 5))
    assert result[0].status == "PASS"


def test_snapshot_sidecar_is_not_the_controller_and_aks_managed_is_explicit():
    data = inventory()
    data["daemonsets.apps"] = [workload("registry.k8s.io/sig-storage/csi-snapshotter:v8.2.0")]
    rows = {r["id"]: r for r in platform(data)["products"]}
    assert "snapshot" not in rows and rows["csi-snapshotter"]["versions"] == ["8.2.0"]
    data["aks"] = {"kubernetesVersion": "1.34.8", "storageProfile": {"snapshotController": {"enabled": True}}}
    row = next(r for r in platform(data)["products"] if r["id"] == "snapshot")
    assert row["detection_status"] == "DETECTED_ACTIVE"
    assert row["detected_version"] == "MANAGED" and row["compatibility"] == "UNKNOWN"
    assert row["compatibility_legacy"] == "MANAGED_BY_AKS"
    assert row["reason"] == "MANAGED_VERSION_NOT_EXPOSED"
    assert row["status"] == "UNKNOWN"
    assert row["versions"] == ["MANAGED"]
    assert "VERSION_UNKNOWN" not in {f["rule_id"] for f in row["findings"]}


def report(states):
    return {"global_findings": [], "crds": [], "pluto": {"status": "PASS", "exit_code": 0},
        "platform": {"discovery": {"status": "PASS"}, "aks": {"detected": False},
            "products": [{"id": str(i), "category": "operator", "findings": [{"status": s}]} for i, s in enumerate(states)]}}


def test_score_excludes_unknown_and_counts_unweighted_evidence_units():
    result = score(report(["PASS", "UNKNOWN"]))
    assert result["score"] == 100
    assert result["evidence_coverage"] == pytest.approx(66.7)  # two products + Pluto
    assert result["decision"] == "INCOMPLETE"
    assert not result["confirmed_blockers"]


def test_readiness_config_and_error_decision(tmp_path):
    from validator.readiness import load_config
    config = tmp_path / "readiness.yaml"
    config.write_text("readiness:\n  minimum_evidence_coverage: 50\n  unknown_blocks_ready: true\n  warning_blocks_ready: true\n", encoding="utf-8")
    assert score(report(["PASS", "UNKNOWN"]), load_config(config))["decision"] == "ATTENTION_REQUIRED"
    assert score(report(["ERROR"]))["decision"] == "INCOMPLETE"
    assert score(report(["FAIL", "ERROR"]))["decision"] == "BLOCKED"


def test_product_support_is_explicitly_weightless_and_fifteen_crds_do_not_repeat_penalty():
    product = {"id": "istio", "product": "Istio", "status": "FAIL", "versions": ["1.24.1"],
        "findings": [{"rule_id": "NOT_COMPATIBLE", "source": "https://istio.io/", "evidence": {"target": "1.35.9"}}]}
    reference = product_finding(product).to_dict()
    assert reference["score_weight"] == 0 and reference["product_ref"] == "istio"
    assert reference["counted_in"] == "operators"
    base = report(["FAIL"])
    crd = {"findings": [reference, {"category": "schema", "status": "PASS"}]}
    base["crds"] = [crd]
    one = score(base)
    base["crds"] = [deepcopy(crd) for _ in range(15)]
    many = score(base)
    assert one["score"] == many["score"]
    assert many["categories"]["operators"]["observations"] == 1
    assert many["categories"]["crds"]["status"] == "PASS"


def example(context):
    data = deepcopy(read_json(ROOT / "reports/examples/reported-cases/report.json"))
    data["cluster"] = context
    data["cluster_identity"] = "/subscriptions/S/resourceGroups/R/providers/Microsoft.ContainerService/managedClusters/C"
    data["validator"] = {"status": "FAIL", "exit_code": 1}
    data["pluto"].update(status="PASS", exit_code=0, stdout="validación, versión, código, compatibilidad, redacción, información")
    return data


def entries(tmp_path, different=False):
    result = []
    for i, context in enumerate(["cluster", "unrelated-name-admin"]):
        value = example(context)
        if different and i:
            value["pluto"]["status"] = "WARN"
        directory = tmp_path / context
        directory.mkdir()
        file = directory / "report.json"
        file.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        result.append({"context": context, "exit_code": 1, "report_path": file})
    return result


def test_consolidated_deduplicates_identity_retains_contexts_and_utf8(tmp_path):
    output = tmp_path / "consolidated.html"
    consolidate(entries(tmp_path), output)
    text = output.read_text(encoding="utf-8")
    assert text.count('id="cluster-') == 1
    assert "Contextos asociados: 2" in text
    for word in ["validación", "versión", "código", "compatibilidad", "redacción", "información"]:
        assert word in text
    assert "Ã" not in text
    summary = read_json(output.with_suffix(".json"))
    assert len(summary["clusters"]) == 1
    assert summary["clusters"][0]["contexts"] == ["cluster", "unrelated-name-admin"]
    assert "Pluto exit" in text and "Validator exit" in text
    assert "Bloqueo principal" in text and "Productos UNKNOWN" in text
    cluster = summary["clusters"][0]
    assert cluster["pluto"]["exit_code"] == 0 and cluster["validator"]["exit_code"] == 1
    assert cluster["blocking_reasons"][0]["status"] == "FAIL"


def test_context_mismatch_is_not_silently_discarded(tmp_path):
    output = tmp_path / "all.html"
    consolidate(entries(tmp_path, True), output)
    text = output.read_text(encoding="utf-8")
    assert "CONTEXT_DATA_MISMATCH" in text
    assert "unrelated-name-admin" in text
    assert read_json(output.with_suffix(".json"))["clusters"][0]["data_mismatch"]
    assert any(r["rule_id"] == "CONTEXT_DATA_MISMATCH" for r in read_json(output.with_suffix(".json"))["clusters"][0]["blocking_reasons"])


def test_cluster_identity_precedence_and_safe_server_fallback():
    from validator.cluster_identity import identify
    data = {"aks": {"resource_id": "/subscriptions/S/resourceGroups/R/providers/Microsoft.ContainerService/managedClusters/C"},
        "kube_system_uid": "uid", "api_server": "https://HOST:443/"}
    identity = identify(data, "context")
    assert identity["source"] == "azure_resource_id" and identity["cluster_identity"].endswith("/c")
    data.pop("aks")
    assert identify(data, "ctx")["cluster_identity"] == "kube-system:uid"
    data.pop("kube_system_uid")
    assert identify(data, "ctx")["cluster_identity"] == "https://host"
    data["api_server"] = "https://user:PRIVATE@host/?token=PRIVATE"
    assert "PRIVATE" not in json.dumps(identify(data, "ctx"))


def test_istio_and_calico_unchanged_regression():
    data = inventory()
    data["deployments.apps"] = [workload("docker.io/istio/pilot:1.24.1")]
    data["pods"] = [{"spec": {"containers": [{"image": "docker.io/istio/proxyv2:1.24.1"}]}}]
    data["helm"] = [{"chart": "istiod-1.24.1", "app_version": "1.24.1"}]
    data["clusterinformations.crd.projectcalico.org"] = [{"spec": {"calicoVersion": "v3.31.2"}}]
    rows = {r["id"]: r for r in platform(data)["products"]}
    assert rows["istio"]["status"] == "FAIL"
    assert {f["rule_id"] for f in rows["istio"]["findings"]} == {"VERSION_EOL", "NOT_COMPATIBLE"}
    assert rows["istio"]["findings"][0]["evidence"]["catalog_lookup"]["selected_selector"] == "1.24.x"
    assert rows["calico"]["normalized_versions"] == ["3.31.2"]
    assert rows["calico"]["findings"][0]["rule_id"] == "COMPATIBLE"
    assert rows["calico"]["findings"][0]["evidence"]["catalog_lookup"]["selected_selector"] == "3.31.x"
    assert rows["calico"]["status"] == "PASS"


def test_gatekeeper_workload_without_version_and_helm_priority():
    data = inventory()
    data["deployments.apps"] = [workload("private.example/controller:latest", "gatekeeper-audit")]
    row = platform(data)["products"][0]
    assert row["detection_status"] == "DETECTED_ACTIVE"
    assert row["findings"][0]["rule_id"] == "VERSION_UNKNOWN"
    data["deployments.apps"] = [workload("openpolicyagent/gatekeeper:v3.17.0", "gatekeeper-audit")]
    data["helm"] = [{"chart": "gatekeeper-3.18.0", "app_version": "3.18.0", "status": "deployed"}]
    row = platform(data)["products"][0]
    assert row["resolved_versions"] == ["3.18.0"]
    assert row["versions"] == ["3.17.0", "3.18.0"]  # no hidden rollout versions


def test_gatekeeper_manager_precedes_audit_and_pods_without_hiding_versions():
    data = inventory()
    data["deployments.apps"] = [workload("openpolicyagent/gatekeeper:v3.18.0", "gatekeeper-controller-manager"),
        workload("openpolicyagent/gatekeeper:v3.17.0", "gatekeeper-audit")]
    data["pods"] = [{"spec": {"containers": [{"image": "openpolicyagent/gatekeeper:v3.16.0"}]}}]
    row = platform(data)["products"][0]
    assert row["resolved_versions"] == ["3.18.0"]
    assert row["versions"] == ["3.16.0", "3.17.0", "3.18.0"]


def test_webhook_and_api_artifacts_require_confirmed_backend():
    data = inventory()
    data["validatingwebhookconfigurations.admissionregistration.k8s.io"] = [{
        "metadata": {"name": "gatekeeper-validating-webhook-configuration"},
        "webhooks": [{"clientConfig": {"service": {"namespace": "policy", "name": "gatekeeper-webhook"}}}]}]
    assert diagnostic(data, "gatekeeper")["detection_status"] == "ARTIFACTS_ONLY"
    data["services"] = [{"metadata": {"namespace": "policy", "name": "gatekeeper-webhook"}}]
    assert diagnostic(data, "gatekeeper")["detection_status"] == "DETECTED_INACTIVE"
    data["endpointslices.discovery.k8s.io"] = [{"metadata": {"namespace": "policy", "labels": {"kubernetes.io/service-name": "gatekeeper-webhook"}},
        "endpoints": [{"addresses": ["10.0.0.1"], "conditions": {"ready": True}}]}]
    assert diagnostic(data, "gatekeeper")["detection_status"] == "DETECTED_ACTIVE"
    assert platform(data)["products"][0]["status"] == "UNKNOWN"  # backend health cannot prove support
    data = inventory()
    data["apiservices.apiregistration.k8s.io"] = [{"spec": {"group": "templates.gatekeeper.sh"}}]
    assert diagnostic(data, "gatekeeper")["detection_status"] == "ARTIFACTS_ONLY"


def test_internal_istio_parser_error_retains_valid_workload_and_calico():
    data = inventory()
    data["istio"] = {"meshVersion": "invalid"}
    data["deployments.apps"] = [workload("docker.io/istio/pilot:1.24.1")]
    data["clusterinformations.crd.projectcalico.org"] = [{"spec": {"calicoVersion": "v3.31.2"}}]
    result = platform(data)
    rows = {r["id"]: r for r in result["products"]}
    assert rows["istio"]["status"] == "FAIL" and rows["istio"]["detection_status"] == "DETECTION_ERROR"
    assert rows["calico"]["status"] == "PASS"


def test_required_error_keeps_observed_activity_separate():
    data = inventory()
    data["deployments.apps"] = [workload("openpolicyagent/gatekeeper:v3.18.0")]
    data["discovery_errors"] = [{"source": "pods", "reason": "forbidden"}]
    row = platform(data)["products"][0]
    assert row["detection_status"] == "INVENTORY_INCOMPLETE"
    assert row["presence_status"] == "DETECTED_ACTIVE" and row["active_controller_confirmed"]


def test_rule_catalog_is_utf8_at_source_and_json_is_not_ascii_escaped(tmp_path):
    rules = read_json(ROOT / "rules/kubernetes.json")
    assert "validación CEL" in rules["rules"][0]["description"]
    assert "redacción" in rules["rules"][0]["recommendation"]
    value = example("test")
    write_reports(value, tmp_path)
    for path in tmp_path.iterdir():
        text = path.read_text(encoding="utf-8")
        assert "validación" in text and "Ã" not in text and "\ufffd" not in text
        assert b"\r\n" not in path.read_bytes()


def test_batch_child_utf8_and_independent_exits(tmp_path, monkeypatch):
    import batch
    def run(command, **kwargs):
        assert kwargs["encoding"] == "utf-8" and kwargs["errors"] == "replace"
        assert kwargs["env"]["PYTHONIOENCODING"] == "utf-8"
        assert kwargs["env"]["PYTHONUTF8"] == "1"
        directory = Path(command[command.index("--output") + 1])
        value = example("test")
        (directory / "report.json").write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return SimpleNamespace(returncode=1, stdout="validación versión código compatibilidad redacción información\n")
    monkeypatch.setattr(batch.subprocess, "run", run)
    assert batch.main(["--context", "test", "--target", "1.35.9", "--output", str(tmp_path)]) == 1
    directory = next(tmp_path.iterdir())
    log = next(directory.glob("*/console.txt")).read_text(encoding="utf-8")
    assert "validación versión código" in log
    row = read_json(directory / "consolidated.json")["clusters"][0]
    assert row["pluto"]["exit_code"] == 0 and row["validator"]["exit_code"] == 1


def test_live_cli_persists_pluto_and_validator_exit_independently(tmp_path, monkeypatch):
    from validator.cli import main
    import subprocess
    def run(command, **kwargs):
        if command[0] == "pluto":
            return SimpleNamespace(returncode=0, stdout="No output to display", stderr="")
        if command[0] == "helm":
            value = []
        elif "version" in command:
            value = {"serverVersion": {"gitVersion": "v1.34.8"}}
        elif "crds" in command:
            value = read_json(ROOT / "fixtures/valid-crds.json")
        elif "namespaces" in command:
            value = {"metadata": {"uid": "cluster-uid"}}
        elif "deployments.apps" in command:
            value = {"items": [workload("docker.io/istio/pilot:1.24.1")]}
        else:
            value = {"items": []}
        return SimpleNamespace(returncode=0, stdout=json.dumps(value, ensure_ascii=False), stderr="")
    monkeypatch.setattr(subprocess, "run", run)
    assert main(["--context", "test", "--target-version", "1.35.9", "--output", str(tmp_path)]) == 1
    result = read_json(tmp_path / "report.json")
    assert result["pluto"]["exit_code"] == 0
    assert result["validator"]["exit_code"] == 1 and result["validator"]["status"] == "FAIL"
    assert result["cluster_identity"] == "kube-system:cluster-uid"


@pytest.mark.parametrize("identity1,identity2,expected", [
    ("kube-system:shared", "kube-system:shared", 1),
    ("https://API.example:443/", "https://api.example", 1),
    ("kube-system:one", "kube-system:two", 2),
    (None, None, 2)])
def test_cluster_fallback_identity_never_deduplicates_by_name(tmp_path, identity1, identity2, expected):
    values = entries(tmp_path)
    for entry, identity in zip(values, [identity1, identity2]):
        value = read_json(entry["report_path"])
        value["cluster_identity"] = identity or ""
        entry["report_path"].write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    output = tmp_path / "all.html"
    consolidate(values, output)
    assert len(read_json(output.with_suffix(".json"))["clusters"]) == expected


@pytest.mark.parametrize("config", ["{}", '{"readiness": null}', '{"readiness": {"minimum_evidence_coverage": 101}}',
    "readiness:\n  unknown_blocks_ready: arbitrary()\n", "readiness:\n  wrong_field: true\n"])
def test_invalid_readiness_config_is_rejected(tmp_path, config):
    from validator.readiness import load_config
    file = tmp_path / "config.yaml"
    file.write_text(config, encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(file)
