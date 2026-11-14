"""Deterministic critic: the only path from a proposal to a runnable scenario.

It never fills in values. Missing values become operator questions (``needs_input``); invalid or
impermissible proposals are ``rejected`` with reasons; only fully specified, permitted, budget-
and control-compliant proposals become a ``ChangeSet`` (``ok``).
"""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from agentic_ops_twin.agent.contracts import Critique, ScenarioProposal
from agentic_ops_twin.decision.scenarios import (
    Change,
    ChangeRejected,
    ChangeSet,
    apply_changes,
    check_changes,
)
from agentic_ops_twin.packs.base import DomainPack
from agentic_ops_twin.simulation.validate import Issue

# Issues the proposer may get one chance to fix; control and scope issues are never repairable.
REPAIRABLE = frozenset(
    {"invalid_output", "unknown_lever", "out_of_bounds", "bad_value", "unknown_condition"}
)


def _err(code: str, path: str, msg: str) -> Issue:
    return Issue(severity="error", code=code, path=path, message=msg)


def parse_proposal(raw: str) -> tuple[ScenarioProposal | None, list[Issue]]:
    text = raw.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.S)
    if fence:
        text = fence.group(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, [_err("invalid_output", "proposal", f"not valid JSON: {exc.msg}")]
    try:
        return ScenarioProposal.model_validate(data), []
    except ValidationError as exc:
        msgs = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
        return None, [_err("invalid_output", "proposal", f"schema violation: {msgs}")]


def _touches_control(lever: str, pack: DomainPack) -> bool:
    lowered = lever.lower()
    names = {c.id.lower() for c in pack.model.controls} | {
        c.step.lower() for c in pack.model.controls
    }
    return any(n in lowered for n in names)


def critique(proposal: ScenarioProposal, pack: DomainPack) -> Critique:
    issues: list[Issue] = []
    questions: list[str] = []
    if proposal.pack_id != pack.id:
        issues.append(
            _err(
                "wrong_pack",
                "pack_id",
                f"proposal targets '{proposal.pack_id}', expected '{pack.id}'",
            )
        )
    if not proposal.in_scope:
        issues.append(
            _err(
                "out_of_scope",
                "request",
                "request is not a what-if over this pack's permitted levers "
                "(the prototype never changes live systems)",
            )
        )
    seen: dict[str, int | str | None] = {}
    for ch in proposal.changes:
        if ch.lever in seen and seen[ch.lever] != ch.value:
            issues.append(
                _err(
                    "contradiction",
                    f"changes.{ch.lever}",
                    f"conflicting values {seen[ch.lever]!r} and {ch.value!r}",
                )
            )
        seen[ch.lever] = ch.value
        if _touches_control(ch.lever, pack):
            issues.append(
                _err(
                    "control_locked",
                    f"changes.{ch.lever}",
                    "mandatory controls cannot be removed, bypassed or changed",
                )
            )
    if any(
        i.code in {"control_locked", "out_of_scope", "wrong_pack", "contradiction"} for i in issues
    ):
        return Critique(
            status="rejected",
            issues=issues,
            questions=[],
            change_set=None,
            demand_condition=None,
            repairable=False,
        )

    questions.extend(proposal.unknowns)
    for ch in proposal.changes:
        if ch.value is None:
            questions.append(f"What value should '{ch.lever}' take?")
    conditions = {c.name for c in (*pack.splits.search_conditions, *pack.splits.heldout_conditions)}
    if proposal.demand_condition is None:
        questions.append(
            f"Which demand condition should be simulated? Options: {', '.join(sorted(conditions))}."
        )
    elif proposal.demand_condition not in conditions:
        issues.append(
            _err(
                "unknown_condition",
                "demand_condition",
                f"'{proposal.demand_condition}' is not a declared condition",
            )
        )

    concrete = [
        Change(lever=c.lever, value=c.value) for c in proposal.changes if c.value is not None
    ]
    current = ChangeSet(name="proposal", changes=tuple(concrete))
    issues.extend(check_changes(pack.model, pack.decision_space, current))
    if issues:
        return Critique(
            status="rejected",
            issues=issues,
            questions=questions,
            change_set=None,
            demand_condition=None,
            repairable=all(i.code in REPAIRABLE for i in issues),
        )
    if questions:
        return Critique(
            status="needs_input",
            issues=[],
            questions=questions,
            change_set=None,
            demand_condition=proposal.demand_condition,
            repairable=False,
        )
    try:
        apply_changes(pack.model, pack.decision_space, current)
    except ChangeRejected as exc:
        return Critique(
            status="rejected",
            issues=exc.issues,
            questions=[],
            change_set=None,
            demand_condition=None,
            repairable=False,
        )
    label = ChangeSet(name="proposal", changes=current.changes).label()
    return Critique(
        status="ok",
        issues=[],
        questions=[],
        change_set=ChangeSet(name=f"proposal:{label}", changes=current.changes),
        demand_condition=proposal.demand_condition,
        repairable=False,
    )
