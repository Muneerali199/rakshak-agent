"""Mesh wire protocol — signed query envelopes and signed response receipts.

Two artifacts travel between vaults (never raw case data):

* **QueryEnvelope** — origin vault → (gateway) → peer vaults:
  ``{request_id, origin_vault, query_type, entity_keys, timestamp}`` + HMAC signature.
* **QueryReceipt** — peer vault → (gateway) → origin vault:
  ``{request_id, responder_vault, hits, hit_summaries, timestamp}`` + HMAC signature.

``hit_summaries`` are privacy-preserving by design: counts and record ids only —
no narratives, no names. The data stays in the district; only the *answer* travels.

Signing: HMAC-SHA256 over canonical JSON (same convention as graph.build / ledger).
Demo deployments use a shared per-vault secret; production swaps this for NIC-issued
certificates — the envelope shape is unchanged.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone

_ENVELOPE_FIELDS = ("request_id", "origin_vault", "query_type", "entity_keys", "timestamp")
_RECEIPT_FIELDS = ("request_id", "responder_vault", "query_type", "hits", "hit_summaries", "timestamp")


def canonical_json(payload) -> str:
    """Deterministic JSON — the same convention used by the evidence ledger."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def _sign_fields(payload: dict, fields: tuple[str, ...], secret: str) -> str:
    body = canonical_json({k: payload[k] for k in fields})
    return hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()


def _verify_fields(payload: dict, fields: tuple[str, ...], signature: str, secret: str) -> bool:
    expected = _sign_fields(payload, fields, secret)
    return hmac.compare_digest(expected, signature or "")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_request_id() -> str:
    return "req-" + uuid.uuid4().hex[:12]


# ---- envelopes ---------------------------------------------------------------
def make_envelope(origin_vault: str, query_type: str, entity_keys: list[str],
                  secret: str, request_id: str | None = None) -> dict:
    """Build a signed query envelope ready to hand to the gateway."""
    env = {
        "request_id": request_id or new_request_id(),
        "origin_vault": origin_vault,
        "query_type": query_type,                    # e.g. "ENTITY_LOOKUP"
        "entity_keys": sorted(entity_keys),          # deterministic ordering for signing
        "timestamp": _now(),
    }
    env["signature"] = _sign_fields(env, _ENVELOPE_FIELDS, secret)
    return env


def verify_envelope(env: dict, secret: str) -> bool:
    """True iff the envelope's signature matches its signed fields."""
    if not all(k in env for k in _ENVELOPE_FIELDS):
        return False
    return _verify_fields(env, _ENVELOPE_FIELDS, env.get("signature", ""), secret)


# ---- receipts ----------------------------------------------------------------
def make_receipt(envelope: dict, responder_vault: str, hits: int,
                 hit_summaries: list[dict], secret: str) -> dict:
    """Build a signed response receipt for a verified envelope."""
    rec = {
        "request_id": envelope["request_id"],
        "responder_vault": responder_vault,
        "query_type": envelope["query_type"],
        "hits": hits,
        "hit_summaries": hit_summaries,
        "timestamp": _now(),
    }
    rec["signature"] = _sign_fields(rec, _RECEIPT_FIELDS, secret)
    return rec


def verify_receipt(rec: dict, secret: str) -> bool:
    if not all(k in rec for k in _RECEIPT_FIELDS):
        return False
    return _verify_fields(rec, _RECEIPT_FIELDS, rec.get("signature", ""), secret)
