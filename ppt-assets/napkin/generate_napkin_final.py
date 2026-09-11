#!/usr/bin/env python3
"""
RAKSHAK-NET — FINAL napkin-style deck images (Slides 4 & 5).

Replicates the napkin.ai aesthetic by hand:
  - wobbly hand-drawn box borders with corner overshoot
  - Bradley Hand (marker) headings, clean sans body
  - doodle circles, squiggle underlines, curvy arrows
  - highlighter swipes behind key numbers
  - cream paper + subtle grain (no flat "AI gradient" look)

All statistics verified (NCRB CII 2024 / PIB Feb-2026 / BNS 2023).

Run:  backend/.venv/bin/python ppt-assets/napkin/generate_napkin_final.py
Out:  ppt-assets/napkin/feasibility-napkin.png   (Slide 4)
      ppt-assets/napkin/impact-napkin.png        (Slide 5)
"""
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import FancyArrowPatch

OUT = Path(__file__).parent

# ---------------------------------------------------------------- fonts -----
BRAD = "/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf"
for f in (BRAD,):
    if Path(f).exists():
        fm.fontManager.addfont(f)
HAND = "Bradley Hand" if Path(BRAD).exists() else "DejaVu Sans"
BODY = ["DejaVu Sans"]

# ---------------------------------------------------------------- palette ---
PAPER = "#fbfaf5"          # warm cream paper
INK   = "#3a3a3a"          # napkin ink stroke
SOFT  = "#6b6b6b"          # secondary text
FAINT = "#9a9a9a"

C = {
    "blue":   ("#dbe7ff", "#5b8def"),
    "green":  ("#d9f7e9", "#33b57c"),
    "orange": ("#ffe7cc", "#f09231"),
    "yellow": ("#fff3c2", "#d9b02f"),
    "pink":   ("#fde2ef", "#e26fa4"),
}
HIGHLIGHT = "#ffe482"      # marker-yellow swipe

rng = np.random.default_rng(42)

plt.rcParams.update({
    "font.family": BODY, "text.color": INK,
    "figure.facecolor": PAPER, "savefig.facecolor": PAPER,
})


# ------------------------------------------------------------ primitives ----
def wobbly_line(ax, x1, y1, x2, y2, color=INK, lw=2.0, seed=0, wobble=0.22,
                overshoot=0.9):
    """Hand-drawn straight-ish line: gentle waviness + tiny corner overshoot."""
    r = np.random.default_rng(seed)
    n = 24
    t = np.linspace(0, 1, n)
    dx, dy = x2 - x1, y2 - y1
    L = max(np.hypot(dx, dy), 1e-9)
    nx, ny = -dy / L, dx / L                      # unit normal
    ox = r.uniform(0, overshoot); oy = r.uniform(0, overshoot)
    xs = x1 - nx * ox + (dx + nx * (ox + oy)) * t
    ys = y1 - ny * oy + (dy + ny * (ox + oy)) * t
    off = (np.sin(t * np.pi * 2.6 + r.uniform(0, 6)) * 0.55
           + r.normal(0, 0.35, n)) * wobble
    xs, ys = xs + nx * off, ys + ny * off
    ax.plot(xs, ys, color=color, lw=lw, solid_capstyle="round", zorder=3)


def wobbly_rect(ax, x, y, w, h, fill, seed=0, lw=2.2):
    """Napkin-style card: pastel fill + 4 wobbly strokes that overshoot corners."""
    ax.fill([x, x + w, x + w, x, x], [y, y, y + h, y + h, y],
            color=fill, zorder=1.5, alpha=0.95)
    corners = [(x, y, x + w, y), (x + w, y, x + w, y + h),
               (x + w, y + h, x, y + h), (x, y + h, x, y)]
    for i, (a, b, c, d) in enumerate(corners):
        wobbly_line(ax, a, b, c, d, color=INK, lw=lw, seed=seed * 7 + i)


def squiggle(ax, x, y, w, color, lw=2.6, seed=0):
    """Hand underline squiggle."""
    r = np.random.default_rng(seed)
    t = np.linspace(0, 1, 60)
    xs = x + w * t
    ys = y + 0.45 * np.sin(t * np.pi * 5 + r.uniform(0, 6)) + r.normal(0, 0.08, 60)
    ax.plot(xs, ys, color=color, lw=lw, solid_capstyle="round", zorder=4)


def doodle_circle(ax, cx, cy, r, color=INK, lw=2.0, seed=0):
    """Imperfect hand-drawn circle (for numbered badges)."""
    r_ = np.random.default_rng(seed)
    th = np.linspace(0, 2 * np.pi, 80)
    rad = r * (1 + 0.06 * np.sin(3 * th + r_.uniform(0, 6))
               + r_.normal(0, 0.02, 80))
    ax.plot(cx + rad * np.cos(th), cy + rad * np.sin(th),
            color=color, lw=lw, solid_capstyle="round", zorder=4)


def doodle_arrow(ax, x1, y1, x2, y2, color=INK, lw=2.0, rad=0.18):
    """Curvy hand arrow."""
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                        mutation_scale=17, color=color, lw=lw,
                        connectionstyle=f"arc3,rad={rad}",
                        shrinkA=1, shrinkB=1, zorder=4)
    ax.add_patch(a)


def highlight(ax, x, y, w, h, color=HIGHLIGHT, alpha=0.45, seed=0):
    """Marker swipe behind a key number."""
    r = np.random.default_rng(seed)
    t = np.linspace(0, 1, 40)
    top = y + h + 0.25 * np.sin(t * 7 + r.uniform(0, 6))
    bot = y - 0.25 * np.sin(t * 6 + r.uniform(0, 6))
    xs = np.concatenate([x + w * t, (x + w * t)[::-1]])
    ys = np.concatenate([top, bot[::-1]])
    ax.fill(xs, ys, color=color, alpha=alpha, lw=0, zorder=2)


def grain(ax, n=260, seed=7):
    """Faint paper speckle so it never looks flat/AI-generated."""
    r = np.random.default_rng(seed)
    xs, ys = r.uniform(0, 100, n), r.uniform(0, 100, n)
    ax.scatter(xs, ys, s=r.uniform(0.4, 1.4, n), color="#8a8378",
               alpha=0.10, lw=0, zorder=0.5)


def txt(ax, x, y, s, size=10, color=INK, weight="normal", ha="center",
        va="center", hand=False, spacing=1.35, style="normal", zorder=5):
    ax.text(x, y, s, fontsize=size, color=color, fontweight=weight, ha=ha,
            va=va, family=HAND if hand else BODY, linespacing=spacing,
            style=style, zorder=zorder)


def footer(ax):
    txt(ax, 50, 2.0, "RAKSHAK-NET  ·  Team Venom  ·  SIH 2026  ·  PS SIH26189",
        size=8.5, color=FAINT, hand=True)


# ------------------------------------------------- overflow self-check ------
def check_overflow(fig, ax, label):
    """Warn if any text runs off the 0-100 canvas."""
    fig.canvas.draw()
    bad = []
    inv = ax.transData.inverted()
    for t in ax.texts:
        bb = t.get_window_extent(renderer=fig.canvas.get_renderer())
        (x0, y0), (x1, y1) = inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])
        if x0 < -0.5 or x1 > 100.5 or y0 < -0.5 or y1 > 100.5:
            bad.append((t.get_text()[:38], round(x0, 1), round(x1, 1)))
    print(f"  [{label}] overflow check: "
          + ("CLEAN" if not bad else f"ISSUES {bad}"))
    return bad


# ================================================= SLIDE 4 · FEASIBILITY ====
def feasibility():
    fig = plt.figure(figsize=(13.33, 7.5))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.axis("off"); grain(ax)

    txt(ax, 50, 94.5, "Feasibility & Viability", size=27, hand=True, weight="bold")
    squiggle(ax, 30.5, 90.8, 39, C["blue"][1], lw=3.2, seed=11)
    txt(ax, 50, 87.0,
        "Constitutional by design — a mesh, never a central database",
        size=11.5, color=SOFT)

    cards = [
        ("TECHNICAL", "blue",
         "119/119 tests passing\nlive 3-vault mesh demo\nstdlib core · air-gapped"),
        ("LEGAL", "green",
         "Police = State subject\nSeventh Sch. II · Entry 2\nDPDP Act 2023 · Puttaswamy"),
        ("OPERATIONAL", "orange",
         "17,798 police stations\n100% on CCTNS (PIB 2026)\nNIC MeghRaj · runs offline"),
        ("ECONOMIC", "yellow",
         "zero cloud / API cost\nrides ₹2,000-cr CCTNS net\ncommodity hardware"),
        ("SOCIAL", "pink",
         "women-safety first\nvictim-shield in code\nno victim profiling"),
    ]
    n = len(cards); w, h, gap = 17.6, 26, 1.8
    x0 = (100 - (n * w + (n - 1) * gap)) / 2; y = 53
    for i, (name, key, body) in enumerate(cards):
        x = x0 + i * (w + gap)
        fill, accent = C[key]
        wobbly_rect(ax, x, y, w, h, fill, seed=i + 3)
        doodle_circle(ax, x + w / 2, y + h - 4.2, 2.6, color=accent, lw=2.2,
                      seed=i + 20)
        txt(ax, x + w / 2, y + h - 4.3, str(i + 1), size=12.5, hand=True,
            color=accent, weight="bold")
        txt(ax, x + w / 2, y + h - 10.6, name, size=13.5, hand=True,
            weight="bold", color=accent)
        squiggle(ax, x + w / 2 - 4.2, y + h - 12.6, 8.4, accent, lw=1.8,
                 seed=i + 40)
        txt(ax, x + w / 2, y + h / 2 - 5.2, body, size=8.4, color=INK)

    # risks -> mitigations
    txt(ax, 50, 44.5, "RISKS  to  MITIGATIONS", size=14.5, hand=True,
        weight="bold")
    doodle_arrow(ax, 30.5, 43.6, 45.5, 43.6, color=INK, lw=2.0, rad=0.10)

    pairs = [
        ("demo HMAC keys", "NIC-issued PKI certs in production"),
        ("synthetic demo data", "CCTNS schema mapping = drop-in"),
        ("adoption resistance", "human-in-the-loop on every output"),
    ]
    w2, h2, gap2 = 29.5, 14.5, 2.2
    x1 = (100 - (3 * w2 + 2 * gap2)) / 2; y2 = 16.5
    for i, (risk, mit) in enumerate(pairs):
        x = x1 + i * (w2 + gap2)
        wobbly_rect(ax, x, y2, w2, h2, "#f4f2ec", seed=i + 60, lw=1.9)
        txt(ax, x + w2 / 2, y2 + h2 - 3.4, risk, size=9.8, color="#c0392b",
            weight="bold")
        doodle_arrow(ax, x + w2 / 2, y2 + h2 - 5.4, x + w2 / 2, y2 + 5.6,
                     color=FAINT, lw=1.8, rad=0.0)
        txt(ax, x + w2 / 2, y2 + 3.6, mit, size=8.8, color="#1e7d4f")

    txt(ax, 50, 9.5,
        "Verified: Seventh Schedule (Const. of India) · DPDP Act No. 22 of 2023 · "
        "Puttaswamy v. UoI (2017) · PIB/MHA, Feb 2026",
        size=7.6, color=FAINT, style="italic")
    footer(ax)
    check_overflow(fig, ax, "feasibility")
    fig.savefig(OUT / "feasibility-napkin.png", dpi=200)
    plt.close(fig); print("  done feasibility-napkin.png")


# ==================================================== SLIDE 5 · IMPACT ======
def impact():
    fig = plt.figure(figsize=(13.33, 7.5))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.axis("off"); grain(ax, seed=13)

    txt(ax, 50, 94.5, "Impact & Benefits", size=27, hand=True, weight="bold")
    squiggle(ax, 34, 90.8, 32, C["green"][1], lw=3.2, seed=21)
    txt(ax, 50, 87.0,
        "Built for the NCRB Women Safety Division — intervention before the next FIR",
        size=11.5, color=SOFT)

    stats = [
        ("58.8L", "FIRs registered in 2024", "NCRB · Crime in India 2024", "blue"),
        ("17,798", "police stations on CCTNS", "100% coverage · PIB, Feb 2026", "orange"),
        ("1,210", "crimes vs women per day", "4.48 lakh in 2023 · NCRB", "pink"),
        ("55 min", "one stalking FIR every…", "BNS §78 (was IPC 354D)", "yellow"),
        ("29.2%", "IPC cases pending probe", "the backlog we collapse", "green"),
    ]
    n = len(stats); w, h, gap = 17.6, 25, 1.8
    x0 = (100 - (n * w + (n - 1) * gap)) / 2; y = 57.5
    for i, (big, label, src, key) in enumerate(stats):
        x = x0 + i * (w + gap)
        fill, accent = C[key]
        wobbly_rect(ax, x, y, w, h, fill, seed=i + 80)
        highlight(ax, x + 2.1, y + h - 8.6, w - 4.2, 5.6, seed=i + 90)
        txt(ax, x + w / 2, y + h - 5.8, big, size=19.5, hand=True,
            weight="bold", color=INK)
        txt(ax, x + w / 2, y + h - 12.6, label, size=8.7, color=INK,
            weight="bold")
        txt(ax, x + w / 2, y + 4.6, src, size=7.3, color=SOFT, style="italic")
        squiggle(ax, x + w / 2 - 4.0, y + h - 14.6, 8.0, accent, lw=1.8,
                 seed=i + 110)

    bands = [
        ("SOCIAL", "pink",
         "stalking-escalation flagged BEFORE the next FIR  ·  victims shielded, never profiled  ·  93.9% of rapes: culprit known to victim — repeat-offender networks are the real case"),
        ("ECONOMIC", "orange",
         "days of cross-district file correspondence collapse to one signed mesh query  ·  zero new national infrastructure — rides the CCTNS network"),
        ("GOVERNANCE", "blue",
         "every claim hash-traceable to its source row  ·  every unmask warrant-backed  ·  3 tamper-evident ledgers  ·  0 LLM in the serving path"),
    ]
    y2 = 41.5
    for i, (tag, key, body) in enumerate(bands):
        yy = y2 - i * 9.6
        fill, accent = C[key]
        wobbly_rect(ax, 6, yy - 3.4, 88, 7.6, fill, seed=i + 130, lw=1.9)
        txt(ax, 13.5, yy + 0.4, tag, size=11, hand=True, weight="bold",
            color=accent)
        txt(ax, 52, yy + 0.4, body, size=8.2, color=INK)

    txt(ax, 50, 8.6,
        "Verified: NCRB Crime in India 2024 & 2023 · PIB/MHA (CCTNS), Feb 2026 · "
        "Bharatiya Nyaya Sanhita §78",
        size=7.6, color=FAINT, style="italic")
    footer(ax)
    check_overflow(fig, ax, "impact")
    fig.savefig(OUT / "impact-napkin.png", dpi=200)
    plt.close(fig); print("  done impact-napkin.png")


if __name__ == "__main__":
    print("Generating final napkin-style deck images ...")
    feasibility()
    impact()
