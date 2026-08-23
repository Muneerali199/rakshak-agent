"""Score predicted clusters against synthgen ground truth (paper §23).

Metrics, matching the proposal's Evaluation table and its targets:

* **Pairwise Precision / Recall / F1** — over all within-cluster mention pairs
  (TP = pairs together in both pred & truth; FP = together in pred only;
  FN = together in truth only). Targets: P > 0.85, R > 0.80.
* **B-cubed Precision / Recall / F1** — per-mention averaged; robust to cluster
  size skew (Bagga & Baldwin), the standard coreference/ER metric.
* **False Merge Rate** — falsely-merged pairs / total non-matching pairs
  (< 0.01 target). Reported both overall and specifically on the ground-truth
  ``false_match_pairs`` traps.
* **False Split Rate** — falsely-split pairs / total matching pairs (< 0.05).

Only mentions with a real ``true_id`` (i.e. present in the ground-truth clusters)
are scored; ``AMOUNT`` mentions (true_id = null) are excluded, as they are a
normalization — not an entity-resolution — target.
"""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations


def _truth_label(gt: dict) -> dict[str, str]:
    """mention_id -> true entity id, from ground_truth.json clusters."""
    label: dict[str, str] = {}
    for eid, mids in gt["clusters"].items():
        for mid in mids:
            label[mid] = eid
    return label


def _pred_label(pred_clusters: dict) -> dict[str, str]:
    label: dict[str, str] = {}
    for cid, mids in pred_clusters.items():
        for mid in mids:
            label[mid] = cid
    return label


def _pairs_within(label: dict[str, str], universe: set[str]) -> set[frozenset]:
    """All unordered same-cluster mention pairs, restricted to ``universe``."""
    groups: dict[str, list[str]] = defaultdict(list)
    for mid, cid in label.items():
        if mid in universe:
            groups[cid].append(mid)
    pairs: set[frozenset] = set()
    for members in groups.values():
        for a, b in combinations(sorted(members), 2):
            pairs.add(frozenset((a, b)))
    return pairs


def _prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if (tp + fp) else 1.0
    r = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f1, 4),
            "tp": tp, "fp": fp, "fn": fn}


def _bcubed(truth: dict[str, str], pred: dict[str, str], universe: set[str]) -> dict:
    t_groups: dict[str, set[str]] = defaultdict(set)
    p_groups: dict[str, set[str]] = defaultdict(set)
    for mid in universe:
        t_groups[truth[mid]].add(mid)
        p_groups[pred[mid]].add(mid)
    prec = rec = 0.0
    for mid in universe:
        tc, pc = t_groups[truth[mid]], p_groups[pred[mid]]
        correct = len(tc & pc)
        prec += correct / len(pc)
        rec += correct / len(tc)
    n = len(universe) or 1
    prec, rec = prec / n, rec / n
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return {"precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4)}


def evaluate(pred: dict, gt: dict) -> dict:
    """Full §23 report comparing predicted clusters to ground truth."""
    truth = _truth_label(gt)
    pred_label = _pred_label(pred["clusters"])

    # score only mentions that (a) have a true id and (b) the predictor placed
    universe = set(truth) & set(pred_label)
    n_missing = len(set(truth) - set(pred_label))

    t_pairs = _pairs_within(truth, universe)
    p_pairs = _pairs_within(pred_label, universe)
    tp = len(t_pairs & p_pairs)
    fp = len(p_pairs - t_pairs)
    fn = len(t_pairs - p_pairs)

    # denominators for rate metrics
    n = len(universe)
    total_pairs = n * (n - 1) // 2
    total_matches = len(t_pairs)
    total_nonmatches = total_pairs - total_matches

    false_merge_rate = fp / total_nonmatches if total_nonmatches else 0.0
    false_split_rate = fn / total_matches if total_matches else 0.0

    # trap-specific false merges: did we merge any known false_match_pair?
    trap_merged = 0
    for a_eid, b_eid in gt.get("false_match_pairs", []):
        a_mids = [m for m in gt["clusters"].get(a_eid, []) if m in universe]
        b_mids = [m for m in gt["clusters"].get(b_eid, []) if m in universe]
        if any(pred_label[x] == pred_label[y] for x in a_mids for y in b_mids):
            trap_merged += 1
    n_traps = len(gt.get("false_match_pairs", []))

    # per-entity-type pairwise breakdown
    by_type = _by_type(truth, pred_label, gt, universe)

    return {
        "pairwise": _prf(tp, fp, fn),
        "bcubed": _bcubed(truth, pred_label, universe),
        "false_merge_rate": round(false_merge_rate, 5),
        "false_split_rate": round(false_split_rate, 5),
        "false_match_traps": {"merged": trap_merged, "total": n_traps},
        "by_type": by_type,
        "coverage": {
            "scored_mentions": n,
            "unresolved_truth_mentions": n_missing,
            "predicted_clusters": len(pred["clusters"]),
            "truth_clusters": len(gt["clusters"]),
        },
        "targets": {   # §23 thresholds, for a quick pass/fail read
            "precision>0.85": _prf(tp, fp, fn)["precision"] > 0.85,
            "recall>0.80": _prf(tp, fp, fn)["recall"] > 0.80,
            "false_merge_rate<0.01": false_merge_rate < 0.01,
            "false_split_rate<0.05": false_split_rate < 0.05,
        },
    }


def _by_type(truth, pred_label, gt, universe) -> dict:
    """Pairwise P/R/F1 split by the ground-truth entity type of each mention."""
    ent_type = {}
    for eid, mids in gt["clusters"].items():
        etype = gt["entities"].get(eid, {}).get("type", "UNKNOWN")
        for mid in mids:
            ent_type[mid] = etype

    out: dict[str, dict] = {}
    for etype in sorted(set(ent_type.get(m, "UNKNOWN") for m in universe)):
        sub = {m for m in universe if ent_type.get(m) == etype}
        tp_ = _pairs_within(truth, sub)
        pp_ = _pairs_within(pred_label, sub)
        out[etype] = _prf(len(tp_ & pp_), len(pp_ - tp_), len(tp_ - pp_))
    return out
