"""Synthesize the three MVP sources — FIR, CDR, FIN — from the ground-truth world.

Records look like realistic ingestion input (noisy, multilingual, with missing and
conflicting fields). Every entity occurrence is emitted as a :class:`Mention` so the
evaluator knows the *true* entity id for each surface form (paper §21.1).
"""
from __future__ import annotations

import random
from datetime import datetime, time, timedelta

from .config import GenConfig
from .entities import Mention, World
from .pools import IPC_SECTIONS
from .variants import amount_form, full_name, noisy_address


class _Narrative:
    """Builds a narrative string while tracking char spans of entity mentions."""

    def __init__(self) -> None:
        self._buf: list[str] = []
        self._pos = 0
        self.spans: list[tuple[dict, int, int]] = []

    def add(self, text: str) -> None:
        self._buf.append(text)
        self._pos += len(text)

    def add_entity(self, surface: str, meta: dict) -> None:
        start = self._pos
        self.add(surface)
        self.spans.append((meta, start, self._pos))

    def text(self) -> str:
        return "".join(self._buf)


def _rng(cfg: GenConfig, salt: int) -> random.Random:
    return random.Random(cfg.seed + salt)


def _actors(rng: random.Random, world: World, n: int):
    pool = [p for p in world.persons if not p.is_irrelevant] or world.persons
    return rng.sample(pool, min(n, len(pool)))


def _random_dt(rng: random.Random, world: World) -> datetime:
    day = world.start + timedelta(days=rng.randrange(world.cfg.days))
    return datetime.combine(day, time(rng.randrange(24), rng.randrange(60), rng.randrange(60)))


def _maybe(rng: random.Random, cfg: GenConfig, value):
    """Return value, or None with probability ``missing_rate``."""
    return None if rng.random() < cfg.missing_rate else value


def _reported_age(rng: random.Random, cfg: GenConfig, true_age: int) -> int:
    if rng.random() < cfg.conflict_rate:              # conflicting attribute across sources
        return max(18, true_age + rng.choice([-3, -2, -1, 1, 2, 3]))
    return true_age


# --------------------------------------------------------------------------- FIR
def generate_firs(world: World) -> tuple[list[dict], list[Mention]]:
    cfg = world.cfg
    rng = _rng(cfg, 100)
    records, mentions = [], []
    mid = 0

    for i in range(cfg.num_fir):
        rid = f"FIR-2026-{i + 1:04d}"
        dt = _random_dt(rng, world)
        place = rng.choice(world.locations)
        section, crime = rng.choice(IPC_SECTIONS)
        extra_sections = [s for s, _ in rng.sample(IPC_SECTIONS, rng.randint(0, 2))]

        people = _actors(rng, world, rng.randint(2, 3))
        complainant, accused = people[0], people[1:]

        def emit(person, field, form):
            nonlocal mid
            mid += 1
            mentions.append(Mention(f"FIR-m{mid:05d}", "FIR", rid, field, "PERSON",
                                    form, person.id))

        # ---- narrative (multilingual) with NER spans
        lang = rng.choice(cfg.languages)
        comp_form, _ = full_name(rng, complainant, cfg)
        acc_forms = [full_name(rng, a, cfg)[0] for a in accused]
        nar = _Narrative()
        date_s = dt.strftime("%d %b %Y") if lang == "en" else dt.strftime("%d/%m/%Y")
        if lang == "hi":
            nar.add(f"दिनांक {date_s} को शिकायतकर्ता ")
            nar.add_entity(comp_form, {"type": "PERSON", "id": complainant.id})
            nar.add(" ने बताया कि ")
            nar.add_entity(acc_forms[0], {"type": "PERSON", "id": accused[0].id})
            nar.add(" ने ")
            nar.add_entity(place.locality, {"type": "LOCATION", "id": place.id})
            nar.add(f" के पास {crime} किया। ")
        elif lang == "hi-en":
            nar.add(f"Dinank {date_s} ko complainant ")
            nar.add_entity(comp_form, {"type": "PERSON", "id": complainant.id})
            nar.add(" ne report kiya ki ")
            nar.add_entity(acc_forms[0], {"type": "PERSON", "id": accused[0].id})
            nar.add(" aur uske saathi ne ")
            nar.add_entity(place.locality, {"type": "LOCATION", "id": place.id})
            nar.add(f" ke paas {crime.lower()} kiya. ")
        else:
            nar.add(f"On {date_s}, complainant ")
            nar.add_entity(comp_form, {"type": "PERSON", "id": complainant.id})
            nar.add(" reported that ")
            nar.add_entity(acc_forms[0], {"type": "PERSON", "id": accused[0].id})
            nar.add(" along with associates committed ")
            nar.add(f"{crime.lower()} near ")
            nar.add_entity(place.locality, {"type": "LOCATION", "id": place.id})
            nar.add(". ")

        # optional vehicle / phone sentence, with spans
        if accused[0].vehicles and rng.random() < 0.5:
            veh = accused[0].vehicles[0]
            nar.add("Vehicle bearing registration ")
            nar.add_entity(veh.plate, {"type": "VEHICLE", "id": veh.id})
            nar.add(" was seen at the spot. ")
        if rng.random() < 0.4:
            ph = accused[0].phone_active_on(dt.date())
            nar.add("The accused was contacted on ")
            nar.add_entity(ph.number, {"type": "PHONE", "id": ph.id})
            nar.add(". ")
        if accused[0].accounts and rng.random() < 0.35:
            acc = accused[0].accounts[0]
            nar.add("Extortion payments were traced to account ")
            nar.add_entity(acc.number, {"type": "ACCOUNT", "id": acc.id})
            nar.add(". ")

        for meta, start, end in nar.spans:
            mid += 1
            mentions.append(Mention(f"FIR-m{mid:05d}", "FIR", rid, "narrative",
                                    meta["type"], nar.text()[start:end], meta["id"],
                                    span=(start, end)))

        # ---- structured fields (often a *different* noisy form → duplicate mentions)
        comp_struct, _ = full_name(rng, complainant, cfg)
        emit(complainant, "complainant", comp_struct)
        complainant_block = {"name": comp_struct}
        if (age := _maybe(rng, cfg, _reported_age(rng, cfg, complainant.age))) is not None:
            complainant_block["age"] = age
        if (addr := _maybe(rng, cfg, noisy_address(rng, complainant.home, cfg))) is not None:
            complainant_block["address"] = addr

        accused_blocks = []
        for a in accused:
            a_form, _ = full_name(rng, a, cfg)
            emit(a, "accused", a_form)
            block = {"name": a_form}
            if (addr := _maybe(rng, cfg, noisy_address(rng, a.home, cfg))) is not None:
                block["address"] = addr
            accused_blocks.append(block)

        records.append({
            "record_id": rid,
            "source": "FIR",
            "date": dt.date().isoformat(),
            "police_station": f"PS {place.locality}",
            "district": place.district,
            "ipc_sections": sorted({section, *extra_sections}),
            "complainant": complainant_block,
            "accused": accused_blocks,
            "narrative": nar.text(),
            "language": lang,
        })
    return records, mentions


# --------------------------------------------------------------------------- CDR
def generate_cdrs(world: World) -> tuple[list[dict], list[Mention], list[dict]]:
    cfg = world.cfg
    rng = _rng(cfg, 200)
    records, mentions, planted = [], [], []

    # partition non-irrelevant people into groups so communities emerge
    pool = [p for p in world.persons if not p.is_irrelevant] or world.persons
    rng.shuffle(pool)
    group_size = max(2, len(pool) // max(1, len(pool) // 6 or 1))
    groups = [pool[i:i + group_size] for i in range(0, len(pool), group_size)]
    groups = [g for g in groups if len(g) >= 2] or [pool]

    for i in range(cfg.num_cdr):
        rid = f"CDR-{i + 1:06d}"
        if rng.random() < 0.7:                        # intra-group call (builds structure)
            g = rng.choice(groups)
            caller, receiver = rng.sample(g, 2)
        else:                                         # cross-group noise
            caller, receiver = rng.sample(pool, 2)
        dt = _random_dt(rng, world)
        cph = caller.phone_active_on(dt.date())
        rph = receiver.phone_active_on(dt.date())
        tower = rng.choice(world.locations)

        records.append({
            "record_id": rid,
            "source": "CDR",
            "caller": cph.number,
            "receiver": rph.number,
            "timestamp": dt.isoformat(),
            "duration_sec": rng.choice([8, 15, 42, 63, 120, 240, 380, 15, 30]),
            "tower": f"{tower.locality}, {tower.district}",
        })
        for field, ph in (("caller", cph), ("receiver", rph)):
            mentions.append(Mention(f"CDR-m{2 * i + (field == 'receiver') + 1:06d}",
                                    "CDR", rid, field, "PHONE", ph.number, ph.id))

    # ---- planted call bursts: one phone suddenly makes many calls in 48h -------
    # Ground-truth positives for the COMM_BURST detector (paper §14.1).
    burst_actors = rng.sample([p for p in pool if p.phones],
                              min(cfg.num_call_bursts, len(pool)))
    for b, actor in enumerate(burst_actors):
        ph = actor.phone_active_on(world.start + timedelta(days=cfg.days // 2))
        window_start = (datetime.combine(world.start, time.min)
                        + timedelta(days=rng.randrange(max(1, cfg.days - 2)),
                                    hours=rng.randrange(0, 22)))
        rec_ids = []
        for j in range(cfg.burst_call_count):
            other = rng.choice(pool)
            if other is actor:
                continue
            oph = other.phone_active_on(window_start.date())
            dt = window_start + timedelta(minutes=rng.randrange(0, 48 * 60))
            rid = f"CDR-{len(records) + 1:06d}"
            records.append({
                "record_id": rid,
                "source": "CDR",
                "caller": ph.number,
                "receiver": oph.number,
                "timestamp": dt.isoformat(),
                "duration_sec": rng.choice([8, 15, 30, 42, 63]),
                "tower": f"{rng.choice(world.locations).locality}, {rng.choice(world.locations).district}",
            })
            rec_ids.append(rid)
        planted.append({"kind": "COMM_BURST", "phone": ph.number,
                        "record_ids": rec_ids,
                        "window_start": window_start.isoformat()})

    return records, mentions, planted


# --------------------------------------------------------------------------- FIN
def generate_fins(world: World) -> tuple[list[dict], list[Mention], list[dict]]:
    cfg = world.cfg
    rng = _rng(cfg, 300)
    records, mentions, planted = [], [], []

    accounts = [(p, acc) for p in world.persons for acc in p.accounts]
    if len(accounts) < 2:
        return records, mentions

    mid = 0

    def emit_transfer(sender, sacc, receiver, racc, dt):
        nonlocal mid
        rid = f"FIN-{len(records) + 1:06d}"
        value = rng.choice([5000, 12000, 25000, 50000, 75000, 100000, 150000, 250000, 1000000])
        records.append({
            "record_id": rid,
            "source": "FIN",
            "sender_account": sacc.number,
            "sender_bank": sacc.bank,
            "receiver_account": racc.number,
            "receiver_bank": racc.bank,
            "amount_raw": amount_form(rng, value),
            "timestamp": dt.isoformat(),
        })
        for field, acc in (("sender_account", sacc), ("receiver_account", racc)):
            mid += 1
            mentions.append(Mention(f"FIN-m{mid:05d}", "FIN", rid, field, "ACCOUNT",
                                    acc.number, acc.id))
        mid += 1
        mentions.append(Mention(f"FIN-m{mid:05d}", "FIN", rid, "amount", "AMOUNT",
                                records[-1]["amount_raw"], None, normalized=str(value)))

    # a few deliberate circular flows (A→B→C→A) as anomaly seeds
    n_cycles = min(cfg.num_planted_cycles, len(accounts) // 3)
    for _ in range(n_cycles):
        ring = rng.sample(accounts, 3)
        base_dt = _random_dt(rng, world)
        rec_ids = []
        for j in range(3):
            (ps, sa), (pr, ra) = ring[j], ring[(j + 1) % 3]
            rid = f"FIN-{len(records) + 1:06d}"
            rec_ids.append(rid)
            emit_transfer(ps, sa, pr, ra, base_dt + timedelta(hours=j * 3))
        # ground-truth positive for the CIRCULAR_FLOW detector (paper §14.1)
        planted.append({"kind": "CIRCULAR_FLOW",
                        "accounts": [acc.number for _, acc in ring],
                        "record_ids": rec_ids})

    while len(records) < cfg.num_fin:
        (ps, sa), (pr, ra) = rng.sample(accounts, 2)
        emit_transfer(ps, sa, pr, ra, _random_dt(rng, world))

    return records, mentions, planted
