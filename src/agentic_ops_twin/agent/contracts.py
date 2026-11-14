"""Contracts between the (untrusted) scenario proposer and the trusted critic."""

from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from agentic_ops_twin.decision.scenarios import (
    CapacityLever,
    ChangeSet,
    PriorityLever,
    VariantLever,
)
from agentic_ops_twin.packs.base import DomainPack
from agentic_ops_twin.simulation.validate import Issue


class ProposedChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lever: str = Field(description="Lever key from the pack context, e.g. 'capacity:adjuster'.")
    value: int | str | None = Field(
        description="Requested value; null when the request does not state it."
    )


class ScenarioProposal(BaseModel):
    """Structured output the proposer must return. Everything in it is untrusted."""

    model_config = ConfigDict(extra="forbid")
    pack_id: str
    in_scope: bool = Field(
        description="False if the request is not a what-if over this pack's levers."
    )
    changes: list[ProposedChange]
    demand_condition: str | None = Field(
        description="A declared demand condition name, or null if the request does not say."
    )
    unknowns: list[str] = Field(
        description="Questions for the operator about values the request "
        "does not determine. Never guess them."
    )
    rationale: str = Field(max_length=600)


def proposal_json_schema() -> dict[str, Any]:
    """Strict JSON schema used for provider structured output."""
    value = {"anyOf": [{"type": "integer"}, {"type": "string"}, {"type": "null"}]}
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["pack_id", "in_scope", "changes", "demand_condition", "unknowns", "rationale"],
        "properties": {
            "pack_id": {"type": "string"},
            "in_scope": {"type": "boolean"},
            "changes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["lever", "value"],
                    "properties": {"lever": {"type": "string"}, "value": value},
                },
            },
            "demand_condition": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            "unknowns": {"type": "array", "items": {"type": "string"}},
            "rationale": {"type": "string"},
        },
    }


class Usage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str
    requested_model: str
    reported_model: str | None
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_usd: float | None
    latency_seconds: float | None
    stop_reason: str | None


class ProposerOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    raw_text: str
    usage: Usage | None


class Proposer(Protocol):
    name: str
    kind: Literal["scripted", "model"]

    def propose(
        self, request: str, context: dict[str, Any], feedback: list[str] | None = None
    ) -> ProposerOutput: ...


class Critique(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ok", "needs_input", "rejected"]
    issues: list[Issue]
    questions: list[str]
    change_set: ChangeSet | None
    demand_condition: str | None
    repairable: bool


def pack_context(pack: DomainPack) -> dict[str, Any]:
    """Synthetic pack description shared with a proposer (no secrets, no private data)."""
    levers = []
    docs = {d.key: d.meaning for d in pack.lever_docs}
    for lv in pack.decision_space.levers:
        entry: dict[str, Any] = {"key": lv.key, "meaning": docs.get(lv.key, "")}
        if isinstance(lv, CapacityLever):
            entry |= {
                "type": "integer",
                "min": lv.min,
                "max": lv.max,
                "current": pack.model.resource(lv.resource).capacity,
            }
        elif isinstance(lv, VariantLever):
            entry |= {
                "type": "choice",
                "allowed": list(lv.allowed),
                "current": pack.model.step(lv.step).active_variant,
            }
        elif isinstance(lv, PriorityLever):
            entry |= {
                "type": "choice",
                "allowed": list(lv.allowed),
                "current": pack.model.queue_policy,
            }
        levers.append(entry)
    conditions = [c.name for c in (*pack.splits.search_conditions, *pack.splits.heldout_conditions)]
    return {
        "pack_id": pack.id,
        "title": pack.title,
        "description": pack.description,
        "levers": levers,
        "demand_conditions": sorted(set(conditions)),
        "mandatory_controls": [
            {"id": c.id, "step": c.step, "description": c.description} for c in pack.model.controls
        ],
        "budget_staffed_cost_per_hour": pack.decision_space.max_staffed_cost_per_hour,
    }
