"""RAKSHAK anomaly detectors (paper §14, Algorithm 6) — pure standard library.

Three MVP detectors over the benchmark records:

* ``CIRCULAR_FLOW`` — cycle detection over the account-transfer graph (A→B→C→A),
  the classic layering pattern of money laundering. Cycles up to length 5.
* ``COMM_BURST``    — z-score on per-phone call volume; a sudden spike of calls.
* ``TRANS_BURST``   — z-score on per-account outgoing transfer count.

Every anomaly is an *analytical* alert requiring investigation — never a claim of
criminality (paper §14.2). ``evaluate`` scores the detectors against the
generator's planted positives (``ground_truth.planted_anomalies``), giving real
precision/recall numbers for the benchmark — possible only because the data is
synthetic, and disclosed as such.
"""
from __future__ import annotations

import math
import statistics
from collections import defaultdict

from resolve.io import deterministic_key


def _phone_key(number: str) -> str:
    return "PH:" + deterministic_key("PHONE", number)


def _account_key(number: str) -> str:
    return "AC:" + deterministic_key("ACCOUNT", number)


def _logistic(z: float) -> float:
    return round(1 / (1 + math.exp(-z)), 3)


# ─────────────────────────── detectors ───────────────────────────

def _find_cycles(edges: dict[str, dict[str, list[str]]], max_len: int = 5) -> list[list[str]]:
    """All elementary cycles of length 3..max_len in a small directed graph (DFS)."""
    cycles: list[list[str]] = []
    nodes = sorted(edges)
    def dfs(start: str, cur: str, path: list[str], seen: set[str]) -> None:
        for nxt in sorted(edges.get(cur, {})):
            if nxt == start and len(path) >= 3:
                cycles.append(path.copy())
            elif nxt not in seen and len(path) < max_len and nxt > start:
                # nxt > start canonicalises rotation so each cycle is found once
                seen.add(nxt)
                path.append(nxt)
                dfs(start, nxt, path, seen)
                path.pop()
                seen.discard(nxt)
    for s in nodes:
        dfs(s, s, [s], {s})
    return cycles


def _temporal_chain(timestamps_per_leg: list[list[str]], window_hours: float) -> bool:
    """Can the cycle legs be chained non-decreasing in time within ``window_hours``?

    Money launderers layer fast — a ring that closes within days is the paper's
    detection-latency target (§23); rings scattered over months are coincidence.
    The cycle can close at any leg, so every rotation is tried; greedy
    earliest-next pick is optimal per candidate start.
    """
    from datetime import datetime

    def ts(t: str) -> float:
        return datetime.fromisoformat(t).timestamp() if t else 0.0

    legs = [sorted(ts(t) for t in leg) for leg in timestamps_per_leg]
    n = len(legs)
    for rot in range(n):                              # which leg the money enters first
        order = legs[rot:] + legs[:rot]
        for start in order[0]:
            cur = start
            ok = True
            for leg in order[1:]:
                nxt = next((t for t in leg if t >= cur), None)
                if nxt is None:
                    ok = False
                    break
                cur = nxt
            if ok and cur - start <= window_hours * 3600:
                return True
    return False


def detect_circular_flows(fin: list[dict], window_hours: float = 24 * 7) -> list[dict]:
    """Temporally-coherent cycles in the account-transfer graph (A→B→C→A within days)."""
    leg_records: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    for r in fin:
        leg_records[(r["sender_account"], r["receiver_account"])].append(
            (r["timestamp"], r["record_id"]))

    adj: dict[str, dict[str, list[tuple[str, str]]]] = defaultdict(dict)
    for (s, t), recs in leg_records.items():
        adj[s][t] = recs

    anomalies = []
    for cyc in _find_cycles({s: dict(t) for s, t in adj.items()}):
        legs = [adj[cyc[i]][cyc[(i + 1) % len(cyc)]] for i in range(len(cyc))]
        if not _temporal_chain([[t for t, _ in leg] for leg in legs], window_hours):
            continue                                   # ring exists but not layered fast → skip
        accounts = [_account_key(a) for a in cyc]
        rids = [rid for leg in legs for _, rid in leg]
        ring = cyc + [cyc[0]]
        anomalies.append({
            "kind": "CIRCULAR_FLOW",
            "entity_id": accounts[0],
            "participants": accounts,
            "severity": 0.95,
            "z_score": None,
            "reason": f"circular fund flow across {len(cyc)} accounts within "
                      f"{window_hours // 24} days: " + " → ".join(ring),
            "evidence_record_ids": rids,
        })
    return anomalies


def _zscore_anomalies(counts: dict[str, int], kind: str, threshold: float = 2.0) -> list[dict]:
    """Flag entities whose activity count is ≥ threshold z-scores above the mean."""
    if len(counts) < 2:
        return []
    vals = list(counts.values())
    mean = statistics.fmean(vals)
    std = statistics.pstdev(vals) or 1.0
    out = []
    for key, n in counts.items():
        z = (n - mean) / std
        if z >= threshold:
            out.append({
                "kind": kind,
                "entity_id": key,
                "participants": [key],
                "severity": _logistic(z),
                "z_score": round(z, 2),
                "reason": f"activity volume {n} is {z:.1f}σ above the network mean "
                          f"({mean:.1f}) — analytical anomaly, verify before acting",
                "evidence_record_ids": [],
            })
    return out


def detect_comm_bursts(cdr: list[dict], window_hours: float = 48) -> list[dict]:
    """Windowed call bursts: a phone's *densest* sliding window, z-scored.

    A burst is a temporal event — "15 calls inside 48h" — not a high lifetime total.
    Scoring each phone by its densest sliding window keeps slow-burn escalation
    trajectories (a few calls a week for weeks) out of the burst detector, so the
    two anomaly families don't cannibalise each other's ground truth.
    """
    from datetime import datetime
    by_phone: dict[str, list[float]] = defaultdict(list)
    for r in cdr:
        try:
            ts = datetime.fromisoformat(r["timestamp"]).timestamp()
        except (ValueError, TypeError, KeyError):
            continue
        by_phone[_phone_key(r["caller"])].append(ts)
        by_phone[_phone_key(r["receiver"])].append(ts)
    counts: dict[str, int] = {}
    for k, tss in by_phone.items():
        tss.sort()
        best, j = 0, 0
        for i, t in enumerate(tss):
            while t - tss[j] > window_hours * 3600:
                j += 1
            best = max(best, i - j + 1)
        counts[k] = best
    return _zscore_anomalies(counts, "COMM_BURST")


def detect_trans_bursts(fin: list[dict]) -> list[dict]:
    counts: dict[str, int] = defaultdict(int)
    for r in fin:
        counts[_account_key(r["sender_account"])] += 1
    return _zscore_anomalies(dict(counts), "TRANS_BURST")


# ─────────────────────── orchestration + evaluation ───────────────────────

def detect_anomalies(bench: dict) -> list[dict]:
    """Run all detectors over the benchmark; returns anomalies sorted by severity."""
    found = (
        detect_circular_flows(bench["fin"])
        + detect_comm_bursts(bench["cdr"])
        + detect_trans_bursts(bench["fin"])
    )
    found.sort(key=lambda a: (-a["severity"], a["kind"], a["entity_id"]))
    for i, a in enumerate(found, 1):
        a["id"] = f"ANOM-{i:03d}"
    return found


def evaluate_anomalies(detected: list[dict], planted: list[dict]) -> dict:
    """Precision/recall of each detector vs the generator's planted positives.

    Cycle matching is at ring level (a detected cycle is a TP when its account set
    equals a planted ring); bursts match on the flagged phone number.
    """
    def pr(kind: str, detected_keys: set, planted_keys: set) -> dict:
        tp = len(detected_keys & planted_keys)
        return {
            "planted": len(planted_keys),
            "detected": len(detected_keys),
            "true_positives": tp,
            "precision": round(tp / len(detected_keys), 3) if detected_keys else None,
            "recall": round(tp / len(planted_keys), 3) if planted_keys else None,
        }

    planted_cycles = {frozenset(_account_key(a) for a in p["accounts"])
                      for p in planted if p["kind"] == "CIRCULAR_FLOW"}
    detected_cycles = {frozenset(a["participants"]) for a in detected if a["kind"] == "CIRCULAR_FLOW"}
    cycle_pr = pr("CIRCULAR_FLOW", detected_cycles, planted_cycles)

    planted_phones = {p["phone"] for p in planted if p["kind"] == "COMM_BURST"}
    burst_pr = pr(
        "COMM_BURST",
        {a["entity_id"] for a in detected if a["kind"] == "COMM_BURST"},
        {_phone_key(x) for x in planted_phones},
    )
    return {"CIRCULAR_FLOW": cycle_pr, "COMM_BURST": burst_pr}
