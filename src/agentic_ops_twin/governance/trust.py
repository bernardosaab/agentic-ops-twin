"""Model trust gate: may this twin's output inform a change at all?

The hidden-truth study showed that a twin can match history on completion rate while being badly
wrong about cycle times and SLA attainment. So "fits history" is not a release criterion. This
gate classifies the twin from evidence about the history it is meant to represent:

* ``validated``: an observed history was checked and no residual diagnostic flagged an
  unmodelled mechanism. This is necessary for trust, not sufficient.
* ``unvalidated``: no observed history was assessed (for example, a hand-authored synthetic
  model). Changes may proceed only under the high-risk approval path, with every approver
  explicitly acknowledging this status.
* ``inadequate``: at least one residual diagnostic flagged a mechanism the twin omits. The
  gate fails closed and no change package can be released.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from agentic_ops_twin.research.calibrate import Diagnostic, diagnose
from agentic_ops_twin.simulation.engine import LogEvent
from agentic_ops_twin.simulation.exogenous import Arrival
from agentic_ops_twin.simulation.model import Frozen, OperatingModel

TrustStatus = Literal["validated", "unvalidated", "inadequate"]


class TrustAssessment(Frozen):
    model_id: str
    model_digest: str
    status: TrustStatus
    evidence: str
    history_hours: float | None
    diagnostics: tuple[Diagnostic, ...]
    effect: str


def assess(
    model: OperatingModel,
    *,
    arrivals: Sequence[Arrival] | None = None,
    events: Sequence[LogEvent] | None = None,
    history_hours: float | None = None,
    evidence: str = "",
) -> TrustAssessment:
    if arrivals is None or events is None or history_hours is None:
        return TrustAssessment(
            model_id=model.id,
            model_digest=model.digest(),
            status="unvalidated",
            evidence=evidence or "no observed history assessed",
            history_hours=None,
            diagnostics=(),
            effect="release requires the high-risk path and explicit acknowledgement by every "
            "approver",
        )
    diags = tuple(diagnose(model, arrivals, events, history_hours))
    flagged = [d.name for d in diags if d.flagged]
    if flagged:
        return TrustAssessment(
            model_id=model.id,
            model_digest=model.digest(),
            status="inadequate",
            evidence=evidence,
            history_hours=history_hours,
            diagnostics=diags,
            effect="release blocked: history shows mechanisms the twin omits ("
            + ", ".join(flagged)
            + ")",
        )
    return TrustAssessment(
        model_id=model.id,
        model_digest=model.digest(),
        status="validated",
        evidence=evidence,
        history_hours=history_hours,
        diagnostics=diags,
        effect="no residual diagnostic flagged; standard risk tiers apply",
    )


def load_history(arrivals_csv: Path, events_csv: Path) -> tuple[list[Arrival], list[LogEvent]]:
    """Read the CSV format written by ``ops-twin dataset`` (an observed event-log export)."""
    with arrivals_csv.open(encoding="utf-8") as fh:
        arrivals = [
            Arrival(r["case_id"], r["case_type"], float(r["arrival_hours"]), float(r["value"]))
            for r in csv.DictReader(fh)
        ]
    with events_csv.open(encoding="utf-8") as fh:
        events = [
            LogEvent(
                r["case_id"],
                r["case_type"],
                float(r["value"]),
                float(r["arrival"]),
                r["step"],
                r["resource"],
                float(r["queued"]),
                float(r["start"]),
                float(r["end"]),
                r["next_step"],
            )
            for r in csv.DictReader(fh)
        ]
    return arrivals, events
