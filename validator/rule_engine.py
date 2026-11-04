"""Versioned declarative JSON predicates; never eval/import external code."""
from pathlib import Path
import re
import hashlib
import json
from urllib.parse import urlsplit
from .collector import read_json
from .models import finding, STATES, SEVERITIES
from .version import Version


def safe_source(url):
    try:
        value = urlsplit(url)
        return value.scheme == "https" and bool(value.hostname) and not (value.username or value.password)
    except (TypeError, ValueError):
        return False


def select(data, path):
    """Dot-separated path; * selects children, ** recursively selects descendants."""
    parts = path.split(".") if path else []

    def walk(node, index):
        if index == len(parts):
            return [node]
        part = parts[index]
        children = list(node.values()) if isinstance(node, dict) else node if isinstance(node, list) else []
        if part == "**":
            values = walk(node, index + 1)
            for child in children:
                values.extend(walk(child, index))
            return values
        if part == "*":
            return [v for child in children for v in walk(child, index + 1)]
        if isinstance(node, dict) and part in node:
            return walk(node[part], index + 1)
        return []
    return walk(data, 0)


def validate_condition(condition, depth=0):
    if not isinstance(condition, dict) or depth > 20:
        raise ValueError("Condición de regla inválida o demasiado profunda.")
    if len(condition) == 1 and ("all" in condition or "any" in condition):
        children = condition.get("all", condition.get("any"))
        if not isinstance(children, list) or not children:
            raise ValueError("all/any requiere una lista no vacía.")
        for child in children:
            validate_condition(child, depth + 1)
        return
    if set(condition) - {"path", "op", "value"} or not isinstance(condition.get("path"), str):
        raise ValueError("Condición requiere path y op; no admite código.")
    op = condition.get("op")
    if op not in ("exists", "absent", "equals", "contains", "count_gt"):
        raise ValueError("Operador de regla no soportado.")
    if op in ("equals", "contains", "count_gt") and "value" not in condition:
        raise ValueError("La condición requiere value.")
    if op == "count_gt" and type(condition["value"]) is not int:
        raise ValueError("count_gt requiere un entero.")


def matches(data, condition):
    if "all" in condition:
        return all(matches(data, c) for c in condition["all"])
    if "any" in condition:
        return any(matches(data, c) for c in condition["any"])
    values = select(data, condition["path"])
    op, expected = condition["op"], condition.get("value")
    if op == "exists":
        return bool(values)
    if op == "absent":
        return not values
    if op == "equals":
        return any(v == expected for v in values)
    if op == "contains":
        return any(expected in v for v in values if isinstance(v, list))
    return len(values) > expected


class RuleEngine:
    def __init__(self, extra_path=None):
        builtin = Path(__file__).resolve().parent.parent / "rules" / "kubernetes.json"
        paths = [builtin]
        if extra_path:
            extra = Path(extra_path)
            candidates = sorted(extra.glob("*.json")) if extra.is_dir() else [extra]
            if not candidates:
                raise ValueError("El directorio de reglas no contiene archivos JSON.")
            paths += [p for p in candidates if p.resolve() != builtin]
        self.rules = []
        self.catalogs = []
        seen = set()
        for path in paths:
            if path.resolve() == builtin.with_name("coverage.json"):
                continue
            self.catalogs.append({"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
            data = read_json(path)
            if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("rules"), list):
                raise ValueError("Archivo de reglas requiere schema_version: 1 y rules: [].")
            self.catalogs[-1]["catalog_version"] = data.get("catalog_version", "unversioned")
            for rule in data["rules"]:
                self.validate(rule)
                if rule["rule_id"] in seen:
                    raise ValueError("Identificador de regla duplicado.")
                seen.add(rule["rule_id"])
                self.rules.append(rule)

    def provenance(self):
        return {"files": self.catalogs, "rules_sha256": hashlib.sha256(json.dumps(self.rules, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()}

    @staticmethod
    def validate(rule):
        required = {"rule_id", "description", "category", "severity", "status", "source", "recommendation", "condition", "applicability", "relation", "validation_type", "evidence"}
        if not isinstance(rule, dict) or not required <= rule.keys():
            raise ValueError("Regla incompleta.")
        if not isinstance(rule["rule_id"], str) or not re.fullmatch(r"[A-Z0-9-]+", rule["rule_id"]):
            raise ValueError("rule_id debe contener mayúsculas, dígitos o guiones.")
        if rule["status"] not in STATES or rule["severity"] not in SEVERITIES or not safe_source(rule["source"]):
            raise ValueError("Estado, severidad o fuente HTTPS de regla inválidos.")
        for key in ("description", "category", "recommendation", "evidence"):
            if not isinstance(rule[key], str) or not rule[key]:
                raise ValueError("Metadatos de regla inválidos.")
        if rule["validation_type"] != "static" or rule["relation"] not in ("preexisting", "upgrade", "limitation", "documented", "tested", "release_change"):
            raise ValueError("Tipo o relación de regla no soportados.")
        app = rule["applicability"]
        allowed = {"current_min", "current_max", "target_min", "target_max", "crosses"}
        if not isinstance(app, dict) or not app or set(app) - allowed:
            raise ValueError("Rango de aplicabilidad inválido.")
        for value in app.values():
            Version.parse(value)
        for prefix in ("current", "target"):
            if prefix + "_min" in app and prefix + "_max" in app and Version.parse(app[prefix + "_min"]) > Version.parse(app[prefix + "_max"]):
                raise ValueError("Rango de aplicabilidad invertido.")
        if "limitations" in rule and (not isinstance(rule["limitations"], list) or any(not isinstance(x, str) for x in rule["limitations"])):
            raise ValueError("limitations debe ser una lista de texto.")
        validate_condition(rule["condition"])

    def evaluate(self, crd, current, target):
        findings = []
        for rule in self.rules:
            app = rule["applicability"]
            applies = all((current if key.startswith("current") else target) >= Version.parse(value)
                          if key.endswith("min") else (current if key.startswith("current") else target) <= Version.parse(value)
                          for key, value in app.items() if key != "crosses")
            if "crosses" in app:
                applies = applies and current < Version.parse(app["crosses"]) <= target
            if applies and matches(crd, rule["condition"]):
                findings.append(finding(rule["rule_id"], rule["category"], rule["status"], rule["description"],
                    severity=rule["severity"], source=rule["source"], recommendation=rule["recommendation"],
                    relation=rule["relation"], validation_type=rule["validation_type"],
                    evidence={"basis": rule["evidence"], "applicability": app, "condition_matched": True},
                    limitations=rule.get("limitations", [])))
        return findings
