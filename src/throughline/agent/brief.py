"""Evidence-linked decision brief built only from stored simulation outputs.

The brief is a draft for human review. It never recommends deployment and the prototype has no
connection to live systems. Every number in the brief is a fact extracted from a stored ledger
record; narratives (template or model) must pass ``check_grounding`` or they are dropped.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict

from throughline.agent.grounding import Fact, GroundingResult, check_grounding
from throughline.core.model import OperatingModel
from throughline.study import HeldOutRow

BRIEF_METRICS: tuple[tuple[str, str, str], ...] = (
    ("objective_cost_per_case", "cost per case incl. SLA penalty", "currency"),
    ("cost_per_completion", "cost per completed case", "currency"),
    ("cycle_median_hours", "median cycle time (completed)", "hours"),
    ("cycle_p95_hours", "p95 cycle time (completed)", "hours"),
    ("completion_rate", "completion rate", "share"),
    ("sla_attainment", "SLA attainment (open = miss)", "share"),
    ("open", "open cases at horizon", "cases"),
    ("escalations", "manual escalations", "cases"),
)

STANDING_LIMITATIONS = (
    "Results are simulated counterfactuals conditional on the stated operating model and "
    "assumptions; they are not causal estimates or forecasts.",
    "Parameters are synthetic and hand-authored; no real operational data was used or validated.",
    "Approval of this brief records a decision for discussion only. Nothing is deployed and the "
    "prototype has no connection to live systems.",
)


class Brief(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pack_id: str
    subject: str
    source_record: str
    model_digest: str
    facts: list[Fact]
    narrative: str
    narrative_source: str
    narrative_grounding: GroundingResult
    rejected_narrative: str | None
    rejected_narrative_problems: list[str]
    markdown: str


class Narrator(Protocol):
    name: str

    def narrate(self, facts_text: str) -> tuple[str, object]: ...


def _fmt_diff(value: float, unit: str) -> str:
    if unit == "share":
        return f"{value * 100:+.1f} pts"
    return f"{value:+.2f}"


def _fmt(value: float, unit: str) -> str:
    if unit == "share":
        return f"{value * 100:.1f}%"
    if unit == "cases":
        return f"{value:.1f}"
    return f"{value:.2f}"


def build_facts(
    rows: Sequence[HeldOutRow], baseline_rows: Sequence[HeldOutRow], source_record: str
) -> list[Fact]:
    facts: list[Fact] = []

    def add(path: str, value: float | None, unit: str) -> None:
        if value is None:
            return
        facts.append(
            Fact(
                id=f"F{len(facts) + 1}",
                source_record=source_record,
                path=path,
                value=float(value),
                unit=unit,
                display=_fmt(float(value), unit),
            )
        )

    base_by_cond = {b.condition: b for b in baseline_rows}
    for row in rows:
        base = base_by_cond.get(row.condition)
        for metric, _, unit in BRIEF_METRICS:
            if base is not None:
                add(
                    f"heldout[{row.condition}][baseline].{metric}.mean",
                    base.summary[metric].mean,
                    unit,
                )
            add(
                f"heldout[{row.condition}][{row.alternative}].{metric}.mean",
                row.summary[metric].mean,
                unit,
            )
            d = row.vs_baseline.get(metric)
            if d is not None and d.mean_difference is not None:
                add(
                    f"heldout[{row.condition}][{row.alternative}].vs_baseline.{metric}.diff",
                    d.mean_difference,
                    unit if unit != "share" else "share",
                )
                add(
                    f"heldout[{row.condition}][{row.alternative}].vs_baseline.{metric}.ci_low",
                    d.ci95_low,
                    unit,
                )
                add(
                    f"heldout[{row.condition}][{row.alternative}].vs_baseline.{metric}.ci_high",
                    d.ci95_high,
                    unit,
                )
    return facts


def _find(facts: list[Fact], suffix: str) -> Fact | None:
    return next((f for f in facts if f.path.endswith(suffix)), None)


class TemplateNarrator:
    """Deterministic offline narrator; writes only cited, fact-backed sentences."""

    name = "template-v1"

    def __init__(self, rows: Sequence[HeldOutRow]) -> None:
        self.rows = rows

    def narrate(self, facts: list[Fact]) -> str:
        out: list[str] = []
        for row in self.rows:
            for metric, label, _unit in BRIEF_METRICS[:6]:
                d = row.vs_baseline.get(metric)
                f_alt = _find(facts, f"[{row.condition}][{row.alternative}].{metric}.mean")
                f_base = _find(facts, f"[{row.condition}][baseline].{metric}.mean")
                if d is None or f_alt is None or f_base is None or d.better == "unavailable":
                    continue
                if d.better == "inconclusive":
                    phrase = "with no clear difference from the baseline"
                else:
                    direction = "lower" if (d.mean_difference or 0) < 0 else "higher"
                    judgement = "an improvement" if d.better == "alternative" else "a deterioration"
                    phrase = f"{direction} than the baseline ({judgement})"
                out.append(
                    f"Under the `{row.condition}` condition, {label} is "
                    f"{f_alt.display} [{f_alt.id}] versus {f_base.display} "
                    f"[{f_base.id}] for the baseline, {phrase}; {d.method} comparison."
                )
        if not out:
            return "No stored comparison results were available, so no summary is given."
        out.append("These are simulated outcomes conditional on the stated assumptions.")
        return " ".join(out)


def facts_text(facts: list[Fact]) -> str:
    return "\n".join(f"[{f.id}] {f.path} = {f.display}" for f in facts)


def build_brief(
    *,
    pack_id: str,
    subject: str,
    source_record: str,
    model: OperatingModel,
    rows: Sequence[HeldOutRow],
    baseline_rows: Sequence[HeldOutRow],
    extra_notes: Sequence[str] = (),
    narrator: Narrator | None = None,
) -> Brief:
    facts = build_facts(rows, baseline_rows, source_record)
    template = TemplateNarrator(rows).narrate(facts)
    narrative, source = template, TemplateNarrator.name
    rejected: str | None = None
    rejected_problems: list[str] = []
    if narrator is not None:
        try:
            text, _usage = narrator.narrate(facts_text(facts))
        except Exception as exc:  # provider failure: keep the template
            text = ""
            rejected_problems = [f"narrator failed: {type(exc).__name__}: {exc}"]
        if text:
            g = check_grounding(text, facts)
            if g.grounded:
                narrative, source = text, narrator.name
            else:
                rejected, rejected_problems = text, g.problems
    grounding = (
        check_grounding(narrative, facts) if facts else GroundingResult(grounded=True, problems=[])
    )

    lines = [
        f"# Decision brief (draft): {subject}",
        "",
        "**Status:** draft for named human review. Approval records a decision for discussion "
        "only; nothing is deployed.",
        "",
        f"- Pack: `{pack_id}`; model `{model.id}` v{model.version}, digest `{model.digest()[:16]}`",
        f"- Evidence: ledger record `{source_record}`",
        f"- Narrative source: {source}; grounding check: "
        f"{'passed' if grounding.grounded else 'FAILED'}",
        "",
        "## Summary",
        "",
        narrative,
        "",
        "## Evidence table",
        "",
        "| Condition | Metric | Baseline | Alternative | Difference (95% CI) | Method | Verdict |",
        "|---|---|---|---|---|---|---|",
    ]
    base_by_cond = {b.condition: b for b in baseline_rows}
    for row in rows:
        base = base_by_cond.get(row.condition)
        for metric, label, unit in BRIEF_METRICS:
            b = base.summary[metric].mean if base else None
            a = row.summary[metric].mean
            d = row.vs_baseline.get(metric)
            diff = "n/a"
            if d is not None and d.mean_difference is not None:
                diff = (
                    f"{_fmt_diff(d.mean_difference, unit)} ("
                    f"{_fmt_diff(d.ci95_low or 0, unit)} to "
                    f"{_fmt_diff(d.ci95_high or 0, unit)})"
                )
            lines.append(
                f"| {row.condition} | {label} | {_fmt(b, unit) if b is not None else 'n/a'} | "
                f"{_fmt(a, unit) if a is not None else 'n/a'} | {diff} | "
                f"{d.method if d else 'n/a'} | {d.better if d else 'n/a'} |"
            )
    lines += ["", "## Constraint checks", ""]
    for row in rows:
        lines.append(
            f"- {row.condition}: {'meets' if row.feasible else 'fails'} the decision "
            f"rule ({row.feasible_note})"
        )
    lines += ["", "## Assumptions", ""]
    lines += [f"- `{a.id}` ({a.source}): {a.text}" for a in model.assumptions]
    lines += ["", "## Limitations", ""]
    lines += [f"- {x}" for x in (*STANDING_LIMITATIONS, *extra_notes)]
    if rejected is not None or rejected_problems:
        lines += [
            "",
            "## Rejected narrative",
            "",
            "A model-written narrative failed the grounding check and was not used:",
            "",
        ]
        lines += [f"- {p}" for p in rejected_problems]
    return Brief(
        pack_id=pack_id,
        subject=subject,
        source_record=source_record,
        model_digest=model.digest(),
        facts=facts,
        narrative=narrative,
        narrative_source=source,
        narrative_grounding=grounding,
        rejected_narrative=rejected,
        rejected_narrative_problems=rejected_problems,
        markdown="\n".join(lines) + "\n",
    )


ReviewDecision = Literal["approve", "reject"]
