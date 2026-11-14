"""Staged write-gate in front of a *sandboxed* system of record.

The prototype never touches a live system. To demonstrate governed write-back end to end, it
keeps a local JSON "system of record" holding each pack's lever-addressable configuration
(capacities, step variants, queue policy). A change reaches it only through this gate:

1. **Escrow.** A brief's change set becomes a ``ChangePackage``. The package carries a
   field-level quote (before and after), the model digest, the trust status and a risk tier. It
   is recorded in the provenance graph with a payload hash.
2. **Approval.** Named approvers sign the exact payload hash with an HMAC token (keys come from a
   local keyring; see the limitations below). High-risk packages need two distinct approvers.
   A maker can never approve their own package. Approvers must acknowledge an unvalidated twin.
3. **Release.** Deterministic sensors re-check everything:
   - the package is still valid;
   - the payload hash and the brief are current;
   - the model digest has not drifted;
   - the trust gate passes;
   - the system of record still equals the quoted "before" state;
   - the tokens are valid, unexpired, distinct, not the maker's, and sufficient for the tier.

   If all pass, the change is written and **read back**. Any failure appends a ``refusal``
   record with its reasons and leaves the system of record unchanged (fail-closed).

Limitations: reviewer keys are local secrets created by the operator, so identities are
illustrative, not authenticated. This is a demonstration of the control pattern, not a security
product.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from agentic_ops_twin.decision.scenarios import ChangeSet, apply_changes
from agentic_ops_twin.governance.ledger import Ledger, Record, canonical, sha256
from agentic_ops_twin.packs.base import DomainPack
from agentic_ops_twin.simulation.model import Frozen, OperatingModel

RiskTier = Literal["standard", "high"]
TOKEN_TTL = timedelta(hours=24)


class WritePolicy(Frozen):
    """Trusted release policy (not changeable by any proposal)."""

    high_risk_cost_change_fraction: float = Field(default=0.10, ge=0)
    approvals_standard: int = Field(default=1, ge=1)
    approvals_high: int = Field(default=2, ge=2)


DEFAULT_POLICY = WritePolicy()


def configuration(model: OperatingModel) -> dict[str, Any]:
    """Lever-addressable configuration, as stored in the system of record."""
    return {
        "capacities": {r.name: r.capacity for r in model.resources},
        "variants": {s.id: s.active_variant for s in model.steps},
        "queue_policy": model.queue_policy,
    }


def _diff(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for section in ("capacities", "variants"):
        for key in sorted(set(before[section]) | set(after[section])):
            b, a = before[section].get(key), after[section].get(key)
            if a != b:
                out.append({"field": f"{section}.{key}", "before": b, "after": a})
    if before["queue_policy"] != after["queue_policy"]:
        out.append(
            {
                "field": "queue_policy",
                "before": before["queue_policy"],
                "after": after["queue_policy"],
            }
        )
    return out


class SystemOfRecord:
    """Local JSON stand-in for an operational system (one document per pack)."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        data: dict[str, Any] = json.loads(self.path.read_text(encoding="utf-8"))
        return data

    def read(self, pack: DomainPack) -> dict[str, Any]:
        data = self._load()
        if pack.id not in data:
            data[pack.id] = configuration(pack.model)
            self._save(data)
        cfg: dict[str, Any] = data[pack.id]
        return cfg

    def write(self, pack_id: str, cfg: dict[str, Any]) -> None:
        data = self._load()
        data[pack_id] = cfg
        self._save(data)

    def _save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")


class Keyring:
    """Local reviewer secrets for HMAC approval tokens (illustrative identity only)."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def _load(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        data: dict[str, str] = json.loads(self.path.read_text(encoding="utf-8"))
        return data

    def add(self, reviewer: str) -> None:
        keys = self._load()
        if reviewer in keys:
            raise ValueError(f"reviewer '{reviewer}' already has a key")
        keys[reviewer] = secrets.token_hex(32)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(keys, indent=1), encoding="utf-8")

    def secret(self, reviewer: str) -> str | None:
        return self._load().get(reviewer)


def token_message(payload_sha256: str, reviewer: str, decision: str, expires_at: str) -> bytes:
    return f"{payload_sha256}|{reviewer}|{decision}|{expires_at}".encode()


def sign(secret: str, message: bytes) -> str:
    return hmac.new(bytes.fromhex(secret), message, hashlib.sha256).hexdigest()


class ChangePackage(Frozen):
    pack_id: str
    target: str = "sandbox-system-of-record"
    change_set: ChangeSet
    before: dict[str, Any]
    after: dict[str, Any]
    field_diff: tuple[dict[str, Any], ...]
    model_id: str
    model_digest: str
    brief_record: str
    trust_record: str
    trust_status: str
    risk_tier: RiskTier
    risk_reasons: tuple[str, ...]
    required_approvals: int
    maker: str
    staffed_cost_before: float
    staffed_cost_after: float

    def payload_sha256(self) -> str:
        return sha256(canonical(self.model_dump(mode="json")))


def risk_tier(
    pack: DomainPack,
    before_model: OperatingModel,
    after_model: OperatingModel,
    trust: str,
    policy: WritePolicy,
) -> tuple[RiskTier, list[str]]:
    reasons = []
    b = {r.name: r.capacity for r in before_model.resources}
    for r in after_model.resources:
        if r.capacity < b[r.name] and r.name in after_model.active_resources():
            reasons.append(f"reduces {r.name} capacity {b[r.name]} → {r.capacity}")
    kinds = {r.name: r.kind for r in after_model.resources}
    for s in after_model.steps:
        old = before_model.step(s.id)
        if s.active_variant != old.active_variant and kinds[s.active.resource] == "automation":
            reasons.append(f"switches '{s.id}' to automation")
    cb, ca = before_model.staffed_cost_per_hour(), after_model.staffed_cost_per_hour()
    if cb > 0 and abs(ca - cb) / cb > policy.high_risk_cost_change_fraction:
        reasons.append(f"staffed cost changes by {100 * (ca - cb) / cb:+.1f}%")
    if trust == "unvalidated":
        reasons.append("twin is unvalidated against observed history")
    return ("high" if reasons else "standard"), reasons


def stage(
    ledger: Ledger,
    sor: SystemOfRecord,
    pack: DomainPack,
    *,
    brief_record: str,
    trust_record: str,
    maker: str,
    policy: WritePolicy = DEFAULT_POLICY,
) -> Record:
    """Create an escrowed change package from a brief (nothing is written yet)."""
    brief = ledger.get(brief_record)
    if brief is None or brief.kind != "brief":
        raise ValueError(f"'{brief_record}' is not a brief record")
    raw_cs = brief.payload["brief"].get("change_set")
    if raw_cs is None:
        raise ValueError("brief has no change set to stage")
    trust = ledger.get(trust_record)
    if trust is None or trust.kind != "trust_assessment":
        raise ValueError(f"'{trust_record}' is not a trust assessment")
    cs = ChangeSet.model_validate(raw_cs)
    current = sor.read(pack)
    base_model = apply_configuration(pack, current)
    after_model, _ = apply_changes(base_model, pack.decision_space, cs)
    status = str(trust.payload["status"])
    tier, reasons = risk_tier(pack, base_model, after_model, status, policy)
    pkg = ChangePackage(
        pack_id=pack.id,
        change_set=cs,
        before=current,
        after=configuration(after_model),
        field_diff=tuple(_diff(current, configuration(after_model))),
        model_id=pack.model.id,
        model_digest=pack.model.digest(),
        brief_record=brief_record,
        trust_record=trust_record,
        trust_status=status,
        risk_tier=tier,
        risk_reasons=tuple(reasons),
        required_approvals=policy.approvals_high if tier == "high" else policy.approvals_standard,
        maker=maker,
        staffed_cost_before=base_model.staffed_cost_per_hour(),
        staffed_cost_after=after_model.staffed_cost_per_hour(),
    )
    return ledger.append(
        "change_package",
        {
            "package": pkg.model_dump(mode="json"),
            "payload_sha256": pkg.payload_sha256(),
            "status": "escrowed",
        },
        edges=[("derived_from", brief_record), ("assessed_by", trust_record)],
    )


def apply_configuration(pack: DomainPack, cfg: dict[str, Any]) -> OperatingModel:
    data = pack.model.model_dump(mode="json")
    for r in data["resources"]:
        r["capacity"] = cfg["capacities"][r["name"]]
    for s in data["steps"]:
        s["active_variant"] = cfg["variants"][s["id"]]
    data["queue_policy"] = cfg["queue_policy"]
    return OperatingModel.model_validate(data)


def approve(
    ledger: Ledger,
    keyring: Keyring,
    *,
    package_record: str,
    reviewer: str,
    decision: Literal["approve", "reject"] = "approve",
    acknowledge_unvalidated: bool = False,
    note: str = "",
    issued_at: datetime | None = None,
) -> Record:
    pkg_rec = ledger.get(package_record)
    if pkg_rec is None or pkg_rec.kind != "change_package":
        raise ValueError(f"'{package_record}' is not a change package")
    secret = keyring.secret(reviewer)
    if secret is None:
        raise ValueError(f"no key for reviewer '{reviewer}'; add one with `ops-twin reviewer add`")
    payload_hash = str(pkg_rec.payload["payload_sha256"])
    expires = ((issued_at or datetime.now(UTC)) + TOKEN_TTL).isoformat(timespec="seconds")
    token = sign(secret, token_message(payload_hash, reviewer, decision, expires))
    return ledger.append(
        "approval",
        {
            "package": package_record,
            "payload_sha256": payload_hash,
            "reviewer": reviewer,
            "decision": decision,
            "expires_at": expires,
            "token": token,
            "acknowledged_unvalidated": acknowledge_unvalidated,
            "note": note,
            "identity": "local HMAC key (illustrative, not authenticated)",
        },
        edges=[("approves" if decision == "approve" else "rejects", package_record)],
    )


def _sensor_checks(
    ledger: Ledger,
    sor: SystemOfRecord,
    keyring: Keyring,
    pack: DomainPack,
    pkg_rec: Record,
    requester: str,
    at: datetime,
) -> tuple[list[str], ChangePackage | None]:
    problems: list[str] = []
    try:
        pkg = ChangePackage.model_validate(pkg_rec.payload["package"])
    except Exception as exc:  # malformed escrow payload
        return [f"package payload is malformed: {exc}"], None
    if pkg.payload_sha256() != pkg_rec.payload["payload_sha256"]:
        problems.append("package payload hash does not match its recorded hash")
    if not ledger.is_valid(pkg_rec.record_id):
        problems.append("package has been invalidated")
    if any(r.kind == "release" for r in ledger.descendants(pkg_rec.record_id, "releases")):
        problems.append("package was already released")
    if not ledger.is_valid(pkg.brief_record):
        problems.append("source brief has been invalidated")
    if pkg.model_digest != pack.model.digest():
        problems.append("model digest changed since the package was staged")
    trust = ledger.get(pkg.trust_record)
    if trust is None or not ledger.is_valid(pkg.trust_record):
        problems.append("trust assessment missing or invalidated")
    elif trust.payload["status"] == "inadequate":
        problems.append(f"trust gate: twin is inadequate ({trust.payload['effect']})")
    if sor.read(pack) != pkg.before:
        problems.append("system of record changed since the quote (stale before-state)")
    approvals = [r for r in ledger.descendants(pkg_rec.record_id) if r.kind == "approval"]
    valid_approvers: set[str] = set()
    for a in approvals:
        p = a.payload
        if p["decision"] == "reject":
            problems.append(f"rejected by {p['reviewer']}")
            continue
        secret = keyring.secret(p["reviewer"])
        msg = token_message(p["payload_sha256"], p["reviewer"], p["decision"], p["expires_at"])
        if secret is None or not hmac.compare_digest(sign(secret, msg), p["token"]):
            problems.append(f"approval by {p['reviewer']}: token does not verify")
        elif p["payload_sha256"] != pkg_rec.payload["payload_sha256"]:
            problems.append(f"approval by {p['reviewer']}: signed a different payload")
        elif datetime.fromisoformat(p["expires_at"]) < at:
            problems.append(f"approval by {p['reviewer']}: token expired")
        elif p["reviewer"] in (pkg.maker, requester):
            problems.append(f"approval by {p['reviewer']}: maker/requester cannot approve")
        elif pkg.trust_status == "unvalidated" and not p["acknowledged_unvalidated"]:
            problems.append(f"approval by {p['reviewer']}: did not acknowledge unvalidated twin")
        else:
            valid_approvers.add(p["reviewer"])
    if len(valid_approvers) < pkg.required_approvals:
        problems.append(
            f"{len(valid_approvers)} valid distinct approval(s); {pkg.required_approvals} required "
            f"for a {pkg.risk_tier}-risk package"
        )
    return problems, pkg


def release(
    ledger: Ledger,
    sor: SystemOfRecord,
    keyring: Keyring,
    pack: DomainPack,
    *,
    package_record: str,
    requester: str,
    at: datetime | None = None,
) -> Record:
    """Release an escrowed package, or record a refusal. Never partially writes."""
    pkg_rec = ledger.get(package_record)
    if pkg_rec is None or pkg_rec.kind != "change_package":
        raise ValueError(f"'{package_record}' is not a change package")
    moment = at or datetime.now(UTC)
    problems, pkg = _sensor_checks(ledger, sor, keyring, pack, pkg_rec, requester, moment)
    if problems or pkg is None:
        return ledger.append(
            "refusal",
            {
                "package": package_record,
                "requester": requester,
                "reasons": problems,
                "system_of_record_changed": False,
            },
            edges=[("refuses", package_record)],
        )
    sor.write(pack.id, pkg.after)
    read_back = sor.read(pack)
    if read_back != pkg.after:
        sor.write(pack.id, pkg.before)
        return ledger.append(
            "refusal",
            {
                "package": package_record,
                "requester": requester,
                "reasons": ["read-back did not match the approved after-state; reverted"],
                "system_of_record_changed": False,
            },
            edges=[("refuses", package_record)],
        )
    approvals = [r.record_id for r in ledger.descendants(package_record) if r.kind == "approval"]
    return ledger.append(
        "release",
        {
            "package": package_record,
            "requester": requester,
            "written": list(pkg.field_diff),
            "read_back_matches": True,
            "target": pkg.target,
            "note": "sandboxed system of record only; no live system is connected",
        },
        edges=[("releases", package_record), *[("authorised_by", a) for a in approvals]],
    )
