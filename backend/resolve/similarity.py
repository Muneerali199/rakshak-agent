"""String-similarity primitives for entity resolution (paper §9.2 "name similarity").

All pure standard library and all returning a score in [0, 1]:

* :func:`levenshtein_ratio` — edit-distance similarity.
* :func:`jaro_winkler`       — Jaro-Winkler (rewards shared prefixes; strong on names).
* :func:`ngram_cosine`       — cosine over character trigram counts (the
  dependency-free stand-in for the proposal's char-n-gram / embedding cosine).
* :func:`token_set_ratio`    — order-invariant best-token matching for multi-word names.

These are the φ_name components combined by the scorer in :mod:`resolve.features`.
"""
from __future__ import annotations

import math
from collections import Counter


def levenshtein(a: str, b: str) -> int:
    """Classic Levenshtein edit distance (two-row DP)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
        prev = cur
    return prev[-1]


def levenshtein_ratio(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    return 1.0 - levenshtein(a, b) / max(len(a), len(b))


def jaro(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    match_dist = max(len(a), len(b)) // 2 - 1
    a_match = [False] * len(a)
    b_match = [False] * len(b)
    matches = 0
    for i, ca in enumerate(a):
        lo = max(0, i - match_dist)
        hi = min(i + match_dist + 1, len(b))
        for j in range(lo, hi):
            if not b_match[j] and b[j] == ca:
                a_match[i] = b_match[j] = True
                matches += 1
                break
    if matches == 0:
        return 0.0
    # count transpositions
    t = 0
    k = 0
    for i in range(len(a)):
        if a_match[i]:
            while not b_match[k]:
                k += 1
            if a[i] != b[k]:
                t += 1
            k += 1
    t //= 2
    m = matches
    return (m / len(a) + m / len(b) + (m - t) / m) / 3.0


def jaro_winkler(a: str, b: str, p: float = 0.1, max_prefix: int = 4) -> float:
    j = jaro(a, b)
    prefix = 0
    for ca, cb in zip(a, b):
        if ca == cb:
            prefix += 1
            if prefix == max_prefix:
                break
        else:
            break
    return j + prefix * p * (1 - j)


def _ngrams(s: str, n: int = 3) -> Counter:
    s = f"  {s} "          # pad so prefixes/suffixes get weight
    return Counter(s[i:i + n] for i in range(len(s) - n + 1))


def ngram_cosine(a: str, b: str, n: int = 3) -> float:
    if not a or not b:
        return 0.0
    va, vb = _ngrams(a, n), _ngrams(b, n)
    common = set(va) & set(vb)
    if not common:
        return 0.0
    dot = sum(va[g] * vb[g] for g in common)
    na = math.sqrt(sum(v * v for v in va.values()))
    nb = math.sqrt(sum(v * v for v in vb.values()))
    return dot / (na * nb) if na and nb else 0.0


def token_set_ratio(a_tokens, b_tokens, sim=jaro_winkler) -> float:
    """Order-invariant similarity between two token tuples.

    Greedy best-match pairs each token of the smaller set with its best remaining
    partner in the larger set. The result blends two views:

    * ``mean_over_larger`` — sum of pair scores / size of the *larger* set, so
      extra/unmatched tokens dilute the score; and
    * ``weakest`` — the minimum pair score, so **every** required token must
      align.

    The weakest-link term is essential for names: "Sana Singh" vs "Sana Sheikh"
    share one token but must NOT match, otherwise single-token bridges chain
    unrelated people together under transitive-closure clustering.
    """
    a = list(a_tokens)
    b = list(b_tokens)
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    used = [False] * len(b)
    scores: list[float] = []
    for ta in a:
        best, best_j = 0.0, -1
        for j, tb in enumerate(b):
            if used[j]:
                continue
            s = sim(ta, tb)
            if s > best:
                best, best_j = s, j
        if best_j >= 0:
            used[best_j] = True
        scores.append(best)
    mean_over_larger = sum(scores) / len(b)     # extra tokens dilute
    weakest = min(scores)                        # every required token must align
    return 0.5 * weakest + 0.5 * mean_over_larger
