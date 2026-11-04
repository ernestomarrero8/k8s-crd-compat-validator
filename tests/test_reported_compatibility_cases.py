from datetime import date
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from validator.platform_catalog import PlatformCatalog, release
from validator.platform_analyzer import analyze
from validator.platform_discovery import detect
from validator.version_resolver import resolve
from validator.readiness import score
from validator.collector import Collector, CollectionError

TODAY = date(2026, 11, 4)


def inventory(images):
    return {"schema_version": 1, "kubernetes_version": "1.34.8",
        "pods": [{"metadata": {"namespace": "system"}, "spec": {"containers": [{"image": image}]}} for image in images],
        "deployments.apps": [], "daemonsets.apps": [], "statefulsets.apps": [], "nodes": [], "helm": []}


def test_istio_1241_finds_minor_matrix_and_fails():
    results = PlatformCatalog().evaluate("Istio", "1.24.1", "1.35.9", "https://istio.io", TODAY)
    assert {f.rule_id: f.status for f in results} == {"VERSION_EOL": "WARN", "NOT_COMPATIBLE": "FAIL"}
    trace = results[-1].evidence["catalog_lookup"]
    assert trace["normalized_version"] == "1.24.1"
    assert trace["selected_selector"] == "1.24.x"
    assert trace["files"] == ["istio.json"]
    assert trace["paths"] == ["catalogs/support/istio.json"]
    assert results[-1].evidence["matrix"]["max_kubernetes"] == "1.31.x"


def test_calico_v3312_finds_minor_matrix():
    results = PlatformCatalog().evaluate("Calico", "v3.31.2", "1.35.9", "https://docs.tigera.io", TODAY)
    assert results[0].status == "PASS"
    assert results[0].evidence["catalog_lookup"]["selected_selector"] == "3.31.x"


@pytest.mark.parametrize("product,image,version,normalized", [
    ("Azure File CSI Driver", "mcr.microsoft.com/oss/v2/kubernetes-csi/azurefile-csi:v1.35.11-6", "v1.35.11-6", "1.35.11"),
    ("Azure Disk CSI Driver", "mcr.microsoft.com/oss/v2/kubernetes-csi/azuredisk-csi:v1.34.7-7", "v1.34.7-7", "1.34.7")])
def test_numeric_vendor_revisions_are_detected_versions_not_unknown(product, image, version, normalized):
    catalog = PlatformCatalog()
    platform, findings = analyze(None, [], "1.34.8", "1.35.9", catalog, inventory([image]))
    row = platform["products"][0]
    assert row["product"] == product
    assert row["versions"] == [version] and row["detected_version"] == version
    assert row["confidence"] == "image_tag"
    assert row["normalized_versions"] == [normalized]
    assert not row["unknown_version"]
    assert row["findings"][0]["rule_id"] == "NO_SUPPORT_DATA"
    assert row["findings"][0]["evidence"]["installed_version"] == version
    assert row["findings"][0]["evidence"]["catalog_lookup"]["reason"] == "family_not_catalogued"


def test_revision_and_prerelease_are_not_globally_coerced():
    assert release("v1.35.11-6") is None
    assert release("v1.35.11-6", "Azure File CSI Driver") == (1, 35, 11)
    assert release("v1.35.11-rc1", "Azure File CSI Driver") is None


def test_explicit_unrecognized_suffix_keeps_raw_version_and_reason():
    finding = PlatformCatalog().evaluate("Azure File CSI Driver", "v1.35.11-custom", "1.35.9", "https://example.com", TODAY)[0]
    assert finding.rule_id == "VERSION_FORMAT_UNVERIFIED"
    assert finding.evidence["detected_version"] == "v1.35.11-custom"
    assert finding.evidence["catalog_lookup"]["reason"] == "unrecognized_version_format"


def test_upstream_matrix_does_not_certify_aks_build():
    finding = PlatformCatalog().evaluate("Azure File CSI Driver", "v1.35.7-6", "1.35.9", "https://example.com", TODAY)[0]
    assert finding.rule_id == "VENDOR_BUILD_UNVERIFIED" and finding.status == "UNKNOWN"
    assert finding.evidence["installed_version"] == "v1.35.7-6"
    assert finding.evidence["matrix"]["version"] == "1.35.7"


def test_exact_vendor_support_and_more_specific_row_override_family(tmp_path):
    base = {"version": "1.35.x", "supported_kubernetes": {"min": "1.30", "max": "1.35"},
            "source": "https://example.com/support", "reviewed_on": "2026-11-04", "evidence": "SYNTHETIC TEST ONLY"}
    exact = base | {"version": "1.35.11", "vendor_versions": ["v1.35.11-6"]}
    file = tmp_path / "test.json"
    file.write_text(json.dumps({"product": "Azure File CSI Driver", "versions": [base, exact]}), encoding="utf-8")
    finding = PlatformCatalog(file).evaluate("Azure File CSI Driver", "v1.35.11-6", "1.35.9", "https://example.com", TODAY)[0]
    assert finding.status == "PASS"
    assert finding.evidence["catalog_lookup"]["selected_selector"] == "1.35.11"


def test_no_match_explains_catalog_present_but_missing_family():
    finding = PlatformCatalog().evaluate("Istio", "1.99.0", "1.35.9", "https://istio.io", TODAY)[0]
    trace = finding.evidence["catalog_lookup"]
    assert trace["catalog_present"] and trace["available_selectors"]
    assert trace["matched_selectors"] == [] and trace["reason"] == "family_not_catalogued"


def test_missing_argocd_has_explicit_detector_diagnostic():
    platform, _ = analyze(None, [], "1.34.8", "1.35.9", PlatformCatalog(), inventory([]))
    diagnostic = next(d for d in platform["detector_diagnostics"] if d["id"] == "argocd")
    assert diagnostic["status"] == "NOT_DETECTED" and diagnostic["catalog_present"]
    assert not platform["products"]


def test_component_tag_is_not_a_flux_product_version():
    platform, _ = analyze(None, [], "1.34.8", "1.35.9", PlatformCatalog(),
        inventory(["ghcr.io/fluxcd/source-controller:v1.6.0"]))
    row = platform["products"][0]
    assert row["product"] == "FluxCD"
    assert row["detected_versions"] == [] and row["versions"] == []
    assert row["findings"][0]["rule_id"] == "VERSION_UNKNOWN"
    assert row["evidence"][0]["declared_tag"] == "v1.6.0"
    assert row["evidence"][0]["version_scope"] == "component_not_product_release"


def test_explicit_private_argocd_alias_and_gatekeeper_deployment(tmp_path):
    aliases = tmp_path / "aliases.json"
    aliases.write_text(json.dumps({"schema_version": 1, "products": [{"id": "argocd", "images": ["private.example.com/platform/argocd"]}]}), encoding="utf-8")
    catalog = PlatformCatalog(detectors_path=aliases)
    data = inventory(["private.example.com/platform/argocd:v3.2.0"])
    data["deployments.apps"] = [{"metadata": {"name": "gatekeeper-controller-manager"}, "spec": {"template": {"spec": {
        "containers": [{"image": "openpolicyagent/gatekeeper:v3.18.0"}]}}}}]
    rows = resolve(detect(data, catalog.detectors))
    assert {r["id"] for r in rows} == {"argocd", "gatekeeper"}
    assert next(r for r in rows if r["id"] == "gatekeeper")["versions"] == ["3.18.0"]
    assert next(r for r in rows if r["id"] == "argocd")["evidence"][0]["identity_basis"] == "configured_repository"


def report(states):
    return {"global_findings": [{"status": s} for s in states], "crds": [{"findings": [{"category": "schema", "status": "PASS"}]}],
        "pluto": {"status": "PASS"}, "platform": {"discovery": {"status": "PASS"}, "aks": {"detected": False},
        "products": [{"category": "operator", "findings": [{"status": s}]} for s in states]}}


def test_partial_evidence_no_longer_erases_category_and_blockers_still_gate():
    unknown = score(report(["PASS", "UNKNOWN"]))
    failed = score(report(["PASS", "FAIL"]))
    passed = score(report(["PASS", "PASS"]))
    assert unknown["categories"]["operators"]["earned_points"] == 20
    assert unknown["decision"] == "ATTENTION REQUIRED"
    assert failed["decision"] == "BLOCKED"
    assert failed["evidence_coverage"] > unknown["evidence_coverage"]
    assert failed["assessed_compatibility_score"] < unknown["assessed_compatibility_score"]
    assert passed["score"] > unknown["score"] and passed["decision"] == "READY"


def test_dns_failure_is_unreachable_not_proof_of_deleted_cluster():
    collector = Collector(runner=lambda *a, **k: SimpleNamespace(returncode=1, stdout="", stderr="dial tcp PRIVATE_HOST: no such host"))
    with pytest.raises(CollectionError) as error:
        collector.version()
    assert error.value.code == "unreachable"
    assert "PRIVATE_HOST" not in str(error.value)
