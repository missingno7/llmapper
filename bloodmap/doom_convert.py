"""Doom → Blood lowering.

Native Doom is recognized as semantic mechanisms, then lowered through
Blood LevelIR construction. Geometry does not pass through BuildIR as a
fake universal format.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from math import hypot
from typing import Any

from .analysis import validate_map
from .construction import ConstructionError, LevelBuilder, new_level
from .doom import DoomDiskMap, DoomLinedef, texture_label
from .doom_geometry import lower_doom_geometry, scale_angle, scale_xy, scale_z
from .doom_semantics import (
    KEY_COLORS, LINEDEF_SPECIALS, analyze_doom_mechanisms, containing_sector,
    doom_to_semantic_level, special_targets,
)
from .mechanisms import Representability, SemanticLevel, solve_progression
from .model import LevelIR


class DoomConversionError(ValueError):
    pass


USER_CHANNEL_MIN = 100
RESERVED_CHANNELS = frozenset({4})

# Role-aware Blood tiles from existing construction / E3L11 corpus defaults.
ROLE_TILES = {
    "wall": 180,
    "door": 104,
    "trim": 181,
    "floor": 292,
    "ceiling": 385,
    "hazard": 278,
    "sky": 0,
    "switch": 1070,
}
SKY_FLATS = {"F_SKY1", "F_SKY2", "F_SKY3", "F_SKY4"}
HAZARD_FLATS = {"NUKAGE1", "NUKAGE2", "NUKAGE3", "LAVA1", "LAVA2", "LAVA3", "LAVA4", "BLOOD1", "BLOOD2", "BLOOD3", "SLIME01", "SLIME02", "SLIME03", "SLIME04", "SLIME05", "SLIME06", "SLIME07", "SLIME08", "SLIME09", "SLIME10", "SLIME11", "SLIME12", "FWATER1", "FWATER2", "FWATER3", "FWATER4"}
DOOR_PREFIXES = ("BIGDOOR", "DOOR", "WOODDOR", "TEKDOOR", "SPCDOOR")
SWITCH_PREFIXES = ("SW1", "SW2")

# GZDoom doomitems.txt names → Blood gameplay roles (NBlood common_game.h types).
ENTITY_MAP = {
    9: (202, 2825, 6, 384, 40, "approximation:ShotgunGuy->shotgun-cultist"),
    58: (211, 1270, 6, 384, 40, "approximation:Spectre->hellhound"),
    64: (204, 2820, 6, 384, 48, "approximation:Archvile->butcher"),
    65: (201, 2820, 6, 384, 40, "approximation:ChaingunGuy->Tommy-cultist"),
    66: (206, 1470, 6, 384, 40, "approximation:Revenant->flesh-gargoyle"),
    67: (203, 2820, 6, 384, 48, "approximation:Fatso->axe-zombie"),
    68: (213, 1920, 6, 384, 32, "approximation:Arachnotron->brown-spider"),
    69: (203, 2820, 6, 384, 48, "approximation:HellKnight->axe-zombie"),
    71: (206, 1470, 6, 384, 40, "approximation:PainElemental->flesh-gargoyle"),
    2001: (41, 559, 3, 128, 48, "semantic:Shotgun->sawed-off"),
    2002: (42, 558, 3, 128, 48, "semantic:Chaingun->Tommy-gun"),
    2003: (46, 526, 3, 128, 48, "approximation:RocketLauncher->napalm"),
    2005: (43, 525, 3, 128, 48, "approximation:Chainsaw->pitchfork"),
    2007: (69, 813, 3, 128, 32, "semantic:Clip->Tommy-ammo"),
    2008: (67, 812, 3, 128, 32, "semantic:Shell->shotgun-ammo"),
    2011: (109, 2169, 3, 128, 40, "semantic:Stimpack->Life-Essence"),
    2012: (107, 519, 3, 128, 48, "semantic:Medikit->Doctor-Bag"),
    2013: (110, 2433, 3, 128, 40, "semantic:Soulsphere->Life-Seed"),
    2014: (108, 2169, 3, 128, 24, "approximation:HealthBonus->med-pouch"),
    2015: (140, 2628, 3, 128, 32, "approximation:ArmorBonus->basic-armor"),
    2018: (140, 2628, 3, 128, 48, "semantic:GreenArmor->basic-armor"),
    2019: (141, 2628, 3, 128, 48, "semantic:BlueArmor->body-armor"),
    2048: (72, 817, 3, 128, 48, "semantic:ClipBox->Tommy-drum"),
    2049: (68, 812, 3, 128, 48, "semantic:ShellBox->shell-box"),
    3001: (201, 2820, 6, 384, 40, "approximation:DoomImp->Tommy-cultist"),
    3002: (211, 1270, 6, 384, 40, "approximation:Demon->hellhound"),
    3003: (203, 2820, 6, 384, 56, "approximation:BaronOfHell->axe-zombie"),
    3004: (201, 2820, 6, 384, 40, "approximation:Zombieman->Tommy-cultist"),
    3005: (206, 1470, 6, 384, 40, "approximation:Cacodemon->flesh-gargoyle"),
}
KEY_ITEMS = {
    "blue": (100, 2552, "semantic:blue-key->Skull-key"),
    "yellow": (101, 2553, "semantic:yellow-key->Eye-key"),
    "red": (102, 2552, "semantic:red-key->Fire-key"),
}


def _classify_texture(name: str, *, role_hint: str) -> tuple[int, str, str]:
    label = texture_label(name) if not isinstance(name, str) else name.upper()
    if not label or label == "-":
        return ROLE_TILES[role_hint], role_hint, "defaulted"
    if label in SKY_FLATS:
        return ROLE_TILES["sky"], "sky", "role-matched"
    if label in HAZARD_FLATS:
        return ROLE_TILES["hazard"], "hazard", "role-matched"
    if any(label.startswith(prefix) for prefix in SWITCH_PREFIXES):
        return ROLE_TILES["switch"], "switch", "role-matched"
    if any(label.startswith(prefix) for prefix in DOOR_PREFIXES):
        return ROLE_TILES["door"], "door", "role-matched"
    return ROLE_TILES[role_hint], role_hint, "role-matched"


def _light_shade(light: int) -> int:
    # wad2map.cpp: j = 28-(sect[z].shade>>3) where shade is Doom light level.
    return 28 - (int(light) >> 3)


class _Channels:
    def __init__(self) -> None:
        self._next = USER_CHANNEL_MIN
        self._by_tag: dict[int, int] = {}

    def allocate(self, tag: int | None = None) -> int:
        if tag is not None and int(tag) in self._by_tag:
            return self._by_tag[int(tag)]
        while self._next in RESERVED_CHANNELS:
            self._next += 1
        channel = self._next
        self._next += 1
        if tag is not None:
            self._by_tag[int(tag)] = channel
        return channel


def _neighbors(level: DoomDiskMap, sector_id: int) -> list[int]:
    found: set[int] = set()
    for line in level.linedefs:
        for side_id, other_id in ((line.side_front, line.side_back), (line.side_back, line.side_front)):
            if side_id == 0xFFFF or other_id == 0xFFFF:
                continue
            if not 0 <= side_id < len(level.sidedefs) or not 0 <= other_id < len(level.sidedefs):
                continue
            if int(level.sidedefs[side_id].sector) == sector_id:
                found.add(int(level.sidedefs[other_id].sector))
    found.discard(sector_id)
    return sorted(found)


def _door_open_ceiling(level: DoomDiskMap, sector_id: int) -> int:
    sector = level.sectors[sector_id]
    candidates = [
        level.sectors[neighbor].ceiling_height
        for neighbor in _neighbors(level, sector_id)
        if level.sectors[neighbor].ceiling_height > sector.ceiling_height
    ]
    if candidates:
        return min(candidates)
    return sector.floor_height + 128


def _lift_down_floor(level: DoomDiskMap, sector_id: int) -> int:
    sector = level.sectors[sector_id]
    candidates = [
        level.sectors[neighbor].floor_height
        for neighbor in _neighbors(level, sector_id)
        if level.sectors[neighbor].floor_height < sector.floor_height
    ]
    if candidates:
        return min(candidates)
    return sector.floor_height - 64


def _centroid(level: DoomDiskMap, sector_id: int) -> tuple[int, int]:
    xs, ys = [], []
    for line in level.linedefs:
        for side_id in (line.side_front, line.side_back):
            if side_id == 0xFFFF or not 0 <= side_id < len(level.sidedefs):
                continue
            if int(level.sidedefs[side_id].sector) != sector_id:
                continue
            vertex = level.vertices[line.v1]
            xs.append(vertex.x)
            ys.append(vertex.y)
    if not xs:
        return 0, 0
    return sum(xs) // len(xs), sum(ys) // len(ys)


def _place_in_sector(builder: LevelBuilder, level: DoomDiskMap, doom_sector: int, build_sector: int, x: int, y: int, **fields: Any) -> int:
    z = fields.pop("z", scale_z(level.sectors[doom_sector].floor_height))
    try:
        return builder.add_sprite(sector=build_sector, x=scale_xy(x), y=scale_xy(-y), z=z, **fields)
    except ConstructionError:
        cx, cy = _centroid(level, doom_sector)
        return builder.add_sprite(
            sector=build_sector, x=scale_xy(cx), y=scale_xy(-cy), z=z, **fields,
        )


def _midpoint_inset(level: DoomDiskMap, line: DoomLinedef, *, into_front: bool = True) -> tuple[int, int]:
    a, b = level.vertices[line.v1], level.vertices[line.v2]
    mx, my = (a.x + b.x) / 2, (a.y + b.y) / 2
    dx, dy = b.x - a.x, b.y - a.y
    length = hypot(dx, dy) or 1
    # Front is to the right of v1→v2.
    nx, ny = dy / length, -dx / length
    if not into_front:
        nx, ny = -nx, -ny
    return int(mx + nx * 8), int(my + ny * 8)


def convert_doom_to_blood(level: DoomDiskMap) -> tuple[LevelIR, dict[str, Any]]:
    if not level.supported:
        raise DoomConversionError(f"cannot convert {level.format} map {level.name}: {level.unsupported_reason}")
    ir = new_level()
    geometry = lower_doom_geometry(level, ir=ir)
    if not ir.sectors:
        raise DoomConversionError(f"{level.name} produced no Build sectors")
    builder = LevelBuilder(ir)
    material_counts: Counter[str] = Counter()
    sector_map: list[int] = geometry["sector_map"]

    for doom_id, sector in enumerate(level.sectors):
        build_id = sector_map[doom_id]
        if build_id < 0:
            continue
        floor_tile, floor_role, floor_class = _classify_texture(sector.floor_texture, role_hint="floor")
        ceil_tile, ceil_role, ceil_class = _classify_texture(sector.ceiling_texture, role_hint="ceiling")
        material_counts.update((floor_class, ceil_class))
        fields = builder.level.sectors[build_id]["fields"]
        shade = _light_shade(sector.light_level)
        fields.update(
            floor_picnum=floor_tile, ceiling_picnum=ceil_tile,
            floor_shade=shade, ceiling_shade=shade,
        )
        if ceil_role == "sky":
            fields["ceiling_stat"] = int(fields.get("ceiling_stat", 0)) | 1

    edge_to_wall = {}
    for key, wall_id in geometry["edge_to_wall"].items():
        line_id, side = (int(part) for part in key.split(":"))
        edge_to_wall[(line_id, side)] = int(wall_id)
        line = level.linedefs[line_id]
        side_id = line.side_front if side == 0 else line.side_back
        if side_id == 0xFFFF or not 0 <= side_id < len(level.sidedefs):
            continue
        sidedef = level.sidedefs[side_id]
        name = texture_label(sidedef.middle_texture)
        if name in {"", "-"}:
            name = texture_label(sidedef.upper_texture) or texture_label(sidedef.lower_texture)
        tile, role, classification = _classify_texture(name or "-", role_hint="wall")
        material_counts[classification] += 1
        builder.level.walls[wall_id]["fields"]["picnum"] = tile
        builder.level.walls[wall_id]["fields"]["shade"] = _light_shade(
            level.sectors[sidedef.sector].light_level
        )

    inventory = analyze_doom_mechanisms(level)
    channels = _Channels()
    mechanism_report: list[dict[str, Any]] = []
    translated = 0
    door_sectors: set[int] = set()

    def build_sector(doom_id: int) -> int | None:
        if not 0 <= doom_id < len(sector_map) or sector_map[doom_id] < 0:
            return None
        return sector_map[doom_id]

    def apply_z_door(doom_id: int, spec, *, channel: int | None, keyed: str | None) -> None:
        target = build_sector(doom_id)
        if target is None:
            return
        source = level.sectors[doom_id]
        open_ceil = scale_z(_door_open_ceiling(level, doom_id))
        closed_ceil = scale_z(source.ceiling_height)
        floor = scale_z(source.floor_height)
        busy = 8 if spec.speed and spec.speed >= 64 else 20
        fields = {
            "state": 0, "busy": 0, "busy_time_a": busy, "busy_time_b": busy,
            "off_ceiling_z": closed_ceil, "on_ceiling_z": open_ceil,
            "off_floor_z": floor, "on_floor_z": floor,
            "interruptable": 0,
        }
        if spec.wait:
            fields.update(wait_time_a=max(1, spec.wait // 10), retrigger_a=1 if spec.repeatable else 0)
        if channel is not None:
            fields.update(rx_id=channel, trigger_push=0, trigger_wall_push=0)
        else:
            fields.update(trigger_push=1, trigger_wall_push=1)
        if keyed:
            fields["key"] = {"blue": 1, "yellow": 2, "red": 3}[keyed]
        builder.level.sectors[target]["fields"]["type"] = 600
        builder.set_behavior("sector", target, **fields)
        door_sectors.add(doom_id)

    def apply_lift(doom_id: int, spec, *, channel: int | None) -> None:
        target = build_sector(doom_id)
        if target is None:
            return
        source = level.sectors[doom_id]
        up = scale_z(source.floor_height)
        down = scale_z(_lift_down_floor(level, doom_id))
        ceil = scale_z(source.ceiling_height)
        busy = 8 if spec.speed and spec.speed >= 64 else 16
        fields = {
            "state": 0, "busy": 0, "busy_time_a": busy, "busy_time_b": busy,
            "off_ceiling_z": ceil, "on_ceiling_z": ceil,
            "off_floor_z": up, "on_floor_z": down,
            "wait_time_a": max(1, (spec.wait or 105) // 10), "retrigger_a": 1,
        }
        if channel is not None:
            fields.update(rx_id=channel, trigger_push=0, trigger_wall_push=0)
        else:
            fields.update(trigger_push=1, trigger_wall_push=1, trigger_enter=1)
        builder.level.sectors[target]["fields"]["type"] = 600
        builder.set_behavior("sector", target, **fields)

    for record in inventory["mechanisms"]:
        spec = LINEDEF_SPECIALS.get(int(record.get("special", 0)))
        if spec is None:
            if record["kind"] == "damage_area":
                for ref in record["targets"]:
                    doom_id = int(ref.split(":")[1])
                    target = build_sector(doom_id)
                    if target is None:
                        continue
                    damage = 1 if record["action"] == "dDamage_Nukage" else 2
                    builder.set_behavior("sector", target, damage_type=damage)
                    translated += 1
                    mechanism_report.append({**record, "blood": "XSECTOR.damage_type", "representability": record["fidelity"]})
            elif record["kind"] == "secret":
                mechanism_report.append({**record, "blood": "unmapped-secret-tally", "representability": Representability.APPROXIMATE.value})
            continue
        targets = [int(item.split(":")[1]) for item in record["targets"] if item.startswith("sector:")]
        representability = spec.fidelity
        if spec.kind in {"door", "key_gate"}:
            channel = None
            if spec.activation == "use" and not spec.local_backsector:
                channel = channels.allocate(record.get("tag"))
                line_id = int(record["id"].split(":")[1])
                line = level.linedefs[line_id]
                fx, fy = _midpoint_inset(level, line)
                front = containing_sector(level, fx, fy)
                if front is None:
                    front = int(level.sidedefs[line.side_front].sector)
                sprite_sector = build_sector(front)
                if sprite_sector is not None:
                    z = scale_z((level.sectors[front].floor_height + level.sectors[front].ceiling_height) // 2)
                    try:
                        switch = builder.add_sprite(
                            sector=sprite_sector, x=scale_xy(fx), y=scale_xy(-fy), z=z,
                            type=20 if spec.repeatable else 21, picnum=1070, status=0,
                            angle=scale_angle(0), cstat=128, x_repeat=40, y_repeat=40,
                        )
                        builder.set_behavior(
                            "sprite", switch, tx_id=channel, command=1, trigger_on=1, trigger_push=1,
                        )
                    except ConstructionError:
                        cx, cy = _centroid(level, front)
                        switch = builder.add_sprite(
                            sector=sprite_sector, x=scale_xy(cx), y=scale_xy(-cy), z=z,
                            type=20 if spec.repeatable else 21, picnum=1070, status=0,
                            cstat=128, x_repeat=40, y_repeat=40,
                        )
                        builder.set_behavior(
                            "sprite", switch, tx_id=channel, command=1, trigger_on=1, trigger_push=1,
                        )
            elif spec.activation == "walk":
                channel = channels.allocate(record.get("tag"))
                line_id = int(record["id"].split(":")[1])
                front = int(level.sidedefs[level.linedefs[line_id].side_front].sector)
                trigger_sector = build_sector(front)
                if trigger_sector is not None:
                    builder.set_behavior(
                        "sector", trigger_sector, tx_id=channel, command=1,
                        trigger_enter=1, trigger_once=0 if spec.repeatable else 1,
                    )
            for doom_id in targets:
                apply_z_door(doom_id, spec, channel=channel, keyed=spec.key)
            translated += 1
            mechanism_report.append({**record, "blood": "type-600", "representability": representability})
        elif spec.kind == "lift":
            channel = channels.allocate(record.get("tag")) if spec.activation == "use" else None
            if spec.activation == "use":
                line_id = int(record["id"].split(":")[1])
                line = level.linedefs[line_id]
                fx, fy = _midpoint_inset(level, line)
                front = containing_sector(level, fx, fy) or int(level.sidedefs[line.side_front].sector)
                sprite_sector = build_sector(front)
                if sprite_sector is not None:
                    z = scale_z(level.sectors[front].floor_height)
                    switch = _place_in_sector(
                        builder, level, front, sprite_sector, fx, fy, z=z,
                        type=20, picnum=1070, status=0, cstat=128, x_repeat=40, y_repeat=40,
                    )
                    builder.set_behavior("sprite", switch, tx_id=channel, command=1, trigger_on=1, trigger_push=1)
            for doom_id in targets:
                apply_lift(doom_id, spec, channel=channel)
            translated += 1
            mechanism_report.append({**record, "blood": "type-600-lift", "representability": representability})
        elif spec.kind == "teleport":
            line_id = int(record["id"].split(":")[1])
            line = level.linedefs[line_id]
            source = int(level.sidedefs[line.side_front].sector)
            dest_things = [thing for thing in level.things if thing.type == 14]
            dest = None
            for thing in dest_things:
                sector_id = containing_sector(level, thing.x, thing.y)
                if sector_id is not None and level.sectors[sector_id].tag == line.tag:
                    dest = (thing, sector_id)
                    break
            src_build, dest_build = build_sector(source), build_sector(dest[1]) if dest else None
            if dest is None or src_build is None or dest_build is None:
                mechanism_report.append({**record, "blood": "omitted", "representability": Representability.UNSUPPORTED.value})
                continue
            thing, dest_sector = dest
            marker = _place_in_sector(
                builder, level, dest_sector, dest_build, thing.x, thing.y,
                z=scale_z(level.sectors[dest_sector].floor_height),
                type=8, picnum=3193, status=0, angle=scale_angle(thing.angle),
            )
            builder.level.sectors[src_build]["fields"]["type"] = 604
            builder.set_behavior(
                "sector", src_build, marker_0=marker, trigger_enter=1, dude_lockout=1, data=0,
            )
            translated += 1
            mechanism_report.append({**record, "blood": "type-604", "representability": Representability.SEMANTIC.value})
        elif spec.kind == "exit":
            line_id = int(record["id"].split(":")[1])
            line = level.linedefs[line_id]
            fx, fy = _midpoint_inset(level, line)
            front = containing_sector(level, fx, fy) or int(level.sidedefs[line.side_front].sector)
            sprite_sector = build_sector(front)
            if sprite_sector is None:
                continue
            z = scale_z(level.sectors[front].floor_height)
            switch = _place_in_sector(
                builder, level, front, sprite_sector, fx, fy, z=z,
                type=20, picnum=318, status=0, cstat=128, x_repeat=40, y_repeat=40,
            )
            builder.set_behavior("sprite", switch, tx_id=4, command=1, trigger_on=1, trigger_push=1)
            translated += 1
            mechanism_report.append({**record, "blood": "channel-4-exit", "representability": Representability.SEMANTIC.value})
        else:
            mechanism_report.append({**record, "blood": "not-lowered", "representability": spec.fidelity})

    entity_records = []
    omitted_entities: Counter[int] = Counter()
    for index, thing in enumerate(level.things):
        sector_id = containing_sector(level, thing.x, thing.y)
        if thing.type == 1:
            if sector_id is None or build_sector(sector_id) is None:
                raise DoomConversionError("player 1 start is not inside a converted sector")
            builder.set_player_start(
                sector=build_sector(sector_id),
                x=scale_xy(thing.x), y=scale_xy(-thing.y),
                z=scale_z(level.sectors[sector_id].floor_height),
                angle=scale_angle(thing.angle),
            )
            continue
        if sector_id is None or build_sector(sector_id) is None:
            omitted_entities[thing.type] += 1
            continue
        color = KEY_COLORS.get(thing.type)
        if color:
            key_type, tile, classification = KEY_ITEMS[color]
            sprite_id = _place_in_sector(
                builder, level, sector_id, build_sector(sector_id), thing.x, thing.y,
                z=scale_z(level.sectors[sector_id].floor_height),
                type=key_type, picnum=tile, status=3, cstat=128, x_repeat=32, y_repeat=32,
                angle=scale_angle(thing.angle),
            )
            builder.set_behavior("sprite", sprite_id)
            entity_records.append({"source_thing": index, "target_sprite": sprite_id, "classification": classification})
            continue
        if thing.type == 14:
            continue
        mapping = ENTITY_MAP.get(thing.type)
        if mapping is None:
            omitted_entities[thing.type] += 1
            continue
        type_, tile, status, cstat, repeat, classification = mapping
        try:
            sprite_id = builder.add_sprite(
                sector=build_sector(sector_id), x=scale_xy(thing.x), y=scale_xy(-thing.y),
                z=scale_z(level.sectors[sector_id].floor_height),
                type=type_, picnum=tile, status=status, cstat=cstat,
                x_repeat=repeat, y_repeat=repeat, angle=scale_angle(thing.angle),
            )
        except ConstructionError:
            omitted_entities[thing.type] += 1
            continue
        builder.set_behavior("sprite", sprite_id)
        entity_records.append({"source_thing": index, "target_sprite": sprite_id, "classification": classification})

    if builder.level.player_start["sector"] < 0:
        raise DoomConversionError("converted map has no player start")
    built = builder.build()
    errors = [item for item in validate_map(built.to_disk_map()) if item.severity == "error"]
    semantic = doom_to_semantic_level(level)
    progression = solve_progression(semantic)
    report = {
        "$schema": "llmapper.doom-blood-conversion",
        "schema_version": 1,
        "source": level.name,
        "source_counts": {
            "sectors": len(level.sectors), "linedefs": len(level.linedefs),
            "sidedefs": len(level.sidedefs), "vertices": len(level.vertices),
            "things": len(level.things),
        },
        "converted_counts": {
            "sectors": len(built.sectors), "walls": len(built.walls), "sprites": len(built.sprites),
        },
        "scale": {
            "xy": geometry["xy_scale"], "z": geometry["z_scale"],
            "xy_evidence": geometry["xy_scale_evidence"],
            "z_evidence": geometry["z_scale_evidence"],
        },
        "geometry": {
            "portals": geometry["portals"],
            "warnings": geometry["warnings"],
            "rejected_sectors": sum(item < 0 for item in sector_map),
        },
        "materials": dict(material_counts),
        "mechanisms_recognized": len(inventory["mechanisms"]),
        "mechanisms_translated": translated,
        "mechanism_records": mechanism_report,
        "unsupported_mechanisms": inventory["unsupported"],
        "entities": {"translated": entity_records, "omitted": dict(omitted_entities)},
        "representability": sorted({item.get("representability", "unsupported") for item in mechanism_report}),
        "representability_counts": dict(Counter(item.get("representability", "unsupported") for item in mechanism_report)),
        "validation_errors": [item.__dict__ for item in errors],
        "semantic_progression": {
            "exit_reachable": progression["exit_reachable"],
            "reached": len(progression["reached_regions"]),
            "keys": progression["keys"],
        },
    }
    if errors:
        raise DoomConversionError(
            f"{level.name} converted but failed structural validation: {errors[0].code} {errors[0].message}"
        )
    return built, report
