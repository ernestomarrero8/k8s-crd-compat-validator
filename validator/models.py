"""Small, JSON-serializable evidence model shared by all checks."""
from dataclasses import asdict, dataclass, field

STATES = ("PASS", "UNKNOWN", "WARN", "FAIL", "ERROR")
SEVERITIES = ("INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL")
DOC = "https://v1-35.docs.kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/"
SCHEMA_SOURCE = DOC + "custom-resource-definitions/"
VERSION_SOURCE = DOC + "custom-resource-definition-versioning/"


@dataclass
class Finding:
    rule_id: str
    category: str
    status: str
    severity: str
    description: str
    evidence: dict = field(default_factory=dict)
    recommendation: str = "Revisar la evidencia antes del upgrade."
    source: str = SCHEMA_SOURCE
    relation: str = "preexisting"
    validation_type: str = "static"
    limitations: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def finding(rule_id, category, status, description, *, severity=None, **kwargs):
    return Finding(rule_id, category, status,
                   severity or {"PASS": "INFO", "UNKNOWN": "INFO", "WARN": "MEDIUM",
                                "FAIL": "HIGH", "ERROR": "HIGH"}[status], description, **kwargs)


def aggregate(findings):
    return max((f.status for f in findings), key=STATES.index, default="UNKNOWN")
