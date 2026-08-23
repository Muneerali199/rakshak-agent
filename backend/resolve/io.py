"""Load the synthgen benchmark and assemble resolver inputs (paper §7.1, §7.2).

Two jobs:

* **Deterministic keys** for high-confidence identifiers (phone → E.164 digits,
  account, vehicle plate, location) — the §9.2 "identifier similarity" path where
  an exact normalized match is a certain merge.
* **PersonRef assembly** — every PERSON mention is enriched with the demographic
  attributes (age, home address) needed for the attribute feature. Narrative
  mentions inherit attributes from the FIR's structured complainant/accused block
  whose name they match, realizing the proposal's "graph-neighborhood / co-occurring
  context" idea in a lightweight, within-record form.

Only the *records* are read as pipeline input; ``true_id`` in ``mentions.jsonl`` is
deliberately ignored here (it is the answer key, consumed only by the evaluator).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .features import PersonRef
from .normalize import normalize_name
from .similarity import jaro_winkler, token_set_ratio

DETERMINISTIC_TYPES = {"PHONE", "ACCOUNT", "VEHICLE", "LOCATION"}


def load_jsonl(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_benchmark(in_dir: str | Path) -> dict:
    d = Path(in_dir)
    return {
        "fir": load_jsonl(d / "fir.jsonl"),
        "cdr": load_jsonl(d / "cdr.jsonl"),
        "fin": load_jsonl(d / "fin.jsonl"),
        "mentions": load_jsonl(d / "mentions.jsonl"),
    }


# --------------------------------------------------------------------------- #
# Deterministic identifier normalization (§7.2)
# --------------------------------------------------------------------------- #
def deterministic_key(entity_type: str, surface: str) -> str:
    if entity_type == "PHONE":
        digits = re.sub(r"\D", "", surface)          # E.164-style: keep digits only
        return digits[-10:] if len(digits) >= 10 else digits
    if entity_type == "ACCOUNT":
        return re.sub(r"\s", "", surface).upper()
    if entity_type == "VEHICLE":
        return re.sub(r"[^0-9A-Za-z]", "", surface).upper()
    if entity_type == "LOCATION":
        return surface.strip().casefold()
    return surface.strip().casefold()


# --------------------------------------------------------------------------- #
# PersonRef assembly with within-record attribute inheritance
# --------------------------------------------------------------------------- #
def _fir_person_blocks(record: dict) -> list[dict]:
    """Flatten a FIR's complainant + accused blocks into attribute carriers."""
    blocks = []
    comp = record.get("complainant")
    if comp:
        blocks.append(comp)
    for acc in record.get("accused", []):
        blocks.append(acc)
    return blocks


def _best_block(surface: str, blocks: list[dict]) -> dict | None:
    """Match a mention surface to the structured block with the closest name."""
    target = normalize_name(surface)
    best, best_score = None, 0.0
    for blk in blocks:
        score = token_set_ratio(target, normalize_name(blk.get("name", "")), sim=jaro_winkler)
        if score > best_score:
            best, best_score = blk, score
    return best if best_score >= 0.6 else None


def build_person_refs(bench: dict) -> list[PersonRef]:
    """One PersonRef per PERSON mention, with attributes joined from its FIR record."""
    fir_by_id = {r["record_id"]: r for r in bench["fir"]}
    refs: list[PersonRef] = []
    for m in bench["mentions"]:
        if m["entity_type"] != "PERSON":
            continue
        age = address = None
        rec = fir_by_id.get(m["record_id"])
        if rec is not None:
            blk = _best_block(m["surface"], _fir_person_blocks(rec))
            if blk is not None:
                age = blk.get("age")
                address = blk.get("address")
        refs.append(PersonRef.build(m["mention_id"], m["surface"], age=age, address=address))
    return refs
