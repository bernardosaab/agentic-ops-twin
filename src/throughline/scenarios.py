"""Bounded, typed scenario levers.

A ``DecisionSpace`` lists the only changes a scenario (or a model-proposed scenario) may make.
There is deliberately no lever type that can edit routes, controls, costs or arrival rates; and
``apply_changes`` re-validates the resulting model, including every mandatory-control path, so a
change that would bypass or automate a control is rejected even if a lever was misconfigured.
"""

from __future__ import annotations

import itertools
from typing import Annotated, Literal

from pydantic import Field

from throughline.core.model import Frozen, OperatingModel
from throughline.core.validate import Issue, ValidationReport, validate


class CapacityLever(Frozen):
    kind: Literal["capacity"] = "capacity"
    resource: str
    min: int = Field(ge=0)
    max: int = Field(ge=0)
    step: int = Field(default=1, ge=1)

    @property
    def key(self) -> str:
        return f"capacity:{self.resource}"

    def options(self) -> list[int]:
        return list(range(self.min, self.max + 1, self.step))


class VariantLever(Frozen):
    kind: Literal["variant"] = "variant"
    step: str
    allowed: tuple[str, ...] = Field(min_length=1)

    @property
    def key(self) -> str:
        return f"variant:{self.step}"

    def options(self) -> list[str]:
        return list(self.allowed)


class PriorityLever(Frozen):
    kind: Literal["priority"] = "priority"
    allowed: tuple[Literal["fifo", "high_value_first"], ...] = Field(min_length=1)

    @property
    def key(self) -> str:
        return "priority:queue_policy"

    def options(self) -> list[str]:
        return list(self.allowed)


Lever = Annotated[CapacityLever | VariantLever | PriorityLever, Field(discriminator="kind")]


class DecisionSpace(Frozen):
    levers: tuple[Lever, ...] = Field(min_length=1)
    max_staffed_cost_per_hour: float = Field(gt=0)
    max_alternatives: int = Field(ge=1, description="Enumeration cap; exceeding it is an error.")

    def lever(self, key: str) -> Lever | None:
        return next((lv for lv in self.levers if lv.key == key), None)


class Change(Frozen):
    lever: str = Field(description="Lever key, e.g. 'capacity:adjuster' or 'variant:triage'.")
    value: int | str


class ChangeSet(Frozen):
    name: str
    changes: tuple[Change, ...]

    def label(self) -> str:
        if not self.changes:
            return "baseline"
        return ", ".join(f"{c.lever}={c.value}" for c in self.changes)


class ChangeRejected(ValueError):
    def __init__(self, issues: list[Issue]) -> None:
        self.issues = issues
        super().__init__("; ".join(f"[{i.code}] {i.path}: {i.message}" for i in issues))


def _issue(code: str, path: str, msg: str) -> Issue:
    return Issue(severity="error", code=code, path=path, message=msg)


def check_changes(model: OperatingModel, space: DecisionSpace, cs: ChangeSet) -> list[Issue]:
    issues: list[Issue] = []
    seen: set[str] = set()
    control_steps = {c.step for c in model.controls}
    for ch in cs.changes:
        path = f"changes.{ch.lever}"
        if ch.lever in seen:
            issues.append(_issue("duplicate_change", path, "lever changed twice"))
        seen.add(ch.lever)
        lever = space.lever(ch.lever)
        if lever is None:
            issues.append(
                _issue("unknown_lever", path, "not a permitted lever in this decision space")
            )
            continue
        if isinstance(lever, CapacityLever):
            if not isinstance(ch.value, int) or isinstance(ch.value, bool):
                issues.append(_issue("bad_value", path, "capacity must be an integer"))
            elif ch.value not in lever.options():
                issues.append(
                    _issue(
                        "out_of_bounds",
                        path,
                        f"{ch.value} outside permitted {lever.min}..{lever.max} "
                        f"(step {lever.step})",
                    )
                )
        elif isinstance(lever, VariantLever):
            if lever.step in control_steps:
                issues.append(
                    _issue(
                        "control_locked",
                        path,
                        f"step '{lever.step}' is a mandatory control and cannot be changed",
                    )
                )
            elif ch.value not in lever.allowed:
                issues.append(
                    _issue(
                        "out_of_bounds", path, f"variant '{ch.value}' not in {list(lever.allowed)}"
                    )
                )
        elif ch.value not in lever.allowed:
            issues.append(_issue("out_of_bounds", path, f"'{ch.value}' not permitted"))
    return issues


def apply_changes(
    model: OperatingModel, space: DecisionSpace, cs: ChangeSet
) -> tuple[OperatingModel, ValidationReport]:
    issues = check_changes(model, space, cs)
    if issues:
        raise ChangeRejected(issues)
    data = model.model_dump(mode="json")
    for ch in cs.changes:
        kind, _, target = ch.lever.partition(":")
        if kind == "capacity":
            for r in data["resources"]:
                if r["name"] == target:
                    r["capacity"] = ch.value
        elif kind == "variant":
            for s in data["steps"]:
                if s["id"] == target:
                    s["active_variant"] = ch.value
        else:
            data["queue_policy"] = ch.value
    try:
        changed = OperatingModel.model_validate(data)
    except ValueError as exc:  # defensive: lever targets something malformed
        raise ChangeRejected([_issue("invalid_result", "model", str(exc))]) from exc
    report = validate(changed)
    if not report.ok:
        raise ChangeRejected(report.errors)
    staffed = changed.staffed_cost_per_hour()
    if staffed > space.max_staffed_cost_per_hour + 1e-9:
        raise ChangeRejected(
            [
                _issue(
                    "over_budget",
                    "resources",
                    f"staffed cost {staffed:.2f}/h exceeds budget "
                    f"{space.max_staffed_cost_per_hour:.2f}/h",
                )
            ]
        )
    return changed, report


Feasible = list[tuple[ChangeSet, OperatingModel]]
Rejected = list[tuple[ChangeSet, str]]


def effective_signature(model: OperatingModel) -> tuple[object, ...]:
    """Configuration identity ignoring capacities of resources no active step uses."""
    active = model.active_resources()
    caps = tuple(sorted((r.name, r.capacity) for r in model.resources if r.name in active))
    variants = tuple(sorted((s.id, s.active_variant) for s in model.steps))
    return caps, variants, model.queue_policy


def enumerate_alternatives(
    model: OperatingModel, space: DecisionSpace
) -> tuple[Feasible, Rejected, Rejected]:
    """All permitted lever combinations.

    Returns (feasible, rejected-with-reason, equivalent-duplicates). Combinations that differ only
    in the capacity of a resource no active step uses (e.g. manual triage staff when triage is
    automated) are behaviourally identical and kept once.
    """
    current: dict[str, int | str] = {}
    for lv in space.levers:
        if isinstance(lv, CapacityLever):
            current[lv.key] = model.resource(lv.resource).capacity
        elif isinstance(lv, VariantLever):
            current[lv.key] = model.step(lv.step).active_variant
        else:
            current[lv.key] = model.queue_policy
    grids = [lv.options() for lv in space.levers]
    total = 1
    for g in grids:
        total *= len(g)
    if total > space.max_alternatives:
        raise ValueError(
            f"decision space has {total} combinations, above the cap of "
            f"{space.max_alternatives}; narrow the levers instead of sampling"
        )
    feasible: Feasible = []
    rejected: Rejected = []
    equivalent: Rejected = []
    seen: dict[tuple[object, ...], str] = {}
    combos = list(itertools.product(*grids))
    baseline_combo = tuple(current[lv.key] for lv in space.levers)
    # Evaluate the baseline first, then fewer changes first, so each set of equivalent
    # configurations is represented by its smallest change set (stable sort keeps grid order).
    combos.sort(key=lambda c: sum(v != b for v, b in zip(c, baseline_combo, strict=True)))
    for combo in combos:
        changes = tuple(
            Change(lever=lv.key, value=v)
            for lv, v in zip(space.levers, combo, strict=True)
            if v != current[lv.key]
        )
        name = "baseline" if not changes else "alt-" + "-".join(str(v) for v in combo)
        cs = ChangeSet(name=name, changes=changes)
        try:
            changed, _ = apply_changes(model, space, cs)
        except ChangeRejected as exc:
            rejected.append((cs, str(exc)))
            continue
        sig = effective_signature(changed)
        if sig in seen:
            equivalent.append((cs, f"equivalent to {seen[sig]}"))
            continue
        seen[sig] = cs.name
        feasible.append((cs, changed))
    return feasible, rejected, equivalent
