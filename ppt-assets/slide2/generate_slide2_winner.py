#!/usr/bin/env python3
"""
RAKSHAK-NET — Slide 2 in EXACT winner format (Raksha-Setu/INNOVISION layout).

Structure copied from the winning deck:
  tagline (one line, caps)
  + PROBLEM OVERVIEW  (5 short pain bullets)
  + PROBLEM SOLUTION  (6 bullets, "Bold Name - explanation")
  + HIERARCHICAL DIAGRAM (3 tier-labelled boxes: switch / vaults / end users)

All PNGs TRANSPARENT, light-mode. Run:
  backend/.venv/bin/python ppt-assets/slide2/generate_slide2_winner.py
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

INK   = "#0f172a"
SUB   = "#475569"
NAVY  = "#1e293b"
CYAN  = "#0891b2"
PURPLE = "#7c3aed"
EMER  = "#059669"
AMBER = "#d97706"
PINK  = "#db2777"
RED   = "#dc2626"
LINE  = "#94a3b8"

plt.rcParams.update({"font.family": FAMS, "text.color": INK})


def canvas(w, h):
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, fc="#ffffff", ec=LINE, lw=1.5, r=1.5):
    b = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                       fc=fc, ec=ec, lw=lw)
    ax.add_patch(b)


def txt(ax, x, y, s, size=11, color=INK, weight="normal", ha="left",
        va="center", mono=False, spacing=1.45):
    fam = (["DejaVu Sans Mono"] + FAMS) if mono else FAMS
    ax.text(x, y, s, fontsize=size, color=color, fontweight=weight, ha=ha,
            va=va, family=fam, linespacing=spacing)


def bullet_list(ax, x, y_top, items, size=9.6, gap=None, dot_color=None,
                color=INK, weight="normal"):
    n = len(items)
    lines = [it.count("\n") + 1 for it in items]
    total_lines = sum(lines)
    if gap is None:
        gap = 78 / (total_lines + n * 0.55)
    y = y_top
    for it, ln in zip(items, lines):
        c = dot_color or RED
        txt(ax, x, y, "•", size=size + 2, color=c, weight="bold")
        txt(ax, x + 2.6, y, it, size=size, color=color, weight=weight,
            spacing=1.32)
        y -= gap * (ln + 0.62)
    return y


def save(fig, name):
    fig.savefig(OUT / name, dpi=200, transparent=True)
    plt.close(fig)
    print(f"  done {name}")


# ================================================ PROBLEM OVERVIEW PANEL =====
def problem_panel():
    fig, ax = canvas(6.2, 6.4)
    txt(ax, 4, 95, "PROBLEM OVERVIEW", size=15, weight="bold", color=RED)
    ax.plot([4, 44], [89.5, 89.5], color=RED, lw=3, solid_capstyle="round")

    items = [
        "FIRs, CDRs and financial trails sit in separate\ndistrict silos — no cross-district view of a case.",
        "Policing is a State subject (Seventh Schedule) —\na central national crime database is legally impossible.",
        "Identity matching across Hindi, English and\nHinglish is manual — Mohd / Mohamad / मोहम्मद.",
        "One cross-district check takes days of manual\nfile correspondence between states.",
        "Generic LLM tools hallucinate links that don't\nexist — unacceptable as court evidence.",
    ]
    bullet_list(ax, 4, 80, items, size=9.4)
    save(fig, "w-problem-panel.png")


# ================================================ PROBLEM SOLUTION PANEL ====
def solution_panel():
    fig, ax = canvas(6.6, 6.4)
    txt(ax, 3, 95, "PROBLEM SOLUTION", size=15, weight="bold", color=EMER)
    ax.plot([3, 46], [89.5, 89.5], color=EMER, lw=3, solid_capstyle="round")

    items = [
        ("Canonical Fusion",
         "one CCTNS-shaped schema unifies",
         "FIRs, CDRs, financial trails; no legacy migration."),
        ("Identity Resolution",
         "4-feature hybrid scoring resolves names",
         "across Hindi, English and Hinglish."),
        ("District Vault Mesh",
         "signed queries travel between vaults;",
         "FIR data never leaves its district."),
        ("Warrant Gate",
         "protected victim data unmasks only behind",
         "a dual-signed, scoped, expiring warrant."),
        ("Tamper-Evident Ledgers",
         "reviews, warrants and mesh exchanges",
         "are SHA-256 hash-chained."),
        ("RakshakAI Self-Security",
         "a 14B fine-tuned model scans the",
         "platform's own code for vulnerabilities."),
    ]

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    inv = ax.transData.inverted()

    y = 81
    for head, l1, l2 in items:
        # bullet + bold head
        txt(ax, 3, y, "•", size=11.5, color=EMER, weight="bold")
        t1 = ax.text(5.2, y, head, fontsize=9.8, fontweight="bold",
                     color=INK, va="center", ha="left")
        bb = t1.get_window_extent(renderer=renderer)
        (bx0, _), (bx1, _) = inv.transform((bb.x0, bb.y0)), inv.transform((bb.x1, bb.y1))
        head_w = bx1 - bx0
        # dash + first line after bold head
        ax.text(5.2 + head_w + 0.7, y, "— " + l1, fontsize=9.4,
                color=INK, va="center", ha="left")
        # second line aligned under the head
        ax.text(5.2, y - 4.9, l2, fontsize=9.4, color=INK, va="center", ha="left")
        y -= 14.4
    save(fig, "w-solution-panel.png")


# ================================================= HIERARCHY (3 TIER) ========
def hierarchy_3tier():
    fig, ax = canvas(5.4, 6.8)
    txt(ax, 50, 96, "HIERARCHICAL", size=14, weight="bold", ha="center", color=CYAN)
    txt(ax, 50, 91.5, "DIAGRAM", size=14, weight="bold", ha="center", color=CYAN)

    # tier labels (left, rotated style -> plain small caps)
    tiers = [("MESH GATEWAY", 76), ("DISTRICT VAULTS", 50), ("END USERS", 24)]

    # Tier 1: gateway
    box(ax, 8, 74, 84, 14, fc="#ffffff", ec=CYAN, lw=2.2)
    txt(ax, 50, 84.5, "MESH GATEWAY", size=11, weight="bold", ha="center", color=CYAN)
    txt(ax, 50, 78.5, "query routing · receipt verification\nhash-chained exchange ledger",
        size=8.2, ha="center", color=SUB, spacing=1.3)

    # Tier 2: vaults
    vb = [
        (8,  "DELHI VAULT",  ":8001", EMER),
        (36, "MUMBAI VAULT", ":8002", PURPLE),
        (64, "JAIPUR VAULT", ":8003", AMBER),
    ]
    for x, name, port, c in vb:
        box(ax, x, 46, 28, 16, fc="#ffffff", ec=c, lw=2.0)
        txt(ax, x + 14, 58.5, name, size=9.3, weight="bold", ha="center", color=c)
        txt(ax, x + 14, 53.5, port, size=7.8, ha="center", color=SUB, mono=True)
        txt(ax, x + 14, 49, "own FIR/CDR/FIN\ngraph", size=7.4, ha="center", color=SUB, spacing=1.25)

    # Tier 3: end users
    ub = [
        (8,  "INVESTIGATING\nOFFICERS", CYAN),
        (36, "SENIOR OFFICERS\n(SP+ countersign)", PURPLE),
        (64, "NCRB / COURT\nAUDITORS", EMER),
    ]
    for x, name, c in ub:
        box(ax, x, 18, 28, 15, fc="#ffffff", ec=c, lw=1.8)
        txt(ax, x + 14, 25.5, name, size=8.2, weight="bold", ha="center", color=c, spacing=1.3)

    # connecting arrows (user -> vault -> gateway)
    for x in (22, 50, 78):
        arrow = FancyArrowPatch((x, 33.2), (x, 45.5), arrowstyle="-|>",
                                mutation_scale=14, color=SUB, lw=1.6)
        ax.add_patch(arrow)
        a2 = FancyArrowPatch((x, 62.5), (x, 73.5), arrowstyle="-|>",
                             mutation_scale=14, color=SUB, lw=1.6)
        ax.add_patch(a2)
    save(fig, "w-hierarchy.png")


# =================================================== TAGLINE BANNER ==========
def tagline_banner():
    fig, ax = canvas(12.9, 1.15)
    txt(ax, 50, 62, "RAKSHAK-NET — A SOVEREIGN CRIMINAL-INTELLIGENCE MESH FOR INDIAN POLICING",
        size=16.5, weight="bold", ha="center", color=NAVY)
    ax.plot([31, 69], [28, 28], color=CYAN, lw=3, solid_capstyle="round")
    save(fig, "w-tagline.png")


if __name__ == "__main__":
    print("Generating slide-2 WINNER-FORMAT assets (transparent) ...")
    problem_panel()
    solution_panel()
    hierarchy_3tier()
    tagline_banner()
