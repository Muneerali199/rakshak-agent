"""CLI:  python -m synthgen --seed 42 --out output"""
from __future__ import annotations

import argparse
import json

from .config import LARGE, GenConfig


def main() -> None:
    p = argparse.ArgumentParser(
        prog="synthgen",
        description="Generate the RAKSHAK synthetic crime-intelligence benchmark.",
    )
    p.add_argument("--seed", type=int, default=42, help="RNG seed (reproducible output)")
    p.add_argument("--out", default="output", help="output directory")
    p.add_argument("--preset", choices=["default", "large"], default="default",
                   help="'large' ≈ thousands of records")
    # optional overrides
    p.add_argument("--persons", type=int, help="number of distinct people")
    p.add_argument("--fir", type=int, help="number of FIRs")
    p.add_argument("--cdr", type=int, help="number of CDRs")
    p.add_argument("--fin", type=int, help="number of financial transfers")
    p.add_argument("--days", type=int, help="timeline length in days")
    args = p.parse_args()

    base = LARGE if args.preset == "large" else GenConfig()
    cfg = GenConfig(
        seed=args.seed,
        num_persons=args.persons or base.num_persons,
        num_false_pairs=base.num_false_pairs,
        irrelevant_person_ratio=base.irrelevant_person_ratio,
        num_fir=args.fir or base.num_fir,
        num_cdr=args.cdr or base.num_cdr,
        num_fin=args.fin or base.num_fin,
        missing_rate=base.missing_rate,
        conflict_rate=base.conflict_rate,
        devanagari_rate=base.devanagari_rate,
        typo_rate=base.typo_rate,
        evolving_phone_rate=base.evolving_phone_rate,
        start_date=base.start_date,
        days=args.days or base.days,
        languages=base.languages,
    )

    from .generate import generate  # imported here so --help stays instant
    manifest = generate(cfg, args.out)
    print(f"✓ wrote benchmark to {args.out}/  (seed={cfg.seed})")
    print(json.dumps(manifest["counts"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
