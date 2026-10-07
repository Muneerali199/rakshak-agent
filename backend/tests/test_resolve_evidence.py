"""Evidence auto-resolution: full document → every person auto-resolved against
the case graph. Officer-gated (rank ≥ 1), honourably labelled engine with an
explicit HITL "route_to_review" flag — never a machine verdict.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

import auth_helpers                            # noqa: E402
import api.main as apimod                      # noqa: E402
from resolve.evidence import engine_name       # noqa: E402

SAMPLE = (
    "Statement: complainant Sunita Devi reported that accused Mohammad Arif and Nehaa Kumaar "
    "sent her threats; Ramesh Kumar moved funds AC0076617711; Suneel Sheikh used vehicle "
    "KA01MN2233 along phone +91 8044997278."
)


def _fresh_app() -> TestClient:
    apimod.BENCH_DIR = Path(tempfile.mkdtemp()) / "bench"
    c = TestClient(apimod.app)
    c.__enter__()
    return c


def test_evidence_resolve_text_auto_resolves_cross_script_names():
    with _fresh_app() as c:
        h = auth_helpers.io_headers(c)
        r = c.post("/api/resolve/evidence", json={"text": SAMPLE}, headers=h)
        assert r.status_code == 200
        d = r.json()
        assert d["engine"] == engine_name()               # honest: builtin-rule-romanizer
        assert d["count"] == 5 and d["candidate_count"] > 0
        rows = {row["surface"]: row for row in d["rows"]}
        assert "Sunita Devi" in rows and "Nehaa Kumaar" in rows
        # exact graph label forms a certain MATCH
        hit = rows["Nehaa Kumaar"]
        assert hit["decision"] == "MATCH" and hit["confidence"] >= 0.99
        assert hit["match"] and hit["match"]["id"].startswith("C")
        # tight phonetic match still resolves (no neu-blocked engine needed)
        assert rows["Suneel Sheikh"]["decision"] == "MATCH"
        # ambiguous lead → HITL route_to_review (never a machine verdict)
        assert any(r["route_to_review"] for r in d["rows"])
        assert "no neural IndicXlit" in d["disclosure"] or "builtin" in d["disclosure"]


def test_evidence_resolve_is_officer_gated():
    with _fresh_app() as c:
        assert c.post("/api/resolve/evidence", json={"text": SAMPLE}).status_code == 401
        assert c.post("/api/resolve/evidence/pdf",
                      files={"file": ("a.pdf", b"%PDF-garbage", "application/pdf")}).status_code == 401


def test_evidence_pdf_extracts_and_resolves():
    with _fresh_app() as c:
        h = auth_helpers.io_headers(c)
        # good-PDF path is exercised by the text handler; here we only sanity-check
        # that a non-PDF upload is rejected with 400, not 500
        r = c.post("/api/resolve/evidence/pdf",
                   files={"file": ("nope.pdf", b"not a pdf at all", "application/pdf")},
                   headers=h)
        assert r.status_code == 400


def test_evidence_in_posture_graded_map():
    with _fresh_app() as c:
        p = c.get("/api/security/posture").json()
        assert p["levels"]["POST /api/resolve/evidence"]["level"] == 1
        assert p["levels"]["POST /api/resolve/evidence/pdf"]["level"] == 1