"""Evidence auto-resolution — paste a document or uplink a PDF and every person
in it is resolved against the vault's case graph automatically, using the same
Hybrid identity resolution engine as the manual comparator.

What is deliberately NOT here: any claim of a neural IndicXlit model on this
box. The engine is whatever ``engine_name()`` returns (today:
``builtin-rule-romanizer`` — the neural export cannot run offline here and we
will not fake it). Tight pronunciation/attribute matching still resolves
cross-script names deterministically via the same pipeline the case graph uses.

Output is a *lead table*, not a verdict: every row carries the best graph match,
the decision (MATCH / UNCERTAIN / REJECT), confidence, and the phonetic/name
basis. ``route_to_review`` flags the ambiguous rows for human review — exactly
the HITL posture.
"""
from __future__ import annotations

from . import indic_xlit as _xlit
from .features import PersonRef, WEIGHTS, score_pair

MAX_CANDIDATES = 400


def engine_name() -> str:
    """Expose the actual transliteration engine honestly (mirror of resolve)."""
    return _xlit.engine_name()


def extract_person_surfaces(text: str) -> list[dict]:
    """Persons found in a document via the case-graph regex NER, span-annotated."""
    from api.ingest import extract_entities  # local import: no import cycle

    seen: set[str] = set()
    out: list[dict] = []
    for e in extract_entities(text):
        if e.kind != "PERSON":
            continue
        key = e.normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "surface": e.surface,
            "normalized": e.normalized,
            "span": list(e.span),
        })
    return out


def auto_resolve(graph, text: str) -> dict:
    persons = extract_person_surfaces(text)

    # candidate index: every PERSON already living in the case graph
    candidates = [
        n for n in graph.nodes.values()
        if getattr(n, "type", "") == "PERSON"
    ][:MAX_CANDIDATES]

    rows: list[dict] = []
    for p in persons:
        a = PersonRef.build("evidence", p["surface"])
        best = None
        for n in candidates:
            b = PersonRef.build(n.label, n.label)
            m = score_pair(a, b)
            if best is None or m.score > best[1].score:
                best = (n, m)
        if best is None:
            rows.append({**p, "match": None, "decision": "NEW",
                         "confidence": 0.0, "route_to_review": False})
            continue
        n, m = best
        decision = {"MATCH": "MATCH", "UNCERTAIN": "UNCERTAIN",
                    "REJECT": "REJECT"}.get(m.decision, m.decision)
        hard_veto = m.decision == "REJECT" and m.parts.get("name", 0) >= 0.8
        rows.append({
            **p,
            "match": {"id": n.id, "label": n.label},
            "decision": decision,
            "confidence": round(m.score, 3),
            "basis": {"name": round(m.parts["name"], 3),
                      "phonetic": round(m.parts["phonetic"], 3)},
            "veto": "hard attribute conflict" if hard_veto else None,
            "route_to_review": decision == "UNCERTAIN",
        })

    rows.sort(key=lambda r: (-r["confidence"], r["surface"].casefold()))
    return {
        "engine": engine_name(),
        "count": len(persons),
        "candidate_count": len(candidates),
        "rows": rows,
        "weights": {("attribute" if k == "attr" else k): v for k, v in WEIGHTS.items()},
        "disclosure": (
            "auto-resolution: regex NER → Hybrid identity scoring (name · phonetic · "
            f"attribute) against the case graph; engine = {engine_name()}. Output is a "
            "lead table — every UNCERTAIN row routes to human review before any link. "
            "No neural IndicXlit is claimed on this box."
        ),
    }