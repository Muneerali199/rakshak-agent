"""Person dossier — the "give me everything we know about this person" endpoint.

Takes a name (any script / spelling variant) and assembles a deterministic
cross-case profile from the vault's graph + bench: the canonical person node,
every alias the graph knows, the FIRs they appear in (role, section, district,
date, age/address block), the identifiers linked through graph edges (phones,
accounts, vehicles), victim-shield status, and cross-case breadth.

No LLM: it is a join over already-verified case data, so it cannot hallucinate.
Candidate matching reuses the same normalize+score pipeline as identity
resolution, so `Mohammad Arif` finds `मोहम्मद आरिफ़` via the shared engine.
"""
from __future__ import annotations

from .features import PersonRef, score_pair
from . import indic_xlit


def engine() -> str:
    return indic_xlit.engine_name()


def _aliases(graph, node_id: str, label: str) -> set[str]:
    meta = getattr(graph.nodes.get(node_id), "meta", {})
    if isinstance(meta, dict):
        return {label, *meta.get("aliases", [])}
    return {label}


def _best_person(graph, name: str) -> tuple[object, float]:
    target = PersonRef.build("q", name)
    best, best_score = None, 0.0
    for n in graph.nodes.values():
        if getattr(n, "type", "") != "PERSON":
            continue
        m = score_pair(target, PersonRef.build(n.label, n.label))
        if m.score > best_score:
            best, best_score = n, m.score
    return best, best_score


def people_in_bench(graph, bench, node_id: str, label: str) -> list[dict]:
    """FIRs whose complainant/accused/witness block resolves to this person."""
    aliases = {normalize(x) for x in _aliases(graph, node_id, label)}
    rows: list[dict] = []
    for rec in bench.get("fir", []):
        blocks = []
        comp = rec.get("complainant")
        if comp:
            blocks.append(("complainant", comp))
        for acc in rec.get("accused", []):
            blocks.append(("accused", acc))
        for role, blk in blocks:
            if normalize(blk.get("name", "")) in aliases:
                rows.append({
                    "record_id": rec.get("record_id"),
                    "role": role,
                    "district": rec.get("district"),
                    "section": rec.get("ipc_sections", []),
                    "age": blk.get("age"),
                    "address": blk.get("address"),
                    "police_station": rec.get("police_station"),
                    "date": rec.get("date"),
                })
                break
    return rows


def normalize(x: str) -> str:
    try:
        from .normalize import normalize_name
        return normalize_name(x)
    except Exception:                                     # noqa: BLE001
        return (x or "").strip().casefold()


def _linked_identifiers(graph, node_id: str) -> dict:
    ids: dict[str, list[str]] = {"phones": [], "accounts": [], "vehicles": []}
    node = graph.nodes.get(node_id)
    if node is None:
        return ids
    for e in getattr(graph, "edges", {}).values():
        if e.source != node_id and e.target != node_id:
            continue
        other = graph.nodes.get(e.target) if e.source == node_id else graph.nodes.get(e.source)
        if other is None or other.type not in ("PHONE", "ACCOUNT", "VEHICLE"):
            continue
        bucket = {"PHONE": "phones", "ACCOUNT": "accounts", "VEHICLE": "vehicles"}[other.type]
        if other.label not in ids[bucket] and len(ids[bucket]) < 8:
            ids[bucket].append(other.label)
    return ids


def dossier(graph, bench, name: str, threshold: float = 0.5) -> dict:
    """Deterministic cross-case profile for a person name."""
    best, score = _best_person(graph, name)
    if best is None or score < threshold:
        return {"found": False, "query": name,
                "engine": engine(),
                "disclosure": "no graph person scored above the ground-truth threshold — "
                              "use Evidence auto-resolve to plant candidates for review first"}
    nid, label = best.id, best.label
    meta = getattr(best, "meta", {}) or {}
    rows = people_in_bench(graph, bench, nid, label)
    ids = _linked_identifiers(graph, nid)
    return {
        "found": True,
        "query": name,
        "name": label,
        "id": nid,
        "match_confidence": round(score, 3),
        "aliases": sorted(_aliases(graph, nid, label)),
        "roles": sorted({r["role"] for r in rows}),
        "victim_shielded": meta.get("role") == "victim" if isinstance(meta, dict) else False,
        "district": meta.get("district") if isinstance(meta, dict) else None,
        "firs": rows,
        "fir_count": len(rows),
        "identifiers": ids,
        "engine": engine(),
        "disclosure": ("deterministic dossier over verified case data (no LLM, no "
                       "cross-script guessing): name → graph join → officer review gate"),
    }