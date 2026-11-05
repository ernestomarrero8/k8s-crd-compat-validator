"""Per-product/CRD scoring with independent evidence coverage and blocker gating."""
import json
from pathlib import Path
import re

WEIGHTS = {"operators": 40, "crds": 25, "pluto": 15, "aks_addons": 10, "storage": 10}
DEFAULT_CONFIG = {"minimum_evidence_coverage": 90, "unknown_blocks_ready": True, "warning_blocks_ready": True}


def load_config(path=None):
    """Accept JSON or the documented scalar-only readiness YAML mapping; no executable YAML."""
    config = {}
    if path:
        text = Path(path).read_text(encoding="utf-8-sig")
        if text.lstrip().startswith("{"):
            document = json.loads(text)
            if not isinstance(document, dict) or "readiness" not in document:
                raise ValueError("Configuración requiere un mapping readiness.")
            config = document["readiness"]
        else:
            lines = [s.split("#", 1)[0].rstrip() for s in text.splitlines() if s.split("#", 1)[0].strip()]
            if not lines or lines[0] != "readiness:":
                raise ValueError("Configuración requiere un mapping readiness.")
            for line in lines[1:]:
                match = re.fullmatch(r"  ([a-z_]+): (true|false|\d+(?:\.\d+)?)", line)
                if not match or match[1] in config:
                    raise ValueError("Configuración readiness inválida; sólo se admiten los tres escalares documentados.")
                config[match[1]] = {"true": True, "false": False}.get(match[2], match[2])
    if not isinstance(config, dict) or set(config) - set(DEFAULT_CONFIG):
        raise ValueError("Opción readiness no reconocida.")
    result = DEFAULT_CONFIG | config
    try:
        if type(result["minimum_evidence_coverage"]) is bool:
            raise ValueError()
        result["minimum_evidence_coverage"] = float(result["minimum_evidence_coverage"])
        if not 0 <= result["minimum_evidence_coverage"] <= 100 or any(type(result[k]) is not bool for k in ("unknown_blocks_ready", "warning_blocks_ready")):
            raise ValueError()
    except (TypeError, ValueError):
        raise ValueError("Umbral readiness debe estar entre 0 y 100 y las políticas deben ser booleanas.") from None
    return result


def score(report, config=None):
    config = DEFAULT_CONFIG | (config or {})
    platform = report.get("platform", {})
    groups = {key: [] for key in WEIGHTS}
    def worst(states):
        return next((s for s in ("FAIL", "ERROR", "UNKNOWN", "WARN") if s in states), "PASS") if states else "UNKNOWN"

    for row in platform.get("products", []):
        key = {"aks": "aks_addons", "storage": "storage"}.get(row["category"], "operators")
        groups[key].append(worst([f["status"] for f in row["findings"]]))
    discovery = platform.get("discovery", {}).get("status", "UNKNOWN")
    if discovery != "PASS":
        for key in ("operators", "aks_addons", "storage"):
            groups[key].append("UNKNOWN")
    for crd in report["crds"]:
        technical = [f["status"] for f in crd["findings"] if f.get("rule_id") != "PRODUCT_SUPPORT" and f.get("score_weight") != 0 and f["category"] not in ("operator", "instances", "storage")]
        storage = [f["status"] for f in crd["findings"] if f["category"] == "storage"]
        if technical:
            groups["crds"].append(worst(technical))
        if storage:
            groups["storage"].append(worst(storage))
    groups["pluto"] = [report.get("pluto", {}).get("status", "UNKNOWN")]
    aks = platform.get("aks", {})
    if aks.get("detected"):
        groups["aks_addons"].append("UNKNOWN")  # Microsoft's managed support is not proved by upstream matrices.
    results, earned, applicable, known_weight, total_units, evaluated_units = {}, 0.0, 0, 0.0, 0, 0
    for key, weight in WEIGHTS.items():
        states = groups[key]
        if not states and discovery == "PASS" and key in ("operators", "aks_addons", "storage", "crds"):
            results[key] = {"weight": weight, "status": "NOT_APPLICABLE", "earned_points": 0, "observations": 0, "evidence_coverage": None, "counts": {}}
            continue
        states = states or ["UNKNOWN"]
        status = worst(states)
        # Average independent units; a single unknown no longer erases every valid product in a category.
        points = weight * sum({"PASS": 1, "WARN": .5}.get(s, 0) for s in states) / len(states)
        known = sum(s in ("PASS", "WARN", "FAIL") for s in states) / len(states)
        total_units += len(states)
        evaluated_units += sum(s in ("PASS", "WARN", "FAIL") for s in states)
        applicable += weight
        earned += points
        known_weight += weight * known
        results[key] = {"weight": weight, "status": status, "earned_points": round(points, 2), "observations": len(states),
                        "evidence_coverage": round(100 * known, 1), "counts": {s: states.count(s) for s in ("PASS", "WARN", "FAIL", "UNKNOWN", "ERROR")}}
    all_states = [f["status"] for f in report["global_findings"]] + [f["status"] for c in report["crds"] for f in c["findings"]] + [s for states in groups.values() for s in states]
    blockers = "FAIL" in all_states
    pending = any(s in ("UNKNOWN", "WARN") for s in all_states)
    coverage = round(100 * evaluated_units / total_units, 1) if total_units else 0
    value = round(100 * earned / known_weight, 1) if known_weight else None
    required_missing = any(s.get("required") and not s.get("completed") for s in platform.get("inventory_sources", []))
    detector_error = any(d.get("detection_status") == "DETECTION_ERROR" for d in platform.get("detector_diagnostics", []))
    incomplete = "ERROR" in all_states or required_missing or detector_error or coverage < config["minimum_evidence_coverage"]
    attention = ("UNKNOWN" in all_states and config["unknown_blocks_ready"]) or ("WARN" in all_states and config["warning_blocks_ready"])
    decision = "BLOCKED" if blockers else "INCOMPLETE" if incomplete else "ATTENTION_REQUIRED" if attention or coverage < 100 else "READY"
    return {"score": value, "scale": 100, "decision": decision, "categories": results,
            "scoring_version": "2.1", "evidence_coverage": coverage, "evaluated_units": evaluated_units, "applicable_units": total_units,
            "weighted_evidence_coverage": round(100 * known_weight / applicable, 1) if applicable else 0,
            "verified_readiness_score": round(100 * earned / applicable, 1) if applicable else 0,
            "assessed_compatibility_score": value, "config": config, "required_inventory_missing": required_missing,
            "applicable_weight": applicable, "confirmed_blockers": blockers, "pending_evidence": pending,
            "incomplete_evaluation": incomplete, "decision_legacy": decision.replace("_", " "),
            "method": "One unit per product/technical CRD/storage CRD and one Pluto unit. Weighted compatibility over evaluated PASS=100%, WARN=50%, FAIL=0% units only; UNKNOWN/ERROR excluded from compatibility, retained in coverage. Evidence coverage = evaluated/applicable units. PRODUCT_SUPPORT references have zero additional weight.",
            "limitation": "El score es una ayuda de revisión; READY exige ausencia de bloqueos, avisos y evidencia pendiente en todo el informe."}
