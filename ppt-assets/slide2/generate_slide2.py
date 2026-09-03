#!/usr/bin/env python3
"""
RAKSHAK-NET — Slide 2 (IDEA) asset generator.

Winner-pattern layout: PROBLEM cards + SOLUTION cards + USP strip + flow banner
+ light transparent mesh architecture. All PNGs are TRANSPARENT (light-mode:
dark text, brand accents) so they paste onto any light Canva/Slides template.

Run:  backend/.venv/bin/python ppt-assets/slide2/generate_slide2.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = Path(__file__).parent

_DEV = "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc"
if Path(_DEV).exists():
    fm.fontManager.addfont(_DEV)
    FAMS = ["DejaVu Sans", "Devanagari Sangam MN"]
else:
    FAMS = ["DejaVu Sans"]

# ------------------------------------------------ light-mode palette --------
INK    = "#0f172a"   # near-black text
SUB    = "#475569"   # secondary text
NAVY   = "#1e293b"   # card fill (dark) for contrast chips
CYAN   = "#0891b2"
CYANL  = "#e0f2fe"   # light cyan fill
PURPLE = "#7c3aed"
PURPL  = "#f3e8ff"
EMER   = "#059669"
EMERL  = "#d1fae5"
AMBER  = "#d97706"
AMBERL = "#fef3c7"
PINK   = "#db2777"
PINKL  = "#fce7f3"
LINE   = "#cbd5e1"

plt.rcParams.update({
    "font.family": FAMS,
    "text.color": INK,
})


def canvas(w, h):
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, fc="#ffffff", ec=LINE, lw=1.4, r=1.8):
    b = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                       fc=fc, ec=ec, lw=lw)
    ax.add_patch(b)
    return b


def txt(ax, x, y, s, size=11, color=INK, weight="normal", ha="center",
        va="center", mono=False, spacing=1.35):
    fam = (["DejaVu Sans Mono"] + FAMS) if mono else FAMS
    ax.text(x, y, s, fontsize=size, color=color, fontweight=weight, ha=ha,
            va=va, family=fam, linespacing=spacing)


def arrow(ax, x1, y1, x2, y2, color=LINE, lw=2.2, ms=15):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=ms,
                        color=color, lw=lw, shrinkA=2, shrinkB=2)
    ax.add_patch(a)


def save(fig, name):
    fig.savefig(OUT / name, dpi=200, transparent=True)
    plt.close(fig)
    print(f"  done {name}")


# ======================================================= PROBLEM CARDS =======
def problem_cards():
    fig, ax = canvas(12.8, 3.6)
    txt(ax, 50, 92, "THE PROBLEM", size=15, weight="bold", color=PINK)
    ax.plot([41, 59], [80, 80], color=PINK, lw=3, solid_capstyle="round")

    cards = [
        ("FRAGMENTED DATA", "FIRs, CDRs, financial trails live in\ndistrict silos — no cross-district view", PINK, PINKL),
        ("MULTILINGUAL NAMES", "Mohd · Mohamad · मोहम्मद —\nsame person, manual matching fails", PURPLE, PURPL),
        ("DAYS OF WAITING", "one cross-district check = days of\nmanual correspondence between states", AMBER, AMBERL),
        ("LLMs HALLUCINATE", "generic AI invents links that don't exist\n— unacceptable as court evidence", CYAN, CYANL),
    ]
    w, h, gap = 22.4, 56, 2.2
    total = 4 * w + 3 * gap
    x0 = (100 - total) / 2
    y = 8
    for i, (head, body, c, fl) in enumerate(cards):
        x = x0 + i * (w + gap)
        box(ax, x, y, w, h, fc=fl, ec=c, lw=2.0)
        txt(ax, x + w/2, y + h - 12, head, size=10.5, weight="bold", color=c)
        txt(ax, x + w/2, y + h/2 - 6, body, size=8.6, color=INK)
    save(fig, "problem-cards.png")


# ====================================================== SOLUTION CARDS =======
def solution_cards():
    fig, ax = canvas(12.8, 3.6)
    txt(ax, 50, 92, "OUR SOLUTION", size=15, weight="bold", color=EMER)
    ax.plot([40, 60], [80, 80], color=EMER, lw=3, solid_capstyle="round")

    cards = [
        ("1 · CANONICAL FUSION", "one CCTNS-shaped schema unifies all\nsources — no legacy migration needed", CYAN, CYANL),
        ("2 · IDENTITY RESOLUTION", "4-feature hybrid scoring resolves names\nacross Hindi · English · Hinglish", PURPLE, PURPL),
        ("3 · DISTRICT VAULT MESH", "signed queries travel between districts\nFIR data never leaves its own vault", EMER, EMERL),
        ("4 · WARRANT GATE + LEDGERS", "victim data unmasks only behind a\ndual-signed warrant · 3 hash-chains", AMBER, AMBERL),
    ]
    w, h, gap = 22.4, 56, 2.2
    total = 4 * w + 3 * gap
    x0 = (100 - total) / 2
    y = 8
    for i, (head, body, c, fl) in enumerate(cards):
        x = x0 + i * (w + gap)
        box(ax, x, y, w, h, fc=fl, ec=c, lw=2.0)
        txt(ax, x + w/2, y + h - 12, head, size=10.5, weight="bold", color=c)
        txt(ax, x + w/2, y + h/2 - 6, body, size=8.6, color=INK)
    save(fig, "solution-cards.png")


# ========================================================== USP STRIP ========
def usp_strip():
    fig, ax = canvas(12.8, 2.5)
    txt(ax, 50, 88, "USP — WHY ONLY US", size=14, weight="bold", color=NAVY)

    items = [
        ("India's FIRST", "evidence-ledger criminal\nintelligence system"),
        ("Constitutional BY DESIGN", "Seventh Schedule — mesh,\nnever centralization"),
        ("ZERO hallucination", "no LLM in serving path —\nretrieval-only, cited"),
        ("LIVE today", "3 vaults + gateway + workbench\n119/119 tests passing"),
    ]
    w, h, gap = 22.4, 56, 2.2
    total = 4 * w + 3 * gap
    x0 = (100 - total) / 2
    y = 6
    for i, (big, small) in enumerate(items):
        x = x0 + i * (w + gap)
        box(ax, x, y, w, h, fc="#ffffff", ec=NAVY, lw=2.2)
        txt(ax, x + w/2, y + h - 13, big, size=10.5, weight="bold", color=NAVY)
        txt(ax, x + w/2, y + h/2 - 7, small, size=8.4, color=SUB)
    save(fig, "usp-strip.png")


# ======================================================== FLOW BANNER ========
def flow_banner():
    fig, ax = canvas(12.8, 1.7)
    steps = [
        ("FRAGMENTED\nDATA", PINK),
        ("ENTITY\nRESOLUTION", PURPLE),
        ("TEMPORAL\nCRIMINAL GRAPH", CYAN),
        ("EVIDENCE-GROUNDED\nINTELLIGENCE", EMER),
    ]
    w, h, gap = 20, 58, 5.2
    total = 4 * w + 3 * gap
    x0 = (100 - total) / 2
    y = 18
    for i, (name, c) in enumerate(steps):
        x = x0 + i * (w + gap)
        box(ax, x, y, w, h, fc="#ffffff", ec=c, lw=2.2)
        txt(ax, x + w/2, y + h/2, name, size=9.8, weight="bold", color=c)
        if i < 3:
            arrow(ax, x + w + 0.6, y + h/2, x + w + gap - 0.6, y + h/2,
                  color=SUB, lw=2.6, ms=17)
    save(fig, "flow-banner.png")


# ================================================ MESH (LIGHT, TRANSPARENT) ==
def mesh_light():
    fig, ax = canvas(12.8, 5.2)
    txt(ax, 50, 94, "DISTRICT VAULT MESH — like UPI for banks", size=13.5,
        weight="bold", color=CYAN)

    box(ax, 33, 52, 34, 30, fc="#ffffff", ec=CYAN, lw=2.6)
    txt(ax, 50, 73.5, "MESH GATEWAY", size=12.5, weight="bold", color=CYAN)
    txt(ax, 50, 68.5, "NPCI-style switch · :8000", size=8.8, color=SUB, mono=True)
    txt(ax, 50, 61, "routes signed queries · stores RECEIPTS only\nhash-chained exchange ledger", size=8.6, color=INK)

    vaults = [
        (6,  10, "DELHI VAULT",  ":8001", EMER),
        (38, 10, "MUMBAI VAULT", ":8002", PURPLE),
        (70, 10, "JAIPUR VAULT", ":8003", AMBER),
    ]
    for x, y, name, port, c in vaults:
        box(ax, x, y, 24, 24, fc="#ffffff", ec=c, lw=2.2)
        txt(ax, x + 12, y + 17, name, size=10.5, weight="bold", color=c)
        txt(ax, x + 12, y + 12.5, f"{port} · own FIR/CDR/FIN graph", size=7.8,
            color=SUB, mono=True)
        txt(ax, x + 12, y + 7, "HMAC-signed receipts\nanswers only — data stays", size=7.8, color=INK)
        gx = 40 if x < 33 else (50 if x < 60 else 60)
        arrow(ax, gx, 52.5, x + 12, 34.5, color=c, lw=2.0,
              )
    txt(ax, 50, 3.5, "queries travel · FIR data never leaves its district · every exchange ledgered",
        size=9.5, weight="bold", color=INK)
    save(fig, "mesh-light.png")


if __name__ == "__main__":
    print("Generating slide-2 assets (transparent, light-mode) ...")
    problem_cards()
    solution_cards()
    usp_strip()
    flow_banner()
    mesh_light()
