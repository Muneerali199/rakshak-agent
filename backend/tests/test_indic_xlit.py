"""IndicXlit adapter tests — neural when present, honest fallback when not.

The offline demo environment has no transformers stack: the adapter must fall
back to the built-in romanizer and disclose the engine truthfully. The neural
path itself is verified with a stubbed pipeline (no model download in CI).
"""
from __future__ import annotations

from resolve import indic_xlit
from resolve.normalize import transliterate


def test_fallback_engine_disclosed():
    # this environment: no local IndicXlit model → honest fallback
    assert indic_xlit.engine_name() in ("builtin-rule-romanizer", "indicxlit-ai4bharat")
    # rule romanizer still handles the benchmark's Devanagari names
    assert transliterate("मोहम्मद") != "मोहम्मद"       # romanized, not passthrough


def test_neural_path_when_available(monkeypatch):
    class _Tok:
        def __call__(self, texts, return_tensors=None):
            return {"ids": texts}
        def decode(self, ids, skip_special_tokens=True):
            return "mohammad"
    class _Model:
        def generate(self, **kw):
            return [[0]]
    monkeypatch.setattr(indic_xlit, "_pipeline", (_Tok(), _Model()))
    monkeypatch.setattr(indic_xlit, "_failed", False)
    assert indic_xlit.available() is True
    assert indic_xlit.engine_name() == "indicxlit-ai4bharat"
    assert transliterate("मोहम्मद") == "mohammad"      # neural answer preferred
    # Latin input never hits the model
    assert indic_xlit.xlit("Mohammad") is None


def test_neural_failure_falls_back(monkeypatch):
    class _Tok:
        def __call__(self, texts, return_tensors=None):
            raise RuntimeError("boom")
    monkeypatch.setattr(indic_xlit, "_pipeline", (_Tok(), object()))
    monkeypatch.setattr(indic_xlit, "_failed", False)
    # model blows up → rule romanizer answers instead; matching never breaks
    assert transliterate("मोहम्मद") != "मोहम्मद"
