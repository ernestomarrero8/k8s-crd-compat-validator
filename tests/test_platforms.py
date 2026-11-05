from copy import deepcopy
from datetime import date
import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
import pytest
from validator.platform_catalog import PlatformCatalog, bound, release
from validator.platform_discovery import detect, collect, command_json
from validator.platform_analyzer import analyze
from validator.azure_validator import analyze as azure_analyze, collect_aks
from validator.readiness import score
from validator.version import Version
from validator.collector import CollectionError, read_json
from validator.cli import main
from validator.report_generator import html

ROOT = Path(__file__).resolve().parents[1]
TODAY = date(2026, 11, 4)


@pytest.fixture
def catalog():
    return PlatformCatalog()


@pytest.mark.parametrize("product_id", [d["id"] for d in PlatformCatalog().detectors])
def test_every_product_has_an_image_detector(catalog, product_id):
    definition = next(d for d in catalog.detectors if d["id"] == product_id)
    data = {"daemonsets.apps": [{"metadata": {"name": "component", "namespace": "system"}, "spec": {"template": {"spec": {
        "containers": [{"image": definition["images"][0] + ":v1.2.3", "env": [{"value": "PRIVATE"}]}]}}}}]}
    rows = detect(data, catalog.detectors)
    assert len(rows) == 1 and rows[0]["id"] == product_id
    assert "PRIVATE" not in json.dumps(rows)


def test_helm_app_version_is_not_chart_version(catalog):
    rows = detect({"helm": [{"chart": "argo-cd-8.3.0", "app_version": "3.2.0", "namespace": "argo"}]}, catalog.detectors)
    assert rows[0]["versions"] == ["3.2.0"]
    rows = detect({"helm": [{"chart": "tigera-operator-3.30.0", "app_version": "3.30.0"}]}, catalog.detectors)
    assert not rows[0]["versions"] and rows[0]["unknown_version"]


def test_typed_repositories_prevent_substring_false_detection(catalog):
    data = {"pods": [{"spec": {"containers": [{"image": "evil.example.com/argocd:v3.2.0"}]}}]}
    assert not detect(data, catalog.detectors)


@pytest.mark.parametrize("tag", ["latest", "main", "v3.2.0-rc1", None])
def test_unknown_and_prerelease_tags_are_not_stable_versions(catalog, tag):
    image = "quay.io/argoproj/argocd" + (":" + tag if tag else "@sha256:abcdef")
    rows = detect({"pods": [{"spec": {"containers": [{"image": image}]}}]}, catalog.detectors)
    assert rows[0]["unknown_version"] and not rows[0]["versions"]


def test_mixed_versions_and_istio_revisions_are_preserved(catalog):
    pods = [{"metadata": {"labels": {"istio.io/rev": v}}, "spec": {"containers": [{"image": "docker.io/istio/pilot:" + v}]}} for v in ("1.21.1", "1.30.0")]
    rows = detect({"pods": pods}, catalog.detectors)
    assert rows[0]["versions"] == ["1.21.1", "1.30.0"]
    assert len(rows[0]["evidence"]) == 2


def test_calico_metadata_version_and_client_cli_not_confused(catalog):
    rows = detect({"crds": [{"metadata": {"name": "clusterinformations.crd.projectcalico.org"}}],
        "clusterinformations.crd.projectcalico.org": [{"spec": {"calicoVersion": "v3.30.0"}}],
        "istio": {"clientVersion": {"version": "1.30.0"}}}, catalog.detectors)
    assert len(rows) == 1 and rows[0]["versions"] == ["v3.30.0"]
    assert not rows[0]["unknown_version"]


def test_support_vs_tested_only_and_eol(catalog):
    findings = catalog.evaluate("Argo CD", "3.2.0", "1.35.9", "https://example.com", TODAY)
    assert [f.status for f in findings] == ["UNKNOWN"]
    assert catalog.evaluate("Argo CD", "3.2.0", "1.34.9", "https://example.com", TODAY)[0].status == "PASS"
    findings = catalog.evaluate("Istio", "1.21.1", "1.35.9", "https://example.com", TODAY)
    assert {f.rule_id: f.status for f in findings} == {"VERSION_EOL": "WARN", "NOT_COMPATIBLE": "FAIL"}
    assert catalog.evaluate("Istio", "1.30.1", "1.35.9", "https://example.com", TODAY)[0].status == "PASS"


def test_expired_matrix_and_missing_version_are_unknown(catalog):
    assert catalog.evaluate("Argo CD", "3.2.0", "1.34.9", "https://example.com", date(2028, 1, 1))[0].status == "UNKNOWN"
    gatekeeper = catalog.evaluate("Gatekeeper", "3.17.0", "1.35.9", "https://example.com", TODAY)[0]
    assert gatekeeper.rule_id == "NO_OFFICIAL_NUMERIC_MATRIX" and gatekeeper.status == "UNKNOWN"
    assert gatekeeper.evidence["legacy_rule_id"] == "NO_SUPPORT_DATA"
    assert catalog.evaluate("Istio", "latest", "1.35.9", "https://example.com", TODAY)[0].rule_id == "VERSION_UNKNOWN"
    assert bound("1.35.x", True) > (1, 35, 100000)


def test_inventory_forbidden_is_unknown_not_absence(catalog):
    class Denied:
        context, timeout = "prod", 1
        def get(self, *a, **kw):
            raise CollectionError("forbidden")
    from unittest.mock import patch
    with patch("validator.platform_discovery.command_json", return_value=(None, "binary_missing")):
        inventory = collect(Denied(), [])
    assert sum(s["required"] and not s["completed"] for s in inventory["inventory_sources"]) == 5
    assert {e["source"] for e in inventory["discovery_errors"]} >= {"deployments.apps", "daemonsets.apps", "statefulsets.apps", "pods", "nodes", "Helm"}
    platform, findings = analyze(None, [], "1.34.8", "1.35.9", catalog)
    assert platform["discovery"]["status"] == "UNKNOWN"


def test_aks_metadata_allowlist_and_enabled_addons():
    data = {"nodes": [{"metadata": {"labels": {"kubernetes.azure.com/node-image-version": "AKSUbuntu-2204"}},
                       "spec": {"providerID": "azure:///subscriptions/sub/resourceGroups/node-rg/x"}}],
        "aks": {"kubernetesVersion": "1.34.8", "secret": "PRIVATE", "addonProfiles": {"azurepolicy": {"enabled": True, "config": {"private": "PRIVATE"}}},
                "securityProfile": {"defender": {"securityMonitoring": {"enabled": True}}}}}
    info, finding = azure_analyze(data, "1.34.8", "1.35.9")
    assert info["detected"] and {a["detector_id"] for a in info["addons"]} == {"azure-policy", "defender"}
    assert finding.status == "UNKNOWN"
    assert "PRIVATE" not in json.dumps(info)


def test_azure_cli_is_bound_to_node_resource_group(monkeypatch):
    calls = []
    def command(command, timeout):
        calls.append(command)
        if "list" in command:
            return [{"name": "real", "resourceGroup": "cluster-rg", "nodeResourceGroup": "node-rg"}], None
        return {"nodeResourceGroup": "node-rg", "kubernetesVersion": "1.34.8"}, None
    monkeypatch.setattr("validator.azure_validator.command_json", command)
    value, error = collect_aks({"nodes": [{"spec": {"providerID": "azure:///subscriptions/sub/resourceGroups/node-rg/x"}}]})
    assert error is None and value["kubernetesVersion"] == "1.34.8"
    assert all(c[:2] == ["az", "aks"] for c in calls)
    assert calls[1][calls[1].index("--name") + 1] == "real"


def base_report():
    return {"global_findings": [], "crds": [], "pluto": {"status": "PASS"},
        "platform": {"products": [], "discovery": {"status": "PASS"}, "aks": {"detected": False}}}


def test_score_weights_unknowns_and_blockers_are_not_diluted():
    report = base_report()
    report["crds"] = [{"findings": [{"category": "schema", "status": "PASS"}]}]
    assert score(report)["score"] == 100
    report["global_findings"] = [{"status": "UNKNOWN"}]
    assert score(report)["decision"] == "ATTENTION_REQUIRED"
    report["platform"]["products"] = [{"category": "operator", "findings": [{"status": "PASS"}] * 100 + [{"status": "FAIL"}]}]
    report["global_findings"] = [{"status": "FAIL"}]
    result = score(report)
    assert result["decision"] == "BLOCKED"
    assert result["categories"]["operators"]["earned_points"] == 0
    assert {k: v["weight"] for k, v in result["categories"].items()} == {"operators": 40, "crds": 25, "pluto": 15, "aks_addons": 10, "storage": 10}


def test_offline_platform_snapshot_in_all_reports_and_target_alias(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: pytest.fail("Offline must not run tools"))
    assert main(["--input", str(ROOT / "fixtures/valid-crds.json"), "--platform-input", str(ROOT / "fixtures/platform-inventory.json"),
                 "--current", "1.34.8", "--target-version", "1.35.9", "--output", str(tmp_path)]) == 1
    report = read_json(tmp_path / "report.json")
    assert report["readiness"]["decision"] == "BLOCKED"
    assert {p["product"] for p in report["platform"]["products"]} == {"Argo CD", "Istio", "Gatekeeper"}
    for extension in ("html", "md"):
        text = (tmp_path / ("report." + extension)).read_text(encoding="utf-8")
        assert "OPERATOR COMPATIBILITY ANALYSIS" in text and "BLOCKED" in text


def test_unknown_matrix_never_passes_on_running_pod(catalog):
    data = {"pods": [{"status": {"phase": "Running"}, "spec": {"containers": [{"image": "openpolicyagent/gatekeeper:v3.17.0"}]}}]}
    rows = detect(data, catalog.detectors)
    assert catalog.evaluate(rows[0]["product"], rows[0]["versions"][0], "1.35.9", rows[0]["source"], TODAY)[0].status == "UNKNOWN"


def test_bad_matrix_and_wildcard_order_rejected(tmp_path):
    with pytest.raises(ValueError):
        bound("1.x.2")
    file = tmp_path / "bad.json"
    file.write_text(json.dumps({"product": "Test", "versions": [{"version": "3.2.x"}]}), encoding="utf-8")
    with pytest.raises(ValueError):
        PlatformCatalog(file)


def test_authoritative_image_not_obscured_by_unknown_helm_app(catalog):
    rows = detect({"pods": [{"metadata": {"namespace": "tigera"}, "spec": {"containers": [{"image": "quay.io/tigera/operator:v1.38.0"}]}}],
        "helm": [{"namespace": "tigera", "chart": "tigera-operator-3.30.0", "app_version": "3.30.0"}]}, catalog.detectors)
    assert rows[0]["versions"] == ["v1.38.0"] and not rows[0]["unknown_version"]


def test_istioctl_control_and_data_versions_both_evaluated(catalog):
    rows = detect({"istio": {"clientVersion": {"version": "1.99.0"},
        "meshVersion": [{"Component": "pilot", "Revision": "stable", "Info": {"version": "1.30.1"}}],
        "dataPlaneVersion": [{"IstioVersion": "1.21.1", "NumProxies": 2}]}}, catalog.detectors)
    assert rows[0]["versions"] == ["1.30.1", "1.21.1"]
    assert "1.99.0" not in str(rows)


def test_live_helm_and_istio_commands_receive_source_context(monkeypatch):
    calls = []
    def command(command, timeout):
        calls.append(command)
        return ([] if command[0] == "helm" else {"meshVersion": [{"Info": {"version": "1.30.0"}}]}), None
    class Live:
        context, timeout = "explicit-production", 12
        def get(self, *args, **kwargs):
            return {"items": []}
    monkeypatch.setattr("validator.platform_discovery.command_json", command)
    collect(Live(), [{"metadata": {"name": "virtualservices.networking.istio.io"}}])
    assert calls[0][calls[0].index("--kube-context") + 1] == "explicit-production"
    assert calls[1] == ["istioctl", "version", "--context", "explicit-production", "-o", "json"]


def test_inventory_limit_and_unknown_versions_lower_score(catalog):
    snapshot = {"schema_version": 1, "kubernetes_version": "1.34.8"} | {k: [] for k in ("deployments.apps", "daemonsets.apps", "statefulsets.apps", "pods", "nodes", "helm")}
    snapshot["pods"] = [{"spec": {"containers": [{"image": "openpolicyagent/gatekeeper:latest"}]}}] * 2
    platform, findings = analyze(None, [], "1.34.8", "1.35.9", catalog, snapshot, limit=1)
    assert platform["discovery"]["status"] == "UNKNOWN"
    report = base_report()
    report["platform"] = platform
    report["global_findings"] = [f.to_dict() for f in findings]
    result = score(report)
    assert result["decision"] == "INCOMPLETE" and result["evidence_coverage"] < 100


def test_snapshot_context_mismatch_cannot_evaluate_another_live_cluster(catalog):
    class Live:
        context = "production"
    with pytest.raises(ValueError, match="contexto"):
        analyze(Live(), [], "1.34.8", "1.35.9", catalog, {"schema_version": 1, "context": "other", "kubernetes_version": "1.34.8"})
