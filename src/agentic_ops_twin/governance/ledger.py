"""Append-only, hash-chained evidence ledger (SQLite).

Each record stores a kind (request, proposal, critique, experiment, brief, review, ...), a JSON
payload, the payload digest and the previous record's hash, so edits or deletions are detectable
by ``verify``. This is tamper-*evident* bookkeeping for a local prototype, not a security control:
anyone with file access can rewrite the whole chain. There is no authentication.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

GENESIS = "0" * 64

_SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    created_at TEXT NOT NULL,
    refs TEXT NOT NULL,
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


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


@dataclass(frozen=True)
class Record:
    seq: int
    record_id: str
    kind: str
    created_at: str
    refs: list[str]
    payload: dict[str, Any]
    payload_sha256: str
    prev_hash: str
    record_hash: str


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

    def append(
        self,
        kind: str,
        payload: dict[str, Any],
        refs: list[str] | None = None,
        created_at: str | None = None,
    ) -> Record:
        refs = list(refs or [])
        for ref in refs:
            if self.get(ref) is None:
                raise KeyError(f"referenced record '{ref}' does not exist")
        body = canonical(payload)
        p_hash = sha256(body)
        prev = self._last_hash()
        ts = created_at or datetime.now(UTC).isoformat(timespec="seconds")
        rec_hash = sha256(canonical([kind, ts, refs, p_hash, prev]))
        record_id = f"{kind}-{rec_hash[:12]}"
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO records (record_id, kind, created_at, refs, payload, payload_sha256,"
                " prev_hash, record_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (record_id, kind, ts, canonical(refs), body, p_hash, prev, rec_hash),
            )
        return Record(
            int(cur.lastrowid or 0), record_id, kind, ts, refs, payload, p_hash, prev, rec_hash
        )

    def _row(self, row: tuple[Any, ...]) -> Record:
        return Record(
            row[0],
            row[1],
            row[2],
            row[3],
            json.loads(row[4]),
            json.loads(row[5]),
            row[6],
            row[7],
            row[8],
        )

    _COLS = (
        "seq, record_id, kind, created_at, refs, payload, payload_sha256, prev_hash, record_hash"
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

    def verify(self) -> tuple[bool, list[str]]:
        problems: list[str] = []
        prev = GENESIS
        for r in self.records():
            if sha256(canonical(r.payload)) != r.payload_sha256:
                problems.append(f"{r.record_id}: payload digest mismatch")
            if r.prev_hash != prev:
                problems.append(f"{r.record_id}: broken chain (prev hash mismatch)")
            expect = sha256(
                canonical([r.kind, r.created_at, r.refs, r.payload_sha256, r.prev_hash])
            )
            if expect != r.record_hash:
                problems.append(f"{r.record_id}: record hash mismatch")
            prev = r.record_hash
        return not problems, problems
