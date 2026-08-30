"""IndicXlit adapter — AI4Bharat (IIT Madras) neural transliteration, optional.

The production path for cross-script name matching: AI4Bharat's IndicXlit model
(``ai4bharat/IndicXlit``, 11 Indic scripts ↔ Latin, open-source, runs fully
offline once downloaded — no API key, no cloud call, MeghRaj-ready).

Design rule — **zero new hard dependencies**: the core stays stdlib-only and the
demo stays air-gapped. If ``transformers`` + a locally cached IndicXlit model are
present, transliteration is neural; otherwise the built-in rule-based romanizer
(:func:`resolve.normalize.transliterate`) runs instead, and :func:`engine_name`
discloses exactly which engine answered. Nothing here ever phones home.
"""
from __future__ import annotations

_MODEL = "ai4bharat/IndicXlit"
_pipeline = None
_failed = False


def _load():
    """Lazy-load IndicXlit if (and only if) the optional stack is installed."""
    global _pipeline, _failed
    if _pipeline is not None or _failed:
        return _pipeline
    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer  # optional dep
        tok = AutoTokenizer.from_pretrained(_MODEL, local_files_only=True)
        model = AutoModelForSeq2SeqLM.from_pretrained(_MODEL, local_files_only=True)
        _pipeline = (tok, model)
    except Exception:                                  # noqa: BLE001 — absence is normal
        _failed = True
        _pipeline = None
    return _pipeline


def available() -> bool:
    """True when the neural engine is usable in this environment."""
    return _load() is not None


def engine_name() -> str:
    """Honest disclosure: which transliteration engine is answering."""
    return "indicxlit-ai4bharat" if available() else "builtin-rule-romanizer"


def xlit(text: str, target_script: str = "en") -> str | None:
    """Neural transliteration, or None when the engine is unavailable.

    Only Devanagari-bearing inputs are sent to the model; Latin passes through
    unchanged upstream. ``None`` (not an exception) signals "fall back".
    """
    pipe = _load()
    if pipe is None or not any("\u0900" <= c <= "\u097F" for c in text):
        return None
    tok, model = pipe
    try:                                                # pragma: no cover — needs model
        batch = tok([text], return_tensors="pt")
        out = model.generate(**batch, max_length=64)
        return tok.decode(out[0], skip_special_tokens=True)
    except Exception:                                   # noqa: BLE001 — never break matching
        return None
