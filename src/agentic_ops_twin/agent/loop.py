"""Bounded proposal loop: propose -> critique -> (at most one repair) -> stop.

An explicit four-state machine rather than an agent framework: the control flow is small,
auditable and identical for the scripted fake and a real model. The loop never runs a simulation
itself; it only produces a validated ``ChangeSet`` (or an explicit stop).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from agentic_ops_twin.agent.contracts import (
    Critique,
    Proposer,
    ProposerOutput,
    ScenarioProposal,
    Usage,
    pack_context,
)
from agentic_ops_twin.agent.critic import critique, parse_proposal
from agentic_ops_twin.decision.scenarios import ChangeSet
from agentic_ops_twin.packs.base import DomainPack
from agentic_ops_twin.simulation.validate import Issue

Status = Literal[
    "ok", "needs_input", "rejected", "invalid_output", "provider_error", "budget_exhausted"
]


class Attempt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    index: int
    raw_text: str | None
    proposal: ScenarioProposal | None
    critique: Critique | None
    parse_issues: list[Issue]
    usage: Usage | None
    error: str | None


class ProposalOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request: str
    pack_id: str
    proposer: str
    proposer_kind: Literal["scripted", "model"]
    status: Status
    change_set: ChangeSet | None
    demand_condition: str | None
    questions: list[str]
    issues: list[Issue]
    attempts: list[Attempt]


class BudgetExhausted(RuntimeError):
    pass


def run_proposal(
    request: str, pack: DomainPack, proposer: Proposer, max_repairs: int = 1
) -> ProposalOutcome:
    if not 0 <= max_repairs <= 1:
        raise ValueError("at most one repair round is permitted")
    ctx = pack_context(pack)
    attempts: list[Attempt] = []
    feedback: list[str] | None = None

    def finish(status: Status, crit: Critique | None, issues: list[Issue]) -> ProposalOutcome:
        return ProposalOutcome(
            request=request,
            pack_id=pack.id,
            proposer=proposer.name,
            proposer_kind=proposer.kind,
            status=status,
            change_set=crit.change_set if crit and status == "ok" else None,
            demand_condition=crit.demand_condition if crit and status == "ok" else None,
            questions=crit.questions if crit else [],
            issues=issues,
            attempts=attempts,
        )

    for i in range(max_repairs + 1):
        try:
            out: ProposerOutput = proposer.propose(request, ctx, feedback)
        except BudgetExhausted as exc:
            attempts.append(
                Attempt(
                    index=i,
                    raw_text=None,
                    proposal=None,
                    critique=None,
                    parse_issues=[],
                    usage=None,
                    error=str(exc),
                )
            )
            return finish("budget_exhausted", None, [])
        except Exception as exc:  # provider/network failure: stop, never guess
            attempts.append(
                Attempt(
                    index=i,
                    raw_text=None,
                    proposal=None,
                    critique=None,
                    parse_issues=[],
                    usage=None,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            return finish("provider_error", None, [])
        proposal, parse_issues = parse_proposal(out.raw_text)
        crit = critique(proposal, pack) if proposal is not None else None
        attempts.append(
            Attempt(
                index=i,
                raw_text=out.raw_text,
                proposal=proposal,
                critique=crit,
                parse_issues=parse_issues,
                usage=out.usage,
                error=None,
            )
        )
        if crit is None:
            if i < max_repairs:
                feedback = [f"{x.code}: {x.message}" for x in parse_issues]
                continue
            return finish("invalid_output", None, parse_issues)
        if crit.status == "rejected" and crit.repairable and i < max_repairs:
            feedback = [f"{x.code} at {x.path}: {x.message}" for x in crit.issues]
            continue
        return finish(crit.status, crit, crit.issues)
    raise AssertionError("unreachable")
