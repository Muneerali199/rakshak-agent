"""RAKSHAK entity-resolution pipeline — Phase 3 (paper §9, §23).

A deterministic, dependency-free hybrid resolver that links noisy, multilingual
entity mentions (FIR / CDR / FIN) back to their real-world entities and scores the
result against the synthgen ground truth.

Implements the MVP's 4-of-8 features (§26): identifier (exact), name
(Levenshtein + Jaro-Winkler + n-gram cosine), phonetic (Indian-tuned Metaphone),
and attribute (age + address Jaccard); transliteration feeds name/phonetic via
normalization. Deferred to Phase 4 (with the graph): temporal, context TF-IDF,
graph-neighborhood.

Quick start:
    from resolve import load_benchmark, resolve, evaluate
    bench = load_benchmark("output")
    pred = resolve(bench)
    import json; gt = json.load(open("output/ground_truth.json"))
    report = evaluate(pred, gt)
"""
from __future__ import annotations

from .cluster import resolve
from .evaluate import evaluate
from .features import score_pair
from .io import load_benchmark, load_jsonl
from .normalize import normalize_name, transliterate
from .phonetic import phonetic_key

__all__ = [
    "resolve", "evaluate", "score_pair", "load_benchmark", "load_jsonl",
    "normalize_name", "transliterate", "phonetic_key",
]
__version__ = "0.1.0"
