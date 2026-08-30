"""Vault runtime configuration — single-node by default, mesh mode via env.

Single-node mode (default, all 92 tests run this way):
    no env vars set → one graph, full bench, no mesh traffic.

Mesh mode (demo):
    RAKSHAK_VAULT_ID=delhi            — this instance's vault identity
    RAKSHAK_BENCH_DIR=output-vaults/delhi
    RAKSHAK_GATEWAY_URL=http://localhost:8000
    RAKSHAK_VAULT_SECRETS={"delhi":"...","mumbai":"...","jaipur":"..."}
    RAKSHAK_PEER_VAULTS={"mumbai":"http://localhost:8002","jaipur":"http://localhost:8003"}

Secrets in env, never in the repo. Demo secrets are stand-ins for NIC-issued
certificates — disclosed as such in the pitch.
"""
from __future__ import annotations

import json
import os

_DEMO_SECRETS = {"delhi": "demo-delhi", "mumbai": "demo-mumbai", "jaipur": "demo-jaipur"}


def vault_id() -> str | None:
    v = os.getenv("RAKSHAK_VAULT_ID", "").strip()
    return v or None


def mesh_enabled() -> bool:
    return vault_id() is not None


def gateway_url() -> str:
    return os.getenv("RAKSHAK_GATEWAY_URL", "http://localhost:8000").rstrip("/")


def vault_secrets() -> dict[str, str]:
    raw = os.getenv("RAKSHAK_VAULT_SECRETS", "").strip()
    if raw:
        try:
            return {k: str(v) for k, v in json.loads(raw).items()}
        except json.JSONDecodeError:
            pass
    # demo fallback — disclosed in docs; production injects real per-vault keys
    return dict(_DEMO_SECRETS)


def my_secret() -> str:
    return vault_secrets().get(vault_id() or "", "demo-unknown")


def peer_vaults() -> dict[str, str]:
    raw = os.getenv("RAKSHAK_PEER_VAULTS", "").strip()
    if raw:
        try:
            return {k: str(v).rstrip("/") for k, v in json.loads(raw).items()}
        except json.JSONDecodeError:
            pass
    defaults = {"delhi": "http://localhost:8001",
                "mumbai": "http://localhost:8002",
                "jaipur": "http://localhost:8003"}
    vid = vault_id()
    return {k: v for k, v in defaults.items() if k != vid}
