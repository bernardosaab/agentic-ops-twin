"""Opt-in adapter behaviour with a stubbed SDK client (no network, no credentials)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

anthropic = pytest.importorskip("anthropic")

from agentic_ops_twin.agent import anthropic_adapter as aa  # noqa: E402
from agentic_ops_twin.agent.loop import run_proposal  # noqa: E402
from agentic_ops_twin.packs import get_pack  # noqa: E402


class StubMessages:
    def __init__(self, text: str, stop: str = "end_turn") -> None:
        self.text, self.stop = text, stop
        self.requests: list[dict[str, Any]] = []

    def create(self, **kw: Any) -> Any:
        self.requests.append(kw)
        return SimpleNamespace(
            model="claude-haiku-5-5",
            stop_reason=self.stop,
            usage=SimpleNamespace(input_tokens=1200, output_tokens=150),
            content=[SimpleNamespace(type="text", text=self.text)],
        )


@pytest.fixture
def stub(monkeypatch: pytest.MonkeyPatch) -> StubMessages:
    msgs = StubMessages(
        json.dumps(
            {
                "pack_id": "insurance",
                "in_scope": True,
                "changes": [{"lever": "capacity:adjuster", "value": 7}],
                "demand_condition": "normal",
                "unknowns": [],
                "rationale": "stub",
            }
        )
    )

    class StubClient:
        def __init__(self, **_: Any) -> None:
            self.messages = msgs

    monkeypatch.setattr(anthropic, "Anthropic", StubClient)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-secret-value")
    return msgs


def test_requires_explicit_cost_cap() -> None:
    with pytest.raises(ValueError, match="cap"):
        aa.AnthropicProposer(max_cost_usd=0)


def test_request_shape_usage_and_cost(stub: StubMessages) -> None:
    prop = aa.AnthropicProposer(max_cost_usd=0.05)
    out = run_proposal("Add 1 adjuster under normal demand.", get_pack("insurance"), prop)
    assert out.status == "ok"
    req = stub.requests[0]
    assert req["model"] == "claude-haiku-5-5"
    assert req["output_config"]["format"]["type"] == "json_schema"
    assert "temperature" not in req
    sent = json.dumps(req)
    assert "sk-test-secret-value" not in sent
    usage = out.attempts[0].usage
    assert usage is not None and usage.input_tokens == 1200
    in_p, out_p = aa.price_for("claude-haiku-5-5")  # type: ignore[misc]
    assert usage.estimated_cost_usd == pytest.approx((1200 * in_p + 150 * out_p) / 1e6)


def test_budget_cap_stops_before_calling(stub: StubMessages) -> None:
    prop = aa.AnthropicProposer(max_cost_usd=1e-7)
    out = run_proposal("Add 1 adjuster under normal demand.", get_pack("insurance"), prop)
    assert out.status == "budget_exhausted"
    assert stub.requests == []


def test_refusal_and_invalid_output_are_not_guessed(stub: StubMessages) -> None:
    stub.stop = "refusal"
    prop = aa.AnthropicProposer(max_cost_usd=0.05)
    assert run_proposal("x", get_pack("insurance"), prop).status == "provider_error"
    stub.stop, stub.text = "end_turn", "I think you should add staff."
    out = run_proposal("x", get_pack("insurance"), aa.AnthropicProposer(max_cost_usd=0.05))
    assert out.status == "invalid_output" and len(out.attempts) == 2
