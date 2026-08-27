"""Experiment A baselines (paper §22, §24) — pure standard library.

Two competitor clusterers scored against the same seed-42 ground truth as the
hybrid resolver, so the deck can show *measured* superiority:

* ``exact_baseline``   — cluster mentions by identical normalized surface text.
                         Fails on transliteration ("Mohd Arif" ≠ "मोहम्मद आरिफ़"),
                         typos, and honorific variants.
* ``fuzzy_baseline``   — single-linkage clustering on name Jaro-Winkler ≥ 0.9.
                         Catches typos but not cross-script names, and merges
                         common-name false pairs (no attribute veto).
* ``hybrid`` (the real pipeline) — identifier short-circuit + name/phonetic/
                         attribute scoring + hard-conflict veto.

All three are scored by the SAME §23 evaluator (resolve.evaluate).
"""
from __future__ import annotations

from collections import defaultdict

from .normalize import normalize_key, normalize_name
from .similarity import jaro_winkler

FUZZY_THRESHOLD = 0.9


def _cluster_from_groups(groups: dict[str, list[str]]) -> dict[str, list[str]]:
    return {f"B{i + 1:05d}": mids for i, (_, mids) in enumerate(sorted(groups.items()))}


def exact_baseline(bench: dict) -> dict:
    """Baseline 1: identical normalized surface ⇒ same entity. Nothing else counts."""
    groups: dict[str, list[str]] = defaultdict(list)
    for m in bench["mentions"]:
        if m["true_id"] is None:
            continue
        key = normalize_key(m["surface"])
        groups[key].append(m["mention_id"])
    return {"clusters": _cluster_from_groups(groups)}


def fuzzy_baseline(bench: dict) -> dict:
    """Baseline 2: single-linkage name Jaro-Winkler ≥ 0.9 on normalized names."""
    # one representative name per mention (normalized token tuple → string)
    names: dict[str, str] = {}
    for m in bench["mentions"]:
        if m["true_id"] is None:
            continue
        mid = m["mention_id"]
        if mid not in names:
            names[mid] = " ".join(normalize_name(m["surface"]))

    mids = sorted(names)
    parent = {m: m for m in mids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    # block by first token to keep the pair loop near-linear
    blocks: dict[str, list[str]] = defaultdict(list)
    for m in mids:
        blocks[names[m].split(" ")[0][:3]].append(m)

    for key in blocks:
        block = blocks[key]
        for i in range(len(block)):
            for j in range(i + 1, len(block)):
                a, b = block[i], block[j]
                if jaro_winkler(names[a], names[b]) >= FUZZY_THRESHOLD:
                    ra, rb = find(a), find(b)
                    if ra != rb:
                        parent[rb] = ra

    merged: dict[str, list[str]] = defaultdict(list)
    for m in mids:
        merged[find(m)].append(m)
    return {"clusters": _cluster_from_groups({k: v for k, v in merged.items()})}
