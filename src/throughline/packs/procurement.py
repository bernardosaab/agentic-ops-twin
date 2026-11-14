"""Synthetic procurement-exception pack (hand-authored parameters, version packs-v1).

Flow: capture -> classify (manual clerk, or ML-assisted with fallout to clerk review) ->
buyer resolution (price mismatches) or receipt chase (missing receipts) -> three-way match
(mandatory control, bounded rework back to resolution) -> segregation-of-duties approval for
high-value invoices (mandatory control) -> posting.
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
    after_match = [
        rule(
            [br("resolution", 0.12, max_traversals=2), br("sod_approval", 0.88)],
            when=(">=", HIGH_VALUE),
            fallback_to="sod_approval",
        ),
        rule(
            [br("resolution", 0.12, max_traversals=2), br("post", 0.88)], fallback_to="sod_approval"
        ),
    ]
    model = OperatingModel.model_validate(
        {
            "id": "procurement-exceptions",
            "version": "1.0.0",
            "description": "Synthetic accounts-payable invoice exceptions with matching controls.",
            "currency": "USD",
            "horizon_hours": 320.0,
            "warmup_hours": 40.0,
            "sla_hours": 16.0,
            "sla_penalty_per_miss": 25.0,
            "queue_policy": "fifo",
            "high_value_threshold": HIGH_VALUE,
            "case_types": [
                case_type("price_mismatch", 2.0, "capture", 4000.0, 1.0),
                case_type("missing_receipt", 1.0, "capture", 2500.0, 0.8),
            ],
            "resources": [
                resource("ap_clerk", "human", 3, 32.0),
                resource("matching_engine", "automation", 3, 4.0),
                resource("buyer", "human", 3, 48.0),
                resource("receiving_clerk", "human", 1, 30.0),
                resource("finance_approver", "human", 1, 85.0),
                resource("erp_posting", "automation", 2, 1.0),
            ],
            "steps": [
                step(
                    "capture",
                    "Capture exception and supporting documents.",
                    {
                        "manual": variant(
                            "ap_clerk", svc("lognormal", 0.2, 0.5), 0.3, to("classify")
                        ),
                    },
                ),
                step(
                    "classify",
                    "Classify the exception and route it.",
                    {
                        "manual": variant(
                            "ap_clerk",
                            svc("lognormal", 0.3, 0.6),
                            0.5,
                            [
                                rule([br("resolution", 0.67), br("receipt_chase", 0.33)]),
                            ],
                        ),
                        "ml_assisted": variant(
                            "matching_engine",
                            svc("deterministic", 0.03),
                            0.6,
                            [
                                rule(
                                    [
                                        br("resolution", 0.5),
                                        br("receipt_chase", 0.25),
                                        br(
                                            "classify_review",
                                            0.25,
                                            escalation=True,
                                            param="classify_fallout",
                                        ),
                                    ]
                                ),
                            ],
                        ),
                    },
                ),
                step(
                    "classify_review",
                    "Clerk reviews an exception the model could not route.",
                    {
                        "manual": variant(
                            "ap_clerk",
                            svc("lognormal", 0.35, 0.6),
                            0.5,
                            [
                                rule([br("resolution", 0.67), br("receipt_chase", 0.33)]),
                            ],
                        ),
                    },
                ),
                step(
                    "resolution",
                    "Buyer resolves price or quantity discrepancy with supplier.",
                    {
                        "manual": variant(
                            "buyer", svc("lognormal", 1.0, 0.9), 2.0, to("three_way_match")
                        ),
                    },
                ),
                step(
                    "receipt_chase",
                    "Receiving confirms goods receipt.",
                    {
                        "manual": variant(
                            "receiving_clerk",
                            svc("lognormal", 0.6, 0.7),
                            1.0,
                            to("three_way_match"),
                        ),
                    },
                ),
                step(
                    "three_way_match",
                    "Clerk verifies PO, receipt and invoice agree.",
                    {
                        "manual": variant(
                            "ap_clerk", svc("lognormal", 0.25, 0.5), 0.5, after_match
                        ),
                    },
                ),
                step(
                    "sod_approval",
                    "Independent finance approval (segregation of duties).",
                    {
                        "manual": variant(
                            "finance_approver", svc("lognormal", 0.4, 0.5), 2.0, to("post")
                        ),
                    },
                ),
                step(
                    "post",
                    "Post the invoice to the ledger.",
                    {
                        "auto": variant("erp_posting", svc("deterministic", 0.02), 0.1, to("done")),
                    },
                ),
            ],
            "controls": [
                {
                    "id": "three-way-match",
                    "step": "three_way_match",
                    "description": "Every exception must pass a three-way match before posting.",
                    "applies_to": ["price_mismatch", "missing_receipt"],
                    "when": None,
                },
                {
                    "id": "sod-high-value",
                    "step": "sod_approval",
                    "description": "Invoices of 10,000 or more need independent finance approval.",
                    "applies_to": ["price_mismatch", "missing_receipt"],
                    "when": {"op": ">=", "threshold": HIGH_VALUE},
                },
            ],
            "assumptions": [
                {
                    "id": "proc-a1",
                    "source": "synthetic-hand-authored",
                    "text": "Case type is not observed by routing; classification splits 67/33.",
                },
                {
                    "id": "proc-a2",
                    "source": "synthetic-hand-authored",
                    "text": "ML-assisted classification sends 25% of exceptions to clerk review.",
                },
                {
                    "id": "proc-a3",
                    "source": "synthetic-hand-authored",
                    "text": "12% of matches fail back to resolution (max twice), then approval.",
                },
                {
                    "id": "proc-a4",
                    "source": "synthetic-hand-authored",
                    "text": "Supplier response time is folded into buyer service time.",
                },
            ],
        }
    )
    space = DecisionSpace(
        levers=(
            CapacityLever(resource="ap_clerk", min=2, max=4),
            CapacityLever(resource="buyer", min=3, max=5),
            CapacityLever(resource="receiving_clerk", min=1, max=2),
            VariantLever(step="classify", allowed=("manual", "ml_assisted")),
            PriorityLever(allowed=("fifo", "high_value_first")),
        ),
        max_staffed_cost_per_hour=520.0,
        max_alternatives=200,
    )
    return DomainPack(
        id="procurement",
        title="Procurement exceptions",
        description="Invoice exception handling with ML-assisted classification and AP controls.",
        generator_version=GENERATOR_VERSION,
        model=model,
        decision_space=space,
        lever_docs=(
            LeverDoc(key="capacity:ap_clerk", meaning="Accounts-payable clerks."),
            LeverDoc(key="capacity:buyer", meaning="Buyers resolving supplier discrepancies."),
            LeverDoc(key="capacity:receiving_clerk", meaning="Receiving clerks."),
            LeverDoc(key="variant:classify", meaning="'manual' or 'ml_assisted' classification."),
            LeverDoc(
                key="priority:queue_policy", meaning="'fifo' or 'high_value_first' queue ordering."
            ),
        ),
        splits=standard_splits(
            [
                DemandCondition(
                    name="receipt_heavy",
                    arrival_multiplier=1.0,
                    case_type_multipliers={"price_mismatch": 0.8, "missing_receipt": 1.5},
                ),
            ]
        ),
        decision_rule=DecisionRule(min_completion_rate=0.95, min_sla_attainment=0.85),
        sensitivity=(
            SensitivityParam(name="arrival_rate", kind="arrival", target=None, low=0.8, high=1.2),
            SensitivityParam(
                name="buyer_service_time", kind="service_scale", target="buyer", low=0.8, high=1.2
            ),
            SensitivityParam(
                name="classify_fallout",
                kind="branch_probability",
                target="classify_fallout",
                low=0.15,
                high=0.35,
            ),
        ),
        hidden_truth=HiddenTruth(
            mechanisms=HiddenMechanisms(handoff_delay_hours=0.3, absenteeism_probability=0.1),
            hourly_profile=PEAKED_PROFILE,
            note="Truth adds 0.3h handoff delays, 10% per-shift absenteeism and a daily peak.",
        ),
    )
