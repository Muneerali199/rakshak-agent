"""Mesh exchange ledger — the gateway's tamper-evident receipt book.

Every cross-vault exchange is recorded here as a hash-chained row: the envelope
the gateway received, the receipts the vaults returned, and whether each signature
verified. The gateway stores **exchange metadata only — never case data** (the
NPCI analogy: the switch sees that a transaction happened, not what your money
bought).

Same chaining discipline as the evidence ledger (api/review_store.py): editing,
deleting, or reordering any historical exchange breaks every link after it, and
``verify_chain()`` reports the first offending row.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS exchanges (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id     TEXT NOT NULL,
    origin_vault   TEXT NOT NULL,
    query_type     TEXT NOT NULL,
    entity_keys    TEXT NOT NULL,          -- canonical JSON list (keys, not data)
    envelope_sig_ok INTEGER NOT NULL,      -- 1/0: origin signature verified
    receipts       TEXT NOT NULL,          -- canonical JSON list of receipts
    receipt_sig_ok INTEGER NOT NULL,       -- 1/0: all receipt signatures verified
    timestamp      TEXT NOT NULL,
    prev_hash      TEXT NOT NULL DEFAULT '',
    chain_hash     TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_exchanges_req ON exchanges (request_id);
"""


def _canonical(payload) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def _sha256(payload) -> str:
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _chain_hash(row: dict) -> str:
    return _sha256({
        "request_id": row["request_id"],
        "origin_vault": row["origin_vault"],
        "query_type": row["query_type"],
        "entity_keys": row["entity_keys"],
        "envelope_sig_ok": row["envelope_sig_ok"],
        "receipts": row["receipts"],
        "receipt_sig_ok": row["receipt_sig_ok"],
        "timestamp": row["timestamp"],
        "prev_hash": row["prev_hash"],
    })


class MeshLedger:
    """Append-only, hash-chained log of cross-vault exchanges (stdlib sqlite3)."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._lock = threading.Lock()
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def log_exchange(self, envelope: dict, receipts: list[dict],
                     envelope_sig_ok: bool, receipt_sig_ok: bool) -> dict:
        """Append one exchange record and return it (with its chain hashes)."""
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._lock:
            row_prev = self._conn.execute(
                "SELECT chain_hash FROM exchanges ORDER BY id DESC LIMIT 1"
            ).fetchone()
            prev_hash = row_prev["chain_hash"] if row_prev else ""
            rec = {
                "request_id": envelope["request_id"],
                "origin_vault": envelope["origin_vault"],
                "query_type": envelope["query_type"],
                "entity_keys": _canonical(envelope["entity_keys"]),
                "envelope_sig_ok": 1 if envelope_sig_ok else 0,
                "receipts": _canonical(receipts),
                "receipt_sig_ok": 1 if receipt_sig_ok else 0,
                "timestamp": ts,
                "prev_hash": prev_hash,
            }
            ch = _chain_hash(rec)
            cur = self._conn.execute(
                "INSERT INTO exchanges (request_id, origin_vault, query_type, entity_keys,"
                " envelope_sig_ok, receipts, receipt_sig_ok, timestamp, prev_hash, chain_hash)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (rec["request_id"], rec["origin_vault"], rec["query_type"], rec["entity_keys"],
                 rec["envelope_sig_ok"], rec["receipts"], rec["receipt_sig_ok"],
                 ts, prev_hash, ch),
            )
            self._conn.commit()
        return {"id": cur.lastrowid, **rec, "chain_hash": ch}

    def get_exchange(self, request_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM exchanges WHERE request_id = ? ORDER BY id DESC LIMIT 1",
            (request_id,),
        ).fetchone()
        return self._row_to_dict(row) if row else None

    def all_exchanges(self, limit: int = 100) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM exchanges ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def verify_chain(self) -> dict:
        rows = self._conn.execute("SELECT * FROM exchanges ORDER BY id").fetchall()
        prev = ""
        for row in rows:
            rec = {
                "request_id": row["request_id"],
                "origin_vault": row["origin_vault"],
                "query_type": row["query_type"],
                "entity_keys": row["entity_keys"],
                "envelope_sig_ok": row["envelope_sig_ok"],
                "receipts": row["receipts"],
                "receipt_sig_ok": row["receipt_sig_ok"],
                "timestamp": row["timestamp"],
                "prev_hash": row["prev_hash"],
            }
            if rec["prev_hash"] != prev:
                return {"ok": False, "records": len(rows), "first_bad_id": row["id"]}
            if row["chain_hash"] != _chain_hash(rec):
                return {"ok": False, "records": len(rows), "first_bad_id": row["id"]}
            prev = row["chain_hash"]
        return {"ok": True, "records": len(rows), "first_bad_id": None}

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "request_id": row["request_id"],
            "origin_vault": row["origin_vault"],
            "query_type": row["query_type"],
            "entity_keys": json.loads(row["entity_keys"]),
            "envelope_sig_ok": bool(row["envelope_sig_ok"]),
            "receipts": json.loads(row["receipts"]),
            "receipt_sig_ok": bool(row["receipt_sig_ok"]),
            "timestamp": row["timestamp"],
            "prev_hash": row["prev_hash"],
            "chain_hash": row["chain_hash"],
        }

    def close(self) -> None:
        self._conn.close()
