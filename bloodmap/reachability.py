"""Where the player can actually get to, and what the rest of the map is for.

Every Blood campaign map contains geometry the player never reaches, and
treating it as level design corrupts everything downstream: a shape corpus that
counts letterforms, an area proposal that groups a switch closet with the room
it wires, a level program that emits an author's signature as nine rooms.

Three separate things live off the playable map, and they are not noise -- they
are different kinds of information:

``logic_closet``
    One sector packed with switches and generators, wired to the level by
    channel rather than by geometry.  E1M6 has a single sector holding 67
    switches and 7 generators.  This is the level's control panel, and reading
    it as a room is wrong; reading it as the trigger wiring is right.

``signature``
    The author's handle, drawn as letter-shaped sectors.  Fifteen of the 43
    campaign maps carry the same nine-glyph stamp, twice in E2M2 and E4M3, plus
    BB3 and BB5.  It is a signature, not architecture.

``helper``
    Sectors that exist to be a link or a warp destination.

Getting reachability itself right needs three facts from NBlood, each of which
is easy to get wrong:

1. The single-player spawn is a ``kMarkerSPStart`` sprite whose
   ``XSPRITE.data1`` is 0, and only that one; the marker overrides
   ``gStartZone[data1]`` and is then deleted (``warp.cpp`` ``warpInit``).  The
   map header's start is the fallback (``blood.cpp:724``).  All 43 campaign maps
   have the marker, and picking any other ``kMarkerSPStart`` puts the camera in
   a closet: on E4M3 the first one by index is in a 7-sector pocket while the
   playable region is 364 sectors.
2. Sectors are joined by upper/lower link markers as well as by walls.  A marker
   in the up family (``kMarkerUpLink``/``UpWater``/``UpStack``/``UpGoo``) pairs
   with the low-family marker whose ``XSPRITE.data1`` matches
   (``warp.cpp`` ``warpInit``).
3. A ``kSectorTeleport`` sector reaches the sector of the ``kMarkerWarpDest``
   sprite its ``XSECTOR.marker0`` names (``triggers.cpp`` ``OperateTeleport``).

Crossing walls alone leaves a median 8.5% of each campaign map unreachable.
Crossing links and teleports too leaves 2.8%, and that remainder is the three
kinds above.
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .model import DiskMap

SCHEMA = "llmapper.reachability"
SCHEMA_VERSION = 1

#: ``common_game.h``.  A sector holds at most one of each family.
UP_MARKERS = {6: "kMarkerLowLink", 9: "kMarkerUpWater", 11: "kMarkerUpStack", 13: "kMarkerUpGoo"}
LOW_MARKERS = {7: "kMarkerUpLink", 10: "kMarkerLowWater", 12: "kMarkerLowStack", 14: "kMarkerLowGoo"}
#: ``warpInit`` files 6/9/11/13 under gUpperLink and 7/10/12/14 under gLowerLink,
#: which is why the two constant names read backwards against the arrays.
UP_FAMILY = frozenset(UP_MARKERS)
LOW_FAMILY = frozenset(LOW_MARKERS)

SP_START = 1
MP_START = 2
WARP_DEST = 8
SWITCH_TYPES = frozenset({20, 21, 22, 23})
GENERATOR_TYPES = frozenset({700, 701, 702, 703, 704, 705, 706, 707, 708, 709, 711})
SECTOR_TELEPORT = 604

#: Enough switches in one unreachable sector that it is a control panel rather
#: than a room someone forgot to connect.  The campaign's closets hold 14 to 67;
#: nothing reachable comes close.
CLOSET_SWITCH_FLOOR = 3


class ReachabilityError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

def wall_owners(disk: DiskMap) -> dict[int, int]:
    owners: dict[int, int] = {}
    for index, sector in enumerate(disk.sectors):
        first = int(sector.fields["wall_ptr"])
        count = int(sector.fields["wall_count"])
        for wall in range(first, first + count):
            owners[wall] = index
    return owners


def portal_graph(disk: DiskMap) -> dict[int, set[int]]:
    """Sector adjacency through two-sided walls, gating ignored.

    A closed door is still a portal: gating is about *when* a player gets
    through, not whether the geometry is part of the level.
    """
    owners = wall_owners(disk)
    graph: dict[int, set[int]] = defaultdict(set)
    for index, wall in enumerate(disk.walls):
        other = int(wall.fields["next_sector"])
        if other < 0 or index not in owners:
            continue
        graph[owners[index]].add(other)
        graph[other].add(owners[index])
    return graph


def link_pairs(disk: DiskMap) -> list[dict[str, Any]]:
    """Stack, water and goo links, paired the way ``warpInit`` pairs them."""
    up: dict[int, list[tuple[int, int]]] = defaultdict(list)
    low: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for index, sprite in enumerate(disk.sprites):
        if sprite.extra is None:
            continue
        kind = int(sprite.fields["type"])
        key = sprite.extra.fields.get("data_1")
        if key is None:
            continue
        record = (int(sprite.fields["sector"]), index)
        if kind in UP_FAMILY:
            up[int(key)].append(record)
        elif kind in LOW_FAMILY:
            low[int(key)].append(record)
    pairs: list[dict[str, Any]] = []
    for key in sorted(set(up) & set(low)):
        for upper_sector, upper_sprite in up[key]:
            for lower_sector, lower_sprite in low[key]:
                pairs.append({
                    "link_id": key,
                    "sectors": [upper_sector, lower_sector],
                    "sprites": [upper_sprite, lower_sprite],
                })
    return pairs


def teleport_pairs(disk: DiskMap) -> list[dict[str, Any]]:
    """``kSectorTeleport`` to the sector its ``marker0`` destination sits in."""
    pairs: list[dict[str, Any]] = []
    for index, sector in enumerate(disk.sectors):
        if int(sector.fields["type"]) != SECTOR_TELEPORT or sector.extra is None:
            continue
        marker = sector.extra.fields.get("marker_0")
        if marker is None or not 0 <= int(marker) < len(disk.sprites):
            continue
        destination = disk.sprites[int(marker)]
        pairs.append({
            "sectors": [index, int(destination.fields["sector"])],
            "marker_sprite": int(marker),
            "marker_is_warp_dest": int(destination.fields["type"]) == WARP_DEST,
        })
    return pairs


# ---------------------------------------------------------------------------
# The spawn
# ---------------------------------------------------------------------------

def player_start(disk: DiskMap) -> dict[str, Any]:
    """The sector single-player actually spawns in.

    ``warpInit`` overrides ``gStartZone[data1]`` from a ``kMarkerSPStart``, so
    only the marker carrying ``data1 == 0`` is the player-one spawn.  Any other
    ``kMarkerSPStart`` is a spawn for a coop slot and may sit anywhere.
    """
    for index, sprite in enumerate(disk.sprites):
        if int(sprite.fields["type"]) != SP_START or sprite.extra is None:
            continue
        if int(sprite.extra.fields.get("data_1") or 0) != 0:
            continue
        return {
            "sector": int(sprite.fields["sector"]),
            "source": "kMarkerSPStart with data1 == 0",
            "sprite": index,
            "provenance": "NBlood source/blood/src/warp.cpp warpInit",
        }
    return {
        "sector": int(disk.header["start_sector"]),
        "source": "map header",
        "sprite": None,
        "provenance": "NBlood source/blood/src/blood.cpp:724 gStartZone from startsectnum",
    }


# ---------------------------------------------------------------------------
# Reachability
# ---------------------------------------------------------------------------

@dataclass
class Reachability:
    start: dict[str, Any]
    reached: frozenset[int]
    offmap: frozenset[int]
    graph: dict[int, set[int]]
    links: list[dict[str, Any]]
    teleports: list[dict[str, Any]]
    sector_count: int

    @property
    def offmap_fraction(self) -> float:
        return len(self.offmap) / max(1, self.sector_count)

    def to_dict(self) -> dict[str, Any]:
        return {
            "$schema": SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "start": dict(self.start),
            "sector_count": self.sector_count,
            "reached": len(self.reached),
            "offmap": sorted(self.offmap),
            "offmap_fraction": round(self.offmap_fraction, 4),
            "links": len(self.links),
            "teleports": len(self.teleports),
            "crossings": ["portal", "link", "teleport"],
            "limitations": [
                "gating is ignored: a closed door is still a portal, because this "
                "answers whether geometry is part of the level, not when it opens",
                "a sector reachable only by a jump, a lift ride or a broken wall is "
                "counted through its portal, never by simulating the player",
            ],
        }


def analyze_reachability(disk: DiskMap) -> Reachability:
    graph = portal_graph(disk)
    links = link_pairs(disk)
    teleports = teleport_pairs(disk)
    joined: dict[int, set[int]] = defaultdict(set)
    for key, value in graph.items():
        joined[key] |= value
    for group in (links, teleports):
        for record in group:
            left, right = record["sectors"]
            joined[left].add(right)
            joined[right].add(left)

    start = player_start(disk)
    origin = start["sector"]
    if not 0 <= origin < len(disk.sectors):
        raise ReachabilityError(f"the player start names sector {origin}, which does not exist")
    seen = {origin}
    pending = deque([origin])
    while pending:
        current = pending.popleft()
        for neighbour in joined[current]:
            if neighbour not in seen:
                seen.add(neighbour)
                pending.append(neighbour)
    everything = set(range(len(disk.sectors)))
    return Reachability(
        start=start, reached=frozenset(seen), offmap=frozenset(everything - seen),
        graph=joined, links=links, teleports=teleports, sector_count=len(disk.sectors),
    )


# ---------------------------------------------------------------------------
# What the off-map geometry is
# ---------------------------------------------------------------------------

def _sector_outline(disk: DiskMap, sector_id: int) -> list[tuple[int, int]]:
    fields = disk.sectors[sector_id].fields
    first, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    return [(int(disk.walls[w].fields["x"]), int(disk.walls[w].fields["y"]))
            for w in range(first, min(first + count, len(disk.walls)))]


def glyph_shape(disk: DiskMap, sector_id: int) -> tuple[tuple[int, int], ...]:
    """A sector outline as offsets from its own corner: the same letter twice
    in two different maps hashes the same."""
    points = _sector_outline(disk, sector_id)
    if not points:
        return ()
    min_x = min(p[0] for p in points)
    min_y = min(p[1] for p in points)
    return tuple(sorted((p[0] - min_x, p[1] - min_y) for p in points))


@dataclass(frozen=True)
class OffmapComponent:
    sectors: tuple[int, ...]
    kind: str
    reasons: tuple[str, ...]
    switches: int = 0
    generators: int = 0
    sprites: int = 0
    with_xsector: int = 0
    markers: int = 0
    player_areas: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "sectors": list(self.sectors),
            "kind": self.kind,
            "reasons": list(self.reasons),
            "switches": self.switches,
            "generators": self.generators,
            "sprites": self.sprites,
            "sectors_with_xsector": self.with_xsector,
            "link_or_warp_markers": self.markers,
            "player_areas": round(self.player_areas, 2),
        }


def _components(sectors: Iterable[int], graph: Mapping[int, set[int]]) -> list[list[int]]:
    left = set(sectors)
    result: list[list[int]] = []
    while left:
        seed = min(left)
        left.discard(seed)
        group = [seed]
        pending = deque([seed])
        while pending:
            current = pending.popleft()
            for neighbour in graph.get(current, ()):
                if neighbour in left:
                    left.discard(neighbour)
                    group.append(neighbour)
                    pending.append(neighbour)
        result.append(sorted(group))
    return result


def _area(points: Sequence[tuple[int, int]]) -> float:
    total = 0.0
    for index, (x1, y1) in enumerate(points):
        x2, y2 = points[(index + 1) % len(points)]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


def classify_offmap(disk: DiskMap, reach: Reachability | None = None, *,
                    glyphs: Iterable[tuple[tuple[int, int], ...]] | None = None,
                    unit: int = 384) -> dict[str, Any]:
    """Sort the off-map geometry into the kinds it actually comes in."""
    reach = reach or analyze_reachability(disk)
    known_glyphs = set(glyphs) if glyphs is not None else set(SIGNATURE_GLYPHS)

    by_sector: dict[int, list[int]] = defaultdict(list)
    for sprite in disk.sprites:
        by_sector[int(sprite.fields["sector"])].append(int(sprite.fields["type"]))

    components: list[OffmapComponent] = []
    for group in _components(reach.offmap, reach.graph):
        types = [t for s in group for t in by_sector.get(s, ())]
        switches = sum(1 for t in types if t in SWITCH_TYPES)
        generators = sum(1 for t in types if t in GENERATOR_TYPES)
        markers = sum(1 for t in types if t in UP_FAMILY or t in LOW_FAMILY or t == WARP_DEST)
        with_xsector = sum(1 for s in group if disk.sectors[s].extra is not None)
        area = sum(_area(_sector_outline(disk, s)) for s in group) / (unit * unit)
        glyph_hits = sum(1 for s in group if glyph_shape(disk, s) in known_glyphs)

        reasons: list[str] = []
        if glyph_hits:
            kind = "signature"
            reasons.append(f"{glyph_hits} of {len(group)} outlines match a known glyph stamp")
        elif switches + generators >= CLOSET_SWITCH_FLOOR:
            kind = "logic_closet"
            reasons.append(f"{switches} switches and {generators} generators, unreachable")
        elif markers:
            kind = "helper"
            reasons.append(f"{markers} link or warp markers")
        elif not types and with_xsector == 0:
            kind = "bare"
            reasons.append("no sprite, no XSECTOR: geometry with nothing wired to it")
        else:
            kind = "sealed"
            reasons.append(f"{len(types)} sprites, {with_xsector} sectors with an XSECTOR")
        components.append(OffmapComponent(
            sectors=tuple(group), kind=kind, reasons=tuple(reasons),
            switches=switches, generators=generators, sprites=len(types),
            with_xsector=with_xsector, markers=markers, player_areas=area,
        ))

    counts: dict[str, int] = defaultdict(int)
    sectors_by_kind: dict[str, int] = defaultdict(int)
    for item in components:
        counts[item.kind] += 1
        sectors_by_kind[item.kind] += len(item.sectors)
    return {
        "$schema": "llmapper.offmap-classification",
        "schema_version": 1,
        "reachability": reach.to_dict(),
        "components": [item.to_dict() for item in components],
        "counts": dict(sorted(counts.items())),
        "sectors_by_kind": dict(sorted(sectors_by_kind.items())),
        "limitations": [
            "a signature is recognised by matching a glyph stamp seen elsewhere in "
            "the corpus, so an unseen author's handle falls into bare",
            "bare is deliberately not a verdict: it holds letterforms this has not "
            "seen before, scenery, and sectors nobody ever finished",
        ],
    }


def design_sectors(disk: DiskMap, *, keep: Sequence[str] = ()) -> frozenset[int]:
    """The sectors a statistic about level design should be computed over.

    Everything the player can reach, plus any off-map kind explicitly kept.
    A signature and a switch closet are not architecture, and counting them
    makes a shape corpus measure the wrong thing.
    """
    reach = analyze_reachability(disk)
    result = set(reach.reached)
    if keep:
        report = classify_offmap(disk, reach)
        keep_kinds = set(keep)
        for component in report["components"]:
            if component["kind"] in keep_kinds:
                result.update(component["sectors"])
    return frozenset(result)


def learn_signature_glyphs(disk: DiskMap, sectors: Iterable[int]) -> tuple[tuple[tuple[int, int], ...], ...]:
    """Collect glyph outlines from a map known to carry a signature."""
    return tuple(sorted({glyph_shape(disk, s) for s in sectors}))


def _load_signature_glyphs() -> tuple[tuple[tuple[int, int], ...], ...]:
    """Outlines of the stamp an author signed fifteen campaign maps with.

    Data, not a rule.  A map without them is not penalised, and a handle this
    has never seen falls through to ``bare`` rather than being guessed at.
    """
    path = Path(__file__).resolve().parent.parent / "knowledge" / "blood" / "offmap-signature-glyphs.json"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()
    return tuple(tuple(tuple(int(v) for v in point) for point in glyph)
                 for glyph in document.get("glyphs", []))


SIGNATURE_GLYPHS: tuple[tuple[tuple[int, int], ...], ...] = _load_signature_glyphs()


__all__ = [
    "SCHEMA", "SCHEMA_VERSION", "ReachabilityError", "Reachability", "OffmapComponent",
    "UP_FAMILY", "LOW_FAMILY", "SWITCH_TYPES", "GENERATOR_TYPES",
    "wall_owners", "portal_graph", "link_pairs", "teleport_pairs", "player_start",
    "analyze_reachability", "classify_offmap", "design_sectors",
    "glyph_shape", "learn_signature_glyphs", "SIGNATURE_GLYPHS",
]
