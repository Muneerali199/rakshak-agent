"""Blindspot analysis — what the system does NOT know about an entity.

Most intelligence software projects false completeness. RAKSHAK-NET does the
opposite: every entity carries an honest *corroboration profile* — which evidence
layers are missing, how much of the network is inferred (vs observed), how many
independent sources corroborate it, and where the temporal record has gaps.

This is investigative humility as a feature: an officer should see the blindspots
before they stake a case on the graph.
"""
from __future__ import annotations

from datetime import datetime

ALL_LAYERS = ("communication", "financial", "spatial")
GAP_DAYS = 14


def _parse_ts(ts: str):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def analyze_blindspot(graph, entity_id: str) -> dict:
    """Return the corroboration profile + human-readable gaps for one entity."""
    node = graph.nodes.get(entity_id)
    if node is None:
        raise KeyError(entity_id)

    edge_ids = graph._adj.get(entity_id, ())          # noqa: SLF001
    edges = [graph.edges[eid] for eid in edge_ids]

    layers_present = {e.layer for e in edges}
    missing_layers = [l for l in ALL_LAYERS if l not in layers_present]

    observed = [e for e in edges if e.creation_method == "EXTRACTED"]
    inferred = [e for e in edges if e.creation_method != "EXTRACTED"]

    # independent corroboration = distinct source records behind the edges
    sources = {e.provenance for e in observed if e.provenance and
               not e.provenance.startswith("co-mention:")}

    # temporal coverage: largest gap between consecutive observed timestamps
    times = sorted(t for t in (_parse_ts(e.timestamp) for e in observed) if t)
    max_gap_days = 0
    gap_between = None
    for a, b in zip(times, times[1:]):
        gap = (b - a).days
        if gap > max_gap_days:
            max_gap_days, gap_between = gap, (a.date().isoformat(), b.date().isoformat())

    # ── corroboration score (honest, explainable deductions from 100) ──
    score = 100
    gaps: list[str] = []
    if missing_layers:
        deduction = 25 * len(missing_layers)
        score -= deduction
        gaps.append("No " + " / ".join(missing_layers) +
                    " layer evidence — the network may extend beyond what is visible")
    if edges and not observed:
        score -= 30
        gaps.append("Every connection here is inferred, none observed — "
                    "needs corroboration before it can support action")
    elif edges and len(inferred) > len(observed):
        score -= 15
        gaps.append(f"Mostly inferred links ({len(inferred)} inferred vs {len(observed)} observed)")
    if len(sources) <= 1:
        score -= 20
        gaps.append("Single-source corroboration — one record stream carries this entity" if sources
                    else "No independent source records corroborate this entity yet")
    if max_gap_days >= GAP_DAYS and gap_between:
        score -= 10
        gaps.append(f"{max_gap_days}-day silence between {gap_between[0]} and {gap_between[1]} — "
                    "activity may have moved off-record")
    score = max(0, score)

    return {
        "entity_id": entity_id,
        "label": node.label,
        "corroboration_score": score,
        "stats": {
            "edges": len(edges),
            "observed": len(observed),
            "inferred": len(inferred),
            "layers_present": sorted(layers_present),
            "missing_layers": missing_layers,
            "independent_sources": len(sources),
            "max_gap_days": max_gap_days,
        },
        "gaps": gaps,
        "verdict": ("well corroborated" if score >= 75 else
                    "partially corroborated — investigate gaps" if score >= 45 else
                    "thin evidence — treat as exploratory only"),
    }
