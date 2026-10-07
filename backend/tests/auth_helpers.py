"""Shared test helpers for the DigiLocker e-KYC verified officer session.

Every *write* endpoint (ingest / review / warrant lifecycle) now requires an
officer session, so API tests log in through the simulated DigiLocker e-KYC
bridge before acting. These helpers keep the synthetic credentials out of the
individual test files.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.auth import BRIDGE_MOCK  # noqa: E402

# deterministic demo officer ids per role
IO_OFFICER = "officer.DEL-001"   # Inspector Aryan Malhotra — IO, Delhi (Kotwali)
IO_OFFICER_B = "officer.MUM-001"  # Inspector Sameer Naik — IO, Mumbai
SP_OFFICER = "officer.DEL-003"   # SP Vikram Rawat — SP (countersign), Delhi Range
FORENSIC_OFFICER = "officer.MUM-002"


def login(client, officer_id: str = IO_OFFICER) -> dict:
    """Log an officer in through the simulated e-KYC bridge; return bearer headers."""
    officers = client.get("/api/auth/officers").json()["officers"]
    o = next(x for x in officers if x["id"] == officer_id)
    assert o["demo"], "test registry must be the sim bridge"
    r = client.post("/api/auth/login", json={
        "aadhaar": o["demo"]["aadhaar"], "otp": o["demo"]["otp"],
        "purpose": "test-run"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["authentication"]["bridge"] == BRIDGE_MOCK
    return {"Authorization": f"Bearer {body['token']}"}


def officer_headers(client, officer_id: str = IO_OFFICER) -> dict:
    """Bearer headers for a specific officer (alias that reads clearly in tests)."""
    return login(client, officer_id)


def io_headers(client) -> dict:
    return login(client, IO_OFFICER)


def sp_headers(client) -> dict:
    return login(client, SP_OFFICER)


def forensic_headers(client) -> dict:
    return login(client, FORENSIC_OFFICER)