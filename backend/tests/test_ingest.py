"""Live FIR ingestion tests (POST /api/ingest/fir).

Covers: regex NER with spans (Indian phones, accounts, vehicles, IPC sections,
names), the anti-noise rules (dates/phone fragments never become IPC sections,
account numbers never double-match as phones), cross-district linkage alerts,
graph growth after merge, and the victim-shield flag on complainants.

    python3 tests/test_ingest.py   # standalone
    pytest -q tests/test_ingest.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

import api.main as apimod                   # noqa: E402
from api.ingest import extract_entities     # noqa: E402

SAMPLE = ("दिनांक 12/04/2026 को शिकायतकर्ता Sunita Devi ने बताया कि Ramesh Kumar ने "
          "उसे +91-8044997278 से धमकी भरा कॉल किया। संदिग्ध का वाहन UP78 GC 4978 देखा गया। "
          "पैसे खाता AC7234309805 में ट्रांसफर हुए। धारा 354D लगाई गई। संदिग्ध का संबंध "
          "Desi Traders Pvt Ltd कंपनी से बताया गया और वह करोल बाग मार्केट में रुका हुआ देखा गया।")


class _Client:
    def __init__(self):
        self.bench = Path(tempfile.mkdtemp()) / "bench"
        apimod.BENCH_DIR = self.bench
        self.c = TestClient(apimod.app).__enter__()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.c.__exit__(None, None, None)
        return False


def _ingest(client: TestClient, **over):
    body = {
        "narrative": SAMPLE,
        "district": "Delhi",
        "police_station": "PS Karol Bagh",
        "date": "2026-04-12",
        "complainant_name": "Sunita Devi",
        "accused_names": ["Ramesh Kumar"],
        **over,
    }
    return client.post("/api/ingest/fir", json=body)


def test_ner_extracts_indian_identifiers_with_spans():
    ents = extract_entities(SAMPLE)
    by_kind = {}
    for e in ents:
        by_kind.setdefault(e.kind, []).append(e)
    assert any(e.normalized == "8044997278" for e in by_kind["PHONE"])
    assert any(e.normalized == "AC7234309805" for e in by_kind["ACCOUNT"])
    assert any(e.normalized == "UP78GC4978" for e in by_kind["VEHICLE"])
    assert any(e.normalized == "354D" for e in by_kind["IPC"])
    # every span points back at the surface in the source text
    for e in ents:
        if e.span != (0, 0):
            assert e.surface in SAMPLE[e.span[0]:e.span[1] + 2] or \
                   SAMPLE[e.span[0]:e.span[1]] in e.surface


def test_ner_extracts_organizations_and_locations():
    ents = extract_entities(SAMPLE)
    by_kind = {}
    for e in ents:
        by_kind.setdefault(e.kind, []).append(e)
    org = {e.surface for e in by_kind.get("ORGANIZATION", [])}
    loc = {e.surface for e in by_kind.get("LOCATION", [])}
    assert org == {"Desi Traders Pvt Ltd"}             # suffix-driven company phrase
    assert loc == {"करोल बाग मार्केट"}                  # Devanagari place marker
    # organisation/location tokens never double-extract as persons
    for e in ents:
        assert not (e.kind == "PERSON" and e.surface in
                    ("Desi", "Traders", "Pvt", "Ltd", "करोल बाग", "मार्केट"))


def test_ner_location_noise_guards():
    assert {e.surface for e in extract_entities(
        "They met at Karol Bagh Road near Kumar Traders.")} == \
        {"Karol Bagh Road", "Kumar Traders"}
    assert {e.surface for e in extract_entities(
        "Stolen from Sector 22 market at evening.")} == {"Sector 22"}
    # the "नगर" tail of a larger word must not become a location
    assert not any(e.kind == "LOCATION" for e in
                   extract_entities("वह पटनागर में रहता है।"))


def test_ner_anti_noise_rules():
    ents = extract_entities(SAMPLE)
    ipcs = {e.normalized for e in ents if e.kind == "IPC"}
    assert "12/04" not in ipcs          # the date is not a section
    assert "91" not in ipcs             # the +91 prefix is not a section
    phones = {e.normalized for e in ents if e.kind == "PHONE"}
    assert "7234309805" not in phones   # the account tail is not a phone


def test_ingest_fires_cross_district_alerts():
    with _Client() as t:
        r = _ingest(t.c)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["record_id"].startswith("FIR-LIVE-")
        assert d["victim_shield_applied"] is True
        alerts = {l["entity_kind"]: l for l in d["cross_case_links"]}
        assert "PHONE" in alerts                      # known benchmark phone
        assert alerts["PHONE"]["cross_district"]      # spans multiple districts
        assert "VEHICLE" in alerts                    # vehicle seen in another FIR
        assert d["new_edges"]                          # graph grew
        sg = t.c.get("/api/graph/subgraph",
                     params={"entity_id": d["new_edges"][0]["source"], "depth": 1}).json()
        assert sg["stats"]["edges"] >= 1              # new node is queryable


def test_ingest_unknown_entities_produce_no_alerts():
    with _Client() as t:
        r = _ingest(t.c, narrative=("दिनांक 13/04/2026 को शिकायतकर्ता ने बताया कि "
                                    "संदिग्ध ने +91-6111100000 से कॉल किया। धारा 506।"))
        assert r.status_code == 200
        d = r.json()
        assert d["cross_case_links"] == []            # nothing to link — honestly empty


def test_ingest_validation_errors():
    with _Client() as t:
        assert t.c.post("/api/ingest/fir", json={"narrative": "short"}).status_code == 422
        assert t.c.post("/api/ingest/fir", json={
            "narrative": SAMPLE, "district": "Delhi"}).status_code == 422


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
