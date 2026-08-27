"""Orchestrate world + record synthesis and write the benchmark to disk.

Outputs (all under ``out_dir``):
  fir.jsonl / cdr.jsonl / fin.jsonl   the noisy input records (what a pipeline ingests)
  mentions.jsonl                       one row per entity occurrence, with its TRUE id
  ground_truth.json                    entities, mention clusters, false-match pairs, evolving ids
  manifest.json                        seed, config, counts, and a SHA-256 per file (tamper-evident)
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from .config import GenConfig
from .entities import Mention, World, build_world
from .records import generate_cdrs, generate_firs, generate_fins


def _mention_dict(m: Mention) -> dict:
    d = asdict(m)
    if d["span"] is not None:
        d["span"] = list(d["span"])
    return d


def _build_entities(world: World) -> dict:
    ents: dict[str, dict] = {}
    for loc in world.locations:
        ents[loc.id] = {"type": "LOCATION", "locality": loc.locality,
                        "district": loc.district, "state": loc.state}
    for p in world.persons:
        ents[p.id] = {
            "type": "PERSON",
            "canonical_name": p.canonical_name,
            "gender": p.gender,
            "age": p.age,
            "home": p.home.id,
            "phones": [ph.id for ph in p.phones],
            "accounts": [ac.id for ac in p.accounts],
            "vehicles": [v.id for v in p.vehicles],
            "is_irrelevant": p.is_irrelevant,
        }
        for ph in p.phones:
            ents[ph.id] = {"type": "PHONE", "number": ph.number, "owner": p.id,
                           "active_from": ph.active_from.isoformat(),
                           "active_to": ph.active_to.isoformat() if ph.active_to else None}
        for ac in p.accounts:
            ents[ac.id] = {"type": "ACCOUNT", "number": ac.number, "bank": ac.bank, "owner": p.id}
        for v in p.vehicles:
            ents[v.id] = {"type": "VEHICLE", "plate": v.plate, "owner": p.id}
    return ents


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(cfg: GenConfig, out_dir: str | Path) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    world = build_world(cfg)
    fir, fir_m = generate_firs(world)
    cdr, cdr_m, cdr_planted = generate_cdrs(world)
    fin, fin_m, fin_planted = generate_fins(world)
    mentions = fir_m + cdr_m + fin_m

    # clusters: true_id -> [mention_id]  (the entity-resolution ground truth)
    clusters: dict[str, list[str]] = defaultdict(list)
    for m in mentions:
        if m.true_id is not None:
            clusters[m.true_id].append(m.mention_id)

    entities = _build_entities(world)
    ground_truth = {
        "entities": entities,
        "clusters": {k: clusters[k] for k in sorted(clusters)},
        "false_match_pairs": [list(pair) for pair in world.false_pairs],
        "evolving_identifiers": {
            p.id: [ph.number for ph in p.phones]
            for p in world.persons if len(p.phones) > 1
        },
        # planted anomaly positives — lets detectors be scored for precision/recall (§21)
        "planted_anomalies": cdr_planted + fin_planted,
    }

    # write record + mention files
    _write_jsonl(out / "fir.jsonl", fir)
    _write_jsonl(out / "cdr.jsonl", cdr)
    _write_jsonl(out / "fin.jsonl", fin)
    _write_jsonl(out / "mentions.jsonl", [_mention_dict(m) for m in mentions])
    with (out / "ground_truth.json").open("w", encoding="utf-8") as f:
        json.dump(ground_truth, f, ensure_ascii=False, indent=2, sort_keys=True)

    # entity-type tally for the summary
    by_type: dict[str, int] = defaultdict(int)
    for e in entities.values():
        by_type[e["type"]] += 1

    manifest = {
        "seed": cfg.seed,
        "config": cfg.to_dict(),
        "counts": {
            "records": {"FIR": len(fir), "CDR": len(cdr), "FIN": len(fin)},
            "mentions": len(mentions),
            "entities_total": len(entities),
            "entities_by_type": dict(sorted(by_type.items())),
            "clusters": len(clusters),
            "false_match_pairs": len(world.false_pairs),
            "evolving_identifier_people": len(ground_truth["evolving_identifiers"]),
        },
        "files": {name: _sha256(out / name) for name in
                  ("fir.jsonl", "cdr.jsonl", "fin.jsonl", "mentions.jsonl", "ground_truth.json")},
    }
    with (out / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, sort_keys=True)

    return manifest
