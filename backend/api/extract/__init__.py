"""Pluggable entity extractor — the model swap-in point (IND_NER_FINETUNE_PLAN §7).

Engines:
* ``regex``  — the engineered baseline (`api.ingest.extract_entities`), always on.
* ``hybrid`` — regex ∪ (neural model spans when a local NER checkpoint exists);
  the neural side is loaded lazily from ``RAKSHAK_MODEL_PATH`` (or
  ``backend/models/indner/``) with ``local_files_only=True`` and **never** blocks
  ingest when absent: the engine falls back to regex and discloses that truth.
* ``indner`` — neural only (useful for the eval harness `scripts/eval_indner.py`).

The output of any engine is the graph's own `ExtractedEntity` shape, so the
pipeline downstream is untouched. No generative text anywhere: span tagger only,
officer review still gates every graph write.
"""
from __future__ import annotations

import os
from pathlib import Path

from api.ingest import ExtractedEntity, extract_entities

MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "indner"

_ENGINE_NAMES = ("regex", "hybrid", "indner")
_missing = "model not installed — see docs/IND_NER_FINETUNE_PLAN.md (train on Omen, drop weights here)"


def model_path() -> Path | None:
    env = os.environ.get("RAKSHAK_MODEL_PATH")
    cand = Path(env) if env else MODEL_DIR
    if (cand / "config.json").exists() and (cand / "model.safetensors").exists():
        return cand
    return None


def engine_available() -> bool:
    return model_path() is not None


def available() -> bool:
    """Neural NER usable on this box right now (honest)."""
    return engine_available()


class ExtractorUnavailable(Exception):
    pass


_loader = None


def _load():
    global _loader
    if _loader is not None or not engine_available():
        return _loader
    try:
        from transformers import (AutoModelForTokenClassification,
                                  AutoTokenizer, pipeline)
        mp = model_path()
        tok = AutoTokenizer.from_pretrained(str(mp), local_files_only=True)
        model = AutoModelForTokenClassification.from_pretrained(str(mp), local_files_only=True)
        _loader = pipeline("token-classification", model=model, tokenizer=tok,
                           aggregation_strategy="simple")
    except Exception:                                      # noqa: BLE001
        _loader = None
    return _loader


_SCHEMA = {"O": "O", "B-PERSON": "PERSON", "I-PERSON": "PERSON",
           "B-PHONE": "PHONE", "I-PHONE": "PHONE",
           "B-ACCOUNT": "ACCOUNT", "I-ACCOUNT": "ACCOUNT",
           "B-VEHICLE": "VEHICLE", "I-VEHICLE": "VEHICLE",
           "B-IPC": "IPC", "I-IPC": "IPC",
           "B-LOCATION": "LOCATION", "I-LOCATION": "LOCATION",
           "B-ORGANIZATION": "ORGANIZATION", "I-ORGANIZATION": "ORGANIZATION"}


def _dedup_entities(ents: list[ExtractedEntity]) -> list[ExtractedEntity]:
    seen: set[tuple[str, str]] = set()
    out: list[ExtractedEntity] = []
    for e in ents:
        key = (e.kind, e.normalized.casefold())
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def _neural_entities(text: str) -> list[ExtractedEntity]:
    pipe = _load()
    if pipe is None:
        return []
    out: list[ExtractedEntity] = []
    try:
        raw = pipe(text)
    except Exception:                                      # noqa: BLE001
        return []
    for span in raw:
        kind = _SCHEMA.get(span.get("entity", "").upper(), span.get("entity", ""))
        surface = span.get("word", "").strip()
        if not surface or kind == "O":
            continue
        start = int(span.get("start", -1))
        end = int(span.get("end", -1))
        ent = ExtractedEntity(kind=kind, surface=surface,
                              normalized=surface, span=(start, end))
        if ent.kind and ent.surface:
            out.append(ent)
    return _dedup_entities(out)


def regex_entities(text: str) -> list[ExtractedEntity]:
    return _dedup_entities(extract_entities(text))


def hybrid_entities(text: str) -> dict:
    rex = regex_entities(text)
    neu = _neural_entities(text) if engine_available() else []
    rex_by = {(e.kind, e.normalized.casefold()): e for e in rex}
    neu_only: list[ExtractedEntity] = []
    disagree: list[dict] = []
    for e in neu:
        key = (e.kind, e.normalized.casefold())
        if key in rex_by:
            continue
        # another kind on the same surface → human decides, regex wins ties
        conflict = next((r for r in rex if r.normalized.casefold() == e.normalized.casefold()), None)
        if conflict is not None:
            disagree.append({"surface": e.surface, "regex": conflict.kind,
                             "model": e.kind, "resolved": conflict.kind})
        else:
            neu_only.append(e)
    final = _dedup_entities(rex + neu_only)
    return {
        "entities": [{"kind": e.kind, "surface": e.surface, "normalized": e.normalized,
                      "span": list(e.span)} for e in final],
        "regex_entities": [{"kind": e.kind, "surface": e.surface} for e in rex],
        "model_entities": [{"kind": e.kind, "surface": e.surface} for e in neu],
        "agreements": [{"kind": e.kind, "surface": e.surface} for e in rex if
                       (e.kind, e.normalized.casefold()) in
                       {(x.kind, x.normalized.casefold()) for x in neu}],
        "disagreements": disagree,
        "engine": "hybrid",
        "model": "regex-only" if not neu else "local-ner",
        "disclosure": (f"hybrid extractor: regex baseline + "
                       f"{'local NER weights' if neu else 'no local NER weights (regex-only path)'} — "
                       "spans are proposals; officer review precedes any graph write"),
    }


def run(text: str, engine: str = "hybrid") -> dict:
    if engine not in _ENGINE_NAMES:
        raise ExtractorUnavailable(f"unknown engine {engine!r}; choose from {_ENGINE_NAMES}")
    if engine == "regex":
        ents = regex_entities(text)
        return {"entities": [{"kind": e.kind, "surface": e.surface,
                              "normalized": e.normalized, "span": list(e.span)} for e in ents],
                "engine": "regex", "model": "builtin-regex", "disagreements": [],
                "disclosure": "regex baseline extractor (builtin, deterministic)"}
    if engine == "indner":
        neu = _neural_entities(text)
        return {"entities": [{"kind": e.kind, "surface": e.surface,
                              "normalized": e.normalized, "span": list(e.span)} for e in neu],
                "engine": "indner",
                "model": "local-ner" if neu else _missing,
                "disclosure": "neural extractor (local weights) — else empty, model not installed"}
    return hybrid_entities(text)