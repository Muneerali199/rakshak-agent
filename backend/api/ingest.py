"""Live FIR ingestion — paste a complaint, watch it become intelligence.

This is the demo's core moment: an investigator pastes raw FIR narrative text
(Hindi / English / Hinglish) and the system:

  1. extracts entities with regex NER (phones, bank accounts, vehicles, IPC sections,
     names, locations) — deterministic, no LLM, fully auditable;
  2. checks every extracted entity against the existing case graph for
     **cross-district linkage** (the same phone/account/vehicle/person appearing in
     FIRs from *other* districts — the unsolved problem of Indian policing);
  3. merges the new FIR into the in-memory graph so the UI updates live;
  4. flags **victim-shield** status of any complainant (Women Safety policy).

Everything is stdlib-only. Extraction patterns are intentionally simple and every
extracted span is returned with its offsets so the UI can highlight the source text —
the same evidence-grounding contract as the rest of the platform.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from resolve.io import deterministic_key

# --------------------------------------------------------------------------- #
# Regex NER — Indian formats, deterministic, every match span-cited
# --------------------------------------------------------------------------- #

# Indian mobile: +91-98xxxxxxxx / +91 98xxxxxxxx / 98xxxxxxxx (10 digits, 6-9 start)
# (?!...): not when the digits are actually the tail of an AC… bank account token
_PHONE_RE = re.compile(r"(?<![A-Z0-9])(?:\+91[\s-]?)?([6-9]\d{9})(?!\d)")

# Bank account tokens: AC + 10 digits (synthgen format), or "A/c" + digits
_ACCOUNT_RE = re.compile(r"\b(AC\d{10})\b|A/?c\s*(?:no\.?\s*)?(\d{9,14})", re.IGNORECASE)

# Indian vehicle registration: DL3C9423 / UP 78 GC 4978 / MH-12-AB-1234
_VEHICLE_RE = re.compile(
    r"\b([A-Z]{2}[\s-]?\d{1,2}[\s-]?[A-Z]{1,3}[\s-]?\d{4})\b"
)

# IPC / BNS sections — require an explicit section marker so dates ("12/04") and
# phone fragments ("91") never match: "धारा 354D", "Section 420", "IPC 120B"
_IPC_RE = re.compile(r"(?:धारा|Section|Sec\.?|IPC|BNS)\s*(\d{2,3}[A-Z]?(?:/\d+)?)", re.IGNORECASE)

# Honourific-stripped person-name heuristic: two or three Capitalised words
# (English only — Devanagari names arrive via the structured accused/complainant
# fields; a regex cannot tell Hindi verbs from surnames and must not guess)
_NAME_EN_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b")

# Common non-person capitalised sequences to drop from the name heuristic
_STOP_NAMES = {
    "FIR", "PS", "IPC", "BNS", "Cr", "No", "Mr", "Ms", "Mrs", "Shri", "Smt",
    "House", "Road", "Street", "Police", "Station", "District", "State",
}

# District list for grounding (matches synthgen pools)
_KNOWN_DISTRICTS = [
    "Mumbai", "Delhi", "New Delhi", "Kanpur", "Lucknow", "Jaipur", "Patna",
    "Varanasi", "Bhopal", "Indore", "Ahmedabad", "Surat", "Pune", "Nagpur",
    "Noida", "Ghaziabad", "Agra", "Meerut", "Prayagraj", "Gurgaon",
]


@dataclass
class ExtractedEntity:
    kind: str           # PERSON | PHONE | ACCOUNT | VEHICLE | IPC | LOCATION
    surface: str        # as it appears in the text
    normalized: str     # graph key form
    span: tuple[int, int]
    node_id: str = ""   # resolved graph node id (filled during graph merge)


@dataclass
class IngestResult:
    record_id: str
    entities: list[ExtractedEntity] = field(default_factory=list)
    cross_case_links: list[dict] = field(default_factory=list)
    new_edges: list[dict] = field(default_factory=list)
    victim_shield_applied: bool = False
    narrative_len: int = 0


# --------------------------------------------------------------------------- #
# Extraction
# --------------------------------------------------------------------------- #
def extract_entities(text: str) -> list[ExtractedEntity]:
    """Regex NER over FIR narrative text. Every entity carries its source span."""
    out: list[ExtractedEntity] = []
    seen: set[tuple[str, str]] = set()

    def _add(kind: str, surface: str, normalized: str, span: tuple[int, int]):
        key = (kind, normalized)
        if key in seen or not normalized:
            return
        seen.add(key)
        out.append(ExtractedEntity(kind=kind, surface=surface,
                                   normalized=normalized, span=span))

    for m in _PHONE_RE.finditer(text):
        raw = m.group(1)
        _add("PHONE", m.group(0), deterministic_key("PHONE", "+91" + raw), m.span())

    for m in _ACCOUNT_RE.finditer(text):
        raw = m.group(1) or (("AC" + m.group(2)) if m.group(2) else "")
        _add("ACCOUNT", m.group(0), deterministic_key("ACCOUNT", raw), m.span())

    for m in _VEHICLE_RE.finditer(text):
        raw = re.sub(r"[\s-]+", "", m.group(1)).upper()
        _add("VEHICLE", m.group(1), deterministic_key("VEHICLE", raw), m.span())

    for m in _IPC_RE.finditer(text):
        _add("IPC", m.group(0), m.group(1).upper(), m.span())

    for m in _NAME_EN_RE.finditer(text):
        name = m.group(1)
        if any(t in _STOP_NAMES for t in name.split()):
            continue
        _add("PERSON", name, name.strip().title(), m.span())

    return out


# --------------------------------------------------------------------------- #
# Cross-district linkage — the "Police Cloud" moment
# --------------------------------------------------------------------------- #
def find_cross_case_links(entities: list[ExtractedEntity], bench: dict,
                          current_district: str) -> list[dict]:
    """Check each extracted entity against existing records for cross-case linkage.

    Returns a list of linkage alerts: the entity, the other record(s) it appears in,
    and which districts those records belong to. This is the inter-district
    correlation that criminals exploit and manual policing misses.
    """
    links: list[dict] = []
    if not bench:
        return links

    # index existing records by entity key
    rec_idx: dict[str, list[dict]] = {}
    for r in bench.get("fir", []):
        rec_idx.setdefault(("FIR", r["record_id"]), []).append(r)
    for r in bench.get("cdr", []):
        for ph in (r["caller"], r["receiver"]):
            rec_idx.setdefault(("PHONE", deterministic_key("PHONE", ph)), []).append(r)
    for r in bench.get("fin", []):
        for ac in (r["sender_account"], r["receiver_account"]):
            rec_idx.setdefault(("ACCOUNT", deterministic_key("ACCOUNT", ac)), []).append(r)

    # FIR narratives mention vehicles/locations as free text — index by substring
    fir_by_vehicle: dict[str, list[dict]] = {}
    for r in bench.get("fir", []):
        nar = r.get("narrative", "")
        for vm in _VEHICLE_RE.finditer(nar):
            vkey = deterministic_key("VEHICLE", re.sub(r"[\s-]+", "", vm.group(1)).upper())
            fir_by_vehicle.setdefault(vkey, []).append(r)

    for ent in entities:
        others: list[dict] = []
        if ent.kind == "PHONE":
            for r in rec_idx.get(("PHONE", ent.normalized), []):
                others.append({"record_id": r["record_id"], "source": "CDR",
                               "district": r.get("tower", "").split(",")[-1].strip() or "unknown"})
        elif ent.kind == "ACCOUNT":
            for r in rec_idx.get(("ACCOUNT", ent.normalized), []):
                others.append({"record_id": r["record_id"], "source": "FIN",
                               "district": "financial-layer"})
        elif ent.kind == "VEHICLE":
            for r in fir_by_vehicle.get(ent.normalized, []):
                others.append({"record_id": r["record_id"], "source": "FIR",
                               "district": r.get("district", "unknown")})

        # keep only cross-district or multi-record hits — the actual alert condition
        districts = {o["district"] for o in others if o["district"] != current_district}
        multi = len(others) > 1
        if districts or multi:
            links.append({
                "entity_kind": ent.kind,
                "entity_surface": ent.surface,
                "entity_key": ent.normalized,
                "linked_records": others[:8],
                "cross_district": sorted(districts),
                "alert": (f"{ent.kind} {ent.surface} also appears in "
                          f"{len(others)} other record(s)"
                          + (f" across districts: {', '.join(sorted(districts))}"
                             if districts else "")),
            })
    return links


# --------------------------------------------------------------------------- #
# Graph merge — the new FIR becomes part of the live case graph
# --------------------------------------------------------------------------- #
def merge_into_graph(graph, bench: dict, record: dict,
                     entities: list[ExtractedEntity],
                     complainant_name: str | None,
                     accused_names: list[str]) -> list[dict]:
    """Merge an ingested FIR into the in-memory graph (Algorithm 3 conventions).

    * The narrative is appended to ``bench['fir']`` so evidence panels can cite it.
    * Extracted PHONE/ACCOUNT/VEHICLE entities become (or reuse) identifier nodes.
    * Named accused become PERSON nodes (new cluster ids); the complainant becomes a
      victim-shielded PERSON node (Women Safety policy — role set at creation).
    * Edges: accused →LOCATED_AT→ location (EXTRACTED), accused →USES/OWNED→
      identifiers (INFERRED, PENDING review — human-in-the-loop), complainant
      →LOCATED_AT→ location (EXTRACTED).
    * Returns the new edge descriptors so the UI can glow them.
    """
    from graph.build import COMMUNICATION, FINANCIAL, SPATIAL  # local: avoid cycles

    record_id = record["record_id"]
    bench.setdefault("fir", []).append(record)
    ts = record.get("date", "")

    # location node (station + district keyed, consistent with build_graph #7)
    loc_label = f'{record.get("police_station", "PS")}, {record.get("district", "")}'.strip(", ")
    loc_id = "LOC:" + deterministic_key("LOCATION", loc_label)
    graph._node(loc_id, loc_label, "LOCATION", SPATIAL, district=record.get("district"))

    # identifier nodes from extracted entities
    node_of: dict[tuple[str, str], str] = {}
    for ent in entities:
        if ent.kind == "PHONE":
            nid = "PH:" + ent.normalized
            graph._node(nid, ent.surface, "PHONE", COMMUNICATION)
        elif ent.kind == "ACCOUNT":
            nid = "AC:" + ent.normalized
            graph._node(nid, ent.surface, "ACCOUNT", FINANCIAL)
        elif ent.kind == "VEHICLE":
            nid = "VH:" + ent.normalized
            graph._node(nid, ent.surface, "VEHICLE", SPATIAL)
        else:
            continue
        ent.node_id = nid
        node_of[(ent.kind, ent.normalized)] = nid

    # person nodes: accused (full analysis) + complainant (victim-shielded)
    accused_ids: list[str] = []
    for name in accused_names:
        cid = "C" + deterministic_key("PERSON", name)[:5].upper()
        graph._node(cid, name, "PERSON", SPATIAL, role="accused",
                    aliases=[name], district=record.get("district"))
        accused_ids.append(cid)

    victim_id: str | None = None
    if complainant_name:
        victim_id = "C" + deterministic_key("PERSON", complainant_name)[:5].upper()
        graph._node(victim_id, complainant_name, "PERSON", SPATIAL, role="victim",
                    aliases=[complainant_name], district=record.get("district"))

    new_edges: list[dict] = []
    prov = f"ingest:{record_id}"
    for cid in accused_ids:
        e = graph._edge(cid, loc_id, "LOCATED_AT", ts, prov, 1.0, "EXTRACTED")
        new_edges.append({"edge_id": e.id, "type": "LOCATED_AT", "source": cid, "target": loc_id})
        for (kind, _), nid in node_of.items():
            etype = "USES" if kind == "PHONE" else "OWNED"
            layer = SPATIAL if kind == "VEHICLE" else None
            e = graph._edge(cid, nid, etype, ts, prov, 0.55, "INFERRED", layer=layer)
            new_edges.append({"edge_id": e.id, "type": etype, "source": cid, "target": nid})
    if victim_id:
        e = graph._edge(victim_id, loc_id, "LOCATED_AT", ts, prov, 1.0, "EXTRACTED")
        new_edges.append({"edge_id": e.id, "type": "LOCATED_AT", "source": victim_id,
                          "target": loc_id})

    # propagate layers onto endpoints (build_graph #5 convention)
    for eid in [e["edge_id"] for e in new_edges]:
        e = graph.edges[eid]
        for nid in (e.source, e.target):
            n = graph.nodes.get(nid)
            if n is not None:
                n.layers.add(e.layer)

    return new_edges
