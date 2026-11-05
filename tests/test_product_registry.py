from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import subprocess
import pytest
from validator.collector import read_json
from validator.platform_catalog import PlatformCatalog
from validator.platform_analyzer import analyze
from validator.version_resolver import resolve
from validator.platform_discovery import detect
from validator.cli import main

ROOT = Path(__file__).resolve().parents[1]
TODAY = date(2026, 11, 4)


def snapshot(version="1.30.7"):
    return {"schema_version": 1, "kubernetes_version": "1.34.8",
        "deployments.apps": [{"metadata": {"namespace": "istio-system", "name": "istiod"},
            "spec": {"template": {"spec": {"containers": [{"image": "docker.io/istio/pilot:" + version}]}}}}],
        "daemonsets.apps": [], "statefulsets.apps": [], "pods": [], "nodes": [], "helm": []}


def istio_crd(crd):
    crd = deepcopy(crd)
    crd["spec"]["group"] = "networking.istio.io"
    crd["metadata"]["name"] = "widgets.networking.istio.io"
    return crd


def test_precedence_and_all_mixed_versions_still_evaluated():
    data = snapshot()
    data["helm"] = [{"namespace": "istio-system", "chart": "istiod-1.29.0", "app_version": "1.29.0"}]
    data["istio"] = {"clientVersion": {"version": "1.99.0"}, "meshVersion": [{"Info": {"version": "1.30.7"}}],
                     "dataPlaneVersion": [{"IstioVersion": "1.21.1", "NumProxies": 1}]}
    catalog = PlatformCatalog()
    registry = resolve(detect(data, catalog.detectors))
    assert len(registry) == 1
    assert registry[0]["resolved_versions"] == ["1.21.1", "1.30.7"]
    assert registry[0]["versions"] == ["1.21.1", "1.29.0", "1.30.7"]
    assert registry[0]["version_conflict"]
    assert "1.99.0" not in str(registry)
    platform, findings = analyze(None, [], "1.34.8", "1.35.9", catalog, data)
    assert platform["products"][0]["status"] == "FAIL"


def test_fallback_helm_resolves_unknown_tag_without_fabricating_binary():
    data = snapshot("latest")
    data["helm"] = [{"namespace": "istio-system", "chart": "istiod-1.30.7", "app_version": "1.30.7"}]
    row = resolve(detect(data, PlatformCatalog().detectors))[0]
    assert row["resolved_versions"] == ["1.30.7"]
    assert row["resolution_sources"] == ["Helm"]
    assert not row["unknown_version"]
    assert any(e.get("declared_tag") == "latest" for e in row["evidence"])


def test_registry_is_one_entry_per_product_and_normalizes_v_tags():
    data = snapshot()
    other = deepcopy(data["deployments.apps"][0])
    other["metadata"]["namespace"] = "second-installation"
    other["spec"]["template"]["spec"]["containers"][0]["image"] = "docker.io/istio/pilot:v1.30.7"
    data["deployments.apps"].append(other)
    row = resolve(detect(data, PlatformCatalog().detectors))[0]
    assert row["versions"] == ["1.30.7"]
    assert len(row["namespaces"]) == 2


@pytest.mark.parametrize("defect", [False, True])
def test_cli_reuses_support_without_hiding_storage_defects(tmp_path, monkeypatch, crd, defect):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("Offline cannot execute tools"))
    crd = istio_crd(crd)
    if defect:
        crd["status"]["storedVersions"] = ["retired"]
    input_ = tmp_path / "crd.json"
    input_.write_text(json.dumps(crd), encoding="utf-8")
    inventory = tmp_path / "inventory.json"
    inventory.write_text(json.dumps(snapshot()), encoding="utf-8")
    output = tmp_path / "reports"
    # No Pluto scan offline: incomplete coverage (2) unless a documented FAIL determines BLOCKED (1).
    assert main(["--input", str(input_), "--platform-input", str(inventory), "--current", "1.34.8", "--target", "1.35.9", "--output", str(output)]) == (1 if defect else 2)
    report = read_json(output / "report.json")
    result = report["crds"][0]
    assert result["product_compatibility"]["status"] == "PASS"
    assert result["product_compatibility"]["versions"] == ["1.30.7"]
    assert result["upgrade_risk"] == ("HIGH" if defect else "INFO")
    rules = {f["rule_id"] for f in result["findings"]}
    assert "PRODUCT_SUPPORT" in rules
    assert rules.isdisjoint({"OPERATOR-SUPPORT", "OPERATOR-IDENTITY", "OPERATOR-OLM"})
    if defect:
        assert result["status"] == "FAIL" and "STORED-INCONSISTENT" in rules
    else:
        assert result["status"] == "UNKNOWN"  # Independent instance inspection still not performed.
    assert "Soporte producto" in (output / "report.html").read_text(encoding="utf-8")
    assert report["platform"]["support_coverage"]["unknown_percentage"] == 0


def test_new_support_schema_and_verifiable_url_required(tmp_path):
    record = {"product": "Example", "version": "2.0.x", "supported_kubernetes": {"min": "1.32", "max": "1.36"},
              "support_state": "supported", "source": "official", "source_url": "https://example.com/support", "reviewed_on": "2026-11-04", "evidence": "Synthetic test record only"}
    path = tmp_path / "example.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    catalog = PlatformCatalog(path)
    assert catalog.evaluate("Example", "2.0.9", "1.35.9", "https://example.com", TODAY)[0].rule_id == "COMPATIBLE"
    assert catalog.evaluate("Example", "2.0.9", "1.37.0", "https://example.com", TODAY)[0].rule_id == "NOT_COMPATIBLE"
    record.pop("source_url")
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError):
        PlatformCatalog(path)


def test_extended_real_support_matrices():
    catalog = PlatformCatalog()
    for product, version in (("Cert Manager", "1.20.0"), ("Calico", "3.31.0")):
        results = catalog.evaluate(product, version, "1.35.9", "https://example.com", TODAY)
        assert results[0].status == "PASS"
        assert results[0].evidence["reviewed_on"]
    old = catalog.evaluate("Cert Manager", "1.16.0", "1.35.9", "https://example.com", TODAY)
    assert {f.rule_id: f.status for f in old} == {"VERSION_EOL": "WARN", "NOT_COMPATIBLE": "FAIL"}
    eol_in_range = catalog.evaluate("Cert Manager", "1.19.0", "1.35.9", "https://example.com", TODAY)
    assert {f.rule_id: f.status for f in eol_in_range} == {"VERSION_EOL": "WARN", "COMPATIBLE": "PASS"}


def test_public_policy_not_invented_into_historical_support():
    result = PlatformCatalog().evaluate("Secrets Store CSI Driver", "1.0.0", "1.35.9", "https://example.com", TODAY)[0]
    assert result.rule_id == "NO_OFFICIAL_KUBERNETES_MATRIX" and result.status == "UNKNOWN"
    assert result.evidence["legacy_rule_id"] == "NO_SUPPORT_DATA"
    assert result.evidence["catalog_limitations"]


def test_duplicate_crds_do_not_duplicate_product_evaluation(crd):
    from validator.product_link import owner_result
    catalog = PlatformCatalog()
    owned = istio_crd(crd)
    platform, findings = analyze(None, [owned, owned], "1.34.8", "1.35.9", catalog, snapshot())
    assert sum(f.rule_id == "COMPATIBLE" for f in findings) == 1
    assert owner_result(owned, platform, catalog.ownership)["product"] == "Istio"
    unrelated = deepcopy(owned)
    unrelated["spec"]["group"] = "not-networking.istio.io"
    unrelated["metadata"]["name"] = "widgets.not-networking.istio.io"
    assert owner_result(unrelated, platform, catalog.ownership) is None


def test_non_primary_crd_can_trigger_official_version_query(monkeypatch):
    from validator.platform_discovery import collect
    catalog = PlatformCatalog()
    calls = []
    class Live:
        context, timeout = "prod", 12
        def get(self, *a, **k):
            return {"items": []}
    def command(args, timeout):
        calls.append(args)
        return ([] if args[0] == "helm" else {"meshVersion": [{"Info": {"version": "1.30.7"}}]}), None
    monkeypatch.setattr("validator.platform_discovery.command_json", command)
    crds = [{"metadata": {"name": "authorizationpolicies.security.istio.io"}, "spec": {"group": "security.istio.io"}}]
    inventory = collect(Live(), crds, definitions=catalog.detectors)
    products = resolve(detect(inventory, catalog.detectors))
    assert len(products) == 1 and products[0]["resolved_versions"] == ["1.30.7"]
    assert calls[-1][:2] == ["istioctl", "version"]
