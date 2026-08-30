"""Multilingual name normalization + Devanagari→Latin transliteration (paper §7.2, §9.2).

Turns the messy surface forms produced by ``synthgen`` (Devanagari, honorifics,
case noise, spelling drift, name-order swaps, romanization variants) back toward a
canonical, comparable representation. Pure standard library — no IndicXlit/ICU
dependency (those are the production upgrade noted in the proposal).

The two public entry points:

* :func:`transliterate` — Devanagari string → romanized Latin (the §9.2
  "transliteration similarity" feature).
* :func:`normalize_name` — full surface name → sorted tuple of clean tokens
  (NFKC, honorific removal, abbreviation expansion, transliteration, casefold),
  order-invariant so "Ram Prasad" and "Prasad Ram" collapse together.
"""
from __future__ import annotations

import unicodedata

# --------------------------------------------------------------------------- #
# Devanagari → Latin transliteration
#
# A compact, dependency-free romanizer covering the vowels, consonants, matras
# and diacritics that appear in the generator's name pools. It is deliberately
# lossy (e.g. inherent-'a' handling is heuristic) because downstream phonetic and
# fuzzy matching absorb the residual error — exactly the hybrid design of §9.
# --------------------------------------------------------------------------- #

# Independent vowels
_IVOWEL = {
    "अ": "a", "आ": "aa", "इ": "i", "ई": "ii", "उ": "u", "ऊ": "uu",
    "ऋ": "ri", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "ऍ": "e", "ऑ": "o",
}

# Consonants — bare form (inherent 'a' is appended separately unless a matra or
# virama follows).
_CONS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng",
    "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "ny",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "व": "v", "ळ": "l",
    "श": "sh", "ष": "sh", "स": "s", "ह": "h",
}

# Consonant + nukta (़) → its distinct romanization (e.g. ख़ान → khan, फ़ातिमा → fatima)
_NUKTA = {
    "क": "q", "ख": "kh", "ग": "g", "ज": "z", "ड": "r", "ढ": "rh",
    "फ": "f", "य": "y",
}

# Dependent vowel signs (matras) — replace the inherent 'a'
_MATRA = {
    "ा": "aa", "ि": "i", "ी": "ii", "ु": "u", "ू": "uu", "ृ": "ri",
    "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ॉ": "o", "ॅ": "e",
}

_VIRAMA = "्"        # halant — suppresses the inherent vowel
_NUKTA_SIGN = "़"
_ANUSVARA = {"ं", "ँ", "ॐ"}   # nasalization → 'n'
_VISARGA = "ः"


def transliterate(text: str) -> str:
    """Romanize a (possibly Devanagari) string; leaves Latin text untouched.

    Prefers AI4Bharat's IndicXlit neural model when it is locally installed
    (:mod:`resolve.indic_xlit` — offline, no API key); otherwise this built-in
    rule-based romanizer runs. The engine in use is disclosed via
    :func:`resolve.indic_xlit.engine_name`.
    """
    from . import indic_xlit                      # local import: optional stack
    if has_devanagari(text):
        neural = indic_xlit.xlit(text)
        if neural is not None:
            return neural
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        cons = _CONS.get(ch)
        if cons is not None:
            # optional nukta immediately after the consonant
            if i + 1 < n and text[i + 1] == _NUKTA_SIGN:
                cons = _NUKTA.get(ch, cons)
                i += 1
            out.append(cons)
            nxt = text[i + 1] if i + 1 < n else ""
            if nxt in _MATRA:
                out.append(_MATRA[nxt])
                i += 2
            elif nxt == _VIRAMA:
                i += 2                     # conjunct — no vowel
            elif nxt == "" or nxt.isspace():
                i += 1                     # Hindi schwa deletion: drop word-final inherent 'a'
            else:
                out.append("a")           # inherent vowel
                i += 1
            continue
        if ch in _IVOWEL:
            out.append(_IVOWEL[ch])
        elif ch in _ANUSVARA:
            out.append("n")
        elif ch == _VISARGA:
            out.append("h")
        elif ch in (_VIRAMA, _NUKTA_SIGN):
            pass                           # stray sign — skip
        else:
            out.append(ch)                 # spaces, Latin, punctuation
        i += 1
    return "".join(out)


def has_devanagari(text: str) -> bool:
    return any("ऀ" <= c <= "ॿ" for c in text)


# --------------------------------------------------------------------------- #
# Name normalization
# --------------------------------------------------------------------------- #

# Honorifics the generator prepends (variants.py: _MALE_HON / _FEMALE_HON) plus a
# few common extras. NB: "md"/"mohd" are NOT here — in this data they are always
# name tokens (→ Mohammad), never honorifics, so they must survive to expansion.
_HONORIFICS = {
    "sh", "shri", "sri", "mr", "mrs", "ms", "smt", "km", "kumari", "dr",
    "sh.", "mr.", "ms.", "smt.",
}

# §7.2 "expansion of abbreviations ('Mohd' → 'Mohammad')". Kept small and general:
# well-known Indian name abbreviations, not a copy of the benchmark's variant table.
_ABBREV = {
    "mohd": "mohammad", "md": "mohammad", "muhd": "mohammad", "mohmd": "mohammad",
    "mohammed": "mohammad", "muhammad": "mohammad", "mohamad": "mohammad",
    "abdool": "abdul",
}

# Light romanization folding so spelling/transliteration variants converge.
# Applied to already-romanized tokens (order matters: multi-char first).
_FOLD = [
    ("aa", "a"), ("ee", "i"), ("oo", "u"), ("ph", "f"),
    ("ck", "k"), ("kh", "k"), ("gh", "g"), ("sh", "s"), ("zh", "j"),
    ("z", "j"), ("w", "v"), ("y", "i"), ("x", "ks"),
]

_PUNCT = str.maketrans("", "", ".,'`-_/")


def _strip_diacritics(token: str) -> str:
    """Drop combining marks left over from NFKD (e.g. accented Latin)."""
    return "".join(c for c in unicodedata.normalize("NFKD", token)
                   if not unicodedata.combining(c))


def clean_token(token: str) -> str:
    """Normalize one already-transliterated token to a comparable core form."""
    t = _strip_diacritics(token).translate(_PUNCT).casefold().strip()
    t = _ABBREV.get(t, t)
    for a, b in _FOLD:
        t = t.replace(a, b)
    # collapse consecutive duplicate letters ("siingh" → "singh", "shharma" → "sharma")
    out, prev = [], ""
    for c in t:
        if c != prev:
            out.append(c)
        prev = c
    return "".join(out)


def normalize_name(surface: str) -> tuple[str, ...]:
    """Surface person-name → sorted tuple of clean tokens (order-invariant).

    Pipeline: NFKC → transliterate Devanagari → tokenize → drop honorifics →
    expand abbreviations + fold spelling → sort. Sorting makes "Ram Prasad" and
    "Prasad Ram" identical, matching the generator's occasional surname-first swap.
    """
    text = unicodedata.normalize("NFKC", surface)
    text = transliterate(text)
    tokens: list[str] = []
    for raw in text.replace(".", " ").split():
        low = raw.casefold().strip(".,'`-_")
        if low in _HONORIFICS:
            continue
        cleaned = clean_token(raw)
        if cleaned:
            tokens.append(cleaned)
    return tuple(sorted(tokens))


def normalize_key(surface: str) -> str:
    """A single joined string key for the normalized name (blocking/debug)."""
    return " ".join(normalize_name(surface))
