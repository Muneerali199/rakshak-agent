"""End-to-end API tests via FastAPI TestClient (paper Algorithms 2, 3, 7).

Requires the web deps (pip install -r api/requirements.txt). The TestClient triggers the
app's lifespan, which generates (seed 42), resolves, and builds the graph in a temp dir.

    python3 tests/test_api.py       # standalone
    pytest -q                       # if pytest is installed
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

import api.main as apimod                   # noqa: E402


def _client() -> TestClient:
    # point the service at a throwaway benchmark dir so tests never touch ./output
    apimod.BENCH_DIR = Path(tempfile.mkdtemp()) / "bench"
    return TestClient(apimod.app)            # context-managed below to run lifespan


def test_resolve_matches_mohammad_arif():
    with _client() as c:
        r = c.post("/api/resolve", json={
            "name_a": "Mohammad Arif", "name_b": "Mohd Arif",
            "address_a": "H.No 76, Aminabad, Lucknow", "address_b": "Aminabad Rd, Lucknow",
            "age_a": 34, "age_b": 35,
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["decision"] == "MATCH"
        assert d["confidence"] >= 0.72
        assert d["features"]["phonetic"] == 1.0          # metaphone(Mohammad Arif)==metaphone(Mohd Arif)
        assert d["features"]["name"] > 0.9
        assert d["calibrated"] is False                  # Criticism-3 disclosure
        assert d["normalized_a"] == d["normalized_b"]    # both → "arif mohammad"


def test_resolve_devanagari_matches_roman():
    with _client() as c:
        r = c.post("/api/resolve", json={"name_a": "मोहम्मद आरिफ़", "name_b": "Mohd Arif"})
        assert r.status_code == 200
        assert r.json()["decision"] == "MATCH"


def test_resolve_deterministic_phone_forces_match():
    with _client() as c:
        r = c.post("/api/resolve", json={
            "name_a": "A B", "name_b": "Totally Different", "phone_a": "+91-98765-43210", "phone_b": "9876543210",
        })
        d = r.json()
        assert d["features"]["identifier"] == 1.0
        assert d["decision"] == "MATCH" and d["confidence"] == 1.0


def test_subgraph_and_evidence_roundtrip():
    with _client() as c:
        # find a high-risk PERSON via the convenience endpoint
        ents = c.get("/api/entities", params={"type": "PERSON", "limit": 5}).json()
        assert ents, "expected some person entities"
        root = ents[0]["id"]

        sg = c.get("/api/graph/subgraph", params={"entity_id": root, "depth": 2}).json()
        assert sg["root"] == root
        assert sg["stats"]["nodes"] >= 1
        assert sg["edges"], "hub should have edges"

        # every edge exposes provenance + a verifiable hash
        edge = sg["edges"][0]
        assert len(edge["audit_hash"]) == 64
        ev = c.get(f"/api/evidence/{edge['id']}").json()
        assert ev["edge_id"] == edge["id"]
        assert ev["hash_verified"] is True
        assert ev["source_documents"]
        assert ev["reviewer_actions"] == ["ACCEPT", "REJECT", "MODIFY"]


def test_layer_filter_and_404s():
    with _client() as c:
        ph = next(e for e in c.get("/api/entities", params={"type": "PERSON"}).json())
        sg = c.get("/api/graph/subgraph", params={"entity_id": ph["id"], "layers": "spatial"}).json()
        assert set(sg["layer_assignments"]).issubset({"spatial"})
        assert c.get("/api/graph/subgraph", params={"entity_id": "NOPE"}).status_code == 404
        assert c.get("/api/evidence/E99999").status_code == 404


def test_health():
    with _client() as c:
        h = c.get("/api/health").json()
        assert h["status"] == "ok" and h["nodes"] > 0 and h["edges"] > 0


def test_repeat_offender_signal():
    """Every PERSON carries fir_count + repeat_offender; the repeat flag is on
    whenever a person is linked to ≥2 distinct FIR documents (history-sheet lead)."""
    with _client() as c:
        ents = c.get("/api/entities", params={"type": "PERSON"}).json()
        assert ents, "expected some person entities"
        for e in ents:
            assert "fir_count" in e and "repeat_offender" in e
            assert e["fir_count"] >= 0
            assert e["repeat_offender"] == (e["fir_count"] >= 2)
        repeats = [e for e in ents if e["repeat_offender"]]
        assert repeats, "seed-42 should contain at least one repeat-involved person"


def test_hindi_transliterate_and_profile_offline():
    """English→Hindi demo layer is offline + rule-based (builtin-hindi-rules-v1):
    identifiers pass through verbatim, names/addresses render in Devanagari."""
    with _client() as c:
        tok = c.post("/api/auth/login", json={
            "aadhaar": "700011771177", "otp": "771177", "purpose": "test"}).json()["token"]
        h = {"Authorization": f"Bearer {tok}"}

        t = c.post("/api/hindi/transliterate", json={
            "texts": ["Nehaa Kumaar", "Sunita Devi", "Delhi"]}, headers=h).json()
        assert t["engine"] == "builtin-hindi-rules-v1"
        assert t["hindi"] == ["नेहा कुमार", "सुनिता देवी", "दिल्ली"]
        assert "no neural model" in t["disclosure"]

        p = c.post("/api/hindi/profile", json={
            "fields": {
                "name": "Sunita Devi", "phone": "+91-8044997278",
                "account": "AC7234309805", "section": "IPC 354D",
            }}, headers=h).json()
        items = {it["field"]: it for it in p["items"]}
        assert items["name"]["hindi"] == "सुनिता देवी"
        assert items["phone"]["original"] == "+91-8044997278"
        assert items["phone"]["hindi"] == "+91-8044997278"          # identifiers untouched
        assert items["account"]["hindi"] == "AC7234309805"
        assert "सुनिता देवी" in p["paragraph"]


if __name__ == "__main__":
    import traceback

    tests = {k: v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)}
    passed = 0
    for name, fn in tests.items():
        try:
            fn()
            print(f"  ok    {name}")
            passed += 1
        except Exception:
            print(f"  FAIL  {name}")
            traceback.print_exc()
    print(f"\n{passed}/{len(tests)} passed")
    raise SystemExit(0 if passed == len(tests) else 1)
