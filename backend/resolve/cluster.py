"""Clustering: turn scored pairwise decisions into predicted entity clusters.

Two paths, per §9.2:

* **Deterministic** (PHONE / ACCOUNT / VEHICLE / LOCATION) — mentions with an
  identical normalized identifier key are merged with certainty.
* **Probabilistic** (PERSON) — phonetic **blocking** generates candidate pairs
  (so we never score all O(n²) pairs — essential for the LARGE preset), each pair
  is scored (:func:`resolve.features.score_pair`), and only ``MATCH`` decisions
  are *considered* for merging. ``UNCERTAIN`` pairs are never merged — they are
  counted as the human-review queue (§9.3), keeping the false-merge rate low
  (§23 target < 0.01).

  MATCH pairs are then merged **greedily in descending score order under
  complete linkage**: two clusters may only fuse if *every* cross pair between
  their members is itself a ``MATCH`` (and, when attribute evidence exists on
  both sides, the attribute similarity clears a floor). Single-linkage
  union-find alone collapses at scale (100–400 person mentions): a handful of
  permissive pairwise MATCHes transitively chain dozens of same-sounding but
  distinct people into one cluster, driving PERSON precision to ~0.33 on the
  400-person benchmark while recall stays ~0.97. Complete linkage trades a
  little recall for a large precision gain (0.87–0.88 at 200–300 persons in
  our sweep) — the right trade for an investigative tool where a false merge
  implies accusing the wrong person.

The output mirrors the ground-truth shape (``cluster_id -> [mention_id]``) so the
evaluator can score it directly.
"""
from __future__ import annotations

from collections import defaultdict

from .features import PersonRef, score_pair
from .io import build_person_refs, deterministic_key

# A phonetic block larger than this is a near-stopword key (e.g. very common
# surname sound); we still process it but the cap documents the guard against
# pathological all-pairs blowup on huge inputs.
_MAX_BLOCK = 400

# Attribute similarity floor for cluster fusion: when both sides carry usable
# attributes (age/address), a pair with attr < this is treated as evidence
# *against* merging even if name/phonetic look like a MATCH. Missing attributes
# (attr is None / unknown) never veto — absence of data must not fabricate a
# mismatch (§7.1/§25). Chosen from the n=100..400 sweep: single-linkage
# precision 0.33–0.70 vs complete+floor 0.87–0.88 at n=200–300.
_ATTR_MERGE_FLOOR = 0.3


class _UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:      # path compression
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1


def _candidate_pairs(refs: list[PersonRef]):
    """Yield index pairs that share at least one phonetic block (dedup'd)."""
    blocks: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(refs):
        for code in set(r.phon):
            blocks[code].append(i)
    seen: set[tuple[int, int]] = set()
    for members in blocks.values():
        if len(members) > _MAX_BLOCK:
            continue
        for a in range(len(members)):
            for b in range(a + 1, len(members)):
                pair = (members[a], members[b])
                if pair not in seen:
                    seen.add(pair)
                    yield pair


def _attr_ok(res) -> bool:
    """True unless known attributes disagree below the merge floor."""
    attr = res.parts.get("attr")
    return attr is None or attr >= _ATTR_MERGE_FLOOR


def _cross_ok(refs: list[PersonRef], a_members: list[int], b_members: list[int]) -> bool:
    """Complete-linkage gate: every cross pair must itself be a clean MATCH."""
    for a in a_members:
        for b in b_members:
            res = score_pair(refs[a], refs[b])
            if res.decision != "MATCH" or not _attr_ok(res):
                return False
    return True


def resolve(bench: dict) -> dict:
    """Resolve all mentions to predicted clusters.

    Returns ``{"clusters": {cid: [mention_id,...]}, "stats": {...}}``.
    """
    clusters: dict[str, list[str]] = {}
    next_cid = 0

    def new_cid() -> str:
        nonlocal next_cid
        next_cid += 1
        return f"C{next_cid:05d}"

    # ---- deterministic identifiers: exact normalized-key groups -------------
    det_groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for m in bench["mentions"]:
        et = m["entity_type"]
        if et in ("PHONE", "ACCOUNT", "VEHICLE", "LOCATION"):
            det_groups[(et, deterministic_key(et, m["surface"]))].append(m["mention_id"])
    for mids in det_groups.values():
        clusters[new_cid()] = sorted(mids)

    # ---- PERSON: blocked, scored, complete-linkage greedy merge -------------
    refs = build_person_refs(bench)
    n_match = n_uncertain = n_reject = n_pairs = 0
    merge_pairs: list[tuple[float, int, int]] = []
    for i, j in _candidate_pairs(refs):
        res = score_pair(refs[i], refs[j])
        n_pairs += 1
        if res.decision == "MATCH":
            n_match += 1
            if _attr_ok(res):
                merge_pairs.append((res.score, i, j))
        elif res.decision == "UNCERTAIN":
            n_uncertain += 1
        else:
            n_reject += 1
    merge_pairs.sort(reverse=True)   # strongest evidence fuses first

    parent = list(range(len(refs)))
    members: dict[int, list[int]] = {i: [i] for i in range(len(refs))}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for _, i, j in merge_pairs:
        ri, rj = find(i), find(j)
        if ri == rj:
            continue
        if _cross_ok(refs, members[ri], members[rj]):
            parent[ri] = rj
            members[rj].extend(members[ri])
            del members[ri]

    person_clusters: dict[int, list[str]] = defaultdict(list)
    for i, r in enumerate(refs):
        person_clusters[find(i)].append(r.mention_id)
    for mids in person_clusters.values():
        clusters[new_cid()] = sorted(mids)

    return {
        "clusters": clusters,
        "stats": {
            "person_mentions": len(refs),
            "person_clusters": len(person_clusters),
            "deterministic_clusters": len(det_groups),
            "candidate_pairs": n_pairs,
            "pair_decisions": {"MATCH": n_match, "UNCERTAIN": n_uncertain, "REJECT": n_reject},
            "human_review_queue": n_uncertain,
        },
    }
