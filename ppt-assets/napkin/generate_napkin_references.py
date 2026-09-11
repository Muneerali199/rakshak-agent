#!/usr/bin/env python3
"""
RAKSHAK-NET — FINAL napkin-style Slide 6: Research & References.

Left  : live Report 2.0 screenshot pasted polaroid-style (washi tape + tilt)
        + hand caption + PROTOTYPE & PROOF link card.
Right : 8 citation rows, each mapped to the module it inspired.

Same hand-drawn aesthetic as slides 4/5 (wobbly ink, Bradley Hand, paper grain).

Run:  backend/.venv/bin/python ppt-assets/napkin/generate_napkin_references.py
Out:  ppt-assets/napkin/references-napkin.png
"""
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.transforms as mtransforms
from matplotlib.image import imread
from matplotlib.patches import Polygon, FancyArrowPatch

OUT = Path(__file__).parent
REPO = OUT.parents[2]                      # rakshak-agent/ (screenshots live here)
SHOT = REPO / "mesh-fir-live.png"

# ---------------------------------------------------------------- fonts -----
BRAD = "/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf"
DEV  = "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc"
for f in (BRAD, DEV):
    if Path(f).exists():
        fm.fontManager.addfont(f)
HAND = "Bradley Hand" if Path(BRAD).exists() else "DejaVu Sans"
BODY = ["DejaVu Sans"]
MONO = ["DejaVu Sans Mono"]
DEVA = ["Devanagari Sangam MN", "DejaVu Sans"]

# ---------------------------------------------------------------- palette ---
PAPER = "#ffffff"
INK   = "#3a3a3a"
SOFT  = "#6b6b6b"
FAINT = "#9a9a9a"
GREEN = "#1e7d4f"

C = {
    "blue":   ("#dbe7ff", "#5b8def"),
    "green":  ("#d9f7e9", "#33b57c"),
    "orange": ("#ffe7cc", "#f09231"),
    "yellow": ("#fff3c2", "#d9b02f"),
    "pink":   ("#fde2ef", "#e26fa4"),
}

plt.rcParams.update({
    "font.family": BODY, "text.color": INK,
    "figure.facecolor": PAPER, "savefig.facecolor": PAPER,
})


# ------------------------------------------------------------ primitives ----
def wobbly_line(ax, x1, y1, x2, y2, color=INK, lw=2.0, seed=0, wobble=0.22,
                overshoot=0.9):
    r = np.random.default_rng(seed)
    n = 24
    t = np.linspace(0, 1, n)
    dx, dy = x2 - x1, y2 - y1
    L = max(np.hypot(dx, dy), 1e-9)
    nx, ny = -dy / L, dx / L
    ox = r.uniform(0, overshoot); oy = r.uniform(0, overshoot)
    xs = x1 - nx * ox + (dx + nx * (ox + oy)) * t
    ys = y1 - ny * oy + (dy + ny * (ox + oy)) * t
    off = (np.sin(t * np.pi * 2.6 + r.uniform(0, 6)) * 0.55
           + r.normal(0, 0.35, n)) * wobble
    xs, ys = xs + nx * off, ys + ny * off
    ax.plot(xs, ys, color=color, lw=lw, solid_capstyle="round", zorder=3)


def wobbly_rect(ax, x, y, w, h, fill, seed=0, lw=2.2):
    ax.fill([x, x + w, x + w, x, x], [y, y, y + h, y + h, y],
            color=fill, zorder=1.5, alpha=0.95)
    corners = [(x, y, x + w, y), (x + w, y, x + w, y + h),
               (x + w, y + h, x, y + h), (x, y + h, x, y)]
    for i, (a, b, c, d) in enumerate(corners):
        wobbly_line(ax, a, b, c, d, color=INK, lw=lw, seed=seed * 7 + i)


def squiggle(ax, x, y, w, color, lw=2.6, seed=0):
    r = np.random.default_rng(seed)
    t = np.linspace(0, 1, 60)
    xs = x + w * t
    ys = y + 0.45 * np.sin(t * np.pi * 5 + r.uniform(0, 6)) + r.normal(0, 0.08, 60)
    ax.plot(xs, ys, color=color, lw=lw, solid_capstyle="round", zorder=4)


def doodle_circle(ax, cx, cy, r, color=INK, lw=2.0, seed=0):
    r_ = np.random.default_rng(seed)
    th = np.linspace(0, 2 * np.pi, 80)
    rad = r * (1 + 0.06 * np.sin(3 * th + r_.uniform(0, 6))
               + r_.normal(0, 0.02, 80))
    ax.plot(cx + rad * np.cos(th), cy + rad * np.sin(th),
            color=color, lw=lw, solid_capstyle="round", zorder=4)


def doodle_arrow(ax, x1, y1, x2, y2, color=INK, lw=2.0, rad=0.18):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                        mutation_scale=17, color=color, lw=lw,
                        connectionstyle=f"arc3,rad={rad}",
                        shrinkA=1, shrinkB=1, zorder=4)
    ax.add_patch(a)


def doodle_check(ax, x, y, color=GREEN, lw=2.0, s=1.0):
    ax.plot([x, x + 0.9 * s, x + 2.6 * s],
            [y + 0.5 * s, y - 0.5 * s, y + 1.1 * s],
            color=color, lw=lw, solid_capstyle="round", zorder=5)


def grain(ax, n=260, seed=7):
    r = np.random.default_rng(seed)
    xs, ys = r.uniform(0, 100, n), r.uniform(0, 100, n)
    ax.scatter(xs, ys, s=r.uniform(0.4, 1.4, n), color="#a8a8a8",
               alpha=0.08, lw=0, zorder=0.5)


def txt(ax, x, y, s, size=10, color=INK, weight="normal", ha="center",
        va="center", hand=False, mono=False, dev=False, spacing=1.35,
        style="normal", zorder=5):
    fam = HAND if hand else (MONO if mono else (DEVA if dev else BODY))
    ax.text(x, y, s, fontsize=size, color=color, ha=ha, va=va,
            family=fam, linespacing=spacing, style=style,
            fontweight="bold" if (hand and weight == "bold") else weight,
            zorder=zorder)


def footer(ax):
    txt(ax, 50, 2.0, "RAKSHAK-NET  ·  Team Venom  ·  SIH 2026  ·  PS SIH26189",
        size=8.5, color=FAINT, hand=True)


def check_overflow(fig, ax, label):
    fig.canvas.draw()
    ren = fig.canvas.get_renderer()
    inv = ax.transData.inverted()
    boxes = []
    bad = []
    for t in ax.texts:
        bb = t.get_window_extent(renderer=ren)
        (x0, y0), (x1, y1) = inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])
        boxes.append((t.get_text()[:26], x0, y0, x1, y1))
        if x0 < -0.5 or x1 > 100.5 or y0 < -0.5 or y1 > 100.5:
            bad.append((t.get_text()[:38], round(x0, 1), round(x1, 1)))
    # pairwise same-area collisions (catches tag-vs-title overlaps)
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            ox = min(a[3], b[3]) - max(a[1], b[1])
            oy = min(a[4], b[4]) - max(a[2], b[2])
            if ox > 0.3 and oy > 0.25:
                bad.append((f"OVERLAP '{a[0]}' x '{b[0]}'", round(ox, 1)))
    print(f"  [{label}] overflow check: "
          + ("CLEAN" if not bad else f"ISSUES {bad}"))
    return bad


# ---------------------------------------------------- polaroid paste --------
def rot(xs, ys, cx, cy, deg):
    a = np.deg2rad(deg)
    xr = (np.asarray(xs) - cx) * np.cos(a) - (np.asarray(ys) - cy) * np.sin(a) + cx
    yr = (np.asarray(xs) - cx) * np.sin(a) + (np.asarray(ys) - cy) * np.cos(a) + cy
    return xr, yr


def paste_polaroid(ax, img_path, cx, cy, w, h, angle=-1.6, seed=5,
                   caption=None, cap_size=10.5):
    """Screenshot as a hand-pasted polaroid: white backing, ink border,
    two washi-tape strips, slight tilt, optional caption in the bottom strip."""
    img = imread(str(img_path))
    # data-aspect fix: x-unit=0.1333in, y-unit=0.075in → keep pixel aspect
    w_data = w
    h_data = w * (0.1333 / 0.075) * (img.shape[0] / img.shape[1])
    x0, x1 = cx - w_data / 2, cx + w_data / 2
    y0, y1 = cy - h_data / 2, cy + h_data / 2

    # white backing (extra-deep bottom strip for the polaroid caption)
    bw, bh = w_data + 2.6, h_data + 2.2
    bx = [cx - bw / 2, cx + bw / 2, cx + bw / 2, cx - bw / 2, cx - bw / 2]
    by = [cy - bh / 2 - 3.4, cy - bh / 2 - 3.4, cy + bh / 2, cy + bh / 2,
          cy - bh / 2 - 3.4]
    bxr, byr = rot(bx, by, cx, cy, angle)
    ax.fill(bxr, byr, color="#fdfdfd", zorder=4.5)

    # screenshot with rotation
    im = ax.imshow(img, extent=[x0, x1, y0, y1], zorder=5,
                   interpolation="bilinear")
    tr = (mtransforms.Affine2D().rotate_deg_around(cx, cy, angle)
          + ax.transData)
    im.set_transform(tr)
    ax.set_aspect("auto")   # imshow forces 'equal' → undoes it (full-width 16:9)

    # ink border around the photo (wobbly, in rotated frame)
    for i, (a, b, c, d) in enumerate([(x0, y0, x1, y0), (x1, y0, x1, y1),
                                      (x1, y1, x0, y1), (x0, y1, x0, y0)]):
        ar, br = rot([a, c], [b, d], cx, cy, angle)
        wobbly_line(ax, ar[0], br[0], ar[1], br[1], color=INK, lw=1.7,
                    seed=seed * 9 + i, wobble=0.14, overshoot=0.4)

    # washi tape strips (top-left & top-right, pastel, semi-opaque)
    for (tx, ty, tang, col) in [(x0 + 3.2, y1, -7, "#e26fa4"),
                                (x1 - 3.2, y1, 6, "#5b8def")]:
        tw, th = 6.4, 2.0
        px = [tx - tw / 2, tx + tw / 2, tx + tw / 2, tx - tw / 2, tx - tw / 2]
        py = [ty - th / 2, ty - th / 2, ty + th / 2, ty + th / 2, ty - th / 2]
        pxr, pyr = rot(px, py, tx, ty, tang)
        tape = Polygon(np.column_stack([pxr, pyr]), closed=True,
                       facecolor=col, edgecolor="none", alpha=0.45, zorder=6)
        ax.add_patch(tape)

    # hand-written caption in the polaroid bottom strip (below the photo)
    if caption:
        txt(ax, cx, y0 - 2.0, caption, size=cap_size, hand=True,
            weight="bold", color=INK, zorder=7)


# ===================================================== SLIDE 6 · REFERENCE ==
def references():
    fig = plt.figure(figsize=(13.33, 7.5))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.axis("off"); grain(ax, seed=23)

    # ---- header
    txt(ax, 50, 94.5, "Research & References", size=27, hand=True, weight="bold")
    squiggle(ax, 31.5, 90.8, 37, C["blue"][1], lw=3.2, seed=31)
    txt(ax, 50, 87.2, "Every citation maps to a module we actually built",
        size=11.5, color=SOFT)

    # ================= LEFT: screenshot at max size =================
    # photo spans x 1.5..46.8; image 1.84:1 → data h = 45.3*0.7299 ≈ 33.1
    paste_polaroid(ax, SHOT, cx=24.15, cy=67.8, w=45.3, h=0, angle=-1.2,
                   caption="one Hindi FIR — entities · links · mesh · shield",
                   cap_size=10.5)

    doodle_check(ax, 2.6, 40.2, color=GREEN, lw=2.2, s=0.9)
    txt(ax, 25.8, 38.7,
        "live cross-district linkage — FIR data never left its district\n119/119 tests  ·  3/3 ledgers verify ok:true",
        size=7.7, color=GREEN, ha="center")

    # ---- compact link block (prototype proof)
    wobbly_rect(ax, 3.5, 11.8, 42.8, 24.2, "#f7f7f7", seed=64, lw=2.0)
    txt(ax, 6.2, 32.6, "PROTOTYPE & PROOF", size=9.5, hand=True,
        weight="bold", ha="left", color=INK)
    links = [
        (28.8, "repo",  "github.com/Muneerali199/rakshak-agent"),
        (25.4, "model", "huggingface.co/Muneerali199/rakshak-cwe-14b-sft-final"),
        (22.0, "demo",  "scripts/run_mesh.sh — 3 vaults, offline"),
    ]
    for y, label, url in links:
        txt(ax, 6.2, y, label, size=7.6, weight="bold", ha="left", color=SOFT)
        txt(ax, 12.8, y, url, size=6.8, mono=True, ha="left", color=INK)
    txt(ax, 25, 15.8, "interactive citations → references.html (same folder)",
        size=7.0, color=FAINT, style="italic")
    txt(ax, 25, 13.4, "live screenshots in repo: mesh-fir · warrant-gate · report-2",
        size=7.0, color=FAINT, style="italic")

    # ================= RIGHT: citations with real URLs =================
    txt(ax, 50.5, 83.8, "CITED WORKS  →  MODULES THEY INSPIRED", size=8.2,
        color=FAINT, ha="left", weight="bold")

    rows = [
        ("Rossi et al. — Temporal Graph Networks",
         "Machine Learning journal, 2020",
         "arxiv.org/abs/2006.10637",
         "→ timestamped edges", "blue"),
        ("Boccaletti et al. — Multilayer Networks",
         "Physics Reports, 2014",
         "arxiv.org/abs/1407.0742",
         "→ graph layers", "green"),
        ("Christen — Data Matching",
         "Springer, 2012",
         "doi.org/10.1007/978-3-642-31164-2",
         "→ identity resolution", "orange"),
        ("COMI-LINGUA — Hinglish Dataset",
         "EMNLP 2025 Findings",
         "arxiv.org/abs/2503.21670",
         "→ Hinglish NER", "pink"),
        ("AI4Bharat IndicXlit · Bhashini",
         "IIT Madras · MeitY mission",
         "github.com/AI4Bharat/IndicXlit",
         "→ मोहम्मद ↔ Mohd", "yellow", True),
        ("Ying et al. — GNNExplainer",
         "NeurIPS, 2019",
         "arxiv.org/abs/1903.03894",
         "→ evidence trace", "blue"),
        ("Qwen2.5-Coder + LoRA",
         "Alibaba Cloud, 2024",
         "arxiv.org/abs/2409.12186",
         "→ RakshakAI 14B", "green"),
        ("NCRB — Crime in India 2024",
         "Ministry of Home Affairs",
         "ncrb.gov.in",
         "→ crime-data grounding", "orange"),
    ]
    y = 79.5
    step = 9.35
    hotspots = []
    for i, row in enumerate(rows):
        title, venue, url, tag = row[0], row[1], row[2], row[3]
        key = row[4]
        is_dev = row[5] if len(row) > 5 else False
        accent = C[key][1]
        # number badge
        doodle_circle(ax, 53.3, y + 1.9, 1.85, color=accent, lw=1.8, seed=i + 51)
        txt(ax, 53.3, y + 1.85, str(i + 1), size=8.5, hand=True,
            weight="bold", color=accent)
        # citation title + module tag on same line
        txt(ax, 57.2, y + 1.9, title, size=8.3, ha="left", weight="bold")
        txt(ax, 96.5, y + 1.9, tag, size=7.0, ha="right", color=accent,
            weight="bold", dev=is_dev)
        # venue (italic) + real URL (mono, link-blue)
        txt(ax, 57.2, y - 0.8, venue, size=6.9, ha="left", color=SOFT,
            style="italic")
        txt(ax, 57.2, y - 3.0, url, size=6.9, mono=True, ha="left",
            color="#2563eb")
        # hand-ruled separator
        if i < len(rows) - 1:
            wobbly_line(ax, 50.5, y - 4.5, 96.5, y - 4.5, color="#dedede",
                        lw=1.1, seed=i + 71, wobble=0.16, overshoot=0.4)
        # hotspot rect for Google Slides overlay (slide-percent coords)
        hotspots.append((title, url,
                         50.5 / 100, (100 - (y + 3.6)) / 100,      # left, top
                         96.5 / 100, (100 - (y - 4.2)) / 100))     # right, bottom
        y -= step

    txt(ax, 73.5, 7.6,
        "clickable bibliography → references.html (in repo)",
        size=7.4, color=FAINT, style="italic")
    footer(ax)
    check_overflow(fig, ax, "references")
    fig.savefig(OUT / "references-napkin.png", dpi=200)
    plt.close(fig)

    print("  done references-napkin.png")
    print("  --- Google Slides link-hotspot rectangles (L,T,R,B in % of slide) ---")
    for title, url, l, t, r, b in hotspots:
        print(f"    {title[:34]:36s} {url:34s} "
              f"L{l*100:.0f}% T{t*100:.0f}% R{r*100:.0f}% B{b*100:.0f}%")


if __name__ == "__main__":
    print("Generating final napkin-style Slide 6 ...")
    references()
