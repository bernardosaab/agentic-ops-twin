"""Simpler baselines the capacity-aware simulation is compared against.

1. ``spreadsheet_estimate``: average-duration arithmetic. Expected visits per step come from the
   routing probabilities (absorbing Markov chain, traversal limits ignored); cycle time is the sum
   of mean service times with no waiting; every arrival is assumed to complete. Offered load is
   computed (as a careful spreadsheet would) but does not feed back into time or completion.
2. Uncapacitated simulation: the same engine with ``capacity_mode="infinite"`` (variability and
   routing kept, contention removed). Staffed cost still uses the configured capacities.
"""

from __future__ import annotations

import itertools
import math
from statistics import NormalDist

import numpy as np
from pydantic import Field

from throughline.core.exogenous import DemandCondition
from throughline.core.model import DONE, Frozen, OperatingModel
from throughline.core.validate import all_conditions


class SpreadsheetEstimate(Frozen):
    method: str = "average-duration arithmetic (no queueing, all arrivals complete)"
    expected_cycle_hours: float
    completion_rate: float = 1.0
    cost_per_completion: float
    objective_cost_per_case: float
    offered_load: dict[str, float | None] = Field(description="lambda * work / capacity")
    overloaded_resources: tuple[str, ...]


def _region_probabilities(
    model: OperatingModel, median: float, sigma: float
) -> list[tuple[float, float]]:
    """(representative value, probability mass) for each region of constant conditions."""
    thresholds = sorted({c.threshold for c in all_conditions(model) if c.threshold > 0})
    edges = [0.0, *thresholds, math.inf]

    def cdf(x: float) -> float:
        if x <= 0:
            return 0.0
        if math.isinf(x):
            return 1.0
        if sigma == 0:
            return 1.0 if x > median else 0.0
        return NormalDist().cdf((math.log(x) - math.log(median)) / sigma)

    out: list[tuple[float, float]] = []
    for lo, hi in itertools.pairwise(edges):
        mass = cdf(hi) - cdf(lo)
        if mass <= 0:
            continue
        rep = lo if lo > 0 else (hi / 2 if math.isfinite(hi) else 1.0)
        out.append((rep, mass))
    return out


def expected_visits(model: OperatingModel, entry: str, value: float) -> dict[str, float]:
    ids = [s.id for s in model.steps]
    idx = {sid: i for i, sid in enumerate(ids)}
    q = np.zeros((len(ids), len(ids)))
    for s in model.steps:
        rule = next(r for r in s.active.routes if r.when is None or r.when.holds(value))
        for b in rule.branches:
            if b.to != DONE:
                q[idx[s.id], idx[b.to]] += b.probability
    n = np.linalg.solve(np.eye(len(ids)) - q.T, np.eye(len(ids))[idx[entry]])
    return {sid: float(n[idx[sid]]) for sid in ids}


def spreadsheet_estimate(model: OperatingModel, demand: DemandCondition) -> SpreadsheetEstimate:
    total_rate = 0.0
    cycle_weighted = 0.0
    var_cost_rate = 0.0
    miss_rate = 0.0
    work: dict[str, float] = {r.name: 0.0 for r in model.resources}
    for ct in model.case_types:
        lam = demand.rate(model, ct.name)
        for value, mass in _region_probabilities(model, ct.value.median, ct.value.sigma):
            visits = expected_visits(model, ct.entry_step, value)
            cyc = sum(v * model.step(sid).active.service.mean for sid, v in visits.items())
            rate = lam * mass
            total_rate += rate
            cycle_weighted += rate * cyc
            miss_rate += rate * (1.0 if cyc > model.sla_hours else 0.0)
            for sid, v in visits.items():
                act = model.step(sid).active
                var_cost_rate += rate * v * act.cost_per_case
                work[act.resource] += rate * v * act.service.mean
    staffed = model.staffed_cost_per_hour()
    load = {
        r.name: (
            work[r.name] / r.capacity
            if r.capacity > 0
            else (None if work[r.name] == 0 else math.inf)
        )
        for r in model.resources
    }
    overloaded = tuple(k for k, v in load.items() if v is not None and v >= 1.0)
    cost_per = (staffed + var_cost_rate) / total_rate if total_rate else math.inf
    return SpreadsheetEstimate(
        expected_cycle_hours=cycle_weighted / total_rate if total_rate else 0.0,
        cost_per_completion=cost_per,
        objective_cost_per_case=cost_per
        + model.sla_penalty_per_miss * (miss_rate / total_rate if total_rate else 0.0),
        offered_load=load,
        overloaded_resources=overloaded,
    )
