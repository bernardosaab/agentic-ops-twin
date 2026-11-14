"""Scenario-proposal evaluation against labelled synthetic requests.

Scores the *end-to-end* outcome (proposer + trusted critic) per request: status, error code,
exact change set and demand condition. Control-removal requests are additionally checked for the
safety property that no such request ever yields a runnable scenario.

Scripted-fake results describe hand-written rules on requests by the same authors; they are not a
measurement of AI capability. Real-model results are reported only from actual runs, with usage.
"""

from __future__ import annotations

import json
from collections import defaultdict
from importlib import resources
from typing import Any

from pydantic import BaseModel, ConfigDict

from agentic_ops_twin.agent.contracts import Proposer
from agentic_ops_twin.agent.loop import ProposalOutcome, run_proposal
from agentic_ops_twin.packs import get_pack


class LabelledRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    pack: str
    split: str
    category: str
    text: str
    expected: dict[str, Any]


class RequestResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    pack: str
    split: str
    category: str
    expected_status: str
    actual_status: str
    expected_code: str | None
    actual_codes: list[str]
    correct: bool
    reason: str
    outcome: ProposalOutcome


class EvalReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    proposer: str
    proposer_kind: str
    dataset_version: str
    n: int
    correct: int
    by_split: dict[str, dict[str, int]]
    by_category: dict[str, dict[str, int]]
    control_requests: int
    control_requests_runnable: int
    invalid_outputs: int
    provider_errors: int
    total_input_tokens: int | None
    total_output_tokens: int | None
    total_estimated_cost_usd: float | None
    results: list[RequestResult]


def load_requests() -> tuple[str, list[LabelledRequest]]:
    raw = (
        resources.files("agentic_ops_twin.packs")
        .joinpath("data/requests.json")
        .read_text(encoding="utf-8")
    )
    data = json.loads(raw)
    return data["version"], [LabelledRequest.model_validate(r) for r in data["requests"]]


def score(req: LabelledRequest, out: ProposalOutcome) -> tuple[bool, str]:
    exp = req.expected
    codes = [i.code for i in out.issues]
    if out.status != exp["status"]:
        return False, f"status {out.status} != expected {exp['status']}"
    if exp["status"] == "rejected" and exp.get("code") not in codes:
        return False, f"expected code {exp.get('code')} not in {codes}"
    if exp["status"] == "ok":
        assert out.change_set is not None
        got = {c.lever: c.value for c in out.change_set.changes}
        if got != exp["changes"]:
            return False, f"changes {got} != expected {exp['changes']}"
        if out.demand_condition != exp["condition"]:
            return False, f"condition {out.demand_condition} != expected {exp['condition']}"
    return True, "match"


def evaluate(
    proposer: Proposer,
    *,
    split: str | None = None,
    pack: str | None = None,
    limit: int | None = None,
) -> EvalReport:
    version, reqs = load_requests()
    reqs = [
        r for r in reqs if (split is None or r.split == split) and (pack is None or r.pack == pack)
    ]
    if limit is not None:
        reqs = reqs[:limit]
    results: list[RequestResult] = []
    by_split: dict[str, dict[str, int]] = defaultdict(lambda: {"n": 0, "correct": 0})
    by_cat: dict[str, dict[str, int]] = defaultdict(lambda: {"n": 0, "correct": 0})
    tin = tout = 0
    cost = 0.0
    have_usage = False
    usage_complete = True
    for r in reqs:
        out = run_proposal(r.text, get_pack(r.pack), proposer)
        ok, reason = score(r, out)
        for a in out.attempts:
            if a.usage is not None:
                have_usage = True
                if (
                    a.usage.input_tokens is None
                    or a.usage.output_tokens is None
                    or a.usage.estimated_cost_usd is None
                ):
                    usage_complete = False
                else:
                    tin += a.usage.input_tokens
                    tout += a.usage.output_tokens
                    cost += a.usage.estimated_cost_usd
        results.append(
            RequestResult(
                id=r.id,
                pack=r.pack,
                split=r.split,
                category=r.category,
                expected_status=r.expected["status"],
                actual_status=out.status,
                expected_code=r.expected.get("code"),
                actual_codes=[i.code for i in out.issues],
                correct=ok,
                reason=reason,
                outcome=out,
            )
        )
        for bucket in (by_split[r.split], by_cat[r.category]):
            bucket["n"] += 1
            bucket["correct"] += int(ok)
    controls = [x for x in results if x.category == "control"]
    return EvalReport(
        proposer=proposer.name,
        proposer_kind=proposer.kind,
        dataset_version=version,
        n=len(results),
        correct=sum(x.correct for x in results),
        by_split=dict(by_split),
        by_category=dict(by_cat),
        control_requests=len(controls),
        control_requests_runnable=sum(x.actual_status == "ok" for x in controls),
        invalid_outputs=sum(x.actual_status == "invalid_output" for x in results),
        provider_errors=sum(x.actual_status == "provider_error" for x in results),
        total_input_tokens=tin if have_usage and usage_complete else None,
        total_output_tokens=tout if have_usage and usage_complete else None,
        total_estimated_cost_usd=round(cost, 6) if have_usage and usage_complete else None,
        results=results,
    )
