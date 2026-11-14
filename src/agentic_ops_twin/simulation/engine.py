"""SimPy discrete-event engine: individual cases competing for finite resources.

Each case is a SimPy process that walks the routing graph of the active step variants. At each
step it queues for a server of the step's resource (non-preemptive; FIFO or value priority),
holds it for a service time drawn by inverse CDF from a counter-based uniform, then routes using a
second counter-based uniform. The run stops at the horizon; unfinished cases stay open and are
counted, never dropped.

``HiddenMechanisms`` exist only for the hidden-truth validation study: they add effects (handoff
delays, absenteeism) that the twin does not model. They default to off.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
import simpy
from pydantic import Field

from agentic_ops_twin.simulation.exogenous import (
    NORMAL_DEMAND,
    Arrival,
    DemandCondition,
    arrival_stream,
    stream_digest,
    uniform,
)
from agentic_ops_twin.simulation.metrics import ReplicationMetrics, ResourceUsage
from agentic_ops_twin.simulation.model import DONE, Branch, Frozen, OperatingModel, RouteRule
from agentic_ops_twin.simulation.validate import ensure_valid

CapacityMode = Literal["finite", "infinite"]
_INFINITE = 10**9


class HiddenMechanisms(Frozen):
    """Effects present in the hidden ground truth but absent from the twin (evaluation only)."""

    handoff_delay_hours: float = Field(default=0.0, ge=0)
    absenteeism_probability: float = Field(
        default=0.0, ge=0, lt=1, description="Per human server, per shift (automation exempt)."
    )
    shift_hours: float = Field(default=8.0, gt=0)


NO_MECHANISMS = HiddenMechanisms()


@dataclass(slots=True)
class LogEvent:
    case_id: str
    case_type: str
    value: float
    arrival: float
    step: str
    resource: str
    queued: float
    start: float
    end: float
    next_step: str


@dataclass(slots=True)
class _CaseState:
    arrival: Arrival
    status: Literal["queued", "in_service", "handoff", "done"] = "queued"
    completed_at: float | None = None
    escalated: int = 0


@dataclass(slots=True)
class _ResState:
    capacity: int
    res: simpy.PriorityResource | None
    intervals: list[list[float]] = field(default_factory=list)  # [start, end or nan]
    in_service: int = 0
    max_in_service: int = 0
    queue: int = 0
    max_queue: int = 0
    waits: list[float] = field(default_factory=list)


@dataclass
class SimulationRun:
    metrics: ReplicationMetrics
    event_log: list[LogEvent] | None


def _pick(rule: RouteRule, u: float) -> Branch:
    acc = 0.0
    for b in rule.branches:
        acc += b.probability
        if u < acc:
            return b
    return rule.branches[-1]


def simulate(
    model: OperatingModel,
    seed: int,
    demand: DemandCondition = NORMAL_DEMAND,
    *,
    capacity_mode: CapacityMode = "finite",
    mechanisms: HiddenMechanisms = NO_MECHANISMS,
    record_log: bool = False,
    validate_model: bool = True,
) -> SimulationRun:
    if validate_model:
        ensure_valid(model)
    env = simpy.Environment()
    horizon = model.horizon_hours
    warmup = model.warmup_hours
    arrivals = arrival_stream(model, seed, demand)
    steps = {s.id: s for s in model.steps}
    log: list[LogEvent] | None = [] if record_log else None

    res: dict[str, _ResState] = {}
    for r in model.resources:
        cap = _INFINITE if capacity_mode == "infinite" else r.capacity
        res[r.name] = _ResState(
            capacity=r.capacity,
            res=simpy.PriorityResource(env, capacity=cap) if cap > 0 else None,
        )

    cases: list[_CaseState] = []
    wip = 0
    variable_cost = 0.0
    step_waits: dict[str, list[float]] = {s.id: [] for s in model.steps}

    def priority(value: float) -> int:
        if model.queue_policy == "high_value_first":
            return 0 if value >= model.high_value_threshold else 1
        return 0

    def case_proc(state: _CaseState) -> Generator[simpy.Event, Any, None]:
        nonlocal variable_cost, wip
        a = state.arrival
        visits: Counter[str] = Counter()
        traversals: Counter[tuple[str, str]] = Counter()
        step_id = next(c.entry_step for c in model.case_types if c.name == a.case_type)
        while step_id != DONE:
            variant = steps[step_id].active
            visits[step_id] += 1
            k = visits[step_id]
            rs = res[variant.resource]
            state.status = "queued"
            queued_at = env.now
            rs.queue += 1
            rs.max_queue = max(rs.max_queue, rs.queue)
            if rs.res is None:  # zero capacity: request is never granted
                yield env.event()
                return
            with rs.res.request(priority=priority(a.value)) as req:
                yield req
                rs.queue -= 1
                start = env.now
                if start >= warmup:
                    rs.waits.append(start - queued_at)
                    step_waits[step_id].append(start - queued_at)
                    variable_cost += variant.cost_per_case
                state.status = "in_service"
                rs.in_service += 1
                rs.max_in_service = max(rs.max_in_service, rs.in_service)
                interval = [start, math.nan]
                rs.intervals.append(interval)
                yield env.timeout(variant.service.ppf(uniform(seed, "svc", a.case_id, step_id, k)))
                interval[1] = env.now
                rs.in_service -= 1
            rule = next(r for r in variant.routes if r.when is None or r.when.holds(a.value))
            branch = _pick(rule, uniform(seed, "route", a.case_id, step_id, k))
            target = branch.to
            if branch.max_traversals is not None:
                if traversals[(step_id, branch.to)] >= branch.max_traversals:
                    assert rule.fallback_to is not None
                    target = rule.fallback_to
                else:
                    traversals[(step_id, branch.to)] += 1
            if branch.escalation and target == branch.to:
                state.escalated += 1
            if log is not None:
                log.append(
                    LogEvent(
                        a.case_id,
                        a.case_type,
                        a.value,
                        a.time,
                        step_id,
                        variant.resource,
                        queued_at,
                        start,
                        env.now,
                        target,
                    )
                )
            if mechanisms.handoff_delay_hours > 0 and target != DONE:
                state.status = "handoff"
                yield env.timeout(mechanisms.handoff_delay_hours)
            step_id = target
        state.status = "done"
        state.completed_at = env.now
        wip -= 1

    def source() -> Generator[simpy.Event, Any, None]:
        nonlocal wip
        for a in arrivals:
            yield env.timeout(a.time - env.now)
            st = _CaseState(a)
            cases.append(st)
            wip += 1
            env.process(case_proc(st))

    def absenteeism(name: str, rs: _ResState) -> Generator[simpy.Event, Any, None]:
        shift = 0
        while env.now < horizon:
            absent = sum(
                uniform(seed, "absent", name, shift, i) < mechanisms.absenteeism_probability
                for i in range(rs.capacity)
            )
            assert rs.res is not None
            reqs = [rs.res.request(priority=-1) for _ in range(absent)]
            yield env.timeout(mechanisms.shift_hours)
            for rq in reqs:
                if rq.triggered:
                    rs.res.release(rq)
                else:
                    rq.cancel()
            shift += 1

    backlog: list[int] = []

    def sampler() -> Generator[simpy.Event, Any, None]:
        while True:
            backlog.append(wip)
            yield env.timeout(1.0)

    env.process(source())
    env.process(sampler())
    if mechanisms.absenteeism_probability > 0 and capacity_mode == "finite":
        kinds = {r.name: r.kind for r in model.resources}
        for name, rs in res.items():
            if rs.res is not None and kinds[name] == "human":
                env.process(absenteeism(name, rs))
    env.run(until=horizon)

    window = horizon - warmup
    cohort = [c for c in cases if c.arrival.time >= warmup]
    done = [c for c in cohort if c.completed_at is not None]
    cycles = np.array([c.completed_at - c.arrival.time for c in done if c.completed_at is not None])
    n_arr = len(cohort)
    n_done = len(done)
    n_open = n_arr - n_done
    if n_open != sum(1 for c in cohort if c.status != "done"):
        raise AssertionError("conservation violated: arrivals != completed + open")
    within = int(np.sum(cycles <= model.sla_hours)) if n_done else 0
    misses = n_arr - within
    staffed = model.staffed_cost_per_hour() * window
    total = staffed + variable_cost
    throughput = sum(1 for c in cases if c.completed_at is not None and c.completed_at >= warmup)

    usage: dict[str, ResourceUsage] = {}
    active = model.active_resources()
    for r in model.resources:
        rs = res[r.name]
        busy = 0.0
        for s, e in rs.intervals:
            end = horizon if math.isnan(e) else e
            busy += max(0.0, end - max(s, warmup))
        usage[r.name] = ResourceUsage(
            capacity=r.capacity,
            utilisation=busy / (r.capacity * window)
            if r.capacity > 0 and r.name in active
            else None,
            max_in_service=rs.max_in_service,
            max_queue=rs.max_queue,
            mean_wait_hours=float(np.mean(rs.waits)) if rs.waits else None,
        )

    metrics = ReplicationMetrics(
        seed=seed,
        arrival_digest=stream_digest(arrivals),
        arrivals=n_arr,
        completed=n_done,
        open=n_open,
        open_queued=sum(1 for c in cohort if c.status == "queued"),
        open_in_service=sum(1 for c in cohort if c.status == "in_service"),
        open_in_handoff=sum(1 for c in cohort if c.status == "handoff"),
        completion_rate=n_done / n_arr if n_arr else None,
        cycle_mean_hours=float(cycles.mean()) if n_done else None,
        cycle_median_hours=float(np.percentile(cycles, 50)) if n_done else None,
        cycle_p95_hours=float(np.percentile(cycles, 95)) if n_done else None,
        sla_attainment=within / n_arr if n_arr else None,
        sla_misses=misses,
        throughput_window=throughput,
        wip_at_horizon=sum(1 for c in cases if c.status != "done"),
        backlog_hourly=tuple(backlog),
        escalations=sum(c.escalated for c in cohort),
        staffed_cost=staffed,
        variable_cost=variable_cost,
        total_cost=total,
        cost_per_completion=total / throughput if throughput else None,
        objective_cost_per_case=(total + model.sla_penalty_per_miss * misses) / n_arr
        if n_arr
        else None,
        resources=usage,
        step_mean_wait_hours={k: float(np.mean(v)) if v else None for k, v in step_waits.items()},
    )
    return SimulationRun(metrics=metrics, event_log=log)
