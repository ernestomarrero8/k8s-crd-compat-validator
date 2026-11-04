"""Evidence-weighted score; unknown contributes no earned points and blocks READY."""
WEIGHTS = {"operators": 40, "crds": 25, "pluto": 15, "aks_addons": 10, "storage": 10}


def score(report):
    platform = report.get("platform", {})
    groups = {key: [] for key in WEIGHTS}
    for row in platform.get("products", []):
        key = {"aks": "aks_addons", "storage": "storage"}.get(row["category"], "operators")
        groups[key].extend(f["status"] for f in row["findings"])
    discovery = platform.get("discovery", {}).get("status", "UNKNOWN")
    if discovery != "PASS":
        for key in ("operators", "aks_addons", "storage"):
            groups[key].append("UNKNOWN")
    groups["crds"] = [f["status"] for c in report["crds"] for f in c["findings"] if f["category"] not in ("operator", "instances", "storage")]
    groups["storage"].extend(f["status"] for c in report["crds"] for f in c["findings"] if f["category"] == "storage")
    groups["pluto"] = [report.get("pluto", {}).get("status", "UNKNOWN")]
    aks = platform.get("aks", {})
    if aks.get("detected"):
        groups["aks_addons"].append("UNKNOWN")  # Microsoft's managed support is not proved by upstream matrices.
    results, earned, applicable = {}, 0.0, 0
    for key, weight in WEIGHTS.items():
        states = groups[key]
        if not states and discovery == "PASS" and key in ("operators", "aks_addons", "storage"):
            results[key] = {"weight": weight, "status": "NOT_APPLICABLE", "earned_points": 0, "observations": 0}
            continue
        states = states or ["UNKNOWN"]
        # Worst evidence governs a category; numerous PASS checks cannot dilute a blocker.
        status = next((s for s in ("ERROR", "FAIL", "UNKNOWN", "WARN") if s in states), "PASS")
        points = weight * {"PASS": 1, "WARN": .5}.get(status, 0)
        applicable += weight
        earned += points
        results[key] = {"weight": weight, "status": status, "earned_points": points, "observations": len(states)}
    all_states = [f["status"] for f in report["global_findings"]] + [f["status"] for c in report["crds"] for f in c["findings"]]
    blockers = any(s in ("FAIL", "ERROR") for s in all_states)
    pending = any(s in ("UNKNOWN", "WARN") for s in all_states)
    value = round(100 * earned / applicable, 1) if applicable else 0
    decision = "BLOCKED" if blockers else "ATTENTION REQUIRED" if pending or value < 90 else "READY"
    return {"score": value, "scale": 100, "decision": decision, "categories": results,
            "applicable_weight": applicable, "confirmed_blockers": blockers, "pending_evidence": pending,
            "method": "Worst finding per category. PASS=100%, WARN=50%, UNKNOWN/FAIL/ERROR=0%; N/A excluded and remaining weights normalized.",
            "limitation": "El score es una ayuda de revisión; READY exige ausencia de bloqueos, avisos y evidencia pendiente en todo el informe."}
