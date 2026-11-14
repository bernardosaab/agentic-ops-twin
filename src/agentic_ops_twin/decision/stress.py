"""Breaking-point stress tests: what breaks when the demand assumption is wrong?

For an alternative, bisect the arrival multiplier to find the largest demand level at which the
pre-declared decision rule still holds (its *headroom*), and report what breaks first: the
binding constraint and the most utilised resource at the first failing level. This turns a
point recommendation into a statement about how much error in the demand assumption it can
absorb.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from pydantic import Field

from agentic_ops_twin.decision.experiment import Job, run_jobs
from agentic_ops_twin.decision.search import feasible
from agentic_ops_twin.packs.base import DomainPack
from agentic_ops_twin.simulation.exogenous import DemandCondition
from agentic_ops_twin.simulation.model import Frozen, OperatingModel


class StressPoint(Frozen):
    multiplier: float
    sla_attainment: float | None
    completion_rate: float | None
    meets_rule: bool
    note: str
    max_utilisation_resource: str | None
    max_utilisation: float | None


class StressResult(Frozen):
    alternative: str
    label: str
    seeds: tuple[int, ...]
    headroom_multiplier: float | None = Field(
        description="Largest tested demand multiplier that still meets the rule (None if even "
        "current demand fails)."
    )
    first_failing_multiplier: float | None
    binding_constraint: str | None
    breaks_first_at: str | None = Field(description="Most utilised resource at first failure.")
    points: tuple[StressPoint, ...]


def _point(
    pack: DomainPack, model: OperatingModel, m: float, seeds: Sequence[int], workers: int | None
) -> StressPoint:
    demand = DemandCondition(name=f"stress-x{m:.3f}", arrival_multiplier=m)
    res = run_jobs([Job(model, tuple(seeds), demand, "stress", f"x{m:.3f}")], workers)[0]
    ok, note = feasible(res.summary, pack.decision_rule)
    util: dict[str, float] = {}
    for r in res.runs[0].resources:
        vals = [x.resources[r].utilisation for x in res.runs]
        clean = [v for v in vals if v is not None]
        if clean:
            util[r] = float(np.mean(clean))
    top = max(util, key=lambda k: util[k]) if util else None
    return StressPoint(
        multiplier=round(m, 4),
        sla_attainment=res.summary["sla_attainment"].mean,
        completion_rate=res.summary["completion_rate"].mean,
        meets_rule=ok,
        note=note,
        max_utilisation_resource=top,
        max_utilisation=util.get(top) if top else None,
    )


def breaking_point(
    pack: DomainPack,
    model: OperatingModel,
    *,
    name: str,
    label: str,
    seeds: Sequence[int],
    upper: float = 2.0,
    iterations: int = 6,
    workers: int | None = None,
) -> StressResult:
    points = [_point(pack, model, 1.0, seeds, workers)]
    if not points[0].meets_rule:
        first = points[0]
        return StressResult(
            alternative=name,
            label=label,
            seeds=tuple(seeds),
            headroom_multiplier=None,
            first_failing_multiplier=1.0,
            binding_constraint=first.note,
            breaks_first_at=first.max_utilisation_resource,
            points=tuple(points),
        )
    hi_point = _point(pack, model, upper, seeds, workers)
    points.append(hi_point)
    if hi_point.meets_rule:
        return StressResult(
            alternative=name,
            label=label,
            seeds=tuple(seeds),
            headroom_multiplier=upper,
            first_failing_multiplier=None,
            binding_constraint=None,
            breaks_first_at=None,
            points=tuple(points),
        )
    lo, hi, fail = 1.0, upper, hi_point
    for _ in range(iterations):
        mid = (lo + hi) / 2
        p = _point(pack, model, mid, seeds, workers)
        points.append(p)
        if p.meets_rule:
            lo = mid
        else:
            hi, fail = mid, p
    return StressResult(
        alternative=name,
        label=label,
        seeds=tuple(seeds),
        headroom_multiplier=round(lo, 4),
        first_failing_multiplier=round(hi, 4),
        binding_constraint=fail.note,
        breaks_first_at=fail.max_utilisation_resource,
        points=tuple(sorted(points, key=lambda p: p.multiplier)),
    )
