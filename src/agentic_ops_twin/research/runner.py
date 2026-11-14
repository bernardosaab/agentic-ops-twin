"""Pre-registered research studies (see docs/preregistration.md)."""

from __future__ import annotations

import hashlib
import json
import math
import random
import time
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats as sps

from agentic_ops_twin.decision.baselines import spreadsheet_estimate
from agentic_ops_twin.decision.experiment import Job, ScenarioResult, run_jobs
from agentic_ops_twin.decision.scenarios import ChangeSet, apply_changes, enumerate_alternatives
from agentic_ops_twin.decision.search import (
    feasible,
    select,
    select_spreadsheet,
    spreadsheet_feasible,
)
from agentic_ops_twin.governance.ledger import Ledger, sha256
from agentic_ops_twin.packs import get_pack
from agentic_ops_twin.packs.base import DomainPack
from agentic_ops_twin.research.calibrate import Calibration, calibrate
from agentic_ops_twin.research.selection import pcs
from agentic_ops_twin.simulation.engine import simulate
from agentic_ops_twin.simulation.exogenous import DemandCondition, arrival_stream
from agentic_ops_twin.simulation.model import OperatingModel

HISTORY_SEED = 500
HISTORY_HOURS = 960.0
VALIDATION_SEEDS = tuple(range(7000, 7008))
WORLD_SEEDS = tuple(range(8000, 8004))
POOL_SEEDS = tuple(range(30000, 30040))
LONGRUN_SEEDS = tuple(range(20000, 20060))
N_ALTERNATIVES = 12
N_WORLDS = 12
BUDGETS = (50, 100, 150, 200)
MACRO = 400
DELTA_IZ = 1.0
OBJ = "objective_cost_per_case"


def _unbounded_space(pack: DomainPack) -> Any:
    # Calibrated rates change staffed cost only through capacities, which are unchanged; the
    # pack's budget therefore applies as-is.
    return pack.decision_space


def _truth_demand(pack: DomainPack, cond: DemandCondition) -> DemandCondition:
    return cond.model_copy(
        update={
            "name": f"{cond.name}+truth-profile",
            "hourly_profile": pack.hidden_truth.hourly_profile,
        }
    )


def _history(pack: DomainPack) -> tuple[OperatingModel, list[Any], list[Any]]:
    hist_model = pack.model.model_copy(update={"horizon_hours": HISTORY_HOURS, "warmup_hours": 0.0})
    demand = _truth_demand(pack, pack.condition("normal"))
    run = simulate(
        hist_model, HISTORY_SEED, demand, mechanisms=pack.hidden_truth.mechanisms, record_log=True
    )
    arrivals = arrival_stream(hist_model, HISTORY_SEED, demand)
    assert run.event_log is not None
    return hist_model, arrivals, run.event_log


def _restore_horizon(cal_model: OperatingModel, pack: DomainPack) -> OperatingModel:
    return cal_model.model_copy(
        update={"horizon_hours": pack.model.horizon_hours, "warmup_hours": pack.model.warmup_hours}
    )


def _pick_alternatives(pack: DomainPack) -> list[ChangeSet]:
    feasible_alts, _, _ = enumerate_alternatives(pack.model, pack.decision_space)
    names = sorted(cs.name for cs, _ in feasible_alts if cs.name != "baseline")
    rng = random.Random(f"{pack.id}-alternatives-v1")
    chosen = set(rng.sample(names, min(N_ALTERNATIVES - 1, len(names))))
    return [cs for cs, _ in feasible_alts if cs.name == "baseline" or cs.name in chosen]


def _means(results: dict[str, ScenarioResult], metric: str = OBJ) -> dict[str, float]:
    out: dict[str, float] = {}
    for k, v in results.items():
        m = v.summary[metric].mean
        if m is not None:
            out[k] = m
    return out


def _tau(pred: dict[str, float], truth: dict[str, float]) -> float | None:
    keys = sorted(set(pred) & set(truth))
    if len(keys) < 3:
        return None
    t = sps.kendalltau([pred[k] for k in keys], [truth[k] for k in keys]).statistic
    return None if t is None or math.isnan(t) else float(t)


def _regret(
    choice: str | None, truth: dict[str, ScenarioResult], pack: DomainPack
) -> dict[str, Any]:
    """Truth-measured consequence of acting on a method's choice.

    ``regret`` is defined only when the choice is feasible in truth: its truth objective minus
    the best truth-feasible objective. An infeasible choice is a constraint failure, reported
    as such rather than as a (possibly negative) regret.
    """
    tsum = {k: v.summary for k, v in truth.items()}
    best = select(tsum, pack.decision_rule)
    tm = _means(truth)
    if choice is None:
        return {
            "choice": None,
            "truth_best": best,
            "regret": None,
            "choice_feasible_in_truth": None,
        }
    ok = feasible(tsum[choice], pack.decision_rule)[0]
    regret = tm[choice] - tm[best] if ok and best is not None else None
    return {"choice": choice, "truth_best": best, "regret": regret, "choice_feasible_in_truth": ok}


def hidden_truth_study(
    pack: DomainPack, workers: int | None, quick: bool
) -> tuple[dict[str, Any], Calibration, list[ChangeSet], dict[str, dict[str, ScenarioResult]]]:
    """Returns (report, calibration, alternatives, truth results by condition)."""
    hist_model, arrivals, log = _history(pack)
    cal = calibrate(pack.model, arrivals, log, HISTORY_HOURS, seed=HISTORY_SEED)
    twin = _restore_horizon(cal.model, pack)
    alts = _pick_alternatives(pack)
    seeds = VALIDATION_SEEDS[:4] if quick else VALIDATION_SEEDS
    conds = [pack.condition("normal"), pack.condition("surge_25")]
    jobs: list[Job] = []
    sheet: dict[str, dict[str, Any]] = {}
    for cond in conds:
        sheet[cond.name] = {}
        for cs in alts:
            truth_m, _ = apply_changes(pack.model, pack.decision_space, cs)
            twin_m, _ = apply_changes(twin, _unbounded_space(pack), cs)
            jobs.append(
                Job(
                    truth_m,
                    seeds,
                    _truth_demand(pack, cond),
                    cs.name,
                    "truth",
                    mechanisms=pack.hidden_truth.mechanisms,
                )
            )
            jobs.append(Job(twin_m, seeds, cond, cs.name, "twin"))
            jobs.append(
                Job(twin_m, seeds, cond, cs.name, "uncapacitated", capacity_mode="infinite")
            )
            sheet[cond.name][cs.name] = spreadsheet_estimate(twin_m, cond)
    results = run_jobs(jobs, workers)
    grouped: dict[str, dict[str, dict[str, ScenarioResult]]] = {}
    for job, res in zip(jobs, results, strict=True):
        cname = job.demand.name.split("+")[0]
        grouped.setdefault(cname, {}).setdefault(job.label, {})[job.scenario] = res

    per_cond: dict[str, Any] = {}
    for cond in conds:
        g = grouped[cond.name]
        truth = g["truth"]
        tm = _means(truth)
        preds = {
            "capacity_aware_twin": _means(g["twin"]),
            "uncapacitated_sim": _means(g["uncapacitated"]),
            "spreadsheet": {k: v.objective_cost_per_case for k, v in sheet[cond.name].items()},
        }
        choices = {
            "capacity_aware_twin": select(
                {k: v.summary for k, v in g["twin"].items()}, pack.decision_rule
            ),
            "uncapacitated_sim": select(
                {k: v.summary for k, v in g["uncapacitated"].items()}, pack.decision_rule
            ),
            "spreadsheet": select_spreadsheet(sheet[cond.name], twin.sla_hours),
        }
        mape = {
            m: float(np.mean([abs(p[k] - tm[k]) / abs(tm[k]) for k in p if k in tm]))
            for m, p in preds.items()
        }
        per_cond[cond.name] = {
            "kendall_tau": {m: _tau(p, tm) for m, p in preds.items()},
            "objective_mape": mape,
            "choices": {m: _regret(c, truth, pack) for m, c in choices.items()},
            "truth_feasible": sorted(
                k for k, v in truth.items() if feasible(v.summary, pack.decision_rule)[0]
            ),
            "spreadsheet_feasible": sorted(
                k for k, v in sheet[cond.name].items() if spreadsheet_feasible(v, twin.sla_hours)[0]
            ),
            "objective_means": {"truth": tm, **preds},
        }
    base_t = grouped["normal"]["truth"]["baseline"].summary
    base_w = grouped["normal"]["twin"]["baseline"].summary
    fit = {}
    for metric in (
        "cycle_median_hours",
        "cycle_p95_hours",
        "completion_rate",
        "sla_attainment",
        OBJ,
    ):
        t, w = base_t[metric].mean, base_w[metric].mean
        fit[metric] = {
            "truth": t,
            "twin": w,
            "relative_error": None if not t or w is None else (w - t) / t,
        }
    taus = {c: per_cond[c]["kendall_tau"] for c in per_cond}
    h1 = all(
        taus[c]["capacity_aware_twin"] is not None
        and all(
            taus[c][m] is None or taus[c]["capacity_aware_twin"] > taus[c][m]
            for m in ("uncapacitated_sim", "spreadsheet")
        )
        for c in taus
    )
    report = {
        "history": {
            "seed": HISTORY_SEED,
            "hours": HISTORY_HOURS,
            "arrivals": len(arrivals),
            "events": len(log),
        },
        "mechanisms": pack.hidden_truth.model_dump(mode="json"),
        "calibration": [p.model_dump(mode="json") for p in cal.parameters],
        "uncalibrated": list(cal.uncalibrated),
        "diagnostics": [d.model_dump(mode="json") for d in cal.diagnostics],
        "baseline_fit_normal": fit,
        "alternatives": [{"name": cs.name, "label": cs.label()} for cs in alts],
        "validation_seeds": list(seeds),
        "conditions": per_cond,
        "h1_supported": h1,
    }
    del hist_model
    return report, cal, alts, {c: g["truth"] for c, g in grouped.items()}


def selection_study(pack: DomainPack, workers: int | None, quick: bool) -> dict[str, Any]:
    feasible_alts, _, _ = enumerate_alternatives(pack.model, pack.decision_space)
    cond = pack.condition("normal")
    ranked = sorted(
        (
            (spreadsheet_estimate(m, cond).objective_cost_per_case, cs.name, cs, m)
            for cs, m in feasible_alts
            if spreadsheet_feasible(spreadsheet_estimate(m, cond), m.sla_hours)[0]
        ),
        key=lambda t: (t[0], t[1]),
    )[:10]
    pool_seeds = POOL_SEEDS[:20] if quick else POOL_SEEDS
    long_seeds = LONGRUN_SEEDS[:20] if quick else LONGRUN_SEEDS
    jobs = [Job(m, pool_seeds, cond, name, "pool") for _, name, _, m in ranked]
    jobs += [Job(m, long_seeds, cond, name, "longrun") for _, name, _, m in ranked]
    res = run_jobs(jobs, workers)
    pool = [
        np.array([r.scalar(OBJ) for r in x.runs], dtype=float) for x in res if x.label == "pool"
    ]
    longrun = [x for x in res if x.label == "longrun"]
    true_means = np.array([x.summary[OBJ].mean for x in longrun], dtype=float)
    true_se = [x.summary[OBJ].sd / math.sqrt(x.summary[OBJ].n) for x in longrun]  # type: ignore[operator]
    budgets = [b for b in BUDGETS if b <= len(pool) * len(pool_seeds)]
    macro = 100 if quick else MACRO
    rows = []
    for b in budgets:
        pe, se_e = pcs(pool, true_means, b, "equal", macro, DELTA_IZ, seed=b)
        po, se_o = pcs(pool, true_means, b, "ocba", macro, DELTA_IZ, seed=b)
        rows.append(
            {"budget": b, "pcs_equal": pe, "se_equal": se_e, "pcs_ocba": po, "se_ocba": se_o}
        )
    order = np.argsort(true_means)
    h2 = all(r["pcs_ocba"] >= r["pcs_equal"] for r in rows) and any(
        r["pcs_ocba"] > r["pcs_equal"] for r in rows
    )
    return {
        "alternatives": [name for _, name, _, _ in ranked],
        "long_run_means": dict(zip([n for _, n, _, _ in ranked], true_means.tolist(), strict=True)),
        "long_run_se": dict(zip([n for _, n, _, _ in ranked], true_se, strict=True)),
        "gap_best_to_second": float(true_means[order[1]] - true_means[order[0]]),
        "within_indifference_zone": int(np.sum(true_means - true_means.min() <= DELTA_IZ)),
        "pool_size": len(pool_seeds),
        "long_run_reps": len(long_seeds),
        "macro": macro,
        "delta_iz": DELTA_IZ,
        "rows": rows,
        "h2_supported": h2,
    }


def _bootstrap_world(
    pack: DomainPack, arrivals: list[Any], log: list[Any], w: int
) -> OperatingModel:
    rng = np.random.default_rng(10_000 + w)
    ids = sorted({a.case_id for a in arrivals})
    pick = rng.choice(len(ids), size=len(ids), replace=True)
    counts: dict[str, int] = {}
    for i in pick:
        counts[ids[i]] = counts.get(ids[i], 0) + 1
    arr = [a for a in arrivals for _ in range(counts.get(a.case_id, 0))]
    evs = [e for e in log for _ in range(counts.get(e.case_id, 0))]
    cal = calibrate(pack.model, arr, evs, HISTORY_HOURS, seed=w, diagnostics=False)
    return _restore_horizon(cal.model, pack)


def robust_study(
    pack: DomainPack,
    alts: list[ChangeSet],
    point_choice: str | None,
    workers: int | None,
    quick: bool,
) -> dict[str, Any]:
    _, arrivals, log = _history(pack)
    n_worlds = 4 if quick else N_WORLDS
    worlds = [_bootstrap_world(pack, arrivals, log, w) for w in range(n_worlds)]
    cond = pack.condition("normal")
    jobs = []
    for w, wm in enumerate(worlds):
        for cs in alts:
            m, _ = apply_changes(wm, pack.decision_space, cs)
            jobs.append(Job(m, WORLD_SEEDS, cond, cs.name, f"w{w}"))
    res = run_jobs(jobs, workers)
    obj: dict[str, list[float]] = {cs.name: [] for cs in alts}
    feas: dict[str, list[bool]] = {cs.name: [] for cs in alts}
    for w in range(n_worlds):
        world = {r.scenario: r for r in res if r.label == f"w{w}"}
        f_w = {k: feasible(v.summary, pack.decision_rule)[0] for k, v in world.items()}
        o_w = {k: float(v.summary[OBJ].mean or math.inf) for k, v in world.items()}
        best = min((o_w[k] for k in o_w if f_w[k]), default=min(o_w.values()))
        for k in obj:
            obj[k].append(o_w[k] - best)
            feas[k].append(f_w[k])
    base_obj = [r for r in res if r.scenario == "baseline"]
    stats_ = {}
    for k in obj:
        stats_[k] = {
            "max_regret": max(obj[k]),
            "mean_regret": float(np.mean(obj[k])),
            "feasible_share": float(np.mean(feas[k])),
        }
    p_dom = {}
    for k in obj:
        wins = 0
        for w in range(n_worlds):
            rk = next(r for r in res if r.scenario == k and r.label == f"w{w}")
            rb = next(r for r in base_obj if r.label == f"w{w}")
            wins += int(
                feasible(rk.summary, pack.decision_rule)[0]
                and (rk.summary[OBJ].mean or math.inf) < (rb.summary[OBJ].mean or 0)
            )
        p_dom[k] = wins / n_worlds
    cands = [k for k in obj if stats_[k]["feasible_share"] >= 0.8]
    robust = min(cands, key=lambda k: (stats_[k]["max_regret"], k)) if cands else None
    return {
        "worlds": n_worlds,
        "seeds_per_world": len(WORLD_SEEDS),
        "regret": stats_,
        "p_dominates_baseline": p_dom,
        "point_choice": point_choice,
        "robust_choice": robust,
        "fragile_point_choice": point_choice is not None
        and (stats_.get(point_choice, {}).get("feasible_share", 0) < 0.8),
    }


def run_research(
    pack_ids: tuple[str, ...], *, out: Path, ledger_path: str, workers: int | None, quick: bool
) -> None:
    prereg = Path("docs/preregistration.md")
    text = prereg.read_text(encoding="utf-8")
    ledger = Ledger(ledger_path)
    prec = ledger.append(
        "preregistration", {"path": str(prereg), "sha256": sha256(text), "quick": quick}
    )
    summary: dict[str, Any] = {
        "preregistration_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "preregistration_record": prec.record_id,
        "quick": quick,
        "packs": {},
    }
    for pid in pack_ids:
        t0 = time.perf_counter()
        pack = get_pack(pid)
        h1, _cal, alts, truth_by_cond = hidden_truth_study(pack, workers, quick)
        h2 = selection_study(pack, workers, quick)
        point = h1["conditions"]["normal"]["choices"]["capacity_aware_twin"]["choice"]
        h3 = robust_study(pack, alts, point, workers, quick)
        # H3 is judged in the hidden truth under held-out +25% demand (simulated in H1).
        surge = truth_by_cond["surge_25"]
        rp = _regret(point, surge, pack)
        rr = _regret(h3["robust_choice"], surge, pack)
        means = _means(surge)
        h3["truth_surge"] = {
            "point": rp,
            "robust": rr,
            "point_objective": means.get(point) if point else None,
            "robust_objective": means.get(h3["robust_choice"]) if h3["robust_choice"] else None,
        }
        if point is None or h3["robust_choice"] is None:
            h3["h3_supported"], h3["h3_basis"] = None, "a choice is missing"
        elif rp["regret"] is not None and rr["regret"] is not None:
            h3["h3_supported"] = rr["regret"] <= rp["regret"] + 1e-9
            h3["h3_basis"] = "truth regret among truth-feasible alternatives"
        elif rp["choice_feasible_in_truth"] != rr["choice_feasible_in_truth"]:
            h3["h3_supported"] = bool(rr["choice_feasible_in_truth"])
            h3["h3_basis"] = "only one choice meets the decision rule in truth"
        else:
            po, ro = h3["truth_surge"]["point_objective"], h3["truth_surge"]["robust_objective"]
            h3["h3_supported"] = None if po is None or ro is None else ro <= po + 1e-9
            h3["h3_basis"] = (
                "neither choice meets the decision rule in truth; compared on truth objective only"
            )
        report = {
            "pack": pid,
            "hidden_truth": h1,
            "selection": h2,
            "robust": h3,
            "runtime_seconds": round(time.perf_counter() - t0, 1),
        }
        rec = ledger.append(
            "experiment", {"type": "research", "report": report}, refs=[prec.record_id]
        )
        report["ledger_record"] = rec.record_id
        summary["packs"][pid] = report
        dest = out / pid / ("research-quick.json" if quick else "research.json")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
        print(
            f"{pid}: H1={h1['h1_supported']} H2={h2['h2_supported']} "
            f"H3={h3['h3_supported']} ({report['runtime_seconds']} s); wrote {dest}"
        )
    from agentic_ops_twin.reporting.research_report import render_research

    md = out / ("research-quick.md" if quick else "research.md")
    md.write_text(render_research(summary), encoding="utf-8")
    print(f"wrote {md}")
