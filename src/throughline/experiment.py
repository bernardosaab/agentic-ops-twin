"""Replicated scenario runs and published seed splits."""

from __future__ import annotations

import os
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

from pydantic import Field, model_validator

from throughline.core.engine import NO_MECHANISMS, CapacityMode, HiddenMechanisms, simulate
from throughline.core.exogenous import EXOGENOUS_SCHEME, DemandCondition
from throughline.core.metrics import SCALAR_METRICS, ReplicationMetrics
from throughline.core.model import Frozen, OperatingModel
from throughline.core.stats import Estimate, summarise
from throughline.core.validate import ensure_valid


class Splits(Frozen):
    """Seeds and demand conditions for search (selection) and held-out evaluation.

    Search seeds and held-out seeds must be disjoint; held-out demand conditions may include
    conditions never seen during search. Selection uses only the search split.
    """

    search_seeds: tuple[int, ...] = Field(min_length=2)
    heldout_seeds: tuple[int, ...] = Field(min_length=2)
    search_conditions: tuple[DemandCondition, ...] = Field(min_length=1)
    heldout_conditions: tuple[DemandCondition, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _disjoint(self) -> Splits:
        overlap = set(self.search_seeds) & set(self.heldout_seeds)
        if overlap:
            raise ValueError(f"search and held-out seeds overlap: {sorted(overlap)}")
        return self


class ScenarioResult(Frozen):
    scenario: str
    label: str
    model_id: str
    model_version: str
    model_digest: str
    condition: DemandCondition
    capacity_mode: CapacityMode
    exogenous_scheme: str
    seeds: tuple[int, ...]
    runs: tuple[ReplicationMetrics, ...]
    summary: dict[str, Estimate]


def run_scenario(
    model: OperatingModel,
    seeds: Sequence[int],
    demand: DemandCondition,
    *,
    scenario: str,
    label: str,
    capacity_mode: CapacityMode = "finite",
    mechanisms: HiddenMechanisms = NO_MECHANISMS,
) -> ScenarioResult:
    runs = tuple(
        simulate(
            model,
            s,
            demand,
            capacity_mode=capacity_mode,
            mechanisms=mechanisms,
            validate_model=(i == 0),
        ).metrics
        for i, s in enumerate(seeds)
    )
    return ScenarioResult(
        scenario=scenario,
        label=label,
        model_id=model.id,
        model_version=model.version,
        model_digest=model.digest(),
        condition=demand,
        capacity_mode=capacity_mode,
        exogenous_scheme=EXOGENOUS_SCHEME,
        seeds=tuple(seeds),
        runs=runs,
        summary=summarise(runs, SCALAR_METRICS),
    )


@dataclass(frozen=True)
class Job:
    model: OperatingModel
    seeds: tuple[int, ...]
    demand: DemandCondition
    scenario: str
    label: str
    capacity_mode: CapacityMode = "finite"
    mechanisms: HiddenMechanisms = NO_MECHANISMS


def _one(task: tuple[Job, int]) -> ReplicationMetrics:
    job, seed = task
    return simulate(
        job.model,
        seed,
        job.demand,
        capacity_mode=job.capacity_mode,
        mechanisms=job.mechanisms,
        validate_model=False,
    ).metrics


def run_jobs(jobs: Sequence[Job], workers: int | None = None) -> list[ScenarioResult]:
    """Run every (job, seed) task, optionally across processes; results are order-independent.

    Each replication is a pure function of (model, seed, demand, mode, mechanisms), so worker count
    never changes results.
    """
    for job in jobs:
        ensure_valid(job.model)
    tasks = [(job, s) for job in jobs for s in job.seeds]
    if workers is None:
        # Each worker is a full interpreter; cap the default to keep memory modest (notably on
        # Windows, where processes are spawned). Override with --workers or THROUGHLINE_WORKERS.
        env = os.environ.get("THROUGHLINE_WORKERS")
        workers = int(env) if env else min(len(tasks), os.cpu_count() or 1, 6)
    if workers <= 1 or len(tasks) < 8:
        metrics = [_one(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            metrics = list(pool.map(_one, tasks, chunksize=max(1, len(tasks) // (workers * 8))))
    out: list[ScenarioResult] = []
    i = 0
    for job in jobs:
        runs = tuple(metrics[i : i + len(job.seeds)])
        i += len(job.seeds)
        out.append(
            ScenarioResult(
                scenario=job.scenario,
                label=job.label,
                model_id=job.model.id,
                model_version=job.model.version,
                model_digest=job.model.digest(),
                condition=job.demand,
                capacity_mode=job.capacity_mode,
                exogenous_scheme=EXOGENOUS_SCHEME,
                seeds=job.seeds,
                runs=runs,
                summary=summarise(runs, SCALAR_METRICS),
            )
        )
    return out
