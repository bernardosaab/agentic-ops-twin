"""Compiled-path-first routing with explicit skips, escalation tiers and shadow mode.

Known request shapes are handled by a *compiled* path: deterministic rules that cost nothing and
behave the same every time. Work the compiled path cannot fully account for is not guessed at.
It is **skipped with a recorded reason** and escalated:

1. through optional model tiers, cheapest first, until one returns a usable proposal; or
2. to a human queue, when no tier is configured or every tier fails.

A skip happens when:

* no compiled rule matched anything in the request (and it is not a recognised out-of-scope
  request); or
* the request contains a quantity that the compiled proposal does not explain, either as a
  value or as a change from the current value. A partial reading would silently drop it.

Every routed outcome, whatever its source, still passes the same deterministic critic. Shadow
mode runs a second proposer on requests the compiled path accepted and records whether they
agree. It never changes the outcome; it produces evidence for promoting or retiring rules.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from agentic_ops_twin.agent.contracts import Proposer, pack_context
from agentic_ops_twin.agent.fake import OUT_OF_SCOPE, RESOURCE_SYNONYMS, FakeProposer
from agentic_ops_twin.agent.loop import ProposalOutcome, run_proposal
from agentic_ops_twin.packs.base import DomainPack

RouteStatus = Literal[
    "ok",
    "needs_input",
    "rejected",
    "skipped",
    "invalid_output",
    "provider_error",
    "budget_exhausted",
]
_NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?")


class RouteStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tier: str
    kind: str
    status: str
    reason: str


class RoutedOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request: str
    pack_id: str
    status: RouteStatus
    decided_by: str | None
    skip_reason: str | None
    route: list[RouteStep]
    outcome: ProposalOutcome | None
    shadow: dict[str, Any] | None


def unexplained_quantities(
    request: str, outcome: ProposalOutcome, context: dict[str, Any]
) -> list[str]:
    """Numbers in the request that no proposed value or change-from-current accounts for."""
    text = request.lower()
    for syns in RESOURCE_SYNONYMS.values():
        for syn in syns:
            if any(ch.isdigit() for ch in syn):
                text = text.replace(syn, " ")
    numbers = {float(n) for n in _NUMBER.findall(text)}
    explained: set[float] = set()
    current = {lv["key"]: lv.get("current") for lv in context["levers"]}
    proposal = outcome.attempts[-1].proposal if outcome.attempts else None
    for ch in proposal.changes if proposal else []:
        if isinstance(ch.value, int) and not isinstance(ch.value, bool):
            explained.add(float(ch.value))
            cur = current.get(ch.lever)
            if isinstance(cur, int):
                explained.add(float(abs(ch.value - cur)))
    return [f"{n:g}" for n in sorted(numbers - explained)]


class Router:
    def __init__(
        self,
        *,
        compiled: Proposer | None = None,
        tiers: Sequence[Proposer] = (),
        shadow: Proposer | None = None,
    ) -> None:
        self.compiled = compiled or FakeProposer()
        self.tiers = list(tiers)
        self.shadow = shadow
        self.name = "router[" + ",".join([self.compiled.name, *[t.name for t in self.tiers]]) + "]"

    def _skip_reason(self, request: str, out: ProposalOutcome, ctx: dict[str, Any]) -> str | None:
        lowered = request.lower()
        if (
            out.status == "rejected"
            and any(i.code == "out_of_scope" for i in out.issues)
            and not any(w in lowered for w in OUT_OF_SCOPE)
        ):
            return "no compiled rule matched the request"
        missing = unexplained_quantities(request, out, ctx)
        if missing and out.status in ("ok", "needs_input"):
            return f"quantity {', '.join(missing)} not explained by the compiled reading"
        return None

    def route(self, request: str, pack: DomainPack) -> RoutedOutcome:
        ctx = pack_context(pack)
        steps: list[RouteStep] = []
        compiled = run_proposal(request, pack, self.compiled)
        reason = self._skip_reason(request, compiled, ctx)
        steps.append(
            RouteStep(
                tier="compiled",
                kind=self.compiled.kind,
                status="skipped" if reason else compiled.status,
                reason=reason or "handled by compiled rules",
            )
        )
        if reason is None:
            shadow = None
            if self.shadow is not None:
                sh = run_proposal(request, pack, self.shadow)
                agree = sh.status == compiled.status and (
                    (sh.change_set.changes if sh.change_set else None)
                    == (compiled.change_set.changes if compiled.change_set else None)
                )
                shadow = {
                    "proposer": self.shadow.name,
                    "status": sh.status,
                    "agrees": agree,
                    "outcome": sh.model_dump(mode="json"),
                }
            return RoutedOutcome(
                request=request,
                pack_id=pack.id,
                status=compiled.status,
                decided_by=self.compiled.name,
                skip_reason=None,
                route=steps,
                outcome=compiled,
                shadow=shadow,
            )
        for tier in self.tiers:
            out = run_proposal(request, pack, tier)
            usable = out.status in ("ok", "needs_input", "rejected")
            steps.append(
                RouteStep(
                    tier=tier.name,
                    kind=tier.kind,
                    status=out.status,
                    reason="accepted" if usable else "unusable; escalate",
                )
            )
            if usable:
                return RoutedOutcome(
                    request=request,
                    pack_id=pack.id,
                    status=out.status,
                    decided_by=tier.name,
                    skip_reason=reason,
                    route=steps,
                    outcome=out,
                    shadow=None,
                )
        steps.append(
            RouteStep(
                tier="human-queue",
                kind="human",
                status="skipped",
                reason="no automated tier could handle it; routed to an operator",
            )
        )
        return RoutedOutcome(
            request=request,
            pack_id=pack.id,
            status="skipped",
            decided_by=None,
            skip_reason=reason,
            route=steps,
            outcome=None,
            shadow=None,
        )
