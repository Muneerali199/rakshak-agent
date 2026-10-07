"""Warrant Gate tests — DEPA consent artifacts with four-eyes countersignature.

Covers the constitutional rules in code: dual signatures (requester ≠ approver),
seniority (SP+), scoped access, expiry, revocation, and a tamper-evident ledger —
plus the API-level gate on protected evidence.
"""
from __future__ import annotations

import pytest

import auth_helpers
from api.warrants import WarrantStore


@pytest.fixture()
def store(tmp_path):
    s = WarrantStore(str(tmp_path / "warrants.db"))
    yield s
    s.close()


def test_request_approve_use_flow(store):
    w = store.request("edge:E-1", "io.sharma", "INSPECTOR", "victim identity needed for chargesheet")
    assert w["status"] == "PENDING"
    ok = store.approve(w["warrant_id"], "sp.rao", "SP")
    assert ok["ok"] is True and ok["status"] == "APPROVED"
    chk = store.check(w["warrant_id"], "edge:E-1")
    assert chk["ok"] is True
    # REQUEST + APPROVE + USE all ledgered
    events = store.all_events()
    assert [e["event"] for e in reversed(events)] == ["REQUEST", "APPROVE", "USE"]
    assert store.verify_chain()["ok"] is True


def test_self_approval_denied(store):
    w = store.request("edge:E-1", "io.sharma", "INSPECTOR", "x")
    out = store.approve(w["warrant_id"], "io.sharma", "SP")   # same person
    assert out["ok"] is False and "self-approval" in out["error"]
    assert store.check(w["warrant_id"], "edge:E-1", log_use=False)["ok"] is False


def test_junior_approver_denied(store):
    w = store.request("edge:E-1", "io.sharma", "INSPECTOR", "x")
    out = store.approve(w["warrant_id"], "si.verma", "SI")    # below SP
    assert out["ok"] is False and "SP" in out["error"]


def test_scope_and_revocation_enforced(store):
    w = store.request("edge:E-1", "io.sharma", "INSPECTOR", "x")
    store.approve(w["warrant_id"], "sp.rao", "SP")
    # wrong scope → denied
    assert store.check(w["warrant_id"], "edge:E-2", log_use=False)["ok"] is False
    # revoke → denied
    store.revoke(w["warrant_id"], "sp.rao", "SP")
    assert store.check(w["warrant_id"], "edge:E-1", log_use=False)["ok"] is False


def test_ledger_tamper_breaks_chain(store):
    w = store.request("edge:E-1", "io.sharma", "INSPECTOR", "x")
    store.approve(w["warrant_id"], "sp.rao", "SP")
    store._conn.execute("UPDATE warrants SET approver_id='mallory' WHERE id = 2")
    res = store.verify_chain()
    assert res["ok"] is False and res["first_bad_id"] == 2


# ---- API-level gate -------------------------------------------------------------
@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    import api.main as apimod
    with TestClient(apimod.app) as c:
        yield c


def _shielded_edge_id(client) -> str:
    """Find an edge touching a victim node (shielded) in the live graph."""
    ents = client.get("/api/entities", params={"type": "PERSON", "limit": 50}).json()
    victim = next((e for e in ents if e.get("meta", {}).get("role") == "victim"), None)
    assert victim, "benchmark must contain at least one victim node"
    sg = client.get("/api/graph/subgraph",
                    params={"entity_id": victim["id"], "depth": 1}).json()
    assert sg["edges"], "victim must have at least one edge"
    return sg["edges"][0]["id"]


def test_evidence_masked_without_warrant(client):
    eid = _shielded_edge_id(client)
    ev = client.get(f"/api/evidence/{eid}").json()
    assert ev["victim_shield"] is True
    assert "[PROTECTED VICTIM]" in ev["claim"]
    assert ev["warrant_id"] is None


def test_evidence_unmasked_with_dual_signed_warrant(client):
    eid = _shielded_edge_id(client)
    # request as the IO…
    io = auth_helpers.io_headers(client)
    w = client.post("/api/warrants", json={
        "scope": f"edge:{eid}", "requester_id": "ignored-client-value",
        "requester_role": "INSPECTOR", "reason": "chargesheet identity confirmation"},
        headers=io).json()
    assert w["ok"] is True
    # …countersigned by a different SP (identity comes from the session, not the body)
    sp = auth_helpers.sp_headers(client)
    ap = client.post(f"/api/warrants/{w['warrant_id']}/approve",
                     json={"approver_id": "ignored-client-value", "approver_role": "SP"},
                     headers=sp).json()
    assert ap["ok"] is True
    # invalid warrant id → 403
    assert client.get(f"/api/evidence/{eid}", params={"warrant_id": "W-BOGUS"}).status_code == 403
    # valid warrant → unmasked, cited
    ev = client.get(f"/api/evidence/{eid}", params={"warrant_id": w["warrant_id"]}).json()
    assert "[PROTECTED VICTIM]" not in ev["claim"]
    assert ev["warrant_id"] == w["warrant_id"]
    # the access itself was ledgered
    events = client.get("/api/warrants").json()["events"]
    assert any(e["event"] == "USE" and e["warrant_id"] == w["warrant_id"] for e in events)
    assert client.get("/api/warrants/verify").json()["ok"] is True
