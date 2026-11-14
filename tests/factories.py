"""Small hand-built operating models for analytical and edge-case tests."""

from __future__ import annotations

from typing import Any

from agentic_ops_twin.simulation.model import OperatingModel


def single_queue(
    *,
    rate: float,
    mean_service: float,
    servers: int,
    kind: str = "exponential",
    horizon: float = 2000.0,
    warmup: float = 200.0,
    value_sigma: float = 0.0,
) -> OperatingModel:
    return OperatingModel.model_validate(
        {
            "id": "single-queue",
            "version": "test",
            "description": "One step, one resource pool.",
            "currency": "USD",
            "horizon_hours": horizon,
            "warmup_hours": warmup,
            "sla_hours": 10.0,
            "sla_penalty_per_miss": 0.0,
            "queue_policy": "fifo",
            "high_value_threshold": 0.0,
            "case_types": [
                {
                    "name": "job",
                    "arrival_rate_per_hour": rate,
                    "entry_step": "serve",
                    "value": {"median": 100.0, "sigma": value_sigma},
                }
            ],
            "resources": [
                {"name": "server", "kind": "human", "capacity": servers, "cost_per_hour": 10.0}
            ],
            "steps": [
                {
                    "id": "serve",
                    "description": "Single service step.",
                    "active_variant": "manual",
                    "variants": {
                        "manual": {
                            "resource": "server",
                            "service": {"kind": kind, "mean": mean_service},
                            "cost_per_case": 1.0,
                            "routes": [
                                {"when": None, "branches": [{"to": "done", "probability": 1.0}]}
                            ],
                        }
                    },
                }
            ],
            "controls": [],
            "assumptions": [],
        }
    )


def controlled_flow(**overrides: Any) -> dict[str, Any]:
    """Two-step flow where high-value cases must pass a human approval control."""
    data: dict[str, Any] = {
        "id": "controlled",
        "version": "test",
        "description": "Intake then approval for high-value cases.",
        "currency": "USD",
        "horizon_hours": 200.0,
        "warmup_hours": 20.0,
        "sla_hours": 8.0,
        "sla_penalty_per_miss": 5.0,
        "queue_policy": "fifo",
        "high_value_threshold": 1000.0,
        "case_types": [
            {
                "name": "claim",
                "arrival_rate_per_hour": 2.0,
                "entry_step": "intake",
                "value": {"median": 800.0, "sigma": 0.8},
            }
        ],
        "resources": [
            {"name": "clerk", "kind": "human", "capacity": 2, "cost_per_hour": 30.0},
            {"name": "approver", "kind": "human", "capacity": 1, "cost_per_hour": 60.0},
            {"name": "bot", "kind": "automation", "capacity": 5, "cost_per_hour": 2.0},
        ],
        "steps": [
            {
                "id": "intake",
                "description": "Intake.",
                "active_variant": "manual",
                "variants": {
                    "manual": {
                        "resource": "clerk",
                        "service": {"kind": "exponential", "mean": 0.5},
                        "cost_per_case": 1.0,
                        "routes": [
                            {
                                "when": {"op": ">=", "threshold": 1000.0},
                                "branches": [{"to": "approve", "probability": 1.0}],
                            },
                            {"when": None, "branches": [{"to": "done", "probability": 1.0}]},
                        ],
                    }
                },
            },
            {
                "id": "approve",
                "description": "Human approval.",
                "active_variant": "manual",
                "variants": {
                    "manual": {
                        "resource": "approver",
                        "service": {"kind": "exponential", "mean": 0.4},
                        "cost_per_case": 2.0,
                        "routes": [
                            {"when": None, "branches": [{"to": "done", "probability": 1.0}]}
                        ],
                    },
                    "automated": {
                        "resource": "bot",
                        "service": {"kind": "deterministic", "mean": 0.01},
                        "cost_per_case": 0.1,
                        "routes": [
                            {"when": None, "branches": [{"to": "done", "probability": 1.0}]}
                        ],
                    },
                },
            },
        ],
        "controls": [
            {
                "id": "high-value-approval",
                "step": "approve",
                "description": "Approval >= 1000.",
                "applies_to": ["claim"],
                "when": {"op": ">=", "threshold": 1000.0},
            }
        ],
        "assumptions": [],
    }
    data.update(overrides)
    return data
