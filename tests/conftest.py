from copy import deepcopy
from pathlib import Path
import pytest
from validator.collector import read_json
from validator.version import Version
from validator.rule_engine import RuleEngine
from validator.crd_analyzer import analyze

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def crd():
    return deepcopy(read_json(ROOT / "fixtures" / "valid-crds.json")["items"][0])


@pytest.fixture
def inspect_crd():
    def run(crd, **kwargs):
        return analyze(crd, Version.parse("1.34.8"), Version.parse("1.35.9"), RuleEngine(), **kwargs)
    return run
