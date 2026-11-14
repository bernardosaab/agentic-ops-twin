"""Scripted offline proposer.

Deterministic keyword and regular-expression rules, written by hand for the synthetic packs.
It exists so the offline demo, tests and critic can run without a model. It is **not** a model,
and its scores on the labelled requests are **not** a measurement of AI performance: the rules
and the requests were written by the same authors.
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from agentic_ops_twin.agent.contracts import ProposerOutput

NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "a": 1,
    "an": 1,
    "another": 1,
}

# Hand-written synonyms for resources and steps in the synthetic packs.
RESOURCE_SYNONYMS: dict[str, tuple[str, ...]] = {
    "adjuster": ("adjusters", "adjuster", "reviewers", "reviewer", "claims handlers"),
    "triage_officer": ("triage officers", "triage officer", "triage staff"),
    "fraud_analyst": ("fraud analysts", "fraud analyst"),
    "ap_clerk": ("ap clerks", "ap clerk", "accounts-payable clerks"),
    "buyer": ("buyers", "buyer"),
    "receiving_clerk": ("receiving clerks", "receiving clerk"),
    "tier1_agent": (
        "tier 1 agents",
        "tier-1 agents",
        "tier 1 agent",
        "tier-1 agent",
        "first-line agents",
    ),
    "tier2_agent": ("tier 2 agents", "tier-2 agents", "tier 2 agent", "tier-2 agent"),
    "specialist": ("specialists", "specialist"),
}
STEP_SYNONYMS: dict[str, tuple[str, ...]] = {
    "triage": ("triage",),
    "classify": ("classification", "classify", "classifying"),
    "routing": ("routing", "ticket routing"),
}
CONDITION_SYNONYMS: dict[str, tuple[str, ...]] = {
    "surge_25": ("surge", "25% more", "25 percent more", "higher demand", "peak demand"),
    "normal": (
        "normal demand",
        "current demand",
        "today's demand",
        "usual demand",
        "normal volume",
        "current volume",
    ),
    "complex_mix": ("complex mix", "more complex claims"),
    "receipt_heavy": ("receipt heavy", "receipt-heavy", "more missing receipts"),
    "billing_spike": ("billing spike", "more billing disputes"),
}
CONTROL_WORDS: dict[str, tuple[str, ...]] = {
    "fraud_check": ("fraud check", "fraud review"),
    "senior_approval": ("senior approval", "approval step"),
    "three_way_match": ("three-way match", "three way match", "matching control"),
    "sod_approval": ("segregation of duties", "finance approval", "sod approval"),
    "qa_review": ("qa review", "refund qa", "quality review"),
}
OUT_OF_SCOPE = (
    "deploy",
    "production",
    "go live",
    "live system",
    "send an email",
    "write a poem",
    "change the erp",
    "update the crm",
)
REMOVE_VERBS = r"(?:skip|bypass|remove|waive|drop|eliminate|without|turn off)"


def _num(tok: str) -> int | None:
    if tok.isdigit():
        return int(tok)
    return NUMBER_WORDS.get(tok)


class FakeProposer:
    name = "scripted-fake-v1"
    kind: Literal["scripted", "model"] = "scripted"

    def propose(
        self, request: str, context: dict[str, Any], feedback: list[str] | None = None
    ) -> ProposerOutput:
        text = " " + request.lower().replace("\n", " ") + " "
        levers = {lv["key"]: lv for lv in context["levers"]}
        changes: list[dict[str, Any]] = []
        unknowns: list[str] = []
        matched_any = False

        for ctl in context["mandatory_controls"]:
            words = CONTROL_WORDS.get(ctl["step"], ())
            if any(re.search(REMOVE_VERBS + r"\b[^.]*\b" + re.escape(w), text) for w in words):
                changes.append({"lever": f"remove_control:{ctl['id']}", "value": "removed"})
                matched_any = True

        num = r"(\d+|one|two|three|four|five|six|a|an|another)"
        for key, lv in levers.items():
            kind, _, target = key.partition(":")
            if kind == "capacity":
                for syn in RESOURCE_SYNONYMS.get(target, (target.replace("_", " "),)):
                    s = re.escape(syn)
                    found = False
                    for m in re.finditer(
                        rf"(?:add|hire|extra|plus)\s+{num}\s+(?:more\s+)?{s}\b"
                        rf"|{num}\s+more\s+{s}\b",
                        text,
                    ):
                        n = _num(m.group(1) or m.group(2))
                        changes.append({"lever": key, "value": lv["current"] + (n or 0)})
                        found = True
                    for m in re.finditer(
                        rf"(?:remove|cut|reduce|lose|fewer)\s+(?:by\s+)?{num}\s+"
                        rf"{s}\b|{num}\s+fewer\s+{s}\b",
                        text,
                    ):
                        n = _num(m.group(1) or m.group(2))
                        changes.append({"lever": key, "value": lv["current"] - (n or 0)})
                        found = True
                    if not found:
                        am = re.search(rf"{s}\s+(?:to|at)\s+(\d+)\b|(\d+)\s+{s}\b", text)
                        if am:
                            value = int(am.group(1) or am.group(2))
                            changes.append({"lever": key, "value": value})
                            found = True
                    if not found and re.search(rf"(?:more|additional|extra|some)\s+{s}\b", text):
                        changes.append({"lever": key, "value": None})
                        unknowns.append(f"How many {syn} should the scenario use?")
                        found = True
                    if found:
                        matched_any = True
                        break
            elif kind == "variant":
                manual = "manual" if "manual" in lv["allowed"] else lv["allowed"][0]
                auto = next((a for a in lv["allowed"] if a != manual), manual)
                for syn in STEP_SYNONYMS.get(target, (target,)):
                    s = re.escape(syn)
                    if re.search(
                        rf"automat\w*\s+(?:the\s+)?{s}|{s}\s+(?:model|automation|"
                        rf"classifier)|ml[- ]assisted\s+{s}|auto[- ]?{s}",
                        text,
                    ):
                        changes.append({"lever": key, "value": auto})
                        matched_any = True
                        break
                    if re.search(rf"manual\s+{s}|{s}\s+(?:stays|remains)\s+manual", text):
                        changes.append({"lever": key, "value": manual})
                        matched_any = True
                        break
            elif kind == "priority":
                if re.search(r"high[- ]value\s+first|prioriti[sz]e\s+high[- ]value|by value", text):
                    changes.append({"lever": key, "value": "high_value_first"})
                    matched_any = True
                elif re.search(r"\bfifo\b|first[- ]in", text):
                    changes.append({"lever": key, "value": "fifo"})
                    matched_any = True

        condition = None
        for name, syns in CONDITION_SYNONYMS.items():
            if name in context["demand_conditions"] and any(s in text for s in syns):
                condition = name
                matched_any = True
                break
        if re.search(r"\bbaseline\b|current operation|as[- ]is", text):
            matched_any = True

        in_scope = matched_any and not any(w in text for w in OUT_OF_SCOPE)
        proposal = {
            "pack_id": context["pack_id"],
            "in_scope": in_scope,
            "changes": changes,
            "demand_condition": condition,
            "unknowns": unknowns,
            "rationale": "Scripted keyword mapping (not a model).",
        }
        return ProposerOutput(raw_text=json.dumps(proposal), usage=None)
