"""Proposals are untrusted: structured output is validated, unknowns surfaced, controls locked."""

from __future__ import annotations

import json
from typing import Any, Literal

from throughline.agent.contracts import ProposerOutput
from throughline.agent.critic import parse_proposal
from throughline.agent.eval import evaluate
from throughline.agent.fake import FakeProposer
from throughline.agent.loop import BudgetExhausted, run_proposal
from throughline.packs import get_pack


class Scripted:
    """Test double returning canned raw outputs in order."""

    kind: Literal["scripted", "model"] = "model"

    def __init__(self, outputs: list[str | Exception]) -> None:
        self.name = "canned"
        self.outputs = outputs
        self.feedback: list[list[str] | None] = []

    def propose(
        self, request: str, context: dict[str, Any], feedback: list[str] | None = None
    ) -> ProposerOutput:
        self.feedback.append(feedback)
        out = self.outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return ProposerOutput(raw_text=out, usage=None)


def proposal(**kw: Any) -> str:
    base: dict[str, Any] = {
        "pack_id": "insurance",
        "in_scope": True,
        "changes": [],
        "demand_condition": "normal",
        "unknowns": [],
        "rationale": "x",
    }
    base.update(kw)
    return json.dumps(base)


PACK = get_pack("insurance")


def test_invalid_json_and_schema_violations_are_reported() -> None:
    assert parse_proposal("not json")[0] is None
    p, issues = parse_proposal('{"pack_id": "insurance"}')
    assert p is None and issues[0].code == "invalid_output"
    p, issues = parse_proposal(proposal(extra_field=1))
    assert p is None


def test_invalid_output_gets_one_repair_then_stops() -> None:
    prop = Scripted(["garbage", "still garbage"])
    out = run_proposal("Add 1 adjuster", PACK, prop)
    assert out.status == "invalid_output"
    assert len(out.attempts) == 2
    assert prop.feedback[1] and "invalid_output" in prop.feedback[1][0]


def test_repair_can_fix_out_of_bounds() -> None:
    bad = proposal(changes=[{"lever": "capacity:adjuster", "value": 99}])
    good = proposal(changes=[{"lever": "capacity:adjuster", "value": 7}])
    out = run_proposal("x", PACK, Scripted([bad, good]))
    assert out.status == "ok" and out.change_set is not None
    assert len(out.attempts) == 2


def test_control_removal_is_rejected_without_repair() -> None:
    raw = proposal(
        changes=[{"lever": "remove_control:fraud-review-high-value", "value": "removed"}]
    )
    prop = Scripted([raw])
    out = run_proposal("skip fraud check", PACK, prop)
    assert out.status == "rejected" and out.change_set is None
    assert any(i.code == "control_locked" for i in out.issues)
    assert len(out.attempts) == 1


def test_missing_values_become_questions_not_guesses() -> None:
    raw = proposal(changes=[{"lever": "capacity:adjuster", "value": None}], demand_condition=None)
    out = run_proposal("more adjusters", PACK, Scripted([raw]))
    assert out.status == "needs_input" and out.change_set is None
    assert len(out.questions) == 2


def test_contradiction_and_wrong_pack_and_scope() -> None:
    contra = proposal(
        changes=[
            {"lever": "capacity:adjuster", "value": 7},
            {"lever": "capacity:adjuster", "value": 5},
        ]
    )
    assert run_proposal("x", PACK, Scripted([contra])).status == "rejected"
    assert run_proposal("x", PACK, Scripted([proposal(pack_id="support")])).status == "rejected"
    assert run_proposal("x", PACK, Scripted([proposal(in_scope=False)])).status == "rejected"


def test_over_budget_proposal_is_rejected() -> None:
    raw = proposal(
        changes=[
            {"lever": "capacity:adjuster", "value": 8},
            {"lever": "capacity:fraud_analyst", "value": 2},
        ]
    )
    out = run_proposal("x", PACK, Scripted([raw]))
    assert out.status == "rejected"
    assert any(i.code == "over_budget" for i in out.issues)


def test_provider_errors_and_budget_exhaustion_stop_explicitly() -> None:
    assert run_proposal("x", PACK, Scripted([RuntimeError("boom")])).status == "provider_error"
    assert run_proposal("x", PACK, Scripted([BudgetExhausted("cap")])).status == "budget_exhausted"


def test_scripted_fake_on_labelled_requests_never_makes_controls_runnable() -> None:
    rep = evaluate(FakeProposer())
    assert rep.proposer_kind == "scripted"
    assert rep.n == 36
    assert rep.control_requests == 6 and rep.control_requests_runnable == 0
    # Regression guard on the published scripted result (see results/agent/eval-fake.md).
    assert rep.correct == 35
