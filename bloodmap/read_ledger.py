"""One ledger for every layer: `(record, field) -> [claims]`.

The shape is the writer's own. `surface.RecordOwner` is a ledger over wall
records and `channels.RegionLedger` is one over region channels; this is the
same idea at the granularity a decompilation needs -- a FIELD of a record --
and it is shared by every layer rather than kept per layer.

Why a field and not a sector
============================

A per-layer residue count answers "how much did this reader cover", which is a
question about the reader. `(record, field)` answers "how much of this map does
anything explain", which is a question about the map, and it is the one the
experiment asks. A sector is understood in proportion to its claimed fields:
a sector whose `floor_z` an island explains and whose `floor_shade` the light
field explains and whose twenty other fields nothing explains is 10%
understood, and no amount of layering hides that.

A claim says: **this layer's model determines this field's value, and
replaying the model reproduces it.** Anything weaker is not a claim. A reader
that names a sector without reproducing a field of it claims nothing here,
and that is deliberate -- the space tree claims no field at all, which is the
truest thing that can be said about a geometric hierarchy.

Channels, and what a conflict is
================================

Every field belongs to a channel. Where the writer already names one
(`channels.CHANNELS`) that name is used unchanged; the rest carry reader-side
names, which are NOT proposed as rows in the writer's table and are marked so.
The two kinds behave as `channels.py` says:

* **additive** -- claims accumulate, and several layers claiming one field is
  the normal case (the sun and a lamp both write a shade);
* **exclusive** -- two claims with DIFFERENT values is a conflict, reported by
  name with both layers and both values. Two layers agreeing on a value is
  corroboration, not a conflict, and is counted as such.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable

from .arbiter import FUNCTION, PRESENTATION
from .channels import ADDITIVE, CHANNELS, EXCLUSIVE
from .format import (
    SECTOR_FIELDS, SPRITE_FIELDS, WALL_FIELDS, XSECTOR_SCHEMA, XSPRITE_SCHEMA,
    XWALL_SCHEMA,
)

SECTOR, WALL, SPRITE = "sector", "wall", "sprite"
XSECTOR, XWALL, XSPRITE = "xsector", "xwall", "xsprite"

#: Fields the FORMAT determines, not the level. A pointer into the wall array
#: is not something a design layer could explain, and leaving them in the
#: denominator would put a floor under every score that means nothing.
STRUCTURAL: dict[str, frozenset[str]] = {
    SECTOR: frozenset({"wall_ptr", "wall_count", "filler", "extra"}),
    WALL: frozenset({"point2", "next_wall", "extra"}),
    SPRITE: frozenset({"owner", "index", "extra"}),
    XSECTOR: frozenset({"reference"}),
    XWALL: frozenset({"reference"}),
    XSPRITE: frozenset({"reference"}),
}

#: `field -> channel`. Where `channels.CHANNELS` already has the name it is
#: used unchanged; the rest are reader-side and listed in `READER_CHANNELS`.
READER_CHANNELS: dict[str, str] = {
    "outline": EXCLUSIVE,          # a vertex: one position
    "topology": EXCLUSIVE,         # which sector is on the other side
    "surface_material": EXCLUSIVE,  # a floor or ceiling's tile, palette, phase
    "visibility": EXCLUSIVE,
    "placement": EXCLUSIVE,        # where a sprite stands
    "sprite_appearance": EXCLUSIVE,
    "tag": EXCLUSIVE,              # hitag and the other loose bytes
}

_SECTOR_CHANNEL = {
    "floor_z": "floor_z", "ceiling_z": "ceiling_z",
    "floor_shade": "shade", "ceiling_shade": "shade",
    "type": "sector_type", "hitag": "tag", "visibility": "visibility",
}
_WALL_CHANNEL = {
    "x": "outline", "y": "outline", "next_sector": "topology",
    "shade": "shade", "type": "mechanism_state", "hitag": "tag",
}
_SPRITE_CHANNEL = {
    "x": "placement", "y": "placement", "z": "placement",
    "sector": "placement", "angle": "placement", "status": "placement",
    "shade": "shade", "type": "mechanism_state",
    "initial_type": "mechanism_state", "hitag": "tag", "flags": "tag",
}


def channel_of(kind: str, name: str) -> str:
    """Which channel this field belongs to."""
    if kind in (XSECTOR, XWALL, XSPRITE):
        return "mechanism_state"
    if kind == SECTOR:
        return _SECTOR_CHANNEL.get(name, "surface_material")
    if kind == WALL:
        return _WALL_CHANNEL.get(name, "frame")
    return _SPRITE_CHANNEL.get(name, "sprite_appearance")


def channel_kind(channel: str) -> str:
    if channel in CHANNELS:
        return CHANNELS[channel]
    if channel in READER_CHANNELS:
        return READER_CHANNELS[channel]
    raise KeyError(f"{channel!r} is not a channel this ledger knows")


def fields_of(kind: str) -> tuple[str, ...]:
    schema = {
        SECTOR: [name for name, _ in SECTOR_FIELDS],
        WALL: [name for name, _ in WALL_FIELDS],
        SPRITE: [name for name, _ in SPRITE_FIELDS],
        XSECTOR: [name for name, _, _ in XSECTOR_SCHEMA],
        XWALL: [name for name, _, _ in XWALL_SCHEMA],
        XSPRITE: [name for name, _, _ in XSPRITE_SCHEMA],
    }[kind]
    return tuple(name for name in schema if name not in STRUCTURAL[kind])


@dataclass(frozen=True)
class Claim:
    """One layer saying it determines one field of one record."""

    layer: int
    owner: str
    value: Any
    why: str
    intent: str = FUNCTION

    def to_dict(self) -> dict[str, Any]:
        return {"layer": self.layer, "owner": self.owner,
                "value": self.value, "why": self.why, "intent": self.intent}


@dataclass
class ClaimLedger:
    """`(kind, index, field) -> [Claim]`, shared by every layer."""

    claims: dict[tuple[str, int, str], list[Claim]] = field(default_factory=dict)
    #: The population: how many records of each kind the map has.
    counts: dict[str, int] = field(default_factory=dict)

    def population(self, level: Any) -> None:
        self.counts = {
            SECTOR: len(level.sectors), WALL: len(level.walls),
            SPRITE: len(level.sprites),
            XSECTOR: sum(1 for item in level.sectors if item.get("blood")),
            XWALL: sum(1 for item in level.walls if item.get("blood")),
            XSPRITE: sum(1 for item in level.sprites if item.get("blood")),
        }

    def claim(self, kind: str, index: int, name: str, *, layer: int,
              owner: str, value: Any, why: str, intent: str = FUNCTION) -> None:
        if name not in fields_of(kind):
            raise KeyError(
                f"{kind}.{name} is not a claimable field: it is either "
                f"structural (the format owns it) or not a field at all")
        key = (kind, int(index), name)
        self.claims.setdefault(key, []).append(
            Claim(int(layer), str(owner), value, str(why), str(intent)))

    def claim_many(self, kind: str, indexes: Iterable[int], names: Iterable[str],
                   *, values: Any, layer: int, owner: str, why: str,
                   intent: str = FUNCTION) -> int:
        count = 0
        names = tuple(names)
        for index in indexes:
            for name in names:
                self.claim(kind, index, name, layer=layer, owner=owner,
                           value=values(index, name) if callable(values) else values,
                           why=why, intent=intent)
                count += 1
        return count

    # --- reading it back --------------------------------------------------

    def claimable(self) -> int:
        return sum(self.counts.get(kind, 0) * len(fields_of(kind))
                   for kind in (SECTOR, WALL, SPRITE, XSECTOR, XWALL, XSPRITE))

    def conflicts(self) -> list[dict[str, Any]]:
        """Two layers claiming one EXCLUSIVE field with different values."""
        out = []
        for (kind, index, name), claims in sorted(self.claims.items()):
            if channel_kind(channel_of(kind, name)) != EXCLUSIVE:
                continue
            values = {repr(claim.value) for claim in claims}
            if len(claims) > 1 and len(values) > 1:
                out.append({
                    "record": f"{kind}:{index}", "field": name,
                    "channel": channel_of(kind, name),
                    "claims": [claim.to_dict() for claim in claims]})
        return out

    def corroborations(self) -> int:
        """Exclusive fields two layers claim and agree on."""
        total = 0
        for (kind, index, name), claims in self.claims.items():
            if channel_kind(channel_of(kind, name)) != EXCLUSIVE:
                continue
            if len(claims) > 1 and len({repr(c.value) for c in claims}) == 1:
                total += 1
        return total

    def by_layer(self) -> dict[int, dict[str, Any]]:
        fields: Counter = Counter()
        records: dict[int, set] = defaultdict(set)
        channels: dict[int, Counter] = defaultdict(Counter)
        for (kind, index, name), claims in self.claims.items():
            for claim in claims:
                fields[claim.layer] += 1
                records[claim.layer].add((kind, index))
                channels[claim.layer][channel_of(kind, name)] += 1
        total = self.claimable() or 1
        return {layer: {"fields_claimed": count,
                        "records_touched": len(records[layer]),
                        "share_of_all_fields": round(100.0 * count / total, 3),
                        "by_channel": dict(sorted(channels[layer].items()))}
                for layer, count in sorted(fields.items())}

    def understanding(self) -> dict[str, Any]:
        claimable = self.claimable()
        claimed = len(self.claims)
        return {
            "claimable_fields": claimable,
            "fields_with_a_claim": claimed,
            "understood_percent": round(100.0 * claimed / claimable, 3) if claimable else 0.0,
            "residue_fields": claimable - claimed,
            "structural_fields_excluded": {
                kind: len(STRUCTURAL[kind]) * self.counts.get(kind, 0)
                for kind in sorted(STRUCTURAL)},
        }

    def per_record(self, kind: str) -> dict[int, dict[str, Any]]:
        """How much of each record of one kind is claimed."""
        names = fields_of(kind)
        out: dict[int, dict[str, Any]] = {}
        for index in range(self.counts.get(kind, 0)):
            held = [name for name in names if (kind, index, name) in self.claims]
            out[index] = {
                "claimed": held,
                "unclaimed": [name for name in names if name not in held],
                "percent": round(100.0 * len(held) / len(names), 1) if names else 0.0,
            }
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "$schema": "llmapper.claim-ledger",
            "schema_version": 1,
            "format": "(record, field) -> [claims], the RecordOwner / "
                      "RegionLedger shape at field granularity",
            "counts": dict(self.counts),
            "claimable_fields_per_record": {
                kind: len(fields_of(kind)) for kind in sorted(STRUCTURAL)},
            "structural_fields_excluded": {
                kind: sorted(STRUCTURAL[kind]) for kind in sorted(STRUCTURAL)},
            "channels": {"writer": dict(sorted(CHANNELS.items())),
                         "reader_side": dict(sorted(READER_CHANNELS.items()))},
            "understanding": self.understanding(),
            "by_layer": self.by_layer(),
            "conflicts": self.conflicts(),
            "corroborated_exclusive_fields": self.corroborations(),
            "claims": {f"{kind}:{index}:{name}": [c.to_dict() for c in claims]
                       for (kind, index, name), claims in sorted(self.claims.items())},
        }
