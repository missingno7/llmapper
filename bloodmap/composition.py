from __future__ import annotations

import copy
from dataclasses import dataclass
from fractions import Fraction
from math import ceil, hypot, isqrt
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


@dataclass
class AttachmentResult:
    level: LevelIR
    composition: CompositionResult
    destination_wall: int
    fragment_wall: int
    attached_wall: int
    destination_sector: int
    attached_sector: int
    quarter_turns: int
    dx: int
    dy: int
    dz: int
    vertical_opening: int
    vertical_opening_at_endpoints: tuple[int, int]
    blocking_cleared: bool
    resolved_relationships: list[FragmentRelationship]
    layout_conflicts: list[dict[str, Any]]

    def report(self) -> dict[str, Any]:
        value = self.composition.report()
        value.update({
            "operation": "attach",
            "placement": {
                "quarter_turns": self.quarter_turns,
                "dx": self.dx,
                "dy": self.dy,
                "dz": self.dz,
            },
            "connection": {
                "destination_wall": self.destination_wall,
                "fragment_wall": self.fragment_wall,
                "attached_wall": self.attached_wall,
                "destination_sector": self.destination_sector,
                "attached_sector": self.attached_sector,
                "vertical_opening": self.vertical_opening,
                "vertical_opening_at_endpoints": list(self.vertical_opening_at_endpoints),
                "passable_at_rest": self.vertical_opening > 0 and not (
                    self.level.walls[self.destination_wall]["fields"]["cstat"] & 1
                    or self.level.walls[self.attached_wall]["fields"]["cstat"] & 1
                ),
                "blocking_cleared": self.blocking_cleared,
            },
            "resolved_relationships": [item.to_dict() for item in self.resolved_relationships],
            "layout_check": {
                "status": "pass" if not self.layout_conflicts else "fail",
                "conflicts": self.layout_conflicts,
            },
        })
        return value


@dataclass
class PathwayResult:
    level: LevelIR
    wall_a: int
    wall_b: int
    sector_ids: list[int]
    wall_ids: list[int]
    portal_pairs: list[tuple[int, int]]
    floor_z: list[int]
    ceiling_z: list[int]
    step_heights: list[int]
    portal_openings: list[int]
    route: list[tuple[int, int]]
    layout_conflicts: list[dict[str, Any]]
    blocking_cleared: bool

    def report(self) -> dict[str, Any]:
        return {
            "operation": "connect_with_pathway",
            "endpoint_walls": [self.wall_a, self.wall_b],
            "generated": {
                "sector_ids": self.sector_ids,
                "wall_ids": self.wall_ids,
                "portal_pairs": [list(pair) for pair in self.portal_pairs],
                "floor_z": self.floor_z,
                "ceiling_z": self.ceiling_z,
                "step_heights": self.step_heights,
                "portal_openings": self.portal_openings,
                "route": [list(point) for point in self.route],
            },
            "layout_check": {
                "status": "pass" if not self.layout_conflicts else "fail",
                "conflicts": self.layout_conflicts,
            },
            "blocking_cleared": self.blocking_cleared,
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


def _wall_segment(level: LevelIR, wall_id: int) -> tuple[tuple[int, int], tuple[int, int]]:
    wall = level.walls[wall_id]["fields"]
    end = level.walls[int(wall["point2"])]["fields"]
    return (int(wall["x"]), int(wall["y"])), (int(end["x"]), int(end["y"]))


def _orientation(a: tuple[int, int], b: tuple[int, int], c: tuple[int, int]) -> int:
    value = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return (value > 0) - (value < 0)


def _segment_conflict(
    a: tuple[int, int], b: tuple[int, int], c: tuple[int, int], d: tuple[int, int],
) -> str | None:
    """Return crossing/overlap; endpoint-only contact is intentionally allowed."""
    oa, ob = _orientation(a, b, c), _orientation(a, b, d)
    oc, od = _orientation(c, d, a), _orientation(c, d, b)
    if oa * ob < 0 and oc * od < 0:
        return "crossing"
    if oa == ob == oc == od == 0:
        axis = 0 if abs(b[0] - a[0]) >= abs(b[1] - a[1]) else 1
        left = max(min(a[axis], b[axis]), min(c[axis], d[axis]))
        right = min(max(a[axis], b[axis]), max(c[axis], d[axis]))
        if right > left:
            return "collinear_overlap"
    return None


def _point_in_sector(level: LevelIR, sector_id: int, point: tuple[int, int]) -> int:
    """Return -1 on boundary, 0 outside, and 1 inside (even-odd across all loops)."""
    x, y = point
    sector = level.sectors[sector_id]["fields"]
    first, count = int(sector["wall_ptr"]), int(sector["wall_count"])
    inside = False
    for wall_id in range(first, first + count):
        a, b = _wall_segment(level, wall_id)
        if _orientation(a, b, point) == 0 and (
            min(a[0], b[0]) <= x <= max(a[0], b[0])
            and min(a[1], b[1]) <= y <= max(a[1], b[1])
        ):
            return -1
        if (a[1] > y) != (b[1] > y):
            crossing_x = Fraction(a[0]) + Fraction(
                (y - a[1]) * (b[0] - a[0]), b[1] - a[1]
            )
            if crossing_x > x:
                inside = not inside
    return int(inside)


def find_layout_conflicts(
    level: LevelIR,
    *,
    existing_sector_count: int,
    existing_wall_count: int,
    portal_walls: tuple[int, int] | None = None,
    portal_wall_pairs: list[tuple[int, int]] | None = None,
) -> list[dict[str, Any]]:
    """Find new-vs-existing XY crossings, overlaps, and containment."""
    new_sector_ids = range(existing_sector_count, len(level.sectors))
    new_wall_ids: list[int] = []
    for sector_id in new_sector_ids:
        fields = level.sectors[sector_id]["fields"]
        new_wall_ids.extend(range(int(fields["wall_ptr"]), int(fields["wall_ptr"]) + int(fields["wall_count"])))
    ignored_pairs = {
        frozenset(pair) for pair in (portal_wall_pairs or [])
    }
    if portal_walls is not None:
        ignored_pairs.add(frozenset(portal_walls))
    conflicts: list[dict[str, Any]] = []
    for old_wall in range(existing_wall_count):
        old_segment = _wall_segment(level, old_wall)
        for new_wall in new_wall_ids:
            if frozenset((old_wall, new_wall)) in ignored_pairs:
                continue
            kind = _segment_conflict(*old_segment, *_wall_segment(level, new_wall))
            if kind:
                conflicts.append({
                    "kind": kind,
                    "existing_wall": old_wall,
                    "new_wall": new_wall,
                })

    # Crossings cover interpenetration. These tests cover one footprint wholly
    # inside another without accepting boundary points at the intended doorway.
    for new_wall in new_wall_ids:
        point = _wall_segment(level, new_wall)[0]
        for old_sector in range(existing_sector_count):
            if _point_in_sector(level, old_sector, point) == 1:
                conflicts.append({
                    "kind": "new_inside_existing",
                    "existing_sector": old_sector,
                    "new_wall": new_wall,
                    "point": list(point),
                })
                break
    for old_wall in range(existing_wall_count):
        point = _wall_segment(level, old_wall)[0]
        for new_sector in new_sector_ids:
            if _point_in_sector(level, new_sector, point) == 1:
                conflicts.append({
                    "kind": "existing_inside_new",
                    "existing_wall": old_wall,
                    "new_sector": new_sector,
                    "point": list(point),
                })
                break
    return conflicts


def _sector_surface_z(
    level: LevelIR, sector_id: int, x: int, y: int, surface: str,
) -> int:
    """Evaluate a Blood/Build sector plane at a point using getzsofslope arithmetic."""
    sector = level.sectors[sector_id]["fields"]
    if surface not in {"ceiling", "floor"}:
        raise CompositionError(f"unknown sector surface {surface!r}")
    z = int(sector[f"{surface}_z"])
    if not int(sector[f"{surface}_stat"]) & 2:
        return z
    wall_id = int(sector["wall_ptr"])
    wall = level.walls[wall_id]["fields"]
    next_wall = level.walls[int(wall["point2"])]["fields"]
    dx, dy = int(next_wall["x"]) - int(wall["x"]), int(next_wall["y"]) - int(wall["y"])
    divisor = isqrt(dx * dx + dy * dy) << 5
    if divisor == 0:
        return z
    # NBlood selects ENGINE_19960925, so getzsofslope uses dmulscale3 without
    # the extra EDUKE32 compatibility shift.
    cross = (dx * (y - int(wall["y"])) - dy * (x - int(wall["x"]))) >> 3
    numerator = int(sector[f"{surface}_heinum"]) * cross
    correction = abs(numerator) // divisor
    if numerator < 0:
        correction = -correction
    return z + correction


def _sample_centerline(
    points: list[tuple[float, float]], section_count: int,
) -> list[tuple[float, float]]:
    lengths = [
        hypot(points[index + 1][0] - points[index][0], points[index + 1][1] - points[index][1])
        for index in range(len(points) - 1)
    ]
    if any(length == 0 for length in lengths):
        raise CompositionError("pathway route contains a zero-length leg")
    total = sum(lengths)
    samples: list[tuple[float, float]] = []
    for sample_id in range(section_count + 1):
        distance = total * sample_id / section_count
        traversed = 0.0
        for leg_id, length in enumerate(lengths):
            if distance <= traversed + length or leg_id == len(lengths) - 1:
                ratio = min(1.0, max(0.0, (distance - traversed) / length))
                a, b = points[leg_id], points[leg_id + 1]
                samples.append((
                    a[0] + (b[0] - a[0]) * ratio,
                    a[1] + (b[1] - a[1]) * ratio,
                ))
                break
            traversed += length
    return samples


def connect_with_pathway(
    level: LevelIR,
    wall_a: int,
    wall_b: int,
    *,
    via: list[tuple[int, int]] | None = None,
    sectors: int | None = None,
    max_step_height: int = 2048,
    min_opening: int = 8192,
    clear_blocking: bool = False,
    allow_overlap: bool = False,
) -> PathwayResult:
    """Generate an inert corridor/stair strip between two free room walls.

    Endpoint wall lengths may differ. The generated strip follows an optional
    centerline, interpolates width, and adds enough flat sectors to keep every
    floor transition within ``max_step_height``.
    """
    if wall_a == wall_b:
        raise CompositionError("pathway endpoint walls must be different")
    if not 0 <= wall_a < len(level.walls) or not 0 <= wall_b < len(level.walls):
        raise CompositionError("pathway endpoint wall id is out of range")
    if max_step_height <= 0 or min_opening <= 0:
        raise CompositionError("max_step_height and min_opening must be positive")
    owners = _wall_owners(level)
    owner_a, owner_b = owners[wall_a], owners[wall_b]
    if owner_a is None or owner_b is None or owner_a == owner_b:
        raise CompositionError("pathway endpoints must belong to two different sectors")
    for wall_id in (wall_a, wall_b):
        fields = level.walls[wall_id]["fields"]
        if fields["next_wall"] != -1 or fields["next_sector"] != -1:
            raise CompositionError(f"pathway endpoint wall {wall_id} must be one-sided")

    a0, a1 = _wall_segment(level, wall_a)
    b0, b1 = _wall_segment(level, wall_b)
    width_a, width_b = hypot(a1[0] - a0[0], a1[1] - a0[1]), hypot(b1[0] - b0[0], b1[1] - b0[1])
    if width_a == 0 or width_b == 0:
        raise CompositionError("pathway endpoint walls must have nonzero length")

    endpoint_points = ((a0, a1, owner_a), (b0, b1, owner_b))
    endpoint_floors: list[int] = []
    endpoint_ceilings: list[int] = []
    for start, end, sector_id in endpoint_points:
        floors = [_sector_surface_z(level, sector_id, *point, "floor") for point in (start, end)]
        ceilings = [_sector_surface_z(level, sector_id, *point, "ceiling") for point in (start, end)]
        endpoint_floors.append(round(sum(floors) / 2))
        endpoint_ceilings.append(round(sum(ceilings) / 2))

    floor_delta = abs(endpoint_floors[1] - endpoint_floors[0])
    required_for_height = 1 if floor_delta == 0 else ceil(floor_delta / max_step_height) + 1
    center_a = ((a0[0] + a1[0]) / 2, (a0[1] + a1[1]) / 2)
    center_b = ((b0[0] + b1[0]) / 2, (b0[1] + b1[1]) / 2)
    route_points = [center_a, *[(float(x), float(y)) for x, y in (via or [])], center_b]
    required_for_route = len(route_points) - 1
    required_sectors = max(1, required_for_height, required_for_route)
    sector_count = required_sectors if sectors is None else int(sectors)
    if sector_count < required_sectors:
        raise CompositionError(
            f"pathway requires at least {required_sectors} sectors for its route and elevation; "
            f"got {sector_count}"
        )

    centers = _sample_centerline(route_points, sector_count)
    sections: list[tuple[tuple[int, int], tuple[int, int]]] = [(a1, a0)]
    previous_vector = (a1[0] - a0[0], a1[1] - a0[1])
    for index in range(1, sector_count):
        before, after = centers[index - 1], centers[index + 1]
        tx, ty = after[0] - before[0], after[1] - before[1]
        length = hypot(tx, ty)
        if length == 0:
            raise CompositionError("pathway sampling produced a zero-length tangent")
        width = width_a + (width_b - width_a) * index / sector_count
        px, py = -ty / length * width / 2, tx / length * width / 2
        candidate = (px * 2, py * 2)
        if candidate[0] * previous_vector[0] + candidate[1] * previous_vector[1] < 0:
            px, py = -px, -py
        center = centers[index]
        left = (round(center[0] + px), round(center[1] + py))
        right = (round(center[0] - px), round(center[1] - py))
        if left == right:
            raise CompositionError("pathway interpolation collapsed to zero width")
        sections.append((left, right))
        previous_vector = (left[0] - right[0], left[1] - right[1])
    sections.append((b0, b1))

    if sector_count == 1:
        floor_z = [endpoint_floors[0]]
        ceiling_z = [endpoint_ceilings[0]]
        if endpoint_floors[0] != endpoint_floors[1]:
            raise CompositionError("one-sector pathway cannot represent differing floor heights")
    else:
        floor_z = [
            round(endpoint_floors[0] + (endpoint_floors[1] - endpoint_floors[0]) * index / (sector_count - 1))
            for index in range(sector_count)
        ]
        ceiling_z = [
            round(endpoint_ceilings[0] + (endpoint_ceilings[1] - endpoint_ceilings[0]) * index / (sector_count - 1))
            for index in range(sector_count)
        ]
    for index, (ceiling, floor) in enumerate(zip(ceiling_z, floor_z)):
        if floor - ceiling < min_opening:
            raise CompositionError(
                f"generated pathway sector {index} has {floor - ceiling} Z units of clearance; "
                f"minimum is {min_opening}"
            )

    result = copy.deepcopy(level)
    old_sector_count, old_wall_count = len(result.sectors), len(result.walls)
    sector_ids: list[int] = []
    wall_ids: list[int] = []
    for index in range(sector_count):
        sector_id = len(result.sectors)
        first_wall = len(result.walls)
        sector = copy.deepcopy(level.sectors[owner_a])
        sector["id"] = sector_id
        sector["blood"] = None
        sector["fields"].update(
            wall_ptr=first_wall, wall_count=4, ceiling_z=ceiling_z[index], floor_z=floor_z[index],
            ceiling_heinum=0, floor_heinum=0, extra=-1, type=0, hitag=0,
        )
        sector["fields"]["ceiling_stat"] &= ~2
        sector["fields"]["floor_stat"] &= ~2
        result.sectors.append(sector)
        sector_ids.append(sector_id)

        left, right = sections[index]
        next_left, next_right = sections[index + 1]
        points = [left, right, next_right, next_left]
        for point_id, (x, y) in enumerate(points):
            wall_id = len(result.walls)
            wall = copy.deepcopy(level.walls[wall_a])
            wall["id"] = wall_id
            wall["blood"] = None
            wall["fields"].update(
                x=x, y=y, point2=first_wall + (point_id + 1) % 4,
                next_wall=-1, next_sector=-1, cstat=0, extra=-1, type=0, hitag=0,
            )
            result.walls.append(wall)
            wall_ids.append(wall_id)

    portal_pairs = [(wall_a, wall_ids[0])]
    portal_pairs.extend(
        (wall_ids[index * 4 + 2], wall_ids[(index + 1) * 4])
        for index in range(sector_count - 1)
    )
    portal_pairs.append((wall_b, wall_ids[-2]))

    internal_pairs = {frozenset(pair) for pair in portal_pairs[1:-1]}
    layout_conflicts = find_layout_conflicts(
        result,
        existing_sector_count=old_sector_count,
        existing_wall_count=old_wall_count,
        portal_wall_pairs=[portal_pairs[0], portal_pairs[-1]],
    )
    for left_index, left_wall in enumerate(wall_ids):
        left_segment = _wall_segment(result, left_wall)
        for right_wall in wall_ids[left_index + 1:]:
            if frozenset((left_wall, right_wall)) in internal_pairs:
                continue
            kind = _segment_conflict(*left_segment, *_wall_segment(result, right_wall))
            if kind:
                layout_conflicts.append({
                    "kind": "pathway_" + kind,
                    "new_wall_a": left_wall,
                    "new_wall_b": right_wall,
                })
    if layout_conflicts and not allow_overlap:
        raise CompositionError(
            f"generated pathway overlaps level geometry: {layout_conflicts[0]}; "
            "adjust the room placement or route"
        )

    all_owners = _wall_owners(result)
    for left_wall, right_wall in portal_pairs:
        left_owner, right_owner = all_owners[left_wall], all_owners[right_wall]
        if left_owner is None or right_owner is None:
            raise CompositionError("generated pathway portal has no owning sector")
        result.walls[left_wall]["fields"].update(next_wall=right_wall, next_sector=right_owner)
        result.walls[right_wall]["fields"].update(next_wall=left_wall, next_sector=left_owner)

    blocking_cleared = False
    for endpoint in (wall_a, wall_b):
        if result.walls[endpoint]["fields"]["cstat"] & 1:
            if not clear_blocking:
                raise CompositionError(
                    f"pathway endpoint wall {endpoint} blocks movement; use clear_blocking=True"
                )
            result.walls[endpoint]["fields"]["cstat"] &= ~1
            blocking_cleared = True

    portal_openings: list[int] = []
    step_heights: list[int] = []
    for left_wall, right_wall in portal_pairs:
        left_owner, right_owner = all_owners[left_wall], all_owners[right_wall]
        points = _wall_segment(result, left_wall)
        openings: list[int] = []
        steps_at_portal: list[int] = []
        for x, y in points:
            left_floor = _sector_surface_z(result, int(left_owner), x, y, "floor")
            right_floor = _sector_surface_z(result, int(right_owner), x, y, "floor")
            left_ceiling = _sector_surface_z(result, int(left_owner), x, y, "ceiling")
            right_ceiling = _sector_surface_z(result, int(right_owner), x, y, "ceiling")
            openings.append(min(left_floor, right_floor) - max(left_ceiling, right_ceiling))
            steps_at_portal.append(abs(left_floor - right_floor))
        portal_opening, step_height = min(openings), max(steps_at_portal)
        if portal_opening < min_opening:
            raise CompositionError(
                f"pathway portal {left_wall}/{right_wall} has {portal_opening} Z units of opening; "
                f"minimum is {min_opening}"
            )
        if step_height > max_step_height:
            raise CompositionError(
                f"pathway portal {left_wall}/{right_wall} has step height {step_height}; "
                f"maximum is {max_step_height}"
            )
        portal_openings.append(portal_opening)
        step_heights.append(step_height)

    result.metadata["source_crc32"] = "00000000"
    errors = [item for item in validate_map(result.to_disk_map()) if item.severity == "error"]
    if errors:
        first = errors[0]
        raise CompositionError(
            f"generated pathway violates structure: {first.code} at {first.location}: {first.message}"
        )
    return PathwayResult(
        level=result,
        wall_a=wall_a,
        wall_b=wall_b,
        sector_ids=sector_ids,
        wall_ids=wall_ids,
        portal_pairs=portal_pairs,
        floor_z=floor_z,
        ceiling_z=ceiling_z,
        step_heights=step_heights,
        portal_openings=portal_openings,
        route=[(round(x), round(y)) for x, y in centers],
        layout_conflicts=layout_conflicts,
        blocking_cleared=blocking_cleared,
    )


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


def attach_fragment(
    level: LevelIR,
    fragment: LevelFragment,
    *,
    destination_wall: int,
    fragment_wall: int,
    dz: int = 0,
    quarter_turns: int | None = None,
    channel_policy: str = "error",
    clear_blocking: bool = False,
    allow_blocked: bool = False,
    allow_overlap: bool = False,
) -> AttachmentResult:
    """Align a fragment wall to a destination wall, reject overlap, and connect it."""
    _validate_fragment_identity(fragment)
    if clear_blocking and allow_blocked:
        raise CompositionError("clear_blocking and allow_blocked are mutually exclusive")
    if not 0 <= destination_wall < len(level.walls):
        raise CompositionError(f"destination wall {destination_wall} is out of range")
    if not 0 <= fragment_wall < len(fragment.walls):
        raise CompositionError(f"fragment wall {fragment_wall} is out of range")

    destination_owners = _wall_owners(level)
    destination_sector = destination_owners[destination_wall]
    if destination_sector is None:
        raise CompositionError(f"destination wall {destination_wall} has no owning sector")

    destination = level.walls[destination_wall]["fields"]
    source = fragment.walls[fragment_wall]["fields"]
    if destination["next_wall"] != -1 or destination["next_sector"] != -1:
        raise CompositionError("destination attachment wall must be one-sided")
    if source["next_wall"] != -1 or source["next_sector"] != -1:
        raise CompositionError("fragment attachment wall must be one-sided")
    if not 0 <= destination["point2"] < len(level.walls):
        raise CompositionError("destination attachment wall has an invalid point2")
    if not 0 <= source["point2"] < len(fragment.walls):
        raise CompositionError("fragment attachment wall has an invalid point2")

    destination_end = level.walls[destination["point2"]]["fields"]
    source_end = fragment.walls[source["point2"]]["fields"]
    destination_vector = (
        destination_end["x"] - destination["x"],
        destination_end["y"] - destination["y"],
    )
    source_vector = (source_end["x"] - source["x"], source_end["y"] - source["y"])
    destination_length = destination_vector[0] ** 2 + destination_vector[1] ** 2
    source_length = source_vector[0] ** 2 + source_vector[1] ** 2
    if destination_length == 0 or source_length == 0:
        raise CompositionError("attachment walls must have nonzero length")
    if destination_length != source_length:
        raise CompositionError("attachment walls must have equal length")

    def rotate(x: int, y: int, turns: int) -> tuple[int, int]:
        for _ in range(turns):
            x, y = -y, x
        return x, y

    turns_to_try = [quarter_turns % 4] if quarter_turns is not None else list(range(4))
    placement: tuple[int, int, int] | None = None
    for turns in turns_to_try:
        start_x, start_y = rotate(source["x"], source["y"], turns)
        end_x, end_y = rotate(source_end["x"], source_end["y"], turns)
        dx, dy = destination_end["x"] - start_x, destination_end["y"] - start_y
        if (end_x + dx, end_y + dy) == (destination["x"], destination["y"]):
            placement = turns, dx, dy
            break
    if placement is None:
        qualifier = f" with quarter_turns={quarter_turns % 4}" if quarter_turns is not None else ""
        raise CompositionError(
            "attachment walls cannot be aligned by an exact quarter-turn rotation" + qualifier
        )
    turns, dx, dy = placement

    destination_blocking = bool(destination["cstat"] & 1)
    source_blocking = bool(source["cstat"] & 1)
    if (destination_blocking or source_blocking) and not (clear_blocking or allow_blocked):
        raise CompositionError(
            "attachment wall blocks movement; use clear_blocking=True or allow_blocked=True explicitly"
        )

    composition = insert_fragment(
        level, fragment, dx=dx, dy=dy, dz=dz, quarter_turns=turns,
        channel_policy=channel_policy,
    )
    attached_wall = composition.allocations["wall"].resolve(fragment_wall)
    attached_owners = _wall_owners(composition.level)
    attached_sector = attached_owners[attached_wall]
    if attached_sector is None:
        raise CompositionError(f"attached wall {attached_wall} has no owning sector")

    layout_conflicts = find_layout_conflicts(
        composition.level,
        existing_sector_count=len(level.sectors),
        existing_wall_count=len(level.walls),
        portal_walls=(destination_wall, attached_wall),
    )
    if layout_conflicts and not allow_overlap:
        first = layout_conflicts[0]
        raise CompositionError(
            f"attached fragment overlaps existing layout: {first}; "
            "use allow_overlap=True only for intentional stacked geometry"
        )
    if layout_conflicts:
        composition.warnings.append(
            f"attachment allowed {len(layout_conflicts)} intentional layout conflict(s)"
        )

    portal_points = (
        (int(destination["x"]), int(destination["y"])),
        (int(destination_end["x"]), int(destination_end["y"])),
    )
    opening_at_endpoints: list[int] = []
    for x, y in portal_points:
        destination_ceiling = _sector_surface_z(
            composition.level, destination_sector, x, y, "ceiling",
        )
        destination_floor = _sector_surface_z(
            composition.level, destination_sector, x, y, "floor",
        )
        attached_ceiling = _sector_surface_z(
            composition.level, attached_sector, x, y, "ceiling",
        )
        attached_floor = _sector_surface_z(
            composition.level, attached_sector, x, y, "floor",
        )
        opening_at_endpoints.append(
            min(destination_floor, attached_floor) - max(destination_ceiling, attached_ceiling)
        )
    vertical_opening_at_endpoints = tuple(opening_at_endpoints)
    vertical_opening = min(vertical_opening_at_endpoints)
    if vertical_opening <= 0 and not allow_blocked:
        raise CompositionError(
            "attached sectors have no vertical opening at rest; use allow_blocked=True explicitly"
        )

    connected = connect_portals(composition.level, destination_wall, attached_wall)
    blocking_cleared = False
    if clear_blocking:
        for wall_id in (destination_wall, attached_wall):
            fields = connected.walls[wall_id]["fields"]
            if fields["cstat"] & 1:
                fields["cstat"] &= ~1
                blocking_cleared = True

    resolved = [
        item for item in composition.unresolved_relationships
        if item.classification == "external_geometry"
        and item.source.get("space") == "fragment"
        and item.source.get("kind") == "wall"
        and item.source.get("id") == fragment_wall
    ]
    composition.unresolved_relationships = [
        item for item in composition.unresolved_relationships if item not in resolved
    ]
    if vertical_opening <= 0:
        composition.warnings.append("attached portal has no vertical opening at rest")
    if allow_blocked and (destination_blocking or source_blocking):
        composition.warnings.append("attached portal retains a movement-blocking wall flag")

    errors = [item for item in validate_map(connected.to_disk_map()) if item.severity == "error"]
    if errors:
        first = errors[0]
        raise CompositionError(
            f"attached fragment violates structure: {first.code} at {first.location}: {first.message}"
        )
    return AttachmentResult(
        level=connected,
        composition=composition,
        destination_wall=destination_wall,
        fragment_wall=fragment_wall,
        attached_wall=attached_wall,
        destination_sector=destination_sector,
        attached_sector=attached_sector,
        quarter_turns=turns,
        dx=dx,
        dy=dy,
        dz=dz,
        vertical_opening=vertical_opening,
        vertical_opening_at_endpoints=vertical_opening_at_endpoints,
        blocking_cleared=blocking_cleared,
        resolved_relationships=resolved,
        layout_conflicts=layout_conflicts,
    )
