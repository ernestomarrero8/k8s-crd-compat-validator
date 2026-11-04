import json
import subprocess
from types import SimpleNamespace
import pytest
from validator.coverage import CoverageCatalog
from validator.version import Version
from validator.rule_engine import RuleEngine
from validator import pluto
from validator.conversion_validator import analyze
from validator.report_generator import build_report, write_reports
from validator.cli import exit_code


def test_future_target_keeps_change_rules_but_is_unreviewed(crd):
    current, target = Version.parse("1.34.8"), Version.parse("1.36.1")
    assert "K135-CONDITION-GENERATION" in {r.rule_id for r in RuleEngine().evaluate(crd, current, target)}
    observation = CoverageCatalog().assess(current, target)
    assert observation.status == "UNKNOWN"
    assert [s["status"] for s in observation.evidence["steps"]] == ["partial", "unreviewed"]
    assert CoverageCatalog().protocols(target) is None


def test_reviewed_no_changes_differs_from_unknown(tmp_path):
    data = CoverageCatalog().data
    record = data["reviews"][0]
    record.update(current_min="1.35.0", current_max="1.35.99", target_min="1.36.0", target_max="1.36.99", status="reviewed_no_changes")
    path = tmp_path / "coverage.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    catalog = CoverageCatalog(path)
    assert catalog.assess(Version.parse("1.35.9"), Version.parse("1.36.1")).status == "PASS"
    assert catalog.assess(Version.parse("1.35.9"), Version.parse("1.37.1")).status == "UNKNOWN"
    original_hash = catalog.sha256
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    assert CoverageCatalog(path).sha256 != original_hash


def test_protocols_unreviewed_are_not_assumed(crd):
    crd["spec"]["conversion"] = {"strategy": "Webhook", "webhook": {"conversionReviewVersions": ["v1"], "clientConfig": {"url": "https://example.com/convert"}}}
    assert next(f for f in analyze(crd) if f.rule_id == "CONVERSION-REVIEW").status == "UNKNOWN"


def test_builtin_rules_directory_with_coverage():
    assert RuleEngine("rules").provenance() == RuleEngine().provenance()


@pytest.mark.parametrize("code,status", [(0,"PASS"),(2,"WARN"),(3,"FAIL"),(4,"WARN"),(1,"ERROR"),(9,"ERROR")])
def test_pluto_exit_statuses_and_exact_context_target(code, status, monkeypatch):
    monkeypatch.setenv("PLUTO_ONLY_SHOW_REMOVED", "true")
    def runner(command, **kwargs):
        assert command[:5] == ["pluto", "detect-all-in-cluster", "-o", "wide", "--kube-context"]
        assert command[5] == "production"
        assert command[7] == "k8s=v1.36.1"
        assert kwargs["shell"] is False and kwargs["timeout"] == 12
        assert not any(k.startswith("PLUTO_") for k in kwargs["env"])
        return SimpleNamespace(returncode=code, stdout="NAME NAMESPACE\nwidget default\n", stderr="secret=HIDDEN")
    result, finding = pluto.run("production", Version.parse("1.36.1"), 12, runner=runner)
    assert result["status"] == finding.status == status
    assert "HIDDEN" not in json.dumps(result)
    assert result["exit_code"] == code


@pytest.mark.parametrize("error", [FileNotFoundError(), subprocess.TimeoutExpired("pluto", 1), OSError()])
def test_pluto_failure_does_not_abort_report(error):
    def runner(*args, **kwargs):
        raise error
    result, finding = pluto.run("source", Version.parse("1.35.9"), runner=runner)
    assert result["status"] == "ERROR"
    report = build_report("source", "1.34.8", "1.35.9", {}, [], [finding])
    assert exit_code(report, set()) == 2


def test_pluto_offline_never_launches_process():
    def runner(*args, **kwargs):
        pytest.fail("Offline launched Pluto")
    result, finding = pluto.run("offline", Version.parse("1.35.9"), offline=True, runner=runner)
    assert not result["executed"] and finding.status == "UNKNOWN"


def test_pluto_table_in_all_reports_escaped(tmp_path):
    result, finding = pluto.run("source", Version.parse("1.35.9"), runner=lambda *a, **k: SimpleNamespace(returncode=2, stdout="NAME NAMESPACE\n<script>evil</script> default\ntoken=HIDDEN", stderr=""))
    report = build_report("source", "1.34.8", "1.35.9", {}, [], [finding])
    report["pluto"] = result
    report["knowledge"] = RuleEngine().provenance()
    write_reports(report, tmp_path)
    for path in tmp_path.iterdir():
        text = path.read_text(encoding="utf-8")
        assert "NAME NAMESPACE" in text
        assert "HIDDEN" not in text
        if path.suffix != ".json":
            assert "<script>" not in text


def test_invalid_coverage_rejected(tmp_path):
    path = tmp_path / "coverage.json"
    data = CoverageCatalog().data
    data["conversion_protocols"][0]["target_min"] = "1..35"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="cobertura"):
        CoverageCatalog(path)
