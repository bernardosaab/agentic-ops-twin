"""Per-replication metrics.

Definitions (also in docs/assumptions-and-limitations.md):

* **Cohort**: cases arriving inside the measurement window ``[warmup, horizon)``. Cases arriving
  during warm-up load the system but are excluded from cohort counts.
* **Conservation**: ``arrivals == completed + open`` for the cohort (asserted).
* **Cycle-time statistics** use *completed* cohort cases only, and are always reported next to the
  completion rate and open count, so unfinished work cannot make a policy look fast.
* **SLA attainment**: share of cohort arrivals completed within ``sla_hours``. Open cases count as
  misses (conservative: their outcome is unknown at the horizon).
* **Cost**: staffed cost (capacity x rate x window hours) plus per-case variable cost for services
  started inside the window. ``cost_per_completion`` divides by all completions in the window.
* **Economic objective** ``objective_cost_per_case``: (window cost + SLA penalty x cohort misses) /
  cohort arrivals. Pre-declared single objective for ranking and selection.
"""

from __future__ import annotations

from pydantic import Field

from throughline.core.model import Frozen


class ResourceUsage(Frozen):
    capacity: int
    utilisation: float | None = Field(description="Busy server-hours / staffed server-hours.")
    max_in_service: int
    max_queue: int
    mean_wait_hours: float | None


class ReplicationMetrics(Frozen):
    seed: int
    arrival_digest: str
    arrivals: int
    completed: int
    open: int
    open_queued: int
    open_in_service: int
    open_in_handoff: int
    completion_rate: float | None
    cycle_mean_hours: float | None
    cycle_median_hours: float | None
    cycle_p95_hours: float | None
    sla_attainment: float | None
    sla_misses: int
    throughput_window: int
    wip_at_horizon: int
    backlog_hourly: tuple[int, ...]
    escalations: int
    staffed_cost: float
    variable_cost: float
    total_cost: float
    cost_per_completion: float | None
    objective_cost_per_case: float | None
    resources: dict[str, ResourceUsage]
    step_mean_wait_hours: dict[str, float | None]

    def scalar(self, name: str) -> float | None:
        value = getattr(self, name)
        if value is None:
            return None
        return float(value)


SCALAR_METRICS: tuple[str, ...] = (
    "arrivals",
    "completed",
    "open",
    "completion_rate",
    "cycle_median_hours",
    "cycle_p95_hours",
    "sla_attainment",
    "escalations",
    "total_cost",
    "cost_per_completion",
    "objective_cost_per_case",
    "wip_at_horizon",
)

# Direction used by comparisons, Pareto filtering and briefs.
LOWER_IS_BETTER: frozenset[str] = frozenset(
    {
        "open",
        "cycle_median_hours",
        "cycle_p95_hours",
        "escalations",
        "total_cost",
        "cost_per_completion",
        "objective_cost_per_case",
        "wip_at_horizon",
    }
)
