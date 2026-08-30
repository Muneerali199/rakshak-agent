"""Stalking-escalation detection (paper §14 extension, Women Safety Division focus).

Most violence against women is preceded by an *escalating* contact pattern: a stalker
whose harassment FIR was filed does not stop — call volume climbs, night-time calls
begin, and proximity tightens. Each FIR sits in a separate file; nobody sees the
curve. This detector computes that curve.

Method (pure stdlib, fully deterministic):

* Group CDR records by directed (caller → receiver) pair, bucket calls by ISO week.
* **Volume spike** — latest week's count ≥ 2× the prior-weeks average and ≥ 4 calls.
* **Night-call bonus** — calls between 23:00 and 05:00 count double (a classic
  stalking signal), folded into the spike score.
* **Victim linkage** — if the receiver phone is attributed (graph USES edge) to a
  person named as complainant in any FIR, the caller is escalating toward a
  *protected party* → severity CRITICAL. The victim identity stays shielded; the
  alert exposes only the caller's behavior.

Every alert is an analytical lead for a human investigator — never a claim of
criminality (paper §14.2), and never a profile of the victim.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime

from resolve.io import deterministic_key

_NIGHT_HOURS = set(range(23, 24)) | set(range(0, 6))   # 23:00–05:59


def _phone_key(number: str) -> str:
    return "PH:" + deterministic_key("PHONE", number)


def _week_bucket(ts: str) -> str:
    """ISO week key for a CDR timestamp; unparseable → 'unknown'."""
    try:
        dt = datetime.fromisoformat(ts)
        iso = dt.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    except (ValueError, TypeError):
        return "unknown"


def _is_night(ts: str) -> bool:
    try:
        return datetime.fromisoformat(ts).hour in _NIGHT_HOURS
    except (ValueError, TypeError):
        return False


def detect_escalation(bench: dict, graph=None,
                      spike_ratio: float = 2.0, min_recent: int = 4) -> list[dict]:
    """Detect escalating caller→receiver contact patterns from CDR records.

    ``bench``  — the benchmark dict with a ``cdr`` list.
    ``graph``  — optional built graph; when given, receiver phones are checked for
                 attribution to a complainant (victim linkage raises severity).
    """
    # ---- bucket calls per directed pair --------------------------------------
    pair_weeks: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    pair_records: dict[tuple[str, str], list[str]] = defaultdict(list)
    pair_nights: dict[tuple[str, str], int] = defaultdict(int)
    pair_last_ts: dict[tuple[str, str], str] = {}

    for r in bench.get("cdr", []):
        caller, receiver = r["caller"], r["receiver"]
        pair = (caller, receiver)
        wk = _week_bucket(r.get("timestamp", ""))
        if wk == "unknown":
            continue
        pair_weeks[pair][wk] += 1
        pair_records[pair].append(r["record_id"])
        if _is_night(r.get("timestamp", "")):
            pair_nights[pair] += 1
        ts = r.get("timestamp", "")
        if ts > pair_last_ts.get(pair, ""):
            pair_last_ts[pair] = ts

    # ---- victim-linked receivers (receiver phone → complainant person) --------
    protected_receivers: set[str] = set()
    if graph is not None:
        complainant_clusters = {n.id for n in graph.nodes.values()
                                if n.type == "PERSON" and n.meta.get("role") == "victim"}
        for e in graph.edges.values():
            if e.type == "USES" and e.source in complainant_clusters:
                protected_receivers.add(e.target)   # e.target is a PH: node id

    alerts: list[dict] = []
    for (caller, receiver), weeks in pair_weeks.items():
        ordered = sorted(weeks)
        if len(ordered) < 2:
            continue                                # need a baseline and a rise
        counts = [weeks[w] for w in ordered]

        # peak-week escalation: find the earliest week whose volume is both
        # ≥ min_recent and ≥ spike_ratio × the average of the weeks BEFORE it.
        # (A later trickle week must not mask the spike — trajectory, not endpoint.)
        peak_i = None
        for i in range(1, len(counts)):
            prior = counts[:i]
            if counts[i] >= min_recent and counts[i] >= spike_ratio * statistics.fmean(prior):
                peak_i = i
                break
        if peak_i is None:
            continue
        recent = counts[peak_i]
        avg = statistics.fmean(counts[:peak_i])
        ratio = recent / avg

        nights = pair_nights[(caller, receiver)]
        # score: spike ratio with night-call amplification, squashed to (0,1)
        raw = ratio * (1 + 0.5 * nights)
        score = round(1 - 1 / (1 + raw / 10), 3)    # monotonic squash, ~0.5 at raw=10

        victim_linked = _phone_key(receiver) in protected_receivers
        if victim_linked:
            severity = "CRITICAL"
        elif nights >= 2 or ratio >= 4:
            severity = "HIGH"
        else:
            severity = "MEDIUM"

        alerts.append({
            "id": f"ESC-{len(alerts) + 1:03d}",
            "caller": _phone_key(caller),
            "caller_label": caller,
            "receiver": _phone_key(receiver),
            "receiver_label": receiver,
            "victim_linked": victim_linked,
            "weekly_counts": counts,
            "night_calls": nights,
            "score": score,
            "severity": severity,
            "reason": (
                f"contact volume {recent} in week {ordered[peak_i]} is {ratio:.1f}× the prior "
                f"weekly average ({avg:.1f})"
                + (f" with {nights} night-time calls" if nights else "")
                + (" — receiver is a complainant on record (protected party)"
                   if victim_linked else "")
                + " — analytical escalation lead, verify before acting"
            ),
            "evidence_record_ids": pair_records[(caller, receiver)][:20],
        })

    sev_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}
    alerts.sort(key=lambda a: (sev_rank[a["severity"]], -a["score"]))
    return alerts
