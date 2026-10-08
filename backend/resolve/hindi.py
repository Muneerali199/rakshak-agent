"""Deterministic English→Hindi demo layer (offline, rule-based, honest labels).

Two jobs:

1. **Latin → Devanagari transliteration** of names / places (the reverse of
   :mod:`resolve.normalize`). A small built-in syllabifying romanizer — demo
   quality, NOT a neural model. The engine id is disclosed in every response
   so a panel never mistakestransliteration for translation, and translation
   for machine understanding.

2. **Known-vocabulary translation** for the fixed, bounded set of labels the
   UI shows in Hindi gear (roles, record kinds, entity types, edges, sections).

Nothing here ever phones home, and no free-text translation is attempted beyond
that bounded vocabulary — that keeps the honesty contract: the system does what
it advertises, offline, deterministically.
"""
from __future__ import annotations

import re

ENGINE = "builtin-hindi-rules-v1"
DISCLOSURE = (
    "English→Hindi demo layer: rule-based Devanagari transliteration + deterministic "
    "translation of the fixed UI vocabulary — offline, no neural model, no API. "
    f"engine = {ENGINE}"
)

# --------------------------------------------------------------------------- #
# Latin → Devanagari (syllabifying)
# --------------------------------------------------------------------------- #

_CONS1 = {
    "k": "क", "g": "ग", "c": "च", "j": "ज", "t": "त", "d": "द", "n": "न",
    "p": "प", "b": "ब", "m": "म", "r": "र", "l": "ल", "v": "व", "w": "व",
    "s": "स", "h": "ह", "y": "य", "f": "फ़", "z": "ज़", "x": "क्ष", "q": "क़",
}
_CONS2 = {
    "chh": "छ", "kh": "ख", "gh": "घ", "th": "थ", "dh": "ध", "ph": "फ",
    "bh": "भ", "sh": "श", "jh": "झ", "ng": "ङ", "ss": "ष",
}
_VOW_L = {"a": "अ", "e": "ए", "i": "इ", "o": "ओ", "u": "उ"}                 # first-letter
_VOW_M = {"e": "े", "i": "ि", "o": "ो", "u": "ु"}                            # matras
_VOW2_L = {"aa": "आ", "ee": "ई", "ii": "ई", "oo": "ऊ", "uu": "ऊ", "ai": "ऐ", "au": "औ"}
_VOW2_M = {"aa": "ा", "ee": "ी", "ii": "ी", "oo": "ू", "uu": "ू", "ai": "ै", "au": "ौ"}

# Exact-token overrides for very common name parts whose conventional spelling the
# syllable scanner can't derive ("Kumar"→कुमार, "Singh"→सिंह). Deterministic, small,
# disclosed. Keys checked case-insensitively per word.
_OVERRIDES = {
    "kumar": "कुमार", "kumaar": "कुमार", "singh": "सिंह", "devi": "देवी",
    "das": "दास", "dass": "दास", "sharma": "शर्मा", "verma": "वर्मा",
    "delhi": "दिल्ली", "mumbai": "मुंबई", "jaipur": "जयपुर", "kanpur": "कानपुर",
    "lucknow": "लखनऊ", "karol": "करोल", "bagh": "बाग़", "nagar": "नगर",
    "gali": "गली", "road": "रोड", "market": "मार्केट", "pvt": "प्राइवेट",
    "ltd": "लिमिटेड", "traders": "ट्रेडर्स", "industries": "इंडस्ट्रीज",
}


def to_devanagari(text: str) -> str:
    """Transliterate a Latin string to Devanagari (already-Devanagari passes through).

    Syllabifies greedily: vowels before consonants become matras, word-final ``a``
    becomes ``ा`` (so "Nehaa"→नेहा, "Sunita"→सुनीता, "Kumaar"→कुमार). Deterministic
    and offline; disclosed engine ``builtin-hindi-rules-v1``.
    """
    from .normalize import has_devanagari
    if has_devanagari(text):
        return text
    out: list[str] = []
    for word in re.split(r"(\s+)", text):
        if not word.strip():
            out.append(word)
            continue
        override = None
        if word.isalpha():
            override = _OVERRIDES.get(word.lower())
        if override is not None:
            out.append(override)
            continue
        i, n = 0, len(word)
        prev_c = False
        while i < n:
            two = word[i:i + 2].lower()
            three = word[i:i + 3].lower() if i + 2 < n else ""
            if word[i].isalpha():
                if three == "chh":
                    out.append("छ"); prev_c = True; i += 3
                    continue
                if two in _VOW2_L:
                    if prev_c:
                        out.append(_VOW2_M[two])
                    else:
                        out.append(_VOW2_L[two])
                    prev_c = False
                    i += 2
                    continue
                ch = word[i].lower()
                if ch in "aeiou":
                    if prev_c:
                        if i + 1 >= n and ch == "a":
                            out.append("ा")      # name-ending a → long ā
                        elif i + 1 >= n and ch == "i":
                            out.append("ी")      # name-ending i → long ī ("Devi")
                        elif ch != "a":
                            out.append(_VOW_M[ch])
                    else:
                        out.append(_VOW_L[ch])
                    prev_c = False
                    i += 1
                    continue
                if two in _CONS2:
                    out.append(_CONS2[two])
                    prev_c = True
                    i += 2
                    continue
                base = _CONS1.get(ch)
                if base is not None:
                    out.append(base)
                    prev_c = True
                    i += 1
                    continue
            out.append(word[i]); prev_c = False; i += 1  # digits, punctuation
    return "".join(out)


# --------------------------------------------------------------------------- #
# Bounded vocabulary translation
# --------------------------------------------------------------------------- #

_TERMS_HI: dict[str, str] = {
    # roles
    "accused": "आरोपित", "complainant": "शिकायतकर्ता", "victim": "पीड़ित",
    "witness": "गवाह",
    # record / evidence kinds
    "fir": "प्राथमिकी", "cdr": "कॉल विवरण", "fin": "वित्तीय विवरण",
    "record": "अभिलेख",
    # entity types
    "person": "व्यक्ति", "phone": "मोबाइल", "account": "खाता",
    "vehicle": "वाहन", "location": "स्थान", "organization": "संस्था",
    # relationship kinds
    "contacted": "संपर्क किया", "uses": "प्रयोग करता है", "owned": "स्वामित्व",
    "located_at": "उपस्थित", "transferred": "हस्तांतरित", "associate_of": "संबंधित",
    # security / status
    "shielded": "संरक्षित", "observed": "प्रमाणित", "inferred": "अनुमानित",
    "match": "मेल", "uncertain": "समीक्षा आवश्यक", "reject": "अस्वीकृत",
    "review": "समीक्षा", "pending": "लंबित", "accepted": "स्वीकृत",
    "rejected": "अस्वीकृत",
    # sections
    "ipc": "धारा",
    # misc UI nouns
    "case": "मामला", "graph": "संजाल", "evidence": "साक्ष्य",
    "risk": "जोखिम", "confident": "विश्वसनीय", "influence": "प्रभाव",
}


def term(text: str) -> str:
    """Translate a known vocabulary item; unknown text passes through unchanged."""
    t = _TERMS_HI.get(text.strip().lower())
    return t if t is not None else text


def terms(texts: list[str]) -> list[str]:
    return [term(t) for t in texts]


def transliterate(texts: list[str]) -> list[str]:
    return [to_devanagari(t) for t in texts]


# --------------------------------------------------------------------------- #
# Profile card (English structured profile → Devanagari profile)
# --------------------------------------------------------------------------- #

_LABELS_HI = {
    "name": "नाम", "father_name": "पिता का नाम", "husband_name": "पति का नाम",
    "dob": "जन्म तिथि", "age": "आयु", "address": "पता", "phone": "मोबाइल",
    "account": "खाता", "vehicle": "वाहन", "occupation": "व्यवसाय",
    "section": "धारा", "police_station": "थाना", "district": "जिला",
    "date": "दिनांक",
}

# kinds / fields whose values are opaque identifiers, never transliterated
_IDENTIFIER_FIELDS = {"phone", "account", "vehicle", "dob", "age", "date", "section"}
_IDENTIFIER_KINDS = {"PHONE", "ACCOUNT", "VEHICLE", "IPC"}

_ENTITY_KIND_HI = {
    "PERSON": "नाम", "PHONE": "मोबाइल", "ACCOUNT": "खाता", "VEHICLE": "वाहन",
    "LOCATION": "स्थान", "ORGANIZATION": "संस्था", "IPC": "धारा",
}


def profile_to_hindi(*, fields: dict | None = None, text: str | None = None,
                     extract=None) -> dict:
    """Turn an English profile (structured fields or raw text) into Devanagari.

    ``fields`` maps keys from ``_LABELS_HI`` to English values (names/places are
    transliterated; section/case values use the vocabulary map). When only
    ``text`` is given, the vault's regex extractor pulls entities first and every
    extracted entity becomes a row. Returns the side-by-side rows plus a ready to
    read Devanagari paragraph. Deterministic, offline.
    """
    items: list[dict] = []
    if fields:
        for key, value in fields.items():
            if value is None or str(value) == "":
                continue
            fkey = str(key).lower()
            label = _LABELS_HI.get(fkey, fkey)
            items.append({
                "field": fkey,
                "label": label,
                "original": str(value),
                "hindi": str(value) if fkey in _IDENTIFIER_FIELDS else _to_profile_value(str(value)),
            })
    if text and extract is not None:
        try:
            entities = extract(text)
        except Exception:                                    # noqa: BLE001 — extraction best-effort
            entities = []
        seen = set()
        for e in entities:
            if e.kind in seen:
                continue
            seen.add(e.kind)
            label = _ENTITY_KIND_HI.get(e.kind, e.kind)
            items.append({
                "field": e.kind,
                "label": label,
                "original": e.surface,
                "hindi": e.surface if e.kind in _IDENTIFIER_KINDS else to_devanagari(e.surface),
            })
    paragraph = " | ".join(
        f"{it['label']}: {it['hindi']}" for it in items
    )
    return {
        "items": items,
        "paragraph": paragraph,
        "engine": ENGINE,
        "disclosure": DISCLOSURE,
    }


def _to_profile_value(value: str) -> str:
    """Value → Devanagari: names/places transliterated, known terms translated."""
    lowered = value.strip().lower()
    if lowered in _TERMS_HI:
        return _TERMS_HI[lowered]
    if re.fullmatch(r"(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,3})", value.strip()):
        return value.strip()                     # dates / ages stay Latin digits
    return to_devanagari(value)