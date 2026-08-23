"""The synthetic "world": ground-truth entities and their relationships.

``build_world`` deterministically constructs People (with Phones, Accounts,
Vehicles, home Location) plus the deliberate traps the proposal calls for:
duplicate mentions (handled at record time), evolving phone numbers, and
false-match pairs — two DIFFERENT people who share an identical name.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta

from .config import GenConfig
from .pools import (
    BANKS,
    FEMALE_FIRST_NAMES,
    MALE_FIRST_NAMES,
    PLACES,
    RTO_SERIES,
    SURNAMES,
    NameEntry,
)


@dataclass
class Location:
    id: str
    locality: str
    district: str
    state: str


@dataclass
class Phone:
    id: str
    number: str
    active_from: date
    active_to: date | None  # None == still active at horizon end


@dataclass
class Account:
    id: str
    number: str
    bank: str


@dataclass
class Vehicle:
    id: str
    plate: str


@dataclass
class Person:
    id: str
    first: NameEntry
    surname: NameEntry
    gender: str
    age: int
    home: Location
    phones: list[Phone]
    accounts: list[Account]
    vehicles: list[Vehicle]
    is_irrelevant: bool = False

    @property
    def canonical_name(self) -> str:
        return f"{self.first.canonical} {self.surname.canonical}"

    def phone_active_on(self, day: date) -> Phone:
        for ph in self.phones:
            if ph.active_from <= day and (ph.active_to is None or day < ph.active_to):
                return ph
        return self.phones[0]


@dataclass
class Mention:
    """One occurrence of an entity inside a record — the unit of ground truth."""
    mention_id: str
    source: str        # FIR | CDR | FIN
    record_id: str
    field: str
    entity_type: str   # PERSON | PHONE | ACCOUNT | VEHICLE | LOCATION | AMOUNT
    surface: str
    true_id: str | None
    span: tuple[int, int] | None = None
    normalized: str | None = None


@dataclass
class World:
    cfg: GenConfig
    persons: list[Person]
    locations: list[Location]
    false_pairs: list[tuple[str, str]] = field(default_factory=list)

    @property
    def start(self) -> date:
        return date.fromisoformat(self.cfg.start_date)

    @property
    def end(self) -> date:
        return self.start + timedelta(days=self.cfg.days)


def _unique_phone(rng: random.Random, used: set[str]) -> str:
    while True:
        num = "+91" + rng.choice("6789") + "".join(rng.choice("0123456789") for _ in range(9))
        if num not in used:
            used.add(num)
            return num


def _plate(rng: random.Random, state: str) -> str:
    series = rng.choice(RTO_SERIES.get(state, [s for v in RTO_SERIES.values() for s in v]))
    letters = "".join(rng.choice("ABCDEFGHJKLMNPRSTUVWXYZ") for _ in range(2))
    return f"{series} {letters} {rng.randint(1000, 9999)}"


def _make_person(rng, pid, home, used_phones, cfg, *, first=None, surname=None):
    gender = rng.choice(["M", "M", "M", "F"])  # skew keeps women-safety cases meaningful but present
    first = first or rng.choice(MALE_FIRST_NAMES if gender == "M" else FEMALE_FIRST_NAMES)
    surname = surname or rng.choice(SURNAMES)
    age = rng.randint(19, 62)

    start = date.fromisoformat(cfg.start_date)
    horizon = start + timedelta(days=cfg.days)
    phones = [Phone(id=f"{pid}-PH1", number=_unique_phone(rng, used_phones),
                    active_from=start, active_to=None)]
    if rng.random() < cfg.evolving_phone_rate:  # evolving identifier
        switch = start + timedelta(days=rng.randint(20, max(21, cfg.days - 10)))
        phones[0].active_to = switch
        phones.append(Phone(id=f"{pid}-PH2", number=_unique_phone(rng, used_phones),
                             active_from=switch, active_to=None))

    accounts = [Account(id=f"{pid}-AC{i + 1}",
                        number="AC" + "".join(rng.choice("0123456789") for _ in range(10)),
                        bank=rng.choice(BANKS))
                for i in range(rng.randint(0, 2))]
    vehicles = [Vehicle(id=f"{pid}-V1", plate=_plate(rng, home.state))] if rng.random() < 0.55 else []

    return Person(id=pid, first=first, surname=surname, gender=gender, age=age,
                  home=home, phones=phones, accounts=accounts, vehicles=vehicles)


def build_world(cfg: GenConfig) -> World:
    rng = random.Random(cfg.seed)
    locations = [Location(id=f"L{i + 1:04d}", locality=lc, district=d, state=s)
                 for i, (lc, d, s) in enumerate(PLACES)]

    persons: list[Person] = []
    used_phones: set[str] = set()
    for i in range(cfg.num_persons):
        home = rng.choice(locations)
        persons.append(_make_person(rng, f"P{i + 1:04d}", home, used_phones, cfg))

    # mark a subset as "irrelevant" (they will appear once, disconnected)
    n_irrelevant = int(cfg.num_persons * cfg.irrelevant_person_ratio)
    for p in rng.sample(persons, min(n_irrelevant, len(persons))):
        p.is_irrelevant = True

    # false-match traps: a twin with an IDENTICAL name but different id/home/attrs
    false_pairs: list[tuple[str, str]] = []
    base_pool = [p for p in persons if not p.is_irrelevant] or persons
    for k in range(cfg.num_false_pairs):
        base = rng.choice(base_pool)
        other_home = rng.choice([lo for lo in locations if lo.district != base.home.district] or locations)
        twin = _make_person(rng, f"P{cfg.num_persons + k + 1:04d}", other_home, used_phones, cfg,
                             first=base.first, surname=base.surname)
        twin.age = max(19, base.age + rng.choice([-9, -7, 8, 11]))  # different real person
        persons.append(twin)
        false_pairs.append((base.id, twin.id))

    return World(cfg=cfg, persons=persons, locations=locations, false_pairs=false_pairs)
