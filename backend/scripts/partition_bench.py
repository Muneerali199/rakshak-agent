#!/usr/bin/env python3
"""Partition the seed-42 benchmark into district vaults for the mesh demo.

Each vault gets only the records its districts would legally hold — policing is a
State subject, so the demo's data sovereignty is real, not cosmetic:

    delhi  ← New Delhi, Kanpur
    mumbai ← Mumbai, Lucknow
    jaipur ← Jaipur, Kolkata

Rules:
  * FIR  → by ``district`` field; CDR → by tower city; FIN → hash of sender account.
  * **Planted anomaly sets are pinned whole to one vault** (the vault holding the
    majority of the set's records) — a burst/cycle/escalation must stay detectable
    inside a single district, exactly as it would in reality.
  * Mentions follow their record's vault.
  * Each vault gets a sliced ``ground_truth.json`` (planted anomalies fully inside
    it) so per-vault evaluation stays honest.

Run:  python3 scripts/partition_bench.py
Writes: backend/output-vaults/{delhi,mumbai,jaipur}/*.jsonl + ground_truth.json
Then verifies: per-vault anomaly + escalation detection still fire.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

OUT = BACKEND / "output"
VAULTS_DIR = BACKEND / "output-vaults"

VAULT_OF_DISTRICT = {
    "New Delhi": "delhi", "Kanpur": "delhi",
    "Mumbai": "mumbai", "Lucknow": "mumbai",
    "Jaipur": "jaipur", "Kolkata": "jaipur",
}
VAULT_IDS = ["delhi", "mumbai", "jaipur"]


def _load(name: str) -> list[dict]:
    p = OUT / name
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def _cdr_city(rec: dict) -> str:
    return rec.get("tower", "").split(",")[-1].strip()


def _fin_vault(rec: dict) -> str:
    h = int(hashlib.sha256(rec["sender_account"].encode()).hexdigest(), 16)
    return VAULT_IDS[h % len(VAULT_IDS)]


def main() -> None:
    fir, cdr, fin, mentions = (_load(n) for n in
                               ("fir.jsonl", "cdr.jsonl", "fin.jsonl", "mentions.jsonl"))
    gt = json.loads((OUT / "ground_truth.json").read_text(encoding="utf-8"))

    # 1) natural assignment
    vault_of: dict[str, str] = {}
    for r in fir:
        vault_of[r["record_id"]] = VAULT_OF_DISTRICT[r["district"]]
    for r in cdr:
        vault_of[r["record_id"]] = VAULT_OF_DISTRICT[_cdr_city(r)]
    for r in fin:
        vault_of[r["record_id"]] = _fin_vault(r)

    # 2) pin planted anomaly sets whole to their majority vault
    pinned_sets: list[tuple[dict, str]] = []
    for a in gt.get("planted_anomalies", []):
        ids = [rid for rid in a.get("record_ids", []) if rid in vault_of]
        if not ids:
            continue
        counts = {v: 0 for v in VAULT_IDS}
        for rid in ids:
            counts[vault_of[rid]] += 1
        home = max(counts, key=counts.get)
        for rid in ids:
            vault_of[rid] = home
        pinned_sets.append((a, home))

    # 3) write partitions
    for vid in VAULT_IDS:
        (VAULTS_DIR / vid).mkdir(parents=True, exist_ok=True)
    parts: dict[str, dict[str, list]] = {v: {"fir": [], "cdr": [], "fin": [], "mentions": []}
                                         for v in VAULT_IDS}
    for name, recs in (("fir", fir), ("cdr", cdr), ("fin", fin)):
        for r in recs:
            parts[vault_of[r["record_id"]]][name].append(r)
    for m in mentions:
        v = vault_of.get(m["record_id"])
        if v:
            parts[v]["mentions"].append(m)

    for vid in VAULT_IDS:
        for name in ("fir", "cdr", "fin", "mentions"):
            lines = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in parts[vid][name])
            (VAULTS_DIR / vid / f"{name}.jsonl").write_text(lines, encoding="utf-8")
        planted = [a for a, home in pinned_sets if home == vid]
        gt_slice = dict(gt, planted_anomalies=planted)
        (VAULTS_DIR / vid / "ground_truth.json").write_text(
            json.dumps(gt_slice, ensure_ascii=False, indent=1), encoding="utf-8")

    # 4) verification: per-vault detection must still fire
    from analytics import detect_anomalies, evaluate_anomalies
    from analytics.escalation import detect_escalation
    from graph import build_graph
    from resolve import load_benchmark, resolve

    print(f"{'vault':<8} {'fir':>4} {'cdr':>5} {'fin':>4} | anomalies (eval) | escalation")
    print("-" * 78)
    for vid in VAULT_IDS:
        bench = load_benchmark(VAULTS_DIR / vid)
        graph = build_graph(bench, resolve(bench)["clusters"])
        anomalies = detect_anomalies(bench)
        planted = [a for a, home in pinned_sets if home == vid]
        ev = evaluate_anomalies(anomalies, planted) if planted else {"note": "no planted"}
        esc = detect_escalation(bench, graph)
        ev_s = (f"P {ev.get('precision', '-')} / R {ev.get('recall', '-')}"
                if isinstance(ev, dict) and "precision" in ev else str(ev))
        print(f"{vid:<8} {len(bench['fir']):>4} {len(bench['cdr']):>5} {len(bench['fin']):>4} | "
              f"{len(anomalies):>2} ({ev_s}) | {len(esc)}")
    print("\nWrote partitions to", VAULTS_DIR)


if __name__ == "__main__":
    main()
