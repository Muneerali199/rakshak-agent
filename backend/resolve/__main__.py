"""CLI:  python -m resolve --in output            # resolve + evaluate against ground truth
       python -m resolve --in output --out pred.json --no-eval
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .cluster import resolve
from .evaluate import evaluate
from .io import load_benchmark


def main() -> None:
    p = argparse.ArgumentParser(
        prog="resolve",
        description="Resolve RAKSHAK entity mentions to clusters and evaluate (paper §9, §23).",
    )
    p.add_argument("--in", dest="in_dir", default="output",
                   help="benchmark directory produced by `python -m synthgen`")
    p.add_argument("--out", help="write predicted clusters as JSON to this path")
    p.add_argument("--no-eval", action="store_true",
                   help="skip evaluation (e.g. when ground_truth.json is absent)")
    p.add_argument("--verbose", action="store_true", help="print the per-type breakdown")
    args = p.parse_args()

    bench = load_benchmark(args.in_dir)
    pred = resolve(bench)
    print(f"✓ resolved {pred['stats']['person_mentions']} person mentions "
          f"+ {pred['stats']['deterministic_clusters']} deterministic groups "
          f"→ {len(pred['clusters'])} clusters")
    print(json.dumps(pred["stats"], indent=2))

    if args.out:
        Path(args.out).write_text(json.dumps(pred["clusters"], indent=2), encoding="utf-8")
        print(f"✓ wrote clusters to {args.out}")

    if not args.no_eval:
        gt_path = Path(args.in_dir) / "ground_truth.json"
        gt = json.loads(gt_path.read_text(encoding="utf-8"))
        report = evaluate(pred, gt)
        if not args.verbose:
            report.pop("by_type", None)
        print("\n=== Evaluation (paper §23) ===")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        passed = all(report["targets"].values())
        print(f"\n{'✓ ALL §23 TARGETS MET' if passed else '✗ some §23 targets missed'}")


if __name__ == "__main__":
    main()
