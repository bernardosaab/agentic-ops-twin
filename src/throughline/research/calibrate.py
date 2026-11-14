"""Calibrate a twin from an observed event log, and diagnose what the log says it misses.

Calibration estimates, from baseline history only:

* arrival rates per case type (stationary Poisson assumption) and the lognormal value attribute;
* service-time mean and coefficient of variation for each *active* step variant;
* branch probabilities from observed transitions.

Inactive variants (for example an automation that was never switched on) cannot be calibrated
from this history; their authored parameters are kept and flagged as an assumption.

Residual diagnostics test assumptions the twin makes that the log can contradict: zero handoff
delay between steps, full nominal capacity whenever work is queued, and stationary arrivals.
"""

from __future__ import annotations

import itertools
import math
from collections import Counter, defaultdict
from collections.abc import Sequence
from typing import Any

import numpy as np
from pydantic import Field

from throughline.core.engine import LogEvent
from throughline.core.exogenous import Arrival
from throughline.core.model import Frozen, OperatingModel


class ParamEstimate(Frozen):
    name: str
    estimate: float
    ci95_low: float | None
    ci95_high: float | None
    n: int


class Diagnostic(Frozen):
    name: str
    statistic: float
    threshold: float
    flagged: bool
    meaning: str


class Calibration(Frozen):
    model: OperatingModel
    parameters: tuple[ParamEstimate, ...]
    uncalibrated: tuple[str, ...] = Field(description="Variants kept at authored values.")
    diagnostics: tuple[Diagnostic, ...]


def _lognormal_fit(xs: Sequence[float]) -> tuple[float, float]:
    arr = np.asarray(xs, dtype=float)
    mean = float(arr.mean())
    sd = float(arr.std(ddof=1)) if len(arr) > 1 else 0.0
    return mean, max(sd / mean, 1e-3) if mean > 0 else 1e-3


def _boot_ci(
    xs: Sequence[float], rng: np.random.Generator, b: int = 200
) -> tuple[float | None, float | None]:
    arr = np.asarray(xs, dtype=float)
    if len(arr) < 5:
        return None, None
    means = arr[rng.integers(0, len(arr), size=(b, len(arr)))].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def calibrate(
    structure: OperatingModel,
    arrivals: Sequence[Arrival],
    log: Sequence[LogEvent],
    horizon_hours: float,
    *,
    seed: int = 0,
    diagnostics: bool = True,
) -> Calibration:
    rng = np.random.default_rng(seed)
    data: dict[str, Any] = structure.model_dump(mode="json")
    params: list[ParamEstimate] = []

    by_type: dict[str, list[Arrival]] = defaultdict(list)
    for a in arrivals:
        by_type[a.case_type].append(a)
    for ct in data["case_types"]:
        xs = by_type.get(ct["name"], [])
        rate = len(xs) / horizon_hours
        se = math.sqrt(len(xs)) / horizon_hours
        ct["arrival_rate_per_hour"] = rate
        params.append(
            ParamEstimate(
                name=f"arrival_rate[{ct['name']}]",
                estimate=rate,
                ci95_low=rate - 1.96 * se,
                ci95_high=rate + 1.96 * se,
                n=len(xs),
            )
        )
        if len(xs) >= 2:
            logs = np.log([a.value for a in xs])
            ct["value"] = {"median": float(math.exp(logs.mean())), "sigma": float(logs.std(ddof=1))}

    durations: dict[str, list[float]] = defaultdict(list)
    transitions: dict[tuple[str, int], Counter[str]] = defaultdict(Counter)
    for e in log:
        durations[e.step].append(e.end - e.start)
    step_rules: dict[str, list[dict[str, Any]]] = {}
    for s in data["steps"]:
        step_rules[s["id"]] = s["variants"][s["active_variant"]]["routes"]
    for e in log:
        rules = step_rules[e.step]
        idx = next(
            i
            for i, r in enumerate(rules)
            if r["when"] is None
            or (
                e.value >= r["when"]["threshold"]
                if r["when"]["op"] == ">="
                else e.value < r["when"]["threshold"]
            )
        )
        transitions[(e.step, idx)][e.next_step] += 1

    uncalibrated: list[str] = []
    for s in data["steps"]:
        for vname, v in s["variants"].items():
            if vname != s["active_variant"]:
                uncalibrated.append(f"{s['id']}.{vname}")
                continue
            obs = durations.get(s["id"], [])
            if len(obs) < 2:
                uncalibrated.append(f"{s['id']}.{vname} (too few observations)")
                continue
            svc = v["service"]
            mean, cv = _lognormal_fit(obs)
            lo, hi = _boot_ci(obs, rng)
            params.append(
                ParamEstimate(
                    name=f"service_mean[{s['id']}]",
                    estimate=mean,
                    ci95_low=lo,
                    ci95_high=hi,
                    n=len(xs),
                )
            )
            if svc["kind"] == "deterministic":
                svc["mean"] = mean
            else:
                v["service"] = {"kind": "lognormal", "mean": mean, "cv": cv}
            for ri, rule in enumerate(v["routes"]):
                counts = transitions.get((s["id"], ri))
                if not counts or len(rule["branches"]) == 1:
                    continue
                targets = [b["to"] for b in rule["branches"]]
                total = sum(counts[t] for t in targets)
                if total == 0:
                    continue
                probs = [counts[t] / total for t in targets]
                # Keep every authored edge possible (validator requires the structure intact).
                probs = [max(p, 1e-4) for p in probs]
                z = sum(probs)
                for b, p in zip(rule["branches"], probs, strict=True):
                    b["probability"] = p / z
                drift = 1 - sum(b["probability"] for b in rule["branches"])
                rule["branches"][-1]["probability"] += drift
                params.append(
                    ParamEstimate(
                        name=f"branch[{s['id']}#{ri}]",
                        estimate=rule["branches"][0]["probability"],
                        ci95_low=None,
                        ci95_high=None,
                        n=total,
                    )
                )
    data["version"] = f"{structure.version}+calibrated"
    data["assumptions"] = [
        {
            "id": "cal-1",
            "source": "calibrated-from-log",
            "text": "Arrival rates, case values, active service times and branch probabilities "
            "were estimated from the observed baseline history.",
        },
        {
            "id": "cal-2",
            "source": "calibrated-from-log",
            "text": "Arrivals are assumed stationary Poisson; staff are assumed fully available; "
            "handoffs are assumed instantaneous.",
        },
        *(
            [
                {
                    "id": "cal-3",
                    "source": "synthetic-hand-authored",
                    "text": "Not observed in history, kept at authored values: "
                    + ", ".join(uncalibrated),
                }
            ]
            if uncalibrated
            else []
        ),
    ]
    model = OperatingModel.model_validate(data)
    return Calibration(
        model=model,
        parameters=tuple(params),
        uncalibrated=tuple(uncalibrated),
        diagnostics=tuple(diagnose(structure, arrivals, log, horizon_hours)) if diagnostics else (),
    )


def diagnose(
    structure: OperatingModel,
    arrivals: Sequence[Arrival],
    log: Sequence[LogEvent],
    horizon_hours: float,
) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    # 1. Handoff gaps: time between finishing one step and joining the next queue.
    by_case: dict[str, list[LogEvent]] = defaultdict(list)
    for e in log:
        by_case[e.case_id].append(e)
    gaps: list[float] = []
    for evs in by_case.values():
        evs.sort(key=lambda x: x.start)
        gaps.extend(b.queued - a.end for a, b in itertools.pairwise(evs))
    mean_gap = float(np.mean(gaps)) if gaps else 0.0
    out.append(
        Diagnostic(
            name="mean_handoff_gap_hours",
            statistic=mean_gap,
            threshold=1e-6,
            flagged=mean_gap > 1e-6,
            meaning="The twin assumes zero time between steps; a positive gap "
            "means unmodelled handoff delay.",
        )
    )
    # 2. Idle capacity while work waits: fraction of queue-waiting time during which fewer than
    #    the nominal number of servers were busy (sampled at 0.1h).
    caps = {r.name: r.capacity for r in structure.resources}
    grid = np.arange(0.0, horizon_hours, 0.1)
    worst = 0.0
    worst_res = ""
    for res, cap in caps.items():
        evs = [e for e in log if e.resource == res]
        if cap <= 0 or not evs or res not in structure.active_resources():
            continue
        starts = np.array([e.start for e in evs])
        ends = np.array([e.end for e in evs])
        queued = np.array([e.queued for e in evs])
        busy = np.searchsorted(np.sort(starts), grid, side="right") - np.searchsorted(
            np.sort(ends), grid, side="right"
        )
        waiting = np.searchsorted(np.sort(queued), grid, side="right") - np.searchsorted(
            np.sort(starts), grid, side="right"
        )
        mask = waiting > 0
        if mask.sum() < 10:
            continue
        frac = float(np.mean(busy[mask] < cap))
        if frac > worst:
            worst, worst_res = frac, res
    out.append(
        Diagnostic(
            name="idle_capacity_while_queued",
            statistic=worst,
            threshold=0.05,
            flagged=worst > 0.05,
            meaning="Share of time work waited although fewer than the nominal "
            f"servers were busy (worst resource: {worst_res or 'n/a'}); "
            "suggests effective capacity below nominal.",
        )
    )
    # 3. Arrival non-stationarity: dispersion of hourly arrival counts by hour of day.
    counts = np.zeros(math.ceil(horizon_hours))
    for a in arrivals:
        counts[int(a.time)] += 1
    by_hod = [counts[h::24].mean() for h in range(24) if len(counts[h::24])]
    mean_rate = float(np.mean(counts)) if len(counts) else 0.0
    ratio = (max(by_hod) / min(by_hod)) if by_hod and min(by_hod) > 0 else math.inf
    out.append(
        Diagnostic(
            name="peak_to_trough_hourly_arrivals",
            statistic=float(ratio),
            threshold=2.0,
            flagged=ratio > 2.0,
            meaning=f"Ratio of busiest to quietest hour-of-day arrival rate "
            f"(mean {mean_rate:.2f}/h); the twin assumes a constant rate.",
        )
    )
    return out
