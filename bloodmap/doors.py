"""Native Blood door and gate implementations.

A moving sector is not yet a usable door. This layer keeps five independent
facets, mined from original campaign maps rather than from a hardcoded prefab:

    Behavior     what geometry changes
    Interaction  what player action causes it
    Condition    what must be true for success
    Feedback     what the player sees/hears on refuse or success
    Signifier    how the map visually communicates the affordance

Verified construction fragments only fill native fields (Push vs Wallpush vs
RX). They do not choose materials, frames, or key emblems.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any, Iterable

from .blood_types import classify
from .format import read_map
from .model import DiskMap
from .patterns import classify_map_population, list_original_maps
from .player_space import PLAYER_PROFILES


SCHEMA = "llmapper.blood-doors"
SCHEMA_VERSION = 1
PLAYER = PLAYER_PROFILES["blood"]
PLAYER_WIDTH = PLAYER.body_width
PLAYER_HEIGHT = PLAYER.standing_height
ACTION_SCAN_RANGE = 64  # NBlood player.cpp ActionScan hitscan range

MOTION_TYPES = {600, 602, 613, 614, 615, 616, 617}
Z_MOTION_TYPES = {600, 602}
SLIDE_TYPES = {614, 616}
ROTATE_TYPES = {613, 615, 617}
KEY_TYPES = {100: 1, 101: 2, 102: 3, 103: 4, 104: 5, 105: 6, 106: 7}
KEY_NAMES = {
    1: "skull", 2: "eye", 3: "fire", 4: "dagger", 5: "spider", 6: "moon", 7: "key7",
}
SWITCH_TYPES = {20, 21, 22, 23}
MARKER_TYPES = set(range(1, 19))
DUDE_CATEGORY = "dude"
SIGNIFIER_RADIUS_PW = 3.0
CLOSED_OPENING = 512
EXAMPLE_CAP = 12
AUTH_CLASSES = {
    "MANDATORY", "OPTIONAL", "STATE_DEPENDENT", "INTENTIONALLY_UNREACHABLE",
    "HELPER", "UNKNOWN",
}


class DoorError(ValueError):
    pass


def xsector_direct_use(*, key: int | None = None) -> dict[str, int]:
    """XSECTOR bits for a door used from the adjacent room.

    NBlood ActionScan (Use, range 64) fires XSECTOR.Wallpush when the hitscan
    hits a portal whose *next* sector has that bit. XSECTOR.Push fires only if
    the player is already in the sector or the hitscan strikes its floor or
    ceiling. A closed Z-door has zero height, so the player stands in the
    hallway: Wallpush is required. Push is kept so an already-entered slab
    still works. This is not a complete door.
    """
    fields = {"trigger_push": 1, "trigger_wall_push": 1}
    if key is not None:
        fields["key"] = int(key)
    return fields


def xsector_remote_rx(rx_id: int) -> dict[str, int]:
    """RX-only motion: no Push, no Wallpush. Switch TX is a separate object."""
    return {"rx_id": int(rx_id), "trigger_push": 0, "trigger_wall_push": 0}


def z_motion_endpoints(floor_z: int, open_ceiling_z: int) -> dict[str, int]:
    return {
        "off_ceiling_z": int(floor_z),
        "on_ceiling_z": int(open_ceiling_z),
        "off_floor_z": int(floor_z),
        "on_floor_z": int(floor_z),
    }


def z_motion_door(floor_z: int, open_ceiling_z: int, *,
                  interaction: str = "direct", rx_id: int | None = None,
                  key: int | None = None, open_time: int = 5,
                  close_time: int | None = None) -> dict[str, int]:
    """Complete XSECTOR behaviour for a rising Z-motion door.

    A type-600 sector with only :func:`z_motion_endpoints` is *not* a complete
    door.  In particular, zero ``busy_time_a`` and ``busy_time_b`` make
    NBlood set its state immediately.  The campaign-backed default is five
    tenths of a second in both directions (the value used by the
    reasoned-authoring pilot).  The three interaction modes keep direct use,
    remote switches, and their deliberate combination distinct in source.

    ``interaction`` is one of ``"direct"``, ``"remote"`` or ``"both"``.
    ``rx_id`` is required for ``remote`` and ``both``; ``key`` only applies to
    direct use.  Return this dictionary as a region's ``sector_behavior``.
    """
    if interaction not in {"direct", "remote", "both"}:
        raise DoorError("interaction must be 'direct', 'remote', or 'both'")
    if interaction in {"remote", "both"} and rx_id is None:
        raise DoorError("a remote Z-motion door needs rx_id")
    if int(open_time) < 1:
        raise DoorError("a Z-motion door needs open_time >= 1; zero is instant")
    if close_time is not None and int(close_time) < 1:
        raise DoorError("a Z-motion door needs close_time >= 1; zero is instant")

    fields = {
        "busy_time_a": int(open_time),
        "busy_time_b": int(open_time if close_time is None else close_time),
        **z_motion_endpoints(floor_z, open_ceiling_z),
    }
    if interaction in {"direct", "both"}:
        fields.update(xsector_direct_use(key=key))
    if interaction in {"remote", "both"}:
        # Do not use xsector_remote_rx here for the dual case: it correctly
        # clears direct-use bits for a remote-only door.
        fields["rx_id"] = int(rx_id)
        if interaction == "remote":
            fields["trigger_push"] = 0
            fields["trigger_wall_push"] = 0
    return fields


def _extra(obj) -> dict[str, Any] | None:
    return None if obj.extra is None else dict(obj.extra.fields)


def _wall_owners(disk: DiskMap) -> list[int]:
    owners = [-1] * len(disk.walls)
    for sector_id, sector in enumerate(disk.sectors):
        first = int(sector.fields["wall_ptr"])
        count = int(sector.fields["wall_count"])
        for wall_id in range(first, first + count):
            owners[wall_id] = sector_id
    return owners


def _wall_segment(disk: DiskMap, wall_id: int) -> tuple[tuple[int, int], tuple[int, int]]:
    wall = disk.walls[wall_id]
    nxt = disk.walls[int(wall.fields["point2"])]
    return (
        (int(wall.fields["x"]), int(wall.fields["y"])),
        (int(nxt.fields["x"]), int(nxt.fields["y"])),
    )


def _midpoint(a: tuple[int, int], b: tuple[int, int]) -> tuple[float, float]:
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


def _owner_walls(disk: DiskMap, sector_id: int) -> list[int]:
    fields = disk.sectors[sector_id].fields
    first = int(fields["wall_ptr"])
    return list(range(first, first + int(fields["wall_count"])))


def _opening(disk: DiskMap, left: int, right: int) -> int:
    lf, lc = int(disk.sectors[left].fields["floor_z"]), int(disk.sectors[left].fields["ceiling_z"])
    rf, rc = int(disk.sectors[right].fields["floor_z"]), int(disk.sectors[right].fields["ceiling_z"])
    # Blood Z grows downward; ceiling_z < floor_z.
    return min(lf, rf) - max(lc, rc)


def _is_motion(sector, extra: dict[str, Any] | None) -> bool:
    type_id = int(sector.fields["type"])
    if type_id in MOTION_TYPES:
        return True
    if extra is None:
        return False
    return (
        int(extra.get("off_ceiling_z") or 0) != int(extra.get("on_ceiling_z") or 0)
        or int(extra.get("off_floor_z") or 0) != int(extra.get("on_floor_z") or 0)
    )


def _motion_kind(type_id: int, extra: dict[str, Any]) -> str:
    if type_id in SLIDE_TYPES:
        return "slide"
    if type_id in ROTATE_TYPES:
        return "rotate"
    ceil_d = int(extra.get("on_ceiling_z") or 0) - int(extra.get("off_ceiling_z") or 0)
    floor_d = int(extra.get("on_floor_z") or 0) - int(extra.get("off_floor_z") or 0)
    if ceil_d and floor_d:
        return "z_split"
    if floor_d:
        return "z_floor"
    if ceil_d:
        return "z_ceiling"
    return "unknown"


def _trigger_names(extra: dict[str, Any]) -> list[str]:
    names = (
        "trigger_push", "trigger_wall_push", "trigger_enter", "trigger_exit",
        "trigger_vector", "trigger_touch", "trigger_proximity", "trigger_once",
    )
    return [name for name in names if extra.get(name)]


def _interaction(extra: dict[str, Any], portal_xwalls: list[dict[str, Any]]) -> str:
    wp = bool(extra.get("trigger_wall_push"))
    push = bool(extra.get("trigger_push"))
    rx = int(extra.get("rx_id") or 0) > 0
    xwall_push = any("trigger_push" in item.get("triggers", []) for item in portal_xwalls)
    enter = bool(extra.get("trigger_enter") or extra.get("trigger_proximity") or extra.get("trigger_touch"))
    if wp or xwall_push:
        kind = "wall_push"
    elif push:
        kind = "sector_push"
    elif enter:
        kind = "touch"
    elif rx:
        kind = "remote_rx"
    else:
        kind = "unknown"
    if rx and kind != "remote_rx":
        return f"{kind}+remote"
    return kind


def _family_signature(record: dict[str, Any]) -> str:
    return "|".join((
        f"t{record['type_id']}",
        record["motion"],
        record["interaction"].split("+")[0],
        "rx" if record["rx_id"] else "norx",
        "key" if record["key"] else "nokey",
        "closed" if record["closed_at_rest"] else "open",
    ))


def _solid_picnums(disk: DiskMap, sector_id: int) -> Counter:
    counts: Counter = Counter()
    for wall_id in _owner_walls(disk, sector_id):
        wall = disk.walls[wall_id]
        if int(wall.fields["next_sector"]) >= 0:
            continue
        counts[int(wall.fields["picnum"])] += 1
    return counts


def _nearby_sprites(
    disk: DiskMap,
    points: list[tuple[float, float]],
    *,
    floor_z: int,
    radius: float,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for sprite_id, sprite in enumerate(disk.sprites):
        fields = sprite.fields
        x, y, z = int(fields["x"]), int(fields["y"]), int(fields["z"])
        dist = min(hypot(x - px, y - py) for px, py in points) if points else 10**9
        if dist > radius:
            continue
        typed = classify("sprite", int(fields["type"]))
        extra = _extra(sprite)
        out.append({
            "sprite_id": sprite_id,
            "type_id": int(fields["type"]),
            "type_name": typed["name"],
            "category": typed["category"],
            "picnum": int(fields["picnum"]),
            "cstat": int(fields["cstat"]),
            "wall_aligned": bool(int(fields["cstat"]) & 16),
            "x_repeat": int(fields["x_repeat"]),
            "y_repeat": int(fields["y_repeat"]),
            "pal": int(fields["pal"]),
            "distance_pw": round(dist / PLAYER_WIDTH, 3),
            "height_ph": round((floor_z - z) / PLAYER_HEIGHT, 3),
            "key": 0 if extra is None else int(extra.get("key") or 0),
            "tx_id": 0 if extra is None else int(extra.get("tx_id") or 0),
            "lock_message": 0 if extra is None else int(extra.get("lock_message") or 0),
        })
    out.sort(key=lambda item: item["distance_pw"])
    return out


def observe_motion_sector(disk: DiskMap, sector_id: int, *, owners: list[int] | None = None) -> dict[str, Any] | None:
    sector = disk.sectors[sector_id]
    extra = _extra(sector)
    if extra is None or not _is_motion(sector, extra):
        return None
    type_id = int(sector.fields["type"])
    owners = owners if owners is not None else _wall_owners(disk)
    floor_z = int(sector.fields["floor_z"])
    ceil_z = int(sector.fields["ceiling_z"])
    rest_opening = floor_z - ceil_z
    off_floor = int(extra.get("off_floor_z") or floor_z)
    on_floor = int(extra.get("on_floor_z") or floor_z)
    off_ceil = int(extra.get("off_ceiling_z") or ceil_z)
    on_ceil = int(extra.get("on_ceiling_z") or ceil_z)
    open_opening = min(off_floor, on_floor) - max(off_ceil, on_ceil)
    # on-state opening for a rising-ceiling door:
    on_opening = on_floor - on_ceil
    portals: list[dict[str, Any]] = []
    portal_xwalls: list[dict[str, Any]] = []
    portal_points: list[tuple[float, float]] = []
    approach_picnums: Counter = Counter()
    door_wall_picnums: Counter = Counter()
    neighbor_fill: Counter = Counter()
    for wall_id in _owner_walls(disk, sector_id):
        wall = disk.walls[wall_id]
        next_sector = int(wall.fields["next_sector"])
        picnum = int(wall.fields["picnum"])
        if next_sector < 0:
            door_wall_picnums[picnum] += 1
            continue
        a, b = _wall_segment(disk, wall_id)
        width = hypot(b[0] - a[0], b[1] - a[1])
        portal_points.append(_midpoint(a, b))
        next_wall = int(wall.fields["next_wall"])
        approach = disk.walls[next_wall] if 0 <= next_wall < len(disk.walls) else wall
        approach_pic = int(approach.fields["picnum"])
        approach_picnums[approach_pic] += 1
        door_wall_picnums[picnum] += 1
        neighbor_fill.update(_solid_picnums(disk, next_sector))
        xwall = _extra(wall)
        axwall = _extra(approach) if approach is not wall else None
        portal = {
            "wall_id": wall_id,
            "next_sector": next_sector,
            "width": int(round(width)),
            "width_pw": round(width / PLAYER_WIDTH, 3),
            "opening": _opening(disk, sector_id, next_sector),
            "door_picnum": picnum,
            "approach_picnum": approach_pic,
            "approach_over_picnum": int(approach.fields["over_picnum"]),
            "approach_shade": int(approach.fields["shade"]),
            "approach_pal": int(approach.fields["pal"]),
            "approach_x_repeat": int(approach.fields["x_repeat"]),
            "approach_y_repeat": int(approach.fields["y_repeat"]),
            "approach_cstat": int(approach.fields["cstat"]),
            "neighbor_fill_picnum": (_solid_picnums(disk, next_sector).most_common(1) or [(None, 0)])[0][0],
        }
        portals.append(portal)
        for payload, source_id in ((xwall, wall_id), (axwall, next_wall)):
            if payload is None:
                continue
            portal_xwalls.append({
                "wall_id": source_id,
                "key": int(payload.get("key") or 0),
                "tx_id": int(payload.get("tx_id") or 0),
                "rx_id": int(payload.get("rx_id") or 0),
                "triggers": _trigger_names(payload),
            })
    distinct_portals = [
        portal for portal in portals
        if portal["approach_picnum"] != portal["neighbor_fill_picnum"]
        and portal["neighbor_fill_picnum"] is not None
    ]
    distinct_faces = []
    seen_faces = set()
    for portal in distinct_portals:
        pic = portal["approach_picnum"]
        if pic not in seen_faces:
            seen_faces.add(pic)
            distinct_faces.append(pic)
    interaction = _interaction(extra, portal_xwalls)
    sprites = _nearby_sprites(
        disk, portal_points or [(0.0, 0.0)],
        floor_z=floor_z,
        radius=SIGNIFIER_RADIUS_PW * PLAYER_WIDTH,
    ) if portal_points else []
    record = {
        "sector_id": sector_id,
        "type_id": type_id,
        "type_name": classify("sector", type_id)["name"],
        "motion": _motion_kind(type_id, extra),
        "interaction": interaction,
        "direct_use": interaction.startswith(("wall_push", "sector_push", "touch")),
        "remote": int(extra.get("rx_id") or 0) > 0,
        "key": int(extra.get("key") or 0),
        "key_name": KEY_NAMES.get(int(extra.get("key") or 0)),
        "locked": int(extra.get("locked") or 0),
        "rx_id": int(extra.get("rx_id") or 0),
        "tx_id": int(extra.get("tx_id") or 0),
        "state": int(extra.get("state") or 0),
        "triggers": _trigger_names(extra),
        "busy_time_a": int(extra.get("busy_time_a") or 0),
        "rest_opening": rest_opening,
        "on_opening": on_opening,
        "open_opening_hint": open_opening,
        "closed_at_rest": rest_opening <= CLOSED_OPENING,
        "sufficient_open": on_opening >= PLAYER_HEIGHT,
        "floor_z": floor_z,
        "ceiling_z": ceil_z,
        "off_floor_z": off_floor,
        "on_floor_z": on_floor,
        "off_ceiling_z": off_ceil,
        "on_ceiling_z": on_ceil,
        "floor_picnum": int(sector.fields["floor_picnum"]),
        "ceiling_picnum": int(sector.fields["ceiling_picnum"]),
        "portals": portals,
        "portal_xwalls": portal_xwalls,
        "approach_picnums": dict(approach_picnums),
        "door_wall_picnums": dict(door_wall_picnums),
        "neighbor_fill_picnums": dict(neighbor_fill),
        "distinct_approach_faces": distinct_faces[:6],
        "visually_distinct_from_fill": bool(distinct_faces),
        "nearby_sprites": sprites[:16],
    }
    record["family"] = _family_signature(record)
    return record


def mine_map(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    disk = read_map(path)
    owners = _wall_owners(disk)
    occurrences = []
    for sector_id in range(len(disk.sectors)):
        record = observe_motion_sector(disk, sector_id, owners=owners)
        if record is None:
            continue
        record["map"] = path.name
        occurrences.append(record)
    return {
        "map": path.name,
        "population": classify_map_population(path),
        "sectors": len(disk.sectors),
        "occurrences": occurrences,
    }


def _cluster(occurrences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in occurrences:
        groups[item["family"]].append(item)
    families = []
    for signature, items in sorted(groups.items(), key=lambda pair: (-len(pair[1]), pair[0])):
        maps = sorted({item["map"] for item in items})
        faces: Counter = Counter()
        fills: Counter = Counter()
        for item in items:
            faces.update(item.get("approach_picnums") or {})
            fills.update(item.get("neighbor_fill_picnums") or {})
        families.append({
            "family": signature,
            "count": len(items),
            "maps": len(maps),
            "map_names": maps[:24],
            "type_id": items[0]["type_id"],
            "motion": items[0]["motion"],
            "interaction": items[0]["interaction"],
            "direct_use": items[0]["direct_use"],
            "remote": items[0]["remote"],
            "keyed": any(item["key"] for item in items),
            "closed_at_rest_share": round(sum(1 for item in items if item["closed_at_rest"]) / len(items), 3),
            "visually_distinct_share": round(
                sum(1 for item in items if item["visually_distinct_from_fill"]) / len(items), 3,
            ),
            "top_approach_picnums": faces.most_common(8),
            "top_neighbor_fill_picnums": fills.most_common(8),
            "examples": [_compact_occurrence(item) for item in items[:EXAMPLE_CAP]],
        })
    return families


def _compact_occurrence(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "map": item.get("map"),
        "sector_id": item["sector_id"],
        "type_id": item["type_id"],
        "motion": item["motion"],
        "interaction": item["interaction"],
        "key": item["key"],
        "rx_id": item["rx_id"],
        "triggers": item["triggers"],
        "closed_at_rest": item["closed_at_rest"],
        "rest_opening": item["rest_opening"],
        "on_opening": item["on_opening"],
        "distinct_approach_faces": item["distinct_approach_faces"],
        "approach_picnums": item["approach_picnums"],
        "neighbor_fill_picnums": item["neighbor_fill_picnums"],
        "portal_widths_pw": [p["width_pw"] for p in item.get("portals") or []],
        "nearby_sprite_picnums": [
            s["picnum"] for s in item.get("nearby_sprites") or []
            if s["type_id"] not in KEY_TYPES and s["category"] != DUDE_CATEGORY
        ][:8],
    }


def mine_directory(directory: str | Path, *, population: str = "blood-campaign") -> dict[str, Any]:
    files = list_original_maps(directory, population=population)
    if not files:
        raise DoorError(f"no {population} maps in {directory}")
    occurrences: list[dict[str, Any]] = []
    maps = []
    for path in files:
        mined = mine_map(path)
        maps.append({"map": mined["map"], "count": len(mined["occurrences"])})
        occurrences.extend(mined["occurrences"])
    families = _cluster(occurrences)
    signifiers = mine_key_signifiers(occurrences)
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "population": population,
        "maps": len(files),
        "occurrence_count": len(occurrences),
        "family_count": len(families),
        "per_map": maps,
        "families": families,
        "key_signifiers": signifiers,
        "limitations": [
            "names such as vertical-ceiling-door are INTERPRETED cluster labels, not native types",
            "closed_at_rest uses rest opening <= 512, not a mapper-authored door flag",
            "approach picnum is the paired portal wall the player looks at from the neighbor",
            "generated reconstructions are excluded by population classification",
        ],
    }


def query_door_precedents(
    catalog: dict[str, Any],
    *,
    direct_use: bool | None = None,
    remote: bool | None = None,
    keyed: bool | None = None,
    key_id: int | None = None,
    motion: str | None = None,
    type_id: int | None = None,
    interaction: str | None = None,
    closed_at_rest: bool | None = None,
    visually_distinct: bool | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Design-precedent retrieval. Does not insert a prefab."""
    hits: list[dict[str, Any]] = []
    for family in catalog.get("families") or []:
        for example in family.get("examples") or []:
            if direct_use is not None and bool(family.get("direct_use")) != direct_use:
                break
            if remote is not None and bool(family.get("remote")) != remote:
                break
            if keyed is not None and bool(family.get("keyed")) != keyed:
                break
            if motion is not None and family.get("motion") != motion:
                break
            if type_id is not None and int(family.get("type_id") or 0) != type_id:
                break
            if interaction is not None and interaction not in str(family.get("interaction") or ""):
                break
            if key_id is not None and int(example.get("key") or 0) != key_id:
                continue
            if closed_at_rest is not None and bool(example.get("closed_at_rest")) != closed_at_rest:
                continue
            if visually_distinct is not None:
                distinct = bool(example.get("distinct_approach_faces"))
                if distinct != visually_distinct:
                    continue
            payload = dict(example)
            payload["family"] = family["family"]
            hits.append(payload)
            if len(hits) >= limit:
                return hits
    return hits


def mine_key_signifiers(occurrences: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Sprites and approach walls near keyed motion, versus the unkeyed baseline."""
    keyed: list[dict[str, Any]] = []
    unkeyed: list[dict[str, Any]] = []
    for item in occurrences:
        (keyed if item.get("key") else unkeyed).append(item)

    def _sprite_counts(items: list[dict[str, Any]]) -> Counter:
        counts: Counter = Counter()
        for item in items:
            seen = set()
            for sprite in item.get("nearby_sprites") or []:
                if sprite["type_id"] in KEY_TYPES or sprite["type_id"] in MARKER_TYPES:
                    continue
                if sprite["category"] in {DUDE_CATEGORY, "weapon", "ammo", "health", "armor", "powerup", "key"}:
                    continue
                key = (sprite["picnum"], sprite["type_id"], int(sprite["wall_aligned"]))
                if key in seen:
                    continue
                seen.add(key)
                counts[key] += 1
        return counts

    def _face_counts(items: list[dict[str, Any]]) -> Counter:
        counts: Counter = Counter()
        for item in items:
            for pic, n in (item.get("approach_picnums") or {}).items():
                counts[int(pic)] += n
        return counts

    keyed_sprites = _sprite_counts(keyed)
    unkeyed_sprites = _sprite_counts(unkeyed)
    keyed_faces = _face_counts(keyed)
    unkeyed_faces = _face_counts(unkeyed)
    keyed_n, unkeyed_n = max(1, len(keyed)), max(1, len(unkeyed))

    sprite_rows = []
    for key, count in keyed_sprites.most_common(40):
        picnum, type_id, wall_aligned = key
        baseline = unkeyed_sprites.get(key, 0)
        keyed_rate = count / keyed_n
        unkeyed_rate = baseline / unkeyed_n
        maps = sorted({
            item.get("map") for item in keyed
            if any(
                s["picnum"] == picnum and s["type_id"] == type_id
                for s in item.get("nearby_sprites") or []
            )
        })
        by_key: Counter = Counter()
        for item in keyed:
            if any(s["picnum"] == picnum and s["type_id"] == type_id for s in item.get("nearby_sprites") or []):
                by_key[item["key"]] += 1
        sprite_rows.append({
            "picnum": picnum,
            "type_id": type_id,
            "type_name": classify("sprite", type_id)["name"],
            "wall_aligned": bool(wall_aligned),
            "keyed_occurrences": count,
            "unkeyed_occurrences": baseline,
            "keyed_rate": round(keyed_rate, 3),
            "unkeyed_rate": round(unkeyed_rate, 3),
            "lift": round(keyed_rate / unkeyed_rate, 2) if unkeyed_rate else None,
            "maps": len(maps),
            "map_names": maps[:16],
            "by_key": {KEY_NAMES.get(k, str(k)): n for k, n in by_key.most_common()},
            "confidence": "strong" if count >= 8 and len(maps) >= 4 and (unkeyed_rate == 0 or keyed_rate >= 3 * unkeyed_rate) else (
                "moderate" if count >= 4 and len(maps) >= 2 else "weak"
            ),
        })

    face_rows = []
    for picnum, count in keyed_faces.most_common(24):
        baseline = unkeyed_faces.get(picnum, 0)
        keyed_rate = count / keyed_n
        unkeyed_rate = baseline / unkeyed_n
        face_rows.append({
            "picnum": picnum,
            "keyed_portal_walls": count,
            "unkeyed_portal_walls": baseline,
            "keyed_rate": round(keyed_rate, 3),
            "unkeyed_rate": round(unkeyed_rate, 3),
            "lift": round(keyed_rate / unkeyed_rate, 2) if unkeyed_rate else None,
        })

    return {
        "$schema": "llmapper.blood-key-signifiers",
        "schema_version": SCHEMA_VERSION,
        "keyed_motion_sectors": len(keyed),
        "unkeyed_motion_sectors": len(unkeyed),
        "sprite_candidates": sprite_rows,
        "approach_wall_candidates": face_rows,
        "notes": [
            "association is co-occurrence near keyed motion, not a proven emblem ontology",
            "key pickup sprites (types 100-106) are excluded",
            "confidence is corpus repetition, not visual resemblance",
        ],
    }


def mine_scenic_candidates(path: str | Path) -> dict[str, Any]:
    """Sectors that are not rest-walkable from start but share a portal with one that is.

    Candidates only. The LLM interprets; this does not label scenery.
    """
    from .spatial import analyze_spatial

    path = Path(path)
    disk = read_map(path)
    spatial = analyze_spatial(disk.to_build_ir())
    rest: set[int] = set()
    start = int(disk.header["start_sector"])
    graph: dict[int, set[int]] = defaultdict(set)
    for edge in spatial["views"]["traversability"]["walkable_at_rest"]:
        a = int(str(edge["sectors"][0]).split(":")[1])
        b = int(str(edge["sectors"][1]).split(":")[1])
        graph[a].add(b)
        graph[b].add(a)
    pending = [start]
    rest.add(start)
    while pending:
        current = pending.pop()
        for nxt in graph.get(current, ()):
            if nxt not in rest:
                rest.add(nxt)
                pending.append(nxt)
    owners = _wall_owners(disk)
    candidates = []
    for sector_id in range(len(disk.sectors)):
        if sector_id in rest:
            continue
        neighbors = []
        for wall_id in _owner_walls(disk, sector_id):
            nxt = int(disk.walls[wall_id].fields["next_sector"])
            if nxt >= 0 and nxt in rest:
                neighbors.append({
                    "neighbor": nxt,
                    "wall_id": wall_id,
                    "picnum": int(disk.walls[wall_id].fields["picnum"]),
                    "opening": _opening(disk, sector_id, nxt),
                    "blocking": bool(int(disk.walls[wall_id].fields["cstat"]) & 1),
                })
        if not neighbors:
            continue
        sprites = [
            {
                "sprite_id": index,
                "type_id": int(sprite.fields["type"]),
                "picnum": int(sprite.fields["picnum"]),
                "category": classify("sprite", int(sprite.fields["type"]))["category"],
            }
            for index, sprite in enumerate(disk.sprites)
            if int(sprite.fields["sector"]) == sector_id
        ]
        gameplay = [s for s in sprites if s["category"] in {"weapon", "ammo", "health", "armor", "key", "dude", "flag"}]
        candidates.append({
            "sector_id": sector_id,
            "floor_picnum": int(disk.sectors[sector_id].fields["floor_picnum"]),
            "ceiling_picnum": int(disk.sectors[sector_id].fields["ceiling_picnum"]),
            "type_id": int(disk.sectors[sector_id].fields["type"]),
            "visible_from_rest_via_portal": neighbors,
            "sprite_count": len(sprites),
            "gameplay_sprites": len(gameplay),
            "has_xsector": disk.sectors[sector_id].extra is not None,
        })
    return {
        "map": path.name,
        "rest_reachable": len(rest),
        "adjacent_unreachable": len(candidates),
        "candidates": candidates[:80],
    }


def authored_gate_audit(compiled) -> dict[str, Any]:
    """Forensic per-gate report for a PlanarLayout compile (authored maps only)."""
    disk = compiled.level.to_disk_map()
    owners = _wall_owners(disk)
    gates = []
    for region_id, region in compiled.layout.regions.items():
        if region.type not in MOTION_TYPES and region.role not in {"doorway", "gated_pocket"}:
            continue
        sector_id = compiled.allocations[region_id].sector_id
        native = observe_motion_sector(disk, sector_id, owners=owners) or {}
        intent = dict(region.intent)
        classification = str(intent.get("classification") or "UNKNOWN")
        extra = _extra(disk.sectors[sector_id]) or {}
        failures = []
        wants_direct = intent.get("interaction") == "direct_use" or (
            extra.get("trigger_push") and not extra.get("rx_id")
        )
        if wants_direct and not extra.get("trigger_wall_push"):
            failures.append(
                "closed Z-door used from the hallway requires XSECTOR.trigger_wall_push; "
                "trigger_push alone does not fire ActionScan on the portal wall"
            )
        if native.get("closed_at_rest") and not native.get("visually_distinct_from_fill"):
            if classification != "OPTIONAL" and intent.get("hidden") is not True:
                failures.append(
                    "approach portal picnum matches neighboring fill; closed gate is not visually a door"
                )
        if extra.get("key") and not any(
            s["type_id"] not in KEY_TYPES and s["category"] not in {DUDE_CATEGORY, "key"}
            for s in native.get("nearby_sprites") or []
        ):
            if not native.get("distinct_approach_faces"):
                failures.append("keyed gate has no nearby non-key sprite and no distinct face tile")
        if native.get("closed_at_rest") and not native.get("sufficient_open"):
            failures.append("on-state opening is below standing player height")
        approach = []
        for portal in native.get("portals") or []:
            approach.append({
                "wall_id": portal["wall_id"],
                "approach_picnum": portal["approach_picnum"],
                "neighbor_fill_picnum": portal["neighbor_fill_picnum"],
                "width_pw": portal["width_pw"],
                "opening": portal["opening"],
            })
        gates.append({
            "region_id": region_id,
            "sector_id": sector_id,
            "semantic_intent": intent,
            "classification": classification,
            "native_implementation": {
                "type_id": native.get("type_id") or region.type,
                "motion": native.get("motion"),
                "family": native.get("family"),
                "triggers": native.get("triggers") or [],
                "rx_id": native.get("rx_id") or 0,
                "tx_id": native.get("tx_id") or 0,
                "key": native.get("key") or 0,
            },
            "visual_implementation": {
                "region_wall_picnum": region.wall_picnum,
                "region_floor_picnum": region.floor_picnum,
                "region_ceiling_picnum": region.ceiling_picnum,
                "approach_portals": approach,
                "visually_distinct": native.get("visually_distinct_from_fill"),
                "nearby_sprites": native.get("nearby_sprites") or [],
            },
            "interaction_trigger": native.get("interaction") or "unknown",
            "lock_condition": native.get("key") or 0,
            "movement_behavior": native.get("motion"),
            "opening_state": {
                "on_opening": native.get("on_opening"),
                "sufficient_open": native.get("sufficient_open"),
            },
            "closing_state": {
                "rest_opening": native.get("rest_opening"),
                "closed_at_rest": native.get("closed_at_rest"),
            },
            "player_facing": {
                "identify_visually": bool(native.get("visually_distinct_from_fill")) or bool(intent.get("hidden")),
                "activate_from_adjacent": bool(extra.get("trigger_wall_push")) or bool(extra.get("rx_id")),
                "use_triggers": bool(extra.get("trigger_wall_push")) or bool(extra.get("rx_id")),
                "requires_intended_key": bool(extra.get("key")),
                "open_enough": bool(native.get("sufficient_open")),
            },
            "player_facing_failures": failures,
        })
    return {
        "$schema": "llmapper.authored-gate-audit",
        "schema_version": SCHEMA_VERSION,
        "map_name": compiled.layout.name,
        "gate_count": len(gates),
        "gates": gates,
        "action_scan_range": ACTION_SCAN_RANGE,
        "evidence": (
            "NBlood ActionScan: XWALL.trigger_push; portal hit whose next XSECTOR has "
            "trigger_wall_push; XSECTOR.trigger_push only if already inside or floor/ceiling hit"
        ),
    }


def gate_audit_markdown(audit: dict[str, Any]) -> str:
    lines = [
        f"# {audit.get('map_name') or 'Authored'} door / gate audit",
        "",
        "Authored-map forensic report. Original campaign maps are evidence, not this file.",
        "",
        f"ActionScan Use range: {audit.get('action_scan_range')} Build units.",
        "",
        str(audit.get("evidence") or ""),
        "",
    ]
    for gate in audit.get("gates") or []:
        native = gate["native_implementation"]
        visual = gate["visual_implementation"]
        fail = gate.get("player_facing_failures") or []
        lines.extend([
            f"## {gate['region_id']}",
            "",
            f"- classification: `{gate.get('classification')}`",
            f"- intent: `{gate.get('semantic_intent')}`",
            f"- native: type {native.get('type_id')} {native.get('motion')} family `{native.get('family')}`",
            f"- triggers: {native.get('triggers')} rx={native.get('rx_id')} key={native.get('key')}",
            f"- interaction: {gate.get('interaction_trigger')}",
            f"- closed rest opening: {gate['closing_state'].get('rest_opening')} "
            f"open-state: {gate['opening_state'].get('on_opening')}",
            f"- region tiles wall/floor/ceil: "
            f"{visual.get('region_wall_picnum')}/{visual.get('region_floor_picnum')}/{visual.get('region_ceiling_picnum')}",
            f"- visually distinct approach face: {visual.get('visually_distinct')}",
        ])
        for portal in visual.get("approach_portals") or []:
            lines.append(
                f"  - portal wall {portal['wall_id']}: approach picnum {portal['approach_picnum']} "
                f"vs neighbor fill {portal['neighbor_fill_picnum']} "
                f"width {portal['width_pw']} pw opening {portal['opening']}"
            )
        if fail:
            lines.append("- player-facing failures:")
            for item in fail:
                lines.append(f"  - {item}")
        else:
            lines.append("- player-facing failures: none recorded")
        lines.append("")
    return "\n".join(lines) + "\n"


def door_affordance_report(compiled) -> dict[str, Any]:
    """Acceptance: no mandatory door may be mechanically invisible or unusable."""
    audit = authored_gate_audit(compiled)
    results = []
    ok = True
    for gate in audit["gates"]:
        intent = gate.get("semantic_intent") or {}
        classification = gate.get("classification") or "UNKNOWN"
        hidden = bool(intent.get("hidden"))
        failures = list(gate.get("player_facing_failures") or [])
        if classification in {"INTENTIONALLY_UNREACHABLE", "HELPER"}:
            status = "exempt"
        elif classification == "OPTIONAL" and hidden:
            status = "pass" if not [
                item for item in failures if "Wallpush" in item or "opening is below" in item
            ] else "fail"
        else:
            status = "pass" if not failures else "fail"
        if status == "fail":
            ok = False
        results.append({
            "region_id": gate["region_id"],
            "classification": classification,
            "status": status,
            "failures": failures,
            "native": gate["native_implementation"],
            "visual_distinct": gate["visual_implementation"].get("visually_distinct"),
            "interaction": gate.get("interaction_trigger"),
        })
    return {
        "$schema": "llmapper.door-affordance",
        "schema_version": SCHEMA_VERSION,
        "ok": ok,
        "gates": results,
    }
