"""Assumption critic for operating models.

Structural checks reject models that cannot be simulated faithfully; they never repair or fill in
missing values. The control-path check proves, for each mandatory control, that no routing path
for an applicable case reaches ``done`` without visiting the control step.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, ConfigDict

from agentic_ops_twin.simulation.model import DONE, Condition, OperatingModel, RouteRule


class Issue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    severity: Literal["error", "warning"]
    code: str
    path: str
    message: str


class ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    model_id: str
    model_digest: str
    issues: tuple[Issue, ...]

    @property
    def ok(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "warning"]


class ModelValidationError(ValueError):
    def __init__(self, report: ValidationReport) -> None:
        self.report = report
        lines = "; ".join(f"[{i.code}] {i.path}: {i.message}" for i in report.errors)
        super().__init__(f"operating model '{report.model_id}' is invalid: {lines}")


def _dupes(names: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    dup: set[str] = set()
    for n in names:
        (dup if n in seen else seen).add(n)
    return dup


def _matching_rule(rules: tuple[RouteRule, ...], value: float) -> RouteRule | None:
    for rule in rules:
        if rule.when is None or rule.when.holds(value):
            return rule
    return None


def all_conditions(model: OperatingModel) -> list[Condition]:
    conds: list[Condition] = []
    for s in model.steps:
        for v in s.variants.values():
            conds.extend(r.when for r in v.routes if r.when is not None)
    conds.extend(c.when for c in model.controls if c.when is not None)
    return conds


def representative_values(model: OperatingModel) -> list[float]:
    """Values covering every region in which all routing/control conditions are constant."""
    ts = sorted({c.threshold for c in all_conditions(model)})
    reps = {0.0}
    for i, t in enumerate(ts):
        reps.add(t)
        reps.add((t + ts[i + 1]) / 2 if i + 1 < len(ts) else t + 1.0)
        if i == 0 and t > 0:
            reps.add(t / 2)
    return sorted(reps)


def _edges(model: OperatingModel, value: float) -> dict[str, set[str]]:
    """Possible transitions (p > 0 or fallback) for a case with ``value``, active variants only."""
    graph: dict[str, set[str]] = {}
    for s in model.steps:
        rule = _matching_rule(s.active.routes, value)
        targets: set[str] = set()
        if rule is not None:
            targets |= {b.to for b in rule.branches if b.probability > 0}
            if rule.fallback_to is not None:
                targets.add(rule.fallback_to)
        graph[s.id] = targets
    return graph


def _path_avoiding(graph: dict[str, set[str]], start: str, avoid: str) -> list[str] | None:
    """Return a path start -> DONE that never visits ``avoid`` (BFS), or None."""
    if start == avoid:
        return None
    prev: dict[str, str | None] = {start: None}
    frontier = [start]
    while frontier:
        nxt: list[str] = []
        for node in frontier:
            for t in sorted(graph.get(node, set())):
                if t == avoid or t in prev:
                    continue
                prev[t] = node
                if t == DONE:
                    path = [DONE]
                    cur: str | None = node
                    while cur is not None:
                        path.append(cur)
                        cur = prev[cur]
                    return list(reversed(path))
                nxt.append(t)
        frontier = nxt
    return None


def _reachable(graph: dict[str, set[str]], start: str) -> set[str]:
    seen = {start}
    stack = [start]
    while stack:
        for t in graph.get(stack.pop(), set()):
            if t not in seen:
                seen.add(t)
                stack.append(t)
    return seen


def control_violations(model: OperatingModel) -> list[Issue]:
    issues: list[Issue] = []
    step_ids = {s.id for s in model.steps}
    entries = {c.name: c.entry_step for c in model.case_types}
    for ctl in model.controls:
        path = f"controls.{ctl.id}"
        if ctl.step not in step_ids:
            issues.append(
                Issue(
                    severity="error",
                    code="control_unknown_step",
                    path=path,
                    message=f"control step '{ctl.step}' does not exist",
                )
            )
            continue
        res_name = model.step(ctl.step).active.resource
        kinds = {r.name: r.kind for r in model.resources}
        if kinds.get(res_name) != "human":
            issues.append(
                Issue(
                    severity="error",
                    code="control_not_human",
                    path=path,
                    message=f"control step '{ctl.step}' must be performed by a human "
                    f"resource, active variant uses '{res_name}'",
                )
            )
        for ct in ctl.applies_to:
            if ct not in entries:
                issues.append(
                    Issue(
                        severity="error",
                        code="control_unknown_case_type",
                        path=path,
                        message=f"case type '{ct}' does not exist",
                    )
                )
                continue
            for value in representative_values(model):
                if ctl.when is not None and not ctl.when.holds(value):
                    continue
                bypass = _path_avoiding(_edges(model, value), entries[ct], ctl.step)
                if bypass is not None:
                    issues.append(
                        Issue(
                            severity="error",
                            code="control_bypass",
                            path=path,
                            message=f"case type '{ct}' with value {value:g} can reach done without "
                            f"'{ctl.step}': {' -> '.join(bypass)}",
                        )
                    )
                    break
    return issues


def validate(model: OperatingModel) -> ValidationReport:
    issues: list[Issue] = []

    def err(code: str, path: str, msg: str) -> None:
        issues.append(Issue(severity="error", code=code, path=path, message=msg))

    def warn(code: str, path: str, msg: str) -> None:
        issues.append(Issue(severity="warning", code=code, path=path, message=msg))

    for label, names in (
        ("resources", [r.name for r in model.resources]),
        ("steps", [s.id for s in model.steps]),
        ("case_types", [c.name for c in model.case_types]),
        ("controls", [c.id for c in model.controls]),
    ):
        for d in _dupes(names):
            err("duplicate_name", label, f"duplicate name '{d}'")

    if DONE in {s.id for s in model.steps}:
        err("reserved_name", "steps", f"'{DONE}' is reserved for case completion")
    if model.warmup_hours >= model.horizon_hours:
        err(
            "warmup_exceeds_horizon",
            "warmup_hours",
            f"warm-up {model.warmup_hours}h must be shorter than horizon {model.horizon_hours}h",
        )

    resources = {r.name for r in model.resources}
    targets = {s.id for s in model.steps} | {DONE}
    used_resources: set[str] = set()
    referenced_resources: set[str] = set()
    unlimited: dict[str, set[str]] = {s.id: set() for s in model.steps}

    for s in model.steps:
        for vname, v in s.variants.items():
            p = f"steps.{s.id}.variants.{vname}"
            if v.resource not in resources:
                err("unknown_resource", p, f"resource '{v.resource}' does not exist")
            referenced_resources.add(v.resource)
            if vname == s.active_variant:
                used_resources.add(v.resource)
            if v.routes[-1].when is not None:
                err("no_default_route", p, "last route rule must be unconditional (when: null)")
            for ri, rule in enumerate(v.routes):
                rp = f"{p}.routes[{ri}]"
                limited = any(b.max_traversals is not None for b in rule.branches)
                if limited and rule.fallback_to is None:
                    err("missing_fallback", rp, "rule with traversal limits needs 'fallback_to'")
                if rule.fallback_to is not None and rule.fallback_to not in targets:
                    err("unknown_target", rp, f"fallback '{rule.fallback_to}' does not exist")
                for b in rule.branches:
                    if b.to not in targets:
                        err("unknown_target", rp, f"branch target '{b.to}' does not exist")
                    elif b.to == s.id and b.max_traversals is None:
                        err("unbounded_loop", rp, "self-loop requires max_traversals")
                    if b.max_traversals is None and b.probability > 0 and b.to != DONE:
                        unlimited[s.id].add(b.to)
                if rule.fallback_to is not None and rule.fallback_to != DONE:
                    unlimited[s.id].add(rule.fallback_to)

    # Unbounded cycles: the graph of edges without traversal limits must be acyclic.
    state: dict[str, int] = {}

    def dfs(node: str, trail: list[str]) -> None:
        state[node] = 1
        for t in sorted(unlimited.get(node, set())):
            if state.get(t) == 1:
                cyc = [*trail[trail.index(t) :], t] if t in trail else [node, t]
                err(
                    "unbounded_loop",
                    f"steps.{node}",
                    f"cycle without traversal limit: {' -> '.join(cyc)}",
                )
            elif t not in state:
                dfs(t, [*trail, t])
        state[node] = 2

    for sid in sorted(unlimited):
        if sid not in state:
            dfs(sid, [sid])

    for ct in model.case_types:
        p = f"case_types.{ct.name}"
        if ct.entry_step not in targets - {DONE}:
            err("unknown_entry", p, f"entry step '{ct.entry_step}' does not exist")
        if ct.arrival_rate_per_hour == 0:
            warn("zero_arrivals", p, "arrival rate is zero; this case type generates no work")

    if not any(i.severity == "error" for i in issues):
        reachable_steps: set[str] = set()
        for value in representative_values(model):
            g = _edges(model, value)
            for ct in model.case_types:
                reach = _reachable(g, ct.entry_step)
                reachable_steps |= reach
                for node in sorted(reach - {DONE}):
                    if DONE not in _reachable(g, node):
                        err(
                            "cannot_complete",
                            f"steps.{node}",
                            f"case type '{ct.name}' (value {value:g}) cannot reach done "
                            f"from '{node}'",
                        )
        for s in model.steps:
            if s.id not in reachable_steps:
                warn(
                    "unreachable_step",
                    f"steps.{s.id}",
                    "no case type reaches this step under the active variants",
                )
        issues.extend(control_violations(model))
        for r in model.resources:
            if r.name not in referenced_resources:
                warn("unused_resource", f"resources.{r.name}", "no step variant uses this resource")
            elif r.name in used_resources and r.capacity == 0:
                warn(
                    "zero_capacity",
                    f"resources.{r.name}",
                    "capacity is zero: cases needing this resource can never complete",
                )

    # Deduplicate while preserving order.
    unique = tuple(dict.fromkeys(issues))
    return ValidationReport(model_id=model.id, model_digest=model.digest(), issues=unique)


def ensure_valid(model: OperatingModel) -> ValidationReport:
    report = validate(model)
    if not report.ok:
        raise ModelValidationError(report)
    return report
