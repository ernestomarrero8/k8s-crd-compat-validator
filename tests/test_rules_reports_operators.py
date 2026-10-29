from copy import deepcopy
from pathlib import Path
import json
import hashlib
from html.parser import HTMLParser
import pytest
from validator.rule_engine import RuleEngine, matches
from validator.version import Version
from validator.operator_validator import OperatorCatalog, analyze as operator_analyze
from validator.report_generator import build_report, write_reports, html, markdown
from validator.models import finding
from validator.cli import exit_code
from validator.crd_analyzer import analyze_target, analyze_instances
from validator.collector import Collector, CollectionError


def test_crossing_rule_only_fires_on_crossing(crd):
    engine = RuleEngine()
    forward = engine.evaluate(crd, Version.parse("1.34.8"), Version.parse("1.35.9"))
    patch = engine.evaluate(crd, Version.parse("1.35.8"), Version.parse("1.35.9"))
    assert "K135-CONDITION-GENERATION" in {f.rule_id for f in forward}
    assert not patch


def test_external_rule_needs_no_python_changes(tmp_path, crd):
    rule = deepcopy(RuleEngine().rules[0])
    rule.update(rule_id="CUSTOM-REVIEW", condition={"path": "spec.scope", "op": "equals", "value": "Namespaced"}, status="UNKNOWN")
    file = tmp_path / "custom.json"
    file.write_text(json.dumps({"schema_version": 1, "rules": [rule]}), encoding="utf-8")
    result = RuleEngine(file).evaluate(crd, Version.parse("1.34.8"), Version.parse("1.35.9"))
    assert "CUSTOM-REVIEW" in {f.rule_id for f in result}


@pytest.mark.parametrize("change", [
    {"condition": {"path": "spec", "op": "eval", "value": "danger"}},
    {"source": "javascript:alert(1)"},
    {"status": "COMPATIBLE"},
    {"applicability": {"target_min": "1.36.0", "target_max": "1.35.0"}},
    {"limitations": "not-list"},
])
def test_bad_rules_rejected(tmp_path, change):
    rule = deepcopy(RuleEngine().rules[0])
    rule.update(rule_id="CUSTOM-INVALID", **change)
    file = tmp_path / "rules.json"
    file.write_text(json.dumps({"schema_version": 1, "rules": [rule]}), encoding="utf-8")
    with pytest.raises(ValueError):
        RuleEngine(file)


def test_duplicate_rule_id_rejected(tmp_path):
    file = tmp_path / "duplicate.json"
    file.write_text(json.dumps({"schema_version": 1, "rules": [RuleEngine().rules[0]]}), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicado"):
        RuleEngine(file)


def test_predicate_all_any():
    assert matches({"a": [1, 2]}, {"all": [{"path": "a.*", "op": "count_gt", "value": 1}, {"path": "b", "op": "absent"}]})
    assert matches({"a": [1, 2]}, {"any": [{"path": "a", "op": "contains", "value": 2}, {"path": "b", "op": "exists"}]})


def test_report_escape_and_all_formats(tmp_path, crd, inspect_crd):
    result = inspect_crd(crd)
    result["name"] = "<script>alert(1)</script> | [link](javascript:bad)"
    report = build_report("test", Version.parse("1.34.8"), Version.parse("1.35.9"), {}, [result], [])
    files = write_reports(report, tmp_path)
    assert len(files) == 3
    output = html(report)
    assert "<script>" not in output
    assert "&lt;script&gt;" in output
    assert "\\[link\\]" in markdown(report)
    class Audit(HTMLParser):
        tags = []
        def handle_starttag(self, tag, attrs):
            self.tags.append(tag)
    parser = Audit()
    parser.feed(output)
    assert "table" in parser.tags and "details" in parser.tags
    assert "script" not in parser.tags and "iframe" not in parser.tags
    assert json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))["summary"]["total_crds"] == 1


def test_exit_code_looks_at_all_findings_not_only_worst_status():
    report = {"global_findings": [], "crds": [{"status": "FAIL", "findings": [{"status": "FAIL"}, {"status": "UNKNOWN"}]}]}
    assert exit_code(report, {"UNKNOWN"}) == 1
    report["global_findings"].append({"status": "ERROR"})
    assert exit_code(report, set()) == 2


def catalogue(tmp_path, **updates):
    entry = {"crds": ["widgets.example.com"], "operator": "example-operator", "operator_version": "2.0.0",
             "kubernetes_min": "1.34.0", "kubernetes_max": "1.35.99", "source": "https://example.com/official-support",
             "source_sha256": hashlib.sha256(b"test vendor support document").hexdigest(),
             "reviewed_on": "2026-10-29", "evidence": "TEST FIXTURE ONLY; not a real support matrix."}
    entry.update(updates)
    file = tmp_path / "operators.json"
    file.write_text(json.dumps([entry]), encoding="utf-8")
    return file


def test_operator_documented_support_and_mismatch(tmp_path, crd):
    catalog = OperatorCatalog(catalogue(tmp_path))
    findings = operator_analyze(crd, Version.parse("1.35.9"), catalog=catalog)
    support = next(f for f in findings if f.rule_id == "OPERATOR-SUPPORT")
    assert support.status == "PASS" and support.relation == "documented"
    crd["metadata"]["labels"]["app.kubernetes.io/version"] = "1.0.0"
    assert next(f for f in operator_analyze(crd, Version.parse("1.35.9"), catalog=catalog) if f.rule_id == "OPERATOR-SUPPORT").status == "UNKNOWN"


def test_outside_matrix_warn_not_proven_fail(tmp_path, crd):
    catalog = OperatorCatalog(catalogue(tmp_path, kubernetes_max="1.34.99"))
    support = next(f for f in operator_analyze(crd, Version.parse("1.35.9"), catalog=catalog) if f.rule_id == "OPERATOR-SUPPORT")
    assert support.status == "WARN"


def test_source_hash_changed_is_unknown(tmp_path, crd):
    catalog = OperatorCatalog(catalogue(tmp_path), verify_sources=True)
    catalog.cache["https://example.com/official-support"] = "changed"
    support = next(f for f in operator_analyze(crd, Version.parse("1.35.9"), catalog=catalog) if f.rule_id == "OPERATOR-SUPPORT")
    assert support.status == "UNKNOWN"


def test_olm_owned_identification(crd):
    class Live:
        def get(self, *args, **kwargs):
            return {"items": [{"spec": {"displayName": "Operator", "version": "3.0.0", "minKubeVersion": "1.30.0",
                                       "customresourcedefinitions": {"owned": [{"name": crd["metadata"]["name"]}]}}}]}
    identity = next(f for f in operator_analyze(crd, Version.parse("1.35.9"), Live()) if f.rule_id == "OPERATOR-IDENTITY")
    assert any(c["basis"] == "olm_owned" and c["version"] == "3.0.0" for c in identity.evidence["candidates"])


def test_target_read_does_not_claim_admission(crd):
    class Target:
        def _run(self, args):
            assert args[:2] == ["get", "--raw"]
            return {"resources": [{"name": "widgets"}]}
    findings = analyze_target(crd, Target(), {crd["metadata"]["name"]: crd}, None)
    states = {f.rule_id: f.status for f in findings}
    assert states["TARGET-DISCOVERY"] == "PASS"
    assert states["TARGET-WRITE-UNTESTED"] == "UNKNOWN"


def test_target_definition_mismatch(crd):
    different = deepcopy(crd)
    different["spec"]["versions"][0]["served"] = False
    assert analyze_target(crd, object(), {crd["metadata"]["name"]: different}, None)[0].status == "UNKNOWN"
    assert analyze_target(crd, object(), {}, None)[0].status == "UNKNOWN"


def test_instance_count_and_partial_result(crd):
    class Live:
        def instances(self, *args, **kwargs):
            return {"count_observed": 1, "complete": False, "requested_version": "example.com/v1alpha1", "response_versions": ["example.com/v1alpha1"]}, [{"spec": {"replicas": -1, "private": "DO_NOT_PRINT"}}]
    finding_ = analyze_instances(crd, Live(), {})[0]
    assert finding_.status == "WARN"
    assert finding_.evidence["objects_with_possible_schema_issues"] == 1
    assert finding_.evidence["persisted_versions"] == "UNKNOWN"
    assert "DO_NOT_PRINT" not in repr(finding_.to_dict())


def test_collector_rejects_mutation():
    with pytest.raises(ValueError, match="solo admite"):
        Collector()._run(["apply", "-f", "example.json"])
    with pytest.raises(ValueError, match="solo admite"):
        Collector()._run(["config", "use-context", "other"])
