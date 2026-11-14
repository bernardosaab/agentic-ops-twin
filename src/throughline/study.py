"""Decision study: baseline ladder, bounded search, held-out evaluation and sensitivity.

Pipeline for one domain pack (selection uses the search split only):

1. Enumerate every permitted lever combination; record rejected ones with reasons.
2. On the search split, score every feasible alternative three ways: spreadsheet arithmetic,
   uncapacitated simulation and capacity-aware simulation (repeated replications).
3. Each method selects an alternative with the same pre-declared decision rule.
4. Re-run the baseline, each method's choice and the leading Pareto alternatives on the held-out
   split (fresh seeds and unseen demand conditions) with the capacity-aware simulation, paired
   against the baseline only where arrival-stream digests are verified identical.
5. One-at-a-time sensitivity of the capacity-aware choice versus baseline.
"""

from __future__ import annotations

import time
from typing import Literal

import numpy as np
from pydantic import Field

from throughline.baselines import SpreadsheetEstimate, spreadsheet_estimate
from throughline.core.exogenous import EXOGENOUS_SCHEME, DemandCondition
from throughline.core.metrics import SCALAR_METRICS
from throughline.core.model import Frozen, OperatingModel
from throughline.core.stats import Difference, Estimate, compare, pairing_status
from throughline.experiment import Job, ScenarioResult, Splits, run_jobs
from throughline.packs.base import DecisionRule, DomainPack
from throughline.scenarios import Change, ChangeSet, enumerate_alternatives
from throughline.search import (
    feasible,
    pareto_front,
    select,
    select_spreadsheet,
    spreadsheet_feasible,
)
from throughline.sensitivity import perturb

Profile = Literal["quick", "full"]
METHODS: tuple[str, ...] = ("spreadsheet", "uncapacitated_sim", "capacity_aware_sim")
COMPARE_METRICS: tuple[str, ...] = (
    "objective_cost_per_case",
    "cost_per_completion",
    "cycle_median_hours",
    "cycle_p95_hours",
    "completion_rate",
    "sla_attainment",
    "open",
    "escalations",
)


class AlternativeRecord(Frozen):
    name: str
    label: str
    changes: tuple[Change, ...]
    model_digest: str
    staffed_cost_per_hour: float
    search: dict[str, Estimate]
    uncapacitated: dict[str, Estimate]
    spreadsheet: SpreadsheetEstimate
    feasible: bool
    feasible_note: str
    uncapacitated_feasible: bool
    spreadsheet_feasible: bool
    mean_utilisation: dict[str, float | None]
    mean_step_wait_hours: dict[str, float | None]


class HeldOutRow(Frozen):
    alternative: str
    label: str
    roles: tuple[str, ...]
    condition: str
    summary: dict[str, Estimate]
    feasible: bool
    feasible_note: str
    vs_baseline: dict[str, Difference]


class SensitivityRow(Frozen):
    parameter: str
    value: float
    alternative: str
    summary: dict[str, Estimate]
    feasible: bool
    vs_baseline: Difference | None


class AutomationEffect(Frozen):
    alternative: str
    label: str
    changed_step: str
    utilisation_change: dict[str, float]
    step_wait_change_hours: dict[str, float]
    objective_difference: Difference
    p95_difference: Difference
    downstream_load_increase: tuple[str, ...] = Field(
        description="Resources whose mean utilisation rose by >= 0.05 under this change."
    )


class DecisionStudy(Frozen):
    pack_id: str
    pack_title: str
    generator_version: str
    model_id: str
    model_version: str
    model_digest: str
    exogenous_scheme: str
    profile: Profile
    decision_rule: DecisionRule
    search_seeds: tuple[int, ...]
    heldout_seeds: tuple[int, ...]
    search_conditions: tuple[DemandCondition, ...]
    heldout_conditions: tuple[DemandCondition, ...]
    n_enumerated: int
    n_equivalent: int
    rejected: tuple[tuple[str, str, str], ...]
    alternatives: tuple[AlternativeRecord, ...]
    selections: dict[str, str | None]
    pareto: tuple[str, ...]
    heldout: tuple[HeldOutRow, ...]
    sensitivity: tuple[SensitivityRow, ...]
    automation_effects: tuple[AutomationEffect, ...]
    pairing_checks: tuple[str, ...]
    simulated_replications: int
    runtime_seconds: float


def profile_splits(splits: Splits, profile: Profile) -> Splits:
    if profile == "full":
        return splits
    return splits.model_copy(
        update={"search_seeds": splits.search_seeds[:4], "heldout_seeds": splits.heldout_seeds[:6]}
    )


def _mean_usage(res: ScenarioResult) -> tuple[dict[str, float | None], dict[str, float | None]]:
    util: dict[str, float | None] = {}
    waits: dict[str, float | None] = {}
    first = res.runs[0]
    for r in first.resources:
        xs = [m.resources[r].utilisation for m in res.runs]
        vals = [x for x in xs if x is not None]
        util[r] = float(np.mean(vals)) if vals else None
    for s in first.step_mean_wait_hours:
        ws = [m.step_mean_wait_hours[s] for m in res.runs]
        wv = [w for w in ws if w is not None]
        waits[s] = float(np.mean(wv)) if wv else None
    return util, waits


def run_study(
    pack: DomainPack, *, profile: Profile = "full", workers: int | None = None
) -> DecisionStudy:
    t0 = time.perf_counter()
    splits = profile_splits(pack.splits, profile)
    model = pack.model
    rule = pack.decision_rule
    feasible_alts, rejected, equivalent = enumerate_alternatives(model, pack.decision_space)
    by_name: dict[str, tuple[ChangeSet, OperatingModel]] = {
        cs.name: (cs, m) for cs, m in feasible_alts
    }
    if "baseline" not in by_name:
        raise ValueError("baseline configuration is not inside the decision space or budget")
    search_cond = splits.search_conditions[0]
    seeds = splits.search_seeds
    jobs = [Job(m, seeds, search_cond, cs.name, cs.label()) for cs, m in feasible_alts]
    jobs += [
        Job(m, seeds, search_cond, cs.name, cs.label(), capacity_mode="infinite")
        for cs, m in feasible_alts
    ]
    results = run_jobs(jobs, workers)
    n_reps = len(jobs) * len(seeds)
    finite = {r.scenario: r for r in results if r.capacity_mode == "finite"}
    infinite = {r.scenario: r for r in results if r.capacity_mode == "infinite"}

    records: list[AlternativeRecord] = []
    sheets: dict[str, SpreadsheetEstimate] = {}
    for cs, m in feasible_alts:
        fr = finite[cs.name]
        sheet = spreadsheet_estimate(m, search_cond)
        sheets[cs.name] = sheet
        ok, note = feasible(fr.summary, rule)
        util, waits = _mean_usage(fr)
        records.append(
            AlternativeRecord(
                name=cs.name,
                label=cs.label(),
                changes=cs.changes,
                model_digest=m.digest(),
                staffed_cost_per_hour=m.staffed_cost_per_hour(),
                search=fr.summary,
                uncapacitated=infinite[cs.name].summary,
                spreadsheet=sheet,
                feasible=ok,
                feasible_note=note,
                uncapacitated_feasible=feasible(infinite[cs.name].summary, rule)[0],
                spreadsheet_feasible=spreadsheet_feasible(sheet, m.sla_hours)[0],
                mean_utilisation=util,
                mean_step_wait_hours=waits,
            )
        )

    selections = {
        "spreadsheet": select_spreadsheet(sheets, model.sla_hours),
        "uncapacitated_sim": select({k: v.summary for k, v in infinite.items()}, rule),
        "capacity_aware_sim": select({k: v.summary for k, v in finite.items()}, rule),
    }
    pareto = pareto_front({k: v.summary for k, v in finite.items()})

    roles: dict[str, list[str]] = {"baseline": ["baseline"]}
    for method, name in selections.items():
        if name is not None:
            roles.setdefault(name, []).append(f"selected:{method}")
    for name in pareto[:3]:
        roles.setdefault(name, []).append("pareto")

    pairing: list[str] = []
    base_finite = finite["baseline"]
    effects: list[AutomationEffect] = []
    for cs, _ in feasible_alts:
        if len(cs.changes) == 1 and cs.changes[0].lever.startswith("variant:"):
            alt = finite[cs.name]
            bu, bw = _mean_usage(base_finite)
            au, aw = _mean_usage(alt)
            du = {k: au[k] - bu[k] for k in au if au[k] is not None and bu[k] is not None}  # type: ignore[operator]
            dw = {k: aw[k] - bw[k] for k in aw if aw[k] is not None and bw[k] is not None}  # type: ignore[operator]
            effects.append(
                AutomationEffect(
                    alternative=cs.name,
                    label=cs.label(),
                    changed_step=cs.changes[0].lever.split(":", 1)[1],
                    utilisation_change=du,
                    step_wait_change_hours=dw,
                    objective_difference=compare(
                        "objective_cost_per_case", base_finite.runs, alt.runs
                    ),
                    p95_difference=compare("cycle_p95_hours", base_finite.runs, alt.runs),
                    downstream_load_increase=tuple(k for k, v in du.items() if v >= 0.05),
                )
            )
            pairing.append(
                f"search {cs.name} vs baseline: {pairing_status(base_finite.runs, alt.runs)[1]}"
            )

    # Held-out evaluation.
    ho_jobs = [
        Job(by_name[name][1], splits.heldout_seeds, cond, name, by_name[name][0].label())
        for cond in splits.heldout_conditions
        for name in roles
    ]
    ho_results = run_jobs(ho_jobs, workers)
    n_reps += len(ho_jobs) * len(splits.heldout_seeds)
    heldout: list[HeldOutRow] = []
    for cond in splits.heldout_conditions:
        base = next(
            r for r in ho_results if r.scenario == "baseline" and r.condition.name == cond.name
        )
        for r in (x for x in ho_results if x.condition.name == cond.name):
            ok, note = feasible(r.summary, rule)
            diffs = {mname: compare(mname, base.runs, r.runs) for mname in COMPARE_METRICS}
            if r.scenario != "baseline":
                pairing.append(
                    f"held-out {cond.name} {r.scenario} vs baseline: "
                    f"{pairing_status(base.runs, r.runs)[1]}"
                )
            heldout.append(
                HeldOutRow(
                    alternative=r.scenario,
                    label=r.label,
                    roles=tuple(roles[r.scenario]),
                    condition=cond.name,
                    summary=r.summary,
                    feasible=ok,
                    feasible_note=note,
                    vs_baseline=diffs,
                )
            )
    # Demand-changing comparisons are deliberately unpaired; record one as evidence.
    surge = [r for r in ho_results if r.scenario == "baseline"]
    if len(surge) >= 2:
        pairing.append(
            f"held-out baseline {surge[0].condition.name} vs {surge[1].condition.name}: "
            f"{pairing_status(surge[0].runs, surge[1].runs)[1]}"
        )

    # Sensitivity of the capacity-aware choice versus baseline (held-out seeds, first condition).
    sens: list[SensitivityRow] = []
    chosen = selections["capacity_aware_sim"]
    sens_names = ["baseline"] + ([chosen] if chosen and chosen != "baseline" else [])
    cond0 = splits.heldout_conditions[0]
    s_jobs: list[Job] = []
    s_keys: list[tuple[str, float, str]] = []
    for p in pack.sensitivity:
        for value in (p.low, p.high):
            for name in sens_names:
                m2, d2 = perturb(by_name[name][1], cond0, p, value)
                s_jobs.append(Job(m2, splits.heldout_seeds, d2, name, f"{p.name}={value:g}"))
                s_keys.append((p.name, value, name))
    s_results = run_jobs(s_jobs, workers)
    n_reps += len(s_jobs) * len(splits.heldout_seeds)
    lookup = {k: r for k, r in zip(s_keys, s_results, strict=True)}
    for (pname, value, name), r in lookup.items():
        base_r = lookup[(pname, value, "baseline")]
        sens.append(
            SensitivityRow(
                parameter=pname,
                value=value,
                alternative=name,
                summary={
                    k: r.summary[k]
                    for k in (
                        "objective_cost_per_case",
                        "completion_rate",
                        "sla_attainment",
                        "cycle_p95_hours",
                    )
                },
                feasible=feasible(r.summary, rule)[0],
                vs_baseline=None
                if name == "baseline"
                else compare("objective_cost_per_case", base_r.runs, r.runs),
            )
        )

    return DecisionStudy(
        pack_id=pack.id,
        pack_title=pack.title,
        generator_version=pack.generator_version,
        model_id=model.id,
        model_version=model.version,
        model_digest=model.digest(),
        exogenous_scheme=EXOGENOUS_SCHEME,
        profile=profile,
        decision_rule=rule,
        search_seeds=splits.search_seeds,
        heldout_seeds=splits.heldout_seeds,
        search_conditions=splits.search_conditions,
        heldout_conditions=splits.heldout_conditions,
        n_enumerated=len(feasible_alts) + len(rejected) + len(equivalent),
        n_equivalent=len(equivalent),
        rejected=tuple((cs.name, cs.label(), reason) for cs, reason in rejected),
        alternatives=tuple(records),
        selections=selections,
        pareto=tuple(pareto),
        heldout=tuple(heldout),
        sensitivity=tuple(sens),
        automation_effects=tuple(effects),
        pairing_checks=tuple(pairing),
        simulated_replications=n_reps,
        runtime_seconds=round(time.perf_counter() - t0, 2),
    )


__all__ = ["METHODS", "SCALAR_METRICS", "DecisionStudy", "evaluate_change_set", "run_study"]


def evaluate_change_set(
    pack: DomainPack,
    change_set: ChangeSet,
    condition: str,
    *,
    profile: Profile = "full",
    workers: int | None = None,
) -> tuple[HeldOutRow, HeldOutRow]:
    """Run a validated change set and the baseline on the held-out seeds for one condition."""
    from throughline.scenarios import apply_changes

    splits = profile_splits(pack.splits, profile)
    cond = pack.condition(condition)
    changed, _ = apply_changes(pack.model, pack.decision_space, change_set)
    base_res, alt_res = run_jobs(
        [
            Job(pack.model, splits.heldout_seeds, cond, "baseline", "baseline"),
            Job(changed, splits.heldout_seeds, cond, change_set.name, change_set.label()),
        ],
        workers,
    )
    rows = []
    for res, roles in ((base_res, ("baseline",)), (alt_res, ("proposal",))):
        ok, note = feasible(res.summary, pack.decision_rule)
        rows.append(
            HeldOutRow(
                alternative=res.scenario,
                label=res.label,
                roles=roles,
                condition=cond.name,
                summary=res.summary,
                feasible=ok,
                feasible_note=note,
                vs_baseline={m: compare(m, base_res.runs, res.runs) for m in COMPARE_METRICS},
            )
        )
    return rows[0], rows[1]
