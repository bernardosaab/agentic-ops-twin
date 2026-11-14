"""Markdown summary of stored research results."""

from __future__ import annotations

from typing import Any


def _f(x: Any, digits: int = 3) -> str:
    if x is None:
        return "n/a"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, float):
        return f"{x:.{digits}f}"
    return str(x)


def render_research(summary: dict[str, Any]) -> str:
    out = [
        "# Research studies (pre-registered)",
        "",
        f"Pre-registration SHA-256 `{summary['preregistration_sha256'][:16]}` (ledger record "
        f"`{summary['preregistration_record']}`). Profile: "
        f"{'quick (reduced replications)' if summary['quick'] else 'full'}.",
        "",
        "| Pack | H1 ranking validity | H2 OCBA ≥ equal | H3 robust ≤ point regret | Runtime s |",
        "|---|---|---|---|---|",
    ]
    for pid, r in summary["packs"].items():
        out.append(
            f"| {pid} | {_f(r['hidden_truth']['h1_supported'])} | "
            f"{_f(r['selection']['h2_supported'])} | {_f(r['robust']['h3_supported'])} | "
            f"{r['runtime_seconds']} |"
        )
    for pid, r in summary["packs"].items():
        h1, h2, h3 = r["hidden_truth"], r["selection"], r["robust"]
        out += [
            "",
            f"## {pid}",
            "",
            "### H1: hidden-truth validation",
            "",
            f"History: {h1['history']['hours']:.0f} h, {h1['history']['arrivals']} arrivals "
            f"(seed {h1['history']['seed']}). Hidden mechanisms: "
            f"{h1['mechanisms']['note']}",
            "",
            "Residual diagnostics on the baseline log:",
            "",
        ]
        for d in h1["diagnostics"]:
            out.append(
                f"- `{d['name']}` = {_f(d['statistic'])} (threshold {d['threshold']}): "
                f"{'**flagged**' if d['flagged'] else 'not flagged'}. {d['meaning']}"
            )
        out += [
            "",
            "Baseline fit under normal demand (twin vs truth):",
            "",
            "| Metric | Truth | Twin | Relative error |",
            "|---|---|---|---|",
        ]
        for m, v in h1["baseline_fit_normal"].items():
            out.append(f"| {m} | {_f(v['truth'])} | {_f(v['twin'])} | {_f(v['relative_error'])} |")
        out += [
            "",
            "| Condition | Method | Kendall τ vs truth | Objective MAPE | Choice | "
            "Truth regret | Choice feasible in truth |",
            "|---|---|---|---|---|---|---|",
        ]
        for cname, c in h1["conditions"].items():
            for m in ("capacity_aware_twin", "uncapacitated_sim", "spreadsheet"):
                ch = c["choices"][m]
                out.append(
                    f"| {cname} | {m} | {_f(c['kendall_tau'][m])} | "
                    f"{_f(c['objective_mape'][m])} | {ch['choice']} | "
                    f"{_f(ch['regret'], 2)} | {_f(ch['choice_feasible_in_truth'])} |"
                )
            out.append(
                f"| {cname} | truth best feasible | — | — | "
                f"{c['choices']['capacity_aware_twin']['truth_best']} | — | — |"
            )
        if h1["uncalibrated"]:
            out += [
                "",
                "Kept at authored values (not observable in history): "
                + ", ".join(f"`{u}`" for u in h1["uncalibrated"]),
            ]
        out += [
            "",
            "### H2: budgeted selection (on the twin)",
            "",
            f"10 alternatives; long-run means from {h2['long_run_reps']} replications; gap "
            f"best to second {_f(h2['gap_best_to_second'], 2)}; "
            f"{h2['within_indifference_zone']} alternative(s) within δ = {h2['delta_iz']}; "
            f"{h2['macro']} macro-replications from a pool of {h2['pool_size']}.",
            "",
            "| Budget | PCS equal (±SE) | PCS OCBA (±SE) |",
            "|---|---|---|",
        ]
        for row in h2["rows"]:
            out.append(
                f"| {row['budget']} | {row['pcs_equal']:.3f} ± {row['se_equal']:.3f} | "
                f"{row['pcs_ocba']:.3f} ± {row['se_ocba']:.3f} |"
            )
        out += [
            "",
            "### H3: robustness across bootstrap parameter worlds",
            "",
            f"{h3['worlds']} worlds × {h3['seeds_per_world']} replications. Point choice "
            f"`{h3['point_choice']}`; minimax-regret choice `{h3['robust_choice']}`; point "
            f"choice fragile (feasible in < 80% of worlds): "
            f"{_f(h3['fragile_point_choice'])}.",
            "",
            "In the hidden truth under held-out +25% demand:",
            "",
            f"- point choice: objective {_f(h3['truth_surge']['point_objective'], 2)}, "
            f"meets rule {_f(h3['truth_surge']['point']['choice_feasible_in_truth'])}, "
            f"regret {_f(h3['truth_surge']['point']['regret'], 2)}",
            f"- robust choice: objective {_f(h3['truth_surge']['robust_objective'], 2)}, "
            f"meets rule {_f(h3['truth_surge']['robust']['choice_feasible_in_truth'])}, "
            f"regret {_f(h3['truth_surge']['robust']['regret'], 2)}",
            f"- basis for H3: {h3['h3_basis']}",
            "",
        ]
    out += [
        "## Reading these results",
        "",
        "- The hidden truth is itself a simulator written by the same authors; agreement "
        "with it is evidence about structural robustness to the listed mechanisms only, not "
        "about real operations.",
        "- Regret is measured against the lowest truth objective among the evaluated "
        "alternatives, not against the global optimum.",
        "- With three packs, hypothesis outcomes are descriptive; no multiplicity-corrected "
        "significance claim is made.",
    ]
    return "\n".join(out) + "\n"
