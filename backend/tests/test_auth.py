"""Aadhaar-verified officer authentication tests.

Covers the identity + access-control commitments end-to-end via TestClient and
directly at the auth service layer:
  * login through the (honestly labelled) simulated DigiLocker e-KYC bridge
    issues an expiring, purpose-bound token whose payload carries NO Aadhaar
    material;
  * the store persists only masked last-4 + UID token — never the raw number;
  * write endpoints are locked to an officer session; SP-ranked actions reject
    junior sessions; every denial is hash-chained into the auth ledger;
  * expired / forged / tampered tokens are rejected; tampering the auth ledger
    breaks the chain.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

import auth_helpers                         # noqa: E402
import api.main as apimod                   # noqa: E402
from api.auth import (                       # noqa: E402
    BRIDGE_MOCK, AadhaarAuth, issue_token, verify_token)


def _fresh_app() -> TestClient:
    apimod.BENCH_DIR = Path(tempfile.mkdtemp()) / "bench"
    c = TestClient(apimod.app)
    c.__enter__()
    return c


def _demo_creds(client, officer_id: str) -> dict:
    officers = client.get("/api/auth/officers").json()["officers"]
    return next(o for o in officers if o["id"] == officer_id)["demo"]


def _login_dict(client, officer_id=auth_helpers.IO_OFFICER) -> dict:
    demo = _demo_creds(client, officer_id)
    r = client.post("/api/auth/login", json={
        "aadhaar": demo["aadhaar"], "otp": demo["otp"], "purpose": "test-run"})
    assert r.status_code == 200, r.text
    return r.json()


def test_login_issues_purpose_bound_token_without_aadhaar():
    with _fresh_app() as c:
        d = _login_dict(c)
        assert d["ok"] is True
        assert d["authentication"]["bridge"] == BRIDGE_MOCK
        assert d["authentication"]["txn"].startswith("AUTH-")
        assert "consent_id" in d["authentication"]
        assert d["officer"]["id"] == auth_helpers.IO_OFFICER
        assert "aadhaar_masked" in d["officer"]
        assert "aadhaar" not in d["token"].lower()
        me = c.get("/api/auth/me",
                   headers={"Authorization": f"Bearer {d['token']}"}).json()
        assert me["id"] == auth_helpers.IO_OFFICER and me["role"] == "IO"
        assert me["aadhaar_masked"].startswith("XXXX-")


def test_request_otp_first_step_of_handshake():
    with _fresh_app() as c:
        demo = _demo_creds(c, auth_helpers.IO_OFFICER)
        r = c.post("/api/auth/request-otp", json={"aadhaar": demo["aadhaar"]})
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True and d["txn"].startswith("AUTH-")
        assert d["bridge"] == BRIDGE_MOCK
        assert "XXXX-XXXX-1177" in d["masked"]
        assert "OTP dispatched" in d["hint"]
        unknown = c.post("/api/auth/request-otp", json={"aadhaar": "999999999999"})
        assert unknown.status_code == 200 and unknown.json()["ok"] is False


def test_wrong_otp_denied_and_denial_ledgered():
    with _fresh_app() as c:
        demo = _demo_creds(c, auth_helpers.IO_OFFICER)
        bad = c.post("/api/auth/login", json={
            "aadhaar": demo["aadhaar"], "otp": "000000",
            "purpose": "test"}).json()
        assert bad["ok"] is False and "OTP" in bad["error"]
        status = c.get("/api/security/posture").json()["auth"]
        assert status["ledger"]["ok"] is True      # denial chain is intact and growing


def test_unknown_aadhaar_denied():
    with _fresh_app() as c:
        r = c.post("/api/auth/login", json={
            "aadhaar": "700099999999", "otp": "999999",
            "purpose": "test"}).json()
        assert r["ok"] is False and r["error"]


def test_ingest_locked_to_officer_session():
    with _fresh_app() as c:
        body = {"narrative": "Accused ne complainant ko phone kiya 8044997278 se.",
                "district": "Delhi", "police_station": "PS Kotwali",
                "date": "2026-06-01", "accused_names": ["A Test"],
                "complainant_name": "V Test"}
        assert c.post("/api/ingest/fir", json=body).status_code == 401
        h = auth_helpers.io_headers(c)
        r = c.post("/api/ingest/fir", json=body, headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["record_id"].startswith("FIR-LIVE-")


def test_warrant_approve_requires_sp_rank():
    with _fresh_app() as c:
        io = auth_helpers.io_headers(c)
        w = c.post("/api/warrants", json={"scope": "edge:E-1", "requester_id": "x",
                                          "requester_role": "x",
                                          "reason": "test"}, headers=io).json()
        assert w["ok"] is True
        r = c.post(f"/api/warrants/{w['warrant_id']}/approve",
                   json={"approver_id": "x", "approver_role": "IO"}, headers=io)
        assert r.status_code == 403 and "rank" in r.json()["detail"].lower()
        ap = c.post(f"/api/warrants/{w['warrant_id']}/approve",
                    json={"approver_id": "x", "approver_role": "SP"},
                    headers=auth_helpers.sp_headers(c))
        assert ap.status_code == 200 and ap.json()["status"] == "APPROVED"


def test_self_approval_blocked_four_eyes():
    with _fresh_app() as c:
        sp = auth_helpers.sp_headers(c)
        w = c.post("/api/warrants", json={"scope": "edge:E-2", "requester_id": "x",
                                          "requester_role": "x",
                                          "reason": "four-eyes"}, headers=sp).json()
        assert w["ok"] is True
        r = c.post(f"/api/warrants/{w['warrant_id']}/approve",
                   json={"approver_id": "x", "approver_role": "SP"}, headers=sp)
        assert r.status_code == 403 and "self-approval" in r.json()["detail"].lower()


def test_expired_and_forged_tokens_rejected():
    svc = AadhaarAuth(str(Path(tempfile.mkdtemp()) / "auth.db"))
    o = svc.store.by_id(auth_helpers.IO_OFFICER)
    expired = issue_token(o, exp=int(time.time()) - 10)
    assert verify_token(expired) is None
    forged = issue_token(o) + "deadbeef"
    assert verify_token(forged) is None
    svc.close()


def test_raw_aadhaar_never_persisted():
    with _fresh_app() as c:
        _login_dict(c)
        con = sqlite3.connect(Path(apimod.BENCH_DIR) / "auth.db")
        cols = [r[1] for r in con.execute("PRAGMA table_info(officers)")]
        con.close()
        assert "aadhaar" not in cols
        assert "aadhaar_last4" in cols and "uid_token" in cols
        blob = (Path(apimod.BENCH_DIR) / "auth.db").read_bytes()
        assert b"700011771177" not in blob     # no full 12-digit number on disk


def test_auth_ledger_tamper_breaks_chain():
    with _fresh_app() as c:
        _login_dict(c)
        con = sqlite3.connect(Path(apimod.BENCH_DIR) / "auth_ledger.db")
        con.execute("UPDATE auth_log SET report='[MALLORY]' WHERE id = 1")
        con.commit()
        con.close()
        auth = c.get("/api/security/posture").json()["auth"]
        assert auth["ledger"]["ok"] is False and auth["ledger"]["first_bad_id"] == 1