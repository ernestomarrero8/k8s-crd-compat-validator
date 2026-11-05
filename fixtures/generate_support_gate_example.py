"""Synthetic support gate examples; pagination is mocked, no cluster/process is accessed."""
import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generate_followup_example import snapshot, deployment
from validator.collector import Collector, read_json
from validator.cli import main as validate
from validator.report_generator import write_reports
from validator.consolidated_report import consolidate


def build_snapshot():
    data = snapshot()
    data["deployments.apps"][1]["spec"]["template"]["spec"]["containers"][0]["image"] = "mcr.microsoft.com/oss/v2/open-policy-agent/gatekeeper:v3.23.1-8"
    data["deployments.apps"][2]["spec"]["template"]["spec"]["containers"][0]["image"] = "mcr.microsoft.com/oss/v2/tigera/operator:v1.40.15-4"
    data["daemonsets.apps"] += [deployment("disk", "mcr.microsoft.com/oss/v2/kubernetes-csi/azuredisk-csi:v1.34.7-7"),
        deployment("file", "mcr.microsoft.com/oss/v2/kubernetes-csi/azurefile-csi:v1.35.11-6"),
        deployment("provider", "mcr.microsoft.com/oss/azure/secrets-store/provider-azure:v1.1.0")]
    data["aks"].update(addonProfiles={"azurepolicy": {"enabled": True}, "azureKeyvaultSecretsProvider": {"enabled": True}},
        securityProfile={"defender": {"securityMonitoring": {"enabled": True}}}, agentPoolProfiles=[{"enableAutoScaling": True}])
    data["aks"]["storageProfile"].update(diskCSIDriver={"enabled": True}, fileCSIDriver={"enabled": True})
    data["discovery_errors"] = [{"source": "istioctl version", "reason": "binary_missing"}]
    now = datetime.now(timezone.utc)
    data["pods"] = data["pods"][:157]
    for i, pod in enumerate(data["pods"]):
        pod["spec"]["containers"][0]["image"] = "docker.io/istio/proxyv2:1.24.1"
        status = pod["status"]
        status["phase"] = "Succeeded" if i < 20 else "Failed" if 25 <= i < 27 else "Pending" if 30 <= i < 32 else "Running"
        if 20 <= i < 25:
            pod["metadata"]["deletionTimestamp"] = now.isoformat()
        if i in (30, 31):
            status["startTime"] = (now - timedelta(seconds=1200 if i == 30 else 30)).isoformat()
        status["conditions"][0]["status"] = "False" if i < 32 else "True"
        status["containerStatuses"][0]["ready"] = i >= 32
    data["pods"] += [{"metadata": {"name": f"plain-app-{i}", "namespace": "other"}, "spec": {"containers": []}} for i in range(2500)]
    all_pods = data["pods"]
    def mocked_api(command, **kwargs):
        query = parse_qs(urlsplit(command[-1]).query)
        offset, count = int(query.get("continue", ["0"])[0]), int(query["limit"][0])
        items = all_pods[offset:offset + count]
        result = {"items": items, "metadata": {"resourceVersion": "synthetic", "continue": str(offset + len(items)) if offset + len(items) < len(all_pods) else ""}}
        return SimpleNamespace(returncode=0, stdout=json.dumps(result), stderr="")
    captured = Collector("synthetic", runner=mocked_api).list_paginated("pods")
    data["pods"] = captured["items"]
    data["inventory_pages"] = {"pods": captured["inventory"]}
    return data


def main():
    parser = argparse.ArgumentParser(description="Generar soporte actual/objetivo y comparaciones sintéticas")
    parser.add_argument("--full-platform-evidence", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = root / "reports/examples/support-gate"
    output.mkdir(parents=True, exist_ok=True)
    baseline = build_snapshot()
    cases = [("demo-match", "match", False, 20000, False), ("demo-match-admin", "match", True, 20000, False),
        ("demo-partial", "partial", False, 120, False), ("demo-partial-admin", "partial", True, 120, False),
        ("demo-different", "different", False, 20000, False), ("demo-different-admin", "different", False, 20000, True)]
    entries = []
    with TemporaryDirectory() as temporary:
        temporary = Path(temporary)
        for context, identity, reverse, limit, change_version in cases:
            data = deepcopy(baseline)
            data["aks"]["id"] = f"/subscriptions/synthetic/resourceGroups/demo/providers/Microsoft.ContainerService/managedClusters/{identity}"
            if reverse:
                data["pods"].reverse()
            if change_version:
                data["deployments.apps"][3]["spec"]["template"]["spec"]["containers"][0]["image"] = "quay.io/argoproj/argocd:v3.3.0"
            file = temporary / "inventory.json"
            file.write_text(json.dumps(data), encoding="utf-8")
            directory = output / context
            code = validate(["--input", str(root / "fixtures/valid-crds.json"), "--platform-input", str(file), "--current", "1.34.8", "--target-version", "1.35.9",
                "--platform-limit", str(limit), "--output", str(directory), "--format", "json"] + (["--full-platform-evidence"] if args.full_platform_evidence else []))
            report = read_json(directory / "report.json")
            report.update(cluster=context, synthetic_example=True)
            write_reports(report, directory)
            entries.append({"context": context, "exit_code": code, "report_path": directory / "report.json"})
    consolidate(entries, output / "consolidated.html")
    print("Synthetic only: 2657 Pods via 6 mocked pages; 6 contexts / 3 identities; MATCH, INCONCLUSIVE and MISMATCH.")


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    main()
