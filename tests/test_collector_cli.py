import json
import subprocess
from types import SimpleNamespace
from pathlib import Path
import pytest
from validator.collector import Collector, CollectionError, crd_items, read_json
from validator.cli import main
from validator.version import Version, upgrade_path

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("value", ["1.35.9", "v1.35.9", "v1.35.9-aks.1", "v1.35.9+build.2"])
def test_versions(value):
    assert str(Version.parse(value)) == "1.35.9"


@pytest.mark.parametrize("value", ["1..35.9", "1.35", "1.035.9", "1.35.9garbage", "1.35.9-rc.1", "", None])
def test_invalid_versions(value):
    with pytest.raises(ValueError):
        Version.parse(value)


def test_upgrade_path():
    assert upgrade_path(Version.parse("1.33.8"), Version.parse("1.35.9"))["intermediate_minors"] == ["1.34"]
    for target in ("1.34.8", "1.34.7", "1.33.9"):
        with pytest.raises(ValueError):
            upgrade_path(Version.parse("1.34.8"), Version.parse(target))


def response(data, code=0, error=""):
    return SimpleNamespace(returncode=code, stdout=json.dumps(data), stderr=error)


def test_detect_server_not_client_version():
    calls = []
    def runner(cmd, **kwargs):
        if cmd[0] == "pluto":
            return SimpleNamespace(returncode=0, stdout="No output to display", stderr="")
        calls.append(cmd)
        assert kwargs["shell"] is False
        return response({"clientVersion": {"gitVersion": "v1.36.0"}, "serverVersion": {"gitVersion": "v1.34.8"}})
    client = Collector("production", runner=runner)
    assert str(client.version()) == "1.34.8"
    assert "production" in calls[0]


def test_pin_active_context():
    calls = []
    def runner(cmd, **kwargs):
        if cmd[0] == "pluto":
            return SimpleNamespace(returncode=0, stdout="No output to display", stderr="")
        calls.append(cmd)
        if "current-context" in cmd:
            return SimpleNamespace(returncode=0, stdout="production\n", stderr="")
        return response({"serverVersion": {"gitVersion": "v1.34.8"}})
    client = Collector(runner=runner)
    assert client.current_context() == "production"
    client.version()
    assert calls[1][2:4] == ["--context", "production"]


def test_rbac_error_is_sanitized():
    collector = Collector(runner=lambda *a, **k: response({}, 1, "Forbidden bearer VERY_SECRET_TOKEN"))
    with pytest.raises(CollectionError) as error:
        collector.crds()
    assert error.value.code == "forbidden"
    assert "VERY_SECRET" not in str(error.value)


def test_invalid_json_from_kubectl():
    collector = Collector(runner=lambda *a, **k: SimpleNamespace(returncode=0, stdout="invalid", stderr=""))
    with pytest.raises(CollectionError, match="JSON"):
        collector.version()


def test_timeout():
    def runner(*args, **kwargs):
        raise subprocess.TimeoutExpired("kubectl", 1)
    with pytest.raises(CollectionError) as error:
        Collector(runner=runner).version()
    assert error.value.code == "timeout"


def test_pagination_and_limit_and_versions():
    calls = []
    def runner(cmd, **kwargs):
        if cmd[0] == "pluto":
            return SimpleNamespace(returncode=0, stdout="No output to display", stderr="")
        calls.append(cmd)
        return response({"items": [{"apiVersion": "example.com/v1", "spec": {"private": "hidden"}}],
                         "metadata": {"continue": "a+b/="}})
    client = Collector(runner=runner)
    summary, objects = client.instances("example.com", "v1", "widgets", max_pages=2, max_instances=2)
    assert summary["count_observed"] == 2
    assert not summary["complete"]
    assert summary["response_versions"] == ["example.com/v1"]
    assert "continue=a%2Bb%2F%3D" in calls[1][-1]
    assert "hidden" not in repr(summary)
    assert len(objects) == 2
    assert all("get" in cmd and "--raw" in cmd for cmd in calls)


def test_query_budget():
    client = Collector(max_queries=1, runner=lambda *a, **k: response({"serverVersion": {"gitVersion": "v1.34.8"}}))
    client.version()
    with pytest.raises(CollectionError) as error:
        client.version()
    assert error.value.code == "query_limit"


def test_offline_does_not_call_subprocess_or_network(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Offline must not access network/cluster")
    monkeypatch.setattr(subprocess, "run", forbidden)
    import urllib.request
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", forbidden)
    assert main(["--input", str(ROOT / "fixtures/valid-crds.json"), "--current", "1.34.8", "--target", "1.35.9", "--include-instances", "--output", str(tmp_path)]) == 0
    report = read_json(tmp_path / "report.json")
    assert report["kubectl_queries"] == 0
    assert report["crds"][0]["status"] == "UNKNOWN"
    assert all((tmp_path / f"report.{ext}").exists() for ext in ("json", "md", "html"))


def test_strict_unknown_fails_ci(tmp_path):
    assert main(["--input", str(ROOT / "fixtures/valid-crds.json"), "--current", "1.34.8", "--target", "1.35.9", "--fail-on", "FAIL,WARN,UNKNOWN", "--output", str(tmp_path)]) == 1


@pytest.mark.parametrize("extra", [["--target", "1..35.9"], ["--target", "1.33.0"], ["--target", "1.35.9", "--context", "prod"], ["--target", "1.35.9", "--verify-sources"]])
def test_invalid_cli(tmp_path, extra):
    assert main(["--input", str(ROOT / "fixtures/valid-crds.json"), "--current", "1.34.8", "--output", str(tmp_path)] + extra) == 2


def test_invalid_json_input(tmp_path):
    file = tmp_path / "invalid.json"
    file.write_text("{bad", encoding="utf-8")
    assert main(["--input", str(file), "--current", "1.34.8", "--target", "1.35.9"]) == 2


def test_utf16_export(tmp_path, crd):
    file = tmp_path / "crds.json"
    file.write_text(json.dumps(crd), encoding="utf-16")
    assert crd_items(read_json(file)) == [crd]


def test_live_cli_uses_only_read_commands(tmp_path, crd, monkeypatch):
    calls = []
    def runner(cmd, **kwargs):
        if cmd[0] == "pluto":
            return SimpleNamespace(returncode=0, stdout="No output to display", stderr="")
        calls.append(cmd)
        if "version" in cmd:
            return response({"serverVersion": {"gitVersion": "v1.34.8"}})
        if "crds" in cmd:
            return response({"kind": "List", "items": [crd]})
        if "clusterserviceversions.operators.coreos.com" in cmd:
            return response({}, 1, "NotFound")
        raise AssertionError(cmd)
    monkeypatch.setattr(subprocess, "run", runner)
    assert main(["--context", "source", "--target", "1.35.9", "--output", str(tmp_path)]) == 0
    assert len(calls) == 3
    assert all(set(cmd).isdisjoint({"apply", "create", "patch", "delete", "replace", "edit"}) for cmd in calls)


def test_target_context_mismatch_aborts(tmp_path, crd, monkeypatch):
    def runner(cmd, **kwargs):
        if cmd[0] == "pluto":
            return SimpleNamespace(returncode=0, stdout="No output to display", stderr="")
        if "version" in cmd:
            return response({"serverVersion": {"gitVersion": "v1.34.8"}})
        return response({"kind": "List", "items": [crd]})
    monkeypatch.setattr(subprocess, "run", runner)
    assert main(["--context", "source", "--target", "1.35.9", "--target-context", "target", "--output", str(tmp_path)]) == 2


def test_mixed_fixture_exercises_all_intended_categories(tmp_path):
    assert main(["--input", str(ROOT / "fixtures/mixed-crds.json"), "--current", "1.34.8", "--target", "1.35.9", "--output", str(tmp_path)]) == 1
    report = read_json(tmp_path / "report.json")
    assert report["summary"]["states"] == {"PASS": 0, "UNKNOWN": 1, "WARN": 2, "FAIL": 3, "ERROR": 0}
    assert not any(f["rule_id"] == "STRUCTURE-INVALID" for c in report["crds"] for f in c["findings"])


def test_target_context_and_instances_full_cli(tmp_path, crd, monkeypatch):
    calls = []
    def runner(cmd, **kwargs):
        if cmd[0] == "pluto":
            return SimpleNamespace(returncode=0, stdout="No output to display", stderr="")
        calls.append(cmd)
        context = cmd[cmd.index("--context") + 1]
        if "version" in cmd:
            return response({"serverVersion": {"gitVersion": "v1.35.9" if context == "target" else "v1.34.8"}})
        if "crds" in cmd:
            return response({"kind": "List", "items": [crd]})
        if "clusterserviceversions.operators.coreos.com" in cmd:
            return response({"items": []})
        if "--raw" in cmd:
            if context == "target":
                return response({"resources": [{"name": "widgets"}]})
            return response({"items": [{"apiVersion": "example.com/v1alpha1", "spec": {"replicas": 2}}], "metadata": {}})
        raise AssertionError(cmd)
    monkeypatch.setattr(subprocess, "run", runner)
    assert main(["--context", "source", "--target", "1.35.9", "--target-context", "target", "--include-instances", "--output", str(tmp_path)]) == 0
    report = read_json(tmp_path / "report.json")
    assert report["kubectl_queries"] == len(calls)
    findings = {f["rule_id"]: f for f in report["crds"][0]["findings"]}
    assert findings["TARGET-DISCOVERY"]["status"] == "PASS"
    assert findings["INSTANCES-READ"]["evidence"]["count_observed"] == 1
    assert findings["TARGET-WRITE-UNTESTED"]["status"] == "UNKNOWN"


def test_no_credentials_in_any_generated_report(tmp_path, crd, monkeypatch):
    crd["metadata"]["annotations"] = {"private-api-key": "DO_NOT_EXPOSE"}
    def runner(cmd, **kwargs):
        if cmd[0] == "pluto":
            return SimpleNamespace(returncode=0, stdout="No output to display", stderr="")
        if "version" in cmd:
            return response({"serverVersion": {"gitVersion": "v1.34.8"}})
        if "crds" in cmd:
            return response({"kind": "List", "items": [crd]})
        if "--raw" in cmd:
            return response({"items": [{"apiVersion": "example.com/v1alpha1", "spec": {"replicas": "DO_NOT_EXPOSE"}}], "metadata": {}})
        return response({}, 1, "Forbidden credentials DO_NOT_EXPOSE")
    monkeypatch.setattr(subprocess, "run", runner)
    assert main(["--context", "test", "--target", "1.35.9", "--include-instances", "--output", str(tmp_path)]) == 0
    for path in tmp_path.iterdir():
        assert "DO_NOT_EXPOSE" not in path.read_text(encoding="utf-8")


@pytest.mark.parametrize("pluto_code,expected", [(3, 1), (1, 2)])
def test_live_pluto_result_affects_cli_and_preserves_crd_report(tmp_path, crd, monkeypatch, pluto_code, expected):
    def runner(cmd, **kwargs):
        if cmd[0] == "pluto":
            assert cmd[cmd.index("--kube-context") + 1] == "source"
            assert cmd[cmd.index("--target-versions") + 1] == "k8s=v1.35.9"
            return SimpleNamespace(returncode=pluto_code, stdout="NAME NAMESPACE\nold-resource default", stderr="")
        if "version" in cmd:
            return response({"serverVersion": {"gitVersion": "v1.34.8"}})
        if "crds" in cmd:
            return response({"kind": "List", "items": [crd]})
        return response({"items": []})
    monkeypatch.setattr(subprocess, "run", runner)
    assert main(["--context", "source", "--target", "1.35.9", "--output", str(tmp_path)]) == expected
    report = read_json(tmp_path / "report.json")
    assert report["summary"]["total_crds"] == 1
    assert report["pluto"]["exit_code"] == pluto_code
    assert report["knowledge"]["coverage_catalog_version"]
    if pluto_code == 3:
        assert "old-resource" in (tmp_path / "report.html").read_text(encoding="utf-8")
