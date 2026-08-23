"""Tests for the synthetic benchmark generator.

Focus: (1) reproducibility by seed, (2) ground-truth integrity, (3) that the
deliberate traps (false pairs, evolving ids) and NER spans are actually correct.

Run either way (no dependencies needed for the first one):
    python3 tests/test_synthgen.py     # standalone runner
    pytest -q                          # if pytest is installed
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# make `synthgen` importable whether run standalone or under pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from synthgen import GenConfig, generate  # noqa: E402


def _load(d: Path) -> dict:
    def jsonl(name: str) -> list[dict]:
        text = (d / name).read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in text if line.strip()]

    return {
        "fir": jsonl("fir.jsonl"),
        "cdr": jsonl("cdr.jsonl"),
        "fin": jsonl("fin.jsonl"),
        "mentions": jsonl("mentions.jsonl"),
        "gt": json.loads((d / "ground_truth.json").read_text(encoding="utf-8")),
        "manifest": json.loads((d / "manifest.json").read_text(encoding="utf-8")),
    }


def test_same_seed_is_byte_identical():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        m1 = generate(GenConfig(seed=42), d / "a")
        m2 = generate(GenConfig(seed=42), d / "b")
        assert m1["files"] == m2["files"]          # identical SHA-256 for every file


def test_different_seed_changes_output():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        m1 = generate(GenConfig(seed=1), d / "a")
        m2 = generate(GenConfig(seed=2), d / "b")
        assert m1["files"]["fir.jsonl"] != m2["files"]["fir.jsonl"]


def test_manifest_counts_match_files():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        man = generate(GenConfig(seed=3), d)
        b = _load(d)
        assert man["counts"]["records"] == {"FIR": len(b["fir"]), "CDR": len(b["cdr"]), "FIN": len(b["fin"])}
        assert man["counts"]["mentions"] == len(b["mentions"])


def test_ground_truth_integrity():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        generate(GenConfig(seed=7), d)
        b = _load(d)
        ents, clusters = b["gt"]["entities"], b["gt"]["clusters"]

        seen = set()
        for m in b["mentions"]:
            if m["true_id"] is not None:
                assert m["true_id"] in ents, f"orphan mention → {m}"
                assert m["mention_id"] in clusters[m["true_id"]]
                seen.add(m["mention_id"])

        flat = [mid for ids in clusters.values() for mid in ids]
        assert len(flat) == len(set(flat))          # no mention counted twice
        assert set(flat) == seen                    # clusters cover exactly the resolved mentions
        for key in clusters:
            assert key in ents                      # every cluster is a real entity


def test_false_match_pairs_are_same_name_different_person():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        generate(GenConfig(seed=5), d)
        b = _load(d)
        ents, pairs = b["gt"]["entities"], b["gt"]["false_match_pairs"]
        assert pairs, "expected some false-match traps"
        for a, c in pairs:
            assert a != c
            assert ents[a]["canonical_name"] == ents[c]["canonical_name"]   # the trap
            assert ents[a]["home"] != ents[c]["home"] or ents[a]["age"] != ents[c]["age"]


def test_evolving_identifiers_consistent():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        generate(GenConfig(seed=9), d)
        b = _load(d)
        ents, evolving = b["gt"]["entities"], b["gt"]["evolving_identifiers"]
        for pid, numbers in evolving.items():
            assert len(numbers) >= 2
            assert numbers == [ents[phid]["number"] for phid in ents[pid]["phones"]]


def test_narrative_ner_spans_align():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        generate(GenConfig(seed=11), d)
        b = _load(d)
        fir_by_id = {r["record_id"]: r for r in b["fir"]}
        checked = 0
        for m in b["mentions"]:
            if m["source"] == "FIR" and m["field"] == "narrative" and m["span"]:
                s, e = m["span"]
                assert fir_by_id[m["record_id"]]["narrative"][s:e] == m["surface"]
                checked += 1
        assert checked > 0                          # spans were actually exercised


if __name__ == "__main__":
    import traceback

    tests = {k: v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)}
    passed = 0
    for name, fn in tests.items():
        try:
            fn()
            print(f"  ok    {name}")
            passed += 1
        except Exception:
            print(f"  FAIL  {name}")
            traceback.print_exc()
    print(f"\n{passed}/{len(tests)} passed")
    raise SystemExit(0 if passed == len(tests) else 1)
