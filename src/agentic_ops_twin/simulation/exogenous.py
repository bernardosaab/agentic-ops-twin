"""Counter-based exogenous inputs and pairing verification.

Every random draw is a pure function of ``(seed, stream, key...)`` hashed with BLAKE2b. Draws do
not depend on the order in which simulation events consume them, so two scenarios whose event
orders diverge (different capacities, routing or variants) still see the same arrival times, case
values, service uniforms and routing uniforms for the same case, step and visit.

Identical seeds are *not* assumed sufficient for pairing: each run publishes a digest of its
realised arrival stream, and comparisons pair replications only when digests match.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import NormalDist

from pydantic import Field

from agentic_ops_twin.simulation.model import Frozen, OperatingModel

EXOGENOUS_SCHEME = "blake2b-counter-v1"
_TWO64 = float(2**64)
_STD_NORMAL = NormalDist()


def uniform(seed: int, *key: object) -> float:
    """Deterministic uniform in the open interval (0, 1)."""
    raw = repr((EXOGENOUS_SCHEME, seed, *key)).encode()
    x = int.from_bytes(hashlib.blake2b(raw, digest_size=8).digest(), "big")
    return (x + 0.5) / _TWO64


class DemandCondition(Frozen):
    """Exogenous demand scenario applied on top of the operating model's arrival rates."""

    name: str
    arrival_multiplier: float = Field(gt=0)
    case_type_multipliers: dict[str, float] = Field(default_factory=dict)
    hourly_profile: tuple[float, ...] | None = Field(
        default=None,
        description="Optional 24 hour-of-day rate multipliers (normalised to mean 1).",
    )

    def rate(self, model: OperatingModel, case_type: str) -> float:
        base = next(c.arrival_rate_per_hour for c in model.case_types if c.name == case_type)
        return base * self.arrival_multiplier * self.case_type_multipliers.get(case_type, 1.0)


NORMAL_DEMAND = DemandCondition(name="normal", arrival_multiplier=1.0)


@dataclass(frozen=True, slots=True)
class Arrival:
    case_id: str
    case_type: str
    time: float
    value: float


def arrival_stream(model: OperatingModel, seed: int, demand: DemandCondition) -> list[Arrival]:
    """Poisson arrivals per case type up to the horizon (thinning when a profile is supplied)."""
    for name in demand.case_type_multipliers:
        if name not in {c.name for c in model.case_types}:
            raise ValueError(
                f"demand condition '{demand.name}' references unknown case type {name}"
            )
    profile: Sequence[float] | None = None
    if demand.hourly_profile is not None:
        if len(demand.hourly_profile) != 24 or min(demand.hourly_profile) < 0:
            raise ValueError("hourly_profile must contain 24 non-negative multipliers")
        mean = sum(demand.hourly_profile) / 24
        if mean <= 0:
            raise ValueError("hourly_profile must have a positive mean")
        profile = [p / mean for p in demand.hourly_profile]
    out: list[Arrival] = []
    for ct in model.case_types:
        rate = demand.rate(model, ct.name)
        if rate <= 0:
            continue
        peak = rate * (max(profile) if profile is not None else 1.0)
        t = 0.0
        i = 0
        n = 0
        while True:
            t += -math.log1p(-uniform(seed, "arrival", ct.name, i)) / peak
            if t >= model.horizon_hours:
                break
            accept = True
            if profile is not None:
                accept = uniform(seed, "thin", ct.name, i) <= profile[int(t) % 24] * rate / peak
            if accept:
                z = _STD_NORMAL.inv_cdf(uniform(seed, "value", ct.name, n))
                value = ct.value.median * math.exp(ct.value.sigma * z)
                out.append(Arrival(f"{ct.name}-{n}", ct.name, t, value))
                n += 1
            i += 1
    out.sort(key=lambda a: (a.time, a.case_id))
    return out


def stream_digest(arrivals: Sequence[Arrival]) -> str:
    h = hashlib.sha256(EXOGENOUS_SCHEME.encode())
    for a in arrivals:
        h.update(f"{a.case_id}|{a.case_type}|{a.time:.9f}|{a.value:.6f};".encode())
    return h.hexdigest()
