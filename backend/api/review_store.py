"""Human-in-the-loop review persistence (paper Algorithm 8) — hash-chained ledger.

An append-only, **hash-chained** SQLite audit log of investigator review decisions over
graph edges. Every ACCEPT / REJECT / MODIFY is recorded with the reviewer id, a UTC
timestamp, the SHA-256 of the evidence-panel payload that was reviewed, and any
modifications (e.g. an adjusted confidence for INFERRED edges).

Hash chaining (the "evidence ledger"): every record additionally stores

* ``prev_hash``  — the ``chain_hash`` of the previous record ("" for the genesis row), and
* ``chain_hash`` — SHA-256 over the full record payload *including* ``prev_hash``.

So editing, deleting, or reordering **any** historical row breaks every link after it,
and ``verify_chain()`` reports the first offending record id. This delivers the
tamper-evidence property people reach for "blockchain" to get — with stdlib sqlite3.

The store is stdlib-only (`sqlite3`), consistent with the core packages' zero-
dependency design; it lives under ``api/`` because only the web layer touches it.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reviews (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    edge_id        TEXT NOT NULL,
    decision       TEXT NOT NULL CHECK (decision IN ('ACCEPT', 'REJECT', 'MODIFY')),
    reviewer_id    TEXT NOT NULL,
    timestamp      TEXT NOT NULL,
    evidence_hash  TEXT NOT NULL,
    modifications  TEXT,
    prev_status    TEXT NOT NULL,
    prev_hash      TEXT NOT NULL DEFAULT '',
    chain_hash     TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_reviews_edge ON reviews (edge_id);
"""


def canonical_json(payload) -> str:
    """Deterministic JSON for hashing (same convention as graph.build.Edge.canonical)."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def sha256_of(payload) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _chain_hash(row: dict) -> str:
    """SHA-256 over the full audit record *including* the previous record's hash."""
    return sha256_of({
        "edge_id": row["edge_id"],
        "decision": row["decision"],
        "reviewer_id": row["reviewer_id"],
        "timestamp": row["timestamp"],
        "evidence_hash": row["evidence_hash"],
        "modifications": row["modifications"],
        "prev_status": row["prev_status"],
        "prev_hash": row["prev_hash"],
    })


class ReviewStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # FastAPI runs sync endpoints in a threadpool, so the connection must be
        # usable across threads; the lock serialises writes (SQLite is single-writer).
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._lock = threading.Lock()
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._migrate()
            self._conn.commit()

    # ---- migration ----------------------------------------------------------
    def _migrate(self) -> None:
        """Add the chain columns to pre-ledger databases and backfill existing rows."""
        cols = {r[1] for r in self._conn.execute("PRAGMA table_info(reviews)")}
        if "prev_hash" not in cols:
            self._conn.execute("ALTER TABLE reviews ADD COLUMN prev_hash TEXT NOT NULL DEFAULT ''")
        if "chain_hash" not in cols:
            self._conn.execute("ALTER TABLE reviews ADD COLUMN chain_hash TEXT NOT NULL DEFAULT ''")
        # backfill ONLY rows written before the ledger existed (chain_hash == '').
        # Rows that already carry a chain hash are never "repaired" here — that would
        # silently undo tampering, which is exactly what verify_chain() must catch.
        rows = self._conn.execute(
            "SELECT * FROM reviews WHERE chain_hash = '' ORDER BY id"
        ).fetchall()
        if not rows:
            return
        prev_row = self._conn.execute(
            "SELECT chain_hash FROM reviews WHERE chain_hash != '' AND id < ?"
            " ORDER BY id DESC LIMIT 1",
            (rows[0]["id"],),
        ).fetchone()
        prev = prev_row["chain_hash"] if prev_row else ""
        for row in rows:
            rec = {
                "edge_id": row["edge_id"],
                "decision": row["decision"],
                "reviewer_id": row["reviewer_id"],
                "timestamp": row["timestamp"],
                "evidence_hash": row["evidence_hash"],
                "modifications": row["modifications"],
                "prev_status": row["prev_status"],
                "prev_hash": prev,
            }
            ch = _chain_hash(rec)
            self._conn.execute(
                "UPDATE reviews SET prev_hash = ?, chain_hash = ? WHERE id = ?",
                (prev, ch, row["id"]),
            )
            prev = ch

    # ---- writes ---------------------------------------------------------------
    def add_review(
        self,
        edge_id: str,
        decision: str,
        reviewer_id: str,
        evidence_payload: dict,
        prev_status: str,
        modifications: dict | None = None,
    ) -> dict:
        """Append one audit record and return it as a plain dict (Algorithm 8, line 1–8).

        The record is hash-chained to the previous record: ``prev_hash`` is the last
        row's ``chain_hash`` and ``chain_hash`` covers the full payload, so any later
        tampering with history is detectable via :meth:`verify_chain`.
        """
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        ev_hash = sha256_of(evidence_payload)
        mods_json = canonical_json(modifications) if modifications else None
        with self._lock:
            prev_hash = self._conn.execute(
                "SELECT chain_hash FROM reviews ORDER BY id DESC LIMIT 1"
            ).fetchone()
            prev_hash = prev_hash["chain_hash"] if prev_hash else ""
            rec = {
                "edge_id": edge_id,
                "decision": decision,
                "reviewer_id": reviewer_id,
                "timestamp": ts,
                "evidence_hash": ev_hash,
                "modifications": mods_json,
                "prev_status": prev_status,
                "prev_hash": prev_hash,
            }
            ch = _chain_hash(rec)
            cur = self._conn.execute(
                "INSERT INTO reviews (edge_id, decision, reviewer_id, timestamp,"
                " evidence_hash, modifications, prev_status, prev_hash, chain_hash)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (edge_id, decision, reviewer_id, ts, ev_hash, mods_json,
                 prev_status, prev_hash, ch),
            )
            self._conn.commit()
        return {
            "id": cur.lastrowid,
            "edge_id": edge_id,
            "decision": decision,
            "reviewer_id": reviewer_id,
            "timestamp": ts,
            "evidence_hash": ev_hash,
            "modifications": modifications,
            "prev_status": prev_status,
            "prev_hash": prev_hash,
            "chain_hash": ch,
        }

    # ---- reads ----------------------------------------------------------------
    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "edge_id": row["edge_id"],
            "decision": row["decision"],
            "reviewer_id": row["reviewer_id"],
            "timestamp": row["timestamp"],
            "evidence_hash": row["evidence_hash"],
            "modifications": json.loads(row["modifications"]) if row["modifications"] else None,
            "prev_status": row["prev_status"],
            "prev_hash": row["prev_hash"],
            "chain_hash": row["chain_hash"],
        }

    def latest_reviews(self) -> dict[str, dict]:
        """Map of edge_id → its most recent review record (used to overlay state at startup)."""
        rows = self._conn.execute(
            "SELECT r.* FROM reviews r"
            " JOIN (SELECT edge_id, MAX(id) AS max_id FROM reviews GROUP BY edge_id) m"
            " ON r.edge_id = m.edge_id AND r.id = m.max_id"
        ).fetchall()
        return {row["edge_id"]: self._row_to_dict(row) for row in rows}

    def all_reviews(self, edge_id: str | None = None, limit: int = 200) -> list[dict]:
        """Full append-only history, newest first — optionally filtered by edge."""
        if edge_id:
            rows = self._conn.execute(
                "SELECT * FROM reviews WHERE edge_id = ? ORDER BY id DESC LIMIT ?", (edge_id, limit)
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM reviews ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [self._row_to_dict(row) for row in rows]

    # ---- ledger verification ----------------------------------------------------
    def verify_chain(self) -> dict:
        """Re-walk the whole ledger, recomputing every link.

        Returns ``{ok, records, first_bad_id}`` — ``ok`` is False (and ``first_bad_id``
        set) if any row's stored hashes don't match a recomputation, or a row's
        ``prev_hash`` doesn't equal the previous row's ``chain_hash``. An empty ledger
        verifies as ok.
        """
        rows = self._conn.execute("SELECT * FROM reviews ORDER BY id").fetchall()
        prev = ""
        for row in rows:
            # hash over the raw stored values (modifications as its stored JSON string)
            rec = {
                "edge_id": row["edge_id"],
                "decision": row["decision"],
                "reviewer_id": row["reviewer_id"],
                "timestamp": row["timestamp"],
                "evidence_hash": row["evidence_hash"],
                "modifications": row["modifications"],
                "prev_status": row["prev_status"],
                "prev_hash": row["prev_hash"],
            }
            if rec["prev_hash"] != prev:
                return {"ok": False, "records": len(rows), "first_bad_id": row["id"]}
            if row["chain_hash"] != _chain_hash(rec):
                return {"ok": False, "records": len(rows), "first_bad_id": row["id"]}
            prev = row["chain_hash"]
        return {"ok": True, "records": len(rows), "first_bad_id": None}

    def close(self) -> None:
        self._conn.close()
