"""Surface-form noise: turn a canonical entity into the messy strings a real
record would contain — transliteration, honorifics, spelling drift, name-order
swaps, noisy addresses, and lakh/crore money notation (paper §7.2, §21.1).

Every function is pure w.r.t. the ``rng`` passed in, so output is reproducible.
"""
from __future__ import annotations

import random

from .pools import NameEntry

# small, deliberately imperfect romanization substitutions
_SUBS = [
    ("ph", "f"), ("f", "ph"),
    ("aa", "a"), ("ee", "i"), ("oo", "u"),
    ("v", "w"), ("w", "v"),
    ("y", "i"),
]

_MALE_HON = ["Sh.", "Shri", "Mr."]
_FEMALE_HON = ["Smt.", "Ms."]


def _typo(rng: random.Random, s: str) -> str:
    """Apply one mild perturbation to a romanized string."""
    if len(s) < 3:
        return s
    op = rng.choice(["swap", "drop", "double", "sub"])
    i = rng.randrange(len(s) - 1)
    if op == "swap":
        return s[:i] + s[i + 1] + s[i] + s[i + 2:]
    if op == "drop":
        return s[:i] + s[i + 1:]
    if op == "double":
        return s[:i] + s[i] + s[i:]
    # substitution
    lowered = s.lower()
    rng.shuffle(subs := list(_SUBS))
    for a, b in subs:
        pos = lowered.find(a)
        if pos != -1:
            return s[:pos] + b + s[pos + len(a):]
    return s


def name_form(rng: random.Random, entry: NameEntry, *, devanagari: bool, typo_rate: float) -> str:
    """Pick one surface form for a single name token."""
    if devanagari and entry.devanagari:
        return entry.devanagari
    form = rng.choice([entry.canonical, *entry.variants])
    if rng.random() < typo_rate:
        form = _typo(rng, form)
    r = rng.random()
    if r < 0.08:
        form = form.lower()
    elif r < 0.12:
        form = form.upper()
    return form


def full_name(rng: random.Random, person, cfg) -> tuple[str, str]:
    """Return ``(surface_name, lang)`` for a person mention."""
    use_dev = rng.random() < cfg.devanagari_rate
    first = name_form(rng, person.first, devanagari=use_dev, typo_rate=cfg.typo_rate)
    last = name_form(rng, person.surname, devanagari=use_dev, typo_rate=cfg.typo_rate)
    parts = [first, last]
    if not use_dev and rng.random() < 0.12:   # occasional surname-first order
        parts.reverse()
    name = " ".join(parts)
    if not use_dev and rng.random() < 0.22:    # occasional honorific prefix
        hon = rng.choice(_MALE_HON if person.gender == "M" else _FEMALE_HON)
        name = f"{hon} {name}"
    return name, ("hi" if use_dev else "en")


def noisy_address(rng: random.Random, location, cfg) -> str:
    hn = f"{rng.choice(['House No', 'H.No', 'HNo', 'makan no'])} {rng.randint(1, 220)}"
    road = rng.choice(["Road", "Rd", "Rd.", "gali", "St."])
    parts = [hn, f"{location.locality} {road}", location.district]
    if rng.random() < 0.5:
        parts.append(location.state)
    if rng.random() < 0.2:      # sometimes house number is missing
        parts = parts[1:]
    return ", ".join(parts)


def _indian_commas(value: int) -> str:
    s = str(value)
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups) + "," + tail


def amount_form(rng: random.Random, value: int) -> str:
    """Render an INR amount in one of several noisy notations."""
    forms = [f"₹{_indian_commas(value)}", f"Rs. {value}", f"{value}/-", f"INR {value}"]
    if value >= 100000:
        lakhs = value / 100000
        forms.append(f"{int(lakhs)} lakh" if lakhs == int(lakhs) else f"{lakhs:.1f} lakh")
    if value >= 10000000:
        forms.append(f"{value / 10000000:.2f} crore")
    return rng.choice(forms)
