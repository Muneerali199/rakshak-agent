#!/usr/bin/env python3
"""
RAKSHAK-NET — SIH 2026 deck diagram generator.

Generates brand-themed diagrams (dark #0a0f1c, cyan/purple/emerald accents)
as high-res PNGs for the Venom SIH idea-submission deck.

Run:  backend/.venv/bin/python ppt-assets/generate_diagrams.py
Out:  ppt-assets/*.png  (200 DPI)
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = Path(__file__).parent

# Register a Devanagari-capable font so Hindi renders (macOS system font).
_DEV = "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc"
if Path(_DEV).exists():
    fm.fontManager.addfont(_DEV)
    _FAMILIES = ["DejaVu Sans", "Devanagari Sangam MN"]
else:
    _FAMILIES = ["DejaVu Sans"]

# ---------------------------------------------------------------- palette ---
BG      = "#0a0f1c"
PANEL   = "#131c2e"
PANEL2  = "#1a2540"
BORDER  = "#2b3a5c"
TXT     = "#e2e8f0"
SUB     = "#94a3b8"
CYAN    = "#22d3ee"
PURPLE  = "#a78bfa"
EMERALD = "#34d399"
AMBER   = "#fbbf24"
RED     = "#f87171"
PINK    = "#f472b6"

plt.rcParams.update({
    "font.family": _FAMILIES,
    "text.color": TXT,
    "figure.facecolor": BG,
    "axes.facecolor": BG,
    "savefig.facecolor": BG,
})


def canvas(w, h):
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, fc=PANEL, ec=BORDER, lw=1.4, r=1.6, alpha=1.0, ls="-"):
    b = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                       fc=fc, ec=ec, lw=lw, alpha=alpha, linestyle=ls)
    ax.add_patch(b)
    return b


def txt(ax, x, y, s, size=11, color=TXT, weight="normal", ha="center",
        va="center", mono=False, spacing=1.3):
    fam = (["DejaVu Sans Mono"] + _FAMILIES) if mono else _FAMILIES
    ax.text(x, y, s, fontsize=size, color=color, fontweight=weight, ha=ha,
            va=va, family=fam, linespacing=spacing)


def arrow(ax, x1, y1, x2, y2, color=CYAN, lw=2.2, style="-|>", ms=16,
          ls="-", alpha=1.0, rad=0.0):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                        mutation_scale=ms, color=color, lw=lw, linestyle=ls,
                        alpha=alpha, connectionstyle=f"arc3,rad={rad}",
                        shrinkA=2, shrinkB=2)
    ax.add_patch(a)


def header(ax, title, subtitle=None, accent=CYAN):
    txt(ax, 50, 95.5, title, size=19, weight="bold")
    ax.plot([38, 62], [91.5, 91.5], color=accent, lw=3, solid_capstyle="round")
    if subtitle:
        txt(ax, 50, 88, subtitle, size=10.5, color=SUB)


def footer(ax, s="RAKSHAK-NET  ·  Team Venom  ·  SIH 2026 (SIH26189)"):
    txt(ax, 50, 2.2, s, size=8, color="#5b6b8c")


def save(fig, name):
    fig.savefig(OUT / name, dpi=200)
    plt.close(fig)
    print(f"  done {name}")


# ============================================================ 1 · MESH ======
def mesh_architecture():
    fig, ax = canvas(13.33, 8.2)
    header(ax, "The District Vault Mesh",
           "The UPI pattern for criminal intelligence — queries travel, data never leaves its district", CYAN)

    # Gateway (NPCI-style switch)
    box(ax, 33, 58, 34, 22, fc=PANEL2, ec=CYAN, lw=2.4)
    txt(ax, 50, 75.5, "MESH GATEWAY", size=13.5, weight="bold", color=CYAN)
    txt(ax, 50, 71.3, "NPCI-style switch  ·  :8000", size=9.5, color=SUB, mono=True)
    txt(ax, 50, 65.5, "routes signed queries · stores RECEIPTS, never case data\nhash-chained exchange ledger · /mesh/verify", size=9, color=TXT)

    vaults = [
        (8,  20, "DELHI VAULT",  ":8001", "116 nodes · 253 edges", EMERALD),
        (38, 20, "MUMBAI VAULT", ":8002", "122 nodes · 301 edges", PURPLE),
        (68, 20, "JAIPUR VAULT", ":8003", "136 nodes · 242 edges", AMBER),
    ]
    for x, y, name, port, stats, c in vaults:
        box(ax, x, y, 24, 18, fc=PANEL, ec=c, lw=2.0)
        txt(ax, x+12, y+13.8, name, size=11.5, weight="bold", color=c)
        txt(ax, x+12, y+9.8, f"{port} · its own FIR/CDR/FIN graph", size=8.6, color=SUB, mono=True)
        txt(ax, x+12, y+5.8, stats + "\nHMAC-signed receipts", size=8.6, color=TXT)

        # gateway -> vault (query) and vault -> gateway (receipt)
        gx = 42 if x < 33 else (50 if x < 60 else 58)
        arrow(ax, gx, 58.5, x+12, 38.6, color=c, lw=2.0, rad=-0.12 if x < 33 else (0.12 if x > 60 else 0.0))
        txt(ax, (gx+x+12)/2 - (6 if x < 33 else (-6 if x > 60 else 0)), 49,
            "signed query", size=7.6, color=c, ha="center")

    txt(ax, 50, 12, "FIR data stays in-district  ·  only answers + signatures cross  ·  every exchange lands in the ledger",
        size=10, color=EMERALD, weight="bold")
    txt(ax, 50, 8, "UPI made banks interoperable without centralizing money — we make police districts interoperable without centralizing FIRs",
        size=9, color=SUB)
    footer(ax)
    save(fig, "01-mesh-architecture.png")


# ====================================================== 2 · FIR PIPELINE ====
def fir_pipeline():
    fig, ax = canvas(13.33, 7.0)
    header(ax, "From FIR to Court-Ready Evidence Chain",
           "Methodology — every step is deterministic, auditable, and hash-chained", EMERALD)

    steps = [
        ("1. FILE FIR", "paste raw FIR text\nHindi / English / Hinglish", CYAN),
        ("2. EXTRACT", "regex NER · source spans\nzero LLM, fully auditable", CYAN),
        ("3. RESOLVE", "Mohd ↔ Mohamad\n↔ मोहम्मद · hybrid scoring", PURPLE),
        ("4. MESH QUERY", "cross-district fan-out\nsigned receipts per vault", PURPLE),
        ("5. GRAPH + LEDGER", "temporal edges · SHA-256\nprovenance on every link", EMERALD),
        ("6. WARRANT GATE", "protected data needs\ndual-signed warrant (SP+)", AMBER),
        ("7. REPORT 2.0", "court-ready chain\n+ blindspot honesty score", EMERALD),
    ]
    n = len(steps)
    w, h, gap = 11.6, 30, 1.4
    total = n * w + (n - 1) * gap
    x0 = (100 - total) / 2
    y = 38
    for i, (name, sub, c) in enumerate(steps):
        x = x0 + i * (w + gap)
        box(ax, x, y, w, h, fc=PANEL, ec=c, lw=2.0, r=2.2)
        txt(ax, x + w/2, y + h - 6.5, name, size=9.6, weight="bold", color=c)
        txt(ax, x + w/2, y + h/2 - 3.5, sub, size=7.4, color=TXT)
        if i < n - 1:
            arrow(ax, x + w + 0.2, y + h/2, x + w + gap - 0.2, y + h/2,
                  color=BORDER, lw=2.4, ms=13)

    # guarantee band
    box(ax, 12, 14, 76, 12, fc=PANEL2, ec=EMERALD, lw=1.6, r=2.0)
    txt(ax, 50, 20, "GUARANTEED IN CODE", size=9.5, weight="bold", color=EMERALD)
    txt(ax, 50, 16.5,
        "no LLM in the serving path → cannot hallucinate   ·   every edge cites its source document   ·   every access is ledgered",
        size=8.8, color=TXT)
    footer(ax)
    save(fig, "02-fir-to-report-pipeline.png")


# =================================================== 3 · WARRANT SEQUENCE ===
def warrant_sequence():
    fig, ax = canvas(13.33, 7.6)
    header(ax, "The Warrant Gate — DEPA Consent for Police Data",
           "Unmasking a protected identity is a legal action, not a click", AMBER)

    actors = [(14, "INVESTIGATING\nOFFICER", CYAN), (50, "WARRANT\nGATE", AMBER),
              (86, "SENIOR OFFICER\n(SP+ countersign)", PURPLE)]
    for x, name, c in actors:
        box(ax, x - 11, 66, 22, 12, fc=PANEL, ec=c, lw=2.0)
        txt(ax, x, 72, name, size=9.8, weight="bold", color=c)
        ax.plot([x, x], [26, 66], color=BORDER, lw=1.2, ls="--")

    seq = [
        (14, 50, 60, "1 · request warrant — scope, reason, expiry", CYAN),
        (50, 86, 53, "2 · forward for countersign", AMBER),
        (86, 50, 46, "3 · dual-sign  (self-approval REJECTED in code)", PURPLE),
        (50, 14, 39, "4 · unmask — scoped · expiring · revocable", EMERALD),
    ]
    for x1, x2, y, label, c in seq:
        arrow(ax, x1 + (2 if x2 > x1 else -2), y, x2 - (2 if x2 > x1 else -2), y,
              color=c, lw=2.2, ms=15)
        txt(ax, 50, y + 2.4, label, size=8.8, color=c)

    box(ax, 22, 14, 56, 10, fc=PANEL2, ec=RED, lw=1.6, r=2.0)
    txt(ax, 50, 19.8, "EVERY ACCESS IS HASH-CHAINED INTO THE WARRANT LEDGER", size=9.2,
        weight="bold", color=RED)
    txt(ax, 50, 16.2, "/api/warrants/verify walks the chain and names the first tampered record",
        size=8.4, color=SUB)
    footer(ax)
    save(fig, "03-warrant-gate-sequence.png")


# ==================================================== 4 · FEASIBILITY ======
def feasibility_grid():
    fig, ax = canvas(13.33, 7.8)
    header(ax, "Feasibility & Viability",
           "The only SIH entry that is constitutional BY DESIGN — policing is a State subject, so we mesh instead of centralize", PURPLE)

    cards = [
        ("TECHNICAL", "119/119 tests passing\nlive 3-vault mesh demo\nstdlib core, air-gapped", CYAN),
        ("LEGAL", "Seventh-Schedule compliant\nno central FIR database\nDEPA-style consent artifacts", EMERALD),
        ("OPERATIONAL", "runs offline / air-gapped\nNIC MeghRaj deployable\nCCTNS-schema native", PURPLE),
        ("ECONOMIC", "zero cloud / API cost\nstdlib Python core\ncommodity hardware", AMBER),
        ("SOCIAL", "women-safety focused\nvictim-shield by policy\nno victim profiling", PINK),
    ]
    n = len(cards)
    w, h, gap = 17.6, 30, 1.8
    total = n * w + (n - 1) * gap
    x0 = (100 - total) / 2
    y = 44
    for i, (name, body, c) in enumerate(cards):
        x = x0 + i * (w + gap)
        box(ax, x, y, w, h, fc=PANEL, ec=c, lw=2.0, r=2.4)
        txt(ax, x + w/2, y + h - 5, name, size=10.5, weight="bold", color=c)
        txt(ax, x + w/2, y + h/2 - 3.5, body, size=8.2, color=TXT)

    # risks -> mitigations strip
    txt(ax, 50, 36.5, "RISKS  →  MITIGATIONS", size=10.5, weight="bold", color=SUB)
    pairs = [
        ("Demo HMAC secrets", "NIC-issued PKI certs in production"),
        ("Synthetic benchmark data", "CCTNS schema mapping = drop-in"),
        ("Adoption resistance", "human-in-the-loop on every output"),
    ]
    w2, h2, gap2 = 29.5, 12, 2.2
    total2 = 3 * w2 + 2 * gap2
    x1 = (100 - total2) / 2
    for i, (risk, mit) in enumerate(pairs):
        x = x1 + i * (w2 + gap2)
        box(ax, x, 20, w2, h2, fc=PANEL2, ec=BORDER, lw=1.4, r=1.8)
        txt(ax, x + w2/2, 28.4, risk, size=8.8, color=RED, weight="bold")
        txt(ax, x + w2/2, 24.6, "↓", size=10, color=SUB)
        txt(ax, x + w2/2, 22.2, mit, size=8.2, color=EMERALD)
    footer(ax)
    save(fig, "04-feasibility-grid.png")


# ======================================================== 5 · IMPACT ========
def impact_stats():
    fig, ax = canvas(13.33, 7.8)
    header(ax, "Impact & Benefits",
           "Built for the NCRB Women Safety Division — intervention before the next FIR", EMERALD)

    stats = [
        ("58L+", "FIRs registered yearly (NCRB)", "manual cross-district\nlinkage today", CYAN),
        ("16,000+", "police stations on CCTNS", "siloed per-district\nrecords today", PURPLE),
        ("days → seconds", "cross-district linkage", "signed mesh query\nvs manual correspondence", EMERALD),
        ("3", "tamper-evident ledgers", "reviews · warrants · mesh\nall verify ok:true", AMBER),
        ("0", "LLM calls in serving path", "hallucination impossible\nby construction", PINK),
    ]
    n = len(stats)
    w, h, gap = 17.6, 34, 1.8
    total = n * w + (n - 1) * gap
    x0 = (100 - total) / 2
    y = 42
    for i, (big, label, sub, c) in enumerate(stats):
        x = x0 + i * (w + gap)
        box(ax, x, y, w, h, fc=PANEL, ec=c, lw=2.0, r=2.4)
        txt(ax, x + w/2, y + h - 8.5, big, size=17, weight="bold", color=c)
        txt(ax, x + w/2, y + h - 14.5, label, size=8.0, color=TXT, weight="bold")
        txt(ax, x + w/2, y + 8.5, sub, size=7.6, color=SUB)

    bands = [
        ("SOCIAL", "stalking-escalation alerts flag the pattern BEFORE assault · victims shielded, never profiled", PINK),
        ("ECONOMIC", "officer-hours of manual correlation collapse to one signed query · zero new infrastructure", AMBER),
        ("GOVERNANCE", "every answer court-traceable · every access warrant-backed · audit-ready by default", CYAN),
    ]
    y2 = 26
    for i, (tag, body, c) in enumerate(bands):
        yy = y2 - i * 7.4
        box(ax, 10, yy - 2.6, 80, 6.2, fc=PANEL2, ec=c, lw=1.4, r=1.6)
        txt(ax, 17.5, yy + 0.5, tag, size=9.4, weight="bold", color=c)
        txt(ax, 52.5, yy + 0.5, body, size=8.2, color=TXT)
    footer(ax)
    save(fig, "05-impact-stats.png")


# ==================================================== 6 · COMPARISON ========
def comparison_table():
    fig, ax = canvas(13.33, 7.6)
    header(ax, "Why Not What Exists Today?",
           "Every alternative either centralizes (illegal), surveils (unconstitutional), or phones home (foreign)", CYAN)

    cols = ["", "CCTNS today", "Foreign SaaS\n(Palantir-type)", "Surveillance-state\n(IJOP-type)", "RAKSHAK-NET"]
    rows = [
        ("Cross-district intelligence", "manual, days", "yes — but data leaves India", "yes — mass dragnet", "YES — signed mesh, seconds"),
        ("Legal under Seventh Schedule", "yes (but siloed)", "NO — centralizes state data", "n/a", "YES — data stays in-district"),
        ("Data sovereignty", "yes", "NO — foreign cloud", "state-controlled", "YES — on-prem, air-gapped"),
        ("Rights & audit trail", "partial", "opaque", "NONE", "YES — warrants + 3 ledgers"),
        ("Hallucination risk", "n/a", "LLM-driven", "n/a", "ZERO — retrieval-only"),
    ]
    x0, ytop, cw = 4, 76, [26, 16.5, 16.5, 16.5, 17.5]
    rh = 9.6
    xs = [x0]
    for w in cw[:-1]:
        xs.append(xs[-1] + w)
    # header row
    for j, ctext in enumerate(cols):
        c = EMERALD if j == 4 else BORDER
        fc = PANEL2 if j == 4 else PANEL
        box(ax, xs[j], ytop, cw[j] - 0.6, 10, fc=fc, ec=c, lw=2.0 if j == 4 else 1.2, r=1.2)
        txt(ax, xs[j] + cw[j]/2, ytop + 5, ctext, size=8.8,
            weight="bold", color=EMERALD if j == 4 else SUB)
    for i, row in enumerate(rows):
        y = ytop - (i + 1) * rh
        for j, cell in enumerate(row):
            c = EMERALD if j == 4 else BORDER
            fc = "#12233a" if j == 4 else (PANEL if j == 0 else BG)
            box(ax, xs[j], y, cw[j] - 0.6, rh - 0.6, fc=fc, ec=c,
                lw=1.6 if j == 4 else 1.0, r=1.2)
            col = TXT if j in (0, 4) else SUB
            if j > 0 and cell.startswith(("NO", "NONE")):
                col = RED
            if j > 0 and j != 4 and cell.startswith(("yes", "partial", "manual")):
                col = AMBER if cell != "yes" else SUB
            txt(ax, xs[j] + cw[j]/2, y + rh/2 - 0.3, cell, size=7.8,
                color=col, weight="bold" if j in (0, 4) else "normal")
    txt(ax, 50, 6.5, "China can surveil. Estonia can share. Only India — the land of UPI and DEPA — can do both, constitutionally.",
        size=9.6, color=CYAN, weight="bold")
    footer(ax)
    save(fig, "06-comparison.png")


# =================================================== 7 · GRAPH LAYERS =======
def graph_layers():
    fig, ax = canvas(13.33, 7.6)
    header(ax, "The Temporal Knowledge Graph",
           "Six proposed layers — three seeded and live today, every edge timestamped + SHA-256 hashed", PURPLE)

    layers = [
        ("6 · DIGITAL / SOCIAL", "planned", "#3b4a6b", False),
        ("5 · CASE / EVENT", "planned", "#3b4a6b", False),
        ("4 · ORGANIZATIONAL", "planned", "#3b4a6b", False),
        ("3 · SPATIAL", "LIVE — locations, sightings", AMBER, True),
        ("2 · FINANCIAL", "LIVE — accounts, transfers", EMERALD, True),
        ("1 · COMMUNICATION", "LIVE — calls, CDR links", CYAN, True),
    ]
    wmax, wmin = 76, 40
    y = 12
    h = 10.5
    for i, (name, tag, c, live) in enumerate(layers):
        w = wmin + (wmax - wmin) * (i + 1) / len(layers)
        x = (100 - w) / 2
        fc = PANEL if live else "#101627"
        box(ax, x, y + i * (h + 0.8), w, h, fc=fc, ec=c, lw=2.0 if live else 1.0,
            r=1.6, alpha=1.0 if live else 0.6, ls="-" if live else "--")
        txt(ax, 50, y + i * (h + 0.8) + h/2 + 1.6, name, size=10,
            weight="bold", color=c if live else SUB)
        txt(ax, 50, y + i * (h + 0.8) + h/2 - 2.6, tag, size=8,
            color=c if live else "#5b6b8c")

    txt(ax, 88, 30, "every edge:\nobserved / inferred\n+ timestamp\n+ provenance span\n+ SHA-256 hash", size=8.6, color=SUB, ha="left")
    footer(ax)
    save(fig, "07-graph-layers.png")


# ================================================= 8 · THREE GUARANTEES =====
def three_guarantees():
    fig, ax = canvas(13.33, 6.6)
    header(ax, "Three Guarantees — Enforced in Code",
           "India's first evidence-ledger criminal intelligence system", EMERALD)

    cards = [
        ("NEVER LIES", CYAN,
         "retrieval-only query\ncites the edges behind every claim\nrefuses unknowns — no LLM,\nno hallucination possible"),
        ("NEVER TAMPERS", PURPLE,
         "reviews · warrants · mesh exchanges\nSHA-256 hash-chained\nverify endpoints name the\nfirst broken record"),
        ("NEVER PROFILES\nTHE INNOCENT", PINK,
         "victim-shield policy in code\npseudonymized complainants\nunmasking needs a dual-signed,\nscoped, expiring warrant"),
    ]
    w, h, gap = 29, 44, 3.5
    total = 3 * w + 2 * gap
    x0 = (100 - total) / 2
    y = 26
    for i, (name, c, body) in enumerate(cards):
        x = x0 + i * (w + gap)
        box(ax, x, y, w, h, fc=PANEL, ec=c, lw=2.4, r=2.6)
        txt(ax, x + w/2, y + h - 8, name, size=12.5, weight="bold", color=c)
        ax.plot([x + w/2 - 5, x + w/2 + 5], [y + h - 12, y + h - 12], color=c, lw=2.4)
        txt(ax, x + w/2, y + h/2 - 4.5, body, size=8.6, color=TXT)
    txt(ax, 50, 14, "China's IJOP had the detection capability — without the rights or accountability. We inverted it.",
        size=9.4, color=SUB)
    footer(ax)
    save(fig, "08-three-guarantees.png")


if __name__ == "__main__":
    print("Generating RAKSHAK-NET deck diagrams ...")
    mesh_architecture()
    fir_pipeline()
    warrant_sequence()
    feasibility_grid()
    impact_stats()
    comparison_table()
    graph_layers()
    three_guarantees()
