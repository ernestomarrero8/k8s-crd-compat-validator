"""Policy/technical semantics, known distribution builds, complete inventories and comparisons."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
import pytest
from validator.collector import Collector, read_json
from validator.platform_analyzer import analyze
from validator.platform_catalog import PlatformCatalog
from validator.consolidated_report import consolidate
from validator.report_generator import html
from test_report_followup import inventory, workload, example, save

NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)


def platform(data, catalog=None):
    return analyze(None, [], "1.34.8", "1.35.9", catalog or PlatformCatalog(), data)[0]


def test_istio_support_policy_is_not_a_demonstrated_technical_failure():
    data = inventory()
    data["deployments.apps"] = [workload("istiod", [{"name": "discovery", "image": "docker.io/istio/pilot:1.24.1"}])]
    row = platform(data)["products"][0]
    assert row["status"] == "FAIL" and row["support_status"] == "FAIL_SUPPORT_POLICY"
    assert row["technical_status"] == "NOT_TESTED"
    assert row["operational_status"] == "RUNNING_OUTSIDE_SUPPORT_MATRIX"
    assert row["current_kubernetes_evaluation"]["version"] == "1.34.8"
    assert row["current_kubernetes_evaluation"]["support_status"] == "OUTSIDE_SUPPORT_MATRIX"
    assert row["current_kubernetes_evaluation"]["observed_runtime"] == "ACTIVE"
    assert row["target_kubernetes_evaluation"]["support_status"] == "OUTSIDE_SUPPORT_MATRIX"
    assert row["decision"] == "BLOCKED" and row["preexisting_support_debt"] is True
    finding = next(f for f in row["findings"] if f["rule_id"] == "NOT_COMPATIBLE")
    assert finding["evidence"]["failure_domain"] == "SUPPORT_POLICY"
    assert "no ha demostrado una falla técnica" in row["support_explanation"]
    report = example("test"); report["platform"] = platform(data)
    text = html(report)
    assert "Soporte actual" in text and "Soporte objetivo" in text
    assert "Incompatibilidad técnica demostrada" in text and "NOT_TESTED" in text


def test_helm_alone_does_not_prove_running_outside_matrix():
    data = inventory(); data["helm"] = [{"chart": "istiod-1.24.1", "app_version": "1.24.1"}]
    row = platform(data)["products"][0]
    assert row["technical_status"] == "NOT_TESTED"
    assert row["current_kubernetes_evaluation"]["observed_runtime"] == "NOT_CONFIRMED"
    assert row["operational_status"] != "RUNNING_OUTSIDE_SUPPORT_MATRIX"


def test_running_product_without_matrix_does_not_claim_to_run_inside_support():
    data = inventory(); data["deployments.apps"] = [workload("gatekeeper-audit", [{"name": "manager", "image": "openpolicyagent/gatekeeper:v3.23.1"}])]
    row = platform(data)["products"][0]
    assert row["current_kubernetes_evaluation"]["observed_runtime"] == "ACTIVE"
    assert row["current_kubernetes_evaluation"]["support_status"] == "UNKNOWN"
    assert row["operational_status"] == "RUNNING_SUPPORT_UNKNOWN"
    assert row["preexisting_support_debt"] is None and row["additional_upgrade_support_risk"] is None


def test_new_upgrade_risk_is_separate_from_existing_support_debt(tmp_path):
    record = {"version": "1.30.x", "supported_kubernetes": {"min": "1.32", "max": "1.34"},
        "reviewed_on": "2026-11-05", "source": "https://example.com/synthetic", "evidence": "SYNTHETIC TEST ONLY"}
    file = tmp_path / "catalog.json"; file.write_text(json.dumps({"product": "Istio", "versions": [record]}), encoding="utf-8")
    data = inventory(); data["deployments.apps"] = [workload("istiod", [{"image": "docker.io/istio/pilot:1.30.1"}])]
    row = platform(data, PlatformCatalog(file))["products"][0]
    assert row["preexisting_support_debt"] is False and row["additional_upgrade_support_risk"] is True
    assert row["current_kubernetes_evaluation"]["support_status"] == "WITHIN_SUPPORT_MATRIX"
    assert row["target_kubernetes_evaluation"]["support_status"] == "OUTSIDE_SUPPORT_MATRIX"


@pytest.mark.parametrize("id_,name,repo,raw,upstream,revision", [
    ("gatekeeper", "gatekeeper-audit", "mcr.microsoft.com/oss/v2/open-policy-agent/gatekeeper", "v3.23.1-8", "3.23.1", "8"),
    ("tigera", "tigera-operator", "mcr.microsoft.com/oss/v2/tigera/operator", "v1.40.15-4", "1.40.15", "4"),
    ("tigera", "tigera-operator", "mcr.microsoft.com/oss/v2/tigera/operator", "v1.38.13-6", "1.38.13", "6")])
def test_known_microsoft_packaging_revision_is_normalized(id_, name, repo, raw, upstream, revision):
    data = inventory()
    data["deployments.apps"] = [workload(name, [{"name": "tigera-operator" if id_ == "tigera" else "manager", "image": repo + ":" + raw}])]
    row = platform(data)["products"][0]
    assert row["id"] == id_ and row["versions"] == [upstream]
    assert row["normalized_versions"] == [upstream] and not row["unknown_version"]
    assert row["version_details"][0] == {"raw_version": raw, "upstream_version": upstream, "distribution_revision": revision,
        "repository": repo, "normalization_rule": "microsoft_packaging_revision"}
    assert row["detected_versions"] == [raw]
    assert all(f["rule_id"] not in ("VERSION_UNKNOWN", "VERSION_FORMAT_UNVERIFIED") for f in row["findings"])
    assert row["findings"][0]["evidence"]["raw_version"] == raw
    if id_ == "gatekeeper":
        assert row["findings"][0]["rule_id"] == "NO_OFFICIAL_NUMERIC_MATRIX"


@pytest.mark.parametrize("repo,tag", [("mirror.example/opa/gatekeeper", "v3.23.1-8"),
    ("openpolicyagent/gatekeeper", "v3.23.1-8"), ("mcr.microsoft.com/oss/v2/open-policy-agent/gatekeeper", "v3.23.1-rc.1")])
def test_distribution_normalization_is_not_a_global_prerelease_rule(repo, tag):
    data = inventory(); data["deployments.apps"] = [workload("gatekeeper-audit", [{"name": "manager", "image": repo + ":" + tag}])]
    row = platform(data)["products"][0]
    assert row["normalized_versions"] == []
    assert row["findings"][0]["rule_id"] == "VERSION_FORMAT_UNVERIFIED"


@pytest.mark.parametrize("explicit_build,expected", [(False, "UNKNOWN"), (True, "PASS")])
def test_matrix_uses_upstream_selector_without_certifying_an_unreviewed_build(tmp_path, explicit_build, expected):
    record = {"version": "3.23.x", "supported_kubernetes": {"min": "1.31", "max": "1.35"},
        "reviewed_on": "2026-11-05", "source": "https://example.com/synthetic", "evidence": "SYNTHETIC TEST ONLY"}
    if explicit_build: record["vendor_versions"] = ["v3.23.1-8"]
    file = tmp_path / "catalog.json"; file.write_text(json.dumps({"product": "Gatekeeper", "versions": [record]}), encoding="utf-8")
    data = inventory(); data["deployments.apps"] = [workload("gatekeeper-audit", [{"name": "manager", "image": "mcr.microsoft.com/oss/v2/open-policy-agent/gatekeeper:v3.23.1-8"}])]
    row = platform(data, PlatformCatalog(file))["products"][0]
    assert row["status"] == expected
    assert row["findings"][0]["evidence"]["catalog_lookup"]["selected_selector"] == "3.23.x"
    assert row["findings"][0]["evidence"]["upstream_version"] == "3.23.1"


def paged_runner(total, fail_page=None, advance=None):
    calls = []
    def run(command, **kwargs):
        assert command[0] == "kubectl" and "--raw" in command and "get" in command
        query = parse_qs(urlsplit(command[-1]).query)
        offset = int(query.get("continue", ["0"])[0]); size = int(query["limit"][0])
        assert size <= 500
        calls.append((offset, size, kwargs))
        if fail_page == len(calls): return SimpleNamespace(returncode=1, stdout="", stderr="Forbidden PRIVATE_TOKEN")
        count = min(size, total - offset)
        value = {"items": [{"metadata": {"name": f"pod-{i}", "uid": str(i)}, "spec": {"containers": []}} for i in range(offset, offset + count)],
            "metadata": {"resourceVersion": "constant", "continue": str(offset + count) if offset + count < total else ""}}
        if advance: advance()
        return SimpleNamespace(returncode=0, stdout=json.dumps(value), stderr="")
    return run, calls


def test_paginated_pods_exceed_two_thousand_and_finish_only_without_continue():
    runner, calls = paged_runner(2505)
    value = Collector("test", runner=runner).list_paginated("pods", limit=20000)
    assert len(value["items"]) == 2505 and len(calls) == 6
    assert value["inventory"]["inventory_complete"] and value["inventory"]["items_scanned"] == 2505
    assert value["inventory"]["pages"] == 6
    assert "continue" not in value["inventory"]  # tokens never exported


def test_pagination_maximum_is_a_safety_limit_not_a_page_size():
    runner, calls = paged_runner(1000)
    value = Collector("test", runner=runner).list_paginated("pods", limit=750)
    assert len(value["items"]) == 750 and len(calls) == 2
    assert value["inventory"]["error"] == "inventory_limit" and not value["inventory"]["inventory_complete"]


def test_pagination_keeps_partial_inventory_on_rbac_failure():
    runner, _ = paged_runner(1000, fail_page=2)
    value = Collector("test", runner=runner).list_paginated("pods", limit=20000)
    assert len(value["items"]) == 500 and value["inventory"]["error"] == "forbidden"
    assert "PRIVATE_TOKEN" not in json.dumps(value)


def test_global_cluster_deadline_stops_pagination_and_keeps_partial_data(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr("validator.collector.monotonic", lambda: clock[0])
    runner, calls = paged_runner(1000, advance=lambda: clock.__setitem__(0, 2.0))
    value = Collector("test", runner=runner, total_timeout=1).list_paginated("pods", limit=20000)
    assert len(value["items"]) == 500 and len(calls) == 1
    assert value["inventory"]["error"] == "cluster_timeout"


def test_truncated_contexts_are_inconclusive_even_when_counts_are_equal(tmp_path):
    a, b = example("a"), example("b")
    for r in (a, b): r["platform"]["inventory_sources"] = [{"source": "pods", "required": True, "completed": False, "error": "inventory_limit", "items_scanned": 2000}]
    b["platform"]["products"][0]["evidence"].append({"from": "pods", "name": "different-sample"})
    file = tmp_path / "all.html"; consolidate([save(tmp_path, a, 2), save(tmp_path, b, 2)], file)
    row = read_json(file.with_suffix(".json"))["clusters"][0]
    assert not row["data_mismatch"]
    assert row["comparison_status"] == "CONTEXT_COMPARISON_INCONCLUSIVE"
    assert row["comparison_evidence"]["reason"] == "inventory_truncated"
    assert row["comparison_evidence"]["affected_sources"] == ["pods"]
    assert row["comparison_evidence"]["context_a_examined"] == 2000 and row["comparison_evidence"]["context_b_examined"] == 2000
    text = file.read_text(encoding="utf-8")
    assert "CONTEXT_COMPARISON_INCONCLUSIVE" in text and "CONTEXT_DATA_MISMATCH" not in text


def test_complete_contexts_with_real_version_difference_still_mismatch(tmp_path):
    a, b = example("a"), example("b")
    b["platform"]["products"][0]["versions"] = ["99.0.0"]
    file = tmp_path / "all.html"; consolidate([save(tmp_path, a, 1), save(tmp_path, b, 1)], file)
    row = read_json(file.with_suffix(".json"))["clusters"][0]
    assert row["data_mismatch"] and row["comparison_status"] == "CONTEXT_DATA_MISMATCH"


def test_optional_istioctl_missing_is_not_an_inventory_error():
    data = inventory(); data["deployments.apps"] = [workload("istiod", [{"image": "docker.io/istio/pilot:1.24.1"}])]
    data["discovery_errors"] = [{"source": "istioctl version", "reason": "binary_missing"}]
    result = platform(data); row = result["products"][0]
    optional = row["evidence_summary"]["optional_sources_unavailable"][0]
    assert optional["status"] == "OPTIONAL_SOURCE_UNAVAILABLE" and optional["impact"] == "none_for_version_detection"
    assert row["evidence_summary"]["inventory_errors"] == []
    assert result["discovery"]["evidence"]["errors"] == []
    assert result["discovery"]["status"] == "PASS"


def pod(name, phase, ready=False, reason=None, start=None, terminating=False):
    item = {"metadata": {"name": name, "namespace": "app"}, "spec": {"containers": [{"name": "istio-proxy", "image": "docker.io/istio/proxyv2:1.30.1"}]},
        "status": {"phase": phase, "conditions": [{"type": "Ready", "status": "True" if ready else "False"}],
            "containerStatuses": [{"name": "istio-proxy", "ready": ready, "restartCount": 1, "state": {"waiting": {"reason": reason}} if reason else {}}]}}
    if start: item["status"]["startTime"] = start
    if terminating: item["metadata"]["deletionTimestamp"] = "2026-11-05T11:59:00Z"
    return item


def test_sidecar_inactivity_is_classified_without_penalizing_completed_jobs():
    from validator.workload_evidence import istio_summary
    data = inventory(); data["pods"] = [pod("done", "Succeeded"), pod("ending", "Running", terminating=True), pod("failed", "Failed"),
        pod("not-ready", "Running"), pod("crash", "Running", reason="CrashLoopBackOff"), pod("pull", "Pending", reason="ImagePullBackOff"),
        pod("pending-old", "Pending", start="2026-11-05T11:40:00Z"), pod("pending-new", "Pending", start="2026-11-05T11:59:30Z")]
    definition = next(d for d in PlatformCatalog().detectors if d["id"] == "istio")
    summary = istio_summary(data, definition, now=NOW)["data_plane"]
    assert sum(summary["inactive_reasons"].values()) == 8
    assert summary["inactive_reasons"]["Completed"] == 1 and summary["inactive_reasons"]["Terminating"] == 1
    assert summary["operational_warnings"]["Pending_prolonged"] == 1
    assert summary["operational_warnings"]["Running_proxy_not_Ready"] == 1
    assert summary["operational_warnings"]["CrashLoopBackOff"] == 1 and summary["operational_warnings"]["ImagePullBackOff"] == 1
    data["pods"] = [pod("done", "Succeeded")]
    data["deployments.apps"] = [workload("istiod", [{"image": "docker.io/istio/pilot:1.30.1"}])]
    row = platform(data)["products"][0]
    assert all(f["rule_id"] != "ISTIO-DATA-PLANE-READINESS" for f in row["findings"])


def test_aks_management_requires_metadata_and_does_not_turn_unknown_into_pass(tmp_path):
    data = inventory(); data["daemonsets.apps"] = [workload("disk", [{"image": "mcr.microsoft.com/oss/v2/kubernetes-csi/azuredisk-csi:v1.34.7-7"}])]
    row = platform(data)["products"][0]
    assert row.get("managed_by") != "AKS"
    data["aks"] = {"kubernetesVersion": "1.34.8", "storageProfile": {"diskCSIDriver": {"enabled": True}, "snapshotController": {"enabled": True}}}
    result = platform(data); disk = next(p for p in result["products"] if p["id"] == "azure-disk")
    assert disk["managed_by"] == "AKS" and disk["status"] == "UNKNOWN"
    report = example("test"); report["platform"] = result
    file = tmp_path / "all.html"; consolidate([save(tmp_path, report, 1)], file)
    row = read_json(file.with_suffix(".json"))["clusters"][0]
    assert disk["product"] in row["aks_managed_unknown"] and disk["product"] not in row["third_party_unknown"]


def test_collection_uses_pagination_and_records_complete_counts(monkeypatch):
    from validator.platform_discovery import collect
    runner, pages = paged_runner(2505)
    def run(command, **kwargs):
        return runner(command, **kwargs) if "--raw" in command else SimpleNamespace(returncode=0, stdout='{"items": []}', stderr="")
    monkeypatch.setattr("validator.platform_discovery.command_json", lambda *a: ([], None))
    data = collect(Collector("test", runner=run), [])
    record = next(s for s in data["inventory_sources"] if s["source"] == "pods")
    assert record["inventory_complete"] and record["completed"] and record["items_scanned"] == 2505
    assert record["pages"] == 6 and len(pages) == 6


@pytest.mark.parametrize("mode,error", [("repeat", "pagination_loop"), ("revision", "pagination_snapshot_changed"), ("invalid", "invalid_response")])
def test_bad_pagination_is_incomplete_without_exporting_tokens(mode, error):
    count = [0]
    def run(command, **kwargs):
        count[0] += 1
        value = {"items": [{"metadata": {"name": str(count[0])}}], "metadata": {"continue": "PRIVATE_CONTINUE_TOKEN", "resourceVersion": "a"}}
        if count[0] == 2:
            if mode == "revision": value["metadata"]["resourceVersion"] = "b"
            if mode == "invalid": value["metadata"]["continue"] = 123
        return SimpleNamespace(returncode=0, stdout=json.dumps(value), stderr="")
    result = Collector("test", runner=run).list_paginated("pods")
    assert result["inventory"]["error"] == error and not result["inventory"]["inventory_complete"]
    assert len(result["items"]) == 1 and "PRIVATE_CONTINUE_TOKEN" not in json.dumps(result)


def test_snapshot_page_metadata_cannot_hide_a_new_safety_limit():
    data = inventory(); data["pods"] = [pod("a", "Running", ready=True), pod("b", "Running", ready=True)]
    data["inventory_pages"] = {"pods": {"inventory_complete": True, "pages": 1, "items_scanned": 2, "error": None}}
    result, _ = analyze(None, [], "1.34.8", "1.35.9", PlatformCatalog(), data, limit=1)
    source = next(s for s in result["inventory_sources"] if s["source"] == "pods")
    assert not source["completed"] and not source["inventory_complete"] and source["error"] == "inventory_limit"
    assert source["items_scanned"] == 1


def test_completed_only_sidecars_are_artifacts_without_operational_warn():
    data = inventory(); data["pods"] = [pod("old-job", "Succeeded")]
    row = platform(data)["products"][0]
    assert row["presence_status"] == "ARTIFACTS_ONLY"
    assert not any(f["status"] == "WARN" for f in row["findings"])
    assert row["current_kubernetes_evaluation"]["observed_runtime"] == "NOT_CONFIRMED"


def test_complete_contexts_do_not_mismatch_only_due_to_optional_evidence_samples(tmp_path):
    a, b = example("a"), example("b")
    product = b["platform"]["products"][0]
    product["evidence"].append({"from": "pods", "name": "different-order-sample"})
    product["resolution_sources"] = ["Helm"]
    b["platform"]["optional_sources_unavailable"] = [{"source": "istioctl version", "reason": "binary_missing"}]
    file = tmp_path / "all.html"; consolidate([save(tmp_path, a, 1), save(tmp_path, b, 1)], file)
    result = read_json(file.with_suffix(".json"))["clusters"][0]
    assert not result["data_mismatch"] and result["comparison_status"] == "MATCH"


def test_actual_technical_crd_failure_is_not_relabelled_as_support_policy(tmp_path):
    value = example("test")
    f = deepcopy(value["crds"][0]["findings"][0])
    f.update(rule_id="SYNTHETIC-STORAGE-FAIL", category="storage", status="FAIL", severity="HIGH", evidence={})
    value["crds"][0]["findings"].append(f)
    file = tmp_path / "all.html"; consolidate([save(tmp_path, value, 1)], file)
    reasons = read_json(file.with_suffix(".json"))["clusters"][0]["blocking_reasons"]
    reason = next(r for r in reasons if r["rule_id"] == f["rule_id"])
    assert reason["result_type"] == "FAIL_TECHNICAL" and reason["failure_domain"] == "TECHNICAL"


def test_packaging_matrix_prefers_explicit_build_when_upstream_rows_overlap(tmp_path):
    base = {"version": "3.23.x", "supported_kubernetes": {"min": "1.31", "max": "1.35"},
        "reviewed_on": "2026-11-05", "source": "https://example.com/synthetic", "evidence": "SYNTHETIC TEST ONLY"}
    file = tmp_path / "catalog.json"
    file.write_text(json.dumps({"product": "Gatekeeper", "versions": [base | {"vendor_versions": ["v3.23.1-8"]},
        base | {"vendor_versions": ["v3.23.1-9"], "supported_kubernetes": {"min": "1.31", "max": "1.34"}}]}), encoding="utf-8")
    data = inventory(); data["deployments.apps"] = [workload("gatekeeper-audit", [{"name": "manager", "image": "mcr.microsoft.com/oss/v2/open-policy-agent/gatekeeper:v3.23.1-8"}])]
    row = platform(data, PlatformCatalog(file))["products"][0]
    assert row["status"] == "PASS" and row["findings"][0]["evidence"]["matrix"]["vendor_versions"] == ["v3.23.1-8"]
