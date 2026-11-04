"""Reviewed support records: tested-only matrices never imply incompatibility."""
from datetime import date
import hashlib
import json
from pathlib import Path
import re
from .collector import read_json
from .models import finding, aggregate
from .rule_engine import safe_source

ROOT = Path(__file__).resolve().parents[1] / "catalogs/operators"


def release(value):
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)(?:\+[\w.-]+|-(?:distroless|fips|aks|azure)[\w.-]*)?", str(value))
    return tuple(map(int, match.groups())) if match else None


def bound(value, upper=False):
    parts = str(value).removeprefix("v").split(".")
    if not 1 <= len(parts) <= 3:
        raise ValueError("Versión/rango de catálogo inválido.")
    result, wildcard = [], False
    for part in parts + ["x"] * (3 - len(parts)):
        if part in ("x", "*"):
            wildcard = True
            result.append(float("inf") if upper else 0)
        elif part.isdigit() and not wildcard:
            result.append(int(part))
        else:
            raise ValueError("Wildcard o versión de catálogo inválidos.")
    return tuple(result)


def in_range(version, lower, upper):
    return bound(lower) <= version <= bound(upper, True)


class PlatformCatalog:
    def __init__(self, path=None):
        self.detectors = read_json(ROOT / "detectors.json")["products"]
        self.records, self.files = {}, []
        folder = Path(path) if path else ROOT
        paths = sorted(folder.glob("*.json")) if folder.is_dir() else [folder]
        if not paths:
            raise ValueError("Catálogo de plataformas vacío.")
        for file in paths:
            if file.name == "detectors.json":
                continue
            data = read_json(file)
            if not isinstance(data, dict) or not isinstance(data.get("product"), str) or not isinstance(data.get("versions"), list):
                raise ValueError("Catálogo de plataforma requiere product y versions.")
            self.files.append({"file": file.name, "catalog_version": data.get("catalog_version", "unversioned"),
                               "sha256": hashlib.sha256(file.read_bytes()).hexdigest()})
            for record in data["versions"]:
                try:
                    if not isinstance(record, dict) or not safe_source(record["source"]) or not record["evidence"]:
                        raise ValueError()
                    if record["matrix_type"] not in ("supported", "tested") or type(record["exclusive"]) is not bool:
                        raise ValueError()
                    if record["matrix_type"] == "tested" and record["exclusive"]:
                        raise ValueError()
                    if bound(record["version"]) > bound(record["version"], True) or bound(record["min_kubernetes"]) > bound(record["max_kubernetes"], True):
                        raise ValueError()
                    reviewed, expires = date.fromisoformat(record["reviewed_on"]), date.fromisoformat(record["valid_until"])
                    if reviewed > expires:
                        raise ValueError()
                    if record.get("end_of_support"):
                        date.fromisoformat(record["end_of_support"])
                except (KeyError, TypeError, ValueError):
                    raise ValueError("Registro de compatibilidad incompleto o inválido.") from None
            self.records.setdefault(data["product"], []).extend(data["versions"])

    def evaluate(self, product, version, target, source, today=None):
        today = today or date.today()
        observed, target_release = release(version), release(str(target))
        def result(id_, status, text, record=None):
            return finding(id_, "operator_compatibility", status, text,
                source=record["source"] if record else source, relation="documented" if record else "limitation",
                evidence={"product": product, "installed_version": version, "target": str(target), "matrix": record or {}},
                recommendation="Revisar la matriz oficial y actualizar el componente o completar evidencia antes del upgrade.")
        if not observed:
            return [result("OPERATOR-VERSION-UNKNOWN", "UNKNOWN", "No se determinó una versión de producto inequívoca; un chart, digest o tag mutable no demuestra versión efectiva.")]
        records = [r for r in self.records.get(product, []) if in_range(observed, r["version"], r["version"])]
        if len(records) != 1:
            return [result("OPERATOR-NO-MATRIX", "UNKNOWN", "No existe una única fila de matriz oficial revisada para esta versión.")]
        record = records[0]
        findings = []
        if record.get("end_of_support") and today > date.fromisoformat(record["end_of_support"]):
            findings.append(result("OPERATOR-END-OF-SUPPORT", "WARN", "Versión fuera de mantenimiento según la fecha oficial registrada.", record))
        if not date.fromisoformat(record["reviewed_on"]) <= today <= date.fromisoformat(record["valid_until"]):
            findings.append(result("OPERATOR-NO-MATRIX", "UNKNOWN", "La revisión de la matriz no está vigente para la fecha del análisis.", record))
        elif in_range(target_release, record["min_kubernetes"], record["max_kubernetes"]):
            findings.append(result("OPERATOR-COMPATIBLE", "PASS", "Objetivo dentro del rango documentado; consultar si la evidencia acredita soporte o pruebas upstream.", record))
        elif record["exclusive"]:
            findings.append(result("OPERATOR-NOT-COMPATIBLE", "FAIL", "Objetivo fuera del rango de soporte explícito del proveedor; no se recomienda este upgrade con la versión instalada.", record))
        else:
            findings.append(result("OPERATOR-NO-MATRIX", "UNKNOWN", "Objetivo fuera de las versiones probadas; esto no demuestra incompatibilidad.", record))
        return findings

    def provenance(self):
        return {"files": self.files, "detectors_sha256": hashlib.sha256(json.dumps(self.detectors, sort_keys=True).encode()).hexdigest()}
