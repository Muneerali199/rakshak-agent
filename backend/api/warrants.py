"""Warrant Gate — DEPA-style consent artifacts for protected-data access.

Modelled on India's Account Aggregator / DEPA architecture (RBI-regulated):
data is shared only against a **scoped, expiring, revocable, signed artifact** —
never on a bare click. Here the artifact is a *warrant*: an investigating officer
requests access to a protected party's identity, a senior officer countersigns,
and every request / approval / use / revocation is hash-chained into a ledger.

Design rules (constitutional by construction):
  * requester and approver must be **different people** (four-eyes principle,
    the INTERPOL dual-key model — and the approval gate IJOP had, with the
    cryptographic proof IJOP lacked);
  * approver must hold a **senior rank** (SP and above);
  * every warrant has scope + expiry; use outside scope/expiry is denied;
  * the ledger is tamper-evident — editing history breaks the chain.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone

_SCHEMA = """
CREATE TABLE IF NOT EXISTS warrants (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    warrant_id     TEXT NOT NULL,
    event          TEXT NOT NULL CHECK (event IN ('REQUEST','APPROVE','USE','REVOKE','DENY')),
    scope          TEXT NOT NULL,           -- e.g. 'victim:C00143' or 'edge:E-...'
    requester_id   TEXT NOT NULL,
    requester_role TEXT NOT NULL,
    approver_id    TEXT,
    approver_role  TEXT,
    reason         TEXT,
    expires_at     TEXT,
    timestamp      TEXT NOT NULL,
    prev_hash      TEXT NOT NULL DEFAULT '',
    chain_hash     TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_warrants_wid ON warrants (warrant_id);
"""

SENIOR_ROLES = {"SP", "SSP", "DIG", "IG", "CP", "DCP"}
DEFAULT_TTL_MINUTES = 30


def _canonical(payload) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def _sha256(payload) -> str:
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _chain_hash(row: dict) -> str:
    return _sha256({k: row[k] for k in (
        "warrant_id", "event", "scope", "requester_id", "requester_role",
        "approver_id", "approver_role", "reason", "expires_at", "timestamp", "prev_hash")})


def _now() -> datetime:
    return datetime.now(timezone.utc)


class WarrantStore:
    """Append-only, hash-chained ledger of warrant lifecycle events."""

    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._lock = threading.Lock()
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # ---- internal -------------------------------------------------------------
    def _append(self, **fields) -> dict:
        ts = _now().isoformat(timespec="seconds")
        with self._lock:
            row_prev = self._conn.execute(
                "SELECT chain_hash FROM warrants ORDER BY id DESC LIMIT 1").fetchone()
            prev = row_prev["chain_hash"] if row_prev else ""
            rec = {"timestamp": ts, "prev_hash": prev,
                   "approver_id": None, "approver_role": None, "reason": None,
                   "expires_at": None, **fields}
            ch = _chain_hash(rec)
            cur = self._conn.execute(
                "INSERT INTO warrants (warrant_id, event, scope, requester_id, requester_role,"
                " approver_id, approver_role, reason, expires_at, timestamp, prev_hash, chain_hash)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (rec["warrant_id"], rec["event"], rec["scope"], rec["requester_id"],
                 rec["requester_role"], rec["approver_id"], rec["approver_role"],
                 rec["reason"], rec["expires_at"], ts, prev, ch))
            self._conn.commit()
        return {"id": cur.lastrowid, **rec, "chain_hash": ch}

    def _events(self, warrant_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM warrants WHERE warrant_id = ? ORDER BY id", (warrant_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ---- lifecycle --------------------------------------------------------------
    def request(self, scope: str, requester_id: str, requester_role: str,
                reason: str, ttl_minutes: int = DEFAULT_TTL_MINUTES) -> dict:
        """Open a warrant request (PENDING until a senior countersigns)."""
        wid = "W-" + uuid.uuid4().hex[:8].upper()
        expires = (_now() + timedelta(minutes=ttl_minutes)).isoformat(timespec="seconds")
        rec = self._append(warrant_id=wid, event="REQUEST", scope=scope,
                           requester_id=requester_id, requester_role=requester_role,
                           reason=reason, expires_at=expires)
        return {"warrant_id": wid, "status": "PENDING", "scope": scope,
                "expires_at": expires, "request_event": rec}

    def approve(self, warrant_id: str, approver_id: str, approver_role: str) -> dict:
        """Countersign a pending warrant — four-eyes + seniority enforced in code."""
        events = self._events(warrant_id)
        if not events:
            return {"ok": False, "error": f"warrant '{warrant_id}' not found"}
        if any(e["event"] == "APPROVE" for e in events):
            return {"ok": False, "error": "warrant already approved"}
        if any(e["event"] == "REVOKE" for e in events):
            return {"ok": False, "error": "warrant was revoked"}
        req = events[0]
        if approver_id.strip().lower() == req["requester_id"].strip().lower():
            self._append(warrant_id=warrant_id, event="DENY", scope=req["scope"],
                         requester_id=req["requester_id"],
                         requester_role=req["requester_role"],
                         approver_id=approver_id, approver_role=approver_role,
                         reason="self-approval is not permitted (four-eyes principle)")
            return {"ok": False, "error": "self-approval is not permitted — a senior officer must countersign"}
        if approver_role.upper() not in SENIOR_ROLES:
            self._append(warrant_id=warrant_id, event="DENY", scope=req["scope"],
                         requester_id=req["requester_id"],
                         requester_role=req["requester_role"],
                         approver_id=approver_id, approver_role=approver_role,
                         reason="approver rank below SP")
            return {"ok": False, "error": f"approver must be SP rank or above (got {approver_role})"}
        self._append(warrant_id=warrant_id, event="APPROVE", scope=req["scope"],
                     requester_id=req["requester_id"], requester_role=req["requester_role"],
                     approver_id=approver_id, approver_role=approver_role.upper(),
                     reason=req["reason"], expires_at=req["expires_at"])
        return {"ok": True, "warrant_id": warrant_id, "status": "APPROVED",
                "scope": req["scope"], "expires_at": req["expires_at"]}

    def check(self, warrant_id: str, scope: str, log_use: bool = True) -> dict:
        """Validate a warrant for a scope; optionally ledger the access itself (USE event)."""
        events = self._events(warrant_id)
        if not events:
            return {"ok": False, "error": "warrant not found"}
        req = events[0]
        if any(e["event"] == "REVOKE" for e in events):
            return {"ok": False, "error": "warrant revoked"}
        approvals = [e for e in events if e["event"] == "APPROVE"]
        if not approvals:
            return {"ok": False, "error": "warrant pending countersignature"}
        if req["scope"] != scope:
            return {"ok": False, "error": f"warrant scope is '{req['scope']}', not '{scope}'"}
        if req["expires_at"] and _now() > datetime.fromisoformat(req["expires_at"]):
            return {"ok": False, "error": "warrant expired"}
        if log_use:
            ap = approvals[-1]
            self._append(warrant_id=warrant_id, event="USE", scope=scope,
                         requester_id=req["requester_id"], requester_role=req["requester_role"],
                         approver_id=ap["approver_id"], approver_role=ap["approver_role"],
                         reason=req["reason"], expires_at=req["expires_at"])
        return {"ok": True, "warrant_id": warrant_id, "scope": scope}

    def revoke(self, warrant_id: str, by: str, role: str) -> dict:
        events = self._events(warrant_id)
        if not events:
            return {"ok": False, "error": "warrant not found"}
        req = events[0]
        self._append(warrant_id=warrant_id, event="REVOKE", scope=req["scope"],
                     requester_id=by, requester_role=role, reason="revoked")
        return {"ok": True, "warrant_id": warrant_id, "status": "REVOKED"}

    # ---- audit ------------------------------------------------------------------
    def all_events(self, limit: int = 200) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM warrants ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def verify_chain(self) -> dict:
        rows = self._conn.execute("SELECT * FROM warrants ORDER BY id").fetchall()
        prev = ""
        for row in rows:
            rec = {k: row[k] for k in ("warrant_id", "event", "scope", "requester_id",
                                       "requester_role", "approver_id", "approver_role",
                                       "reason", "expires_at", "timestamp", "prev_hash")}
            if rec["prev_hash"] != prev or row["chain_hash"] != _chain_hash(rec):
                return {"ok": False, "records": len(rows), "first_bad_id": row["id"]}
            prev = row["chain_hash"]
        return {"ok": True, "records": len(rows), "first_bad_id": None}

    def close(self) -> None:
        self._conn.close()
