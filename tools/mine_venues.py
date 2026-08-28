"""The anatomy of an enterable venue, measured from the maps that have them.

Blood City needs bars, shops, and attractions.  The precedents are E1M4's
carnival attractions and E3M1's saloon/hotel complex (DWE3M1's venues join
where they exist).  This pass finds every interior a player enters from open
sky and measures what the design pattern actually is: how the entrance
announces itself, what happens to light at the threshold, how the main room
sizes against the frontage, whether the counter/stage is geometry or sprites,
and what the venue spends in channels and decoration.

    python -m tools.mine_venues -o projects/blood-city/references/venue-mining.json

The city-street machinery does not transfer to E1M4 -- its midway fragments
into small at-grade sky pieces -- so "public space" here is *all* sky-ceiling
sectors, and a venue is an interior component entered from any of them.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import statistics
from collections import Counter, defaultdict
from typing import Any

from bloodmap.blood_types import SPRITE_TYPES
from bloodmap.doors import MOTION_TYPES, ROTATE_TYPES, SLIDE_TYPES, SWITCH_TYPES, Z_MOTION_TYPES
from tools.mine_city_norms import MapGeom, indoor_components, doorways, load_source

SCHEMA = "llmapper.venue-anatomy"
SCHEMA_VERSION = 1

SOURCES = [
    ("E1M4", "blood", "maps/blood/E1M4.MAP"),
    ("E3M1", "blood", "maps/blood/E3M1.MAP"),
    ("DWE3M1", "blood", "maps/blood/DWE3M1.MAP"),
]

FIRST_USER_CHANNEL = 30

#: A venue smaller than this is a closet or a niche.
MIN_VENUE_AREA = 4_000_000

#: Signage is what you can read while deciding to enter: sprites within this
#: radius of a doorway midpoint.
ENTRANCE_RADIUS = 2048

#: A platform this far above the venue's own floor is furniture-height
#: geometry (counter, stage, dais); above the ceiling of the band it is a
#: mezzanine, below it a step.
PLATFORM_MIN_Z = 1024
PLATFORM_MAX_Z = 8192


def _shade_stats(values: list[int]) -> dict[str, float] | None:
    if not values:
        return None
    return {
        "mean": round(statistics.mean(values), 1),
        "min": min(values),
        "max": max(values),
    }


def _sprite_alignment(sprite: Any) -> str:
    bits = int(sprite.fields["cstat"]) & 48
    return {0: "face", 16: "wall", 32: "floor"}.get(bits, "other")


def _receiver_kind(kind: str, type_id: int) -> str:
    if kind == "sector":
        if type_id in Z_MOTION_TYPES:
            return "door_z"
        if type_id in SLIDE_TYPES:
            return "door_slide"
        if type_id in ROTATE_TYPES:
            return "door_rotate"
        if type_id in MOTION_TYPES:
            return "motion_other"
        return f"sector_{type_id}"
    if kind == "sprite":
        if type_id in SWITCH_TYPES:
            return "switch"
        entry = SPRITE_TYPES.get(type_id)
        if entry:
            category = entry.get("category", "unknown")
            return {"sound": "sound", "trap": "destruction", "thing": "destruction",
                    "marker": "spawn_marker"}.get(category, category)
        return f"sprite_{type_id}"
    return f"{kind}_{type_id}"


def venue_channels(geom: MapGeom, sectors: set[int]) -> dict[str, Any]:
    walls_of = {w for s in sectors for w in geom.sector_walls[s]}
    channels: dict[int, dict[str, list[str]]] = defaultdict(lambda: {"tx": [], "rx": []})
    for kind, items, member in (
        ("sector", geom.sectors, lambda i: i in sectors),
        ("wall", geom.walls, lambda i: i in walls_of),
        ("sprite", geom.sprites, lambda i: int(geom.sprites[i].fields["sector"]) in sectors),
    ):
        for index, item in enumerate(items):
            if item.extra is None or not member(index):
                continue
            type_id = int(item.fields.get("type", 0))
            tx = int(item.extra.fields.get("tx_id", 0) or 0)
            rx = int(item.extra.fields.get("rx_id", 0) or 0)
            if tx >= FIRST_USER_CHANNEL:
                channels[tx]["tx"].append(_receiver_kind(kind, type_id))
            if rx >= FIRST_USER_CHANNEL:
                channels[rx]["rx"].append(_receiver_kind(kind, type_id))
    spend = Counter()
    for record in channels.values():
        for role in record["rx"]:
            spend[role] += 1
    return {
        "user_channels_touching": len(channels),
        "channel_ids": sorted(channels),
        "receiver_spend": dict(spend.most_common()),
    }


def venue_record(geom: MapGeom, public: set[int], component: set[int],
                 doors: list[dict[str, Any]], public_shade_mean: float,
                 public_density: float) -> dict[str, Any]:
    area = sum(geom.area[s] for s in component)
    sprites_in = [
        (i, s) for i, s in enumerate(geom.sprites)
        if int(s.fields["sector"]) in component
    ]
    wall_count = sum(len(geom.sector_walls[s]) for s in component)

    # Entrance: doorways plus what stands within reading distance of them.
    door_walls = [d["wall"] for d in doors]
    door_mid = []
    for w in door_walls:
        (x1, y1), (x2, y2) = geom.wall_segment(w)
        door_mid.append(((x1 + x2) / 2, (y1 + y2) / 2))
    signage = Counter()
    signage_picnums = Counter()
    for i, sprite in enumerate(geom.sprites):
        sx, sy = int(sprite.fields["x"]), int(sprite.fields["y"])
        if any(math.hypot(sx - mx, sy - my) <= ENTRANCE_RADIUS for mx, my in door_mid):
            side = "public" if int(sprite.fields["sector"]) in public else \
                "venue" if int(sprite.fields["sector"]) in component else "other"
            signage[f"{side}_{_sprite_alignment(sprite)}"] += 1
            signage_picnums[int(sprite.fields["picnum"])] += 1

    # Marquee light: animated shade on the door-adjacent sectors, either side.
    threshold_sectors = {d["street_sector"] for d in doors} | {d["into_sector"] for d in doors}
    marquee = []
    for s in threshold_sectors:
        extra = geom.sectors[s].extra
        if extra is None:
            continue
        amplitude = int(extra.fields.get("amplitude", 0) or 0)
        if amplitude:
            marquee.append({"sector": s, "amplitude": amplitude,
                            "wave": int(extra.fields.get("shade_wave", 0) or 0),
                            "freq": int(extra.fields.get("shade_frequency", 0) or 0)})

    # Threshold light: the step from the night street into the room.
    inside_shades = [int(geom.sectors[s].fields["floor_shade"]) for s in component]
    door_public_shades = [int(geom.sectors[d["street_sector"]].fields["floor_shade"])
                          for d in doors]

    # Frontage: shared edge with public space (doorway walls included).
    frontage = 0.0
    for s in component:
        for w in geom.sector_walls[s]:
            other = int(geom.walls[w].fields["next_sector"])
            if other >= 0 and other in public:
                frontage += geom.wall_length(w)

    # Main room and furniture-height platforms.
    main = max(component, key=lambda s: geom.area[s])
    floors = [geom.floor_z[s] for s in component]
    modal_floor = Counter(floors).most_common(1)[0][0]
    platforms = []
    for s in component:
        rise = modal_floor - geom.floor_z[s]
        if PLATFORM_MIN_Z <= rise <= PLATFORM_MAX_Z and geom.area[s] < area / 2:
            platforms.append({"sector": s, "rise_z": rise, "area": round(geom.area[s])})

    alignment = Counter(_sprite_alignment(s) for _i, s in sprites_in)
    picnums = Counter(int(s.fields["picnum"]) for _i, s in sprites_in)

    return {
        "sectors": len(component),
        "sector_ids": sorted(component),
        "area": round(area),
        "budget": {"sectors": len(component), "walls": wall_count,
                   "sprites": len(sprites_in)},
        "channels": venue_channels(geom, component),
        "entrance": {
            "doorways": len(doors),
            "doorway_total_width": round(sum(d["width"] for d in doors)),
            "via_door_sector": sum(1 for d in doors if d["via_door_sector"]),
            "signage_by_side_alignment": dict(signage),
            "signage_picnums_top6": signage_picnums.most_common(6),
            "marquee_animated_sectors": marquee,
        },
        "threshold": {
            "public_floor_shade_at_door": _shade_stats(door_public_shades),
            "venue_floor_shade": _shade_stats(inside_shades),
            "shade_step_mean": round(
                statistics.mean(inside_shades) - statistics.mean(door_public_shades), 1)
            if inside_shades and door_public_shades else None,
        },
        "main_room": {
            "sector": main,
            "area": round(geom.area[main]),
            "share_of_venue": round(geom.area[main] / area, 2),
            "frontage_length": round(frontage),
            "main_room_area_per_frontage": round(geom.area[main] / frontage)
            if frontage else None,
        },
        "platforms_furniture_height": platforms,
        "decoration": {
            "sprites_by_alignment": dict(alignment),
            "sprites_per_1M_area": round(len(sprites_in) / area * 1e6, 2),
            "public_sprites_per_1M_area": round(public_density, 2),
            "density_vs_public": round(len(sprites_in) / area * 1e6 / public_density, 2)
            if public_density else None,
            "picnums_top8": picnums.most_common(8),
        },
    }


def analyze_map(name: str, game: str, path: str) -> dict[str, Any]:
    geom = load_source(name, game, path)
    public = {i for i in range(len(geom.sectors)) if geom.parallax[i]}
    components, membership = indoor_components(geom, public)
    doors = doorways(geom, public, membership)
    by_component: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for door in doors:
        if door["interior_component"] is not None:
            by_component[door["interior_component"]].append(door)

    public_area = sum(geom.area[s] for s in public)
    public_sprites = sum(1 for s in geom.sprites if int(s.fields["sector"]) in public)
    public_density = public_sprites / public_area * 1e6 if public_area else 0.0
    public_shade = statistics.mean(
        int(geom.sectors[s].fields["floor_shade"]) for s in public) if public else 0.0

    venues = []
    for index, comp_doors in sorted(by_component.items()):
        component = components[index]
        if sum(geom.area[s] for s in component) < MIN_VENUE_AREA:
            continue
        record = venue_record(geom, public, component, comp_doors,
                              public_shade, public_density)
        record["interior_component"] = index
        venues.append(record)
    venues.sort(key=lambda v: -v["area"])
    return {
        "map": name,
        "public_sky_sectors": len(public),
        "public_floor_shade_mean": round(public_shade, 1),
        "public_sprites_per_1M_area": round(public_density, 2),
        "venues": venues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output",
                        default="projects/blood-city/references/venue-mining.json")
    args = parser.parse_args(argv)
    payload = {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "scope": {
            "sources": [n for n, _g, _p in SOURCES],
            "method": __doc__,
            "thresholds": {
                "min_venue_area": MIN_VENUE_AREA,
                "entrance_radius": ENTRANCE_RADIUS,
                "platform_band_z": [PLATFORM_MIN_Z, PLATFORM_MAX_Z],
            },
        },
        "per_map": [analyze_map(*source) for source in SOURCES],
    }
    out = pathlib.Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    for record in payload["per_map"]:
        print(record["map"], "venues:", len(record["venues"]))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
