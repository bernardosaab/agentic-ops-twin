"""Known analytical and deterministic queue results."""

from __future__ import annotations

import math

import pytest
from factories import single_queue

from agentic_ops_twin.simulation.engine import simulate
from agentic_ops_twin.simulation.stats import estimate


def erlang_c_wait(lam: float, mu: float, c: int) -> float:
    """Mean waiting time in queue for M/M/c."""
    a = lam / mu
    rho = a / c
    s = sum(a**k / math.factorial(k) for k in range(c))
    top = a**c / (math.factorial(c) * (1 - rho))
    p_wait = top / (s + top)
    return p_wait / (c * mu - lam)


def test_deterministic_service_without_contention_is_exact() -> None:
    # Deterministic service with far more servers than concurrent work: no queueing, so every
    # cycle time equals the service time exactly.
    model = single_queue(rate=0.2, mean_service=0.5, servers=50, kind="deterministic")
    m = simulate(model, seed=1).metrics
    assert m.cycle_median_hours == pytest.approx(0.5)
    assert m.cycle_p95_hours == pytest.approx(0.5)
    assert m.resources["server"].mean_wait_hours == pytest.approx(0.0)


@pytest.mark.parametrize(("lam", "mean_s", "c"), [(0.8, 1.0, 1), (2.4, 1.0, 3)])
def test_mmc_mean_wait_matches_erlang_c(lam: float, mean_s: float, c: int) -> None:
    model = single_queue(rate=lam, mean_service=mean_s, servers=c, horizon=4000, warmup=400)
    waits = [simulate(model, seed=s).metrics.resources["server"].mean_wait_hours for s in range(12)]
    est = estimate("wait", waits)
    theory = erlang_c_wait(lam, 1 / mean_s, c)
    assert est.ci95_low is not None and est.ci95_high is not None
    # Allow a small margin for warm-up bias on top of the replication interval.
    margin = 0.1 * theory
    assert est.ci95_low - margin <= theory <= est.ci95_high + margin, (est, theory)


def test_utilisation_matches_offered_load() -> None:
    model = single_queue(rate=2.4, mean_service=1.0, servers=3, horizon=4000, warmup=400)
    utils = [simulate(model, seed=s).metrics.resources["server"].utilisation for s in range(8)]
    est = estimate("u", utils)
    assert est.mean == pytest.approx(0.8, abs=0.03)


def test_littles_law_holds_for_stable_queue() -> None:
    model = single_queue(rate=0.8, mean_service=1.0, servers=1, horizon=5000, warmup=500)
    m = simulate(model, seed=3).metrics
    # L = lambda * W, using the hourly WIP samples after warm-up.
    samples = m.backlog_hourly[500:]
    l_obs = sum(samples) / len(samples)
    assert m.cycle_mean_hours is not None
    assert l_obs == pytest.approx(0.8 * m.cycle_mean_hours, rel=0.15)
