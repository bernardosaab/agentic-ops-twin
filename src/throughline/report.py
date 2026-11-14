"""Markdown rendering of stored study results (numbers come only from the study object)."""

from __future__ import annotations

from throughline.core.stats import Estimate
from throughline.study import DecisionStudy


def _e(est: Estimate | None, pct: bool = False, digits: int = 2) -> str:
    if est is None or est.mean is None:
        return "n/a"
    if pct:
        s = f"{est.mean * 100:.1f}%"
        if est.ci95_low is not None and est.ci95_high is not None:
            s += f" ({est.ci95_low * 100:.1f}–{est.ci95_high * 100:.1f})"
        return s
    s = f"{est.mean:.{digits}f}"
    if est.ci95_low is not None and est.ci95_high is not None:
        s += f" ({est.ci95_low:.{digits}f}–{est.ci95_high:.{digits}f})"
    return s


def render_study(s: DecisionStudy) -> str:
    alts = {a.name: a for a in s.alternatives}
    out = [
        f"# Decision study: {s.pack_title}",
        "",
        f"Model `{s.model_id}` v{s.model_version} (digest `{s.model_digest[:16]}`), generator "
        f"`{s.generator_version}`, exogenous scheme `{s.exogenous_scheme}`, profile "
        f"`{s.profile}`. {s.simulated_replications} simulated replications in "
        f"{s.runtime_seconds:.1f} s.",
        "",
        f"Search split: seeds {s.search_seeds[0]}–{s.search_seeds[-1]} "
        f"({len(s.search_seeds)}), conditions {[c.name for c in s.search_conditions]}. "
        f"Held-out split: seeds {s.heldout_seeds[0]}–{s.heldout_seeds[-1]} "
        f"({len(s.heldout_seeds)}), conditions {[c.name for c in s.heldout_conditions]}.",
        "",
        f"Decision rule (declared before search): minimise `{s.decision_rule.objective}` subject "
        f"to mean completion rate >= {s.decision_rule.min_completion_rate} and mean SLA "
        f"attainment >= {s.decision_rule.min_sla_attainment}.",
        "",
        f"Enumerated {s.n_enumerated} lever combinations: {len(s.alternatives)} evaluated, "
        f"{len(s.rejected)} rejected (budget, bounds or controls), {s.n_equivalent} "
        f"behaviourally equivalent duplicates skipped.",
        "",
        "## Selections by method (search split)",
        "",
        "| Method | Selected alternative | Objective on search split (capacity-aware, 95% CI) |",
        "|---|---|---|",
    ]
    for method, name in s.selections.items():
        if name is None:
            out.append(f"| {method} | none feasible | n/a |")
        else:
            out.append(
                f"| {method} | {alts[name].label} | "
                f"{_e(alts[name].search['objective_cost_per_case'])} |"
            )
    out += [
        "",
        "## Held-out evaluation (capacity-aware simulation)",
        "",
        "Mean (95% CI) across held-out replications. Differences are versus baseline under "
        "the same condition; `paired` only where arrival-stream digests were verified "
        "identical.",
        "",
        "| Condition | Alternative | Roles | Objective | p95 h (completed) | Completion | "
        "SLA | Open | Δ objective vs baseline | Rule |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in s.heldout:
        d = r.vs_baseline["objective_cost_per_case"]
        diff = (
            "—"
            if r.alternative == "baseline" or d.mean_difference is None
            else (
                f"{d.mean_difference:+.2f} ({d.ci95_low:+.2f} to {d.ci95_high:+.2f}) {d.method}, "
                f"{d.better}"
            )
        )
        out.append(
            f"| {r.condition} | {r.label} | {', '.join(r.roles)} | "
            f"{_e(r.summary['objective_cost_per_case'])} | {_e(r.summary['cycle_p95_hours'])} | "
            f"{_e(r.summary['completion_rate'], pct=True)} | "
            f"{_e(r.summary['sla_attainment'], pct=True)} | {_e(r.summary['open'], digits=1)} | "
            f"{diff} | {'meets' if r.feasible else 'fails'} |"
        )
    if s.automation_effects:
        out += [
            "",
            "## Automation-only changes (search split)",
            "",
            "Change in mean utilisation by resource when only the automation variant is "
            "switched on. A rise of at least 5 points is flagged as a downstream load "
            "increase.",
            "",
        ]
        for ef in s.automation_effects:
            ups = (
                ", ".join(
                    f"{k} {v * 100:+.1f} pts"
                    for k, v in ef.utilisation_change.items()
                    if abs(v) >= 0.005
                )
                or "none"
            )
            od, pd = ef.objective_difference, ef.p95_difference
            out.append(
                f"- `{ef.label}`: utilisation changes {ups}; flagged: "
                f"{list(ef.downstream_load_increase) or 'none'}; objective difference "
                f"{od.mean_difference:+.2f} ({od.method}, {od.better}); p95 difference "
                f"{pd.mean_difference:+.2f} h ({pd.better})."
            )
    if s.sensitivity:
        out += [
            "",
            "## Sensitivity (held-out seeds, first held-out condition)",
            "",
            "| Parameter | Value | Alternative | Objective | SLA | Rule | Δ objective vs "
            "baseline |",
            "|---|---|---|---|---|---|---|",
        ]
        for row in s.sensitivity:
            dv = row.vs_baseline
            dtxt = (
                "—"
                if dv is None or dv.mean_difference is None
                else (f"{dv.mean_difference:+.2f} ({dv.better})")
            )
            out.append(
                f"| {row.parameter} | {row.value:g} | {row.alternative} | "
                f"{_e(row.summary['objective_cost_per_case'])} | "
                f"{_e(row.summary['sla_attainment'], pct=True)} | "
                f"{'meets' if row.feasible else 'fails'} | {dtxt} |"
            )
    out += ["", "## Pairing verification", ""]
    out += [f"- {p}" for p in s.pairing_checks[:6]]
    if len(s.pairing_checks) > 6:
        out.append(f"- ... {len(s.pairing_checks) - 6} more checks in study.json")
    out += [
        "",
        "## Interpretation limits",
        "",
        "- Simulated counterfactuals are conditional on this synthetic model; they are not "
        "causal estimates or forecasts.",
        "- The capacity-aware selection is re-evaluated on held-out seeds and demand, but "
        "the alternative set and decision rule were authored with knowledge of the model.",
        "- Spreadsheet and uncapacitated choices are scored here by the capacity-aware "
        "simulation, which is itself only a model.",
    ]
    return "\n".join(out) + "\n"
