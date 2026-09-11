#!/usr/bin/env python3
"""Composite tech-stack logos onto a draw.io 2x export.

draw.io cannot embed bitmaps (its style parser splits on ';' and truncates
base64 data URIs), so every image slot is filled here, after export.

Geometry contract:
  - output PNG is exported at scale 2, border 0  ->  px = drawio_coord * 2
  - each slot is a white box in the source diagram; this script replaces the
    broken-image glyph with the real tight-cropped logo (full slot height, centered).

Usage:
  python3 composite_logos.py --base technical-approach.png \
      --log-dir ../../technical/logos --out technical-approach.png

Slot table below mirrors technical-approach.drawio (logo0..logo7 at y=784 h=38).
"""
from __future__ import annotations

import argparse
import collections
from pathlib import Path

from PIL import Image

# name -> (x, y, w, h) in drawio coordinates, matching ll0..ll7 labels.
SLOTS = {
    "python":        (258, 784, 38, 38),
    "fastapi":       (393, 784, 38, 38),
    "sqlite":        (530, 784, 34, 38),
    "react":         (661, 784, 43, 38),
    "typescript":    (798, 784, 38, 38),
    "tailwindcss":   (921, 784, 62, 38),
    "vite":          (1067, 784, 40, 38),
    "huggingface":   (1201, 784, 42, 38),
}

SCALE = 2


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="2x draw.io export PNG")
    ap.add_argument("--log-dir", required=True, help="directory of tight-cropped logo PNGs")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    im = Image.open(args.base).convert("RGB")
    log_dir = Path(args.log_dir)

    # modal colour of the strip band (already pasted-background-safe: pure white)
    band = im.crop((80, im.height - 260, im.width - 80, im.height - 20))
    modal = collections.Counter(band.get_flattened_data()).most_common(1)[0][0]

    for name, (x, y, w, h) in SLOTS.items():
        x0, y0 = x * SCALE, y * SCALE
        x1, y1 = (x + w) * SCALE, (y + h) * SCALE
        im.paste(modal, (x0, y0, x1, y1))

        src = Image.open(log_dir / f"{name}.png").convert("RGBA")
        l, u, r, d = src.getchannel("A").getbbox()
        src = src.crop((l, u, r, d))
        sw, sh = src.size
        th = h * SCALE
        tw = round(sw * th / sh)
        src = src.resize((tw, th), Image.LANCZOS)
        cx = (x0 + x1) // 2
        im.paste(src, (cx - tw // 2, y0, cx - tw // 2 + tw, y0 + th), src)

    im.save(args.out)
    print(f"composited {len(SLOTS)} logos -> {args.out} ({im.size})")


if __name__ == "__main__":
    main()