from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from .analysis import validate_map
from .fragment import FragmentError, FragmentRelationship, LevelFragment, SYSTEM_CHANNELS
from .model import LevelIR


class CompositionError(ValueError):
    pass


@dataclass(frozen=True)
class DestinationMap:
    kind: str
    fragment_to_destination: dict[int, int]

    def resolve(self, fragment_id: int) -> int:
        try:
            return self.fragment_to_destination[fragment_id]
        except KeyError as exc:
            raise CompositionError(f"{self.kind} fragment id {fragment_id} was not allocated") from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "fragment_to_destination": {
                str(key): value for key, value in sorted(self.fragment_to_destination.items())
            },
        }


@dataclass
class CompositionResult:
    level: LevelIR
    allocations: dict[str, DestinationMap]
    channel_map: dict[int, int]
    unresolved_relationships: list[FragmentRelationship]
    warnings: list[str]

    def report(self) -> dict[str, Any]:
        return {
            "allocations": {name: value.to_dict() for name, value in sorted(self.allocations.items())},
            "channel_map": {str(key): value for key, value in sorted(self.channel_map.items())},
            "unresolved_relationships": [value.to_dict() for value in self.unresolved_relationships],
            "warnings": list(self.warnings),
            "result_counts": {
                "sectors": len(self.level.sectors),
                "walls": len(self.level.walls),
                "sprites": len(self.level.sprites),
            },
        }


def _blood(item: dict[str, Any]) -> dict[str, int] | None:
    extra = item.get("blood")
    return None if extra is None else extra["fields"]


def _used_channels(level: LevelIR) -> set[int]:
    result: set[int] = set()
    for objects in (level.sectors, level.walls, level.sprites):
        for item in objects:
            fields = _blood(item)
            if fields is not None:
                result.update(value for value in (fields["tx_id"], fields["rx_id"]) if value)
    return result


def _fragment_channels(fragment: LevelFragment) -> set[int]:
    result: set[int] = set()
    for objects in (fragment.sectors, fragment.walls, fragment.sprites):
        for item in objects:
            fields = _blood(item)
            if fields is not None:
                result.update(value for value in (fields["tx_id"], fields["rx_id"]) if value)
    return result


def _validate_fragment_identity(fragment: LevelFragment) -> None:
    for kind, objects in (
        ("sector", fragment.sectors), ("wall", fragment.walls), ("sprite", fragment.sprites),
    ):
        actual = [int(item["id"]) for item in objects]
        expected = list(range(len(objects)))
        if actual != expected:
            raise CompositionError(
                f"fragment {kind} IDs must be dense and ordered as {expected}, got {actual}"
            )


def _allocate_channels(
    level: LevelIR, fragment: LevelFragment, policy: str,
) -> tuple[dict[int, int], list[str]]:
    if policy not in {"error", "remap"}:
        raise CompositionError(f"unsupported channel policy {policy!r}")
    used = _used_channels(level)
    fragment_channels = _fragment_channels(fragment)
    result: dict[int, int] = {}
    warnings: list[str] = []
    reserved = set(used)

    def allocate_user_channel() -> int:
        for candidate in range(100, 1024):
            if candidate not in reserved:
                reserved.add(candidate)
                return candidate
        raise CompositionError("no free Blood user channel remains in 100..1023")

    for channel in sorted(fragment_channels):
        if not 0 < channel < 1024:
            raise CompositionError(f"channel {channel} is outside the Blood field range 1..1023")
        if channel in SYSTEM_CHANNELS:
            result[channel] = channel
            continue
        if channel < 100:
            if channel in used:
                raise CompositionError(
                    f"undefined/reserved channel {channel} collides with destination and cannot be safely remapped"
                )
            result[channel] = channel
            warnings.append(f"undefined channel {channel} preserved without invented semantics")
            reserved.add(channel)
            continue
        if channel in used:
            if policy == "error":
                raise CompositionError(
                    f"user channel {channel} collides with destination; use channel_policy='remap' explicitly"
                )
            result[channel] = allocate_user_channel()
        else:
            result[channel] = channel
            reserved.add(channel)
    return result, warnings


def _used_extra_ids(objects: list[dict[str, Any]]) -> set[int]:
    return {item["fields"]["extra"] for item in objects if item["fields"]["extra"] > 0}


def _allocate_extra_map(
    kind: str, fragment_objects: list[dict[str, Any]], destination_objects: list[dict[str, Any]], limit: int,
) -> DestinationMap:
    used = _used_extra_ids(destination_objects)
    local_ids = sorted({item["fields"]["extra"] for item in fragment_objects if item["fields"]["extra"] > 0})
    mapping: dict[int, int] = {}
    candidate = 1
    for local_id in local_ids:
        while candidate in used and candidate < limit:
            candidate += 1
        if candidate >= limit:
            raise CompositionError(f"no free {kind} index remains below {limit}")
        mapping[local_id] = candidate
        used.add(candidate)
        candidate += 1
    return DestinationMap(kind, mapping)


def transform_fragment(
    fragment: LevelFragment, *, dx: int = 0, dy: int = 0, dz: int = 0,
    quarter_turns: int = 0, pivot_x: int = 0, pivot_y: int = 0,
) -> LevelFragment:
    """Return a transformed copy without changing relationship/index identity."""
    result = copy.deepcopy(fragment)
    turns = quarter_turns % 4

    def point(x: int, y: int) -> tuple[int, int]:
        x, y = x - pivot_x, y - pivot_y
        for _ in range(turns):
            x, y = -y, x
        return x + pivot_x + dx, y + pivot_y + dy

    for wall in result.walls:
        fields = wall["fields"]
        fields["x"], fields["y"] = point(fields["x"], fields["y"])
    for sprite in result.sprites:
        fields = sprite["fields"]
        fields["x"], fields["y"] = point(fields["x"], fields["y"])
        fields["z"] += dz
        if turns:
            fields["angle"] = (fields["angle"] + 512 * turns) & 2047
        blood = _blood(sprite)
        if blood is not None:
            blood["target_x"], blood["target_y"] = point(blood["target_x"], blood["target_y"])
            blood["target_z"] += dz
            if turns:
                blood["goal_angle"] = (blood["goal_angle"] + 512 * turns) & 2047
    for sector in result.sectors:
        fields = sector["fields"]
        fields["ceiling_z"] += dz
        fields["floor_z"] += dz
        blood = _blood(sector)
        if blood is not None:
            for name in ("off_ceiling_z", "on_ceiling_z", "off_floor_z", "on_floor_z"):
                blood[name] += dz
            if turns:
                blood["pan_angle"] = (blood["pan_angle"] + 512 * turns) & 2047
                blood["wind_angle"] = (blood["wind_angle"] + 512 * turns) & 2047
    return result


def insert_fragment(
    level: LevelIR,
    fragment: LevelFragment,
    *,
    dx: int = 0,
    dy: int = 0,
    dz: int = 0,
    quarter_turns: int = 0,
    pivot_x: int = 0,
    pivot_y: int = 0,
    channel_policy: str = "error",
) -> CompositionResult:
    """Append a fragment with deterministic allocation and no implicit connections."""
    _validate_fragment_identity(fragment)
    fragment = transform_fragment(
        fragment, dx=dx, dy=dy, dz=dz, quarter_turns=quarter_turns,
        pivot_x=pivot_x, pivot_y=pivot_y,
    )
    result = copy.deepcopy(level)
    sector_base, wall_base, sprite_base = len(result.sectors), len(result.walls), len(result.sprites)
    if sector_base + len(fragment.sectors) > 1024:
        raise CompositionError("composition exceeds the v7 sector limit 1024")
    if wall_base + len(fragment.walls) > 8192:
        raise CompositionError("composition exceeds the v7 wall limit 8192")
    if sprite_base + len(fragment.sprites) > 4096:
        raise CompositionError("composition exceeds the v7 sprite limit 4096")

    sector_map = DestinationMap("sector", {i: sector_base + i for i in range(len(fragment.sectors))})
    wall_map = DestinationMap("wall", {i: wall_base + i for i in range(len(fragment.walls))})
    sprite_map = DestinationMap("sprite", {i: sprite_base + i for i in range(len(fragment.sprites))})
    xsector_map = _allocate_extra_map("xsector", fragment.sectors, result.sectors, 1024)
    xwall_map = _allocate_extra_map("xwall", fragment.walls, result.walls, 8192)
    xsprite_map = _allocate_extra_map("xsprite", fragment.sprites, result.sprites, 4096)
    allocations = {
        "sector": sector_map, "wall": wall_map, "sprite": sprite_map,
        "xsector": xsector_map, "xwall": xwall_map, "xsprite": xsprite_map,
    }
    channel_map, warnings = _allocate_channels(result, fragment, channel_policy)

    def prepare(item: dict[str, Any], kind: str, local_id: int) -> dict[str, Any]:
        value = copy.deepcopy(item)
        value.pop("source_id", None)
        value["id"] = allocations[kind].resolve(local_id)
        fields = value["fields"]
        if fields["extra"] > 0:
            fields["extra"] = allocations["x" + kind].resolve(fields["extra"])
        blood = _blood(value)
        if blood is not None:
            blood["reference"] = value["id"]
            for name in ("tx_id", "rx_id"):
                if blood[name]:
                    blood[name] = channel_map[blood[name]]
        return value

    for local_id, fragment_sector in enumerate(fragment.sectors):
        value = prepare(fragment_sector, "sector", local_id)
        fields = value["fields"]
        fields["wall_ptr"] = wall_map.resolve(fields["wall_ptr"])
        blood = _blood(value)
        if blood is not None:
            for name in ("marker_0", "marker_1"):
                if blood[name] >= 0:
                    blood[name] = sprite_map.resolve(blood[name])
        result.sectors.append(value)

    for local_id, fragment_wall in enumerate(fragment.walls):
        value = prepare(fragment_wall, "wall", local_id)
        fields = value["fields"]
        fields["point2"] = wall_map.resolve(fields["point2"])
        if fields["next_wall"] >= 0 or fields["next_sector"] >= 0:
            if fields["next_wall"] < 0 or fields["next_sector"] < 0:
                raise CompositionError(f"fragment wall {local_id} has a partial portal reference")
            fields["next_wall"] = wall_map.resolve(fields["next_wall"])
            fields["next_sector"] = sector_map.resolve(fields["next_sector"])
        result.walls.append(value)

    for local_id, fragment_sprite in enumerate(fragment.sprites):
        value = prepare(fragment_sprite, "sprite", local_id)
        fields = value["fields"]
        fields["sector"] = sector_map.resolve(fields["sector"])
        fields["index"] = value["id"]
        if fields["owner"] >= 0:
            fields["owner"] = sprite_map.resolve(fields["owner"])
        blood = _blood(value)
        if blood is not None:
            for name in ("target", "burn_source"):
                if blood[name] >= 0:
                    blood[name] = sprite_map.resolve(blood[name])
        result.sprites.append(value)

    result.metadata["source_crc32"] = "00000000"
    errors = [item for item in validate_map(result.to_disk_map()) if item.severity == "error"]
    if errors:
        first = errors[0]
        raise CompositionError(
            f"inserted fragment violates structure: {first.code} at {first.location}: {first.message}"
        )
    unresolved = [
        value for value in fragment.relationships
        if value.classification in {
            "external_geometry", "external_trigger", "external_marker", "external_ownership",
        }
    ]
    return CompositionResult(result, allocations, channel_map, unresolved, warnings)


def _wall_owners(level: LevelIR) -> list[int | None]:
    owners: list[int | None] = [None] * len(level.walls)
    for sector_id, sector in enumerate(level.sectors):
        first, count = sector["fields"]["wall_ptr"], sector["fields"]["wall_count"]
        for wall_id in range(first, first + count):
            if not 0 <= wall_id < len(owners):
                raise CompositionError(f"sector {sector_id} has an invalid wall range")
            if owners[wall_id] is not None:
                raise CompositionError(f"wall {wall_id} is owned by multiple sectors")
            owners[wall_id] = sector_id
    return owners


def connect_portals(level: LevelIR, wall_a: int, wall_b: int) -> LevelIR:
    """Connect two reversed, coincident one-sided walls as a reciprocal portal."""
    if wall_a == wall_b:
        raise CompositionError("a wall cannot be connected to itself")
    if not 0 <= wall_a < len(level.walls) or not 0 <= wall_b < len(level.walls):
        raise CompositionError("portal wall id is out of range")
    owners = _wall_owners(level)
    sector_a, sector_b = owners[wall_a], owners[wall_b]
    if sector_a is None or sector_b is None or sector_a == sector_b:
        raise CompositionError("portal walls must belong to two different sectors")
    a, b = level.walls[wall_a]["fields"], level.walls[wall_b]["fields"]
    if a["next_wall"] != -1 or a["next_sector"] != -1 or b["next_wall"] != -1 or b["next_sector"] != -1:
        raise CompositionError("both portal walls must currently be one-sided")
    a_end = level.walls[a["point2"]]["fields"]
    b_end = level.walls[b["point2"]]["fields"]
    if (a["x"], a["y"]) != (b_end["x"], b_end["y"]) or (a_end["x"], a_end["y"]) != (b["x"], b["y"]):
        raise CompositionError("portal walls are not coincident with reversed endpoints")
    result = copy.deepcopy(level)
    result.walls[wall_a]["fields"].update(next_wall=wall_b, next_sector=sector_b)
    result.walls[wall_b]["fields"].update(next_wall=wall_a, next_sector=sector_a)
    result.metadata["source_crc32"] = "00000000"
    errors = [item for item in validate_map(result.to_disk_map()) if item.severity == "error"]
    if errors:
        raise CompositionError(f"portal connection failed validation: {errors[0].message}")
    return result
