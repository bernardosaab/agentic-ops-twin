"""Grounding check for narratives: every number must come from a cited stored fact.

A narrative (template-written or model-written) passes only if:

* every citation tag ``[F<n>]`` refers to an existing fact, and
* every sentence containing a number cites at least one fact, and
* every number in that sentence equals one of its cited facts' values at some rounding
  (0-3 decimals), or the value as a percentage when followed by ``%``.

This catches invented or altered numbers and dangling citations. It does not prove the prose is
a fair summary; the brief always includes the full fact table next to any narrative.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

CITATION = re.compile(r"\[F(\d+)\]")
NUMBER = re.compile(r"(?<![\w.\[])[-+]?\d+(?:,\d{3})*(?:\.\d+)?%?")


class Fact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    source_record: str
    path: str
    value: float
    unit: str
    display: str


class GroundingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    grounded: bool
    problems: list[str]


def _matches(token: str, value: float) -> bool:
    pct = token.endswith("%")
    raw = token.rstrip("%").replace(",", "")
    try:
        num = float(raw)
    except ValueError:
        return False
    options = [value * 100, value] if pct else [value, value * 100]
    for cand in options:
        for k in range(4):
            if abs(num - round(cand, k)) <= 0.5 * 10**-k + 1e-9 and (
                k > 0 or abs(num - cand) < 1.0
            ):
                return True
    return False


def check_grounding(text: str, facts: list[Fact]) -> GroundingResult:
    by_id = {f.id: f for f in facts}
    problems: list[str] = []
    if not text.strip():
        return GroundingResult(grounded=False, problems=["empty narrative"])
    for m in CITATION.finditer(text):
        if f"F{m.group(1)}" not in by_id:
            problems.append(f"citation [F{m.group(1)}] does not refer to a stored fact")
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    for sent in sentences:
        cited = [by_id[f"F{c}"] for c in CITATION.findall(sent) if f"F{c}" in by_id]
        stripped = CITATION.sub(" ", sent)
        numbers = NUMBER.findall(stripped)
        if not numbers:
            continue
        if not cited:
            problems.append(f"uncited number(s) {numbers} in: {sent.strip()[:120]!r}")
            continue
        for tok in numbers:
            if not any(_matches(tok, f.value) for f in cited):
                problems.append(
                    f"number {tok} does not match its cited fact(s) "
                    f"{[f.id for f in cited]} in: {sent.strip()[:120]!r}"
                )
    return GroundingResult(grounded=not problems, problems=problems)
