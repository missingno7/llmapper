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
from .model import record_fields
from .sector_geom import sector_walls


CRACK_TILES = frozenset({546, 547, 548, 549})
GPSPEED_TILE = 10
DUKE_DOOR_TILES = frozenset({150,151,152,153,154,155,156,157,158,159,395,
                           447,448,449,717,781,1102,1144,1169,1178,1179,4391})


def swing_group_operable(duke: DukeDiskMap, sprite: Any) -> bool:
    """ST23 is the entry point that arms SE11s sharing its effector hitag."""
    return any(s.picnum==1 and s.lotag==11 and s.hitag==sprite.hitag
               and (duke.sectors[s.sector].lotag & 0x3fff)==23
               for s in duke.sprites)

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
    23: ("teleport_destination", "controller"),
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
    128: ("glass_break_controller", "unsupported"),
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
    walls = [record_fields(duke.walls[index]) for index in sector_walls(duke, sector_id)]
    xs, ys = [wall["x"] for wall in walls], [wall["y"] for wall in walls]
    return (max(xs) - min(xs), max(ys) - min(ys), len(walls))


def sectors_congruent(duke: DukeDiskMap, left: int, right: int, *, tolerance: int = 8) -> bool:
    """Silent hatches are usually translated copies; Blood stacks need matching shape."""
    width_a, height_a, walls_a = _sector_bbox(duke, left)
    width_b, height_b, walls_b = _sector_bbox(duke, right)
    return walls_a == walls_b and abs(width_a - width_b) <= tolerance and abs(height_a - height_b) <= tolerance


def classify_se7_groups(duke: DukeDiskMap) -> dict[int, dict[str, Any]]:
    """Resolve directed SE7 transports, including destination-only SE23 sprites.

    EDuke32 A_Spawn (game.cpp) searches ascending sprite indices for the first
    *other* live SE7 or SE23 with the same hitag. SE23 owns itself and is skipped
    by G_MoveTransports (actors.cpp). More than two endpoints is therefore a
    directed graph, not an ambiguous pair. An unmatched SE7 stays self-owned.
    Blood water and hatch markers can represent only reciprocal pairs; floor
    teleports can represent each directed edge independently.
    """
    pairs: dict[int, list[tuple[int, Any]]] = defaultdict(list)
    for source_id, sprite in enumerate(duke.sprites):
        if sprite.picnum == 1 and sprite.lotag in {7, 23} and sprite.status < 1024:
            pairs[int(sprite.hitag)].append((source_id, sprite))
    result: dict[int, dict[str, Any]] = {}
    for hitag, pair in sorted(pairs.items()):
        tags = {duke.sectors[sprite.sector].lotag for _source_id, sprite in pair}
        on_floor = [se7_on_floor(duke, sprite) for _source_id, sprite in pair]
        endpoints = [
            {
                "source_sprite": source_id,
                "source_sector": sprite.sector,
                "lotag": sprite.lotag,
                "hitag": sprite.hitag,
                "position": [sprite.x, sprite.y, sprite.z],
                "angle": sprite.angle,
                "on_floor": se7_on_floor(duke, sprite),
                "vertical_role": se7_vertical_role(duke, sprite),
                "sector_lotag": duke.sectors[sprite.sector].lotag,
            }
            for source_id, sprite in pair
        ]
        reciprocal = len(pair) == 2 and all(sprite.lotag == 7 for _, sprite in pair)
        if reciprocal and tags == {1, 2} and all(on_floor):
            kind, classification = "water_link", "faithfully-convertible"
        elif reciprocal and tags == {0} and all(on_floor):
            kind, classification = "floor_teleport", "faithfully-convertible"
        elif reciprocal and not any(on_floor):
            kind = "air_hatch"
            classification = (
                "faithfully-convertible"
                if sectors_congruent(duke, pair[0][1].sector, pair[1][1].sector)
                else "semantically-approximated"
            )
        elif not any(sprite.lotag == 7 for _, sprite in pair):
            kind, classification = "destination_only", "controller"
        else:
            kind, classification = "unpaired_se7", "unsupported"

        routes = []
        for source_id, source in pair:
            if source.lotag != 7:
                continue
            destination = next(((i, s) for i, s in pair if i != source_id), None)
            route: dict[str, Any] = {
                "source_sprite": source_id, "source_sector": source.sector,
                "destination_sprite": destination[0] if destination else None,
                "destination_sector": destination[1].sector if destination else None,
                "destination_lotag": destination[1].lotag if destination else None,
                "kind": kind, "classification": classification,
            }
            if destination is None:
                route.update(kind="unpaired_se7", classification="unsupported",
                             reason="No other live SE7 or SE23 shares this hitag; EDuke32 leaves the SE7 self-owned and inactive. No endpoint was invented.")
            elif se7_on_floor(duke, source) and duke.sectors[source.sector].lotag == 0:
                route.update(kind="floor_teleport", classification="faithfully-convertible")
            elif kind not in {"water_link", "air_hatch"}:
                mode = "silent relative-Z" if not se7_on_floor(duke, source) else "water/special-sector"
                route.update(kind="unsupported_transport", classification="unsupported",
                             reason=f"This {mode} route is not a reciprocal water/hatch pair. Blood link markers would introduce a reverse route; sector-enter teleporting would change its activation semantics.")
            routes.append(route)
        if routes and all(route["kind"] == "floor_teleport" for route in routes):
            kind = "floor_teleport" if reciprocal else "directed_teleport"
            classification = "faithfully-convertible"
        elif routes and kind == "unpaired_se7" and len(pair) > 1:
            kind = "mixed_transport"
        result[int(hitag)] = {
            "hitag": int(hitag),
            "kind": kind,
            "classification": classification,
            "congruent": (
                len(pair) == 2 and sectors_congruent(duke, pair[0][1].sector, pair[1][1].sector)
            ),
            "endpoints": endpoints,
            "routes": routes,
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
    for tagged-sector doors and SE31/SE32 via sprite.yvel at spawn.
    """
    speeds = [
        int(sprite.lotag)
        for sprite in duke.sprites
        if sprite.picnum == GPSPEED_TILE and sprite.sector == sector_id
    ]
    return speeds[-1] if speeds else None


def gpspeed_busy_time(duke: DukeDiskMap, sector_id: int, default: int) -> int:
    """Legacy inverse-speed estimate; conversion uses endpoint-aware duke_motion.

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
        if sprite.lotag==11 and not swing_group_operable(duke,sprite):
            record.update(kind="inactive_swing_controller",classification="intentionally-inactive",
                          reason="No same-hitag SE11 group member belongs to ST23; no classic activation path.")
        if sprite.lotag in {7, 23}:
            group = se7_groups.get(sprite.hitag)
            route = next((r for r in group["routes"] if r["source_sprite"] == source_id), None) if group else None
            if route is not None:
                record.update(route)
            elif sprite.status >= 1024:
                record.update(kind="inactive_transport", classification="unsupported",
                              reason="Sprite is not live (statnum >= MAXSTATUS).")
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


def conversion_coverage(duke: DukeDiskMap, records: list[dict[str, Any]],
                        unsupported_sources: set[int]) -> list[dict[str, Any]]:
    """Audit actual lowering separately from a family's theoretical representability."""
    result = []
    inventory = analyze_duke_mechanisms(duke)
    lowered = {r["source_effector"] for r in records if "source_effector" in r}
    lowered_sectors = {r["source_sector"] for r in records
                       if r.get("blood_type") in {600,602,614,615,616,617}}
    for item in inventory["effectors"]:
        i, tag = item["source_sprite"], item["lotag"]
        handled = i in lowered or tag in {1,7,23}
        status = item["classification"] if handled and i not in unsupported_sources else "unsupported"
        reason = None if status != "unsupported" else "No complete native lowering for this source controller; retained geometry is not proof of behavior."
        result.append({**item, "classification":status, "lowered":handled and i not in unsupported_sources,
                       "reason":reason})
    for i, sector in enumerate(duke.sectors):
        raw, tag = int(sector.lotag), int(sector.lotag)&0x3fff
        if not raw:
            continue
        if tag in {16,17,18,19,20,21,22,23,25,27,30}:
            handled = i in lowered_sectors
            kind = "tagged_motion"
        elif tag in {9,26}:
            handled, kind = False, "compound_slide_door" if tag==26 else "vertex_slide_door"
        elif raw == 32767:
            handled, kind = False, "secret_sector"
        elif raw in {-1,-2}:
            handled, kind = False, "exit_sector" if raw==-1 else "delayed_exit_sector"
        elif 10000 <= raw < 16383:
            handled, kind = False, "enter_sound_sector"
        elif tag in {1,2}:
            handled, kind = True, "water_sector"
        else:
            handled, kind = False, "unclassified_tagged_sector"
        result.append({"source_sector":i, "sector_lotag":raw, "kind":kind,
                       "classification":"lowered-see-record" if handled else "unsupported",
                       "lowered":handled})
    for i, sprite in enumerate(duke.sprites):
        if sprite.picnum not in {2,3,4,5,6,8,9,10}:
            continue
        names = {2:"activator",3:"touchplate",4:"locked_activator",5:"sound_controller",
                 6:"locator",8:"master_switch",9:"respawn",10:"gpspeed"}
        handled = sprite.picnum in {2,3,10} or (sprite.picnum==9 and any(r.get("kind")=="dude-spawn" and r.get("source_sprite")==i for r in records))
        result.append({"source_sprite":i,"source_sector":int(sprite.sector),
                       "kind":names[sprite.picnum],"tile":int(sprite.picnum),
                       "lotag":int(sprite.lotag),"hitag":int(sprite.hitag),
                       "classification":"lowered-see-record" if handled else "unsupported",
                       "lowered":handled,
                       "reason":None if handled else "Native controller choreography, locking or audio is not fully implemented; see source fields."})
    for i, wall in enumerate(duke.walls):
        if wall.lotag and wall.picnum in DUKE_DOOR_TILES | {130,134,164,165,166,170}:
            result.append({"source_wall":i, "kind":"tagged_use_wall", "tile":int(wall.picnum),
                           "lotag":int(wall.lotag), "hitag":int(wall.hitag),
                           "classification":"unsupported", "lowered":False,
                           "reason":"Tagged Duke wall Use controls are not translated by the sprite-switch pass."})
    groups = defaultdict(list)
    for i, sprite in enumerate(duke.sprites):
        if sprite.picnum==1 and sprite.lotag in {11,15}:
            groups[(sprite.lotag,sprite.hitag)].append((i,sprite.sector))
    for (tag, hitag), members in sorted(groups.items()):
        if len(members)<2:
            continue
        controller_tags = [{s.lotag for s in duke.sprites if s.sector==sid and s.picnum in {2,4,8}}
                           for _,sid in members]
        connected = bool(set.intersection(*controller_tags))
        result.append({"kind":"linked_moving_group", "effector_lotag":tag,"hitag":hitag,
                       "source_sprites":[i for i,_ in members],"source_sectors":[sid for _,sid in members],
                       "classification":"lowered-see-record" if connected else "unsupported",
                       "lowered":connected,
                       "reason":None if connected else "Local operation must start all same-hitag leaves; independent Push sectors do not reproduce this group."})
    return result
