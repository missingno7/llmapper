"""Semantic inventory for classic Duke3D mechanisms.

This module deliberately describes runtime intent rather than exposing raw
lotags to a conversion profile.  The mappings are grounded in EDuke32's
``game.h``, ``actors.cpp``, and ``sector.cpp``.  It is small on purpose: a
mechanism is only promoted here once its controller topology is understood.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .duke import DukeDiskMap


CRACK_TILES = frozenset({546, 547, 548, 549})
GPSPEED_TILE = 10

# EDuke32 source/duke3d/src/game.h.  Values absent from this table are kept as
# explicit unknowns: an integer tag alone is not conversion evidence.
EFFECTOR_SEMANTICS: dict[int, tuple[str, str]] = {
    0: ("rotating_sector", "faithfully-convertible"),
    1: ("rotation_pivot", "controller"),
    2: ("earthquake", "visual-only-approximation"),
    3: ("shot_out_random_lighting", "visual-only-approximation"),
    4: ("random_lighting", "visual-only-approximation"),
    6: ("subway", "unsupported"),
    7: ("teleport_or_water_link", "faithfully-convertible"),
    8: ("door_linked_lighting", "visual-only-approximation"),
    9: ("door_linked_lighting", "visual-only-approximation"),
    10: ("door_autoclose", "semantically-approximated"),
    11: ("swinging_door", "faithfully-convertible"),
    12: ("switchable_lighting", "semantically-approximated"),
    13: ("explosive_z_sector", "semantically-approximated"),
    15: ("sliding_sector", "faithfully-convertible"),
    16: ("reactor", "unsupported"),
    17: ("warp_elevator", "semantically-approximated"),
    18: ("incremental_z_motion", "unsupported"),
    19: ("explosion_lowers_ceiling", "unsupported"),
    20: ("stretch_bridge", "semantically-approximated"),
    21: ("drop_floor", "unsupported"),
    22: ("teeth_door", "unsupported"),
    23: ("one_way_teleport", "unsupported"),
    24: ("conveyor", "faithfully-convertible"),
    25: ("piston", "unsupported"),
    26: ("escalator", "unsupported"),
    27: ("demo_camera", "visual-only-approximation"),
    28: ("lightning", "visual-only-approximation"),
    29: ("waves", "visual-only-approximation"),
    30: ("two_way_train", "unsupported"),
    31: ("floor_rise_fall", "faithfully-convertible"),
    32: ("ceiling_rise_fall", "faithfully-convertible"),
    33: ("quake_debris", "visual-only-approximation"),
    34: ("conveyor", "unsupported"),
    36: ("projectile_shooter", "unsupported"),
}


def se7_on_floor(duke: DukeDiskMap, sprite: Any) -> bool:
    """EDuke32 ONFLOORZ: ``T5 = (sector.floorz == sprite.z)`` at SE7 spawn.

    Floor teleporters require the player to be on the ground.  An SE whose Z is
    not exactly the sector floor is the silent/hatch path used for manholes.
    """
    return int(sprite.z) == int(duke.sectors[sprite.sector].floor_z)


def se7_vertical_role(duke: DukeDiskMap, sprite: Any) -> str:
    """Upper = closer to the floor (fall-through); lower = closer to the ceiling."""
    sector = duke.sectors[sprite.sector]
    dz_floor = abs(int(sprite.z) - int(sector.floor_z))
    dz_ceiling = abs(int(sprite.z) - int(sector.ceiling_z))
    return "upper" if dz_floor <= dz_ceiling else "lower"


def _sector_bbox(duke: DukeDiskMap, sector_id: int) -> tuple[int, int, int]:
    sector = duke.sectors[sector_id]
    xs = [duke.walls[index].x for index in range(sector.wall_ptr, sector.wall_ptr + sector.wall_count)]
    ys = [duke.walls[index].y for index in range(sector.wall_ptr, sector.wall_ptr + sector.wall_count)]
    return (max(xs) - min(xs), max(ys) - min(ys), int(sector.wall_count))


def sectors_congruent(duke: DukeDiskMap, left: int, right: int, *, tolerance: int = 8) -> bool:
    """Silent hatches are usually translated copies; Blood stacks need matching shape."""
    width_a, height_a, walls_a = _sector_bbox(duke, left)
    width_b, height_b, walls_b = _sector_bbox(duke, right)
    return walls_a == walls_b and abs(width_a - width_b) <= tolerance and abs(height_a - height_b) <= tolerance


def classify_se7_groups(duke: DukeDiskMap) -> dict[int, dict[str, Any]]:
    """Classify every paired SE7 by EDuke32 water / ONFLOORZ / hatch rules."""
    pairs: dict[int, list[tuple[int, Any]]] = defaultdict(list)
    for source_id, sprite in enumerate(duke.sprites):
        if sprite.picnum == 1 and sprite.lotag == 7:
            pairs[int(sprite.hitag)].append((source_id, sprite))
    result: dict[int, dict[str, Any]] = {}
    for hitag, pair in sorted(pairs.items()):
        tags = {duke.sectors[sprite.sector].lotag & 0x3FFF for _source_id, sprite in pair}
        on_floor = [se7_on_floor(duke, sprite) for _source_id, sprite in pair]
        endpoints = [
            {
                "source_sprite": source_id,
                "source_sector": sprite.sector,
                "on_floor": se7_on_floor(duke, sprite),
                "vertical_role": se7_vertical_role(duke, sprite),
                "sector_lotag": duke.sectors[sprite.sector].lotag & 0x3FFF,
            }
            for source_id, sprite in pair
        ]
        if len(pair) == 2 and tags == {1, 2}:
            kind, classification = "water_link", "faithfully-convertible"
        elif len(pair) == 2 and all(on_floor):
            kind, classification = "floor_teleport", "faithfully-convertible"
        elif len(pair) == 2:
            kind = "air_hatch"
            classification = (
                "faithfully-convertible"
                if sectors_congruent(duke, pair[0][1].sector, pair[1][1].sector)
                else "semantically-approximated"
            )
        else:
            kind, classification = "unpaired_se7", "unsupported"
        result[int(hitag)] = {
            "hitag": int(hitag),
            "kind": kind,
            "classification": classification,
            "congruent": (
                len(pair) == 2 and sectors_congruent(duke, pair[0][1].sector, pair[1][1].sector)
            ),
            "endpoints": endpoints,
        }
    return result


def hatch_endpoint_roles(duke: DukeDiskMap, endpoints: list[dict[str, Any]]) -> list[str]:
    """Assign unique upper/lower roles for an air-hatch SE7 pair.

    EDuke32's silent path is relative Z teleport. Blood's upper marker is the
    floor you fall through; the lower marker is the ceiling you arrive through.
    When both effectors classify the same way, the one closer to its floor is
    the upper endpoint.
    """
    roles = [str(item["vertical_role"]) for item in endpoints]
    if len(set(roles)) == len(roles):
        return roles
    ranked = sorted(
        range(len(endpoints)),
        key=lambda index: abs(
            int(duke.sprites[endpoints[index]["source_sprite"]].z)
            - int(duke.sectors[endpoints[index]["source_sector"]].floor_z)
        ),
    )
    resolved = ["lower"] * len(endpoints)
    if ranked:
        resolved[ranked[0]] = "upper"
    return resolved


def gpspeed_lotag(duke: DukeDiskMap, sector_id: int) -> int | None:
    """Return the GPSPEED controller lotag in a sector, if one is present.

    EDuke32 copies this into ``sector.extra`` and uses it as motion velocity
    for tagged-sector doors and some sliding controllers. SE31/SE32 use the
    effector shade instead and ignore this value.
    """
    speeds = [
        int(sprite.lotag)
        for sprite in duke.sprites
        if sprite.picnum == GPSPEED_TILE and sprite.sector == sector_id and sprite.lotag
    ]
    return max(speeds) if speeds else None


def gpspeed_busy_time(duke: DukeDiskMap, sector_id: int, default: int) -> int:
    """Approximate Blood ``busy_time`` ticks from a Duke GPSPEED velocity.

    Fitted so 1024 maps to 5 ticks and 128 maps to 40, matching the inverse of
    Duke's ``sector.extra`` step used by ST18/ST20-class motion.
    """
    speed = gpspeed_lotag(duke, sector_id)
    if speed is None or speed <= 0:
        return default
    return max(4, min(60, int(round(5120 / speed))))


def analyze_duke_mechanisms(duke: DukeDiskMap) -> dict[str, Any]:
    """Return a stable, source-independent behavior inventory for a Duke map.

    Relationships use the Duke tag graph (switch/activator/effectors and
    crack/explosion groups), so callers can use this function on any classic
    v7 board rather than relying on map or object indices.
    """
    effectors = [
        (source_id, sprite)
        for source_id, sprite in enumerate(duke.sprites)
        if sprite.picnum == 1
    ]
    by_hitag: dict[int, list[int]] = defaultdict(list)
    for source_id, sprite in effectors:
        by_hitag[sprite.hitag].append(source_id)

    se7_groups = classify_se7_groups(duke)
    records: list[dict[str, Any]] = []
    for source_id, sprite in effectors:
        kind, classification = EFFECTOR_SEMANTICS.get(
            sprite.lotag, ("unknown_sector_effector", "unsupported")
        )
        record: dict[str, Any] = {
            "source_sprite": source_id,
            "source_sector": sprite.sector,
            "lotag": sprite.lotag,
            "hitag": sprite.hitag,
            "kind": kind,
            "classification": classification,
        }
        if sprite.lotag == 7 and sprite.hitag in se7_groups:
            group = se7_groups[sprite.hitag]
            record["kind"] = group["kind"]
            record["classification"] = group["classification"]
            record["on_floor"] = se7_on_floor(duke, sprite)
        records.append(record)

    cracks: list[dict[str, Any]] = []
    explosion_tags = {
        sprite.hitag for _source_id, sprite in effectors if sprite.lotag == 13
    }
    for source_id, sprite in enumerate(duke.sprites):
        if sprite.picnum not in CRACK_TILES:
            continue
        linked = sprite.hitag in explosion_tags
        cracks.append({
            "source_sprite": source_id,
            "source_sector": sprite.sector,
            "tile": sprite.picnum,
            "link": sprite.hitag,
            "kind": "destructible_wall" if linked else "damageable_crack",
            "classification": "semantically-approximated" if linked else "unsupported",
            "linked_effect": "sector_z_expansion_and_explosion" if linked else None,
        })

    classifications = Counter(record["classification"] for record in records)
    classifications.update(record["classification"] for record in cracks)
    return {
        "$schema": "llmapper.duke-mechanism-inventory",
        "schema_version": 1,
        "counts_by_effector_lotag": dict(sorted(Counter(sprite.lotag for _, sprite in effectors).items())),
        "classifications": dict(sorted(classifications.items())),
        "effectors": records,
        "destructible_walls": cracks,
        "se7_groups": {str(tag): group for tag, group in se7_groups.items()},
        "tag_groups": {
            str(tag): sorted(ids) for tag, ids in sorted(by_hitag.items()) if tag
        },
    }
