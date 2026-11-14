"""Typed operating-model contracts.

Every parameter that changes simulated behaviour is required: there are no silent defaults for
arrival rates, capacities, service times, costs, routing probabilities or the horizon. Models are
immutable; scenario changes produce new validated models (see ``throughline.scenarios``).
"""

from __future__ import annotations

import hashlib
import json
import math
from statistics import NormalDist
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DONE = "done"
_STD_NORMAL = NormalDist()


class Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Distribution(Frozen):
    """Service-time distribution in hours, sampled by inverse CDF from a supplied uniform.

    Inverse-CDF sampling lets two scenarios share the same uniform for the same case/step/visit
    (common random numbers) even when the distribution parameters differ.
    """

    kind: Literal["deterministic", "exponential", "lognormal", "triangular"]
    mean: float = Field(gt=0, description="Mean service time in hours.")
    cv: float | None = Field(
        default=None, gt=0, description="Coefficient of variation (lognormal)."
    )
    low: float | None = Field(default=None, ge=0, description="Triangular minimum (hours).")
    high: float | None = Field(default=None, gt=0, description="Triangular maximum (hours).")

    @model_validator(mode="after")
    def _check(self) -> Distribution:
        if self.kind == "lognormal" and self.cv is None:
            raise ValueError("lognormal distribution requires 'cv'")
        if self.kind != "lognormal" and self.cv is not None:
            raise ValueError(f"'cv' is only valid for lognormal, not {self.kind}")
        if self.kind == "triangular":
            if self.low is None or self.high is None:
                raise ValueError("triangular distribution requires 'low' and 'high'")
            mode = 3 * self.mean - self.low - self.high
            if not (self.low <= mode <= self.high) or self.low >= self.high:
                raise ValueError(
                    "triangular mean is inconsistent with low/high (implied mode outside range)"
                )
        elif self.low is not None or self.high is not None:
            raise ValueError("'low'/'high' are only valid for triangular")
        return self

    def ppf(self, u: float) -> float:
        """Inverse CDF at ``u`` in (0, 1)."""
        if self.kind == "deterministic":
            return self.mean
        if self.kind == "exponential":
            return -self.mean * math.log1p(-u)
        if self.kind == "lognormal":
            assert self.cv is not None
            sigma2 = math.log1p(self.cv**2)
            mu = math.log(self.mean) - sigma2 / 2
            return math.exp(mu + math.sqrt(sigma2) * _STD_NORMAL.inv_cdf(u))
        assert self.low is not None and self.high is not None
        a, b = self.low, self.high
        c = 3 * self.mean - a - b
        fc = (c - a) / (b - a)
        if u < fc:
            return a + math.sqrt(u * (b - a) * (c - a))
        return b - math.sqrt((1 - u) * (b - a) * (b - c))

    @property
    def variance(self) -> float:
        if self.kind == "deterministic":
            return 0.0
        if self.kind == "exponential":
            return self.mean**2
        if self.kind == "lognormal":
            assert self.cv is not None
            return (self.cv * self.mean) ** 2
        assert self.low is not None and self.high is not None
        a, b = self.low, self.high
        c = 3 * self.mean - a - b
        return (a * a + b * b + c * c - a * b - a * c - b * c) / 18

    def scaled(self, factor: float) -> Distribution:
        """Scale the time axis by ``factor`` (keeps shape and coefficient of variation)."""
        if factor <= 0:
            raise ValueError("scale factor must be positive")
        update: dict[str, float] = {"mean": self.mean * factor}
        if self.low is not None and self.high is not None:
            update |= {"low": self.low * factor, "high": self.high * factor}
        return self.model_copy(update=update)


class Condition(Frozen):
    """A predicate on the case's numeric ``value`` attribute (e.g. claim amount)."""

    attribute: Literal["value"] = "value"
    op: Literal[">=", "<"]
    threshold: float = Field(ge=0)

    def holds(self, value: float) -> bool:
        return value >= self.threshold if self.op == ">=" else value < self.threshold


class Branch(Frozen):
    to: str
    probability: float = Field(ge=0, le=1)
    max_traversals: int | None = Field(
        default=None,
        ge=1,
        description="Per-case limit for this edge; required on edges that close a cycle.",
    )
    escalation: bool = Field(default=False, description="Counts as a manual escalation.")
    param: str | None = Field(
        default=None, description="Name of a tunable probability (sensitivity analysis)."
    )


class RouteRule(Frozen):
    """First matching rule wins; its branches are sampled with a routing uniform."""

    when: Condition | None
    branches: tuple[Branch, ...] = Field(min_length=1)
    fallback_to: str | None = Field(
        default=None, description="Target when a sampled branch exceeded its traversal limit."
    )

    @field_validator("branches")
    @classmethod
    def _sum_to_one(cls, v: tuple[Branch, ...]) -> tuple[Branch, ...]:
        total = sum(b.probability for b in v)
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"branch probabilities sum to {total:.6f}, expected 1")
        return v


class StepVariant(Frozen):
    """One way of performing a step (e.g. manual vs automated triage)."""

    resource: str
    service: Distribution
    cost_per_case: float = Field(ge=0)
    routes: tuple[RouteRule, ...] = Field(min_length=1)


class Step(Frozen):
    id: str
    description: str
    variants: dict[str, StepVariant] = Field(min_length=1)
    active_variant: str

    @model_validator(mode="after")
    def _active_exists(self) -> Step:
        if self.active_variant not in self.variants:
            raise ValueError(f"step {self.id}: active variant '{self.active_variant}' not defined")
        return self

    @property
    def active(self) -> StepVariant:
        return self.variants[self.active_variant]


class Resource(Frozen):
    name: str
    kind: Literal["human", "automation"]
    capacity: int = Field(ge=0, description="Concurrent servers. Zero is allowed and warned.")
    cost_per_hour: float = Field(ge=0, description="Staffed cost per server-hour.")


class ValueAttribute(Frozen):
    """Lognormal case value assigned at arrival (synthetic monetary amount)."""

    median: float = Field(gt=0)
    sigma: float = Field(ge=0)


class CaseType(Frozen):
    name: str
    arrival_rate_per_hour: float = Field(ge=0)
    entry_step: str
    value: ValueAttribute


class Control(Frozen):
    """Mandatory control: every path for matching cases must pass ``step``.

    Controls are trusted inputs. No scenario lever can reference them, and every changed model is
    re-checked against them. Control steps must be performed by a human resource.
    """

    id: str
    step: str
    description: str
    applies_to: tuple[str, ...] = Field(min_length=1, description="Case type names.")
    when: Condition | None


class Assumption(Frozen):
    id: str
    text: str
    source: Literal["synthetic-hand-authored", "calibrated-from-log", "operator-supplied"]


class OperatingModel(Frozen):
    id: str
    version: str
    description: str
    currency: str
    horizon_hours: float = Field(gt=0)
    warmup_hours: float = Field(ge=0)
    sla_hours: float = Field(gt=0)
    sla_penalty_per_miss: float = Field(ge=0)
    queue_policy: Literal["fifo", "high_value_first"]
    high_value_threshold: float = Field(ge=0)
    case_types: tuple[CaseType, ...] = Field(min_length=1)
    resources: tuple[Resource, ...] = Field(min_length=1)
    steps: tuple[Step, ...] = Field(min_length=1)
    controls: tuple[Control, ...]
    assumptions: tuple[Assumption, ...]

    def resource(self, name: str) -> Resource:
        for r in self.resources:
            if r.name == name:
                return r
        raise KeyError(name)

    def step(self, step_id: str) -> Step:
        for s in self.steps:
            if s.id == step_id:
                return s
        raise KeyError(step_id)

    def active_resources(self) -> set[str]:
        return {s.active.resource for s in self.steps}

    def staffed_cost_per_hour(self) -> float:
        """Capacity x rate for resources used by an active step variant.

        Resources referenced only by inactive variants (e.g. an automation service that is not
        switched on) are not staffed and cost nothing.
        """
        active = self.active_resources()
        return sum(r.capacity * r.cost_per_hour for r in self.resources if r.name in active)

    def digest(self) -> str:
        """Content hash used to bind results, briefs and reviews to an exact model."""
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()
