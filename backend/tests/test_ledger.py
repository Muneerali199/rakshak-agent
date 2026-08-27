"""Hash-chained evidence ledger tests (Algorithm 8, tamper-evidence layer).

The review audit log is a hash chain: every record's ``chain_hash`` covers the full
payload *including* the previous record's ``chain_hash`` ("" for genesis). These tests
prove the chain links correctly, survives restarts, and — critically — detects any
tampering with historical rows, reporting the first offending record id.

    python3 tests/test_ledger.py   # standalone
    pytest -q tests/test_ledger.py
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.review_store import ReviewStore, sha256_of  # noqa: E402


def _store() -> tuple[ReviewStore, Path]:
    d = Path(tempfile.mkdtemp())
    return ReviewStore(d / "reviews.db"), d


def _add(s: ReviewStore, edge: str, decision: str = "ACCEPT", reviewer: str = "inv-1",
         modifications: dict | None = None):
    return s.add_review(edge_id=edge, decision=decision, reviewer_id=reviewer,
                        evidence_payload={"edge_id": edge, "claim": "x"},
                        prev_status="PENDING", modifications=modifications)


def test_genesis_row_chains_to_empty():
    s, _ = _store()
    r = _add(s, "E00001")
    assert r["prev_hash"] == ""
    assert r["chain_hash"] and len(r["chain_hash"]) == 64
    assert s.verify_chain() == {"ok": True, "records": 1, "first_bad_id": None}
    s.close()
    print("✓ genesis row chains to empty prev_hash")


def test_sequential_chain_links():
    s, _ = _store()
    r1 = _add(s, "E00001")
    r2 = _add(s, "E00002", decision="REJECT")
    r3 = _add(s, "E00001", decision="MODIFY", modifications={"confidence": 0.7})
    assert r2["prev_hash"] == r1["chain_hash"]
    assert r3["prev_hash"] == r2["chain_hash"]
    assert len({r1["chain_hash"], r2["chain_hash"], r3["chain_hash"]}) == 3
    v = s.verify_chain()
    assert v["ok"] and v["records"] == 3
    s.close()
    print("✓ sequential records chain prev→next correctly")


def test_tamper_detection_on_edited_row():
    s, d = _store()
    _add(s, "E00001")
    r2 = _add(s, "E00002", decision="ACCEPT")
    s.close()
    # an attacker edits a historical decision directly in the db
    conn = sqlite3.connect(d / "reviews.db")
    conn.execute("UPDATE reviews SET decision = 'REJECT' WHERE id = ?", (r2["id"],))
    conn.commit()
    conn.close()
    s2 = ReviewStore(d / "reviews.db")
    v = s2.verify_chain()
    assert v["ok"] is False and v["first_bad_id"] == r2["id"]
    s2.close()
    print("✓ editing a historical row is detected at that row")


def test_tamper_propagates_through_chain():
    s, d = _store()
    r1 = _add(s, "E00001")
    _add(s, "E00002")
    _add(s, "E00003")
    s.close()
    # attacker rewrites row 1's chain fields to keep row 1 self-consistent but
    # the recomputed hash changes, breaking row 2's prev_hash linkage
    conn = sqlite3.connect(d / "reviews.db")
    row = conn.execute("SELECT * FROM reviews WHERE id = ?", (r1["id"],)).fetchone()
    cols = [c[1] for c in conn.execute("PRAGMA table_info(reviews)")]
    rec = dict(zip(cols, row))
    rec["reviewer_id"] = "mallory"
    rec["chain_hash"] = sha256_of({k: rec[k] for k in
                                   ("edge_id", "decision", "reviewer_id", "timestamp",
                                    "evidence_hash", "modifications", "prev_status", "prev_hash")})
    conn.execute("UPDATE reviews SET reviewer_id = ?, chain_hash = ? WHERE id = ?",
                 ("mallory", rec["chain_hash"], r1["id"]))
    conn.commit()
    conn.close()
    s2 = ReviewStore(d / "reviews.db")
    v = s2.verify_chain()
    # row 1 verifies (attacker fixed its hash) but row 2's prev_hash no longer matches
    assert v["ok"] is False and v["first_bad_id"] == r1["id"] + 1
    s2.close()
    print("✓ even a 'repaired' tamper breaks the next link in the chain")


def test_chain_survives_restart():
    s, d = _store()
    r1 = _add(s, "E00001")
    r2 = _add(s, "E00002", decision="REJECT")
    s.close()
    s2 = ReviewStore(d / "reviews.db")   # fresh connection, same file
    v = s2.verify_chain()
    assert v["ok"] and v["records"] == 2
    latest = s2.latest_reviews()
    assert latest["E00001"]["chain_hash"] == r1["chain_hash"]
    assert latest["E00002"]["prev_hash"] == r1["chain_hash"]
    assert latest["E00002"]["chain_hash"] == r2["chain_hash"]
    s2.close()
    print("✓ chain verifies identically after a restart")


def test_empty_ledger_verifies_ok():
    s, _ = _store()
    assert s.verify_chain() == {"ok": True, "records": 0, "first_bad_id": None}
    s.close()
    print("✓ empty ledger verifies as ok")


if __name__ == "__main__":
    for fn in (test_genesis_row_chains_to_empty, test_sequential_chain_links,
               test_tamper_detection_on_edited_row, test_tamper_propagates_through_chain,
               test_chain_survives_restart, test_empty_ledger_verifies_ok):
        fn()
    print("ledger: 6/6 passed")
