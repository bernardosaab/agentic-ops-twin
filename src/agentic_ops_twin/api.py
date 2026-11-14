"""Local FastAPI service.

Unauthenticated and intended for ``127.0.0.1`` only. Requests are bounded (replication and seed
limits) to keep the local service responsive. Model calls are never made from the API; it uses
the scripted proposer only.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from agentic_ops_twin.agent.contracts import pack_context
from agentic_ops_twin.agent.fake import FakeProposer
from agentic_ops_twin.agent.loop import ProposalOutcome, run_proposal
from agentic_ops_twin.decision.experiment import Job, ScenarioResult, run_jobs
from agentic_ops_twin.decision.scenarios import ChangeRejected, ChangeSet, apply_changes
from agentic_ops_twin.packs import PACK_IDS, get_pack
from agentic_ops_twin.simulation.model import OperatingModel
from agentic_ops_twin.simulation.validate import ValidationReport, validate

MAX_REPLICATIONS = 20

app = FastAPI(
    title="Agentic Ops Twin (local prototype)",
    description="Capacity-aware operating-model simulation. Local, unauthenticated, synthetic "
    "data only; never deploys changes to any system.",
    version="0.1.0",
)


class ExperimentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pack: str
    change_set: ChangeSet
    condition: str
    seeds: list[int] = Field(min_length=2, max_length=MAX_REPLICATIONS)


class ProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pack: str
    request: str = Field(min_length=1, max_length=2000)


def _pack(pid: str) -> Any:
    if pid not in PACK_IDS:
        raise HTTPException(404, f"unknown pack '{pid}'")
    return get_pack(pid)


@app.get("/packs")
def packs() -> list[dict[str, Any]]:
    return [pack_context(get_pack(p)) for p in PACK_IDS]


@app.get("/packs/{pid}/model")
def pack_model(pid: str) -> OperatingModel:
    return _pack(pid).model  # type: ignore[no-any-return]


@app.post("/validate")
def validate_model(model: OperatingModel) -> ValidationReport:
    return validate(model)


@app.post("/experiments")
def experiment(req: ExperimentRequest) -> list[ScenarioResult]:
    pack = _pack(req.pack)
    try:
        cond = pack.condition(req.condition)
        changed, _ = apply_changes(pack.model, pack.decision_space, req.change_set)
    except KeyError as exc:
        raise HTTPException(422, str(exc)) from exc
    except ChangeRejected as exc:
        raise HTTPException(422, {"rejected": [i.model_dump() for i in exc.issues]}) from exc
    seeds = tuple(req.seeds)
    return run_jobs(
        [
            Job(pack.model, seeds, cond, "baseline", "baseline"),
            Job(changed, seeds, cond, req.change_set.name, req.change_set.label()),
        ],
        workers=1,
    )


@app.post("/proposals")
def proposals(req: ProposalRequest) -> ProposalOutcome:
    return run_proposal(req.request, _pack(req.pack), FakeProposer())
