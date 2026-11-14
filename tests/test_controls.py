"""Mandatory controls cannot be removed, bypassed or automated by any scenario path."""

from __future__ import annotations

import pytest
from factories import controlled_flow

from agentic_ops_twin.decision.scenarios import (
    Change,
    ChangeRejected,
    ChangeSet,
    DecisionSpace,
    VariantLever,
    apply_changes,
    enumerate_alternatives,
)
from agentic_ops_twin.packs import PACK_IDS, get_pack
from agentic_ops_twin.simulation.engine import simulate
from agentic_ops_twin.simulation.model import OperatingModel
from agentic_ops_twin.simulation.validate import validate


def test_routing_that_bypasses_control_is_rejected() -> None:
    data = controlled_flow()
    # High-value cases now skip approval.
    data["steps"][0]["variants"]["manual"]["routes"][0]["branches"][0]["to"] = "done"
    report = validate(OperatingModel.model_validate(data))
    assert any(i.code == "control_bypass" for i in report.errors)


def test_probabilistic_partial_bypass_is_rejected() -> None:
    data = controlled_flow()
    data["steps"][0]["variants"]["manual"]["routes"][0]["branches"] = [
        {"to": "approve", "probability": 0.99},
        {"to": "done", "probability": 0.01},
    ]
    report = validate(OperatingModel.model_validate(data))
    assert any(i.code == "control_bypass" for i in report.errors)


def test_automating_a_control_step_is_rejected_even_if_a_lever_allows_it() -> None:
    model = OperatingModel.model_validate(controlled_flow())
    space = DecisionSpace(
        levers=(VariantLever(step="approve", allowed=("manual", "automated")),),
        max_staffed_cost_per_hour=1000,
        max_alternatives=10,
    )
    with pytest.raises(ChangeRejected, match="control_locked"):
        apply_changes(
            model,
            space,
            ChangeSet(name="x", changes=(Change(lever="variant:approve", value="automated"),)),
        )
    feasible, rejected, _ = enumerate_alternatives(model, space)
    assert [cs.name for cs, _ in feasible] == ["baseline"]
    assert rejected and "control_locked" in rejected[0][1]


def test_validator_rejects_automated_control_directly() -> None:
    data = controlled_flow()
    data["steps"][1]["active_variant"] = "automated"
    report = validate(OperatingModel.model_validate(data))
    assert any(i.code == "control_not_human" for i in report.errors)


def test_unknown_levers_and_out_of_bounds_values_are_rejected() -> None:
    pack = get_pack("insurance")
    for change in (
        Change(lever="capacity:senior_approver", value=0),
        Change(lever="remove_control:fraud-review-high-value", value="removed"),
        Change(lever="capacity:adjuster", value=99),
    ):
        with pytest.raises(ChangeRejected):
            apply_changes(pack.model, pack.decision_space, ChangeSet(name="x", changes=(change,)))


@pytest.mark.parametrize("pid", PACK_IDS)
def test_every_enumerated_alternative_keeps_every_control(pid: str) -> None:
    pack = get_pack(pid)
    feasible, _, _ = enumerate_alternatives(pack.model, pack.decision_space)
    for _, model in feasible:
        assert [c.model_dump() for c in model.controls] == [
            c.model_dump() for c in pack.model.controls
        ]
        assert validate(model).ok


@pytest.mark.parametrize("pid", PACK_IDS)
def test_every_simulated_high_value_case_passes_its_controls(pid: str) -> None:
    pack = get_pack(pid)
    run = simulate(pack.model, seed=1000, record_log=True)
    assert run.event_log is not None
    visited: dict[str, set[str]] = {}
    completed: dict[str, float] = {}
    for e in run.event_log:
        visited.setdefault(e.case_id, set()).add(e.step)
        if e.next_step == "done":
            completed[e.case_id] = e.value
    for ctl in pack.model.controls:
        for case_id, value in completed.items():
            if ctl.when is None or ctl.when.holds(value):
                assert ctl.step in visited[case_id], (ctl.id, case_id)


def test_equivalent_alternatives_collapse_onto_smallest_change_set() -> None:
    pack = get_pack("insurance")
    feasible, _, equivalent = enumerate_alternatives(pack.model, pack.decision_space)
    labels = {cs.label() for cs, _ in feasible}
    assert "variant:triage=automated" in labels
    assert "capacity:triage_officer=1, variant:triage=automated" not in labels
    assert equivalent
