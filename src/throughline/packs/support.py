"""Synthetic customer-support escalation pack (hand-authored parameters, version packs-v1).

Flow: tier-1 intake -> routing (manual by tier 1, or automated classifier whose misroutes need a
tier-1 fix) -> tier 2 -> optional specialist -> QA review for refunds of 500 or more (mandatory
control) -> close.
"""

from __future__ import annotations

from throughline.core.engine import HiddenMechanisms
from throughline.core.exogenous import DemandCondition
from throughline.core.model import OperatingModel
from throughline.packs.base import (
    GENERATOR_VERSION,
    PEAKED_PROFILE,
    DecisionRule,
    DomainPack,
    HiddenTruth,
    LeverDoc,
    SensitivityParam,
    br,
    case_type,
    resource,
    rule,
    standard_splits,
    step,
    svc,
    to,
    variant,
)
from throughline.scenarios import CapacityLever, DecisionSpace, PriorityLever, VariantLever

REFUND_QA = 500.0


def _finish() -> list[dict[str, object]]:
    return [rule([br("qa_review", 1.0)], when=(">=", REFUND_QA)), rule([br("close", 1.0)])]


def build() -> DomainPack:
    model = OperatingModel.model_validate(
        {
            "id": "support-escalations",
            "version": "1.0.0",
            "description": "Synthetic customer-support escalations with refund QA control.",
            "currency": "USD",
            "horizon_hours": 320.0,
            "warmup_hours": 40.0,
            "sla_hours": 12.0,
            "sla_penalty_per_miss": 15.0,
            "queue_policy": "fifo",
            "high_value_threshold": REFUND_QA,
            "case_types": [
                case_type("billing_dispute", 4.0, "tier1_intake", 120.0, 1.0),
                case_type("technical_fault", 3.0, "tier1_intake", 60.0, 0.8),
            ],
            "resources": [
                resource("tier1_agent", "human", 4, 28.0),
                resource("routing_classifier", "automation", 2, 2.0),
                resource("tier2_agent", "human", 7, 40.0),
                resource("specialist", "human", 4, 65.0),
                resource("qa_lead", "human", 1, 50.0),
                resource("ticketing", "automation", 2, 0.5),
            ],
            "steps": [
                step(
                    "tier1_intake",
                    "Tier 1 gathers details.",
                    {
                        "manual": variant(
                            "tier1_agent", svc("lognormal", 0.3, 0.6), 0.3, to("routing")
                        ),
                    },
                ),
                step(
                    "routing",
                    "Route to the right tier-2 queue.",
                    {
                        "manual": variant(
                            "tier1_agent", svc("lognormal", 0.15, 0.5), 0.2, to("tier2")
                        ),
                        "auto_classify": variant(
                            "routing_classifier",
                            svc("deterministic", 0.01),
                            0.1,
                            [
                                rule(
                                    [
                                        br("tier2", 0.75),
                                        br(
                                            "misroute_fix",
                                            0.25,
                                            escalation=True,
                                            param="misroute_rate",
                                        ),
                                    ]
                                ),
                            ],
                        ),
                    },
                ),
                step(
                    "misroute_fix",
                    "Tier 1 corrects a misrouted ticket.",
                    {
                        "manual": variant(
                            "tier1_agent", svc("lognormal", 0.2, 0.5), 0.2, to("tier2")
                        ),
                    },
                ),
                step(
                    "tier2",
                    "Tier 2 investigates.",
                    {
                        "manual": variant(
                            "tier2_agent",
                            svc("lognormal", 0.8, 1.0),
                            1.0,
                            [
                                rule(
                                    [br("specialist", 0.3), br("qa_review", 1.0 - 0.3)],
                                    when=(">=", REFUND_QA),
                                ),
                                rule([br("specialist", 0.3), br("close", 0.7)]),
                            ],
                        ),
                    },
                ),
                step(
                    "specialist",
                    "Specialist resolves complex faults.",
                    {
                        "manual": variant("specialist", svc("lognormal", 1.5, 0.8), 2.0, _finish()),
                    },
                ),
                step(
                    "qa_review",
                    "QA lead reviews refunds of 500 or more.",
                    {
                        "manual": variant("qa_lead", svc("lognormal", 0.3, 0.5), 0.5, to("close")),
                    },
                ),
                step(
                    "close",
                    "Close ticket and notify customer.",
                    {
                        "auto": variant("ticketing", svc("deterministic", 0.01), 0.05, to("done")),
                    },
                ),
            ],
            "controls": [
                {
                    "id": "refund-qa",
                    "step": "qa_review",
                    "description": "Refunds of 500 or more must be reviewed by a QA lead.",
                    "applies_to": ["billing_dispute", "technical_fault"],
                    "when": {"op": ">=", "threshold": REFUND_QA},
                },
            ],
            "assumptions": [
                {
                    "id": "sup-a1",
                    "source": "synthetic-hand-authored",
                    "text": "Ticket value is the refund amount requested.",
                },
                {
                    "id": "sup-a2",
                    "source": "synthetic-hand-authored",
                    "text": "The automated classifier misroutes 25% of tickets; tier 1 fixes them.",
                },
                {
                    "id": "sup-a3",
                    "source": "synthetic-hand-authored",
                    "text": "30% of tier-2 tickets need a specialist, independent of ticket type.",
                },
            ],
        }
    )
    space = DecisionSpace(
        levers=(
            CapacityLever(resource="tier1_agent", min=3, max=5),
            CapacityLever(resource="tier2_agent", min=6, max=8),
            CapacityLever(resource="specialist", min=3, max=5),
            VariantLever(step="routing", allowed=("manual", "auto_classify")),
            PriorityLever(allowed=("fifo", "high_value_first")),
        ),
        max_staffed_cost_per_hour=760.0,
        max_alternatives=200,
    )
    return DomainPack(
        id="support",
        title="Customer-support escalations",
        description="Escalation handling with automated routing and refund QA control.",
        generator_version=GENERATOR_VERSION,
        model=model,
        decision_space=space,
        lever_docs=(
            LeverDoc(key="capacity:tier1_agent", meaning="Tier-1 agents."),
            LeverDoc(key="capacity:tier2_agent", meaning="Tier-2 agents."),
            LeverDoc(key="capacity:specialist", meaning="Specialists."),
            LeverDoc(key="variant:routing", meaning="'manual' or 'auto_classify' routing."),
            LeverDoc(
                key="priority:queue_policy",
                meaning="'fifo' or 'high_value_first' (refund value) queue ordering.",
            ),
        ),
        splits=standard_splits(
            [
                DemandCondition(
                    name="billing_spike",
                    arrival_multiplier=1.0,
                    case_type_multipliers={"billing_dispute": 1.4},
                ),
            ]
        ),
        decision_rule=DecisionRule(min_completion_rate=0.95, min_sla_attainment=0.85),
        sensitivity=(
            SensitivityParam(name="arrival_rate", kind="arrival", target=None, low=0.8, high=1.2),
            SensitivityParam(
                name="specialist_service_time",
                kind="service_scale",
                target="specialist",
                low=0.8,
                high=1.2,
            ),
            SensitivityParam(
                name="misroute_rate",
                kind="branch_probability",
                target="misroute_rate",
                low=0.15,
                high=0.35,
            ),
        ),
        hidden_truth=HiddenTruth(
            mechanisms=HiddenMechanisms(handoff_delay_hours=0.15, absenteeism_probability=0.1),
            hourly_profile=PEAKED_PROFILE,
            note="Truth adds 0.15h handoff delays, 10% per-shift absenteeism and a daily peak.",
        ),
    )
