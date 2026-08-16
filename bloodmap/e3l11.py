from __future__ import annotations

from collections import Counter, defaultdict
from math import cos, pi, sin
from pathlib import Path
from typing import Any

from .analysis import validate_map
from .art import ArtError, nearest_art_tiles
from .construction import LevelBuilder, portal_profiles
from .composition import _point_in_sector, _sector_surface_z
from .conversion import DUKE_TO_BLOOD_MATERIAL_EXACT, _scale, convert_build_ir, native_scale
from .duke import DukeDiskMap
from .duke_semantics import (
    CRACK_TILES, analyze_duke_mechanisms, classify_se7_groups, gpspeed_busy_time,
    hatch_endpoint_roles,
)
from .format import read_map
from .style import corpus_parallax_tiles, load_visual_style, style_tile_usage


class PlayableConversionError(ValueError):
    pass


E3L11ConversionError = PlayableConversionError

USER_CHANNEL_MIN = 100
USER_CHANNEL_MAX = 1023
RESERVED_CHANNELS = frozenset({4})

DUKE_CONTROLLERS = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}
DUKE_SWITCHES = {130, 134, 164, 165, 166, 170}

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
    46: (73, 548, 3, 128, 24, "approximation:crystal ammo->Tesla charge"),
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
    1821: (217, 1570, 6, 384, 48, "approximation:Octabrain stay-put->Gill Beast"),
    1680: (201, 2820, 6, 384, 40, "approximation:Liztroop->Tommy cultist"),
    1682: (201, 2820, 6, 384, 40, "approximation:Liztroop stay-put->Tommy cultist"),
    1744: (201, 2820, 6, 384, 40, "approximation:Liztroop ducking->Tommy cultist"),
    1247: (400, 907, 4, 385, 64, "equivalent:SEENINE->TNT barrel"),
    1550: (218, 1870, 6, 384, 40, "approximation:shark->bone eel"),
    1920: (206, 1470, 6, 384, 40, "approximation:Commander->flesh gargoyle"),
    1960: (206, 1470, 6, 384, 40, "approximation:Recon->flesh gargoyle"),
    2631: (227, 2680, 6, 384, 64, "approximation:Battlelord->Cerberus"),
}


class ChannelAllocator:
    """Map Duke tags onto Blood user channels 100-1023.

    Small tags keep the historical ``100 + tag`` encoding used by E3L11. Tags
    that would overflow that range, or collide with a reserved/already-used
    channel, take the next free user channel. Channel 4 stays reserved for the
    Blood normal-exit TX.
    """

    def __init__(self) -> None:
        self._map: dict[int, int] = {}
        self._used: set[int] = set(RESERVED_CHANNELS)
        self._overflow = USER_CHANNEL_MIN

    def allocate(self, tag: int) -> int:
        tag = int(tag)
        existing = self._map.get(tag)
        if existing is not None:
            return existing
        candidate = USER_CHANNEL_MIN + tag
        if USER_CHANNEL_MIN <= candidate <= USER_CHANNEL_MAX and candidate not in self._used:
            self._map[tag] = candidate
            self._used.add(candidate)
            return candidate
        while self._overflow in self._used:
            self._overflow += 1
            if self._overflow > USER_CHANNEL_MAX:
                raise PlayableConversionError(f"Duke tag {tag} cannot be allocated to a Blood user channel")
        self._map[tag] = self._overflow
        self._used.add(self._overflow)
        self._overflow += 1
        return self._map[tag]


def _channel(tag: int) -> int:
    """One-shot helper for tests; playable conversion uses ChannelAllocator."""
    return ChannelAllocator().allocate(tag)


def _switch_key(sprite: Any) -> int:
    if sprite.picnum == 130:
        return 2 if sprite.pal == 21 else 1
    if sprite.picnum == 170:
        if sprite.pal == 21:
            return 2
        if sprite.pal == 23:
            return 3
        return 1
    return 0


def _neighbors(duke: DukeDiskMap, sector_id: int) -> list[int]:
    sector = duke.sectors[sector_id]
    return sorted({
        duke.walls[index].next_sector
        for index in range(sector.wall_ptr, sector.wall_ptr + sector.wall_count)
        if duke.walls[index].next_sector >= 0
    })


def _underwater_sectors(duke: DukeDiskMap, builder: LevelBuilder) -> list[int]:
    """Stack XSECTOR.Underwater onto every Blood record that needs swim physics.

    DNE3L11, a partial 3:2 conversion of E3L11, sets underwater on every Duke
    ST2 sector — including SE13 holes that are also type-600. DWE1M1 authors
    type-600 doors that sit in a water volume with Push+Wallpush still set.
    Blood XSECTOR flags combine; a sector type does not replace underwater.
    """
    st2 = {
        index for index, sector in enumerate(duke.sectors)
        if (sector.lotag & 0x3FFF) == 2
    }
    submerged = set(st2)
    for sector_id, target in enumerate(builder.level.sectors):
        if target["fields"]["type"] not in {600, 616, 617, 604}:
            continue
        if any(neighbor in st2 for neighbor in _neighbors(duke, sector_id)):
            submerged.add(sector_id)
    return sorted(submerged)


def _crack_cstat(cstat: int) -> int:
    """Wall-aligned, hittable Blood crack. NBlood VectorScan requires hitscan-block."""
    return (int(cstat) | 1 | 16 | 256) & ~32768


def _surface_candidates(blood_maps: Path) -> dict[str, set[int]]:
    """Corpus-backed candidates separated by authored surface role.

    A ceiling light or a floor material may be close in raw ART feature space to
    a wall texture, but that is normally a worse conversion.  Keep each role's
    candidate family distinct before doing the visual match.
    """
    result: dict[str, set[int]] = {"ceiling": set(), "floor": set(), "wall": set(), "sky": set()}
    paths = sorted({path.resolve() for path in blood_maps.glob("*.MAP")} | {path.resolve() for path in blood_maps.glob("*.map")})
    for path in paths:
        disk = read_map(path)
        for sector in disk.sectors:
            if sector.ceiling_stat & 1:
                result["sky"].add(sector.ceiling_picnum)
            else:
                result["ceiling"].add(sector.ceiling_picnum)
            result["floor"].add(sector.floor_picnum)
        result["wall"].update(wall.picnum for wall in disk.walls)
        result["wall"].update(wall.over_picnum for wall in disk.walls if wall.over_picnum)
    return {
        role: {value for value in candidates if 0 < value < 4096}
        for role, candidates in result.items()
    }


def _clamp_shade(value: int) -> int:
    return max(-128, min(127, int(value)))


def _apply_style_atmosphere(builder: LevelBuilder, style: dict[str, Any]) -> None:
    header = style["header"]
    builder.level.metadata["visibility"] = int(header["visibility"])
    builder.level.metadata["sky_type"] = int(header["sky_type"])
    bits = int(header["sky_bits"])
    offsets = [int(value) for value in header["sky_offsets"]]
    expected = 1 << bits
    if len(offsets) < expected:
        offsets = offsets + [0] * (expected - len(offsets))
    builder.level.sky = {"bits": bits, "offsets": offsets[:expected]}


def _apply_materials(
    duke: DukeDiskMap,
    builder: LevelBuilder,
    *,
    duke_art: Path | None,
    blood_art: Path | None,
    blood_maps: Path | None,
    style: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_tiles = {
        "ceiling": {sector.ceiling_picnum for sector in duke.sectors if not (sector.ceiling_stat & 1)},
        "floor": {sector.floor_picnum for sector in duke.sectors},
        "wall": {wall.picnum for wall in duke.walls} | {wall.over_picnum for wall in duke.walls if wall.over_picnum},
        "sky": {sector.ceiling_picnum for sector in duke.sectors if sector.ceiling_stat & 1},
    }
    matches: dict[str, dict[int, dict[str, float | int]]] = {role: {} for role in source_tiles}
    candidate_weights: dict[str, dict[int, int]] = {role: {} for role in source_tiles}
    engine = "role-default"
    warning = None
    if duke_art and blood_art and (blood_maps or style):
        try:
            if style:
                for role in ("ceiling", "floor", "wall", "sky"):
                    candidate_weights[role] = {
                        int(tile): int(count) for tile, count in style["candidates"].get(role, {}).items()
                    }
                if blood_maps:
                    candidate_weights["sky"] = {
                        **candidate_weights["sky"],
                        **corpus_parallax_tiles(blood_maps),
                    }
                candidates = {role: set(weights) for role, weights in candidate_weights.items()}
                engine = "style-constrained ART nearest-neighbour; indoor tiles from the Blood style map, parallax from corpus sky tiles"
            else:
                candidates = _surface_candidates(blood_maps)
                engine = "role-aware ART palette/spatial nearest-neighbour over corpus ceiling, floor, wall, and parallax families"
            palette_root = blood_art / "xmapedit" / "palettes" / "import"
            for role, source in source_tiles.items():
                if not source or not candidates.get(role):
                    continue
                matches[role] = nearest_art_tiles(
                    source,
                    candidates[role],
                    source_art=duke_art,
                    target_art=blood_art,
                    source_palette=palette_root / "DUKE3D.PAL",
                    target_palette=palette_root / "BLOOD.PAL",
                    target_weights=candidate_weights[role] or None,
                )
        except (ArtError, OSError, ValueError) as exc:
            warning = str(exc)
            engine = "role-default"
    decisions: Counter[str] = Counter()
    prefer_style = style is not None

    def material(tile: int, fallback: int, role: str) -> int:
        if prefer_style and tile in matches[role]:
            decisions["style+visual-match"] += 1
            return int(matches[role][tile]["blood_tile"])
        if tile in DUKE_TO_BLOOD_MATERIAL_EXACT:
            decisions["known/manual-mapping"] += 1
            return DUKE_TO_BLOOD_MATERIAL_EXACT[tile]
        if tile in matches[role]:
            decisions["semantic+visual-match"] += 1
            return int(matches[role][tile]["blood_tile"])
        decisions["unmapped-role-default"] += 1
        return fallback

    def finish_surface(target: dict[str, Any], role: str, chosen: int, *, pal_key: str, shade_key: str, skip_shade: bool = False) -> None:
        usage = style_tile_usage(style, role, chosen) if style else None
        if usage and usage["pal_support"] >= 3:
            target[pal_key] = usage["pal"]
            decisions["style-palette"] += 1
        if skip_shade:
            return
        converted = int(target[shade_key])
        if usage and usage["shade_support"] >= 3:
            target[shade_key] = _clamp_shade(round(0.35 * converted + 0.65 * usage["shade"]))
            decisions["style-shade"] += 1
        elif style:
            source_mean = mean_shades[role]
            style_mean = float(style["shades"][role if role != "sky" else "ceiling"]["mean"])
            offset = max(0, min(48, int(round(style_mean - 2 * source_mean))))
            target[shade_key] = _clamp_shade(converted + offset)
            decisions["style-shade-offset"] += 1

    mean_shades = {
        "ceiling": _mean_shade(sector.ceiling_shade for sector in duke.sectors if not (sector.ceiling_stat & 1)),
        "floor": _mean_shade(sector.floor_shade for sector in duke.sectors),
        "wall": _mean_shade(wall.shade for wall in duke.walls),
        "sky": _mean_shade(sector.ceiling_shade for sector in duke.sectors if sector.ceiling_stat & 1),
    }

    for index, source in enumerate(duke.sectors):
        target = builder.level.sectors[index]["fields"]
        sky = bool(source.ceiling_stat & 1)
        ceiling_role = "sky" if sky else "ceiling"
        target["ceiling_picnum"] = material(source.ceiling_picnum, 385 if not sky else 2500, ceiling_role)
        target["floor_picnum"] = material(source.floor_picnum, 292, "floor")
        finish_surface(target, ceiling_role, target["ceiling_picnum"], pal_key="ceiling_pal", shade_key="ceiling_shade", skip_shade=sky)
        finish_surface(target, "floor", target["floor_picnum"], pal_key="floor_pal", shade_key="floor_shade")
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
        finish_surface(target, "wall", target["picnum"], pal_key="pal", shade_key="shade")
    tile_matches = {
        role: {
            str(tile): (
                ({**matches[role][tile], "classification": "style+visual-match"} if prefer_style and tile in matches[role] else
                 {"blood_tile": DUKE_TO_BLOOD_MATERIAL_EXACT[tile], "classification": "known/manual-mapping"}
                 if tile in DUKE_TO_BLOOD_MATERIAL_EXACT else
                 ({**matches[role][tile], "classification": "semantic+visual-match"} if tile in matches[role] else
                  {"blood_tile": None, "classification": "unmapped"}))
            )
            for tile in sorted(tiles)
        }
        for role, tiles in source_tiles.items()
    }
    return {
        "classification": "style-approximation" if style else "approximation",
        "engine": engine,
        "style_source": None if style is None else style.get("source"),
        "decisions": dict(sorted(decisions.items())),
        "unique_source_tiles": len(set().union(*source_tiles.values())),
        "matched_tiles": sum(len(value) for value in matches.values()),
        "tile_matches": tile_matches,
        "warning": warning,
    }


def _mean_shade(values) -> float:
    ordinary = [int(value) for value in values if int(value) > -100]
    if not ordinary:
        return 0.0
    return sum(ordinary) / len(ordinary)


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


def _nudge_into_sector(builder: LevelBuilder, sector_id: int, x: int, y: int) -> tuple[int, int]:
    """Pull a wall-aligned sprite inside its sector after 3:2 rounding."""
    if _point_in_sector(builder.level, sector_id, (x, y)) != 0:
        return x, y
    sector = builder.level.sectors[sector_id]["fields"]
    xs, ys = [], []
    for wall_id in range(int(sector["wall_ptr"]), int(sector["wall_ptr"]) + int(sector["wall_count"])):
        wall = builder.level.walls[wall_id]["fields"]
        xs.append(int(wall["x"]))
        ys.append(int(wall["y"]))
    if not xs:
        return x, y
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    for step in range(1, 17):
        nx = int(round(x + (cx - x) * step / 16))
        ny = int(round(y + (cy - y) * step / 16))
        if _point_in_sector(builder.level, sector_id, (nx, ny)) != 0:
            return nx, ny
    return x, y


def _scaled_position(builder: LevelBuilder, source: Any, scale: Any) -> tuple[int, int, int]:
    x, y, z = _scale(source.x, scale), _scale(source.y, scale), _scale(source.z, scale)
    x, y = _nudge_into_sector(builder, source.sector, x, y)
    ceiling = _sector_surface_z(builder.level, source.sector, x, y, "ceiling")
    floor = _sector_surface_z(builder.level, source.sector, x, y, "floor")
    return x, y, max(ceiling, min(floor, z))


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
        if sprite.type in {6, 7, 9, 10, 11, 12} and sprite.extra is not None:
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
        "model": "reciprocal portals open at configured endpoints plus paired water, stack/link, and teleports",
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
    style_map: str | Path | None = None,
) -> tuple[Any, dict[str, Any]]:
    scale = native_scale("duke3d", "blood")
    geometry, _base_report = convert_build_ir(duke.to_build_ir(), "blood", policy="geometry-only")
    builder = LevelBuilder(geometry.to_level_ir())
    style = load_visual_style(str(style_map)) if style_map else None
    if style:
        _apply_style_atmosphere(builder, style)
    material_report = _apply_materials(
        duke, builder,
        duke_art=Path(duke_art) if duke_art else None,
        blood_art=Path(blood_art) if blood_art else None,
        blood_maps=Path(blood_maps) if blood_maps else None,
        style=style,
    )

    controllers: dict[int, list[tuple[int, bool]]] = defaultdict(list)
    for sprite in duke.sprites:
        if sprite.picnum in {2, 4}:
            controllers[sprite.sector].append((sprite.lotag, sprite.picnum == 4))

    mechanism_counts: Counter[str] = Counter()
    mechanism_records: list[dict[str, Any]] = []
    channels = ChannelAllocator()

    def motion_fields(sector_id: int, **extra: int) -> dict[str, int]:
        target = builder.level.sectors[sector_id]["fields"]
        values = {
            "state": 0, "busy": 0, "busy_time_a": 20, "busy_time_b": 20,
            "interruptable": 0,
            "off_ceiling_z": target["ceiling_z"], "on_ceiling_z": target["ceiling_z"],
            "off_floor_z": target["floor_z"], "on_floor_z": target["floor_z"],
        }
        if controllers.get(sector_id):
            values["rx_id"] = channels.allocate(controllers[sector_id][0][0])
            values["trigger_push"] = 0
            values["trigger_wall_push"] = 0
        else:
            # NBlood ActionScan: XSECTOR.Push fires only if the player is in the
            # sector or hits its floor/ceiling. Closed Z-doors are used from the
            # adjacent room by hitting the portal wall, which requires Wallpush.
            # DNE3L1 authors both bits on unbuttoned type-600 doors.
            values["trigger_push"] = 1
            values["trigger_wall_push"] = 1
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
            busy = gpspeed_busy_time(duke, sector_id, 10)
            fields = motion_fields(sector_id, on_ceiling_z=_scale(max(possible), scale), busy_time_a=busy, busy_time_b=busy)
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
            busy = gpspeed_busy_time(duke, sector_id, 32)
            fields = motion_fields(
                sector_id,
                on_ceiling_z=_scale(source.ceiling_z + delta, scale),
                on_floor_z=_scale(target_floor, scale),
                busy_time_a=busy, busy_time_b=busy,
            )
            builder.set_behavior("sector", sector_id, **fields)
            mechanism_counts["elevator"] += 1
            mechanism_records.append({"source_sector": sector_id, "blood_type": 600, "kind": "elevator"})
        elif tag == 16:  # ST16 platform: floor seeks the nearest neighbor floor.
            current = source.floor_z
            neighbor_floors = [duke.sectors[n].floor_z for n in _neighbors(duke, sector_id)]
            down = [z for z in neighbor_floors if z > current]
            up = [z for z in neighbor_floors if z < current]
            if down:
                target_floor = min(down)
            elif up:
                target_floor = max(up)
            else:
                continue
            target["type"] = 600
            busy = gpspeed_busy_time(duke, sector_id, 24)
            fields = motion_fields(
                sector_id, on_floor_z=_scale(target_floor, scale),
                busy_time_a=busy, busy_time_b=busy,
            )
            builder.set_behavior("sector", sector_id, **fields)
            mechanism_counts["platform"] += 1
            mechanism_records.append({
                "source_sector": sector_id, "blood_type": 600, "kind": "platform",
                "classification": "faithfully-convertible",
            })
        elif tag == 22:  # ST22 splitting door: both surfaces meet, then reopen to neighbors.
            neighbors = _neighbors(duke, sector_id)
            if not neighbors:
                continue
            open_ceiling = min(duke.sectors[n].ceiling_z for n in neighbors)
            open_floor = max(duke.sectors[n].floor_z for n in neighbors)
            collapsed = abs(source.ceiling_z - source.floor_z) <= 256
            if collapsed:
                on_ceiling, on_floor = open_ceiling, open_floor
            else:
                midpoint = (source.ceiling_z + source.floor_z) // 2
                on_ceiling = on_floor = midpoint
            target["type"] = 600
            busy = gpspeed_busy_time(duke, sector_id, 16)
            fields = motion_fields(
                sector_id,
                on_ceiling_z=_scale(on_ceiling, scale),
                on_floor_z=_scale(on_floor, scale),
                busy_time_a=busy, busy_time_b=busy,
            )
            builder.set_behavior("sector", sector_id, **fields)
            mechanism_counts["splitting-door"] += 1
            mechanism_records.append({
                "source_sector": sector_id, "blood_type": 600, "kind": "splitting-door",
                "classification": "faithfully-convertible", "starts_closed": collapsed,
            })

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
        # EDuke32 A_MoveSector: xvel=16 for xrepeat>>3 ticks along the SE angle.
        distance = _scale(max(128, sprite.x_repeat * 2), scale)
        radians = sprite.angle * pi / 1024.0
        builder.level.sprites[marker1]["fields"]["x"] = x + int(round(distance * cos(radians)))
        builder.level.sprites[marker1]["fields"]["y"] = y + int(round(distance * sin(radians)))
        busy = gpspeed_busy_time(duke, sector_id, 24)
        fields = motion_fields(sector_id, marker_0=marker0, marker_1=marker1, busy_time_a=busy, busy_time_b=busy)
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
        busy = gpspeed_busy_time(duke, sector_id, 32)
        fields = motion_fields(sector_id, marker_0=marker, busy_time_a=busy, busy_time_b=busy)
        if activation_tag is not None:
            fields.update(trigger_push=0, trigger_wall_push=0, rx_id=channels.allocate(activation_tag))
        builder.set_behavior("sector", sector_id, **fields)
        mechanism_counts["rotate-bridge"] += 1
        mechanism_records.append({
            "source_sector": sector_id, "source_effector": source_id, "blood_type": 617,
            "kind": "rotate-bridge", "classification": "faithfully-convertible" if activation_tag is not None else "semantically-approximated",
            "activation_tag": activation_tag,
        })

    # SE11 swinging doors pivot about the effector itself (EDuke32 stores wall
    # origins relative to the SE). DNE3L3 lowers the same ST23 pair as type 617.
    for source_id, sprite in enumerate(duke.sprites):
        if sprite.picnum != 1 or sprite.lotag != 11:
            continue
        sector_id = sprite.sector
        target = builder.level.sectors[sector_id]["fields"]
        target["type"] = 617
        x, y, z = _scaled_position(builder, sprite, scale)
        marker = _add_marker(
            builder, sector=sector_id, owner=sector_id, x=x, y=y, z=z,
            type=5, angle=256 if sprite.angle <= 1024 else -256,
        )
        busy = gpspeed_busy_time(duke, sector_id, 24)
        fields = motion_fields(sector_id, marker_0=marker, busy_time_a=busy, busy_time_b=busy)
        builder.set_behavior("sector", sector_id, **fields)
        mechanism_counts["swinging-door"] += 1
        mechanism_records.append({
            "source_sector": sector_id, "source_effector": source_id, "blood_type": 617,
            "kind": "swinging-door", "classification": "faithfully-convertible",
        })

    # SE20 stretch-bridge: Blood type 616 two-marker slide along the SE angle.
    # DNE3L3 used marked-slide 614 for the rebuilt geometry; whole-sector 616 is
    # the closest native lowering of Duke's moving stretch sector.
    for source_id, sprite in enumerate(duke.sprites):
        if sprite.picnum != 1 or sprite.lotag != 20:
            continue
        sector_id = sprite.sector
        target = builder.level.sectors[sector_id]["fields"]
        target["type"] = 616
        x, y, z = _scaled_position(builder, sprite, scale)
        marker0 = _add_marker(builder, sector=sector_id, owner=sector_id, x=x, y=y, z=z, type=3, angle=sprite.angle)
        marker1 = _add_marker(builder, sector=sector_id, owner=sector_id, x=x, y=y, z=z, type=4, angle=sprite.angle)
        distance = _scale(max(128, sprite.x_repeat * 2), scale)
        radians = sprite.angle * pi / 1024.0
        builder.level.sprites[marker1]["fields"]["x"] = x + int(round(distance * cos(radians)))
        builder.level.sprites[marker1]["fields"]["y"] = y + int(round(distance * sin(radians)))
        busy = gpspeed_busy_time(duke, sector_id, 24)
        extra: dict[str, int] = {"marker_0": marker0, "marker_1": marker1, "busy_time_a": busy, "busy_time_b": busy}
        if sprite.hitag:
            extra.update(trigger_push=0, trigger_wall_push=0, rx_id=channels.allocate(sprite.hitag))
        fields = motion_fields(sector_id, **extra)
        builder.set_behavior("sector", sector_id, **fields)
        mechanism_counts["stretch-bridge"] += 1
        mechanism_records.append({
            "source_sector": sector_id, "source_effector": source_id, "blood_type": 616,
            "kind": "stretch-bridge", "classification": "semantically-approximated",
        })

    # SE10 is an autoclose timer on the host door sector, not a tag channel.
    for source_id, sprite in enumerate(duke.sprites):
        if sprite.picnum != 1 or sprite.lotag != 10:
            continue
        wait = max(1, min(60, int(sprite.hitag) if sprite.hitag else 20))
        builder.set_behavior(
            "sector", sprite.sector,
            wait_time_a=wait, retrigger_a=1,
        )
        mechanism_counts["door-autoclose"] += 1
        mechanism_records.append({
            "source_sector": sprite.sector, "source_effector": source_id,
            "kind": "door-autoclose", "classification": "semantically-approximated",
            "wait_time": wait,
        })

    # Duke SE7 is three different runtime machines depending on sector lotag
    # and ONFLOORZ (sprite.z == sector.floorz at spawn).
    se7_groups = classify_se7_groups(duke)
    water_links: Counter[int] = Counter()
    hatch_links: Counter[int] = Counter()
    for link, group in sorted(se7_groups.items()):
        pair = [
            (endpoint["source_sprite"], duke.sprites[endpoint["source_sprite"]])
            for endpoint in group["endpoints"]
        ]
        if group["kind"] == "water_link":
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
        elif group["kind"] == "floor_teleport":
            for (source_id, source), (_dest_id, destination) in ((pair[0], pair[1]), (pair[1], pair[0])):
                x, y, z = _scaled_position(builder, destination, scale)
                marker = _add_marker(
                    builder, sector=destination.sector, owner=source.sector,
                    x=x, y=y, z=z, type=8, angle=destination.angle,
                )
                builder.level.sprites[marker]["fields"]["picnum"] = 3193
                builder.level.sectors[source.sector]["fields"]["type"] = 604
                builder.set_behavior(
                    "sector", source.sector,
                    marker_0=marker, trigger_enter=1, dude_lockout=1, data=0,
                )
                mechanism_counts["teleporter"] += 1
                mechanism_records.append({"source_sprite": source_id, "target_marker": marker, "source_sector": source.sector, "destination_sector": destination.sector, "kind": "teleporter", "link": link})
        elif group["kind"] == "air_hatch":
            # Silent relative teleport when the SE is off the floor. Blood type
            # 604 fires on sector enter; hatches need stack (congruent ROR) or
            # physical room-link instead.
            roles = hatch_endpoint_roles(duke, group["endpoints"])
            upper_type, lower_type = (11, 12) if group["congruent"] else (7, 6)
            for (source_id, sprite), role in zip(pair, roles):
                kind, tile = (upper_type, 2332) if role == "upper" else (lower_type, 2331)
                x, y, z = _scaled_position(builder, sprite, scale)
                new_id = builder.add_sprite(
                    sector=sprite.sector, x=x, y=y, z=z,
                    type=kind, picnum=tile, status=0, angle=sprite.angle, cstat=128,
                    x_repeat=64, y_repeat=64,
                )
                builder.set_behavior("sprite", new_id, data_1=link)
                hatch_links[link] += 1
                mechanism_counts["hatch-marker"] += 1
                mechanism_records.append({
                    "source_sprite": source_id, "target_sprite": new_id,
                    "kind": "upper-stack" if kind == 11 else "lower-stack" if kind == 12 else "upper-link" if kind == 7 else "lower-link",
                    "link": link, "classification": group["classification"],
                })
        else:
            raise E3L11ConversionError(f"Duke SE7 link {link} has {len(pair)} endpoints")

    # SE17 warp elevator: the cabin moves, then teleports to the matching SE17.
    # Blood type 604 already warps on sector enter; that is the playable
    # lowering of the teleport half. Cabin Z-motion is not reproduced.
    warp_elevators: dict[int, list[tuple[int, Any]]] = defaultdict(list)
    for source_id, sprite in enumerate(duke.sprites):
        if sprite.picnum == 1 and sprite.lotag == 17:
            warp_elevators[int(sprite.hitag)].append((source_id, sprite))
    for link, pair in sorted(warp_elevators.items()):
        if len(pair) != 2:
            continue
        for (source_id, source), (_dest_id, destination) in ((pair[0], pair[1]), (pair[1], pair[0])):
            x, y, z = _scaled_position(builder, destination, scale)
            marker = _add_marker(
                builder, sector=destination.sector, owner=source.sector,
                x=x, y=y, z=z, type=8, angle=destination.angle,
            )
            builder.level.sprites[marker]["fields"]["picnum"] = 3193
            builder.level.sectors[source.sector]["fields"]["type"] = 604
            builder.set_behavior(
                "sector", source.sector,
                marker_0=marker, trigger_enter=1, dude_lockout=1, data=0,
            )
            mechanism_counts["warp-elevator"] += 1
            mechanism_records.append({
                "source_sprite": source_id, "target_marker": marker,
                "source_sector": source.sector, "destination_sector": destination.sector,
                "kind": "warp-elevator", "link": link,
                "classification": "semantically-approximated",
            })

    # Conveyors become native Blood floor panning sectors. Tagged conveyors are
    # switchable receivers; untagged ones run continuously.
    for source_id, sprite in enumerate(duke.sprites):
        if sprite.picnum != 1 or sprite.lotag != 24:
            continue
        fields = {"pan_floor": 1, "pan_velocity": 8, "pan_angle": sprite.angle}
        if sprite.hitag:
            fields["rx_id"] = channels.allocate(sprite.hitag)
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
            "sector", sprite.sector, tx_id=channels.allocate(sprite.lotag), command=3,
            trigger_enter=1, trigger_once=1 if sprite.hitag else 0,
        )
        mechanism_counts["touchplate"] += 1
        mechanism_records.append({"source_sprite": source_id, "source_sector": sprite.sector, "kind": "touchplate", "channel": channels.allocate(sprite.lotag)})

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
            rx_id=channels.allocate(sprite.hitag), command=3,
            busy_time_a=18, busy_time_b=18, interruptable=1,
            amplitude=16, shade_frequency=18, shade_wave=1,
            shade_floor=1, shade_ceiling=1, shade_walls=1,
        )
        mechanism_counts["switchable-light-pulse"] += 1
        mechanism_records.append({
            "source_effector": source_id, "source_sector": sprite.sector,
            "kind": "switchable-light-pulse", "classification": "semantically-approximated",
            "channel": channels.allocate(sprite.hitag), "blood": "XSECTOR lighting busy wave",
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

    # Duke CYCLER sprites are sector lighting controllers, the same class as SE4.
    for source_id, sprite in enumerate(duke.sprites):
        if sprite.picnum != 7:
            continue
        builder.set_behavior(
            "sector", sprite.sector,
            shade_always=1, amplitude=12, shade_frequency=12, shade_wave=1,
            shade_floor=1, shade_ceiling=1, shade_walls=1,
        )
        mechanism_counts["ambient-light-flicker"] += 1
        mechanism_records.append({
            "source_sprite": source_id, "source_sector": sprite.sector,
            "kind": "cycler-light", "classification": "visual-only-approximation",
            "blood": "XSECTOR continuous lighting wave",
        })

    # SE13 collapses its sector to the effector Z at spawn, then expands back
    # to the authored surfaces when a same-hitag CRACK detonates. Blood's
    # equivalent is type-600 Z-motion starting collapsed, fired by a shootable
    # kThingWallCrack, plus a hidden kTrapExploder on the same RX channel.
    # Keep authored Z until sprites are placed; sloped holes invert at some XY
    # once both surfaces occupy the effector Z.
    explosive_snaps: list[tuple[int, int, int, bool]] = []
    for source_id, sprite in enumerate(duke.sprites):
        if sprite.picnum != 1 or sprite.lotag != 13:
            continue
        sector_id = sprite.sector
        source_sector = duke.sectors[sector_id]
        target = builder.level.sectors[sector_id]["fields"]
        authored_ceiling = _scale(source_sector.ceiling_z, scale)
        authored_floor = _scale(source_sector.floor_z, scale)
        effector = max(authored_ceiling, min(authored_floor, _scale(sprite.z, scale)))
        closer_to_ceiling = abs(source_sector.ceiling_z - sprite.z) < abs(source_sector.floor_z - sprite.z)
        if sprite.angle == 512:
            if closer_to_ceiling:
                off_ceiling, on_ceiling = effector, authored_ceiling
                off_floor, on_floor = authored_floor, authored_floor
            else:
                off_ceiling, on_ceiling = authored_ceiling, authored_ceiling
                off_floor, on_floor = effector, authored_floor
        else:
            off_ceiling = off_floor = effector
            on_ceiling, on_floor = authored_ceiling, authored_floor
        target["type"] = 600
        fields = motion_fields(
            sector_id,
            off_ceiling_z=off_ceiling, on_ceiling_z=on_ceiling,
            off_floor_z=off_floor, on_floor_z=on_floor,
            busy_time_a=8, busy_time_b=8,
            trigger_push=0, trigger_wall_push=0, rx_id=channels.allocate(sprite.hitag),
        )
        builder.set_behavior("sector", sector_id, **fields)
        explosive_snaps.append((sector_id, off_ceiling, off_floor, sprite.angle != 512))
        mechanism_counts["explosive-z-sector"] += 1
        mechanism_records.append({
            "source_sector": sector_id, "source_effector": source_id,
            "blood_type": 600, "kind": "explosive-z-sector",
            "link": sprite.hitag, "single_surface": sprite.angle == 512,
        })

    explosive_tags = {
        sprite.hitag for sprite in duke.sprites
        if sprite.picnum == 1 and sprite.lotag == 13 and sprite.hitag
    }
    for source_id, sprite in enumerate(duke.sprites):
        if sprite.picnum not in CRACK_TILES or sprite.hitag not in explosive_tags:
            continue
        channel = channels.allocate(sprite.hitag)
        x, y, z = _scaled_position(builder, sprite, scale)
        crack = builder.add_sprite(
            sector=sprite.sector, x=x, y=y, z=z, type=408, picnum=1127,
            status=4, angle=sprite.angle, cstat=_crack_cstat(sprite.cstat),
            x_repeat=max(16, sprite.x_repeat), y_repeat=max(16, sprite.y_repeat),
        )
        # thingInfo[kThingWallCrack] has 0 bullet damage. NBlood actFireVector
        # only fires the sprite command when XSPRITE.Vector is set; Impact
        # covers nearby TNT (E3L11 SEENINE on the same hitag as SE13).
        builder.set_behavior(
            "sprite", crack, tx_id=channel, command=1, state=1,
            trigger_on=1, trigger_off=1, trigger_vector=1, trigger_impact=1,
        )
        explosive = builder.add_sprite(
            sector=sprite.sector, x=x, y=y, z=z, type=459, picnum=908,
            status=11, angle=sprite.angle, cstat=32896, x_repeat=4, y_repeat=4,
        )
        builder.set_behavior("sprite", explosive, rx_id=channel, wait_time=1)
        mechanism_counts["destructible-wall"] += 1
        mechanism_counts["linked-explosion"] += 1
        mechanism_records.append({
            "source_sprite": source_id, "target_crack": crack,
            "target_exploder": explosive, "link": sprite.hitag,
            "kind": "destructible-wall", "classification": "semantically-approximated",
            "graph": "impact -> kThingWallCrack TX -> type 600 expand + kTrapExploder",
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
            channel, command = channels.allocate(sprite.lotag), 3
            key = _switch_key(sprite)
            classification = (
                "equivalent:access-switch" if sprite.picnum in {130, 170} else "equivalent:toggle-switch"
            )
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

    underwater_sectors = _underwater_sectors(duke, builder)
    for sector_id in underwater_sectors:
        builder.set_behavior("sector", sector_id, underwater=1)
    mechanism_counts["underwater-sector"] = len(underwater_sectors)

    for sector_id, off_ceiling, off_floor, flatten in explosive_snaps:
        target = builder.level.sectors[sector_id]["fields"]
        target["ceiling_z"] = off_ceiling
        target["floor_z"] = off_floor
        if flatten:
            target["ceiling_stat"] = int(target.get("ceiling_stat", 0)) & ~2
            target["floor_stat"] = int(target.get("floor_stat", 0)) & ~2

    disk = builder.level.to_disk_map()
    errors = [item for item in validate_map(disk) if item.severity == "error"]
    bad_links = sorted(tag for tag, count in water_links.items() if count != 2)
    bad_hatches = sorted(tag for tag, count in hatch_links.items() if count != 2)
    if errors:
        raise E3L11ConversionError(f"converted map has {len(errors)} structural errors; first: {errors[0].message}")
    if bad_links:
        raise E3L11ConversionError(f"unpaired Duke water links: {bad_links}")
    if bad_hatches:
        raise E3L11ConversionError(f"unpaired Duke air-hatch links: {bad_hatches}")
    progression = _static_progression(disk)
    channel_audit = _channel_audit(disk)
    if not progression["all_exits_reachable"]:
        raise E3L11ConversionError("converted map has no statically reachable Blood exit")

    semantic_inventory = analyze_duke_mechanisms(duke)
    lowered_effectors = {0, 1, 3, 4, 7, 10, 11, 12, 13, 15, 17, 20, 24, 31, 32}
    unsupported_effectors = Counter(
        sprite.lotag for sprite in duke.sprites
        if sprite.picnum == 1 and sprite.lotag not in lowered_effectors
    )
    report = {
        "$schema": "llmapper.playable-conversion-report",
        "schema_version": 1,
        "source_game": "duke3d",
        "target_game": "blood",
        "profile": "playable-duke-to-blood",
        "geometry": {
            "coordinate_scale": "3:2", "topology_preserved": True,
            "sectors": len(duke.sectors), "walls": len(duke.walls),
        },
        "materials": material_report,
        "style": None if style is None else {
            "source": style.get("source"),
            "classification": style["classification"],
            "visibility": style["header"]["visibility"],
            "sky_bits": style["header"]["sky_bits"],
        },
        "mechanisms": {
            "classification": "mixed-equivalent-and-approximate",
            "counts": dict(sorted(mechanism_counts.items())),
            "records": mechanism_records,
            "semantic_inventory": semantic_inventory,
            "water_link_ids": dict(sorted(water_links.items())),
            "hatch_link_ids": dict(sorted(hatch_links.items())),
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
                "CRACK1..4 groups linked to SE13 become shootable Blood wall-crack things (Vector+Impact, hitscan-block cstat) that TX collapsed type-600 sectors and hidden exploders; the hole is Z-expansion, not a gibbed wall.",
                "Duke ST2 sectors keep XSECTOR.Underwater even when they are also type-600 holes or neighbor a Z-door; Blood stacks those flags on one extra record.",
                "Air-hatch SE7 pairs become Blood stack or room-link markers; floor-standing SE7 pairs remain type-604 teleports. Congruent copies use stack, otherwise physical link.",
                "Unbuttoned Z-motion is armed with XSECTOR Push and Wallpush; buttoned motion is RX-only. SE10 autoclose is wait_time_a plus retrigger_a.",
                "SE11 swinging doors become type-617 rotations about the effector; SE20 stretch bridges become type-616 slides.",
                "SE17 warp elevators become type-604 teleports between cabins; the moving-cabin Z animation is not reproduced. ST16 platforms and ST22 splitting doors become type-600 Z-motion. Type-604 pads set dudeLockout so only the player fires enter/TeleFrag.",
                "Earthquake, door-linked lighting, demo-camera, locator, respawn, subway, and master-switch choreography remains explicitly unsupported or visual-only.",
                "Enemy and inventory substitutions preserve combat roles, not exact balance.",
                "ART material selection is role-aware. A Blood style map, when supplied, constrains indoor tiles and tile+pal+shade bundles to that map's vocabulary; parallax skies still match corpus parallax tiles.",
            ],
        },
    }
    return disk, report


convert_playable_duke_to_blood = convert_e3l11_to_blood
