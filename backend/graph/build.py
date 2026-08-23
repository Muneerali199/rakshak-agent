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

# layer names (match the API's Layer enum)
COMMUNICATION, FINANCIAL, SPATIAL = "communication", "financial", "spatial"

# edge type → layer
_TYPE_LAYER = {
    "CONTACTED": COMMUNICATION,
    "TRANSFERRED_TO": FINANCIAL,
    "LOCATED_AT": SPATIAL,
    "ASSOCIATE_OF": COMMUNICATION,   # inferred co-mention, shown on the comm lane
    "USES": COMMUNICATION,           # inferred person→phone ownership (from FIR co-mention)
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

    def _edge(self, src, tgt, etype, ts, prov, conf, method) -> Edge:
        self._eid += 1
        e = Edge(f"E{self._eid:05d}", src, tgt, etype, _TYPE_LAYER[etype],
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
        # representative label = the longest surface (usually the fullest romanized form)
        label = max((mention_meta[m]["surface"] for m in pmids), key=len)
        for m in pmids:
            person_of_mention[m] = cid
            person_aliases[cid].add(mention_meta[m]["surface"])
        person_label[cid] = label

    for cid, lbl in person_label.items():
        g._node(cid, lbl, "PERSON", SPATIAL, aliases=sorted(person_aliases[cid])[:5])

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
        lk = "LOC:" + deterministic_key("LOCATION", r.get("district", loc_label))
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

    # ---- INFERRED person→phone ownership: a phone named in a FIR narrative is
    # attributed to that FIR's *accused* (narratively "the accused was contacted on…").
    # This is what connects PERSON nodes into the communication lane. Low confidence,
    # PENDING review — the human-in-the-loop confirms or rejects it.
    accused_by_fir: dict[str, set] = defaultdict(set)
    phones_by_fir: dict[str, set] = defaultdict(set)
    for m in bench["mentions"]:
        if m["source"] != "FIR":
            continue
        if m["entity_type"] == "PERSON" and m["field"] == "accused":
            cid = person_of_mention.get(m["mention_id"])
            if cid:
                accused_by_fir[m["record_id"]].add(cid)
        elif m["entity_type"] == "PHONE":
            phones_by_fir[m["record_id"]].add("PH:" + deterministic_key("PHONE", m["surface"]))
    for rid, phones in phones_by_fir.items():
        accused = accused_by_fir.get(rid, set())
        # split confidence when the attribution is ambiguous across multiple accused
        conf = 0.55 if len(accused) == 1 else 0.4
        for cid in accused:
            for pk in phones:
                if pk in g.nodes:
                    g._edge(cid, pk, "USES", "", f'co-mention:{rid}', conf, "INFERRED")

    return g
