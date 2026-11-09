"""Versioned deterministic scoring from a completed engine record."""
from fractions import Fraction

SCORING_VERSION = "0.1"
WEIGHTS = {"C": 60, "T": 20, "F": 15, "E": 5}


def score_record(record):
    """Recalculate from final batches and per-turn movement, not cached scores.

    Input is a trusted engine replay, not an authenticated external submission.
    """
    if record.get("scoring_version") != SCORING_VERSION:
        raise ValueError("Unsupported scoring version")
    rows = record["log"]
    if not rows:
        raise ValueError("Cannot score an empty record")
    final = rows[-1]["state"]
    if len(rows) != final["total_turns"] or [r["turn"] for r in rows] != list(range(final["total_turns"])):
        raise ValueError("Only complete matches can be scored")
    budget = final["efficiency_budget"]
    if type(budget) is not int or budget <= 0:
        raise ValueError("Efficiency budget must be a positive integer")
    demand = received = on_time = 0
    coverage = []
    for shelter in final["shelters"]:
        batches = [b for b in shelter["batches"] if b["created_turn"] <= rows[-1]["turn"]]
        d = sum(b["amount"] for b in batches)
        r = sum(min(b["amount"], max(0, b["received"])) for b in batches)
        t = sum(min(b["amount"], max(0, b["received"]), max(0, b["on_time"])) for b in batches)
        demand += shelter["priority"] * d
        received += shelter["priority"] * r
        on_time += shelter["priority"] * t
        if d:
            coverage.append(Fraction(r, d))
    if demand <= 0:
        raise ValueError("Scenario must have positive weighted demand")
    cost = sum(row["movement_cost"] for row in rows)
    if cost < 0:
        raise ValueError("Movement cost cannot be negative")
    metrics = {"C": Fraction(received, demand), "T": Fraction(on_time, demand), "F": min(coverage)}
    metrics["E"] = metrics["C"] * max(Fraction(0), 1 - Fraction(cost, budget))
    total = sum(WEIGHTS[key] * value for key, value in metrics.items())
    return {"version": SCORING_VERSION, "weights": dict(WEIGHTS),
            "metrics": {k: round(float(v), 6) for k, v in metrics.items()},
            "total": round(float(total), 6), "movement_cost": cost, "efficiency_budget": budget}
