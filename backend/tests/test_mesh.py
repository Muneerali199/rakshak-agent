"""Mesh tests — signed envelopes, hash-chained exchange ledger, end-to-end fan-out.

No sockets: gateway fan-out and vault ingest fan-out both use injected transports,
so the whole UPI-of-intelligence flow is tested in-process and deterministically.
"""
from __future__ import annotations

import pytest

from mesh import protocol
from mesh.ledger import MeshLedger

SECRETS = {"delhi": "s-delhi", "mumbai": "s-mumbai", "jaipur": "s-jaipur"}


# ---- protocol -----------------------------------------------------------------
def test_envelope_roundtrip_and_tamper():
    env = protocol.make_envelope("delhi", "ENTITY_LOOKUP", ["PHONE:8044997278"], SECRETS["delhi"])
    assert protocol.verify_envelope(env, SECRETS["delhi"])
    # tampered payload → signature breaks
    bad = dict(env, entity_keys=["PHONE:0000000000"])
    assert not protocol.verify_envelope(bad, SECRETS["delhi"])
    # wrong secret → signature breaks
    assert not protocol.verify_envelope(env, SECRETS["mumbai"])


def test_receipt_roundtrip_and_tamper():
    env = protocol.make_envelope("delhi", "ENTITY_LOOKUP", ["PHONE:8044997278"], SECRETS["delhi"])
    rec = protocol.make_receipt(env, "mumbai", 1,
                                [{"entity_key": "PHONE:8044997278", "record_count": 3,
                                  "record_ids": ["CDR-1", "CDR-2", "CDR-3"]}],
                                SECRETS["mumbai"])
    assert protocol.verify_receipt(rec, SECRETS["mumbai"])
    assert not protocol.verify_receipt(dict(rec, hits=99), SECRETS["mumbai"])
    assert not protocol.verify_receipt(rec, SECRETS["jaipur"])


# ---- exchange ledger ------------------------------------------------------------
def test_mesh_ledger_chain_and_tamper(tmp_path):
    led = MeshLedger(tmp_path / "mesh.db")
    env = protocol.make_envelope("delhi", "ENTITY_LOOKUP", ["PHONE:8044997278"], SECRETS["delhi"])
    led.log_exchange(env, [], envelope_sig_ok=True, receipt_sig_ok=True)
    led.log_exchange(env, [], envelope_sig_ok=True, receipt_sig_ok=True)
    assert led.verify_chain() == {"ok": True, "records": 2, "first_bad_id": None}
    # tamper with history → the chain must break at that row
    led._conn.execute("UPDATE exchanges SET origin_vault = 'mumbai' WHERE id = 1")
    res = led.verify_chain()
    assert res["ok"] is False and res["first_bad_id"] == 1
    led.close()


# ---- gateway end-to-end (in-process vaults) --------------------------------------
@pytest.fixture()
def gateway_client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from mesh import gateway

    monkeypatch.setattr(gateway, "LEDGER", MeshLedger(tmp_path / "gw.db"))
    monkeypatch.setenv("RAKSHAK_VAULT_SECRETS",
                       '{"delhi":"s-delhi","mumbai":"s-mumbai","jaipur":"s-jaipur"}')

    # fake peer vaults: mumbai has the phone, jaipur has nothing
    def fake_transport(url, body, timeout):
        env = body["envelope"]
        vid = "mumbai" if "8002" in url else "jaipur"
        hits = [{"entity_key": k, "record_count": 2, "record_ids": ["CDR-1", "CDR-2"]}
                for k in env["entity_keys"]] if vid == "mumbai" else []
        return protocol.make_receipt(env, vid, len(hits), hits, SECRETS[vid])

    monkeypatch.setattr(gateway, "TRANSPORT", fake_transport)
    with TestClient(gateway.app) as c:
        yield c


def test_gateway_routes_signs_and_logs(gateway_client):
    env = protocol.make_envelope("delhi", "ENTITY_LOOKUP", ["PHONE:8044997278"], SECRETS["delhi"])
    r = gateway_client.post("/mesh/route", json={"envelope": env})
    assert r.status_code == 200
    data = r.json()
    assert data["all_verified"] is True
    by_vault = {rec["responder_vault"]: rec for rec in data["receipts"]}
    assert by_vault["mumbai"]["hits"] == 1          # mumbai found the phone
    assert by_vault["jaipur"]["hits"] == 0          # jaipur clean
    # every receipt independently verifiable
    assert protocol.verify_receipt(by_vault["mumbai"], SECRETS["mumbai"])
    # exchange logged + chain intact
    assert gateway_client.get("/mesh/verify").json()["ok"] is True
    ex = gateway_client.get("/mesh/receipts", params={"request_id": env["request_id"]}).json()
    assert ex["exchange"]["origin_vault"] == "delhi"


def test_gateway_rejects_bad_signature(gateway_client):
    env = protocol.make_envelope("delhi", "ENTITY_LOOKUP", ["PHONE:8044997278"], SECRETS["delhi"])
    env["entity_keys"] = ["PHONE:9999999999"]       # tamper after signing
    r = gateway_client.post("/mesh/route", json={"envelope": env})
    assert r.status_code == 403


def test_gateway_rejects_unknown_vault(gateway_client):
    env = protocol.make_envelope("patna", "ENTITY_LOOKUP", ["PHONE:8044997278"], "s-patna")
    r = gateway_client.post("/mesh/route", json={"envelope": env})
    assert r.status_code == 403


# ---- vault-side responder + ingest fan-out (single app, mesh mode on) -------------
@pytest.fixture()
def vault_client(monkeypatch):
    """The main API app booted as vault 'delhi' with in-process mesh transport."""
    import importlib
    import api.main as apimod
    from fastapi.testclient import TestClient

    monkeypatch.setenv("RAKSHAK_VAULT_ID", "delhi")
    monkeypatch.setenv("RAKSHAK_VAULT_SECRETS",
                       '{"delhi":"s-delhi","mumbai":"s-mumbai","jaipur":"s-jaipur"}')
    importlib.reload(apimod)                        # re-read env-dependent config

    # peer vaults answer in-process
    def fake_peer(url, body, timeout):
        env = body["envelope"]
        vid = "mumbai" if "8002" in url else "jaipur"
        hits = [{"entity_key": k, "record_count": 5,
                 "record_ids": [f"CDR-{i}" for i in range(5)]}
                for k in env["entity_keys"] if k.startswith("PHONE:")] if vid == "mumbai" else []
        return protocol.make_receipt(env, vid, len(hits), hits, SECRETS[vid])

    def fake_gateway(url, body, timeout):           # gateway fan-out, in-process
        env = body["envelope"]
        receipts = [fake_peer("http://localhost:8002", body, timeout),
                    fake_peer("http://localhost:8003", body, timeout)]
        return {"exchange_id": 1, "request_id": env["request_id"], "receipts": receipts}

    monkeypatch.setattr(apimod, "MESH_TRANSPORT", fake_gateway)
    with TestClient(apimod.app) as c:
        yield c
    monkeypatch.setattr(apimod, "MESH_TRANSPORT", None)
    monkeypatch.delenv("RAKSHAK_VAULT_ID", raising=False)
    importlib.reload(apimod)                        # restore single-node mode


def test_vault_mesh_query_responder(vault_client):
    env = protocol.make_envelope("mumbai", "ENTITY_LOOKUP",
                                 ["PHONE:8044997278"], SECRETS["mumbai"])
    r = vault_client.post("/mesh/query", json={"envelope": env})
    assert r.status_code == 200
    rec = r.json()
    assert rec["responder_vault"] == "delhi"
    assert protocol.verify_receipt(rec, SECRETS["delhi"])
    # summaries are privacy-preserving: ids/counts only, no narrative fields
    for s in rec["hit_summaries"]:
        assert set(s) <= {"entity_key", "record_count", "record_ids"}


def test_vault_mesh_query_rejects_forgery(vault_client):
    env = protocol.make_envelope("mumbai", "ENTITY_LOOKUP",
                                 ["PHONE:8044997278"], SECRETS["mumbai"])
    env["entity_keys"] = ["PHONE:1111111111"]
    assert vault_client.post("/mesh/query", json={"envelope": env}).status_code == 403


def test_ingest_fires_mesh_fanout(vault_client):
    r = vault_client.post("/api/ingest/fir", json={
        "narrative": "Complainant ne bataya ki accused ne +918044997278 se dhamki di. "
                     "Vehicle UP78 GC 4978 spot pe dikha. धारा 354D.",
        "district": "New Delhi", "police_station": "PS Karol Bagh",
        "date": "2026-05-01", "accused_names": ["Test Accused"],
        "complainant_name": "Test Complainant"})
    assert r.status_code == 200
    mesh = r.json()["mesh"]
    assert mesh is not None and mesh["all_verified"] is True
    by_vault = {rec["responder_vault"]: rec for rec in mesh["receipts"]}
    assert by_vault["mumbai"]["hits"] >= 1          # mumbai holds the phone's records
    assert all(rec["verified"] for rec in mesh["receipts"])
