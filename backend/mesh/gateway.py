"""Mesh Gateway — the NPCI-style switch between district vaults.

Routes signed query envelopes from one vault to its peers, collects signed
receipts, verifies every signature, and appends a hash-chained record of the
exchange to its own ledger. **The gateway stores exchange metadata only — never
case data.** Run it:

    uvicorn mesh.gateway:app --port 8000
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import protocol
from .client import httpx_transport, Transport
from .ledger import MeshLedger

BASE_DIR = Path(__file__).resolve().parent.parent

# vault registry — in production this is the Sahamati-style central registry
# with NIC-issued identities; demo uses localhost peers + env-overridable map.
_DEFAULT_PEERS = {"delhi": "http://localhost:8001",
                  "mumbai": "http://localhost:8002",
                  "jaipur": "http://localhost:8003"}

LEDGER = MeshLedger(BASE_DIR / "output-vaults" / "gateway" / "mesh_ledger.db")

# test hook: gateway fan-out transport is injectable (no sockets in tests)
TRANSPORT: Transport = httpx_transport


def _secrets() -> dict[str, str]:
    from api.vault_config import vault_secrets
    return vault_secrets()


def _peers() -> dict[str, str]:
    raw = os.getenv("RAKSHAK_MESH_VAULTS", "").strip()
    if raw:
        import json
        try:
            return {k: str(v).rstrip("/") for k, v in json.loads(raw).items()}
        except json.JSONDecodeError:
            pass
    return dict(_DEFAULT_PEERS)


class RouteRequest(BaseModel):
    envelope: dict


app = FastAPI(title="RAKSHAK Mesh Gateway", version="0.1.0")


@app.get("/mesh/health")
def mesh_health() -> dict:
    return {"status": "ok", "vaults": sorted(_peers()), "ledger": LEDGER.verify_chain()}


@app.post("/mesh/route")
def mesh_route(req: RouteRequest) -> dict:
    """Receive a signed envelope, fan it out to peer vaults, return signed receipts."""
    env = req.envelope
    origin = env.get("origin_vault", "")
    secrets = _secrets()
    if origin not in secrets:
        raise HTTPException(403, f"unknown origin vault '{origin}'")
    if not protocol.verify_envelope(env, secrets[origin]):
        raise HTTPException(403, "envelope signature verification failed")

    receipts: list[dict] = []
    all_ok = True
    for vid, url in _peers().items():
        if vid == origin:
            continue
        try:
            rec = TRANSPORT(f"{url}/mesh/query", {"envelope": env}, 3.0)
        except Exception as exc:  # noqa: BLE001 — a down vault must not block others
            receipts.append({
                "request_id": env["request_id"], "responder_vault": vid,
                "query_type": env["query_type"], "hits": 0, "hit_summaries": [],
                "timestamp": "", "signature": "",
                "error": f"unreachable: {exc.__class__.__name__}",
            })
            all_ok = False
            continue
        if not protocol.verify_receipt(rec, secrets.get(vid, "")):
            rec = dict(rec, error="receipt signature verification failed")
            all_ok = False
        receipts.append(rec)

    record = LEDGER.log_exchange(env, receipts, envelope_sig_ok=True, receipt_sig_ok=all_ok)
    return {"exchange_id": record["id"], "request_id": env["request_id"],
            "receipts": receipts, "all_verified": all_ok}


@app.get("/mesh/receipts")
def mesh_receipts(request_id: str | None = None, limit: int = 50) -> dict:
    """Inspect exchange receipts — the visible proof that queries traveled."""
    if request_id:
        ex = LEDGER.get_exchange(request_id)
        if ex is None:
            raise HTTPException(404, f"exchange '{request_id}' not found")
        return {"exchange": ex}
    return {"exchanges": LEDGER.all_exchanges(limit=limit)}


@app.get("/mesh/verify")
def mesh_verify() -> dict:
    """Verify the exchange ledger — tamper-evidence for cross-district traffic."""
    return {**LEDGER.verify_chain(),
            "disclosure": "hash-chained exchange ledger — the switch stores receipts, "
                          "never case data; tampering with any exchange breaks the chain"}
