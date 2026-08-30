"""RakshakAI Sentinel — the platform audits itself, and can prove it.

Inspired by China's MLPS 2.0 (graded protection levels) and Cryptography Law
(certified components) — the architecture, without the authoritarian payload:

  * **Graded endpoint levels** — every route carries a protection level
    (L1 public read → L4 administrative). L3 is *enforced in code* by the
    warrant gate; the full map is published on the posture endpoint.
  * **Self-scanning pipeline** — at startup the platform runs its own security
    scanner over its own source tree and hash-chains the report into a sentinel
    ledger. The system's security posture is itself tamper-evident evidence.
  * **Component integrity** — a build manifest (SHA-256 over every backend source
    file) is computed at boot; if a RakshakAI model file is configured
    (``RAKSHAK_MODEL_PATH``), its hash is pinned and verified the same way.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from .scanner import scan as run_scan

# ---- graded protection map (MLPS-style; L3 enforced by the warrant gate) --------
ENDPOINT_LEVELS: dict[str, tuple[int, str]] = {
    "GET /api/health": (1, "public read"),
    "GET /api/entities": (1, "public read"),
    "GET /api/anomalies": (1, "public read — analytical leads"),
    "GET /api/escalation": (2, "investigator — victim-linked alerts shielded"),
    "GET /api/graph/subgraph": (2, "investigator"),
    "GET /api/query": (2, "investigator — grounded, refuses protected parties"),
    "POST /api/resolve": (2, "investigator"),
    "POST /api/ingest/fir": (2, "investigator — writes to the case graph"),
    "POST /api/review": (2, "investigator — hash-chained review decision"),
    "GET /api/evidence/{edge_id}": (3, "protected — warrant-gated unmasking"),
    "GET /api/report/{entity_id}": (3, "protected — court artifact"),
    "GET /api/blindspot/{entity_id}": (1, "public read — honesty surface"),
    "POST /api/scan": (2, "investigator — RakshakAI self-security"),
    "POST /api/warrants": (3, "protected — warrant lifecycle"),
    "GET /api/warrants": (4, "administrative — audit trail"),
    "GET /api/security/posture": (4, "administrative — this endpoint"),
    "POST /mesh/query": (3, "vault-to-vault — signed envelopes only"),
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sentinel_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    event         TEXT NOT NULL,              -- BOOT_SCAN | MODEL_PIN
    report        TEXT NOT NULL,              -- canonical JSON scan/pin report
    report_hash   TEXT NOT NULL,
    timestamp     TEXT NOT NULL,
    prev_hash     TEXT NOT NULL DEFAULT '',
    chain_hash    TEXT NOT NULL DEFAULT ''
);
"""


def _canonical(payload) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def _sha256(payload) -> str:
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _chain_hash(row: dict) -> str:
    return _sha256({"event": row["event"], "report": row["report"],
                    "timestamp": row["timestamp"], "prev_hash": row["prev_hash"]})


class SentinelStore:
    """Hash-chained log of the platform's own security scans (stdlib sqlite3)."""

    def __init__(self, db_path: str | Path) -> None:
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._lock = threading.Lock()
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def log(self, event: str, report: dict) -> dict:
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        report_json = _canonical(report)
        with self._lock:
            prev_row = self._conn.execute(
                "SELECT chain_hash FROM sentinel_log ORDER BY id DESC LIMIT 1").fetchone()
            prev = prev_row["chain_hash"] if prev_row else ""
            rec = {"event": event, "report": report_json, "timestamp": ts, "prev_hash": prev}
            ch = _chain_hash(rec)
            cur = self._conn.execute(
                "INSERT INTO sentinel_log (event, report, report_hash, timestamp, prev_hash, chain_hash)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (event, report_json, _sha256(report), ts, prev, ch))
            self._conn.commit()
        return {"id": cur.lastrowid, "event": event, "timestamp": ts, "chain_hash": ch}

    def latest(self, event: str | None = None) -> dict | None:
        if event:
            row = self._conn.execute(
                "SELECT * FROM sentinel_log WHERE event = ? ORDER BY id DESC LIMIT 1",
                (event,)).fetchone()
        else:
            row = self._conn.execute(
                "SELECT * FROM sentinel_log ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None

    def verify_chain(self) -> dict:
        rows = self._conn.execute("SELECT * FROM sentinel_log ORDER BY id").fetchall()
        prev = ""
        for row in rows:
            rec = {"event": row["event"], "report": row["report"],
                   "timestamp": row["timestamp"], "prev_hash": row["prev_hash"]}
            if rec["prev_hash"] != prev or row["chain_hash"] != _chain_hash(rec):
                return {"ok": False, "records": len(rows), "first_bad_id": row["id"]}
            prev = row["chain_hash"]
        return {"ok": True, "records": len(rows), "first_bad_id": None}

    def close(self) -> None:
        self._conn.close()


# ---- self-scan + integrity -------------------------------------------------------
def scan_own_codebase(root: Path) -> dict:
    """Run the platform's own scanner over its own source tree (bounded, honest)."""
    findings = []
    files_scanned = 0
    for path in sorted(root.rglob("*.py")):
        if any(part in ("__pycache__", ".venv", "output", "output-vaults") for part in path.parts):
            continue
        if files_scanned >= 40:                     # keep boot fast — bounded scan
            break
        code = path.read_text(encoding="utf-8", errors="ignore")
        result = run_scan(code)
        files_scanned += 1
        for f in result.get("findings", []):
            findings.append({"file": path.name, **f})
    worst = "none"
    order = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    for f in findings:
        sev = str(f.get("severity", "low")).lower()
        if order.get(sev, 1) > order[worst]:
            worst = sev
    return {"files_scanned": files_scanned, "findings": findings[:50],
            "finding_count": len(findings), "worst_severity": worst}


def build_manifest(root: Path) -> dict:
    """SHA-256 over every backend source file — tamper-evident code integrity."""
    h = hashlib.sha256()
    files = 0
    for path in sorted(root.rglob("*.py")):
        if any(part in ("__pycache__", ".venv") for part in path.parts):
            continue
        h.update(path.name.encode())
        h.update(path.read_bytes())
        files += 1
    return {"files": files, "manifest_sha256": h.hexdigest()}


def model_pin() -> dict:
    """Hash-pin the RakshakAI model file when configured; honestly absent otherwise."""
    import os
    path = os.getenv("RAKSHAK_MODEL_PATH", "").strip()
    if not path or not Path(path).exists():
        return {"configured": False, "note": "no local model file pinned (rule-engine mode)"}
    h = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return {"configured": True, "path": Path(path).name, "sha256": h}
