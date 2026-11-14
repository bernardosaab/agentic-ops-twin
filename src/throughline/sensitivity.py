"""One-at-a-time sensitivity within stated ranges.

Sensitivity varies parameters the model already contains; it cannot reveal mechanisms the model
omits (see the hidden-truth study for that).
"""

from __future__ import annotations

from throughline.core.exogenous import DemandCondition
from throughline.core.model import OperatingModel
from throughline.packs.base import SensitivityParam


def perturb(
    model: OperatingModel, demand: DemandCondition, param: SensitivityParam, value: float
) -> tuple[OperatingModel, DemandCondition]:
    """Return a model/demand with ``param`` set to ``value``.

    * arrival: multiply demand by ``value``.
    * service_scale: scale every service distribution performed by resource ``target``.
    * branch_probability: set every branch tagged ``param=target`` to ``value`` and rescale the
      other branches of the same rule proportionally so probabilities still sum to one.
    """
    if param.kind == "arrival":
        return model, demand.model_copy(
            update={
                "name": f"{demand.name}*{param.name}={value:g}",
                "arrival_multiplier": demand.arrival_multiplier * value,
            }
        )
    data = model.model_dump(mode="json")
    touched = False
    for s in data["steps"]:
        for v in s["variants"].values():
            if param.kind == "service_scale" and v["resource"] == param.target:
                svc = v["service"]
                svc["mean"] *= value
                if svc.get("low") is not None:
                    svc["low"] *= value
                    svc["high"] *= value
                touched = True
            if param.kind == "branch_probability":
                for rule in v["routes"]:
                    tagged = [b for b in rule["branches"] if b.get("param") == param.target]
                    if not tagged:
                        continue
                    if not 0 < value < 1:
                        raise ValueError("branch probability must be in (0, 1)")
                    others = [b for b in rule["branches"] if b.get("param") != param.target]
                    old_tagged = sum(b["probability"] for b in tagged)
                    old_rest = 1 - old_tagged
                    for b in tagged:
                        b["probability"] = value * b["probability"] / old_tagged
                    for b in others:
                        b["probability"] = (1 - value) * b["probability"] / old_rest
                    # absorb floating error in the last branch
                    drift = 1 - sum(b["probability"] for b in rule["branches"])
                    rule["branches"][-1]["probability"] += drift
                    touched = True
    if not touched:
        raise ValueError(f"sensitivity parameter '{param.name}' matched nothing in the model")
    data["version"] = f"{model.version}+{param.name}={value:g}"
    return OperatingModel.model_validate(data), demand
