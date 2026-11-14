"""Calibration, residual diagnostics and budgeted selection."""

from __future__ import annotations

import numpy as np
import pytest

from throughline.core.engine import simulate
from throughline.core.exogenous import arrival_stream
from throughline.packs import get_pack
from throughline.research.calibrate import calibrate
from throughline.research.selection import ocba_fractions, pcs

HOURS = 960.0


def _history(pid: str, mechanisms: bool):
    pack = get_pack(pid)
    model = pack.model.model_copy(update={"horizon_hours": HOURS, "warmup_hours": 0.0})
    demand = pack.condition("normal")
    mech = pack.hidden_truth.mechanisms if mechanisms else None
    if mechanisms:
        demand = demand.model_copy(update={"hourly_profile": pack.hidden_truth.hourly_profile})
    kw = {"mechanisms": mech} if mech is not None else {}
    run = simulate(model, 500, demand, record_log=True, **kw)
    return pack, arrival_stream(model, 500, demand), run.event_log


def test_calibration_recovers_parameters_from_mechanism_free_history() -> None:
    pack, arrivals, log = _history("support", mechanisms=False)
    cal = calibrate(pack.model, arrivals, log, HOURS)
    est = {p.name: p for p in cal.parameters}
    for ct in pack.model.case_types:
        e = est[f"arrival_rate[{ct.name}]"]
        assert e.ci95_low is not None and e.ci95_high is not None
        assert e.ci95_low <= ct.arrival_rate_per_hour <= e.ci95_high
    tier2 = est["service_mean[tier2]"]
    assert tier2.estimate == pytest.approx(0.8, rel=0.1)
    assert "routing.auto_classify" in cal.uncalibrated


def test_diagnostics_quiet_without_mechanisms_and_flag_with_them() -> None:
    pack, arrivals, log = _history("procurement", mechanisms=False)
    quiet = {d.name: d for d in calibrate(pack.model, arrivals, log, HOURS).diagnostics}
    assert not quiet["mean_handoff_gap_hours"].flagged
    assert not quiet["idle_capacity_while_queued"].flagged
    assert not quiet["peak_to_trough_hourly_arrivals"].flagged
    pack, arrivals, log = _history("procurement", mechanisms=True)
    loud = {d.name: d for d in calibrate(pack.model, arrivals, log, HOURS).diagnostics}
    assert all(d.flagged for d in loud.values())


def test_ocba_gives_more_budget_to_close_competitors() -> None:
    w = ocba_fractions(np.array([10.0, 10.5, 20.0]), np.array([1.0, 1.0, 1.0]))
    assert w.sum() == pytest.approx(1.0)
    assert w[1] > w[2]


def test_pcs_increases_with_budget_on_a_hard_problem() -> None:
    rng = np.random.default_rng(0)
    pool = [rng.normal(10.0 + 0.2 * i, 2.0, size=200) for i in range(5)]
    true = np.array([10.0 + 0.2 * i for i in range(5)])
    lo, _ = pcs(pool, true, 25, "equal", 300, 0.05, seed=1)
    hi, _ = pcs(pool, true, 150, "equal", 300, 0.05, seed=1)
    assert hi > lo
    ocba, _ = pcs(pool, true, 150, "ocba", 300, 0.05, seed=1)
    assert 0.0 <= ocba <= 1.0
