"""Offline synthetic follow-up report: versions, real diffs, technical causes and bounded HTML."""
from copy import deepcopy
import argparse
from pathlib import Path
import json
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validator.cli import main as validate
from validator.collector import read_json
from validator.report_generator import write_reports
from validator.consolidated_report import consolidate


def deployment(name, image, container="manager"):
    return {"metadata": {"name": name, "namespace": "system"}, "status": {"availableReplicas": 1},
        "spec": {"template": {"spec": {"containers": [{"name": container, "image": image}]}}}}


def snapshot():
    data = {"schema_version": 1, "kubernetes_version": "1.34.8", **{k: [] for k in
        ("deployments.apps", "daemonsets.apps", "statefulsets.apps", "pods", "nodes", "helm")}}
    data["deployments.apps"] = [deployment("istiod", "docker.io/istio/pilot:1.24.1", "discovery"),
        deployment("gatekeeper-audit", "mirror.example/opa/gatekeeper:v3.18.0"),
        deployment("tigera-operator", "mirror.example/tigera/operator:v1.38.0", "tigera-operator"),
        deployment("argocd-server", "quay.io/argoproj/argocd:v3.2.0", "argocd-server")]
    data["daemonsets.apps"] = [deployment("secrets-store-csi", "registry.k8s.io/csi-secrets-store/driver:v1.1.2")]
    data["clusterinformations.crd.projectcalico.org"] = [{"spec": {"calicoVersion": "v3.31.2"}}]
    data["aks"] = {"kubernetesVersion": "1.34.8", "id": "/subscriptions/synthetic/resourceGroups/demo/providers/Microsoft.ContainerService/managedClusters/followup",
        "storageProfile": {"snapshotController": {"enabled": True}}}
    for i in range(160):
        version = "1.24.1" if i < 152 else "1.25.0"
        data["pods"].append({"metadata": {"name": f"synthetic-app-{i}", "namespace": "applications"},
            "spec": {"containers": [{"name": "istio-proxy", "image": "docker.io/istio/proxyv2:" + version}]},
            "status": {"phase": "Running", "conditions": [{"type": "Ready", "status": "False" if i < 12 else "True"}],
                "containerStatuses": [{"name": "istio-proxy", "ready": i >= 12, "restartCount": 2, "state": {"running": {"startedAt": "2026-11-05T00:00:00Z"}}}]}})
    return data


def main():
    parser = argparse.ArgumentParser(description="Generar ejemplos sintéticos sin consultar un clúster")
    parser.add_argument("--full-platform-evidence", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = root / "reports/examples/report-followup"
    output.mkdir(parents=True, exist_ok=True)
    base = snapshot()
    entries = []
    with TemporaryDirectory() as temporary:
        temporary = Path(temporary)
        for context, denied, limit in [("demo-platform", False, 2000), ("demo-platform-admin", True, 2000), ("demo-truncated", False, 120)]:
            data = deepcopy(base)
            if denied:
                data["deployments.apps"] = []
                data["discovery_errors"] = [{"source": "deployments.apps", "reason": "forbidden"}]
            if limit == 120:
                data["aks"]["id"] += "-truncated"
            input_ = temporary / "platform.json"
            input_.write_text(json.dumps(data), encoding="utf-8")
            crds = temporary / "crds.json"
            crds.write_text(json.dumps({"kind": "List", "items": []} if denied else read_json(root / "fixtures/valid-crds.json")), encoding="utf-8")
            directory = output / context
            code = validate(["--input", str(crds), "--platform-input", str(input_), "--current", "1.34.8", "--target-version", "1.35.9",
                "--platform-limit", str(limit), "--output", str(directory), "--format", "json"] + (["--full-platform-evidence"] if args.full_platform_evidence else []))
            report = read_json(directory / "report.json")
            report["cluster"] = context
            report["synthetic_example"] = True
            write_reports(report, directory, "all")
            entries.append({"context": context, "exit_code": code, "report_path": directory / "report.json"})
    consolidate(entries, output / "consolidated.html")
    print("Synthetic only: 3 contexts, 2 identities, 2 technical-error groups; no cluster commands executed.")


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    main()
