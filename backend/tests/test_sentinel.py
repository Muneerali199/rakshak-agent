"""RakshakAI Sentinel tests — the platform audits itself, and proves it."""
from __future__ import annotations

import json

import pytest

from api.sentinel import (SentinelStore, build_manifest, check_manifest, model_pin,
                          release_manifest_check, scan_own_codebase)


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


# ─────────────────── manifest comparison (detection, not display) ───────────────────

def test_check_manifest_first_boot():
    cur = {"files": 3, "manifest_sha256": "a" * 64}
    out = check_manifest(cur, None)
    assert out["first_boot"] is True and out["changed"] is False
    assert out["manifest_sha256"] == "a" * 64


def test_check_manifest_unchanged():
    cur = {"files": 3, "manifest_sha256": "a" * 64}
    prev_row = {"report": json.dumps({"manifest_sha256": "a" * 64, "files": 3})}
    out = check_manifest(cur, prev_row)
    assert out["changed"] is False


def test_check_manifest_changed():
    cur = {"files": 3, "manifest_sha256": "b" * 64}
    prev_row = {"report": json.dumps({"manifest_sha256": "a" * 64, "files": 3})}
    out = check_manifest(cur, prev_row)
    assert out["changed"] is True
    assert out["previous_sha256"] == "a" * 64


def test_release_manifest_check_not_configured():
    assert release_manifest_check({"manifest_sha256": "x"}, "") is None


def test_release_manifest_check_match(tmp_path):
    rel = tmp_path / "release.json"
    rel.write_text(json.dumps({"files": 3, "manifest_sha256": "c" * 64}), encoding="utf-8")
    out = release_manifest_check({"files": 3, "manifest_sha256": "c" * 64}, str(rel))
    assert out["matches_release"] is True


def test_release_manifest_check_mismatch(tmp_path):
    rel = tmp_path / "release.json"
    rel.write_text(json.dumps({"files": 3, "manifest_sha256": "c" * 64}), encoding="utf-8")
    out = release_manifest_check({"files": 3, "manifest_sha256": "d" * 64}, str(rel))
    assert out["matches_release"] is False


def test_release_manifest_check_missing_file(tmp_path):
    out = release_manifest_check({"manifest_sha256": "d" * 64}, str(tmp_path / "gone.json"))
    assert out["matches_release"] is False and out["exists"] is False


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
    # code manifest integrity present AND compared (not merely displayed)
    assert len(body["manifest"]["manifest_sha256"]) == 64
    mc = body["manifest_check"]
    assert mc is not None and "changed" in mc and "first_boot" in mc
