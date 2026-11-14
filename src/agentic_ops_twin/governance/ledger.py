"""Decision provenance graph: an append-only, hash-chained, bi-temporal record store (SQLite).

Every record has:

* a **kind** (request, proposal, experiment, brief, review, change_package, approval, release,
  refusal, invalidation, ...) and a JSON payload with its SHA-256 digest;
* **typed edges** to earlier records (``derived_from``, ``evaluates``, ``approves``,
  ``releases``, ``refuses``, ``invalidates``, ...), so the chain from question to outcome can be
  walked later;
* two times: **transaction time** (when it was recorded) and **valid time** (when the fact it
  states takes effect). Facts are never deleted or edited; they are *invalidated* by a later
  record, and ``as_of`` answers "what did we know, and what was in force, at time T?";
* the previous record's hash, so edits or deletions are detectable by ``verify``.

``reconstruction_pack`` exports a record's full lineage, its invalidations and the verification
result as one self-contained bundle for an auditor or a new owner.

This is tamper-*evident* bookkeeping for a local prototype, not a security control: anyone with
file access can rewrite the whole chain. There is no authentication.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import deque
from contextlib import closing
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

GENESIS = "0" * 64
SCHEMA_VERSION = 2

_SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    created_at TEXT NOT NULL,
    valid_from TEXT NOT NULL,
    edges TEXT NOT NULL,
    payload TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    record_hash TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS no_update BEFORE UPDATE ON records
BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;
CREATE TRIGGER IF NOT EXISTS no_delete BEFORE DELETE ON records
BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;
"""

Edge = tuple[str, str]  # (relation, target record_id)


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


@dataclass(frozen=True)
class Record:
    seq: int
    record_id: str
    kind: str
    created_at: str
    valid_from: str
    edges: list[Edge]
    payload: dict[str, Any]
    payload_sha256: str
    prev_hash: str
    record_hash: str

    @property
    def refs(self) -> list[str]:
        return [target for _, target in self.edges]

    def summary(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "kind": self.kind,
            "recorded_at": self.created_at,
            "valid_from": self.valid_from,
            "edges": [list(e) for e in self.edges],
            "payload_sha256": self.payload_sha256,
            "record_hash": self.record_hash,
        }


@dataclass
class ReconstructionPack:
    target: str
    generated_at: str
    chain_verified: bool
    chain_problems: list[str]
    records: list[dict[str, Any]] = field(default_factory=list)
    invalidations: list[dict[str, Any]] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "reconstruction-pack-v1",
            "target": self.target,
            "generated_at": self.generated_at,
            "chain_verified": self.chain_verified,
            "chain_problems": self.chain_problems,
            "records": self.records,
            "invalidations": self.invalidations,
        }

    def timeline_markdown(self) -> str:
        lines = [
            f"# Reconstruction pack for `{self.target}`",
            "",
            f"Generated {self.generated_at}. Hash chain "
            f"{'verified' if self.chain_verified else 'FAILED VERIFICATION'}.",
            "",
            "| Recorded at | Valid from | Record | Kind | Edges |",
            "|---|---|---|---|---|",
        ]
        for r in self.records:
            edges = ", ".join(f"{rel} → `{t}`" for rel, t in r["edges"]) or "—"
            lines.append(
                f"| {r['recorded_at']} | {r['valid_from']} | `{r['record_id']}` | {r['kind']} "
                f"| {edges} |"
            )
        if self.invalidations:
            lines += ["", "## Invalidations", ""]
            lines += [
                f"- `{i['record_id']}` invalidates `{i['target']}` from {i['valid_from']}: "
                f"{i['reason']}"
                for i in self.invalidations
            ]
        return "\n".join(lines) + "\n"


class Ledger:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def _last_hash(self) -> str:
        row = self._conn.execute(
            "SELECT record_hash FROM records ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        return GENESIS if row is None else str(row[0])

    @staticmethod
    def _hash(kind: str, ts: str, valid: str, edges: list[Edge], p_hash: str, prev: str) -> str:
        return sha256(canonical([SCHEMA_VERSION, kind, ts, valid, edges, p_hash, prev]))

    def append(
        self,
        kind: str,
        payload: dict[str, Any],
        refs: list[str] | None = None,
        created_at: str | None = None,
        *,
        edges: list[Edge] | None = None,
        valid_from: str | None = None,
    ) -> Record:
        """Append a record. ``refs`` are shorthand for ``derived_from`` edges."""
        all_edges: list[Edge] = [("derived_from", r) for r in (refs or [])]
        all_edges += [(rel, target) for rel, target in (edges or [])]
        for _, target in all_edges:
            if self.get(target) is None:
                raise KeyError(f"referenced record '{target}' does not exist")
        body = canonical(payload)
        p_hash = sha256(body)
        prev = self._last_hash()
        ts = created_at or now()
        valid = valid_from or ts
        rec_hash = self._hash(kind, ts, valid, all_edges, p_hash, prev)
        record_id = f"{kind}-{rec_hash[:12]}"
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO records (record_id, kind, created_at, valid_from, edges, payload,"
                " payload_sha256, prev_hash, record_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (record_id, kind, ts, valid, canonical(all_edges), body, p_hash, prev, rec_hash),
            )
        return Record(
            int(cur.lastrowid or 0),
            record_id,
            kind,
            ts,
            valid,
            all_edges,
            payload,
            p_hash,
            prev,
            rec_hash,
        )

    _COLS = (
        "seq, record_id, kind, created_at, valid_from, edges, payload, payload_sha256, "
        "prev_hash, record_hash"
    )

    def _row(self, row: tuple[Any, ...]) -> Record:
        return Record(
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            [(str(a), str(b)) for a, b in json.loads(row[5])],
            json.loads(row[6]),
            row[7],
            row[8],
            row[9],
        )

    def get(self, record_id: str) -> Record | None:
        row = self._conn.execute(
            f"SELECT {self._COLS} FROM records WHERE record_id = ?", (record_id,)
        ).fetchone()
        return None if row is None else self._row(row)

    def records(self, kind: str | None = None) -> list[Record]:
        q = f"SELECT {self._COLS} FROM records"
        args: tuple[Any, ...] = ()
        if kind is not None:
            q += " WHERE kind = ?"
            args = (kind,)
        with closing(self._conn.execute(q + " ORDER BY seq", args)) as cur:
            return [self._row(r) for r in cur.fetchall()]

    # --- bi-temporal queries ------------------------------------------------------------------

    def invalidate(self, record_id: str, reason: str, *, effective_at: str | None = None) -> Record:
        """Record that a fact stops holding from ``effective_at``; the original is kept."""
        if self.get(record_id) is None:
            raise KeyError(f"record '{record_id}' does not exist")
        return self.append(
            "invalidation",
            {"target": record_id, "reason": reason},
            edges=[("invalidates", record_id)],
            valid_from=effective_at,
        )

    def invalidations(self, record_id: str) -> list[Record]:
        return [r for r in self.records("invalidation") if ("invalidates", record_id) in r.edges]

    def is_valid(
        self, record_id: str, *, as_of_recorded: str | None = None, as_of_valid: str | None = None
    ) -> bool:
        """True if the record existed and was not invalidated, as known/in force at the times."""
        rec = self.get(record_id)
        if rec is None:
            return False
        tx = as_of_recorded or now()
        vt = as_of_valid or tx
        if rec.created_at > tx or rec.valid_from > vt:
            return False
        return not any(
            inv.created_at <= tx and inv.valid_from <= vt for inv in self.invalidations(record_id)
        )

    def as_of(
        self, *, recorded: str, valid: str | None = None, kind: str | None = None
    ) -> list[Record]:
        """Records that were known by ``recorded`` and in force (not invalidated) at ``valid``."""
        return [
            r
            for r in self.records(kind)
            if r.kind != "invalidation"
            and self.is_valid(r.record_id, as_of_recorded=recorded, as_of_valid=valid)
        ]

    def lineage(self, record_id: str) -> list[Record]:
        """The record and every ancestor reachable through its edges, oldest first."""
        seen: dict[str, Record] = {}
        queue: deque[str] = deque([record_id])
        while queue:
            rid = queue.popleft()
            if rid in seen:
                continue
            rec = self.get(rid)
            if rec is None:
                raise KeyError(f"record '{rid}' does not exist")
            seen[rid] = rec
            queue.extend(rec.refs)
        return sorted(seen.values(), key=lambda r: r.seq)

    def descendants(self, record_id: str, relation: str | None = None) -> list[Record]:
        return [
            r
            for r in self.records()
            if any(t == record_id and (relation is None or rel == relation) for rel, t in r.edges)
        ]

    def reconstruction_pack(self, record_id: str) -> ReconstructionPack:
        chain = self.lineage(record_id)
        ok, problems = self.verify()
        invs = []
        for rec in chain:
            for inv in self.invalidations(rec.record_id):
                invs.append(
                    {
                        "record_id": inv.record_id,
                        "target": rec.record_id,
                        "valid_from": inv.valid_from,
                        "recorded_at": inv.created_at,
                        "reason": inv.payload.get("reason", ""),
                    }
                )
        return ReconstructionPack(
            target=record_id,
            generated_at=now(),
            chain_verified=ok,
            chain_problems=problems,
            records=[{**r.summary(), "payload": r.payload} for r in chain],
            invalidations=invs,
        )

    def verify(self) -> tuple[bool, list[str]]:
        problems: list[str] = []
        prev = GENESIS
        for r in self.records():
            if sha256(canonical(r.payload)) != r.payload_sha256:
                problems.append(f"{r.record_id}: payload digest mismatch")
            if r.prev_hash != prev:
                problems.append(f"{r.record_id}: broken chain (prev hash mismatch)")
            expect = self._hash(
                r.kind, r.created_at, r.valid_from, r.edges, r.payload_sha256, r.prev_hash
            )
            if expect != r.record_hash:
                problems.append(f"{r.record_id}: record hash mismatch")
            prev = r.record_hash
        return not problems, problems
