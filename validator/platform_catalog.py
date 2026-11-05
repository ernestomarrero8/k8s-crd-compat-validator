"""Reviewed support records: tested-only matrices never imply incompatibility."""
from datetime import date
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import re
from .collector import read_json
from .models import finding
from .rule_engine import safe_source

ROOT = Path(__file__).resolve().parents[1] / "catalogs/operators"
SUPPORT_ROOT = ROOT.parent / "support"


VENDOR_PRODUCTS = {"Azure Disk CSI Driver", "Azure File CSI Driver", "Azure Key Vault CSI Driver", "Azure Key Vault Provider for Secrets Store CSI Driver", "Azure CNI"}


def release(value, product=None):
    suffix = r"|-[0-9]+" if product in VENDOR_PRODUCTS else ""
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)(?:\+[\w.-]+|-(?:distroless|fips|aks|azure)[\w.-]*" + suffix + r")?", str(value))
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
    def __init__(self, path=None, detectors_path=None):
        self.detectors = read_json(ROOT / "detectors.json")["products"]
        if detectors_path:
            aliases = read_json(detectors_path)
            if not isinstance(aliases, dict) or aliases.get("schema_version") != 1 or not isinstance(aliases.get("products"), list):
                raise ValueError("Aliases de detectores requiere schema_version: 1 y products: [].")
            for item in aliases["products"]:
                if not isinstance(item, dict):
                    raise ValueError("Alias de producto inválido.")
                definition = next((d for d in self.detectors if d["id"] == item.get("id")), None)
                if not definition or set(item) - {"id", "images", "charts"}:
                    raise ValueError("Alias de producto no reconocido.")
                for key in ("images", "charts"):
                    values = item.get(key, [])
                    if not isinstance(values, list) or any(not isinstance(v, str) or not v or any(c.isspace() for c in v) for v in values):
                        raise ValueError("Repositorios/charts de alias inválidos.")
                    definition[key] = sorted(set(definition[key]) | set(values))
                    definition["configured_" + key] = values
        self.ownership = read_json(ROOT / "ownership.json")["owners"]
        for definition in self.detectors:
            owners = [o for o in self.ownership if o["product_id"] == definition["id"]]
            definition["crd_groups"] = sorted({group for o in owners for group in o["groups"]})
            definition["crds"] = sorted(set(definition["crds"]) | {name for o in owners for name in o["crds"]})
        self.records, self.files, self.notes = {}, [], {}
        self.product_files = {}
        self.product_paths = {}
        folder = Path(path) if path else SUPPORT_ROOT
        paths = sorted(folder.glob("*.json")) if folder.is_dir() else [folder]
        if not paths:
            raise ValueError("Catálogo de plataformas vacío.")
        for file in paths:
            if file.name in ("detectors.json", "ownership.json"):
                continue
            data = read_json(file)
            if isinstance(data, dict) and "version" in data and "versions" not in data:
                data = {"product": data.get("product"), "catalog_version": data.get("catalog_version", "unversioned"), "versions": [data]}
            if not isinstance(data, dict) or not isinstance(data.get("product"), str) or not isinstance(data.get("versions"), list):
                raise ValueError("Catálogo de plataforma requiere product y versions.")
            self.notes[data["product"]] = {"source": data.get("source"), "limitations": data.get("limitations", [])}
            self.product_files.setdefault(data["product"], []).append(file.name)
            location = file.resolve()
            project = ROOT.parents[1]
            location = location.relative_to(project).as_posix() if location.is_relative_to(project) else str(location)
            self.product_paths.setdefault(data["product"], []).append(location)
            self.files.append({"file": file.name, "catalog_version": data.get("catalog_version", "unversioned"),
                               "path": location,
                               "sha256": hashlib.sha256(file.read_bytes()).hexdigest()})
            for record in data["versions"]:
                try:
                    if "supported_kubernetes" in record:
                        record["min_kubernetes"] = record["supported_kubernetes"]["min"]
                        record["max_kubernetes"] = record["supported_kubernetes"]["max"]
                        record["source"] = record.get("source_url", record.get("source"))
                        record.setdefault("matrix_type", "supported")
                        record.setdefault("exclusive", record["matrix_type"] == "supported")
                        record.setdefault("valid_until", (date.fromisoformat(record["reviewed_on"]) + timedelta(days=90)).isoformat())
                    record.setdefault("support_state", "supported")
                    if record["support_state"] not in ("supported", "eol", "unknown"):
                        raise ValueError()
                    if not isinstance(record, dict) or not safe_source(record["source"]) or not record["evidence"]:
                        raise ValueError()
                    if record["matrix_type"] not in ("supported", "tested") or type(record["exclusive"]) is not bool:
                        raise ValueError()
                    if record["matrix_type"] == "tested" and record["exclusive"]:
                        raise ValueError()
                    if "vendor_versions" in record and (not isinstance(record["vendor_versions"], list) or any(not isinstance(v, str) for v in record["vendor_versions"])):
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
        # The corrected provider display name keeps custom catalogs using the legacy name usable.
        for mapping in (self.records, self.notes, self.product_files, self.product_paths):
            legacy, provider = "Azure Key Vault CSI Driver", "Azure Key Vault Provider for Secrets Store CSI Driver"
            if legacy in mapping and provider not in mapping:
                mapping[provider] = mapping[legacy]

    def evaluate(self, product, version, target, source, today=None, *, raw_version=None):
        today = today or date.today()
        observed, target_release = release(version, product), release(str(target))
        rows = self.records.get(product, [])
        records = [r for r in rows if observed and in_range(observed, r["version"], r["version"])]
        matched_selectors = [r["version"] for r in records]
        exact_vendor = [r for r in records if (raw_version or version) in r.get("vendor_versions", [])]
        if exact_vendor:
            records = exact_vendor
        if records:
            specificity = lambda r: sum(p.isdigit() for p in r["version"].removeprefix("v").split("."))
            best = max(map(specificity, records))
            records = [r for r in records if specificity(r) == best]
        vendor = bool(re.fullmatch(r"v?\d+\.\d+\.\d+-\d+", str(version))) and product in VENDOR_PRODUCTS
        lookup = {"catalog_present": product in self.product_files, "files": self.product_files.get(product, []),
                  "paths": self.product_paths.get(product, []),
                  "available_selectors": [r["version"] for r in rows], "matched_selectors": matched_selectors,
                  "selected_selector": records[0]["version"] if len(records) == 1 else None,
                  "normalized_version": ".".join(map(str, observed)) if observed else None,
                  "reason": "matched" if len(records) == 1 else "ambiguous_matches" if records else "family_not_catalogued" if rows else "no_numeric_rows" if product in self.product_files else "catalog_missing"}
        def result(id_, status, text, record=None):
            policy = self.notes.get(product, {})
            fallback = policy.get("source") if safe_source(policy.get("source")) else source
            return finding(id_, "operator_compatibility", status, text,
                source=record["source"] if record else fallback, relation="documented" if record else "limitation",
                evidence={"product": product, "installed_version": version, "target": str(target), "matrix": record or {},
                          "detected_version": version, "version_confidence": "detected_tag_or_product_metadata" if version != "UNKNOWN" else "unknown",
                          "catalog_lookup": dict(lookup), "distribution_revision": str(version).rsplit("-", 1)[-1] if vendor else None,
                          "reviewed_on": record.get("reviewed_on") if record else None, "catalog_limitations": policy.get("limitations", [])},
                recommendation="Revisar la matriz oficial y actualizar el componente o completar evidencia antes del upgrade.")
        if not observed:
            lookup["reason"] = "version_missing" if version == "UNKNOWN" else "unrecognized_version_format"
            if re.match(r"^v?\d+\.\d+\.\d+", str(version)):
                return [result("VERSION_FORMAT_UNVERIFIED", "UNKNOWN", "Versión explícita detectada; su sufijo/formato no tiene una regla de normalización acreditada para este producto.")]
            return [result("VERSION_UNKNOWN", "UNKNOWN", "No se determinó una versión de producto inequívoca; un chart, digest o tag mutable no demuestra versión efectiva.")]
        if len(records) != 1:
            if product == "Gatekeeper" and not rows and product in self.product_files:
                item = result("NO_OFFICIAL_NUMERIC_MATRIX", "UNKNOWN",
                    f"Gatekeeper {version} fue detectado; la política oficial de releases no proporciona una matriz numérica revisada que acredite Kubernetes {target} para este binario.")
                item.evidence["legacy_rule_id"] = "NO_SUPPORT_DATA"
                return [item]
            if product == "Secrets Store CSI Driver" and not rows and product in self.product_files:
                item = result("NO_OFFICIAL_KUBERNETES_MATRIX", "UNKNOWN",
                    f"La versión {version} fue detectada, pero no se encontró en las fuentes oficiales revisadas una matriz numérica verificable que la vincule con Kubernetes {target}.")
                item.evidence["legacy_rule_id"] = "NO_SUPPORT_DATA"
                return [item]
            return [result("NO_SUPPORT_DATA", "UNKNOWN", "No existe una única fila de matriz oficial revisada para esta versión.")]
        record = records[0]
        if vendor and version not in record.get("vendor_versions", []):
            lookup["reason"] = "vendor_build_not_covered"
            return [result("VENDOR_BUILD_UNVERIFIED", "UNKNOWN", "Versión detectada con revisión de distribución; la matriz upstream no acredita este build administrado.", record)]
        findings = []
        if record.get("support_state") == "eol" or (record.get("end_of_support") and today > date.fromisoformat(record["end_of_support"])):
            findings.append(result("VERSION_EOL", "WARN", "Versión fuera de mantenimiento según la evidencia oficial registrada.", record))
        if not date.fromisoformat(record["reviewed_on"]) <= today <= date.fromisoformat(record["valid_until"]):
            findings.append(result("NO_SUPPORT_DATA", "UNKNOWN", "La revisión de la matriz no está vigente para la fecha del análisis.", record))
        elif record["support_state"] == "unknown":
            findings.append(result("NO_SUPPORT_DATA", "UNKNOWN", "Estado de soporte no acreditado por la fuente registrada.", record))
        elif in_range(target_release, record["min_kubernetes"], record["max_kubernetes"]):
            findings.append(result("COMPATIBLE", "PASS", "Objetivo dentro del rango documentado; consultar si la evidencia acredita soporte o pruebas upstream.", record))
        elif record["exclusive"]:
            item = result("NOT_COMPATIBLE", "FAIL", "El objetivo está fuera de la matriz oficial: bloqueo por política de soporte (FAIL_SUPPORT_POLICY), no una falla técnica demostrada.", record)
            item.evidence.update(failure_domain="SUPPORT_POLICY", support_status="FAIL_SUPPORT_POLICY", technical_status="NOT_TESTED")
            findings.append(item)
        else:
            findings.append(result("NO_SUPPORT_DATA", "UNKNOWN", "Objetivo fuera de las versiones probadas; esto no demuestra incompatibilidad.", record))
        return findings

    def provenance(self):
        return {"files": self.files, "detectors_sha256": hashlib.sha256(json.dumps(self.detectors, sort_keys=True).encode()).hexdigest(),
                "ownership_sha256": hashlib.sha256(json.dumps(self.ownership, sort_keys=True).encode()).hexdigest()}
