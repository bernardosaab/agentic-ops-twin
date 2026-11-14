"""Synthetic insurance-claims pack (hand-authored parameters, version packs-v1).

Flow: intake -> triage (manual officer, or automated model whose fallout goes to adjuster
review) -> assessment (adjusters, with bounded rework) -> fraud check and senior approval for
high-value claims (mandatory controls) -> settlement.
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

HIGH_VALUE = 10_000.0


def build() -> DomainPack:
    after_assessment = [
        rule([br("fraud_check", 1.0)], when=(">=", HIGH_VALUE)),
        rule(
            [br("settlement", 0.92), br("assessment", 0.08, max_traversals=2)],
            fallback_to="settlement",
        ),
    ]
    model = OperatingModel.model_validate(
        {
            "id": "insurance-claims",
            "version": "1.0.0",
            "description": "Synthetic motor and property claims handling with high-value controls.",
            "currency": "USD",
            "horizon_hours": 320.0,
            "warmup_hours": 40.0,
            "sla_hours": 24.0,
            "sla_penalty_per_miss": 40.0,
            "queue_policy": "fifo",
            "high_value_threshold": HIGH_VALUE,
            "case_types": [
                case_type("standard_claim", 3.0, "intake", 1500.0, 0.9),
                case_type("complex_claim", 0.6, "intake", 8000.0, 0.7),
            ],
            "resources": [
                resource("intake_clerk", "human", 2, 35.0),
                resource("triage_officer", "human", 2, 40.0),
                resource("triage_model", "automation", 4, 3.0),
                resource("adjuster", "human", 6, 55.0),
                resource("fraud_analyst", "human", 1, 70.0),
                resource("senior_approver", "human", 1, 90.0),
                resource("payments_system", "automation", 2, 1.0),
            ],
            "steps": [
                step(
                    "intake",
                    "Register claim and documents.",
                    {
                        "manual": variant(
                            "intake_clerk", svc("lognormal", 0.25, 0.5), 0.5, to("triage")
                        ),
                    },
                ),
                step(
                    "triage",
                    "Classify severity and route.",
                    {
                        "manual": variant(
                            "triage_officer", svc("lognormal", 0.5, 0.6), 1.0, to("assessment")
                        ),
                        "automated": variant(
                            "triage_model",
                            svc("deterministic", 0.02),
                            0.8,
                            [
                                rule(
                                    [
                                        br("assessment", 0.78),
                                        br(
                                            "manual_review",
                                            0.22,
                                            escalation=True,
                                            param="triage_fallout",
                                        ),
                                    ]
                                ),
                            ],
                        ),
                    },
                ),
                step(
                    "manual_review",
                    "Adjuster reviews a claim the model could not classify.",
                    {
                        "manual": variant(
                            "adjuster", svc("lognormal", 0.6, 0.6), 1.0, to("assessment")
                        ),
                    },
                ),
                step(
                    "assessment",
                    "Adjuster assesses liability and amount.",
                    {
                        "manual": variant(
                            "adjuster", svc("lognormal", 1.2, 0.8), 2.0, after_assessment
                        ),
                    },
                ),
                step(
                    "fraud_check",
                    "Fraud analyst review.",
                    {
                        "manual": variant(
                            "fraud_analyst", svc("lognormal", 0.8, 0.7), 3.0, to("senior_approval")
                        ),
                    },
                ),
                step(
                    "senior_approval",
                    "Senior approval of high-value settlement.",
                    {
                        "manual": variant(
                            "senior_approver", svc("lognormal", 0.5, 0.5), 3.0, to("settlement")
                        ),
                    },
                ),
                step(
                    "settlement",
                    "Automated payment instruction.",
                    {
                        "auto": variant(
                            "payments_system", svc("deterministic", 0.05), 0.2, to("done")
                        ),
                    },
                ),
            ],
            "controls": [
                {
                    "id": "fraud-review-high-value",
                    "step": "fraud_check",
                    "description": "Claims of 10,000 or more must receive a fraud review.",
                    "applies_to": ["standard_claim", "complex_claim"],
                    "when": {"op": ">=", "threshold": HIGH_VALUE},
                },
                {
                    "id": "senior-approval-high-value",
                    "step": "senior_approval",
                    "description": "Claims of 10,000 or more need senior approval before payment.",
                    "applies_to": ["standard_claim", "complex_claim"],
                    "when": {"op": ">=", "threshold": HIGH_VALUE},
                },
            ],
            "assumptions": [
                {
                    "id": "ins-a1",
                    "source": "synthetic-hand-authored",
                    "text": "Arrivals are stationary Poisson over operating hours; no calendar.",
                },
                {
                    "id": "ins-a2",
                    "source": "synthetic-hand-authored",
                    "text": "Automated triage sends 22% of claims to adjuster review (fallout).",
                },
                {
                    "id": "ins-a3",
                    "source": "synthetic-hand-authored",
                    "text": "8% of assessments need one more assessment pass (at most two extra).",
                },
                {
                    "id": "ins-a4",
                    "source": "synthetic-hand-authored",
                    "text": "Staff are always available; no absenteeism or handoff delay.",
                },
                {
                    "id": "ins-a5",
                    "source": "synthetic-hand-authored",
                    "text": "SLA miss penalty of 40 per case represents customer and rework cost.",
                },
            ],
        }
    )
    space = DecisionSpace(
        levers=(
            CapacityLever(resource="triage_officer", min=1, max=3),
            CapacityLever(resource="adjuster", min=5, max=8),
            CapacityLever(resource="fraud_analyst", min=1, max=2),
            VariantLever(step="triage", allowed=("manual", "automated")),
            PriorityLever(allowed=("fifo", "high_value_first")),
        ),
        max_staffed_cost_per_hour=760.0,
        max_alternatives=200,
    )
    return DomainPack(
        id="insurance",
        title="Insurance claims",
        description="Claims handling with automated-triage option and high-value controls.",
        generator_version=GENERATOR_VERSION,
        model=model,
        decision_space=space,
        lever_docs=(
            LeverDoc(key="capacity:triage_officer", meaning="Number of manual triage officers."),
            LeverDoc(key="capacity:adjuster", meaning="Number of claim adjusters (reviewers)."),
            LeverDoc(key="capacity:fraud_analyst", meaning="Number of fraud analysts."),
            LeverDoc(key="variant:triage", meaning="'manual' officers or 'automated' model."),
            LeverDoc(
                key="priority:queue_policy", meaning="'fifo' or 'high_value_first' queue ordering."
            ),
        ),
        splits=standard_splits(
            [
                DemandCondition(
                    name="complex_mix",
                    arrival_multiplier=1.0,
                    case_type_multipliers={"standard_claim": 0.85, "complex_claim": 1.75},
                ),
            ]
        ),
        decision_rule=DecisionRule(min_completion_rate=0.95, min_sla_attainment=0.85),
        sensitivity=(
            SensitivityParam(name="arrival_rate", kind="arrival", target=None, low=0.8, high=1.2),
            SensitivityParam(
                name="adjuster_service_time",
                kind="service_scale",
                target="adjuster",
                low=0.8,
                high=1.2,
            ),
            SensitivityParam(
                name="triage_fallout",
                kind="branch_probability",
                target="triage_fallout",
                low=0.12,
                high=0.32,
            ),
        ),
        hidden_truth=HiddenTruth(
            mechanisms=HiddenMechanisms(handoff_delay_hours=0.2, absenteeism_probability=0.08),
            hourly_profile=PEAKED_PROFILE,
            note="Truth adds 0.2h handoff delays, 8% per-shift absenteeism and a daily peak.",
        ),
    )
