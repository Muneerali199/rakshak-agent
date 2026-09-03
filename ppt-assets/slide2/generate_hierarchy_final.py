#!/usr/bin/env python3
"""
RAKSHAK-NET — Winner-exact VERTICAL 3-tier HIERARCHICAL DIAGRAM (slide 2, right).

Mirrors the SIH-winning deck: rotated tier labels on the left +
  ADMINISTRATION (top):     MESH GATEWAY capsule
  CORE INFRASTRUCTURE:      3 district vault boxes + ledger chip
  END-USER APPLICATION:     INVESTIGATOR WORKBENCH capsule
with vertical two-way arrows between tiers.

Transparent, light-mode. Run:
  backend/.venv/bin/python ppt-assets/slide2/generate_hierarchy_final.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = Path(__file__).parent

INK   = "#0f172a"
SUB   = "#64748b"
NAVY  = "#1e293b"
CYAN  = "#0891b2"
CYANL = "#ecfeff"
EMER  = "#059669"
EMERL = "#d1fae5"
PURPLE = "#7c3aed"
PURLL = "#f5f3ff"
AMBER = "#d97706"
AMBL  = "#fef3c7"
LINE  = "#94a3b8"

plt.rcParams.update({"font.family": ["DejaVu Sans"], "text.color": INK})


def run():
    fig = plt.figure(figsize=(6.6, 7.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    def box(x, y, w, h, fc="#ffffff", ec=LINE, lw=1.6, r=2.0):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                     boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw))

    def txt(x, y, s, size=10, color=INK, weight="normal", ha="center",
            va="center", mono=False, spacing=1.4, rot=0):
        fam = ["DejaVu Sans Mono"] if mono else ["DejaVu Sans"]
        ax.text(x, y, s, fontsize=size, color=color, fontweight=weight,
                ha=ha, va=va, family=fam, linespacing=spacing, rotation=rot)

    def darrow(x, y1, y2, color=SUB):
        ax.add_patch(FancyArrowPatch((x, y1), (x, y2), arrowstyle="<|-|>",
                     mutation_scale=14, color=color, lw=2.0))

    # ---------------- title ----------------
    txt(52, 96.5, "HIERARCHICAL DIAGRAM", size=14, weight="bold", color=NAVY)
    ax.plot([33, 71], [93.2, 93.2], color=CYAN, lw=3, solid_capstyle="round")

    # ---------------- tier labels (rotated, far left) ----------------
    for label, y, c in [("ADMINISTRATION", 78, CYAN),
                        ("CORE INFRASTRUCTURE", 51, EMER),
                        ("END-USER APPLICATION", 18, PURPLE)]:
        txt(4.0, y, label, size=8.8, color=c, weight="bold", rot=90)
        ax.plot([9.0, 9.0], [y - 10, y + 10], color=c, lw=1.2, alpha=0.55)

    # ============ TIER 1 · MESH GATEWAY (administration, top) ============
    box(13, 68, 83, 19, fc=CYANL, ec=CYAN, lw=2.3)
    txt(54.5, 83.5, "MESH GATEWAY", size=11.5, weight="bold", color=CYAN)
    txt(54.5, 79.8, "NPCI-style switch · :8000", size=7.6, color=SUB, mono=True)
    feats = [("Query routing", 31), ("Receipt verification", 77),
             ("Hash-chained exchange ledger", 31), ("Warrant registry", 77)]
    fy = 74.6
    for i, (f, fx) in enumerate(feats):
        y = fy if i < 2 else fy - 4.4
        txt(fx - 10.5, y, "•", size=9, color=CYAN, weight="bold", ha="left")
        txt(fx - 8.8, y, f, size=8.2, ha="left")

    # vertical arrows tier1 -> tier2
    darrow(54.5, 66.5, 62.5)

    # ============ TIER 2 · DISTRICT VAULTS (core infrastructure) =========
    vaults = [
        (13.5, "DELHI VAULT",  ":8001", EMER, EMERL),
        (41.5, "MUMBAI VAULT", ":8002", PURPLE, PURLL),
        (69.5, "JAIPUR VAULT", ":8003", AMBER, AMBL),
    ]
    for x, name, port, c, fl in vaults:
        box(x, 46, 25, 16.5, fc=fl, ec=c, lw=2.1)
        txt(x + 12.5, 58.6, name, size=9.6, weight="bold", color=c)
        txt(x + 12.5, 55.0, port, size=7.6, color=SUB, mono=True)
        txt(x + 12.5, 51.0, "own FIR/CDR/FIN graph\n+ SQLite ledgers", size=7.2,
            color=SUB, spacing=1.3)
    # ledger chip
    box(31, 37.5, 40, 6.6, fc="#ffffff", ec=NAVY, lw=1.5)
    txt(51, 40.8, "HASH-CHAINED RECEIPTS  ·  3 TAMPER-EVIDENT LEDGERS", size=7.4,
        weight="bold", color=NAVY)

    # vertical arrows tier2 -> tier3
    darrow(54.5, 29.5, 35.5)

    # ============ TIER 3 · INVESTIGATOR WORKBENCH (end-user, bottom) =====
    box(13, 8, 83, 21, fc="#ffffff", ec=PURPLE, lw=2.3)
    txt(54.5, 25.5, "INVESTIGATOR WORKBENCH", size=11.5, weight="bold", color=PURPLE)
    txt(54.5, 21.9, "live analyst UI · React 19 + React Flow", size=7.6, color=SUB, mono=True)
    users = [
        (25, "INVESTIGATING\nOFFICERS", "case graph · FIR ingest\nmesh queries", CYAN),
        (54.5, "SENIOR OFFICERS\n(SP+)", "warrant countersign\nfour-eyes gate", AMBER),
        (84, "NCRB / COURT\nAUDITORS", "evidence chain reports\nledger verification", EMER),
    ]
    for ux, name, sub, c in users:
        txt(ux, 15.8, name, size=8.4, weight="bold", color=c, spacing=1.25)
        txt(ux, 11.2, sub, size=7.2, color=SUB, spacing=1.3)

    # ---------------- bottom caption ----------------
    txt(54.5, 3.2, "signed queries travel between tiers  ·  FIR data never leaves its vault",
        size=8.4, weight="bold", color=NAVY)

    fig.savefig(OUT / "hierarchy-final.png", dpi=200, transparent=True)
    plt.close(fig)
    print("  done hierarchy-final.png")


if __name__ == "__main__":
    run()
