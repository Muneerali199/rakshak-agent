"""Configuration knobs for the RAKSHAK synthetic benchmark generator.

Everything is driven off a single integer ``seed`` so a given config reproduces
byte-for-byte identical output — a hard requirement for a benchmark (paper §21).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class GenConfig:
    # reproducibility
    seed: int = 42

    # world size
    num_persons: int = 50            # distinct *real* people (ground-truth entities)
    num_false_pairs: int = 6         # pairs of DIFFERENT people with near-identical names (traps)
    irrelevant_person_ratio: float = 0.15  # people who appear once, disconnected (noise)

    # record volumes
    num_fir: int = 40                # First Information Reports (has narrative)
    num_cdr: int = 300               # Call Detail Records
    num_fin: int = 120               # financial transactions

    # noise dials (all in [0, 1])
    missing_rate: float = 0.12       # chance a non-key field is dropped
    conflict_rate: float = 0.15      # chance an attribute conflicts across mentions
    devanagari_rate: float = 0.30    # chance a name mention is written in Devanagari
    typo_rate: float = 0.25          # chance a romanized name gets a spelling perturbation
    evolving_phone_rate: float = 0.25  # people who switch phone number mid-timeline

    # timeline
    start_date: str = "2026-01-01"   # ISO date; all events fall within [start, start + days)
    days: int = 120

    # languages used for FIR narratives
    languages: tuple[str, ...] = ("en", "hi", "hi-en")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["languages"] = list(self.languages)
        return d


# A larger, closer-to-paper preset (~thousands of records). Still fast, pure-Python.
LARGE = GenConfig(
    num_persons=400,
    num_false_pairs=40,
    num_fir=400,
    num_cdr=6000,
    num_fin=1500,
    days=365,
)
