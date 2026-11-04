"""Per-product/CRD scoring with independent evidence coverage and blocker gating."""
WEIGHTS = {"operators": 40, "crds": 25, "pluto": 15, "aks_addons": 10, "storage": 10}


def score(report):
    platform = report.get("platform", {})
    groups = {key: [] for key in WEIGHTS}
    def worst(states):
        return next((s for s in ("ERROR", "FAIL", "UNKNOWN", "WARN") if s in states), "PASS") if states else "UNKNOWN"

    for row in platform.get("products", []):
        key = {"aks": "aks_addons", "storage": "storage"}.get(row["category"], "operators")
        groups[key].append(worst([f["status"] for f in row["findings"]]))
    discovery = platform.get("discovery", {}).get("status", "UNKNOWN")
    if discovery != "PASS":
        for key in ("operators", "aks_addons", "storage"):
            groups[key].append("UNKNOWN")
    for crd in report["crds"]:
        technical = [f["status"] for f in crd["findings"] if f["category"] not in ("operator", "instances", "storage")]
        storage = [f["status"] for f in crd["findings"] if f["category"] == "storage"]
        if technical:
            groups["crds"].append(worst(technical))
        if storage:
            groups["storage"].append(worst(storage))
    groups["pluto"] = [report.get("pluto", {}).get("status", "UNKNOWN")]
    aks = platform.get("aks", {})
    if aks.get("detected"):
        groups["aks_addons"].append("UNKNOWN")  # Microsoft's managed support is not proved by upstream matrices.
    results, earned, applicable, known_weight = {}, 0.0, 0, 0.0
    for key, weight in WEIGHTS.items():
        states = groups[key]
        if not states and discovery == "PASS" and key in ("operators", "aks_addons", "storage"):
            results[key] = {"weight": weight, "status": "NOT_APPLICABLE", "earned_points": 0, "observations": 0, "evidence_coverage": None, "counts": {}}
            continue
        states = states or ["UNKNOWN"]
        status = worst(states)
        # Average independent units; a single unknown no longer erases every valid product in a category.
        points = weight * sum({"PASS": 1, "WARN": .5}.get(s, 0) for s in states) / len(states)
        known = sum(s in ("PASS", "WARN", "FAIL") for s in states) / len(states)
        applicable += weight
        earned += points
        known_weight += weight * known
        results[key] = {"weight": weight, "status": status, "earned_points": round(points, 2), "observations": len(states),
                        "evidence_coverage": round(100 * known, 1), "counts": {s: states.count(s) for s in ("PASS", "WARN", "FAIL", "UNKNOWN", "ERROR")}}
    all_states = [f["status"] for f in report["global_findings"]] + [f["status"] for c in report["crds"] for f in c["findings"]] + [s for states in groups.values() for s in states]
    blockers = any(s in ("FAIL", "ERROR") for s in all_states)
    pending = any(s in ("UNKNOWN", "WARN") for s in all_states)
    value = round(100 * earned / applicable, 1) if applicable else 0
    decision = "BLOCKED" if blockers else "ATTENTION REQUIRED" if pending or value < 90 else "READY"
    return {"score": value, "scale": 100, "decision": decision, "categories": results,
            "scoring_version": "2.0", "evidence_coverage": round(100 * known_weight / applicable, 1) if applicable else 0,
            "assessed_compatibility_score": round(100 * earned / known_weight, 1) if known_weight else None,
            "applicable_weight": applicable, "confirmed_blockers": blockers, "pending_evidence": pending,
            "method": "Worst finding per product/CRD, then average units within each weighted category. PASS=100%, WARN=50%, UNKNOWN/FAIL/ERROR=0%; N/A excluded. Evidence coverage and compatibility of assessed units reported separately.",
            "limitation": "El score es una ayuda de revisión; READY exige ausencia de bloqueos, avisos y evidencia pendiente en todo el informe."}
