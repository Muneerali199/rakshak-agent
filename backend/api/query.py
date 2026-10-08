"""Grounded natural-language investigation queries (paper §16, Algorithm 7).

Anti-hallucination contract: the answerer may ONLY reference entities and edges
that exist in the case graph. Every factual sentence cites the edge ids that
support it; if nothing matches, it says so — it never invents nodes, edges, or
relationships. Template-based intent parsing (the paper's disclosed MVP limit).

Pure standard library; `difflib` provides the fuzzy entity grounding.
"""
from __future__ import annotations

import difflib
import re

DISCLOSURE = ("answers are retrieved only from the case graph and cite their evidence — "
              "the model cannot invent entities or relationships (paper §16.3)")

VICTIM_SHIELD_MSG = ("is a protected party in this case. Victim data is pseudonymized and "
                     "access-restricted under Women Safety Division policy — network "
                     "analysis is limited to accused persons.")

VICTIM_SHIELD_MSG_HI = ("इस मामले के संरक्षित पक्ष हैं। पीड़ित डेटा छद्मीकृत और प्रतिबंधित है — "
                        "नेटवर्क विश्लेषण केवल आरोपित व्यक्तियों तक सीमित है।")


def _is_victim(graph, node_id: str) -> bool:
    n = graph.nodes.get(node_id)
    return bool(n) and n.type == "PERSON" and n.meta.get("role") == "victim"

_INTENTS = {
    "contact": r"\b(contact|call|called|talk|talked|phone|spoke|speak|communicat)\w*",
    "associate": r"\b(associate|friend|gang|group|link(ed)? with|network)\w*",
    "location": r"\b(where|seen|spotted|located|location|place|spot|sight)\w*",
    "owned": r"\b(own|owns|owned|account|bank|vehicle|drive|drove|car)\w*",
    "path": r"\b(how|path|route|connect|connected|between|relate|related|chain)\b",
    "anomaly": r"\b(anomal|suspicious|fraud|launder|cycle|burst|alert|flag)\w*",
    "help": r"\b(help|what can|how to|examples?)\b",
}


def _build_entity_index(graph) -> list[dict]:
    """Flatten nodes into searchable entries: label + aliases + id."""
    index = []
    for n in graph.nodes.values():
        names = {n.label, n.id}
        names.update(n.meta.get("aliases", []) or [])
        for name in names:
            if name and len(name) >= 3:
                index.append({"node_id": n.id, "name": str(name), "type": n.type})
    return index


def _find_entities(question: str, graph, max_matches: int = 3) -> list[dict]:
    """Ground question text to graph entities: substring first, then fuzzy token match."""
    index = _build_entity_index(graph)
    ql = question.lower()
    found: dict[str, dict] = {}

    # 1) exact substring (case-insensitive) — covers most demo questions
    for ent in index:
        name = ent["name"].lower()
        if name in ql and len(name) >= 4:
            cur = found.get(ent["node_id"])
            if cur is None or len(name) > len(cur["name"]):
                found[ent["node_id"]] = {**ent, "score": 1.0}

    # 2) fuzzy: close token matches for typos ("aneel sharma" vs "Aneel Sharmaa")
    if not found:
        tokens = re.findall(r"[a-z0-9]{3,}", ql)
        names = {e["name"].lower(): e for e in index}
        for token in tokens:
            for close in difflib.get_close_matches(token, list(names), n=3, cutoff=0.85):
                ent = names[close]
                found.setdefault(ent["node_id"], {**ent, "score": 0.85})

    ranked = sorted(found.values(), key=lambda e: -e["score"])
    return ranked[:max_matches]


def _row(graph, edge, claim: str | None = None) -> dict:
    s = graph.nodes[edge.source].label
    t = graph.nodes[edge.target].label
    return {
        "edge_id": edge.id,
        "focus_entity_id": edge.source,
        "claim": claim or f"{s} —[{edge.type}]→ {t}",
        "confidence": edge.confidence,
        "provenance": edge.provenance,
        "timestamp": edge.timestamp or None,
    }


def _contacts_of(graph, person_id: str) -> list[dict]:
    """X -USES→ phone -CONTACTED→ phone -USES→ person (or the raw phone if unattributed)."""
    rows: list[dict] = []
    seen_phones: set[str] = set()
    for eid in graph._adj.get(person_id, ()):          # noqa: SLF001 — same package family
        e = graph.edges[eid]
        if e.type != "USES" or graph.nodes[e.target].type != "PHONE":
            continue
        phone = e.target
        if phone in seen_phones:
            continue
        seen_phones.add(phone)
        for eid2 in graph._adj.get(phone, ()):          # noqa: SLF001
            e2 = graph.edges[eid2]
            if e2.type != "CONTACTED":
                continue
            other = e2.target if e2.source == phone else e2.source
            # attribute the counterpart phone to a person if an inverse USES edge exists
            for eid3 in graph._adj.get(other, ()):       # noqa: SLF001
                e3 = graph.edges[eid3]
                if e3.type == "USES" and e3.target == other and e3.source != person_id:
                    label = graph.nodes[e3.source].label
                    rows.append(_row(graph, e2, f"{label} ({other}) via {phone}"))
                    break
            else:
                rows.append(_row(graph, e2, f"{graph.nodes[other].label} (unattributed number)"))
    return rows


def _edges_of_type(graph, person_id: str, etype: str) -> list[dict]:
    rows = []
    for eid in graph._adj.get(person_id, ()):            # noqa: SLF001
        e = graph.edges[eid]
        if e.type == etype:
            rows.append(_row(graph, e))
    return rows


def answer_question(question: str, graph, anomalies: list[dict], limit: int = 10,
                    lang: str = "en") -> dict:
    """``lang="hi"`` renders the answer sentence in Hindi (Devanagari labels +
    fixed Hindi templates); evidence rows/citations keep machine labels. The Hindi
    path is the offline rule-based layer (resolve.hindi) — disclosed, not neural."""
    from resolve.hindi import to_devanagari
    q = question.strip()
    ql = q.lower()
    _hi = lang == "hi"
    h = (lambda x: to_devanagari(str(x))) if _hi else (lambda x: str(x))

    def _t(hi_s: str, en_s: str) -> str:
        return hi_s if _hi else en_s

    intent = next((k for k, rx in _INTENTS.items() if re.search(rx, ql)), None)
    matches = _find_entities(q, graph)

    base = {
        "question": q,
        "intent": intent or "unknown",
        "matches": [{"entity_id": m["node_id"], "label": graph.nodes[m["node_id"]].label,
                     "type": m["type"], "score": m["score"]} for m in matches],
        "results": [],
        "citations": [],
    }
    if _hi:
        base["matches"] = [{**m, "label": h(m["label"])} for m in base["matches"]]

    if intent == "anomaly":
        top = anomalies[:limit]

        def _short(a: dict) -> str:
            label = a.get("label") or a["entity_id"].split(":", 1)[-1]
            kind = a["kind"].lower().replace("_", " ")
            return f"{h(label)} ({_t(kind, kind)})"

        names = "; ".join(_short(a) for a in top)
        return {**base,
                "grounded": True,
                "answer": _t(
                    f"{len(anomalies)} विश्लेषणात्मक संदिग्ध गतिविधियाँ दर्ज हैं। प्रमुख: {names}. "
                    f"संपूर्ण सूची के लिए संदिग्ध-गतिविधि पैनल खोलें।",
                    f"{len(anomalies)} analytical anomalies on file. Top: {names}. "
                    f"Open the suspicious-activity panel for the full list."),
                "citations": []}

    if intent == "help" or not intent:
        return {**base,
                "grounded": False,
                "answer": _t(
                    "मामले-संजाल के बारे में पूछें, जैसे “who did <नाम> contact?” — "
                    "या हिंदी में: नाम के सहारे ग्राफ़ से जुड़ाव देखने के लिए पूछें।",
                    "Ask about the case graph, e.g. “who did <name> contact?”, "
                    "“where was <name> seen?”, “what does <name> own?”, "
                    "“how are <A> and <B> connected?”, “any suspicious activity?”"),
                "citations": []}

    if intent == "help" or not intent:
        return {**base,
                "grounded": False,
                "answer": "Ask about the case graph, e.g. \u201cwho did <name> contact?\u201d, "
                          "\u201cwhere was <name> seen?\u201d, \u201cwhat does <name> own?\u201d, "
                          "\u201chow are <A> and <B> connected?\u201d, \u201cany suspicious activity?\u201d",
                "citations": []}

    if intent == "path":
        if len(matches) < 2:
            return {**base,
                    "grounded": len(matches) > 0,
                    "answer": _t(
                        "दो नाम बताइए जिनका जुड़ाव देखना है, जैसे “how are Aneel Sharmaa and "
                        "RAJEHSH Redddi connected?”",
                        "Name two entities from the case file to trace a connection, "
                        "e.g. “how are Aneel Sharmaa and RAJEHSH Redddi connected?”"),
                    "citations": []}
        a, b = matches[0], matches[1]
        # victim-shield: never trace a path through a protected party
        if _is_victim(graph, a["node_id"]) or _is_victim(graph, b["node_id"]):
            vic = a if _is_victim(graph, a["node_id"]) else b
            return {**base,
                    "grounded": True,
                    "answer": f"{h(graph.nodes[vic['node_id']].label)} "
                              + _t(VICTIM_SHIELD_MSG_HI, VICTIM_SHIELD_MSG),
                    "results": [],
                    "citations": []}
        path = graph.shortest_path(a["node_id"], b["node_id"])
        if path is None:
            return {**base,
                    "grounded": True,
                    "answer": _t(
                        f"मामले-संजाल में {h(graph.nodes[a['node_id']].label)} और "
                        f"{h(graph.nodes[b['node_id']].label)} के बीच कोई जुड़ाव नहीं मिला।",
                        f"No connection found between {h(graph.nodes[a['node_id']].label)} and "
                        f"{h(graph.nodes[b['node_id']].label)} within the case graph."),
                    "citations": []}
        rows = [_row(graph, e) for e in path[:limit]]
        chain = " → ".join([h(graph.nodes[path[0].source].label)]
                           + [h(graph.nodes[e.target].label) for e in path])
        return {**base,
                "grounded": True,
                "answer": _t(
                    f"{len(path)}-चरणीय जुड़ाव: {chain}। हर चरण साक्ष्य के साथ उद्धृत है।",
                    f"{len(path)}-step connection: {chain}. Every step cites its evidence."),
                "results": rows,
                "citations": [e.id for e in path[:limit]]}

    if not matches:
        # anti-hallucination: refuse rather than guess (paper §16.3)
        return {**base,
                "grounded": False,
                "answer": _t(
                    "यह व्यक्ति मामले-संजाल में नहीं है, इसलिए साक्ष्य से उत्तर देना संभव नहीं। "
                    "सूची से कोई नाम आज़माइए।",
                    "That entity is not in the case graph, so I cannot answer from "
                    "evidence. Try a name from the entity list."),
                "citations": []}

    person = matches[0]["node_id"]
    label = h(graph.nodes[person].label)

    # victim-shield: a protected party is never network-analyzed (any intent)
    if _is_victim(graph, person):
        return {**base,
                "grounded": True,
                "answer": f"{label} " + _t(VICTIM_SHIELD_MSG_HI, VICTIM_SHIELD_MSG),
                "results": [],
                "citations": []}

    if intent == "contact":
        rows = _contacts_of(graph, person)[:limit]
        if not rows:
            return {**base, "grounded": True,
                    "answer": _t(
                        f"मामले-संजाल में {label} का कोई संचार-अभिलेख नहीं।",
                        f"No communication records for {label} in the case graph."),
                    "citations": []}
        counterparts = sorted({r["claim"].split(" via ")[0] for r in rows})
        shown = ", ".join(h(c) for c in counterparts[:5])
        return {**base, "grounded": True,
                "answer": _t(
                    f"कॉल-विवरण दिखाता है: {label} संपर्क में है {shown}"
                    + (f" — {len(rows)} कॉल अभिलेख उद्धृत।" if len(rows) > 1 else "."),
                    f"CDR records show {label} in contact with: {shown}"
                    + (f" — {len(rows)} call records cited." if len(rows) > 1 else ".")),
                "results": rows,
                "citations": [r["edge_id"] for r in rows]}

    if intent == "associate":
        rows = _edges_of_type(graph, person, "ASSOCIATE_OF")[:limit]
        if not rows:
            return {**base, "grounded": True,
                    "answer": _t(
                        f"{label} के लिए कोई अनुमानित संबंध नहीं — अभी सत्यापन हेतु नहीं।",
                        f"No inferred associations for {label} — nothing to verify yet."),
                    "citations": []}
        return {**base, "grounded": True,
                "answer": _t(
                    f"{label} इनसे अनुमानित रूप से संबंधित: "
                    + ", ".join(h(r["claim"].split("→")[-1].strip()) for r in rows)
                    + ". ये अनुमानित-संबंध मानव समीक्षा की प्रतीक्षा में हैं।",
                    f"{label} is inferred to be associated with: "
                    + ", ".join(r["claim"].split("→")[-1].strip() for r in rows)
                    + ". These are INFERRED links pending human review."),
                "results": rows,
                "citations": [r["edge_id"] for r in rows]}

    if intent == "location":
        rows = _edges_of_type(graph, person, "LOCATED_AT")[:limit]
        if not rows:
            return {**base, "grounded": True,
                    "answer": _t(
                        f"मामले-संजाल में {label} का कोई स्थान-अभिलेख नहीं।",
                        f"No location records for {label} in the case graph."),
                    "citations": []}
        places = sorted({r["claim"].split("→")[-1].strip() for r in rows})
        return {**base, "grounded": True,
                "answer": _t(
                    f"प्राथमिकी के अनुसार {label} यहाँ उपस्थित: " + ", ".join(h(p) for p in places) + ".",
                    f"FIR records place {label} at: " + ", ".join(places) + "."),
                "results": rows,
                "citations": [r["edge_id"] for r in rows]}

    if intent == "owned":
        rows = (_edges_of_type(graph, person, "OWNED") + _edges_of_type(graph, person, "USES"))[:limit]
        if not rows:
            return {**base, "grounded": True,
                    "answer": _t(
                        f"मामले-संजाल में {label} के लिए कोई स्वामित्व/उपकरण-जिम्मेदारी नहीं।",
                        f"No ownership or device attribution for {label} in the case graph."),
                    "citations": []}
        return {**base, "grounded": True,
                "answer": _t(
                    f"{label} {len(rows)} संपत्ति(ओं) से जुड़ा है — खाते, वाहन और संबद्ध मोबाइल। "
                    f"ये अनुमानित आरोपण हैं।",
                    f"{label} is linked to {len(rows)} asset(s) — accounts, vehicles, "
                    "and the attributed phone. These are inferred attributions."),
                "results": rows,
                "citations": [r["edge_id"] for r in rows]}

    return {**base, "grounded": False,
            "answer": _t(
                "समर्थित प्रश्न-प्रकार नहीं।",
                "Unsupported question type."),
            "citations": []}
