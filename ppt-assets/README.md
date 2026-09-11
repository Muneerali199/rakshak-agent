# SIH 2026 deck visuals · asset index & production recipes

All slide graphics for the RAKSHAK-NET submission deck. Naming is deck-wide:
**RAKSHAK‑NET** (platform) · **RakshakAI** (the 14B security model).

---

## Layout

```
ppt-assets/
├─ 01-mesh-architecture.png … 08-three-guarantees.png   final slide images (generate_diagrams.py)
├─ generate_diagrams.py        slide-image generator (PIL, logo compositing)
├─ drawio/                     napkin-style source of truth (sketch=1;jiggle=2)
│  ├─ architecture.drawio        system napkin
│  ├─ methodology.drawio/.png    10-step METHODOLOGY panel (2×5 grid, serpentine arrows)
│  ├─ flowchart.drawio/.png      ONE CROSS-DISTRICT QUERY icon flowchart
│  ├─ technical-approach.drawio  full slide 3: title · methodology · flowchart · TECH STACK strip
│  └─ *.png                      exports @ 2× (transparent: px = drawio coord × 2)
├─ technical/                  icons + logos composited onto the drawio exports
│  ├─ icons/                     15 napkin icons (ingest, identity, graph, anomaly,
│  │                             verdict, ask, shield, warrant, gateway, vault,
│  │                             receipt, chain, report, study, mesh) — 400×400 RGBA
│  └─ logos/                     8 tech logos (python, fastapi, sqlite, react,
│                                typescript, tailwindcss, vite, huggingface) — tight-cropped
├─ napkin/                     feasibility / impact / references napkins + generators
├─ mermaid/                    mermaid sources (decision-tree etc.)
├─ slide2/                     slide-2 variants
└─ scripts/
   ├─ composite_logos.py        erase broken placeholders → paste logos onto a 2× export
   └─ (drawio export driver)    headless-Chrome capture of a drawio file → PNG @ scale 2
```

## Why compositing (never base64 embedding)

Draw.io's style parser splits style values on `;`, so `image=data:image/png;base64,…`
**always truncates** to `data:image/png` — every embedded bitmap silently renders as a
broken-image glyph. The working recipe:

1. Lay out the diagram in draw.io **text + shapes only** (napkin style).
2. Export @ **scale 2, border 0** (headless Chrome) → pixel map `px = coord × 2`.
3. Composite the PNGs (icons / logos) **on top** with PIL at the exact slots
   (see `scripts/composite_logos.py`) — opaque, full-height, centered.

Repeat for any image-bearing slide. Base64 in draw.io styles: never.

## Rebuild the TECH STACK strip (slide 3)

```bash
python3 ppt-assets/scripts/composite_logos.py \
  --base ppt-assets/drawio/technical-approach.png \
  --log-dir ppt-assets/technical/logos \
  --out  ppt-assets/drawio/technical-approach.png
```

`technical-approach.drawio` stores the strip geometry (8 slots at `y=784`,`h=38`); the
slots are intentionally left **image-free** in the source — the script owns them.

## Icon style

Hand-drawn wobbly-stroke SVGs (double-pass pencil texture, main stroke 4.4, ghost 3.2 @ 18%),
rendered transparent via headless Chrome, exported 400×400. Colors follow each card's accent
in the panels (blue / purple / green / yellow / red).