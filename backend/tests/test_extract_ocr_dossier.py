"""OCR, pluggable extractor, and person-dossier endpoints — officer-gated,
honestly-labelled engines, deterministic outputs (no LLM in the serving path).
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

import auth_helpers                            # noqa: E402
import api.main as apimod                      # noqa: E402
from api.extract import engine_available       # noqa: E402

PERSON_TEXT = (
    "शिकायतकर्ता सुनीता देवी ने बताया कि मोहम्मद आरिफ़ ने +91-8044997278 से धमकी दी, "
    "खाता AC0076617711 मालूम हुआ, वाहन UP78GC4978 के साथ का मामला है।"
)


SHARED_BENCH = Path(tempfile.mkdtemp()) / "bench"   # all fixtures mount one dir → warm cluster cache


def _fresh_app() -> TestClient:
    apimod.BENCH_DIR = SHARED_BENCH
    c = TestClient(apimod.app)
    c.__enter__()
    return c


def _png_bytes() -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (240, 240, 240)).save(buf, format="PNG")
    return buf.getvalue()


def test_extract_hybrid_returns_structured_entities():
    with _fresh_app() as c:
        h = auth_helpers.io_headers(c)
        r = c.post("/api/ingest/extract?engine=hybrid", json={"text": PERSON_TEXT}, headers=h)
        assert r.status_code == 200
        d = r.json()
        kinds = {e["kind"] for e in d["entities"]}
        assert "PHONE" in kinds and "ACCOUNT" in kinds and "VEHICLE" in kinds
        assert d["engine"] in {"regex-only", "hybrid"}
        assert "model" in d and "disclosure" in d


def test_extract_hybrid_bad_engine_rejected():
    with _fresh_app() as c:
        h = auth_helpers.io_headers(c)
        r = c.post("/api/ingest/extract?engine=bogus", json={"text": PERSON_TEXT}, headers=h)
        assert r.status_code == 400


def test_ocr_extract_requires_upload_and_is_officer_gated():
    with _fresh_app() as c:
        r = c.post("/api/ocr/extract")                       # no auth
        assert r.status_code == 401
        h = auth_helpers.io_headers(c)
        r = c.post("/api/ocr/extract", headers=h)            # no file
        assert r.status_code == 422
        if not apimod.ocr.available():
            return                                           # box without tesseract → skip live run
        r = c.post("/api/ocr/extract?auto=true", headers=h,
                   files={"file": ("scan.png", _png_bytes(), "image/png")})
        assert r.status_code == 200
        assert r.json()["engine"] == "tesseract-ocr"


def test_person_dossier_resolves_name_and_lists_firs():
    with _fresh_app() as c:
        h = auth_helpers.io_headers(c)
        r = c.post("/api/ingest/fir",
                   json={"record_id": "DEL-FIR-OCR-9", "district": "Delhi",
                         "police_station": "PS Karol Bagh", "date": "2026-10-07",
                         "narrative": PERSON_TEXT,
                         "complainant_name": "Sunita Devi",
                         "accused_names": ["Ravi Das"]},
                   headers=h)
        assert r.status_code == 200
        r = c.post("/api/resolve/person", json={"name": "रवी दास"}, headers=h)
        assert r.status_code == 200
        d = r.json()
        assert d["found"] is True
        assert d["fir_count"] >= 1
        assert "accused" in d["roles"]
        assert d["engine"]
        assert "disclosure" in d


def test_person_dossier_unknown_name_is_honest_not_found():
    with _fresh_app() as c:
        h = auth_helpers.io_headers(c)
        r = c.post("/api/resolve/person", json={"name": "Vikram Singh Rathore"}, headers=h)
        assert r.status_code == 200
        d = r.json()
        assert d["found"] is False
        assert "disclosure" in d


def test_extract_model_availability_flag_reported_honestly():
    assert isinstance(engine_available(), bool)