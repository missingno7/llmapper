from __future__ import annotations

from collections import Counter, defaultdict
from math import hypot
from pathlib import Path
from typing import Any

from .analysis import validate_map
from .art import ArtError, nearest_art_tiles
from .construction import LevelBuilder, portal_profiles
from .composition import _sector_surface_z
from .conversion import DUKE_TO_BLOOD_MATERIAL_EXACT, _scale, convert_build_ir, native_scale
from .duke import DukeDiskMap
from .duke_semantics import CRACK_TILES, analyze_duke_mechanisms
from .format import read_map


class E3L11ConversionError(ValueError):
    pass


DUKE_CONTROLLERS = {1, 2, 3, 4, 5, 6, 8, 9, 10}
DUKE_SWITCHES = {130, 164, 165}

# Deliberate gameplay-role substitutions. The target type/tile pairs are
# established by the local Blood map corpus; "approximation" is kept visible
# in the report because different games do not have one-to-one actor sets.
ENTITY_MAP: dict[int, tuple[int, int, int, int, int, str]] = {
    # weapons
    28: (41, 559, 3, 128, 48, "equivalent:shotgun->sawed-off"),
    22: (42, 558, 3, 128, 48, "equivalent:chaingun->Tommy gun"),
    23: (46, 526, 3, 128, 48, "equivalent:RPG->napalm launcher"),
    24: (45, 539, 3, 128, 48, "approximation:freezer->Tesla cannon"),
    25: (50, 800, 3, 128, 48, "approximation:shrinker->Life Leech"),
    27: (64, 811, 3, 128, 40, "approximation:tripbomb->proximity bombs"),
    29: (45, 539, 3, 128, 48, "approximation:devastator->Tesla cannon"),
    # ammo, health, inventory
    37: (73, 548, 3, 128, 24, "equivalent:freeze ammo->Tesla charge"),
    40: (72, 817, 3, 128, 48, "equivalent:ammo box->Tommy drum"),
    41: (73, 548, 3, 128, 24, "equivalent:battery ammo->Tesla charge"),
    42: (73, 548, 3, 128, 24, "approximation:devastator ammo->Tesla charge"),
    44: (79, 801, 3, 128, 48, "equivalent:rocket ammo->gasoline"),
    47: (63, 809, 3, 384, 48, "equivalent:pipebomb ammo->TNT box"),
    49: (68, 812, 3, 128, 48, "equivalent:shotgun ammo->shell box"),
    51: (109, 2169, 3, 128, 40, "equivalent:cola->Life Essence"),
    52: (109, 2169, 3, 128, 40, "equivalent:portable medkit->Life Essence"),
    53: (107, 519, 3, 128, 48, "equivalent:first aid->Doctor Bag"),
    54: (140, 2628, 3, 128, 64, "equivalent:shield->basic armor"),
    55: (117, 829, 3, 128, 40, "approximation:steroids->Guns Akimbo"),
    57: (115, 827, 3, 128, 40, "approximation:jetpack->Jump Boots"),
    59: (125, 839, 3, 128, 40, "equivalent:heat sensor->Beast Vision"),
    100: (110, 2433, 3, 128, 40, "equivalent:atomic health->Life Seed"),
    # enemies
    2370: (213, 1920, 6, 384, 16, "approximation:slime->brown spider"),
    2120: (201, 2820, 6, 384, 40, "approximation:Lizman->Tommy cultist"),
    2121: (201, 2820, 6, 384, 40, "approximation:Lizman stay-put->Tommy cultist"),
    2150: (202, 2825, 6, 384, 40, "approximation:Lizman spitter->shotgun cultist"),
    2165: (211, 1270, 6, 384, 40, "approximation:Lizman jumper->hellhound"),
    1880: (206, 1470, 6, 384, 40, "approximation:drone->flesh gargoyle"),
    2045: (202, 2825, 6, 384, 40, "approximation:Pigcop dive->shotgun cultist"),
    2000: (202, 2825, 6, 384, 40, "approximation:Pigcop->shotgun cultist"),
    2001: (202, 2825, 6, 384, 40, "approximation:Pigcop stay-put->shotgun cultist"),
    1820: (217, 1570, 6, 384, 48, "approximation:Octabrain->Gill Beast"),
    1960: (206, 1470, 6, 384, 40, "approximation:Recon->flesh gargoyle"),
    2631: (227, 2680, 6, 384, 64, "approximation:Battlelord->Cerberus"),
}


def _channel(tag: int) -> int:
    value = 100 + int(tag)
    if not 100 <= value <= 1023:
        raise E3L11ConversionError(f"Duke tag {tag} cannot be allocated to a Blood user channel")
    return value


def _neighbors(duke: DukeDiskMap, sector_id: int) -> list[int]:
    sector = duke.sectors[sector_id]
    return sorted({
        duke.walls[index].next_sector
        for index in range(sector.wall_ptr, sector.wall_ptr + sector.wall_count)
        if duke.walls[index].next_sector >= 0
    })


def _surface_candidates(blood_maps: Path) -> dict[str, set[int]]:
    """Corpus-backed candidates separated by authored surface role.

    A ceiling light or a floor material may be close in raw ART feature space to
    a wall texture, but that is normally a worse conversion.  Keep each role's
    candidate family distinct before doing the visual match.
    """
    result: dict[str, set[int]] = {"ceiling": set(), "floor": set(), "wall": set()}
    for path in sorted(blood_maps.glob("*.MAP")):
        disk = read_map(path)
        result["ceiling"].update(sector.ceiling_picnum for sector in disk.sectors)
        result["floor"].update(sector.floor_picnum for sector in disk.sectors)
        result["wall"].update(wall.picnum for wall in disk.walls)
        result["wall"].update(wall.over_picnum for wall in disk.walls if wall.over_picnum)
    return {
        role: {value for value in candidates if 0 < value < 4096}
        for role, candidates in result.items()
    }


def _apply_materials(
    duke: DukeDiskMap,
    builder: LevelBuilder,
    *,
    duke_art: Path | None,
    blood_art: Path | None,
    blood_maps: Path | None,
) -> dict[str, Any]:
    source_tiles = {
        "ceiling": {sector.ceiling_picnum for sector in duke.sectors},
        "floor": {sector.floor_picnum for sector in duke.sectors},
        "wall": {wall.picnum for wall in duke.walls} | {wall.over_picnum for wall in duke.walls if wall.over_picnum},
    }
    matches: dict[str, dict[int, dict[str, float | int]]] = {role: {} for role in source_tiles}
    engine = "role-default"
    warning = None
    if duke_art and blood_art and blood_maps:
        try:
            candidates = _surface_candidates(blood_maps)
            for role, source in source_tiles.items():
                matches[role] = nearest_art_tiles(
                    source,
                    candidates[role],
                    source_art=duke_art,
                    target_art=blood_art,
                    source_palette=blood_art / "xmapedit" / "palettes" / "import" / "DUKE3D.PAL",
                    target_palette=blood_art / "xmapedit" / "palettes" / "import" / "BLOOD.PAL",
                )
            engine = "role-aware ART palette/spatial nearest-neighbour over corpus ceiling, floor, and wall families"
        except (ArtError, OSError, ValueError) as exc:
            warning = str(exc)
    decisions: Counter[str] = Counter()

    def material(tile: int, fallback: int, role: str) -> int:
        if tile in DUKE_TO_BLOOD_MATERIAL_EXACT:
            decisions["known/manual-mapping"] += 1
            return DUKE_TO_BLOOD_MATERIAL_EXACT[tile]
        if tile in matches[role]:
            decisions["semantic+visual-match"] += 1
            return int(matches[role][tile]["blood_tile"])
        decisions["unmapped-role-default"] += 1
        return fallback

    for index, source in enumerate(duke.sectors):
        target = builder.level.sectors[index]["fields"]
        target["ceiling_picnum"] = material(source.ceiling_picnum, 385, "ceiling")
        target["floor_picnum"] = material(source.floor_picnum, 292, "floor")
        if (source.lotag & 0x3FFF) == 1:
            target["floor_picnum"] = 2915
            decisions["water-surface"] += 1
        elif (source.lotag & 0x3FFF) == 2:
            target["ceiling_picnum"] = 2915
            decisions["water-surface"] += 1
    for index, source in enumerate(duke.walls):
        target = builder.level.walls[index]["fields"]
        target["picnum"] = material(source.picnum, 180, "wall")
        target["over_picnum"] = material(source.over_picnum, 180, "wall") if source.over_picnum else 0
    tile_matches = {
        role: {
            str(tile): (
                {"blood_tile": DUKE_TO_BLOOD_MATERIAL_EXACT[tile], "classification": "known/manual-mapping"}
                if tile in DUKE_TO_BLOOD_MATERIAL_EXACT else
                ({**matches[role][tile], "classification": "semantic+visual-match"} if tile in matches[role] else
                 {"blood_tile": None, "classification": "unmapped"})
            )
            for tile in sorted(tiles)
        }
        for role, tiles in source_tiles.items()
    }
    return {
        "classification": "approximation",
        "engine": engine,
        "decisions": dict(sorted(decisions.items())),
        "unique_source_tiles": len(set().union(*source_tiles.values())),
        "matched_tiles": sum(len(value) for value in matches.values()),
        "tile_matches": tile_matches,
        "warning": warning,
    }


def _add_marker(
    builder: LevelBuilder, *, sector: int, owner: int, x: int, y: int, z: int,
    type: int, angle: int = 0,
) -> int:
    ceiling = _sector_surface_z(builder.level, sector, x, y, "ceiling")
    floor = _sector_surface_z(builder.level, sector, x, y, "floor")
    z = max(ceiling, min(floor, z))
    sprite_id = builder.add_sprite(
        sector=sector, x=x, y=y, z=z, type=type, picnum=3997,
        status=10, angle=angle, cstat=32896, x_repeat=64, y_repeat=64,
    )
    builder.level.sprites[sprite_id]["fields"]["owner"] = owner
    return sprite_id


def _scaled_position(builder: LevelBuilder, source: Any, scale: Any) -> tuple[int, int, int]:
    x, y, z = _scale(source.x, scale), _scale(source.y, scale), _scale(source.z, scale)
    ceiling = _sector_surface_z(builder.level, source.sector, x, y, "ceiling")
    floor = _sector_surface_z(builder.level, source.sector, x, y, "floor")
    return x, y, max(ceiling, min(floor, z))


def _crack_wall_target(duke: DukeDiskMap, source: Any, *, maximum_distance: float = 8.0) -> int | None:
    """Resolve a wall-aligned Duke crack to the wall it damages.

    CRACK sprites sit on the affected wall at runtime.  Projection onto the
    containing sector's wall segments is portable across board ordering and is
    intentionally conservative: an imprecise decorative crack is reported,
    not converted into a potentially wrong breakable wall.
    """
    sector = duke.sectors[source.sector]
    candidates: list[tuple[float, int]] = []
    for wall_id in range(sector.wall_ptr, sector.wall_ptr + sector.wall_count):
        start = duke.walls[wall_id]
        end = duke.walls[start.point2]
        dx, dy = end.x - start.x, end.y - start.y
        length2 = dx * dx + dy * dy
        if not length2:
            continue
        ratio = max(0.0, min(1.0, ((source.x - start.x) * dx + (source.y - start.y) * dy) / length2))
        distance = hypot(source.x - (start.x + ratio * dx), source.y - (start.y + ratio * dy))
        candidates.append((distance, wall_id))
    if not candidates:
        return None
    distance, wall_id = min(candidates)
    return wall_id if distance <= maximum_distance else None


def _rotation_activation_tag(duke: DukeDiskMap, sectors: set[int]) -> int | None:
    """Find the common Duke MasterSwitch group governing a rotating assembly.

    Duke ST30 sectors point at their SE0 controller through a sector-local
    sprite index.  The player's activation is normally mediated by MasterSwitch
    sprites placed in each member sector.  Recover their common lotag instead
    of using an authored map's channel number.
    """
    tags = {
        sprite.lotag
        for sprite in duke.sprites
        if sprite.picnum == 8 and sprite.sector in sectors and sprite.lotag
    }
    return next(iter(tags)) if len(tags) == 1 else None


def _static_progression(disk: Any) -> dict[str, Any]:
    adjacency: dict[int, set[int]] = defaultdict(set)
    for profile in portal_profiles(disk.to_level_ir(), min_width=512, min_opening=4096):
        if profile["walkable_when_open"]:
            left, right = profile["sectors"]
            adjacency[left].add(right)
            adjacency[right].add(left)
    water: dict[int, list[int]] = defaultdict(list)
    for sprite in disk.sprites:
        if sprite.type in {9, 10} and sprite.extra is not None:
            water[sprite.extra.data_1].append(sprite.sector)
    for sectors in water.values():
        if len(sectors) == 2:
            left, right = sectors
            adjacency[left].add(right)
            adjacency[right].add(left)
    for sector_id, sector in enumerate(disk.sectors):
        if sector.type == 604 and sector.extra is not None and sector.extra.marker_0 >= 0:
            adjacency[sector_id].add(disk.sprites[sector.extra.marker_0].sector)
    reached = {disk.header["start_sector"]}
    pending = list(reached)
    while pending:
        current = pending.pop()
        for neighbor in adjacency[current] - reached:
            reached.add(neighbor)
            pending.append(neighbor)
    exits = {
        sprite.sector for sprite in disk.sprites
        if sprite.extra is not None and sprite.extra.tx_id == 4
    }
    return {
        "model": "reciprocal portals open at configured endpoints plus paired water links and teleports",
        "minimum_portal_width": 512,
        "minimum_opening": 4096,
        "start_sector": disk.header["start_sector"],
        "reachable_sectors": len(reached),
        "total_sectors": len(disk.sectors),
        "exit_sectors": sorted(exits),
        "all_exits_reachable": bool(exits) and exits <= reached,
    }


def _channel_audit(disk: Any) -> dict[str, Any]:
    transmitters: Counter[int] = Counter()
    receivers: Counter[int] = Counter()
    for objects in (disk.sectors, disk.walls, disk.sprites):
        for item in objects:
            if item.extra is None:
                continue
            if item.extra.tx_id:
                transmitters[item.extra.tx_id] += 1
            if item.extra.rx_id:
                receivers[item.extra.rx_id] += 1
    return {
        "transmitters": dict(sorted(transmitters.items())),
        "receivers": dict(sorted(receivers.items())),
        "dangling_user_transmit_channels": sorted(
            channel for channel in transmitters if channel >= 100 and channel not in receivers
        ),
        "dangling_user_receive_channels": sorted(
            channel for channel in receivers if channel >= 100 and channel not in transmitters
        ),
        "special_transmit_channels": sorted(channel for channel in transmitters if channel < 100),
    }


def convert_e3l11_to_blood(
    duke: DukeDiskMap,
    *,
    duke_art: str | Path | None = None,
    blood_art: str | Path | None = None,
    blood_maps: str | Path | None = None,
) -> tuple[Any, dict[str, Any]]:
    scale = native_scale("duke3d", "blood")
    geometry, _base_report = convert_build_ir(duke.to_build_ir(), "blood", policy="geometry-only")
    builder = LevelBuilder(geometry.to_level_ir())
    material_report = _apply_materials(
        duke, builder,
        duke_art=Path(duke_art) if duke_art else None,
        blood_art=Path(blood_art) if blood_art else None,
        blood_maps=Path(blood_maps) if blood_maps else None,
    )

    controllers: dict[int, list[tuple[int, bool]]] = defaultdict(list)
    for sprite in duke.sprites:
        if sprite.picnum in {2, 4}:
            controllers[sprite.sector].append((sprite.lotag, sprite.picnum == 4))

    mechanism_counts: Counter[str] = Counter()
    mechanism_records: list[dict[str, Any]] = []

    def motion_fields(sector_id: int, **extra: int) -> dict[str, int]:
        target = builder.level.sectors[sector_id]["fields"]
        values = {
            "state": 0, "busy": 0, "busy_time_a": 20, "busy_time_b": 20,
            "interruptable": 1,
            "off_ceiling_z": target["ceiling_z"], "on_ceiling_z": target["ceiling_z"],
            "off_floor_z": target["floor_z"], "on_floor_z": target["floor_z"],
        }
        if controllers.get(sector_id):
            values["rx_id"] = _channel(controllers[sector_id][0][0])
        else:
            values["trigger_push"] = 1
        values.update(extra)
        return values

    # Native Duke tagged sector motions.
    for sector_id, source in enumerate(duke.sectors):
        tag = source.lotag & 0x3FFF
        target = builder.level.sectors[sector_id]["fields"]
        if tag == 20:  # ceiling door
            current = source.ceiling_z
            possible = [duke.sectors[n].ceiling_z for n in _neighbors(duke, sector_id) if duke.sectors[n].ceiling_z < current]
            if not possible:
                continue
            target["type"] = 600
            fields = motion_fields(sector_id, on_ceiling_z=_scale(max(possible), scale), busy_time_a=10, busy_time_b=10)
            builder.set_behavior("sector", sector_id, **fields)
            mechanism_counts["ceiling-door"] += 1
            mechanism_records.append({"source_sector": sector_id, "blood_type": 600, "kind": "ceiling-door"})
        elif tag == 18:  # elevator; preserve room height at the selected stop
            current_floor = source.floor_z
            possible = [duke.sectors[n].floor_z for n in _neighbors(duke, sector_id) if duke.sectors[n].floor_z < current_floor]
            if not possible:
                continue
            target_floor = max(possible)
            delta = target_floor - source.floor_z
            target["type"] = 600
            fields = motion_fields(
                sector_id,
                on_ceiling_z=_scale(source.ceiling_z + delta, scale),
                on_floor_z=_scale(target_floor, scale),
                busy_time_a=32, busy_time_b=32,
            )
            builder.set_behavior("sector", sector_id, **fields)
            mechanism_counts["elevator"] += 1
            mechanism_records.append({"source_sector": sector_id, "blood_type": 600, "kind": "elevator"})

    # Duke SE31/SE32 store one endpoint in the effector Z and the other in the
    # authored sector surface. When angle != 1536 Duke moves to the effector
    # endpoint during map initialization, so make that Blood's explicit OFF
    # state as well.
    for source_id, sprite in enumerate(duke.sprites):
        if sprite.picnum != 1 or sprite.lotag not in {31, 32}:
            continue
        sector_id = sprite.sector
        source_sector = duke.sectors[sector_id]
        target = builder.level.sectors[sector_id]["fields"]
        target["type"] = 600
        if sprite.lotag == 32:
            authored, effector = _scale(source_sector.ceiling_z, scale), _scale(sprite.z, scale)
            off, on = (effector, authored) if sprite.angle != 1536 else (authored, effector)
            target["ceiling_z"] = off
            fields = motion_fields(
                sector_id, off_ceiling_z=off, on_ceiling_z=on,
                off_floor_z=target["floor_z"], on_floor_z=target["floor_z"],
                busy_time_a=24, busy_time_b=24,
            )
            kind = "ceiling-rise-fall"
        else:
            authored, effector = _scale(source_sector.floor_z, scale), _scale(sprite.z, scale)
            off, on = (effector, authored) if sprite.angle != 1536 else (authored, effector)
            target["floor_z"] = off
            fields = motion_fields(
                sector_id, off_floor_z=off, on_floor_z=on,
                off_ceiling_z=target["ceiling_z"], on_ceiling_z=target["ceiling_z"],
                busy_time_a=24, busy_time_b=24,
            )
            kind = "floor-rise-fall"
        builder.set_behavior("sector", sector_id, **fields)
        mechanism_counts[kind] += 1
        mechanism_records.append({"source_sector": sector_id, "source_effector": source_id, "blood_type": 600, "kind": kind})

    # Duke SE15 sliding door -> Blood two-marker horizontal slide.
    for source_id, sprite in enumerate(duke.sprites):
        if sprite.picnum != 1 or sprite.lotag != 15:
            continue
        sector_id = sprite.sector
        target = builder.level.sectors[sector_id]["fields"]
        target["type"] = 616
        x, y, z = _scaled_position(builder, sprite, scale)
        marker0 = _add_marker(builder, sector=sector_id, owner=sector_id, x=x, y=y, z=z, type=3, angle=sprite.angle)
        marker1 = _add_marker(builder, sector=sector_id, owner=sector_id, x=x, y=y, z=z, type=4, angle=sprite.angle)
        # Duke runs xrepeat/8 ticks at the SE direction; E3L11 uses angle 0.
        distance = _scale(max(128, sprite.x_repeat * 2), scale)
        builder.level.sprites[marker1]["fields"]["x"] = x + distance
        fields = motion_fields(sector_id, marker_0=marker0, marker_1=marker1, busy_time_a=24, busy_time_b=24)
        builder.set_behavior("sector", sector_id, **fields)
        mechanism_counts["sliding-door"] += 1
        mechanism_records.append({"source_sector": sector_id, "source_effector": source_id, "blood_type": 616, "kind": "sliding-door"})

    # Duke ST30/SE0 rotates 256 Build-angle units about the matching SE1 pivot.
    pivots = {sprite.hitag: sprite for sprite in duke.sprites if sprite.picnum == 1 and sprite.lotag == 1}
    rotation_groups: dict[int, set[int]] = defaultdict(set)
    for sprite in duke.sprites:
        if sprite.picnum == 1 and sprite.lotag == 0 and (duke.sectors[sprite.sector].lotag & 0x3FFF) == 30:
            rotation_groups[sprite.hitag].add(sprite.sector)
    for source_id, sprite in enumerate(duke.sprites):
        if sprite.picnum != 1 or sprite.lotag != 0 or (duke.sectors[sprite.sector].lotag & 0x3FFF) != 30:
            continue
        pivot = pivots.get(sprite.hitag)
        if pivot is None:
            continue
        sector_id = sprite.sector
        target = builder.level.sectors[sector_id]["fields"]
        target["type"] = 617
        marker = _add_marker(
            builder, sector=pivot.sector, owner=sector_id,
            x=_scale(pivot.x, scale), y=_scale(pivot.y, scale), z=_scale(pivot.z, scale),
            type=5, angle=256 if sprite.pal else -256,
        )
        activation_tag = _rotation_activation_tag(duke, rotation_groups[sprite.hitag])
        fields = motion_fields(sector_id, marker_0=marker, busy_time_a=32, busy_time_b=32)
        if activation_tag is not None:
            fields.update(trigger_push=0, rx_id=_channel(activation_tag))
        builder.set_behavior("sector", sector_id, **fields)
        mechanism_counts["rotate-bridge"] += 1
        mechanism_records.append({
            "source_sector": sector_id, "source_effector": source_id, "blood_type": 617,
            "kind": "rotate-bridge", "classification": "faithfully-convertible" if activation_tag is not None else "semantically-approximated",
            "activation_tag": activation_tag,
        })

    # Duke SE7 represents both water links and ordinary teleports. Classify the
    # complete pair first: only an ST1/ST2 pair is a Blood upper/lower link.
    se7_pairs: dict[int, list[tuple[int, Any]]] = defaultdict(list)
    for source_id, sprite in enumerate(duke.sprites):
        if sprite.picnum == 1 and sprite.lotag == 7:
            se7_pairs[sprite.hitag].append((source_id, sprite))
    water_links: Counter[int] = Counter()
    for link, pair in sorted(se7_pairs.items()):
        tags = {duke.sectors[sprite.sector].lotag & 0x3FFF for _source_id, sprite in pair}
        if len(pair) == 2 and tags == {1, 2}:
            for source_id, sprite in pair:
                sector_tag = duke.sectors[sprite.sector].lotag & 0x3FFF
                kind, tile = (9, 2332) if sector_tag == 1 else (10, 2331)
                x, y, z = _scaled_position(builder, sprite, scale)
                new_id = builder.add_sprite(
                    sector=sprite.sector, x=x, y=y, z=z,
                    type=kind, picnum=tile, status=0, angle=sprite.angle, cstat=32896,
                    x_repeat=64, y_repeat=64,
                )
                builder.set_behavior("sprite", new_id, data_1=link)
                if sector_tag == 2:
                    builder.set_behavior("sector", sprite.sector, underwater=1)
                water_links[link] += 1
                mechanism_counts["water-marker"] += 1
                mechanism_records.append({"source_sprite": source_id, "target_sprite": new_id, "kind": "upper-water" if kind == 9 else "lower-water", "link": link})
        elif len(pair) == 2:
            for (source_id, source), (_dest_id, destination) in ((pair[0], pair[1]), (pair[1], pair[0])):
                x, y, z = _scaled_position(builder, destination, scale)
                marker = _add_marker(
                    builder, sector=destination.sector, owner=source.sector,
                    x=x, y=y, z=z, type=8, angle=destination.angle,
                )
                builder.level.sprites[marker]["fields"]["picnum"] = 3193
                builder.level.sectors[source.sector]["fields"]["type"] = 604
                builder.set_behavior("sector", source.sector, marker_0=marker, trigger_enter=1)
                mechanism_counts["teleporter"] += 1
                mechanism_records.append({"source_sprite": source_id, "target_marker": marker, "source_sector": source.sector, "destination_sector": destination.sector, "kind": "teleporter", "link": link})
        else:
            raise E3L11ConversionError(f"Duke SE7 link {link} has {len(pair)} endpoints")

    # Conveyors become native Blood floor panning sectors. Tagged conveyors are
    # switchable receivers; untagged ones run continuously.
    for source_id, sprite in enumerate(duke.sprites):
        if sprite.picnum != 1 or sprite.lotag != 24:
            continue
        fields = {"pan_floor": 1, "pan_velocity": 8, "pan_angle": sprite.angle}
        if sprite.hitag:
            fields["rx_id"] = _channel(sprite.hitag)
        else:
            fields["pan_always"] = 1
        builder.set_behavior("sector", sprite.sector, **fields)
        mechanism_counts["conveyor"] += 1
        mechanism_records.append({"source_sector": sprite.sector, "source_effector": source_id, "kind": "conveyor"})

    # Trigger sectors (Duke touchplates) drive the converted user channel graph.
    for source_id, sprite in enumerate(duke.sprites):
        if sprite.picnum != 3:
            continue
        builder.set_behavior(
            "sector", sprite.sector, tx_id=_channel(sprite.lotag), command=3,
            trigger_enter=1, trigger_once=1 if sprite.hitag else 0,
        )
        mechanism_counts["touchplate"] += 1
        mechanism_records.append({"source_sprite": source_id, "source_sector": sprite.sector, "kind": "touchplate", "channel": _channel(sprite.lotag)})

    # Duke SE12 switches a tagged group of sectors between their authored dark
    # and bright states.  Blood's XSECTOR lighting effect is a native animated
    # shade operation, not a Duke shade-controller emulation.  It provides a
    # deterministic pulse on the same tag channel; the report calls out that
    # this is an approximation rather than claiming identical persistent shade.
    for source_id, sprite in enumerate(duke.sprites):
        if sprite.picnum != 1 or sprite.lotag != 12 or not sprite.hitag:
            continue
        builder.set_behavior(
            "sector", sprite.sector,
            rx_id=_channel(sprite.hitag), command=3,
            busy_time_a=18, busy_time_b=18, interruptable=1,
            amplitude=16, shade_frequency=18, shade_wave=1,
            shade_floor=1, shade_ceiling=1, shade_walls=1,
        )
        mechanism_counts["switchable-light-pulse"] += 1
        mechanism_records.append({
            "source_effector": source_id, "source_sector": sprite.sector,
            "kind": "switchable-light-pulse", "classification": "semantically-approximated",
            "channel": _channel(sprite.hitag), "blood": "XSECTOR lighting busy wave",
        })

    # Duke SE3/SE4 are autonomous random light controllers.  Blood offers the
    # equivalent class of continuous sector-light wave, though not Duke's PRNG
    # sequence.  They are deliberately marked visual-only in the report.
    for source_id, sprite in enumerate(duke.sprites):
        if sprite.picnum != 1 or sprite.lotag not in {3, 4}:
            continue
        builder.set_behavior(
            "sector", sprite.sector,
            shade_always=1, amplitude=12, shade_frequency=12, shade_wave=1,
            shade_floor=1, shade_ceiling=1, shade_walls=1,
        )
        mechanism_counts["ambient-light-flicker"] += 1
        mechanism_records.append({
            "source_effector": source_id, "source_sector": sprite.sector,
            "kind": "ambient-light-flicker", "classification": "visual-only-approximation",
            "blood": "XSECTOR continuous lighting wave",
        })

    # In EDuke32, CRACK1..4 accept qualifying damage, then signal same-hitag
    # SE13 effectors.  Blood's kWallGib is itself impact-triggered and removes
    # blocking/hitscan state; its TX channel drives a hidden Blood exploder.
    # This preserves the meaningful chain: impact -> open passage -> explosion.
    explosive_tags = {
        sprite.hitag for sprite in duke.sprites
        if sprite.picnum == 1 and sprite.lotag == 13 and sprite.hitag
    }
    for source_id, sprite in enumerate(duke.sprites):
        if sprite.picnum not in CRACK_TILES or sprite.hitag not in explosive_tags:
            continue
        wall_id = _crack_wall_target(duke, sprite)
        if wall_id is None:
            mechanism_records.append({
                "source_sprite": source_id, "kind": "destructible-wall",
                "classification": "unsupported", "reason": "no unique containing-sector wall within 8 Duke units",
            })
            continue
        channel = _channel(sprite.hitag)
        wall = builder.level.walls[wall_id]["fields"]
        wall["type"] = 511  # Blood kWallGib
        wall["cstat"] |= 65  # initially block movement and hitscan; kWallGib clears both on impact
        builder.set_behavior(
            "wall", wall_id, state=0, data=12, tx_id=channel, command=3,
            trigger_on=1, trigger_vector=1,
        )
        x, y, z = _scaled_position(builder, sprite, scale)
        explosive = builder.add_sprite(
            sector=sprite.sector, x=x, y=y, z=z, type=459, picnum=908,
            status=4, angle=sprite.angle, cstat=0, x_repeat=4, y_repeat=4,
        )
        builder.set_behavior("sprite", explosive, rx_id=channel)
        mechanism_counts["destructible-wall"] += 1
        mechanism_counts["linked-explosion"] += 1
        mechanism_records.append({
            "source_sprite": source_id, "source_wall": wall_id, "target_wall": wall_id,
            "target_exploder": explosive, "link": sprite.hitag,
            "kind": "destructible-wall", "classification": "semantically-approximated",
            "graph": "impact -> kWallGib open -> TX -> hidden exploder",
        })

    entity_counts: Counter[str] = Counter()
    entity_records: list[dict[str, Any]] = []
    omitted: Counter[int] = Counter()

    def add_gameplay_sprite(source_id: int, definition: tuple[int, int, int, int, int, str]) -> int:
        source = duke.sprites[source_id]
        type_, tile, status, cstat, repeat, classification = definition
        x, y, z = _scaled_position(builder, source, scale)
        new_id = builder.add_sprite(
            sector=source.sector, x=x, y=y, z=z,
            type=type_, picnum=tile, status=status, angle=source.angle, cstat=cstat,
            x_repeat=repeat, y_repeat=repeat, shade=0,
        )
        builder.set_behavior("sprite", new_id)
        entity_counts[classification] += 1
        entity_records.append({"source_sprite": source_id, "target_sprite": new_id, "classification": classification})
        return new_id

    for source_id, sprite in enumerate(duke.sprites):
        if sprite.picnum == 60:  # Duke access card palettes -> two Blood keys
            key_type, key_tile, key_name = (101, 2553, "eye") if sprite.pal == 21 else (100, 2552, "skull")
            add_gameplay_sprite(source_id, (key_type, key_tile, 3, 128, 32, f"equivalent:access-card->{key_name}-key"))
        elif sprite.picnum in ENTITY_MAP:
            add_gameplay_sprite(source_id, ENTITY_MAP[sprite.picnum])
        elif sprite.picnum in DUKE_CONTROLLERS or sprite.picnum in DUKE_SWITCHES or sprite.picnum == 142:
            continue
        else:
            omitted[sprite.picnum] += 1

    # Interactive switches and a guaranteed normal-level exit.
    for source_id, sprite in enumerate(duke.sprites):
        if sprite.picnum not in DUKE_SWITCHES and sprite.picnum != 142:
            continue
        if sprite.picnum == 142:
            channel, key, classification = 4, 0, "equivalent:nuke-button->normal-exit"
            command = 1
        else:
            channel, command = _channel(sprite.lotag), 3
            key = 2 if sprite.picnum == 130 and sprite.pal == 21 else 1 if sprite.picnum == 130 else 0
            classification = "equivalent:access-switch" if sprite.picnum == 130 else "equivalent:toggle-switch"
        x, y, z = _scaled_position(builder, sprite, scale)
        new_id = builder.add_sprite(
            sector=sprite.sector, x=x, y=y, z=z,
            type=20, picnum=318, status=0, angle=sprite.angle, cstat=sprite.cstat,
            x_repeat=max(16, sprite.x_repeat), y_repeat=max(16, sprite.y_repeat),
        )
        builder.set_behavior(
            "sprite", new_id, tx_id=channel, command=command, key=key,
            trigger_on=1, trigger_off=1 if command == 3 else 0, trigger_push=1,
        )
        entity_counts[classification] += 1
        entity_records.append({"source_sprite": source_id, "target_sprite": new_id, "classification": classification, "channel": channel, "key": key})

    disk = builder.level.to_disk_map()
    errors = [item for item in validate_map(disk) if item.severity == "error"]
    bad_links = sorted(tag for tag, count in water_links.items() if count != 2)
    if errors:
        raise E3L11ConversionError(f"converted map has {len(errors)} structural errors; first: {errors[0].message}")
    if bad_links:
        raise E3L11ConversionError(f"unpaired Duke water links: {bad_links}")
    progression = _static_progression(disk)
    channel_audit = _channel_audit(disk)
    if not progression["all_exits_reachable"]:
        raise E3L11ConversionError("converted map has no statically reachable Blood exit")

    semantic_inventory = analyze_duke_mechanisms(duke)
    lowered_effectors = {0, 1, 3, 4, 7, 12, 13, 15, 24, 31, 32}
    unsupported_effectors = Counter(
        sprite.lotag for sprite in duke.sprites
        if sprite.picnum == 1 and sprite.lotag not in lowered_effectors
    )
    report = {
        "$schema": "llmapper.playable-conversion-report",
        "schema_version": 1,
        "source_game": "duke3d",
        "target_game": "blood",
        "profile": "playable-duke-to-blood (E3L11 regression target)",
        "geometry": {
            "coordinate_scale": "3:2", "topology_preserved": True,
            "sectors": len(duke.sectors), "walls": len(duke.walls),
        },
        "materials": material_report,
        "mechanisms": {
            "classification": "mixed-equivalent-and-approximate",
            "counts": dict(sorted(mechanism_counts.items())),
            "records": mechanism_records,
            "semantic_inventory": semantic_inventory,
            "water_link_ids": dict(sorted(water_links.items())),
            "channel_audit": channel_audit,
            "unsupported_sector_effector_lotags": dict(sorted(unsupported_effectors.items())),
        },
        "entities": {
            "translated_counts": dict(sorted(entity_counts.items())),
            "translated": entity_records,
            "omitted_decorative_tiles": dict(sorted(omitted.items())),
        },
        "overall": {
            "structural_validity": True,
            "gameplay_fidelity": "playable approximation",
            "guaranteed_exit_channel": 4,
            "static_progression": progression,
            "limitations": [
                "Switchable lighting uses a Blood XSECTOR pulse rather than Duke's persistent shade state; random lighting uses a continuous visual approximation.",
                "CRACK1..4 groups linked to SE13 become impact-triggered Blood gib walls and hidden exploders; unresolvable crack placement remains unsupported.",
                "Earthquake, door-linked lighting, demo-camera, locator, respawn, and master-switch choreography remains explicitly unsupported or visual-only.",
                "Enemy and inventory substitutions preserve combat roles, not exact balance.",
                "ART material selection is role-aware but still needs an artistic review pass for material-family consistency.",
            ],
        },
    }
    return disk, report
