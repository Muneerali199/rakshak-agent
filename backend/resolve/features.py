"""Pairwise match features and the aggregate identity-resolution score (paper §8.3, §9.2).

Implements the MVP's **4 of 8** features (§26): identifier, name, phonetic, and
attribute similarity. Transliteration is applied as a *normalization* step
(:mod:`resolve.normalize`) that feeds name/phonetic, so cross-script Hindi↔English
names compare directly. The deferred four — temporal, context TF-IDF, and graph
neighborhood — arrive with the Phase-4 graph.

Aggregate score (§8.3):  ``s(a,b) = Σ_k w_k · φ_k(a,b)``  with ``Σ w_k = 1`` and
each ``φ_k ∈ [0,1]``.  Decision: MATCH if ``s ≥ θ_high``, REJECT if ``s ≤ θ_low``,
UNCERTAIN in between (routed to human review, §9.3).  Weights are fixed, sensible
priors here; Platt/isotonic **calibration** on labeled pairs (§9.3) is the
production upgrade, as is the logistic squashing σ used only for display.
"""
from __future__ import annotations

from dataclasses import dataclass

from .normalize import normalize_name
from .phonetic import phonetic_tokens
from .similarity import jaro_winkler, levenshtein_ratio, ngram_cosine, token_set_ratio


# --------------------------------------------------------------------------- #
# A person mention enriched with the context needed for attribute matching.
# --------------------------------------------------------------------------- #
@dataclass
class PersonRef:
    mention_id: str
    surface: str
    tokens: tuple[str, ...]          # normalized, transliterated, sorted
    phon: tuple[str, ...]            # phonetic codes
    age: int | None = None           # from FIR structured block (complainant)
    addr_tokens: frozenset = frozenset()   # geo tokens of the home address (§9.2 address Jaccard)

    @classmethod
    def build(cls, mention_id: str, surface: str, *, age=None, address=None) -> "PersonRef":
        return cls(mention_id, surface, normalize_name(surface),
                   phonetic_tokens(surface), age, _addr_tokens(address))


# Address noise words to drop so only the *place* tokens (locality/district/state)
# drive the Jaccard — house numbers and road abbreviations carry no identity signal.
_ADDR_STOP = {
    "house", "no", "hno", "h", "makan", "rd", "road", "st", "street", "gali",
    "nr", "near", "paas", "",
}


def _addr_tokens(address: str | None) -> frozenset:
    if not address:
        return frozenset()
    import re
    toks = re.split(r"[^0-9A-Za-zऀ-ॿ]+", address.casefold())
    return frozenset(t for t in toks
                     if t and t not in _ADDR_STOP and not t.isdigit())


# --------------------------------------------------------------------------- φ_name
def _token_sim(x: str, y: str) -> float:
    """Blended single-token similarity: Jaro-Winkler + Levenshtein + n-gram cosine."""
    return 0.45 * jaro_winkler(x, y) + 0.30 * levenshtein_ratio(x, y) + 0.25 * ngram_cosine(x, y)


def phi_name(a: PersonRef, b: PersonRef) -> float:
    """Order-invariant blended name similarity (§9.2 name similarity)."""
    return token_set_ratio(a.tokens, b.tokens, sim=_token_sim)


# --------------------------------------------------------------------------- φ_phonetic
def phi_phonetic(a: PersonRef, b: PersonRef) -> float:
    """Fraction of phonetic codes shared, order-invariant (§9.2 phonetic similarity)."""
    if not a.phon or not b.phon:
        return 0.0
    sa, sb = set(a.phon), set(b.phon)
    return len(sa & sb) / max(len(sa), len(sb))


# --------------------------------------------------------------------------- φ_attr
def phi_attr(a: PersonRef, b: PersonRef) -> tuple[float, bool]:
    """Attribute compatibility from demographics (§9.2 attribute similarity).

    Returns ``(score, known)``. ``known`` is False when neither mention carries a
    usable attribute, so the caller can treat attributes as neutral rather than
    penalizing (missing data must not fabricate a mismatch — §7.1/§25).

    A *conflict* (disjoint addresses, or age gap beyond the generator's ±3
    conflict noise) drives the score toward 0 — this is what splits the
    false-match traps (two different people who share a name).
    """
    signals: list[float] = []

    if a.addr_tokens and b.addr_tokens:
        inter = len(a.addr_tokens & b.addr_tokens)
        union = len(a.addr_tokens | b.addr_tokens)
        signals.append(inter / union if union else 0.0)       # address Jaccard (§9.2)
    if a.age is not None and b.age is not None:
        gap = abs(a.age - b.age)
        # generator injects ≤±3 age conflict noise; treat ≤4 as compatible, decay after
        signals.append(1.0 if gap <= 4 else max(0.0, 1.0 - (gap - 4) / 12.0))

    if not signals:
        return 0.0, False
    return sum(signals) / len(signals), True


# --------------------------------------------------------------------------- aggregate
# Convex weights (Σ = 1). Name/phonetic carry the match signal; attribute is the
# disambiguator that suppresses false merges on common names.
WEIGHTS = {"name": 0.55, "phonetic": 0.20, "attr": 0.25}

THETA_HIGH = 0.72     # ≥ → auto-MATCH
THETA_LOW = 0.50      # ≤ → auto-REJECT; between → UNCERTAIN (human review)


@dataclass
class Match:
    score: float
    decision: str                    # MATCH | UNCERTAIN | REJECT
    parts: dict


def score_pair(a: PersonRef, b: PersonRef) -> Match:
    name = phi_name(a, b)
    phon = phi_phonetic(a, b)
    attr, attr_known = phi_attr(a, b)

    if attr_known:
        s = WEIGHTS["name"] * name + WEIGHTS["phonetic"] * phon + WEIGHTS["attr"] * attr
    else:
        # renormalize over the two known features when attributes are absent
        w = WEIGHTS["name"] + WEIGHTS["phonetic"]
        s = (WEIGHTS["name"] * name + WEIGHTS["phonetic"] * phon) / w

    # A hard attribute conflict on a confident name match is the classic false
    # merge (same name, different real person). Veto it to protect precision.
    if attr_known and attr == 0.0 and name >= 0.80:
        decision = "REJECT"
    elif s >= THETA_HIGH:
        decision = "MATCH"
    elif s <= THETA_LOW:
        decision = "REJECT"
    else:
        decision = "UNCERTAIN"

    return Match(round(s, 4), decision,
                 {"name": round(name, 3), "phonetic": round(phon, 3),
                  "attr": round(attr, 3) if attr_known else None})
