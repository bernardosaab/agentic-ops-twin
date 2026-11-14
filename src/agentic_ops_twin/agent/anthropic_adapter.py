"""Opt-in Anthropic Claude adapter for scenario proposals and brief narratives.

Never used unless explicitly selected (``--provider anthropic``) with a cost cap. Only the
synthetic pack description, the operator's request and stored simulation facts are sent; no
credentials, private data or environment details. All output is untrusted and validated
downstream. Pricing comes from ``prices.toml`` (assumptions with an as-of date, not measurements).
"""

from __future__ import annotations

import json
import time
import tomllib
from importlib import resources
from typing import Any, Literal

from agentic_ops_twin.agent.contracts import ProposerOutput, Usage, proposal_json_schema
from agentic_ops_twin.agent.loop import BudgetExhausted

DEFAULT_MODEL = "claude-haiku-5-5"

SYSTEM_PROMPT = (
    "You convert an operator's what-if request about a simulated business process into a JSON "
    "scenario proposal. Use only lever keys and demand-condition names listed in the context. "
    "Never invent values: if the request does not state a number or choice, set value to null "
    "and add a question to 'unknowns'. If the request does not name a demand condition, set "
    "demand_condition to null. Mandatory controls cannot be changed; if the request asks to "
    "skip or remove one, include a change with lever 'remove_control:<control id>' so it can be "
    "rejected. If the request is not a what-if over these levers (for example deploying "
    "changes to live systems), set in_scope to false. Capacity values are absolute totals."
)


def load_prices() -> dict[str, Any]:
    text = resources.files("agentic_ops_twin").joinpath("prices.toml").read_text(encoding="utf-8")
    return tomllib.loads(text)


def price_for(model: str) -> tuple[float, float] | None:
    entry = load_prices().get("models", {}).get(model)
    if entry is None:
        return None
    return float(entry["input_per_mtok"]), float(entry["output_per_mtok"])


class _Client:
    """Thin wrapper holding the SDK client, a spend cap and cumulative estimated spend."""

    def __init__(self, model: str, max_cost_usd: float, max_tokens: int, timeout_s: float) -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise RuntimeError("install the optional extra: pip install -e '.[llm]'") from exc
        if max_cost_usd <= 0:
            raise ValueError("an explicit positive --max-cost-usd cap is required")
        prices = price_for(model)
        if prices is None:
            raise ValueError(f"no pricing assumption for '{model}' in prices.toml; add one first")
        self.model = model
        self.prices = prices
        self.max_cost_usd = max_cost_usd
        self.max_tokens = max_tokens
        self.spent_usd = 0.0
        self.calls: list[Usage] = []
        self._anthropic = anthropic
        self._client = anthropic.Anthropic(timeout=timeout_s, max_retries=1)

    def _cost(self, inp: int, out: int) -> float:
        return (inp * self.prices[0] + out * self.prices[1]) / 1_000_000

    def call(
        self, system: str, user: str, output_format: dict[str, Any] | None
    ) -> tuple[str, Usage]:
        worst = self._cost(len(system + user) // 2 + 50, self.max_tokens)
        if self.spent_usd + worst > self.max_cost_usd:
            raise BudgetExhausted(
                f"next call could cost up to ${worst:.5f}; cap ${self.max_cost_usd:.4f} with "
                f"${self.spent_usd:.5f} already spent"
            )
        output_config: Any = {"effort": "low"}
        if output_format is not None:
            output_config["format"] = output_format
        messages: Any = [{"role": "user", "content": user}]
        t0 = time.perf_counter()
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=messages,
            output_config=output_config,
        )
        latency = time.perf_counter() - t0
        inp = getattr(resp.usage, "input_tokens", None)
        out = getattr(resp.usage, "output_tokens", None)
        cost = self._cost(inp, out) if inp is not None and out is not None else None
        self.spent_usd += cost if cost is not None else worst
        usage = Usage(
            provider="anthropic",
            requested_model=self.model,
            reported_model=getattr(resp, "model", None),
            input_tokens=inp,
            output_tokens=out,
            estimated_cost_usd=cost,
            latency_seconds=latency,
            stop_reason=getattr(resp, "stop_reason", None),
        )
        self.calls.append(usage)
        if resp.stop_reason == "refusal":
            raise RuntimeError("provider declined the request (stop_reason=refusal)")
        if resp.stop_reason == "max_tokens":
            raise RuntimeError("output truncated at max_tokens")
        text = next(
            (str(getattr(b, "text", "")) for b in resp.content if getattr(b, "type", "") == "text"),
            "",
        )
        return text, usage


class AnthropicProposer:
    kind: Literal["scripted", "model"] = "model"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        *,
        max_cost_usd: float,
        max_tokens: int = 2048,
        timeout_s: float = 60.0,
    ) -> None:
        self._c = _Client(model, max_cost_usd, max_tokens, timeout_s)
        self.name = f"anthropic:{model}"

    @property
    def spent_usd(self) -> float:
        return self._c.spent_usd

    @property
    def calls(self) -> list[Usage]:
        return self._c.calls

    def propose(
        self, request: str, context: dict[str, Any], feedback: list[str] | None = None
    ) -> ProposerOutput:
        user = "Context (synthetic simulation pack):\n" + json.dumps(context, indent=1)
        user += "\n\nOperator request:\n" + request
        if feedback:
            user += (
                "\n\nYour previous proposal was rejected by the validator for these "
                "reasons; return a corrected proposal:\n- " + "\n- ".join(feedback)
            )
        fmt = {"type": "json_schema", "schema": proposal_json_schema()}
        text, usage = self._c.call(SYSTEM_PROMPT, user, fmt)
        return ProposerOutput(raw_text=text, usage=usage)


NARRATIVE_PROMPT = (
    "Write a short neutral summary (at most 120 words) of the simulation facts provided. Every "
    "number you write must be copied exactly from a fact and followed by its citation tag, for "
    "example '12.5 [F3]'. Do not compute new numbers, do not recommend deployment, and state that "
    "results are conditional on the model's assumptions."
)


class AnthropicNarrator:
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        *,
        max_cost_usd: float,
        max_tokens: int = 1024,
        timeout_s: float = 60.0,
    ) -> None:
        self._c = _Client(model, max_cost_usd, max_tokens, timeout_s)
        self.name = f"anthropic:{model}"

    @property
    def calls(self) -> list[Usage]:
        return self._c.calls

    def narrate(self, facts_text: str) -> tuple[str, Usage]:
        return self._c.call(NARRATIVE_PROMPT, facts_text, None)
