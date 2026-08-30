"""RakshakAI Sentinel tests — the platform audits itself, and proves it."""
from __future__ import annotations

import pytest

from api.sentinel import SentinelStore, build_manifest, model_pin, scan_own_codebase


def test_self_scan_chained(tmp_path):
    store = SentinelStore(str(tmp_path / "sentinel.db"))
    store.log("BOOT_SCAN", {"files_scanned": 10, "findings": [], "worst_severity": "none"})
    store.log("MODEL_PIN", {"configured": False})
    assert store.verify_chain()["ok"] is True
    latest = store.latest()
    assert latest["event"] == "MODEL_PIN"
    store._conn.execute("UPDATE sentinel_log SET report='{\"hacked\":true}' WHERE id = 1")
    res = store.verify_chain()
    assert res["ok"] is False and res["first_bad_id"] == 1
    store.close()


def test_manifest_and_scan(tmp_path):
    from pathlib import Path
    backend = Path(__file__).resolve().parent.parent
    manifest = build_manifest(backend)
    assert manifest["files"] > 20 and len(manifest["manifest_sha256"]) == 64
    report = scan_own_codebase(backend)
    assert report["files_scanned"] > 0
    assert report["worst_severity"] in ("none", "low", "medium", "high", "critical")


def test_model_pin_absent(monkeypatch):
    monkeypatch.delenv("RAKSHAK_MODEL_PATH", raising=False)
    assert model_pin()["configured"] is False


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    import api.main as apimod
    with TestClient(apimod.app) as c:
        yield c


def test_posture_endpoint(client):
    r = client.get("/api/security/posture")
    assert r.status_code == 200
    body = r.json()
    # graded levels published, L3 warrant gate visible
    assert body["levels"]["GET /api/evidence/{edge_id}"]["level"] == 3
    # boot self-scan present and hash-chained
    assert body["boot_scan"]["report"]["files_scanned"] > 0
    assert body["boot_scan"]["chain_hash"]
    # every ledger verifies
    assert all(l["ok"] for l in body["ledgers"].values() if l is not None)
    # code manifest integrity present
    assert len(body["manifest"]["manifest_sha256"]) == 64
