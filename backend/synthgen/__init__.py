"""RAKSHAK synthetic benchmark generator.

A deterministic, dependency-free generator that emits synthetic FIR / CDR / FIN
records with real-world noise (transliteration, duplicates, missing/conflicting
fields, evolving identifiers, false-match traps) plus full ground truth — the
substrate for entity resolution, the temporal graph, and anomaly detection.

Quick start:
    from synthgen import GenConfig, generate
    generate(GenConfig(seed=42), out_dir="output")
"""
from __future__ import annotations

from .config import LARGE, GenConfig
from .entities import build_world
from .generate import generate

__all__ = ["GenConfig", "LARGE", "build_world", "generate"]
__version__ = "0.1.0"
