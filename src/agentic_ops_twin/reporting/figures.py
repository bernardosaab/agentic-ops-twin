"""Static figures rendered from stored results (light and dark variants).

Every plotted number is read from ``results/`` (decision studies and research reports), except
the backlog trajectories, which are re-simulated deterministically from the stored selections
on the published held-out seeds. Requires the optional ``viz`` extra (matplotlib).

Palette: the validated reference categorical slots 1-3 (blue, orange, aqua) for the three
methods, and neutral ink for the baseline and the hidden truth. Colour always follows the
entity: capacity-aware = blue, uncapacitated = orange, spreadsheet = aqua.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

THEMES: dict[str, dict[str, str]] = {
    "light": {
        "surface": "#fcfcfb",
        "text": "#0b0b0b",
        "text2": "#52514e",
        "muted": "#8a8984",
        "grid": "#e6e5e0",
        "capacity": "#2a78d6",
        "uncap": "#eb6834",
        "sheet": "#1baf7a",
        "neutral": "#8a8984",
        "band": "#f0efec",
    },
    "dark": {
        "surface": "#1a1a19",
        "text": "#f0efec",
        "text2": "#c3c2b7",
        "muted": "#8e8d86",
        "grid": "#33332f",
        "capacity": "#3987e5",
        "uncap": "#d95926",
        "sheet": "#199e70",
        "neutral": "#8e8d86",
        "band": "#262624",
    },
}
METHOD_COLOR = {
    "capacity_aware_sim": "capacity",
    "uncapacitated_sim": "uncap",
    "spreadsheet": "sheet",
    "capacity_aware_twin": "capacity",
}
METHOD_LABEL = {
    "capacity_aware_sim": "Capacity-aware simulation",
    "capacity_aware_twin": "Capacity-aware twin",
    "uncapacitated_sim": "Uncapacitated simulation",
    "spreadsheet": "Spreadsheet (average durations)",
}
PACK_TITLE = {
    "insurance": "Insurance claims",
    "procurement": "Procurement exceptions",
    "support": "Customer support",
}
PACKS = ("insurance", "procurement", "support")


def _plt(theme: dict[str, str]) -> Any:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcdefaults()
    plt.rcParams.update(
        {
            "svg.fonttype": "none",
            "font.family": "sans-serif",
            "font.sans-serif": ["Inter", "Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans"],
            "font.size": 10,
            "figure.facecolor": theme["surface"],
            "axes.facecolor": theme["surface"],
            "savefig.facecolor": theme["surface"],
            "text.color": theme["text"],
            "axes.labelcolor": theme["text2"],
            "axes.edgecolor": theme["grid"],
            "xtick.color": theme["text2"],
            "ytick.color": theme["text2"],
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": theme["grid"],
            "grid.linewidth": 0.8,
            "axes.axisbelow": True,
            "legend.frameon": False,
            "axes.titlesize": 11,
            "axes.titleweight": "semibold",
            "axes.titlecolor": theme["text"],
            "axes.titlelocation": "left",
        }
    )
    return plt


def _title(fig: Any, theme: dict[str, str], title: str, subtitle: str) -> None:
    height = fig.get_figheight()
    fig.text(
        0.012,
        1 - 0.1 / height,
        title,
        ha="left",
        va="top",
        fontsize=13,
        fontweight="bold",
        color=theme["text"],
    )
    fig.text(
        0.012, 1 - 0.38 / height, subtitle, ha="left", va="top", fontsize=9.5, color=theme["text2"]
    )


def _save(fig: Any, out: Path, name: str, mode: str) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{name}-{mode}.svg"
    fig.savefig(path, format="svg", metadata={"Date": None})
    import matplotlib.pyplot as plt

    plt.close(fig)
    return path


def _load(results: Path, pack: str, name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((results / pack / name).read_text(encoding="utf-8"))
    return data


def fig_decision_quality(results: Path, out: Path, mode: str) -> Path:
    t = THEMES[mode]
    plt = _plt(t)
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.9), sharey=True)
    series = [
        ("baseline", "Current operation", "neutral"),
        ("spreadsheet", METHOD_LABEL["spreadsheet"], "sheet"),
        ("uncapacitated_sim", METHOD_LABEL["uncapacitated_sim"], "uncap"),
        ("capacity_aware_sim", METHOD_LABEL["capacity_aware_sim"], "capacity"),
    ]
    conds = ("normal", "surge_25")
    width = 0.19
    for ax, pack in zip(axes, PACKS, strict=True):
        s = _load(results, pack, "study-full.json")
        rows = {(r["condition"], r["alternative"]): r for r in s["heldout"]}
        for i, (key, _label, color) in enumerate(series):
            name = "baseline" if key == "baseline" else s["selections"][key]
            for j, cond in enumerate(conds):
                r = rows[(cond, name)]
                e = r["summary"]["sla_attainment"]
                x = j + (i - 1.5) * (width + 0.02)
                ax.bar(x, e["mean"] * 100, width, color=t[color], linewidth=0)
                ax.errorbar(
                    x,
                    e["mean"] * 100,
                    yerr=[
                        [(e["mean"] - e["ci95_low"]) * 100],
                        [(e["ci95_high"] - e["mean"]) * 100],
                    ],
                    color=t["text2"],
                    linewidth=0.9,
                    capsize=0,
                )
                ax.text(
                    x,
                    min(e["ci95_high"] * 100, 100) + 2,
                    f"{e['mean'] * 100:.0f}",
                    ha="center",
                    va="bottom",
                    fontsize=7.5,
                    color=t["text2"],
                )
        ax.axhline(85, color=t["text"], linewidth=1, linestyle=(0, (4, 3)))
        ax.set_xticks([0, 1], ["Normal demand", "+25% surge"])
        ax.set_ylim(0, 112)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.grid(axis="x", visible=False)
        ax.set_title(PACK_TITLE[pack])
    axes[0].set_ylabel("SLA attainment, held-out (%)")
    handles = [plt.Rectangle((0, 0), 1, 1, color=t[c]) for _, _, c in series]
    handles.append(plt.Line2D([], [], color=t["text"], linewidth=1, linestyle=(0, (4, 3))))
    fig.legend(
        handles,
        [lbl for _, lbl, _ in series] + ["Decision rule: SLA ≥ 85%"],
        loc="lower center",
        ncol=5,
        fontsize=9,
        bbox_to_anchor=(0.5, -0.01),
    )
    _title(
        fig,
        t,
        "Ignoring queues picks options that fail on held-out data",
        "SLA attainment of each method's choice on held-out seeds (mean, 95% CI, 20 "
        "replications). Under the surge, no method's choice meets the rule in any pack.",
    )
    fig.subplots_adjust(top=0.78, bottom=0.2, left=0.06, right=0.99, wspace=0.08)
    return _save(fig, out, "decision-quality", mode)


def fig_calibrated_but_wrong(results: Path, out: Path, mode: str) -> Path:
    t = THEMES[mode]
    plt = _plt(t)
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.3))
    metrics = (
        ("cycle_median_hours", "Median cycle time (hours)", 1.0, "{:.1f} h"),
        ("sla_attainment", "SLA attainment (%)", 100.0, "{:.0f}%"),
    )
    for ax, (metric, label, scale, fmt) in zip(axes, metrics, strict=True):
        for k, pack in enumerate(PACKS):
            fit = _load(results, pack, "research.json")["hidden_truth"]["baseline_fit_normal"]
            twin, truth = fit[metric]["twin"] * scale, fit[metric]["truth"] * scale
            y = len(PACKS) - 1 - k
            ax.plot([twin, truth], [y, y], color=t["muted"], linewidth=2, zorder=1)
            ax.scatter(
                [truth],
                [y],
                s=70,
                color=t["neutral"],
                zorder=2,
                edgecolor=t["surface"],
                linewidth=2,
            )
            ax.scatter(
                [twin],
                [y],
                s=70,
                color=t["capacity"],
                zorder=3,
                edgecolor=t["surface"],
                linewidth=2,
            )
            lo, hi = sorted((twin, truth))
            ax.text(lo, y + 0.22, fmt.format(lo), ha="center", fontsize=8, color=t["text2"])
            ax.text(hi, y + 0.22, fmt.format(hi), ha="center", fontsize=8, color=t["text2"])
        ax.set_yticks(range(len(PACKS)), [PACK_TITLE[p] for p in reversed(PACKS)])
        ax.set_ylim(-0.6, len(PACKS) - 0.3)
        ax.set_title(label)
        ax.grid(axis="y", visible=False)
        if metric == "sla_attainment":
            ax.set_xlim(40, 104)
        else:
            ax.set_xlim(0, None)
    handles = [
        plt.Line2D([], [], marker="o", linestyle="", markersize=8, color=t["capacity"]),
        plt.Line2D([], [], marker="o", linestyle="", markersize=8, color=t["neutral"]),
    ]
    fig.legend(
        handles,
        ["Calibrated twin", "Hidden truth"],
        loc="lower center",
        ncol=2,
        fontsize=9,
        bbox_to_anchor=(0.5, -0.01),
    )
    _title(
        fig,
        t,
        "Calibrated but wrong: matching history is not accuracy",
        "Twin calibrated from 960 h of baseline history vs the hidden truth it came from "
        "(normal demand; completion rate matched within 3.3%)",
    )
    fig.subplots_adjust(top=0.76, bottom=0.2, left=0.16, right=0.98, wspace=0.35)
    return _save(fig, out, "calibrated-but-wrong", mode)


def fig_ranking_validity(results: Path, out: Path, mode: str) -> Path:
    t = THEMES[mode]
    plt = _plt(t)
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.2), sharey=True)
    methods = ("capacity_aware_twin", "uncapacitated_sim", "spreadsheet")
    offsets = {"capacity_aware_twin": 0.18, "uncapacitated_sim": 0.0, "spreadsheet": -0.18}
    for ax, cond, label in zip(
        axes, ("normal", "surge_25"), ("Normal demand", "+25% surge"), strict=True
    ):
        for k, pack in enumerate(PACKS):
            taus = _load(results, pack, "research.json")["hidden_truth"]["conditions"][cond][
                "kendall_tau"
            ]
            y = len(PACKS) - 1 - k
            ax.axhspan(y - 0.4, y + 0.4, color=t["band"], zorder=0, linewidth=0)
            for m in methods:
                v = taus[m]
                if v is None:
                    continue
                ax.scatter(
                    [v],
                    [y + offsets[m]],
                    s=60,
                    color=t[METHOD_COLOR[m]],
                    zorder=3,
                    edgecolor=t["surface"],
                    linewidth=1.5,
                )
                ax.text(
                    v + 0.03,
                    y + offsets[m],
                    f"{v:.2f}",
                    va="center",
                    fontsize=7.5,
                    color=t["text2"],
                )
        ax.set_xlim(0, 1.08)
        ax.set_title(label)
        ax.set_yticks(range(len(PACKS)), [PACK_TITLE[p] for p in reversed(PACKS)])
        ax.grid(axis="y", visible=False)
        ax.set_xlabel("Kendall τ between predicted and true ranking (higher is better)")
    handles = [
        plt.Line2D([], [], marker="o", linestyle="", markersize=8, color=t[METHOD_COLOR[m]])
        for m in methods
    ]
    fig.legend(
        handles,
        [METHOD_LABEL[m] for m in methods],
        loc="lower center",
        ncol=3,
        fontsize=9,
        bbox_to_anchor=(0.5, -0.02),
    )
    _title(
        fig,
        t,
        "Does each method rank options the way the hidden truth does?",
        "Pre-registered H1 across 12 alternatives per pack, 8 validation replications. "
        "Supported in insurance and procurement, not in support under surge.",
    )
    fig.subplots_adjust(top=0.76, bottom=0.27, left=0.16, right=0.98, wspace=0.08)
    return _save(fig, out, "ranking-validity", mode)


def _backlog_series(pack_id: str, study: dict[str, Any], condition: str) -> dict[str, np.ndarray]:
    from agentic_ops_twin.decision.experiment import Job, run_jobs
    from agentic_ops_twin.decision.scenarios import Change, ChangeSet, apply_changes
    from agentic_ops_twin.packs import get_pack

    pack = get_pack(pack_id)
    cond = pack.condition(condition)
    alts = {a["name"]: a for a in study["alternatives"]}
    seeds = tuple(study["heldout_seeds"])
    jobs = []
    keys = []
    for key in ("baseline", "uncapacitated_sim", "capacity_aware_sim"):
        name = "baseline" if key == "baseline" else study["selections"][key]
        cs = ChangeSet(name=name, changes=tuple(Change(**c) for c in alts[name]["changes"]))
        model, _ = apply_changes(pack.model, pack.decision_space, cs)
        jobs.append(Job(model, seeds, cond, name, key))
        keys.append(key)
    out = {}
    for key, res in zip(keys, run_jobs(jobs), strict=True):
        out[key] = np.mean([np.array(r.backlog_hourly, dtype=float) for r in res.runs], axis=0)
    return out


def fig_backlog(results: Path, out: Path, mode: str, cache: dict[str, Any]) -> Path:
    t = THEMES[mode]
    plt = _plt(t)
    study = _load(results, "insurance", "study-full.json")
    if "backlog" not in cache:
        cache["backlog"] = _backlog_series("insurance", study, "surge_25")
    series = cache["backlog"]
    fig, ax = plt.subplots(figsize=(11, 3.6))
    warm = 40
    ax.axvspan(0, warm, color=t["band"], linewidth=0, zorder=0)
    ax.text(
        warm / 2,
        0.97,
        "warm-up",
        transform=ax.get_xaxis_transform(),
        ha="center",
        va="top",
        fontsize=8,
        color=t["text2"],
    )
    styles = (
        ("baseline", "Current operation", "neutral"),
        ("uncapacitated_sim", "Uncapacitated choice (cuts an adjuster)", "uncap"),
        ("capacity_aware_sim", "Capacity-aware choice", "capacity"),
    )
    for key, label, color in styles:
        y = series[key]
        x = np.arange(len(y))
        ax.plot(x, y, color=t[color], linewidth=2, label=label)
        ax.text(
            x[-1] + 4, y[-1], f"{label}  {y[-1]:.0f}", va="center", fontsize=8.5, color=t["text"]
        )
    ax.set_xlim(0, len(series["baseline"]) + 150)
    ax.set_ylim(0, None)
    ax.set_xlabel("Operating hours")
    ax.set_ylabel("Cases in the system")
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper left", bbox_to_anchor=(0.13, 1.0), fontsize=8.5)
    ratio = series["uncapacitated_sim"][-1] / series["capacity_aware_sim"][-1]
    _title(
        fig,
        t,
        f"Under a 25% surge, the cheaper option ends with {ratio:.1f}× the backlog",
        "Insurance pack, mean work-in-progress across the 20 held-out replications "
        "(re-simulated from the stored selections)",
    )
    fig.subplots_adjust(top=0.8, bottom=0.15, left=0.07, right=0.99)
    return _save(fig, out, "backlog-surge", mode)


def fig_downstream_shift(results: Path, out: Path, mode: str) -> Path:
    t = THEMES[mode]
    plt = _plt(t)
    study = _load(results, "insurance", "study-full.json")
    alts = {a["name"]: a for a in study["alternatives"]}
    effect = next(e for e in study["automation_effects"])
    base = alts["baseline"]["mean_utilisation"]
    auto = alts[effect["alternative"]]["mean_utilisation"]
    resources = [
        r
        for r in (
            "intake_clerk",
            "triage_officer",
            "triage_model",
            "adjuster",
            "fraud_analyst",
            "senior_approver",
        )
        if base.get(r) is not None or auto.get(r) is not None
    ]
    fig, ax = plt.subplots(figsize=(11, 3.4))
    h = 0.36
    for k, r in enumerate(resources):
        y = len(resources) - 1 - k
        for off, val, color in (
            (h / 2 + 0.02, base.get(r), "neutral"),
            (-h / 2 - 0.02, auto.get(r), "capacity"),
        ):
            if val is None:
                ax.text(1, y + off, "not staffed", va="center", fontsize=7.5, color=t["muted"])
                continue
            ax.barh(y + off, val * 100, h, color=t[color], linewidth=0)
            ax.text(
                val * 100 + 1,
                y + off,
                f"{val * 100:.0f}%",
                va="center",
                fontsize=7.5,
                color=t["text2"],
            )
    ax.set_yticks(range(len(resources)), [r.replace("_", " ") for r in reversed(resources)])
    ax.set_xlim(0, 105)
    ax.set_xlabel("Mean utilisation, search split (%)")
    ax.grid(axis="y", visible=False)
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=t["neutral"]),
        plt.Rectangle((0, 0), 1, 1, color=t["capacity"]),
    ]
    ax.legend(
        handles, ["Manual triage (current)", "Automated triage"], loc="lower right", fontsize=8.5
    )
    up = effect["utilisation_change"].get("adjuster", 0.0) * 100
    _title(
        fig,
        t,
        "Automating triage moves work downstream",
        f"Insurance pack: the model's 22% fallout lands on adjusters (+{up:.1f} pts), "
        "while total cost per case still falls",
    )
    fig.subplots_adjust(top=0.78, bottom=0.16, left=0.13, right=0.99)
    return _save(fig, out, "downstream-shift", mode)


def render_all(results: Path, out: Path) -> list[Path]:
    paths: list[Path] = []
    cache: dict[str, Any] = {}
    for mode in ("light", "dark"):
        paths.append(fig_decision_quality(results, out, mode))
        paths.append(fig_calibrated_but_wrong(results, out, mode))
        paths.append(fig_ranking_validity(results, out, mode))
        paths.append(fig_backlog(results, out, mode, cache))
        paths.append(fig_downstream_shift(results, out, mode))
    return paths
