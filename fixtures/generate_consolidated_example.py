"""Generate a standalone demonstration from synthetic reports; never uses a cluster."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import argparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validator.collector import read_json
from validator.consolidated_report import consolidate


def main():
    output = Path(__file__).resolve().parents[1] / "reports/examples"
    parser = argparse.ArgumentParser(description="Consolidado sintético de un reporte ya generado")
    parser.add_argument("--source", type=Path, default=output / "report.json")
    args = parser.parse_args()
    base = read_json(args.source)
    entries = []
    for name in ("demo-cluster-a", "demo-cluster-b"):
        report = deepcopy(base)
        report["cluster"] = name
        folder = output / name
        folder.mkdir(exist_ok=True)
        path = folder / "report.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        entries.append({"context": name, "exit_code": 1, "report_path": path})
    entries.append({"context": "demo-unreachable", "exit_code": 2, "report_path": output / "demo-unreachable/report.json"})
    consolidate(entries, output / "consolidated.html")


if __name__ == "__main__":
    main()
