"""Synthetic regressions for the report follow-up; never requires a real cluster."""
from copy import deepcopy
from pathlib import Path
import json
import pytest
from validator.collector import read_json
from validator.platform_analyzer import analyze
from validator.platform_catalog import PlatformCatalog
from validator.report_generator import html, write_reports
from validator.consolidated_report import consolidate

ROOT = Path(__file__).resolve().parents[1]


def inventory():
    return {"schema_version": 1, "kubernetes_version": "1.34.8", **{k: [] for k in
        ("deployments.apps", "daemonsets.apps", "statefulsets.apps", "pods", "nodes", "helm")}}


def workload(name, containers, init=None):
    return {"metadata": {"name": name, "namespace": "system"}, "status": {"availableReplicas": 1},
        "spec": {"template": {"metadata": {}, "spec": {"containers": containers, "initContainers": init or []}}}}


def platform(data, **kwargs):
    return analyze(None, [], "1.34.8", "1.35.9", PlatformCatalog(), data, **kwargs)[0]


@pytest.mark.parametrize("id_,name,image,version,container", [
    ("gatekeeper", "gatekeeper-audit", "mirror.example/opa/gatekeeper:v3.18.0", "3.18.0", "manager"),
    ("gatekeeper", "gatekeeper-controller-manager", "mirror.example/opa/gatekeeper:v3.18.0", "3.18.0", "manager"),
    ("tigera", "tigera-operator", "mirror.example/tigera/operator:v1.38.0", "1.38.0", "tigera-operator")])
def test_known_workload_extracts_controller_image_without_using_helper_tags(id_, name, image, version, container):
    data = inventory()
    obj = workload(name, [{"name": container, "image": image}, {"name": "metrics", "image": "metrics.example/helper:v9.9.9"}],
        [{"name": "init-helper", "image": "docker.io/alpine:3.20.0"}])
    obj["metadata"]["labels"] = {"helm.sh/chart": "synthetic-chart-99.0.0"}
    data["deployments.apps"] = [obj]
    row = next(r for r in platform(data)["products"] if r["id"] == id_)
    assert row["versions"] == [version]
    assert row["detection_status"] == "DETECTED_ACTIVE"
    evidence = row["evidence"][0]
    assert evidence["repository"] == image.rsplit(":", 1)[0]
    assert evidence["declared_tag"] == "v" + version
    assert evidence["chart"] == "synthetic-chart-99.0.0"
    assert len(evidence["observed_containers"]) == 3
    assert "9.9.9" not in row["versions"] and "99.0.0" not in row["versions"]


def test_known_workload_inspects_init_containers_and_keeps_imageid():
    data = inventory()
    obj = workload("gatekeeper-audit", [], [{"name": "manager", "image": "mirror.example/opa/gatekeeper:v3.18.0"}])
    obj["status"]["initContainerStatuses"] = [{"name": "manager", "imageID": "docker-pullable://mirror.example/opa/gatekeeper@sha256:abc", "ready": True, "restartCount": 2,
        "state": {"terminated": {"exitCode": 0, "message": "PRIVATE MESSAGE"}}}]
    data["deployments.apps"] = [obj]
    row = platform(data)["products"][0]
    assert row["versions"] == ["3.18.0"]
    observed = row["evidence"][0]["observed_containers"][0]
    assert observed["imageID"].endswith("sha256:abc") and observed["restartCount"] == 2
    assert "PRIVATE MESSAGE" not in json.dumps(row)


def test_chart_version_is_only_evidence_not_a_product_version():
    data = inventory()
    obj = workload("gatekeeper-audit", [{"name": "manager", "image": "mirror.example/gatekeeper@sha256:abc"}])
    obj["spec"]["template"]["metadata"] = {"labels": {"helm.sh/chart": "gatekeeper-9.9.9", "app.kubernetes.io/version": "3.18.0"}}
    data["deployments.apps"] = [obj]
    row = platform(data)["products"][0]
    assert row["versions"] == ["3.18.0"]
    assert row["evidence"][0]["chart"] == "gatekeeper-9.9.9"
    obj["spec"]["template"]["metadata"]["labels"].pop("app.kubernetes.io/version")
    assert not platform(data)["products"][0]["versions"]


def test_known_workload_preserves_explicit_unverified_image_revision():
    data = inventory()
    data["deployments.apps"] = [workload("gatekeeper-audit", [{"name": "manager", "image": "mirror.example/gatekeeper:v3.18.0-6"}])]
    row = platform(data)["products"][0]
    assert row["detected_version"] == "v3.18.0-6"
    assert row["findings"][0]["rule_id"] == "VERSION_FORMAT_UNVERIFIED"
    assert row["status"] == "UNKNOWN"


def test_tigera_does_not_take_a_helpers_operator_tag():
    data = inventory()
    data["deployments.apps"] = [workload("tigera-operator", [
        {"name": "tigera-operator", "image": "mirror.example/tigera/operator:v1.38.0"},
        {"name": "metrics-helper", "image": "other.example/metrics/operator:v9.9.9"}])]
    row = platform(data)["products"][0]
    assert row["versions"] == ["1.38.0"]


def test_exact_inventory_limit_is_not_proof_of_truncation():
    data = inventory()
    data["pods"] = [{"spec": {"containers": []}} for _ in range(2)]
    result = platform(data, limit=2)
    argo = next(d for d in result["detector_diagnostics"] if d["id"] == "argocd")
    assert argo["detection_status"] == "NOT_DETECTED"
    truncated = platform(data, limit=1)
    assert truncated["discovery"]["status"] == "UNKNOWN"


def test_no_matrix_message_preserves_internal_diagnostic_only():
    result = PlatformCatalog().evaluate("Secrets Store CSI Driver", "v1.1.2", "1.35.9", "https://example.com")[0]
    assert result.status == "UNKNOWN" and result.rule_id == "NO_OFFICIAL_KUBERNETES_MATRIX"
    assert "1.1.2" in result.description and "1.35.9" in result.description
    assert "matriz numérica verificable" in result.description
    assert result.evidence["catalog_lookup"]["reason"] == "no_numeric_rows"


def test_managed_snapshot_dimensions_are_explicit():
    data = inventory()
    data["aks"] = {"kubernetesVersion": "1.34.8", "storageProfile": {"snapshotController": {"enabled": True}}}
    row = platform(data)["products"][0]
    assert row["versions"] == ["MANAGED"] and row["managed_by"] == "AKS"
    assert row["detection_status"] == "DETECTED_ACTIVE"
    assert row["compatibility"] == "UNKNOWN" and row["status"] == "UNKNOWN"
    assert row["reason"] == "MANAGED_VERSION_NOT_EXPOSED"


def test_only_relevant_failed_sources_prevent_negative_product_detection():
    data = inventory()
    data.pop("helm")
    data["discovery_errors"] = [{"source": "nodes", "reason": "forbidden"}]
    result = platform(data)
    argo = next(d for d in result["detector_diagnostics"] if d["id"] == "argocd")
    assert argo["detection_status"] == "NOT_DETECTED"
    assert "Helm inventory unavailable" in argo["limitations"]
    assert any(s["source"] == "crds" and s["completed"] for s in result["inventory_sources"])
    data["discovery_errors"].append({"source": "pods", "reason": "inventory_limit"})
    argo = next(d for d in platform(data)["detector_diagnostics"] if d["id"] == "argocd")
    assert argo["detection_status"] == "INVENTORY_INCOMPLETE"
    assert "pods" in argo["reason"] and "inventory_limit" in argo["reason"]


def example(context):
    value = deepcopy(read_json(ROOT / "reports/examples/reported-cases/report.json"))
    value["cluster"] = context
    value["cluster_identity"] = "kube-system:shared"
    return value


def save(tmp_path, report, code):
    file = tmp_path / (report["cluster"] + ".json")
    file.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    return {"context": report["cluster"], "exit_code": code, "report_path": file}


def test_global_error_explains_exact_source_before_table(tmp_path):
    report = example("cluster-a")
    report["platform"]["inventory_sources"] = [{"source": "pods", "required": True, "completed": False, "error": "inventory_limit", "items_scanned": 2000}]
    entry = save(tmp_path, report, 2)
    output = tmp_path / "all.html"
    consolidate([entry], output)
    text = output.read_text(encoding="utf-8")
    summary = text.split('<div style="overflow-x:auto">', 1)[0]
    assert "Errores técnicos: 1" in summary and "cluster-a" in summary
    assert "pods" in summary and "inventory_limit" in summary and "2000" in summary
    assert "--platform-limit" in summary
    data = read_json(output.with_suffix(".json"))
    assert data["technical_errors"][0]["causes"][0]["source"] == "pods"


def test_mismatch_diff_identifies_counts_products_versions_and_permissions(tmp_path):
    a, b = example("ctx-a"), example("ctx-b")
    b["crds"] = []
    b["summary"]["total_crds"] = 0
    removed = b["platform"]["products"].pop()
    product = b["platform"]["products"][0]
    product["versions"] = []
    b["platform"]["inventory_sources"] = [{"source": "deployments.apps", "required": True, "completed": False, "error": "forbidden", "items_scanned": 0}]
    output = tmp_path / "all.html"
    consolidate([save(tmp_path, a, 1), save(tmp_path, b, 2)], output)
    data = read_json(output.with_suffix(".json"))
    diff = data["clusters"][0]["context_diff"]
    assert diff["crds"]["counts"] == {"ctx-a": 1, "ctx-b": 0}
    assert removed["product"] in diff["products"]["only_in"]["ctx-a"]
    assert diff["inventory_errors"]["by_context"]["ctx-b"][0]["source"] == "deployments.apps"
    assert diff["versions"][product["id"]]["ctx-b"] == ["UNKNOWN"]
    text = output.read_text(encoding="utf-8")
    summary = text.split('<div style="overflow-x:auto">', 1)[0]
    assert "Diferencias entre contextos" in summary and "CRDs" in summary and "deployments.apps" in summary
    assert len(data["clusters"]) == 1  # grouping stays unchanged


def istio_data(count=160):
    data = inventory()
    data["deployments.apps"] = [workload("istiod", [{"name": "discovery", "image": "docker.io/istio/pilot:1.24.1"}])]
    for i in range(count):
        version = "1.24.1" if i < count - 8 else "1.25.0"
        data["pods"].append({"metadata": {"name": f"sidecar-pod-{i}", "namespace": "applications"},
            "spec": {"containers": [{"name": "istio-proxy", "image": "docker.io/istio/proxyv2:" + version}]},
            "status": {"phase": "Running", "conditions": [{"type": "Ready", "status": "False" if i < 12 else "True"}],
                "containerStatuses": [{"name": "istio-proxy", "ready": i >= 12, "restartCount": 3,
                    "state": {"running": {"startedAt": "2026-11-05T00:00:00Z"}}}]}})
    return data


def test_istio_aggregation_counts_all_pods_and_justifies_not_ready():
    row = next(r for r in platform(istio_data())["products"] if r["id"] == "istio")
    summary = row["evidence_summary"]
    assert summary["data_plane"]["pods_observed"] == 160
    assert summary["data_plane"]["inactive_pods"] == 12
    assert summary["data_plane"]["other_active_versions"] == 8
    assert row["versions"] == ["1.24.1", "1.25.0"] and row["status"] == "FAIL"
    evidence = next(e for e in row["evidence"] if e["from"] == "pods")
    assert evidence["observed_status"]["phase"] == "Running" and evidence["activity"] == "inactive"
    assert evidence["observed_containers"][0]["ready"] is False
    assert evidence["observed_containers"][0]["restartCount"] == 3


def test_full_json_is_opt_in_and_html_size_does_not_scale_with_sidecar_count(tmp_path):
    report = example("test")
    sizes = []
    for count in (40, 1000):
        result = platform(istio_data(count), full_evidence=True)
        row = result["products"][0]
        assert sum(e["from"] == "pods" for e in row["evidence"]) == count
        report["platform"] = result
        report["global_findings"] = row["findings"]
        text = html(report)
        assert "Control plane" in text and "Data plane" in text
        assert "sidecar-pod-" not in text
        sizes.append(len(text))
    assert sizes[1] < sizes[0] + 3000
    original = deepcopy(report)
    write_reports(report, tmp_path)
    assert report == original  # rendering never alters JSON, hashes, score or verdicts
    assert "sidecar-pod-999" in (tmp_path / "report.json").read_text(encoding="utf-8")


@pytest.mark.parametrize("count,continuation,incomplete", [(2, False, False), (3, False, True), (1, True, True)])
def test_live_inventory_truncation_requires_omitted_items_or_continuation(monkeypatch, count, continuation, incomplete):
    from validator.platform_discovery import collect
    class Live:
        context, timeout = "test", 1
        def get(self, resource, **kwargs):
            return {"items": [{"spec": {"containers": []}} for _ in range(count)] if resource == "pods" else [],
                "metadata": {"continue": "unreturned-page" if continuation and resource == "pods" else ""}}
    monkeypatch.setattr("validator.platform_discovery.command_json", lambda *a: ([], None))
    data = collect(Live(), [], limit=2)
    source = next(s for s in data["inventory_sources"] if s["source"] == "pods")
    assert source["completed"] is not incomplete


def test_no_numeric_rows_is_json_diagnostic_not_html_text():
    data = inventory()
    data["daemonsets.apps"] = [workload("csi", [{"image": "registry.k8s.io/csi-secrets-store/driver:v1.1.2"}])]
    report = example("test")
    report["platform"] = platform(data)
    report["global_findings"] = report["platform"]["products"][0]["findings"]
    assert "no_numeric_rows" in json.dumps(report)
    assert "no_numeric_rows" not in html(report)


@pytest.mark.parametrize("full", [False, True])
def test_cli_full_platform_evidence_flag_is_explicit_and_offline(tmp_path, full):
    from validator.cli import main
    file = tmp_path / "inventory.json"
    file.write_text(json.dumps(istio_data(40)), encoding="utf-8")
    args = ["--input", str(ROOT / "fixtures/valid-crds.json"), "--platform-input", str(file), "--current", "1.34.8",
        "--target-version", "1.35.9", "--output", str(tmp_path / "report"), "--format", "json"]
    assert main(args + (["--full-platform-evidence"] if full else [])) == 1
    result = read_json(tmp_path / "report/report.json")["platform"]["products"][0]
    assert sum(e["from"] == "pods" for e in result["evidence"]) == (40 if full else 30)
    assert result["evidence_summary"]["data_plane"]["pods_observed"] == 40
