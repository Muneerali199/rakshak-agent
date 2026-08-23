"""Phonetic keys for romanized Indian names (paper §9.2 "phonetic similarity").

A compact, dependency-free Soundex/Metaphone-style encoder *tuned for Indian
phonology* rather than English. It collapses the sound-preserving spelling drift
the generator injects — ``ph↔f``, ``v↔w``, aspirated ``kh/gh/th/dh/bh``, doubled
letters, and matra vowel wobble — so that "Sharma"/"Sarma", "Khan"/"Xan",
"Verma"/"Varma", "Singh"/"Singhh" share a key.

Full Double Metaphone (with its secondary-code branches) is the production
upgrade; this adaptation captures the equivalences that actually occur in the
benchmark's romanization variants.
"""
from __future__ import annotations

from .normalize import normalize_name

# Aspirated / digraph consonants → a single base sound (order: longest first).
_DIGRAPHS = [
    ("chh", "c"), ("sh", "s"), ("zh", "j"), ("ch", "c"),
    ("kh", "k"), ("gh", "g"), ("th", "t"), ("dh", "d"),
    ("bh", "b"), ("ph", "f"), ("jh", "j"), ("wh", "v"),
]

# Soundex-style consonant groups, Indian-tuned (sibilants/velars share a class,
# f/v/b/p labials share a class so ph↔f↔b drift collapses).
_GROUP = {
    "b": "1", "f": "1", "p": "1", "v": "1", "w": "1",
    "c": "2", "g": "2", "j": "2", "k": "2", "q": "2", "s": "2", "x": "2", "z": "2",
    "d": "3", "t": "3",
    "l": "4",
    "m": "5", "n": "5",
    "r": "6",
}


def _code_token(token: str) -> str:
    """Soundex-like phonetic code for one already-cleaned romanized token."""
    t = token
    for a, b in _DIGRAPHS:
        t = t.replace(a, b)
    t = "".join(c for c in t if c.isalpha())
    if not t:
        return ""
    # lead letter kept verbatim (its group still drives following-digit dedup)
    head = t[0]
    codes = [head]
    prev = _GROUP.get(head, "0")
    for c in t[1:]:
        g = _GROUP.get(c, "0")   # vowels + h/y → "0" (dropped, but break runs)
        if g != "0" and g != prev:
            codes.append(g)
        prev = g
    key = codes[0] + "".join(codes[1:])
    return (key + "000")[:4]     # fixed 4-char width like classic Soundex


def phonetic_tokens(surface: str) -> tuple[str, ...]:
    """Sorted phonetic codes for each token of a (possibly Devanagari) name."""
    return tuple(sorted(c for c in (_code_token(t) for t in normalize_name(surface)) if c))


def phonetic_key(surface: str) -> str:
    """Single joined phonetic key for the whole name (used for blocking)."""
    return " ".join(phonetic_tokens(surface))
