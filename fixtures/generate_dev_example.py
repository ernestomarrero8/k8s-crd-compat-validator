"""Generate synthetic grouping/mismatch examples, without accessing any cluster."""
from copy import deepcopy
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validator.collector import read_json
from validator.consolidated_report import consolidate


def main():
    root = Path(__file__).resolve().parents[1]
    output = root / "reports/examples/dev-analysis"
    output.mkdir(parents=True, exist_ok=True)
    base = read_json(root / "reports/examples/reported-cases/report.json")
    entries = []
    for context, cluster, mismatch in [("demo-dev", "dev", False), ("demo-dev-admin", "dev", False),
            ("demo-mismatch", "mismatch", False), ("demo-mismatch-admin", "mismatch", True)]:
        report = deepcopy(base)
        report["cluster"] = context
        report["cluster_identity"] = f"/subscriptions/synthetic/resourceGroups/demo/providers/Microsoft.ContainerService/managedClusters/{cluster}"
        report["synthetic_example"] = True
        if mismatch:
            report["platform"]["inventory_sources"][0]["items_scanned"] += 1
        directory = output / context
        directory.mkdir(exist_ok=True)
        file = directory / "report.json"
        file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        entries.append({"context": context, "exit_code": report["validator"]["exit_code"], "report_path": file})
    consolidate(entries, output / "consolidated.html")
    print("Synthetic only: 4 contexts, 2 cluster identities, 1 explicit data mismatch.")


if __name__ == "__main__":
    main()
