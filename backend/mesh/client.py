"""Vault-side mesh client — fan a query out through the gateway, verify receipts.

Transport is injectable so tests never open sockets: production uses httpx
(already an API dependency), tests pass an in-process callable with the same
signature. All failures degrade gracefully — mesh unavailability must never
break local policing work; the response simply carries an error note.
"""
from __future__ import annotations

from typing import Callable

from . import protocol

# transport: (url: str, json_body: dict, timeout: float) -> dict
Transport = Callable[[str, dict, float], dict]


def httpx_transport(url: str, json_body: dict, timeout: float) -> dict:
    import httpx  # local import: already an api-layer dependency
    resp = httpx.post(url, json=json_body, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def fanout_entity_lookup(origin_vault: str, entity_keys: list[str], gateway_url: str,
                         secrets: dict[str, str], transport: Transport | None = None,
                         timeout: float = 3.0) -> dict:
    """Send a signed ENTITY_LOOKUP envelope to the gateway; return verified receipts.

    ``secrets`` maps vault-id → secret: the envelope is signed with the origin's
    secret; each returned receipt is verified against its *responder's* secret
    (in production: per-vault NIC certificates from the registry).

    Returns ``{request_id, receipts, all_verified, error}`` — ``receipts`` are the
    gateway-returned, signature-verified vault responses (privacy-preserving
    summaries only). On any transport/verification failure, ``error`` explains and
    ``receipts`` holds whatever verified before the failure (possibly empty).
    """
    transport = transport or httpx_transport
    envelope = protocol.make_envelope(origin_vault, "ENTITY_LOOKUP", entity_keys,
                                      secrets[origin_vault])
    out = {"request_id": envelope["request_id"], "receipts": [], "all_verified": False,
           "error": None, "exchange_id": None}
    try:
        resp = transport(f"{gateway_url}/mesh/route", {"envelope": envelope}, timeout)
    except Exception as exc:  # noqa: BLE001 — degrade gracefully, policing continues
        out["error"] = f"mesh gateway unreachable: {exc.__class__.__name__}"
        return out

    receipts = resp.get("receipts", [])
    out["exchange_id"] = resp.get("exchange_id")
    for rec in receipts:
        rec = dict(rec)
        rec["verified"] = protocol.verify_receipt(rec, secrets.get(rec.get("responder_vault", ""), ""))
        out["receipts"].append(rec)
    out["all_verified"] = bool(out["receipts"]) and all(r["verified"] for r in out["receipts"])
    if not out["all_verified"] and out["receipts"]:
        out["error"] = "one or more receipts failed signature verification"
    return out
