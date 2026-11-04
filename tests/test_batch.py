from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
import pytest
import batch
from validator.collector import read_json
from validator.consolidated_report import consolidate

EXAMPLE = Path(__file__).resolve().parents[1] / "reports/examples/report.json"


def make_report(path, context, text="NAME NAMESPACE\nexample default"):
    report = deepcopy(read_json(EXAMPLE))
    report["cluster"] = context
    report["pluto"]["stdout"] = text
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report), encoding="utf-8")
    return report


def test_standalone_consolidated_contains_all_detail_and_failures(tmp_path):
    entries = []
    for index, name in enumerate(("cluster-a", "cluster-b", "unreachable")):
        path = tmp_path / name / "report.json"
        if index < 2:
            make_report(path, name, f"PLUTO-TABLE-{name}")
        entries.append({"context": name, "exit_code": 2 if index == 2 else 1, "report_path": path})
    output = tmp_path / "consolidated.html"
    assert consolidate(entries, output) == "ERROR"
    html = output.read_text(encoding="utf-8")
    for name in ("cluster-a", "cluster-b", "unreachable"):
        assert name in html
    assert "PLUTO-TABLE-cluster-a" in html and "PLUTO-TABLE-cluster-b" in html
    assert "STORED-INCONSISTENT" in html
    assert "No se obtuvo un reporte" in html
    assert "iframe" not in html and "src=" not in html
    assert html.count("<!doctype") == 1
    assert html.count('id="cluster-') == 3


def test_reject_wrong_context_and_escape_input(tmp_path):
    path = tmp_path / "report.json"
    make_report(path, "other")
    output = tmp_path / "consolidated.html"
    assert consolidate([{"context": "<script>attack</script>", "exit_code": 0, "report_path": path}], output) == "ERROR"
    text = output.read_text(encoding="utf-8")
    assert "<script>" not in text and "&lt;script&gt;" in text


@pytest.mark.parametrize("bad", ["not-json", '{"cluster": "ctx", "overall_status": "PASS"}'])
def test_bad_json_does_not_hide_context(tmp_path, bad):
    path = tmp_path / "report.json"
    path.write_text(bad, encoding="utf-8")
    output = tmp_path / "all.html"
    assert consolidate([{"context": "ctx", "exit_code": 0, "report_path": path}], output) == "ERROR"


def test_batch_enumerates_contexts_keeps_failures_and_uses_unique_directories(tmp_path, monkeypatch):
    calls = []
    def runner(command, **kwargs):
        calls.append(command)
        if command[0] == "kubectl":
            assert command == ["kubectl", "config", "get-contexts", "-o", "name"]
            return SimpleNamespace(returncode=0, stdout="a/b\na:b\nunreachable\na/b\n")
        context = command[command.index("--context") + 1]
        directory = Path(command[command.index("--output") + 1])
        assert kwargs["shell"] is False
        assert command[command.index("--format") + 1] == "all"
        if context == "unreachable":
            raise subprocess.TimeoutExpired(command, 1)
        make_report(directory / "report.json", context)
        return SimpleNamespace(returncode=1)
    monkeypatch.setattr(batch.subprocess, "run", runner)
    assert batch.main(["--target-version", "1.35.9", "--output", str(tmp_path), "--include-instances"]) == 2
    run_dir = next(tmp_path.iterdir())
    manifest = read_json(run_dir / "contexts.json")
    assert len(manifest) == 3
    assert manifest[-1]["exit_code"] == 124
    assert len({Path(e["report_path"]).parent for e in manifest}) == 3
    assert "unreachable" in (run_dir / "consolidated.html").read_text(encoding="utf-8")
    assert len(calls) == 4
    # A second invocation must not reuse this run's JSONs.
    assert batch.main(["--target", "1.35.9", "--context", "a/b", "--output", str(tmp_path)]) == 1
    assert len(list(tmp_path.iterdir())) == 2


def test_batch_rejects_override_of_individual_output_format(tmp_path):
    assert batch.main(["--target", "1.35.9", "--context", "ctx", "--format", "html", "--output", str(tmp_path)]) == 2
    assert not list(tmp_path.iterdir())


def test_timeout_marks_existing_detail_incomplete(tmp_path):
    path = tmp_path / "report.json"
    make_report(path, "ctx")
    output = tmp_path / "all.html"
    assert consolidate([{"context": "ctx", "exit_code": 124, "report_path": path}], output) == "ERROR"
    assert "puede ser parcial" in output.read_text(encoding="utf-8")
