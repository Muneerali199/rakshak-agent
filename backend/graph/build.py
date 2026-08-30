"""Phase-4 seed: a 3-layer temporal entity graph with full provenance (paper §10, Algorithm 3).

Builds the MVP's three graph layers directly from the synthgen benchmark, on top of the
Phase-3 resolved entities:

* **Communication** — `CONTACTED` edges between PHONE entities (from CDR).
* **Financial** — `TRANSFERRED_TO` edges between ACCOUNT entities (from FIN).
* **Spatial** — `LOCATED_AT` edges from PERSON entities to LOCATION (from FIR).

Plus **INFERRED** cross-entity `ASSOCIATE_OF` edges from person co-mention in the same FIR
(dashed-grey in the UI). Every edge is built per **Algorithm 3**: it carries `timestamp`,
`confidence`, `provenance` (source doc id), `creation_method`, `review_status`, and a
tamper-evident **SHA-256 `audit_hash`** over its canonical JSON (line 8).

Pure standard library. `AMOUNT`/narrative-only artifacts are ignored; nodes are keyed by the
deterministic identifier (phone/account/location) or the resolved PERSON cluster id, so the
graph is stable and reproducible for a given seed.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field

from resolve.io import deterministic_key

# honorifics the generator prepends (variants.py) — stripped from display labels only
_HON = {"sh.", "sh", "shri", "sri", "mr.", "mr", "ms.", "ms", "smt.", "smt", "km", "kumari", "dr", "dr."}


def _clean_label(surface: str) -> str:
    """Drop a leading honorific token for a tidy node label (display only)."""
    parts = surface.split()
    while parts and parts[0].casefold().strip(".") in {h.strip(".") for h in _HON}:
        parts = parts[1:]
    return " ".join(parts) or surface

# layer names (match the API's Layer enum)
COMMUNICATION, FINANCIAL, SPATIAL = "communication", "financial", "spatial"

# edge type → layer ("OWNED" defaults to financial; person→vehicle OWNED edges
# override to spatial at creation, since a vehicle sighting is a spatial fact)
_TYPE_LAYER = {
    "CONTACTED": COMMUNICATION,
    "TRANSFERRED_TO": FINANCIAL,
    "LOCATED_AT": SPATIAL,
    "ASSOCIATE_OF": COMMUNICATION,   # inferred co-mention, shown on the comm lane
    "USES": COMMUNICATION,           # inferred person→phone ownership (from FIR co-mention)
    "OWNED": FINANCIAL,              # inferred person→account ownership (from FIR co-mention)
}


@dataclass
class Node:
    id: str
    label: str
    type: str                        # PERSON | PHONE | ACCOUNT | LOCATION
    layers: set = field(default_factory=set)
    meta: dict = field(default_factory=dict)


@dataclass
class Edge:
    id: str
    source: str
    target: str
    type: str
    layer: str
    creation_method: str             # EXTRACTED | INFERRED
    confidence: float
    timestamp: str
    provenance: str                  # source document id
    review_status: str = "PENDING"
    audit_hash: str = ""

    def canonical(self) -> str:
        """Deterministic JSON for hashing — excludes the hash itself (Algorithm 3, line 8)."""
        return json.dumps(
            {"source": self.source, "target": self.target, "type": self.type,
             "timestamp": self.timestamp, "provenance": self.provenance,
             "confidence": self.confidence, "creation_method": self.creation_method},
            sort_keys=True, ensure_ascii=False,
        )

    def with_hash(self) -> "Edge":
        self.audit_hash = hashlib.sha256(self.canonical().encode("utf-8")).hexdigest()
        return self

    def verify(self) -> bool:
        return self.audit_hash == hashlib.sha256(self.canonical().encode("utf-8")).hexdigest()


class Graph:
    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, Edge] = {}
        self._adj: dict[str, set] = defaultdict(set)   # node_id → {edge_id}
        self._eid = 0

    # ---- construction helpers ------------------------------------------------
    def _node(self, nid: str, label: str, ntype: str, layer: str, **meta) -> Node:
        n = self.nodes.get(nid)
        if n is None:
            n = self.nodes[nid] = Node(nid, label, ntype, set(), {})
        n.layers.add(layer)
        if meta:
            n.meta.update({k: v for k, v in meta.items() if v is not None})
        return n

    def _edge(self, src, tgt, etype, ts, prov, conf, method, layer: str | None = None) -> Edge:
        self._eid += 1
        e = Edge(f"E{self._eid:05d}", src, tgt, etype, layer or _TYPE_LAYER[etype],
                 method, round(conf, 3), ts, prov).with_hash()
        self.edges[e.id] = e
        self._adj[src].add(e.id)
        self._adj[tgt].add(e.id)
        return e

    # ---- queries -------------------------------------------------------------
    def subgraph(self, root: str, depth: int = 1, layers: set | None = None) -> dict:
        """BFS neighborhood around ``root`` up to ``depth`` hops, optionally layer-filtered."""
        if root not in self.nodes:
            raise KeyError(root)
        seen_nodes = {root}
        seen_edges: set[str] = set()
        frontier = {root}
        for _ in range(max(1, depth)):
            nxt = set()
            for nid in frontier:
                for eid in self._adj[nid]:
                    e = self.edges[eid]
                    if layers and e.layer not in layers:
                        continue
                    seen_edges.add(eid)
                    for end in (e.source, e.target):
                        if end not in seen_nodes:
                            seen_nodes.add(end)
                            nxt.add(end)
            frontier = nxt
            if not frontier:
                break

        edges = [self.edges[e] for e in sorted(seen_edges)]
        layer_assign: dict[str, list] = defaultdict(list)
        for nid in seen_nodes:
            for lyr in sorted(self.nodes[nid].layers):
                if not layers or lyr in layers:
                    layer_assign[lyr].append(nid)
        return {
            "root": root,
            "nodes": [self.nodes[n] for n in sorted(seen_nodes)],
            "edges": edges,
            "layer_assignments": {k: sorted(v) for k, v in layer_assign.items()},
            "stats": {"nodes": len(seen_nodes), "edges": len(edges),
                      "inferred": sum(1 for e in edges if e.creation_method == "INFERRED")},
        }

    def edge(self, edge_id: str) -> Edge:
        return self.edges[edge_id]

    def shortest_path(self, src: str, dst: str, max_depth: int = 6) -> list:
        """BFS shortest edge path between two nodes (paper §16 investigation queries)."""
        if src not in self.nodes or dst not in self.nodes:
            return None
        if src == dst:
            return []
        from collections import deque
        prev: dict[str, tuple] = {src: (None, None)}      # node → (prev node, edge id)
        q = deque([src])
        while q and len(prev) <= len(self.nodes):
            cur = q.popleft()
            for eid in self._adj[cur]:
                e = self.edges[eid]
                nxt = e.target if e.source == cur else e.source
                if nxt in prev:
                    continue
                prev[nxt] = (cur, eid)
                if nxt == dst:
                    path = []
                    node = dst
                    while prev[node][0] is not None:
                        p, eid2 = prev[node]
                        path.append(self.edges[eid2])
                        node = p
                    return list(reversed(path))
                q.append(nxt)
        return None


# --------------------------------------------------------------------------- #
# Build the graph from a resolved benchmark
# --------------------------------------------------------------------------- #
def build_graph(bench: dict, clusters: dict) -> Graph:
    """Construct the 3-layer graph from benchmark records + Phase-3 person clusters.

    ``clusters`` is ``resolve(bench)["clusters"]``; we use it only to give each PERSON a
    stable resolved id and to attach its observed aliases.
    """
    g = Graph()

    # map every resolved PERSON mention_id → (cluster_id, representative label)
    mention_meta = {m["mention_id"]: m for m in bench["mentions"] if m["entity_type"] == "PERSON"}
    person_of_mention: dict[str, str] = {}
    person_label: dict[str, str] = {}
    person_aliases: dict[str, set] = defaultdict(set)
    for cid, mids in clusters.items():
        pmids = [m for m in mids if m in mention_meta]
        if not pmids:
            continue
        # representative label = the longest *honorific-free* surface (fullest clean name)
        surfaces = [mention_meta[m]["surface"] for m in pmids]
        label = max((_clean_label(s) for s in surfaces), key=len)
        for m in pmids:
            person_of_mention[m] = cid
            person_aliases[cid].add(mention_meta[m]["surface"])
        person_label[cid] = label

    # ---- victim-shield roles (Women Safety Division policy) --------------------
    # A resolved person is tagged by how they appear in FIRs:
    #   "accused"   — named as an accused in ≥1 FIR  → full network analysis
    #   "victim"    — named as a complainant and never as an accused → PROTECTED:
    #                 pseudonymized, access-restricted, never network-analyzed
    #   "mentioned" — appears only in narratives     → default handling
    # Accused-in-any-FIR wins over victim, because a complainant in one case can be
    # an accused in another (cross-case linkage is exactly what investigators need).
    roles: dict[str, str] = {}
    for cid in person_label:
        roles[cid] = "mentioned"
    for m in bench["mentions"]:
        if m["entity_type"] != "PERSON" or m["source"] != "FIR":
            continue
        cid = person_of_mention.get(m["mention_id"])
        if cid is None:
            continue
        if m.get("field") == "accused":
            roles[cid] = "accused"
        elif m.get("field") == "complainant" and roles[cid] != "accused":
            roles[cid] = "victim"

    for cid, lbl in person_label.items():
        g._node(cid, lbl, "PERSON", SPATIAL, aliases=sorted(person_aliases[cid])[:5],
                role=roles[cid])

    # ---- Communication: CDR → CONTACTED between phone entities ----------------
    for r in bench["cdr"]:
        ck = "PH:" + deterministic_key("PHONE", r["caller"])
        rk = "PH:" + deterministic_key("PHONE", r["receiver"])
        g._node(ck, r["caller"], "PHONE", COMMUNICATION)
        g._node(rk, r["receiver"], "PHONE", COMMUNICATION)
        g._edge(ck, rk, "CONTACTED", r["timestamp"], r["record_id"], 1.0, "EXTRACTED")

    # ---- Financial: FIN → TRANSFERRED_TO between account entities -------------
    for r in bench["fin"]:
        sk = "AC:" + deterministic_key("ACCOUNT", r["sender_account"])
        tk = "AC:" + deterministic_key("ACCOUNT", r["receiver_account"])
        g._node(sk, r["sender_account"], "ACCOUNT", FINANCIAL, bank=r.get("sender_bank"))
        g._node(tk, r["receiver_account"], "ACCOUNT", FINANCIAL, bank=r.get("receiver_bank"))
        g._edge(sk, tk, "TRANSFERRED_TO", r["timestamp"], r["record_id"], 1.0, "EXTRACTED")

    # ---- Spatial: FIR → LOCATED_AT (person → location) + co-mention inference -
    # index which resolved persons are named in each FIR (via the person mentions)
    fir_persons: dict[str, set] = defaultdict(set)
    for m in bench["mentions"]:
        if m["entity_type"] == "PERSON" and m["source"] == "FIR":
            cid = person_of_mention.get(m["mention_id"])
            if cid:
                fir_persons[m["record_id"]].add(cid)

    for r in bench["fir"]:
        loc_label = f'{r.get("police_station","PS")}, {r.get("district","")}'.strip(", ")
        # key by station+district so distinct police stations never collapse into
        # one mislabeled node (#7) — the label and the key now describe the same place
        lk = "LOC:" + deterministic_key("LOCATION", loc_label)
        g._node(lk, loc_label, "LOCATION", SPATIAL, district=r.get("district"))
        persons = sorted(fir_persons.get(r["record_id"], []))
        for cid in persons:
            g._node(cid, person_label.get(cid, cid), "PERSON", SPATIAL, district=r.get("district"))
            g._edge(cid, lk, "LOCATED_AT", r["date"], r["record_id"], 1.0, "EXTRACTED")
        # INFERRED: people co-named in the same FIR are candidate associates
        for i in range(len(persons)):
            for j in range(i + 1, len(persons)):
                g._edge(persons[i], persons[j], "ASSOCIATE_OF", r["date"],
                        f'co-mention:{r["record_id"]}', 0.6, "INFERRED")

    # ---- INFERRED person→identifier ownership from FIR co-mention -------------
    # A phone / account / vehicle named in a FIR narrative is attributed to that
    # FIR's accused. This is what connects PERSON nodes into the communication
    # AND financial lanes (#5, #6) and materialises vehicles (#11). Low confidence,
    # PENDING review — the human-in-the-loop confirms or rejects it.
    accused_by_fir: dict[str, set] = defaultdict(set)
    complainant_by_fir: dict[str, set] = defaultdict(set)  # victim's own phone in her FIR
    ident_by_fir: dict[tuple[str, str], set] = defaultdict(set)   # (record_id, kind) → node keys
    surfaces: dict[str, str] = {}                                 # node key → display surface
    for m in bench["mentions"]:
        if m["source"] != "FIR":
            continue
        if m["entity_type"] == "PERSON" and m["field"] == "accused":
            cid = person_of_mention.get(m["mention_id"])
            if cid:
                accused_by_fir[m["record_id"]].add(cid)
        elif m["entity_type"] == "PERSON" and m["field"] == "complainant":
            cid = person_of_mention.get(m["mention_id"])
            if cid:
                complainant_by_fir[m["record_id"]].add(cid)
        elif m["entity_type"] == "PHONE":
            k = "PH:" + deterministic_key("PHONE", m["surface"])
            ident_by_fir[(m["record_id"], "PHONE")].add(k)
            surfaces.setdefault(k, m["surface"])
        elif m["entity_type"] == "ACCOUNT":
            k = "AC:" + deterministic_key("ACCOUNT", m["surface"])
            ident_by_fir[(m["record_id"], "ACCOUNT")].add(k)
            surfaces.setdefault(k, m["surface"])
        elif m["entity_type"] == "VEHICLE":
            k = "VH:" + deterministic_key("VEHICLE", m["surface"])
            ident_by_fir[(m["record_id"], "VEHICLE")].add(k)
            surfaces.setdefault(k, m["surface"])

    for rid, accused in accused_by_fir.items():
        # split confidence when the attribution is ambiguous across multiple accused
        conf = 0.55 if len(accused) == 1 else 0.4
        for pk in ident_by_fir.get((rid, "PHONE"), ()):
            for cid in accused:
                if pk in g.nodes:
                    g._edge(cid, pk, "USES", "", f'co-mention:{rid}', conf, "INFERRED")
        for ak in ident_by_fir.get((rid, "ACCOUNT"), ()):
            if ak not in g.nodes:                 # account first seen here → materialise it
                g._node(ak, surfaces.get(ak, ak), "ACCOUNT", FINANCIAL)
            for cid in accused:
                g._edge(cid, ak, "OWNED", "", f'co-mention:{rid}', conf, "INFERRED")
        for vk in ident_by_fir.get((rid, "VEHICLE"), ()):
            if vk not in g.nodes:                 # vehicle first seen here → materialise it
                g._node(vk, surfaces.get(vk, vk), "VEHICLE", SPATIAL)
            for cid in accused:
                g._edge(cid, vk, "OWNED", "", f'co-mention:{rid}', conf, "INFERRED",
                        layer=SPATIAL)            # a vehicle sighting is a spatial fact

    # complainants own their co-mentioned phones too (the victim's number named in
    # her own FIR) — this is what lets escalation detection link a stalker's call
    # pattern to a protected party WITHOUT exposing her identity
    for rid, complainants in complainant_by_fir.items():
        for pk in ident_by_fir.get((rid, "PHONE"), ()):
            for cid in complainants:
                if pk in g.nodes:
                    g._edge(cid, pk, "USES", "", f'co-mention:{rid}', 0.55, "INFERRED")

    # ---- #5: propagate edge layers onto endpoints so hubs become multi-lane ---
    # A person with USES + OWNED + LOCATED_AT edges now spans communication,
    # financial, and spatial — the cross-layer hub the UI halos.
    for e in g.edges.values():
        for nid in (e.source, e.target):
            n = g.nodes.get(nid)
            if n is not None:
                n.layers.add(e.layer)

    # ---- #8: dedupe INFERRED edges — same (src, tgt, type) keeps only the
    # strongest claim, so degree/risk is not inflated by duplicate inference.
    _dedupe_inferred(g)

    return g


def _dedupe_inferred(g: Graph) -> int:
    best: dict[tuple, Edge] = {}
    drop: set[str] = set()
    for e in g.edges.values():
        if e.creation_method != "INFERRED":
            continue
        k = (e.source, e.target, e.type)
        if k not in best:
            best[k] = e
            continue
        keep, gone = (e, best[k]) if e.confidence > best[k].confidence else (best[k], e)
        best[k] = keep
        drop.add(gone.id)
    for eid in drop:
        e = g.edges.pop(eid)
        g._adj[e.source].discard(eid)
        g._adj[e.target].discard(eid)
    return len(drop)
