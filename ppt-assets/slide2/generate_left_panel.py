#!/usr/bin/env python3
"""
RAKSHAK-NET — Slide 2 LEFT PANEL (final): PROBLEM x3 + SOLUTION x3 + USP x3.

Judge-friendly: bold headline + short explanation per bullet. USP uses a
two-column row layout (head | explanation) so nothing can overlap.
Grounded in SIH26189 (AI-Powered Criminal Network Analysis System, NCRB/MHA).

Transparent, light-mode. Run:
  backend/.venv/bin/python ppt-assets/slide2/generate_left_panel.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import FancyBboxPatch

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
RED   = "#dc2626"
EMER  = "#059669"
CYAN  = "#0891b2"
CYANL = "#ecfeff"

plt.rcParams.update({"font.family": FAMS, "text.color": INK})


def run():
    fig = plt.figure(figsize=(7.4, 9.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    def txt(x, y, s, size=10, color=INK, weight="normal", ha="left",
            va="center", spacing=1.3):
        ax.text(x, y, s, fontsize=size, color=color, fontweight=weight,
                ha=ha, va=va, family=FAMS, linespacing=spacing)

    def header(y, label, c):
        txt(2, y, label, size=13.5, weight="bold", color=c)
        ax.plot([2, 2 + 2.9 * len(label) * 0.52], [y - 3.4, y - 3.4],
                color=c, lw=3, solid_capstyle="round")

    def bullet(y, head, expl, c):
        txt(2, y, "•", size=15, color=c, weight="bold")
        txt(4.6, y, head, size=10.8, weight="bold", color=INK)
        txt(4.6, y - 3.6, expl, size=9.0, color=SUB)

    # ================= PROBLEM (3 bullets) =================
    header(97.0, "PROBLEM", RED)
    bullet(90.0, "Police data sits in silos",
           "FIRs, CDRs and money trails live in separate district systems — one suspect's\n"
           "full picture takes days of manual cross-state requests. A central national\n"
           "database is legally impossible: policing is a State subject.", RED)
    bullet(76.5, "One person, many names",
           "Mohd · Mohamad · मोहम्मद — the same person written three ways across Hindi,\n"
           "English and Hinglish records. Manual matching misses links, cannot scale.", RED)
    bullet(64.5, "Generic AI is not court evidence",
           "LLM interfaces hallucinate links that do not exist. Investigators need every\n"
           "claim traceable to a source document — or it fails in court.", RED)

    # ================= SOLUTION (3 bullets) =================
    header(52.5, "SOLUTION", EMER)
    bullet(45.5, "Identity Resolution",
           "4-feature hybrid scoring fuses FIR, CDR and financial records into one\n"
           "canonical schema and resolves multilingual names into a single entity\n"
           "with confidence scores (live: Mohd ↔ मोहम्मद → MATCH).", EMER)
    bullet(32.5, "District Vault Mesh",
           "The UPI pattern: signed queries travel between district vaults over the\n"
           "existing police intranet — the closed network CCTNS already uses for\n"
           "15,000+ police stations. FIR data never leaves its district.", EMER)
    bullet(19.5, "Evidence-Grounded Intelligence",
           "A temporal knowledge graph where every link carries its source + SHA-256\n"
           "hash; victims unmask only behind dual-signed warrants; every human\n"
           "decision lands in a tamper-evident ledger.", EMER)

    # ================= USP (3 rows, two-column) =================
    ax.add_patch(FancyBboxPatch((1.2, 0.8), 97.6, 13.2,
                 boxstyle="round,pad=0,rounding_size=1.6",
                 fc=CYANL, ec=CYAN, lw=1.8))
    txt(3.4, 11.8, "USP — WHY ONLY US", size=12, weight="bold", color=NAVY)
    rows = [
        (8.4, "Constitutional by design", "mesh, never a central database — legally deployable"),
        (5.6, "Zero hallucination", "no LLM in the serving path · answers cite evidence"),
        (2.8, "Sovereign AI stack", "all models on-premise · demo offline · rides CCTNS intranet"),
    ]
    for y, head, expl in rows:
        txt(3.4, y, "•", size=12, color=CYAN, weight="bold")
        txt(5.8, y, head, size=9.4, weight="bold", color=INK)
        txt(30.5, y, expl, size=8.8, color=SUB)

    fig.savefig(OUT / "left-panel.png", dpi=200, transparent=True)
    plt.close(fig)
    print("  done left-panel.png")


if __name__ == "__main__":
    run()
