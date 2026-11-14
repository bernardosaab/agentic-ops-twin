"""Provenance graph, trust gate, write-gate, routing and stress tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from tests_support import ORDERED_TIMES

from agentic_ops_twin.agent.router import Router, unexplained_quantities
from agentic_ops_twin.decision.stress import breaking_point
from agentic_ops_twin.governance.harness_eval import run_harness_eval
from agentic_ops_twin.governance.ledger import Ledger
from agentic_ops_twin.governance.trust import assess, load_history
from agentic_ops_twin.packs import get_pack


def test_bitemporal_invalidation_and_as_of(tmp_path: Path) -> None:
    led = Ledger(tmp_path / "l.sqlite")
    t1, t2, t3, t4 = ORDERED_TIMES
    fact = led.append("brief", {"v": 1}, created_at=t1)
    led.invalidate(fact.record_id, "superseded", effective_at=t3)
    # Recorded at t1; invalidation recorded "now" with valid time t3.
    assert led.is_valid(fact.record_id, as_of_recorded=t2, as_of_valid=t2)
    assert led.is_valid(fact.record_id, as_of_valid=t2)  # known now, but in force at t2
    assert not led.is_valid(fact.record_id, as_of_valid=t4)
    assert fact.record_id in {r.record_id for r in led.as_of(recorded=t2, valid=t2)}
    assert not led.as_of(recorded="9999", valid=t4, kind="brief")
    assert led.verify() == (True, [])
    # The original record is never edited or removed.
    assert led.get(fact.record_id) is not None


def test_lineage_and_reconstruction_pack(tmp_path: Path) -> None:
    led = Ledger(tmp_path / "l.sqlite")
    a = led.append("request", {"text": "x"})
    b = led.append("proposal", {"p": 1}, refs=[a.record_id])
    c = led.append("experiment", {"e": 1}, edges=[("evaluates", b.record_id)])
    d = led.append("brief", {"b": 1}, refs=[c.record_id])
    led.invalidate(b.record_id, "proposal withdrawn")
    pack = led.reconstruction_pack(d.record_id)
    assert [r["record_id"] for r in pack.records] == [
        a.record_id,
        b.record_id,
        c.record_id,
        d.record_id,
    ]
    assert pack.chain_verified and pack.invalidations[0]["target"] == b.record_id
    assert "Reconstruction pack" in pack.timeline_markdown()


def test_trust_gate_states() -> None:
    pack = get_pack("procurement")
    assert assess(pack.model).status == "unvalidated"


def test_harness_golden_jobs_and_negative_tests() -> None:
    rep = run_harness_eval("insurance")
    failed = [(c.id, c.actual, c.reasons) for c in rep.cases if not c.passed]
    assert not failed, failed
    assert rep.total >= 14
    ids = {c.id: c for c in rep.cases}
    assert ids["G1"].actual == "release" and ids["N7"].actual == "refusal"
    assert all(c.system_of_record_unchanged for c in rep.cases if c.expected == "refusal")
    assert rep.reconstruction_chain_verified and rep.reconstruction_pack_records >= 8


def test_router_skips_instead_of_guessing() -> None:
    router = Router()
    out = router.route(
        "Reduce specialists by 1 and prioritise high-value refunds, normal volume.",
        get_pack("support"),
    )
    assert out.status == "skipped" and out.outcome is None
    assert "quantity 1" in (out.skip_reason or "")
    assert [s.tier for s in out.route] == ["compiled", "human-queue"]
    ok = router.route("Add 1 adjuster under normal demand.", get_pack("insurance"))
    assert ok.status == "ok" and ok.decided_by == "scripted-fake-v1"


def test_router_escalates_to_tier_and_shadow_records_agreement() -> None:
    from agentic_ops_twin.agent.fake import FakeProposer

    pack = get_pack("support")
    router = Router(tiers=[FakeProposer()], shadow=FakeProposer())
    skipped = router.route("Reduce specialists by 1, normal volume.", pack)
    assert [s.tier for s in skipped.route][:2] == ["compiled", "scripted-fake-v1"]
    accepted = router.route("Automate ticket routing under normal demand.", pack)
    assert accepted.shadow is not None and accepted.shadow["agrees"] is True


def test_unexplained_quantities_ignores_numbers_in_resource_names() -> None:
    pack = get_pack("support")
    out = Router().route("Set tier 1 agents to 3 and automate routing under current demand.", pack)
    assert out.status == "ok"
    assert out.outcome is not None
    from agentic_ops_twin.agent.contracts import pack_context

    assert unexplained_quantities(out.request, out.outcome, pack_context(pack)) == []


def test_breaking_point_brackets_the_rule() -> None:
    pack = get_pack("insurance")
    res = breaking_point(
        pack,
        pack.model,
        name="baseline",
        label="current",
        seeds=(9000, 9001),
        iterations=3,
        workers=1,
    )
    assert res.headroom_multiplier is not None and res.first_failing_multiplier is not None
    assert 1.0 <= res.headroom_multiplier < res.first_failing_multiplier <= 2.0
    passing = [p for p in res.points if p.meets_rule]
    failing = [p for p in res.points if not p.meets_rule]
    assert max(p.multiplier for p in passing) < min(p.multiplier for p in failing)
    assert res.breaks_first_at is not None


def test_history_csv_round_trip(tmp_path: Path) -> None:
    from agentic_ops_twin.cli import main

    main(["dataset", "--pack", "procurement", "--seed", "1", "--out", str(tmp_path)])
    arrivals, events = load_history(
        tmp_path / "procurement-arrivals-seed1-normal.csv",
        tmp_path / "procurement-events-seed1-normal.csv",
    )
    assert arrivals and events and events[0].end >= events[0].start


@pytest.mark.parametrize("pid", ["insurance", "support"])
def test_staging_requires_change_set_and_trust(tmp_path: Path, pid: str) -> None:
    from agentic_ops_twin.governance.writegate import SystemOfRecord, stage

    led = Ledger(tmp_path / "l.sqlite")
    brief = led.append("brief", {"brief": {"change_set": None}})
    trust = led.append("trust_assessment", {"status": "unvalidated"})
    with pytest.raises(ValueError, match="no change set"):
        stage(
            led,
            SystemOfRecord(tmp_path / "s.json"),
            get_pack(pid),
            brief_record=brief.record_id,
            trust_record=trust.record_id,
            maker="m",
        )
    with_cs = led.append("brief", {"brief": {"change_set": {"name": "x", "changes": []}}})
    with pytest.raises(ValueError, match="trust assessment"):
        stage(
            led,
            SystemOfRecord(tmp_path / "s.json"),
            get_pack(pid),
            brief_record=with_cs.record_id,
            trust_record=with_cs.record_id,
            maker="m",
        )
