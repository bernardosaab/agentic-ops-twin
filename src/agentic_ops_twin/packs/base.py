"""Shared domain-pack contract and authoring helpers.

A domain pack is data plus an adapter: an operating model, a bounded decision space, published
seed splits, sensitivity ranges, a pre-declared decision rule, and (for validation studies only)
hidden-truth mechanisms. Every pack runs on the same engine and interfaces.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from agentic_ops_twin.decision.experiment import Splits
from agentic_ops_twin.decision.scenarios import DecisionSpace
from agentic_ops_twin.simulation.engine import HiddenMechanisms
from agentic_ops_twin.simulation.exogenous import DemandCondition
from agentic_ops_twin.simulation.model import Frozen, OperatingModel

GENERATOR_VERSION = "packs-v1"


class SensitivityParam(Frozen):
    name: str
    kind: Literal["arrival", "service_scale", "branch_probability"]
    target: str | None = Field(
        description="service_scale: resource name; branch_probability: Branch.param name; "
        "arrival: None (all case types)."
    )
    low: float = Field(gt=0)
    high: float = Field(gt=0)


class DecisionRule(Frozen):
    """Pre-declared before any search: minimise the objective subject to service constraints."""

    objective: Literal["objective_cost_per_case"] = "objective_cost_per_case"
    min_completion_rate: float = Field(ge=0, le=1)
    min_sla_attainment: float = Field(ge=0, le=1)


class HiddenTruth(Frozen):
    """Mechanisms the twin omits. Used only by the validation study, never by search."""

    mechanisms: HiddenMechanisms
    hourly_profile: tuple[float, ...] = Field(min_length=24, max_length=24)
    note: str


class LeverDoc(Frozen):
    key: str
    meaning: str


class DomainPack(Frozen):
    id: str
    title: str
    description: str
    generator_version: str
    model: OperatingModel
    decision_space: DecisionSpace
    lever_docs: tuple[LeverDoc, ...]
    splits: Splits
    decision_rule: DecisionRule
    sensitivity: tuple[SensitivityParam, ...]
    hidden_truth: HiddenTruth

    def condition(self, name: str) -> DemandCondition:
        for c in (*self.splits.search_conditions, *self.splits.heldout_conditions):
            if c.name == name:
                return c
        raise KeyError(f"pack {self.id} has no demand condition '{name}'")


# --- authoring helpers -------------------------------------------------------------------------


def br(to: str, p: float, **kw: Any) -> dict[str, Any]:
    return {"to": to, "probability": p, **kw}


def rule(
    branches: list[dict[str, Any]],
    when: tuple[str, float] | None = None,
    fallback_to: str | None = None,
) -> dict[str, Any]:
    return {
        "when": None if when is None else {"op": when[0], "threshold": when[1]},
        "branches": branches,
        "fallback_to": fallback_to,
    }


def to(target: str) -> list[dict[str, Any]]:
    return [rule([br(target, 1.0)])]


def svc(kind: str, mean: float, cv: float | None = None) -> dict[str, Any]:
    d: dict[str, Any] = {"kind": kind, "mean": mean}
    if cv is not None:
        d["cv"] = cv
    return d


def variant(
    resource: str, service: dict[str, Any], cost: float, routes: list[dict[str, Any]]
) -> dict[str, Any]:
    return {"resource": resource, "service": service, "cost_per_case": cost, "routes": routes}


def step(
    sid: str, description: str, variants: dict[str, dict[str, Any]], active: str | None = None
) -> dict[str, Any]:
    return {
        "id": sid,
        "description": description,
        "variants": variants,
        "active_variant": active or next(iter(variants)),
    }


def resource(name: str, kind: str, capacity: int, cost: float) -> dict[str, Any]:
    return {"name": name, "kind": kind, "capacity": capacity, "cost_per_hour": cost}


def case_type(name: str, rate: float, entry: str, median: float, sigma: float) -> dict[str, Any]:
    return {
        "name": name,
        "arrival_rate_per_hour": rate,
        "entry_step": entry,
        "value": {"median": median, "sigma": sigma},
    }


def standard_splits(extra_heldout: list[DemandCondition]) -> Splits:
    normal = DemandCondition(name="normal", arrival_multiplier=1.0)
    return Splits(
        search_seeds=tuple(range(1000, 1010)),
        heldout_seeds=tuple(range(9000, 9020)),
        search_conditions=(normal,),
        heldout_conditions=(
            normal,
            DemandCondition(name="surge_25", arrival_multiplier=1.25),
            *extra_heldout,
        ),
    )


# A day with a morning peak and quiet nights; normalised to mean 1 by the arrival generator.
PEAKED_PROFILE: tuple[float, ...] = (
    0.3,
    0.2,
    0.2,
    0.2,
    0.3,
    0.5,
    0.8,
    1.2,
    1.7,
    1.9,
    1.8,
    1.6,
    1.4,
    1.5,
    1.6,
    1.5,
    1.3,
    1.1,
    0.9,
    0.8,
    0.7,
    0.6,
    0.5,
    0.4,
)
