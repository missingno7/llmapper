from __future__ import annotations

import copy
from dataclasses import dataclass
from math import hypot
from typing import Any, Iterable

from .analysis import validate_map
from .composition import _point_in_sector, _sector_surface_z, _segment_conflict
from .format import SECTOR_FIELDS, SPRITE_FIELDS, WALL_FIELDS, XSECTOR_SCHEMA, XSPRITE_SCHEMA, XWALL_SCHEMA
from .model import LevelIR


class ConstructionError(ValueError):
    pass


def _empty_fields(schema: Iterable[tuple[Any, ...]]) -> dict[str, int]:
    return {str(item[0]): 0 for item in schema}


def new_level(*, visibility: int = 800) -> LevelIR:
    """Create an empty Blood v7 LevelIR ready for explicit construction."""
    return LevelIR(
        metadata={
            "format": "Blood MAP",
            "map_version": 0x0700,
            "visibility": int(visibility),
            "matt_id": 0,
            "sky_type": 0,
            "revision": 1,
            "source_crc32": "00000000",
            "extra_header": {
                "copyright_hex": (b"Generated with bloodmap" + b"\0" * 41).hex(),
                "xsprite_size": 56,
                "xwall_size": 24,
                "xsector_size": 60,
                "xmp_signature_hex": "000000",
                "xmp_header_version": 0,
                "xmp_map_flags": 0,
                "xmp_board_width": 0,
                "xmp_board_height": 0,
                "xmp_palette": 0,
                "xmp_sky_repeat_count": 0,
                "xmp_sky_visibility": 0,
                "reserved_hex": "00" * 37,
            },
        },
        player_start={"x": 0, "y": 0, "z": 0, "angle": 0, "sector": -1},
        sky={"bits": 0, "offsets": [0]},
        sectors=[],
        walls=[],
        sprites=[],
    )


@dataclass(frozen=True)
class SectorAllocation:
    sector_id: int
    wall_ids: tuple[int, ...]


class LevelBuilder:
    """Small, deterministic allocator for scratch-built LevelIR geometry and behavior."""

    def __init__(self, level: LevelIR | None = None):
        self.level = copy.deepcopy(level) if level is not None else new_level()

    def add_sector(
        self,
        points: Iterable[tuple[int, int]],
        *,
        ceiling_z: int = -24576,
        floor_z: int = 8192,
        ceiling_picnum: int = 385,
        floor_picnum: int = 292,
        wall_picnum: int = 180,
        ceiling_shade: int = 0,
        floor_shade: int = 16,
        wall_shade: int = 8,
        type: int = 0,
    ) -> SectorAllocation:
        polygon = [(int(x), int(y)) for x, y in points]
        if len(polygon) < 3:
            raise ConstructionError("a sector needs at least three points")
        if len(set(polygon)) != len(polygon):
            raise ConstructionError("sector points must be unique")
        if int(ceiling_z) > int(floor_z):
            raise ConstructionError("sector ceiling cannot be below its floor")
        area2 = sum(
            polygon[i][0] * polygon[(i + 1) % len(polygon)][1]
            - polygon[(i + 1) % len(polygon)][0] * polygon[i][1]
            for i in range(len(polygon))
        )
        if area2 == 0:
            raise ConstructionError("sector polygon has zero area")
        if area2 < 0:
            raise ConstructionError("sector outer loop must use clockwise Build screen-space winding")
        segments = [
            (polygon[index], polygon[(index + 1) % len(polygon)])
            for index in range(len(polygon))
        ]
        for left in range(len(segments)):
            for right in range(left + 1, len(segments)):
                if right in {left + 1, (left - 1) % len(segments)} or (
                    left == 0 and right == len(segments) - 1
                ):
                    continue
                if _segment_conflict(*segments[left], *segments[right]) is not None:
                    raise ConstructionError("sector polygon self-intersects")

        sector_id = len(self.level.sectors)
        wall_base = len(self.level.walls)
        sector = _empty_fields(SECTOR_FIELDS)
        sector.update(
            wall_ptr=wall_base,
            wall_count=len(polygon),
            ceiling_z=int(ceiling_z),
            floor_z=int(floor_z),
            ceiling_picnum=int(ceiling_picnum),
            floor_picnum=int(floor_picnum),
            ceiling_shade=int(ceiling_shade),
            floor_shade=int(floor_shade),
            type=int(type),
            extra=-1,
        )
        self.level.sectors.append({"id": sector_id, "fields": sector, "blood": None})

        wall_ids: list[int] = []
        for index, (x, y) in enumerate(polygon):
            wall_id = wall_base + index
            next_x, next_y = polygon[(index + 1) % len(polygon)]
            wall = _empty_fields(WALL_FIELDS)
            wall.update(
                x=x,
                y=y,
                point2=wall_base + (index + 1) % len(polygon),
                next_wall=-1,
                next_sector=-1,
                picnum=int(wall_picnum),
                over_picnum=0,
                shade=int(wall_shade),
                x_repeat=max(1, min(255, round(hypot(next_x - x, next_y - y) / 128))),
                y_repeat=8,
                extra=-1,
            )
            self.level.walls.append({"id": wall_id, "fields": wall, "blood": None})
            wall_ids.append(wall_id)
        return SectorAllocation(sector_id, tuple(wall_ids))

    def connect(self, wall_a: int, wall_b: int) -> None:
        wall_a, wall_b = int(wall_a), int(wall_b)
        if wall_a == wall_b or not 0 <= wall_a < len(self.level.walls) or not 0 <= wall_b < len(self.level.walls):
            raise ConstructionError("portal wall IDs must be distinct and in range")
        owners: dict[int, int] = {}
        for sector_id, sector in enumerate(self.level.sectors):
            fields = sector["fields"]
            for wall_id in range(fields["wall_ptr"], fields["wall_ptr"] + fields["wall_count"]):
                owners[wall_id] = sector_id
        owner_a, owner_b = owners.get(wall_a), owners.get(wall_b)
        if owner_a is None or owner_b is None or owner_a == owner_b:
            raise ConstructionError("portal walls must belong to different sectors")
        a = self.level.walls[wall_a]["fields"]
        b = self.level.walls[wall_b]["fields"]
        if a["next_wall"] >= 0 or b["next_wall"] >= 0:
            raise ConstructionError("portal walls must be one-sided")
        a_end = self.level.walls[a["point2"]]["fields"]
        b_end = self.level.walls[b["point2"]]["fields"]
        if (a["x"], a["y"], a_end["x"], a_end["y"]) != (b_end["x"], b_end["y"], b["x"], b["y"]):
            raise ConstructionError("portal walls must have coincident reversed endpoints")
        a.update(next_wall=wall_b, next_sector=owner_b)
        b.update(next_wall=wall_a, next_sector=owner_a)

    def _objects(self, kind: str) -> list[dict[str, Any]]:
        try:
            return {"sector": self.level.sectors, "wall": self.level.walls, "sprite": self.level.sprites}[kind]
        except KeyError as exc:
            raise ConstructionError(f"unknown construction object kind {kind!r}") from exc

    def set_behavior(self, kind: str, object_id: int, **fields: int) -> int:
        objects = self._objects(kind)
        if not 0 <= int(object_id) < len(objects):
            raise ConstructionError(f"{kind} id {object_id} is out of range")
        item = objects[int(object_id)]
        schemas = {"sector": XSECTOR_SCHEMA, "wall": XWALL_SCHEMA, "sprite": XSPRITE_SCHEMA}
        extra_kinds = {"sector": "XSECTOR", "wall": "XWALL", "sprite": "XSPRITE"}
        if item.get("blood") is None:
            used = {
                value["fields"]["extra"]
                for value in objects
                if value["fields"]["extra"] > 0
            }
            extra_id = 1
            while extra_id in used:
                extra_id += 1
            if extra_id >= {"sector": 1024, "wall": 8192, "sprite": 4096}[kind]:
                raise ConstructionError(f"no free X{kind.upper()} id remains")
            blood_fields = _empty_fields(schemas[kind])
            blood_fields["reference"] = int(object_id)
            if kind == "sector":
                blood_fields.update(marker_0=-1, marker_1=-1)
            if kind == "sprite":
                blood_fields.update(target=-1, burn_source=-1)
            item["fields"]["extra"] = extra_id
            item["blood"] = {
                "kind": extra_kinds[kind],
                "fields": blood_fields,
                "opaque_tail_hex": "00000000" if kind == "sprite" else "",
            }
        blood_fields = item["blood"]["fields"]
        unknown = sorted(set(fields) - set(blood_fields))
        if unknown:
            raise ConstructionError(f"unknown {item['blood']['kind']} fields: {unknown}")
        blood_fields.update({name: int(value) for name, value in fields.items()})
        return int(item["fields"]["extra"])

    def add_sprite(
        self,
        *,
        sector: int,
        x: int,
        y: int,
        z: int,
        type: int = 0,
        picnum: int = 0,
        status: int = 0,
        angle: int = 0,
        cstat: int = 128,
        x_repeat: int = 64,
        y_repeat: int = 64,
        shade: int = 0,
        pal: int = 0,
        clipdist: int = 32,
    ) -> int:
        sector_id = int(sector)
        if not 0 <= sector_id < len(self.level.sectors):
            raise ConstructionError(f"sprite sector {sector_id} is out of range")
        point_state = _point_in_sector(self.level, sector_id, (int(x), int(y)))
        if point_state == 0:
            raise ConstructionError("sprite position is outside its sector")
        ceiling = _sector_surface_z(self.level, sector_id, int(x), int(y), "ceiling")
        floor = _sector_surface_z(self.level, sector_id, int(x), int(y), "floor")
        if not ceiling <= int(z) <= floor:
            raise ConstructionError(f"sprite z {z} is outside sector range {ceiling}..{floor}")
        sprite_id = len(self.level.sprites)
        sprite = _empty_fields(SPRITE_FIELDS)
        sprite.update(
            x=int(x), y=int(y), z=int(z), cstat=int(cstat), picnum=int(picnum),
            shade=int(shade), pal=int(pal), clipdist=int(clipdist),
            x_repeat=int(x_repeat), y_repeat=int(y_repeat), sector=sector_id,
            status=int(status), angle=int(angle) & 2047, owner=-1, index=sprite_id,
            type=int(type), extra=-1,
        )
        self.level.sprites.append({"id": sprite_id, "fields": sprite, "blood": None})
        return sprite_id

    def set_player_start(self, *, sector: int, x: int, y: int, z: int, angle: int) -> None:
        sector_id = int(sector)
        if not 0 <= sector_id < len(self.level.sectors):
            raise ConstructionError(f"player sector {sector_id} is out of range")
        if _point_in_sector(self.level, sector_id, (int(x), int(y))) != 1:
            raise ConstructionError("player start must be strictly inside its sector")
        ceiling = _sector_surface_z(self.level, sector_id, int(x), int(y), "ceiling")
        floor = _sector_surface_z(self.level, sector_id, int(x), int(y), "floor")
        if not ceiling <= int(z) <= floor:
            raise ConstructionError(f"player z {z} is outside sector range {ceiling}..{floor}")
        self.level.player_start = {
            "x": int(x), "y": int(y), "z": int(z),
            "angle": int(angle) & 2047, "sector": sector_id,
        }

    def build(self) -> LevelIR:
        if self.level.player_start["sector"] < 0:
            raise ConstructionError("player start has not been assigned")
        errors = [item for item in validate_map(self.level.to_disk_map()) if item.severity == "error"]
        if errors:
            first = errors[0]
            raise ConstructionError(
                f"constructed level violates structure: {first.code} at {first.location}: {first.message}"
            )
        return copy.deepcopy(self.level)


def portal_profiles(
    level: LevelIR, *, min_width: int = 2048, min_opening: int = 8192,
) -> list[dict[str, Any]]:
    """Describe static and configured-open clearance for every reciprocal portal."""

    def surfaces(sector_id: int, x: int, y: int) -> list[tuple[int, int, str]]:
        sector = level.sectors[sector_id]
        values = [(
            _sector_surface_z(level, sector_id, x, y, "ceiling"),
            _sector_surface_z(level, sector_id, x, y, "floor"),
            "current",
        )]
        blood = sector.get("blood")
        if sector["fields"]["type"] in {600, 602} and blood is not None:
            fields = blood["fields"]
            values.extend([
                (int(fields["off_ceiling_z"]), int(fields["off_floor_z"]), "off"),
                (int(fields["on_ceiling_z"]), int(fields["on_floor_z"]), "on"),
            ])
        return list(dict.fromkeys(values))

    profiles: list[dict[str, Any]] = []
    for wall_id, wall in enumerate(level.walls):
        fields = wall["fields"]
        other = int(fields["next_wall"])
        if other < 0 or wall_id > other:
            continue
        end = level.walls[int(fields["point2"])]["fields"]
        width = round(hypot(end["x"] - fields["x"], end["y"] - fields["y"]))
        openings: list[int] = []
        at_rest: list[int] = []
        for x, y in ((fields["x"], fields["y"]), (end["x"], end["y"])):
            left = int(fields["next_sector"])
            right = int(level.walls[other]["fields"]["next_sector"])
            left_values, right_values = surfaces(right, x, y), surfaces(left, x, y)
            at_rest.append(
                min(left_values[0][1], right_values[0][1])
                - max(left_values[0][0], right_values[0][0])
            )
            openings.append(max(
                min(a_floor, b_floor) - max(a_ceiling, b_ceiling)
                for a_ceiling, a_floor, _ in left_values
                for b_ceiling, b_floor, _ in right_values
            ))
        at_rest_opening, configured_opening = min(at_rest), min(openings)
        profiles.append({
            "walls": [wall_id, other],
            "sectors": [int(level.walls[other]["fields"]["next_sector"]), int(fields["next_sector"])],
            "width": width,
            "at_rest_opening": at_rest_opening,
            "configured_opening": configured_opening,
            "wide_enough": width >= int(min_width),
            "walkable_at_rest": width >= int(min_width) and at_rest_opening >= int(min_opening),
            "walkable_when_open": width >= int(min_width) and configured_opening >= int(min_opening),
        })
    return profiles
