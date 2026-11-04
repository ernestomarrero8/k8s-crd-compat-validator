"""Reviewed knowledge is data, independently of a rule's applicability."""
import hashlib
from datetime import date
from pathlib import Path
from .collector import read_json
from .models import finding
from .rule_engine import safe_source
from .version import Version


class CoverageCatalog:
    def __init__(self, path=None):
        path = Path(path) if path else Path(__file__).resolve().parents[1] / "rules" / "coverage.json"
        self.data = read_json(path)
        self.sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        data = self.data
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            raise ValueError("Catálogo de cobertura: schema_version debe ser 1.")
        if not isinstance(data.get("catalog_version"), str) or not data["catalog_version"]:
            raise ValueError("Catálogo de cobertura sin versión.")
        for section in ("reviews", "conversion_protocols"):
            if not isinstance(data.get(section), list):
                raise ValueError("Catálogo de cobertura requiere reviews y conversion_protocols.")
            for record in data[section]:
                if not isinstance(record, dict):
                    raise ValueError("Registro de cobertura inválido.")
                try:
                    date.fromisoformat(record["reviewed_on"])
                    if not isinstance(record["reviewer"], str) or not record["reviewer"] or not safe_source(record["source"]):
                        raise ValueError()
                    prefixes = ("current", "target") if section == "reviews" else ("target",)
                    for prefix in prefixes:
                        if Version.parse(record[prefix + "_min"]) > Version.parse(record[prefix + "_max"]):
                            raise ValueError()
                    if section == "reviews":
                        if record["status"] not in ("partial", "reviewed_changes", "reviewed_no_changes") or not isinstance(record["categories"], list) or not record["categories"] or not isinstance(record["limitations"], list):
                            raise ValueError()
                        if any(not isinstance(x, str) or not x for x in record["categories"] + record["limitations"]):
                            raise ValueError()
                    elif not isinstance(record["versions"], list) or not record["versions"] or any(not isinstance(v, str) for v in record["versions"]):
                        raise ValueError()
                except (KeyError, TypeError, ValueError):
                    raise ValueError("Registro de cobertura incompleto o rango/fecha/fuente inválidos.") from None

    def protocols(self, target):
        records = [r for r in self.data["conversion_protocols"] if Version.parse(r["target_min"]) <= target <= Version.parse(r["target_max"])]
        # Conflicting or overlapping records require reviewer intervention.
        return records[0]["versions"] if len(records) == 1 else None

    def assess(self, current, target):
        boundaries = [current] + [Version(current.major, m, 0) for m in range(current.minor + 1, target.minor)] + [target]
        steps, reviews = [], []
        for start, end in zip(boundaries, boundaries[1:]):
            records = [r for r in self.data["reviews"] if Version.parse(r["current_min"]) <= start <= Version.parse(r["current_max"]) and Version.parse(r["target_min"]) <= end <= Version.parse(r["target_max"])]
            state = "unreviewed" if not records else "partial" if any(r["status"] == "partial" for r in records) else "reviewed"
            steps.append({"current": str(start), "target": str(end), "status": state})
            reviews.extend(r for r in records if r not in reviews)
        evidence = {"catalog_version": self.data["catalog_version"], "sha256": self.sha256, "reviews": reviews, "steps": steps}
        return finding("RULE-COVERAGE", "rules", "UNKNOWN" if any(s["status"] != "reviewed" for s in steps) else "PASS",
                       "Cobertura documental del trayecto solicitado; el alcance se limita a las categorías registradas.",
                       evidence=evidence, relation="documented" if reviews else "limitation",
                       recommendation="Revisar categorías, parches y distribuciones pendientes antes del upgrade.",
                       limitations=["Una revisión sin cambios relevantes no equivale a ausencia de revisión ni certifica compatibilidad completa."])
