"""Selection rules and Pareto filtering over simulated alternatives."""

from __future__ import annotations

from collections.abc import Mapping

from agentic_ops_twin.decision.baselines import SpreadsheetEstimate
from agentic_ops_twin.packs.base import DecisionRule
from agentic_ops_twin.simulation.stats import Estimate


def _mean(summary: Mapping[str, Estimate], metric: str) -> float | None:
    e = summary.get(metric)
    return None if e is None else e.mean


def feasible(summary: Mapping[str, Estimate], rule: DecisionRule) -> tuple[bool, str]:
    cr = _mean(summary, "completion_rate")
    sla = _mean(summary, "sla_attainment")
    obj = _mean(summary, rule.objective)
    if cr is None or sla is None or obj is None:
        return False, "metric undefined (no arrivals or completions)"
    if cr < rule.min_completion_rate:
        return False, f"mean completion rate {cr:.3f} < {rule.min_completion_rate}"
    if sla < rule.min_sla_attainment:
        return False, f"mean SLA attainment {sla:.3f} < {rule.min_sla_attainment}"
    return True, "meets completion and SLA constraints on the mean"


def select(summaries: Mapping[str, Mapping[str, Estimate]], rule: DecisionRule) -> str | None:
    """Feasible alternative with the lowest mean objective (ties broken by name)."""
    best: tuple[float, str] | None = None
    for name, summary in summaries.items():
        ok, _ = feasible(summary, rule)
        obj = _mean(summary, rule.objective)
        if ok and obj is not None and (best is None or (obj, name) < best):
            best = (obj, name)
    return None if best is None else best[1]


def spreadsheet_feasible(est: SpreadsheetEstimate, sla_hours: float) -> tuple[bool, str]:
    if est.overloaded_resources:
        return False, f"offered load >= 1 on {', '.join(est.overloaded_resources)}"
    if est.expected_cycle_hours > sla_hours:
        return False, "expected cycle time exceeds SLA"
    return True, "no overloaded resource and average cycle within SLA"


def select_spreadsheet(
    estimates: Mapping[str, SpreadsheetEstimate], sla_hours: float
) -> str | None:
    best: tuple[float, str] | None = None
    for name, est in estimates.items():
        ok, _ = spreadsheet_feasible(est, sla_hours)
        if ok and (best is None or (est.objective_cost_per_case, name) < best):
            best = (est.objective_cost_per_case, name)
    return None if best is None else best[1]


PARETO_OBJECTIVES: tuple[tuple[str, int], ...] = (
    ("objective_cost_per_case", 1),  # minimise
    ("cycle_p95_hours", 1),  # minimise
    ("completion_rate", -1),  # maximise
)


def pareto_front(summaries: Mapping[str, Mapping[str, Estimate]]) -> list[str]:
    """Non-dominated alternatives on mean objective, p95 and completion rate."""
    pts: dict[str, tuple[float, ...]] = {}
    for name, s in summaries.items():
        vals = [_mean(s, m) for m, _ in PARETO_OBJECTIVES]
        if any(v is None for v in vals):
            continue
        pts[name] = tuple(
            sign * v for (_, sign), v in zip(PARETO_OBJECTIVES, vals, strict=True) if v is not None
        )
    front = []
    for a, pa in pts.items():
        dominated = any(
            all(x <= y for x, y in zip(pb, pa, strict=True)) and pb != pa
            for b, pb in pts.items()
            if b != a
        )
        if not dominated:
            front.append(a)
    return sorted(front, key=lambda n: pts[n])
