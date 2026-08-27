"""Experiment A — entity-resolution baselines vs the hybrid pipeline (paper §22/§24).

Run standalone:
    cd app/backend && python -m experiments.experiment_a
"""
from __future__ import annotations

import json
from pathlib import Path

from resolve import evaluate, load_benchmark, resolve
from resolve.baselines import exact_baseline, fuzzy_baseline


def run(bench: dict, gt: dict) -> dict:
    return {
        "exact": evaluate(exact_baseline(bench), gt),
        "fuzzy": evaluate(fuzzy_baseline(bench), gt),
        "hybrid": evaluate(resolve(bench), gt),
    }


def _fmt(m: dict) -> str:
    p, r, f = m["pairwise"]["precision"], m["pairwise"]["recall"], m["pairwise"]["f1"]
    return f"P {p:.3f}  R {r:.3f}  F1 {f:.3f}"


def main() -> None:
    bench = load_benchmark(Path(__file__).resolve().parent.parent / "output")
    gt = json.loads((Path(__file__).resolve().parent.parent / "output" / "ground_truth.json")
                    .read_text(encoding="utf-8"))
    res = run(bench, gt)

    print("Experiment A — entity resolution on seed-42 benchmark "
          f"({res['hybrid']['coverage']['scored_mentions']} mentions)\n")
    print(f"{'method':<10} {'pairwise P/R/F1':<28} {'false merge':<13} {'false split':<13} traps")
    for name in ("exact", "fuzzy", "hybrid"):
        m = res[name]
        print(f"{name:<10} {_fmt(m):<28} {m['false_merge_rate']:<13} {m['false_split_rate']:<13} "
              f"{m['false_match_traps']['merged']}/{m['false_match_traps']['total']}")

    out = Path(__file__).resolve().parent.parent.parent / "docs" / "EXPERIMENT_A.json"
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nsaved → {out}")


if __name__ == "__main__":
    main()
