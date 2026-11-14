"""Missing and inconsistent assumptions are rejected, never filled in."""

from __future__ import annotations

import copy
from typing import Any

import pytest
from factories import controlled_flow
from pydantic import ValidationError

from agentic_ops_twin.packs import PACK_IDS, get_pack
from agentic_ops_twin.simulation.engine import simulate
from agentic_ops_twin.simulation.model import Distribution, OperatingModel
from agentic_ops_twin.simulation.validate import ModelValidationError, ensure_valid, validate


def codes(data: dict[str, Any]) -> set[str]:
    return {i.code for i in validate(OperatingModel.model_validate(data)).errors}


def test_all_packs_are_valid() -> None:
    for pid in PACK_IDS:
        assert validate(get_pack(pid).model).ok, pid


@pytest.mark.parametrize(
    "field", ["horizon_hours", "sla_hours", "case_types", "resources", "queue_policy"]
)
def test_missing_top_level_field_is_rejected(field: str) -> None:
    data = controlled_flow()
    del data[field]
    with pytest.raises(ValidationError):
        OperatingModel.model_validate(data)


def test_missing_arrival_rate_capacity_and_service_are_rejected() -> None:
    for path in (("case_types", 0, "arrival_rate_per_hour"), ("resources", 0, "capacity")):
        data = controlled_flow()
        del data[path[0]][path[1]][path[2]]
        with pytest.raises(ValidationError):
            OperatingModel.model_validate(data)
    data = controlled_flow()
    del data["steps"][0]["variants"]["manual"]["service"]
    with pytest.raises(ValidationError):
        OperatingModel.model_validate(data)


def test_unknown_fields_are_rejected() -> None:
    data = controlled_flow()
    data["resources"][0]["shift_pattern"] = "unexplained"
    with pytest.raises(ValidationError):
        OperatingModel.model_validate(data)


def test_probabilities_must_sum_to_one() -> None:
    data = controlled_flow()
    data["steps"][0]["variants"]["manual"]["routes"][1]["branches"] = [
        {"to": "done", "probability": 0.7}
    ]
    with pytest.raises(ValidationError, match="sum to"):
        OperatingModel.model_validate(data)


def test_inconsistent_distributions_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Distribution(kind="lognormal", mean=1.0)
    with pytest.raises(ValidationError):
        Distribution(kind="exponential", mean=1.0, cv=0.5)
    with pytest.raises(ValidationError):
        Distribution(kind="triangular", mean=5.0, low=0.0, high=2.0)
    with pytest.raises(ValidationError):
        Distribution(kind="deterministic", mean=0.0)


def test_unknown_references_and_warmup_are_rejected() -> None:
    data = controlled_flow()
    data["steps"][0]["variants"]["manual"]["resource"] = "ghost"
    assert "unknown_resource" in codes(data)
    data = controlled_flow()
    data["steps"][1]["variants"]["manual"]["routes"][0]["branches"][0]["to"] = "nowhere"
    assert "unknown_target" in codes(data)
    data = controlled_flow(warmup_hours=500.0)
    assert "warmup_exceeds_horizon" in codes(data)
    data = controlled_flow()
    data["case_types"][0]["entry_step"] = "missing"
    assert "unknown_entry" in codes(data)


def test_last_route_must_be_unconditional() -> None:
    data = controlled_flow()
    data["steps"][0]["variants"]["manual"]["routes"][1]["when"] = {"op": "<", "threshold": 1000}
    assert "no_default_route" in codes(data)


def test_unbounded_loops_are_rejected_and_bounded_loops_accepted() -> None:
    data = controlled_flow()
    data["steps"][1]["variants"]["manual"]["routes"][0]["branches"] = [
        {"to": "done", "probability": 0.9},
        {"to": "intake", "probability": 0.1},
    ]
    assert "unbounded_loop" in codes(data)
    ok = copy.deepcopy(data)
    ok["steps"][1]["variants"]["manual"]["routes"][0]["branches"][1]["max_traversals"] = 2
    assert "missing_fallback" in codes(ok)
    ok["steps"][1]["variants"]["manual"]["routes"][0]["fallback_to"] = "done"
    assert codes(ok) == set()


def test_zero_capacity_is_warned_not_hidden() -> None:
    data = controlled_flow()
    data["resources"][0]["capacity"] = 0
    report = validate(OperatingModel.model_validate(data))
    assert report.ok
    assert any(w.code == "zero_capacity" for w in report.warnings)


def test_invalid_model_cannot_be_simulated() -> None:
    data = controlled_flow()
    data["steps"][0]["variants"]["manual"]["resource"] = "ghost"
    model = OperatingModel.model_validate(data)
    with pytest.raises(ModelValidationError):
        ensure_valid(model)
    with pytest.raises(ModelValidationError):
        simulate(model, seed=1)
