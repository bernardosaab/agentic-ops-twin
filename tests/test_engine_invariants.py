"""Conservation, reproducibility, resource limits, zero capacity, overload and pairing."""

from __future__ import annotations

import random

import pytest
from factories import single_queue

from agentic_ops_twin.decision.experiment import Job, Splits, run_jobs
from agentic_ops_twin.packs import PACK_IDS, get_pack
from agentic_ops_twin.simulation.engine import HiddenMechanisms, simulate
from agentic_ops_twin.simulation.exogenous import (
    DemandCondition,
    arrival_stream,
    stream_digest,
    uniform,
)
from agentic_ops_twin.simulation.stats import compare, pairing_status


@pytest.mark.parametrize("pid", PACK_IDS)
def test_conservation_and_bounds(pid: str) -> None:
    pack = get_pack(pid)
    for cond in pack.splits.heldout_conditions:
        m = simulate(pack.model, 9000, cond).metrics
        assert m.arrivals == m.completed + m.open
        assert m.open == m.open_queued + m.open_in_service + m.open_in_handoff
        for name, u in m.resources.items():
            assert u.max_in_service <= max(u.capacity, 0), name
            if u.utilisation is not None:
                assert 0.0 <= u.utilisation <= 1.0 + 1e-9


@pytest.mark.parametrize("pid", PACK_IDS)
def test_same_seed_reproduces_identically(pid: str) -> None:
    pack = get_pack(pid)
    a = simulate(pack.model, 1234).metrics
    b = simulate(pack.model, 1234).metrics
    assert a == b
    assert simulate(pack.model, 1235).metrics != a


def test_worker_count_does_not_change_results() -> None:
    pack = get_pack("support")
    job = Job(pack.model, (1, 2, 3, 4, 5, 6, 7, 8), pack.condition("normal"), "b", "b")
    serial = run_jobs([job], workers=1)[0]
    parallel = run_jobs([job], workers=4)[0]
    assert serial.runs == parallel.runs


def test_zero_capacity_completes_nothing_and_keeps_everything_open() -> None:
    model = single_queue(rate=1.0, mean_service=0.5, servers=0, horizon=100, warmup=0)
    m = simulate(model, 1).metrics
    assert m.arrivals > 50
    assert m.completed == 0
    assert m.open == m.arrivals == m.open_queued
    assert m.cycle_p95_hours is None and m.completion_rate == 0
    assert m.sla_attainment == 0
    assert m.resources["server"].utilisation is None


def test_overload_backlog_grows_at_excess_rate() -> None:
    lam, mu, c = 3.0, 1.0, 2  # excess 1 case/hour
    model = single_queue(rate=lam, mean_service=1 / mu, servers=c, horizon=600, warmup=0)
    wips = [simulate(model, s).metrics.wip_at_horizon for s in range(6)]
    mean_wip = sum(wips) / len(wips)
    assert mean_wip == pytest.approx((lam - c * mu) * 600, rel=0.15)
    m = simulate(model, 0).metrics
    assert m.resources["server"].utilisation == pytest.approx(1.0, abs=0.02)


def test_open_cases_do_not_make_policy_look_fast() -> None:
    fast = single_queue(rate=3.0, mean_service=1.0, servers=2, horizon=300, warmup=0)
    m = simulate(fast, 3).metrics
    # p95 is computed on completed cases only, and must be read with completion rate.
    assert m.completion_rate is not None and m.completion_rate < 0.8
    assert m.sla_attainment is not None and m.sla_attainment <= m.completion_rate


def test_counter_based_draws_do_not_depend_on_consumption_order() -> None:
    keys = [("svc", f"c-{i}", "step", 1) for i in range(50)]
    forward = [uniform(7, *k) for k in keys]
    backward = [uniform(7, *k) for k in reversed(keys)]
    assert forward == list(reversed(backward))


def test_shared_seed_alone_does_not_pair_divergent_branches() -> None:
    """Why pairing is verified: a sequential RNG with a shared seed desynchronises when two
    policies consume a different number of draws (e.g. one routes a case through an extra
    step), so later cases no longer see the same service times."""

    def sequential_services(extra_draw_at: int | None) -> list[float]:
        rng = random.Random(42)
        out = []
        for i in range(20):
            out.append(rng.random())
            if extra_draw_at is not None and i == extra_draw_at:
                rng.random()  # extra step's service draw in the other policy
        return out

    a, b = sequential_services(None), sequential_services(5)
    assert a[:6] == b[:6] and a[6:] != b[6:]
    # Counter-based draws keyed by (case, step, visit) are unaffected by the extra step.
    ca = [uniform(42, "svc", f"c-{i}", "assess", 1) for i in range(20)]
    cb = [uniform(42, "svc", f"c-{i}", "assess", 1) for i in range(20)]
    assert ca == cb


def test_pairing_is_verified_by_digest_not_assumed() -> None:
    pack = get_pack("insurance")
    normal, surge = pack.condition("normal"), pack.condition("surge_25")
    seeds = (1, 2, 3)
    base = [simulate(pack.model, s, normal).metrics for s in seeds]
    same = [simulate(pack.model, s, normal).metrics for s in seeds]
    other = [simulate(pack.model, s, surge).metrics for s in seeds]
    assert pairing_status(base, same)[0]
    paired, note = pairing_status(base, other)
    assert not paired and "differ" in note
    assert compare("objective_cost_per_case", base, other).method == "welch"
    assert stream_digest(arrival_stream(pack.model, 1, normal)) == base[0].arrival_digest


def test_hidden_mechanisms_change_outcomes_but_keep_conservation() -> None:
    pack = get_pack("procurement")
    mech = HiddenMechanisms(handoff_delay_hours=0.5, absenteeism_probability=0.2)
    m0 = simulate(pack.model, 5).metrics
    m1 = simulate(pack.model, 5, mechanisms=mech).metrics
    assert m1.arrivals == m1.completed + m1.open
    assert m1.cycle_median_hours is not None and m0.cycle_median_hours is not None
    assert m1.cycle_median_hours > m0.cycle_median_hours


def test_demand_profile_thinning_preserves_mean_rate() -> None:
    pack = get_pack("support")
    flat = DemandCondition(name="flat", arrival_multiplier=1.0)
    peaked = DemandCondition(
        name="peaked", arrival_multiplier=1.0, hourly_profile=pack.hidden_truth.hourly_profile
    )
    n_flat = sum(len(arrival_stream(pack.model, s, flat)) for s in range(5))
    n_peak = sum(len(arrival_stream(pack.model, s, peaked)) for s in range(5))
    assert n_peak == pytest.approx(n_flat, rel=0.05)


def test_search_and_heldout_seeds_are_disjoint() -> None:
    for pid in PACK_IDS:
        sp = get_pack(pid).splits
        assert not set(sp.search_seeds) & set(sp.heldout_seeds)
    with pytest.raises(ValueError, match="overlap"):
        Splits(
            search_seeds=(1, 2),
            heldout_seeds=(2, 3),
            search_conditions=(DemandCondition(name="n", arrival_multiplier=1),),
            heldout_conditions=(DemandCondition(name="n", arrival_multiplier=1),),
        )
