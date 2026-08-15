from __future__ import annotations

import copy
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from .build_ir import BuildIR, BuildIRError
from .construction import LevelBuilder, new_level
from .duke import DukeDiskMap, SECTOR_FIELDS as DUKE_SECTOR_FIELDS
from .duke import SPRITE_FIELDS as DUKE_SPRITE_FIELDS
from .duke import WALL_FIELDS as DUKE_WALL_FIELDS
from .format import SECTOR_FIELDS as BLOOD_SECTOR_FIELDS
from .format import WALL_FIELDS as BLOOD_WALL_FIELDS
from .model import DiskObject


class ConversionError(ValueError):
    pass


@dataclass(frozen=True)
class GameProfile:
    game: str
    native_units_per_normalized_numerator: int
    native_units_per_normalized_denominator: int
    shade_multiplier_from_duke: Fraction
    player_eye_height_native: int
    evidence: str

    @property
    def native_units_per_normalized(self) -> Fraction:
        return Fraction(
            self.native_units_per_normalized_numerator,
            self.native_units_per_normalized_denominator,
        )


GAME_PROFILES = {
    "duke3d": GameProfile(
        "duke3d", 1, 1, Fraction(1, 1), 38 << 8,
        "EDuke32 player.h PHEIGHT plus native E3L1 geometry",
    ),
    "blood": GameProfile(
        "blood", 3, 2, Fraction(2, 1), 0x1600,
        "E3L1/DNE3L1 differential: 1831 directed edges and 433/464 matched sector surfaces at 3:2",
    ),
}


# Only one-to-one, nonzero mappings with at least five exact observations in the
# hand-converted E3L1 pair are enabled. Context-dependent candidates remain report-only.
DUKE_TO_BLOOD_MATERIAL_EXACT = {89: 2500, 216: 492, 698: 471, 793: 1353, 893: 458}
BLOOD_TO_DUKE_MATERIAL_EXACT = {target: source for source, target in DUKE_TO_BLOOD_MATERIAL_EXACT.items()}


def native_scale(source: str, target: str) -> Fraction:
    try:
        return GAME_PROFILES[target].native_units_per_normalized / GAME_PROFILES[source].native_units_per_normalized
    except KeyError as exc:
        raise ConversionError(f"unsupported game profile {exc.args[0]!r}") from exc


def _scale(value: int, scale: Fraction) -> int:
    return round(int(value) * scale.numerator / scale.denominator)


def convert_shade(value: int, source: str, target: str) -> int:
    if source == target:
        return int(value)
    if source == "duke3d" and target == "blood":
        if value <= -100:
            return 0
        return max(-128, min(127, int(value) * 2))
    if source == "blood" and target == "duke3d":
        return max(-128, min(127, round(int(value) / 2)))
    raise ConversionError(f"unsupported shade conversion {source}->{target}")


def _empty(fields: list[tuple[str, str]]) -> dict[str, int]:
    return {name: 0 for name, _kind in fields}


def _mechanism_inventory(build: BuildIR) -> dict[str, Any]:
    if build.source_game == "duke3d":
        controller_names = {1: "sector-effector", 2: "activator", 4: "locked-activator", 8: "master-switch", 10: "gpspeed"}
        controls = Counter(
            controller_names[sprite["fields"]["picnum"]]
            for sprite in build.sprites if sprite["fields"]["picnum"] in controller_names
        )
        tagged = {
            "sectors": sum(bool(item["fields"]["lotag"] or item["fields"]["hitag"]) for item in build.sectors),
            "walls": sum(bool(item["fields"]["lotag"] or item["fields"]["hitag"]) for item in build.walls),
            "sprites": sum(bool(item["fields"]["lotag"] or item["fields"]["hitag"]) for item in build.sprites),
        }
        return {"controller_sprites": dict(sorted(controls.items())), "tagged_objects": tagged}
    document = build.native.get("document", {})
    sectors, walls, sprites = document.get("sectors", []), document.get("walls", []), document.get("sprites", [])
    return {
        "extended_records": {
            "xsectors": sum(item.get("blood") is not None for item in sectors),
            "xwalls": sum(item.get("blood") is not None for item in walls),
            "xsprites": sum(item.get("blood") is not None for item in sprites),
        },
        "switch_sprites": sum(20 <= item["fields"].get("type", 0) < 24 for item in sprites),
    }


def _asset_inventory(build: BuildIR) -> dict[str, list[int]]:
    return {
        "sector_ceiling_tiles": sorted({item["fields"]["ceiling_picnum"] for item in build.sectors}),
        "sector_floor_tiles": sorted({item["fields"]["floor_picnum"] for item in build.sectors}),
        "wall_tiles": sorted({item["fields"]["picnum"] for item in build.walls}),
        "sprite_tiles": sorted({item["fields"]["picnum"] for item in build.sprites}),
        "palettes": sorted(
            {item["fields"]["ceiling_pal"] for item in build.sectors}
            | {item["fields"]["floor_pal"] for item in build.sectors}
            | {item["fields"]["pal"] for item in build.walls}
            | {item["fields"]["pal"] for item in build.sprites}
        ),
    }


def _material(source_tile: int, source: str, target: str, policy: str) -> tuple[int, str]:
    defaults = {"blood": 180, "duke3d": 0}
    if policy == "semantic":
        mapping = DUKE_TO_BLOOD_MATERIAL_EXACT if source == "duke3d" else BLOOD_TO_DUKE_MATERIAL_EXACT
        if source_tile in mapping:
            return mapping[source_tile], "exact"
    return defaults[target], "unmapped"


def _convert_to_blood(build: BuildIR, policy: str) -> tuple[Any, dict[str, Any]]:
    scale = native_scale(build.source_game, "blood")
    level = new_level()
    level.player_start = {
        "x": _scale(build.player_start["x"], scale),
        "y": _scale(build.player_start["y"], scale),
        "z": _scale(build.player_start["z"], scale),
        "angle": int(build.player_start["angle"]) & 2047,
        "sector": int(build.player_start["sector"]),
    }
    material_counts: Counter[str] = Counter()
    for sector_id, item in enumerate(build.sectors):
        source = item["fields"]
        fields = _empty(BLOOD_SECTOR_FIELDS)
        ceiling_tile, ceiling_class = _material(source["ceiling_picnum"], build.source_game, "blood", policy)
        floor_tile, floor_class = _material(source["floor_picnum"], build.source_game, "blood", policy)
        material_counts.update((ceiling_class, floor_class))
        fields.update(
            wall_ptr=source["wall_ptr"], wall_count=source["wall_count"],
            ceiling_z=_scale(source["ceiling_z"], scale), floor_z=_scale(source["floor_z"], scale),
            ceiling_stat=source["ceiling_stat"] & 0x03FF, floor_stat=source["floor_stat"] & 0x03FF,
            ceiling_picnum=ceiling_tile, floor_picnum=floor_tile,
            ceiling_heinum=source["ceiling_heinum"], floor_heinum=source["floor_heinum"],
            ceiling_shade=convert_shade(source["ceiling_shade"], build.source_game, "blood"),
            floor_shade=convert_shade(source["floor_shade"], build.source_game, "blood"),
            ceiling_pal=0, floor_pal=0,
            ceiling_x_panning=source["ceiling_x_panning"], ceiling_y_panning=source["ceiling_y_panning"],
            floor_x_panning=source["floor_x_panning"], floor_y_panning=source["floor_y_panning"],
            visibility=source["visibility"], filler=0, type=0, hitag=0, extra=-1,
        )
        level.sectors.append({"id": sector_id, "fields": fields, "blood": None})
    for wall_id, item in enumerate(build.walls):
        source = item["fields"]
        fields = _empty(BLOOD_WALL_FIELDS)
        tile, classification = _material(source["picnum"], build.source_game, "blood", policy)
        material_counts[classification] += 1
        fields.update(
            x=_scale(source["x"], scale), y=_scale(source["y"], scale),
            point2=source["point2"], next_wall=source["next_wall"], next_sector=source["next_sector"],
            cstat=source["cstat"] & 0x03FF, picnum=tile, over_picnum=0,
            shade=convert_shade(source["shade"], build.source_game, "blood"), pal=0,
            x_repeat=max(1, min(255, _scale(source["x_repeat"], scale))),
            y_repeat=source["y_repeat"], x_panning=source["x_panning"], y_panning=source["y_panning"],
            type=0, hitag=0, extra=-1,
        )
        level.walls.append({"id": wall_id, "fields": fields, "blood": None})

    entity_report = {"translated": [], "omitted": []}
    if policy == "semantic":
        builder = LevelBuilder(level)
        for sprite_id, item in enumerate(build.sprites):
            source = item["fields"]
            # EDuke32 names.h identifies 28/1680 as SHOTGUNSPRITE/LIZTROOP.
            # Across the local Blood corpus, all 122 type-41 pickups use tile
            # 559 and all 550 type-201 cultists use tile 2820.
            definition = {
                28: {"type": 41, "picnum": 559, "status": 3, "cstat": 128, "repeat": 48, "classification": "semantic-equivalent:shotgun-pickup"},
                1680: {"type": 201, "picnum": 2820, "status": 6, "cstat": 384, "repeat": 40, "classification": "approximation:ranged-humanoid"},
            }.get(source["picnum"])
            if definition is None:
                entity_report["omitted"].append({"source_sprite": sprite_id, "tile": source["picnum"], "reason": "no verified semantic mapping"})
                continue
            new_id = builder.add_sprite(
                sector=source["sector"], x=_scale(source["x"], scale), y=_scale(source["y"], scale),
                z=_scale(source["z"], scale), type=definition["type"], picnum=definition["picnum"],
                status=definition["status"], angle=source["angle"], cstat=definition["cstat"],
                x_repeat=definition["repeat"], y_repeat=definition["repeat"], shade=0,
            )
            builder.set_behavior("sprite", new_id)
            entity_report["translated"].append({"source_sprite": sprite_id, "target_sprite": new_id, "classification": definition["classification"]})
        level = builder.level
    else:
        entity_report["omitted"] = [{"count": len(build.sprites), "reason": "geometry-only policy"}]
    return level.to_disk_map(), {"materials": dict(material_counts), "entities": entity_report}


def _convert_to_duke(build: BuildIR, policy: str) -> tuple[DukeDiskMap, dict[str, Any]]:
    scale = native_scale(build.source_game, "duke3d")
    header = {
        "version": 7,
        "start_x": _scale(build.player_start["x"], scale),
        "start_y": _scale(build.player_start["y"], scale),
        "start_z": _scale(build.player_start["z"], scale),
        "start_angle": int(build.player_start["angle"]) & 2047,
        "start_sector": int(build.player_start["sector"]),
    }
    material_counts: Counter[str] = Counter()
    sectors: list[DiskObject] = []
    for item in build.sectors:
        source, fields = item["fields"], _empty(DUKE_SECTOR_FIELDS)
        ceiling_tile, ceiling_class = _material(source["ceiling_picnum"], build.source_game, "duke3d", policy)
        floor_tile, floor_class = _material(source["floor_picnum"], build.source_game, "duke3d", policy)
        material_counts.update((ceiling_class, floor_class))
        fields.update(
            wall_ptr=source["wall_ptr"], wall_count=source["wall_count"],
            ceiling_z=_scale(source["ceiling_z"], scale), floor_z=_scale(source["floor_z"], scale),
            ceiling_stat=source["ceiling_stat"] & 0x03FF, floor_stat=source["floor_stat"] & 0x03FF,
            ceiling_picnum=ceiling_tile, floor_picnum=floor_tile,
            ceiling_heinum=source["ceiling_heinum"], floor_heinum=source["floor_heinum"],
            ceiling_shade=convert_shade(source["ceiling_shade"], build.source_game, "duke3d"),
            floor_shade=convert_shade(source["floor_shade"], build.source_game, "duke3d"),
            ceiling_pal=0, floor_pal=0,
            ceiling_x_panning=source["ceiling_x_panning"], ceiling_y_panning=source["ceiling_y_panning"],
            floor_x_panning=source["floor_x_panning"], floor_y_panning=source["floor_y_panning"],
            visibility=source["visibility"], fog_pal=0, lotag=0, hitag=0, extra=-1,
        )
        sectors.append(DiskObject(fields))
    walls: list[DiskObject] = []
    for item in build.walls:
        source, fields = item["fields"], _empty(DUKE_WALL_FIELDS)
        tile, classification = _material(source["picnum"], build.source_game, "duke3d", policy)
        material_counts[classification] += 1
        fields.update(
            x=_scale(source["x"], scale), y=_scale(source["y"], scale),
            point2=source["point2"], next_wall=source["next_wall"], next_sector=source["next_sector"],
            cstat=source["cstat"] & 0x03FF, picnum=tile, over_picnum=0,
            shade=convert_shade(source["shade"], build.source_game, "duke3d"), pal=0,
            x_repeat=max(1, min(255, _scale(source["x_repeat"], scale))),
            y_repeat=source["y_repeat"], x_panning=source["x_panning"], y_panning=source["y_panning"],
            lotag=0, hitag=0, extra=-1,
        )
        walls.append(DiskObject(fields))
    sprites: list[DiskObject] = []
    entity_report = {"translated": [], "omitted": []}
    if policy == "semantic":
        for sprite_id, item in enumerate(build.sprites):
            source = item["fields"]
            definition = {
                41: {"picnum": 28, "repeat": 32, "classification": "semantic-equivalent:shotgun-pickup"},
                201: {"picnum": 1680, "repeat": 40, "classification": "approximation:ranged-humanoid"},
            }.get(source["lotag"])
            if definition is None:
                entity_report["omitted"].append({"source_sprite": sprite_id, "type": source["lotag"], "reason": "no verified semantic mapping"})
                continue
            fields = _empty(DUKE_SPRITE_FIELDS)
            fields.update(
                x=_scale(source["x"], scale), y=_scale(source["y"], scale), z=_scale(source["z"], scale),
                cstat=0, picnum=definition["picnum"], shade=0, pal=0, clipdist=32, blend=0,
                x_repeat=definition["repeat"], y_repeat=definition["repeat"],
                sector=source["sector"], status=0, angle=source["angle"], owner=-1,
                x_velocity=0, y_velocity=0, z_velocity=0, lotag=0, hitag=0, extra=-1,
            )
            target_id = len(sprites)
            sprites.append(DiskObject(fields))
            entity_report["translated"].append({"source_sprite": sprite_id, "target_sprite": target_id, "classification": definition["classification"]})
    else:
        entity_report["omitted"] = [{"count": len(build.sprites), "reason": "geometry-only policy"}]
    return DukeDiskMap(7, header, sectors, walls, sprites), {"materials": dict(material_counts), "entities": entity_report}


def convert_build_ir(build: BuildIR, target_game: str, *, policy: str = "geometry-only") -> tuple[Any, dict[str, Any]]:
    target_game = target_game.lower()
    if target_game == "duke":
        target_game = "duke3d"
    if policy not in {"strict", "semantic", "geometry-only"}:
        raise ConversionError("policy must be strict, semantic, or geometry-only")
    if build.source_game == target_game:
        return build.to_native_disk_map(), {
            "$schema": "llmapper.conversion-report", "schema_version": 1,
            "source_game": build.source_game, "target_game": target_game, "policy": "native-lossless",
            "overall": {"exactness": "exact", "structural_validity": True},
        }
    if {build.source_game, target_game} != {"blood", "duke3d"}:
        raise ConversionError(f"unsupported conversion {build.source_game}->{target_game}")
    inventory = _asset_inventory(build)
    mechanisms = _mechanism_inventory(build)
    if policy == "strict":
        raise ConversionError(
            "strict cross-game conversion is unavailable: materials, entities, and native mechanisms are not all verified"
        )
    if target_game == "blood":
        disk, decisions = _convert_to_blood(build, policy)
        from .analysis import validate_map
        errors = [item for item in validate_map(disk) if item.severity == "error"]
    else:
        disk, decisions = _convert_to_duke(build, policy)
        errors = [item for item in disk.to_build_ir().validate() if item.severity == "error"]
    report = {
        "$schema": "llmapper.conversion-report",
        "schema_version": 1,
        "source_game": build.source_game,
        "target_game": target_game,
        "policy": policy,
        "normalization": {
            "coordinate_scale": {"numerator": native_scale(build.source_game, target_game).numerator, "denominator": native_scale(build.source_game, target_game).denominator},
            "profile": {game: GAME_PROFILES[game].__dict__ | {"shade_multiplier_from_duke": str(GAME_PROFILES[game].shade_multiplier_from_duke)} for game in (build.source_game, target_game)},
            "rounding": "nearest integer native unit",
        },
        "geometry": {
            "classification": "normalized",
            "sectors": len(build.sectors), "walls": len(build.walls),
            "topology_preserved": True, "slopes_preserved": True,
        },
        "lighting": {
            "classification": "approximation",
            "model": "Blood shade is initially modeled as twice Duke shade; special/sentinel values are target-defaulted",
        },
        "materials": {
            "classification": "mixed" if policy == "semantic" else "unsupported",
            "source_inventory": inventory,
            "decisions": decisions["materials"],
            "unknown_assets_use_explicit_target_default": True,
        },
        "entities": decisions["entities"],
        "mechanisms": {
            "classification": "unsupported",
            "source_inventory": mechanisms,
            "decision": "removed from target rather than translating native tags by number",
        },
        "overall": {
            "structural_validity": not errors,
            "validation_errors": [item.__dict__ for item in errors],
            "geometry_fidelity": "normalized",
            "visual_fidelity": "approximation" if policy == "semantic" else "unsupported",
            "gameplay_fidelity": "unsupported",
            "known_gameplay_differences": "native triggers, controllers, tags, and unmapped entities are omitted",
        },
    }
    if errors:
        raise ConversionError(f"converted {target_game} geometry failed validation: {errors[0].code}")
    return disk, report
