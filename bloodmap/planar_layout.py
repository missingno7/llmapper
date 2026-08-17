"""Planar authored layout: semantic regions compiled into valid LevelIR.

Wall indices are compiler output. Design identity lives on region, connection,
and partition IDs. Partial collinear overlaps and T-junctions are split into
atomic reversed coincidences before portals are paired. Proper crossings fail.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from math import hypot
from typing import Any, Iterable, Sequence

from .analysis import validate_map
from .construction import ConstructionError, LevelBuilder, SectorAllocation, new_level
from .format import SECTOR_FIELDS, WALL_FIELDS
from .geometry_audit import (
    AuthoredGeometryError,
    construction_preflight,
    validate_authored_level,
)
from .model import LevelIR
from .planar_geom import (
    Point,
    Segment,
    area2,
    atomic_subsegments,
    classify_segment_pair,
    collinear_overlap_interval,
    exact_reversed,
    integer_intersection,
    loops_equivalent,
    on_segment_inclusive,
    on_segment_strict,
    point_in_loop,
    point_in_loops,
    polygon_relation,
    t_junction_point,
    undirected_key,
    validate_loop,
    z_interval,
    z_relation,
)

SCHEMA = "llmapper.planar-layout"
SCHEMA_VERSION = 1

PORTAL_ROLES = {"portal", "doorway", "window"}
PARTITION_ROLES = {
    "solid_boundary", "thin_partition", "masked_partition", "breakable_partition",
}


class PlanarLayoutError(AuthoredGeometryError):
    pass


def _empty(schema) -> dict[str, int]:
    return {str(item[0]): 0 for item in schema}


def _connection_has_face(connection: ConnectionSpec) -> bool:
    return any(
        value is not None
        for value in (
            connection.face_picnum, connection.face_over_picnum, connection.face_shade,
            connection.face_cstat, connection.face_x_repeat, connection.face_y_repeat,
        )
    )


def _cycle(points: Sequence[Point]) -> tuple[Point, ...]:
    return tuple((int(x), int(y)) for x, y in points)


@dataclass
class RegionSpec:
    region_id: str
    outer: tuple[Point, ...]
    holes: tuple[tuple[Point, ...], ...] = ()
    ceiling_z: int = -24576
    floor_z: int = 8192
    ceiling_picnum: int = 385
    floor_picnum: int = 292
    wall_picnum: int = 180
    ceiling_shade: int = 0
    floor_shade: int = 16
    wall_shade: int = 8
    role: str = "gameplay"
    layer: str = "ground"
    special: str | None = None
    parallax_ceiling: bool = False
    type: int = 0
    declared_zero_exit: bool = False
    stack_pair: str | None = None
    sector_behavior: dict[str, int] = field(default_factory=dict)
    intent: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectionSpec:
    connection_id: str
    region_a: str
    region_b: str
    role: str = "portal"
    a1: Point | None = None
    a2: Point | None = None
    min_width: int = 512
    min_opening: int = 8192
    gated: bool = False
    wall_behavior: dict[str, int] = field(default_factory=dict)
    attach_policy: str = "single_atomic"
    face_picnum: int | None = None
    face_over_picnum: int | None = None
    face_shade: int | None = None
    face_cstat: int | None = None
    face_x_repeat: int | None = None
    face_y_repeat: int | None = None


@dataclass
class PartitionSpec:
    partition_id: str
    region_a: str
    region_b: str | None
    role: str = "thin_partition"
    a1: Point | None = None
    a2: Point | None = None
    wall_behavior: dict[str, int] = field(default_factory=dict)


@dataclass
class PlacementSpec:
    placement_id: str
    region_id: str
    x: int
    y: int
    z: int
    type: int = 0
    picnum: int = 0
    status: int = 0
    angle: int = 0
    cstat: int = 128
    x_repeat: int = 64
    y_repeat: int = 64
    shade: int = 0
    pal: int = 0
    behavior: dict[str, int] = field(default_factory=dict)
    anchor: dict[str, Any] | None = None


@dataclass
class PlayerStartSpec:
    region_id: str
    x: int
    y: int
    z: int
    angle: int = 0


@dataclass
class SourceEdge:
    edge_id: str
    region_id: str
    a: Point
    b: Point


@dataclass
class AtomicEdge:
    atomic_id: str
    source_id: str
    region_id: str
    a: Point
    b: Point


@dataclass
class ConservationReport:
    source_directed_edges: int
    emitted_directed_edges: int
    dropped_source_edges: list[str]
    duplicated_source_edges: list[str]
    unpaired_portal_candidates: list[str]
    split_count: int
    atomic_segments: int
    walls_owned_once: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_directed_edges": self.source_directed_edges,
            "emitted_directed_edges": self.emitted_directed_edges,
            "dropped_source_edges": list(self.dropped_source_edges),
            "duplicated_source_edges": list(self.duplicated_source_edges),
            "unpaired_portal_candidates": list(self.unpaired_portal_candidates),
            "split_count": self.split_count,
            "atomic_segments": self.atomic_segments,
            "walls_owned_once": self.walls_owned_once,
            "conserved": self.conserved,
        }

    @property
    def conserved(self) -> bool:
        return (
            not self.dropped_source_edges
            and not self.duplicated_source_edges
            and self.walls_owned_once
        )


@dataclass
class CompiledLayout:
    level: LevelIR
    allocations: dict[str, SectorAllocation]
    wall_from_atomic: dict[str, int]
    conservation: ConservationReport
    connection_report: list[dict[str, Any]]
    declared_specials: list[tuple[int, int, str]]
    layout: "PlanarLayout"

    def to_dict(self) -> dict[str, Any]:
        return {
            "$schema": "llmapper.compiled-layout",
            "schema_version": 1,
            "allocations": {
                key: {"sector_id": value.sector_id, "wall_ids": list(value.wall_ids)}
                for key, value in self.allocations.items()
            },
            "conservation": self.conservation.to_dict(),
            "connection_report": self.connection_report,
            "declared_specials": [
                {"sectors": [a, b], "kind": kind} for a, b, kind in self.declared_specials
            ],
        }


class PlanarLayout:
    """Replayable source representation above LevelIR."""

    def __init__(self, *, visibility: int = 800, name: str = ""):
        self.name = name
        self.visibility = int(visibility)
        self.regions: dict[str, RegionSpec] = {}
        self.connections: dict[str, ConnectionSpec] = {}
        self.partitions: dict[str, PartitionSpec] = {}
        self.placements: list[PlacementSpec] = []
        self.player_start: PlayerStartSpec | None = None
        self.special_pairs: list[tuple[str, str, str]] = []

    def add_region(
        self,
        region_id: str,
        outer: Iterable[tuple[int, int]],
        *,
        holes: Iterable[Iterable[tuple[int, int]]] = (),
        **kwargs: Any,
    ) -> str:
        if region_id in self.regions:
            raise PlanarLayoutError(f"duplicate region id {region_id!r}")
        hole_tuples = tuple(_cycle(list(item)) for item in holes)
        self.regions[region_id] = RegionSpec(
            region_id=region_id, outer=_cycle(list(outer)), holes=hole_tuples, **kwargs,
        )
        return region_id

    def carve_hole(self, host_id: str, footprint: Iterable[tuple[int, int]]) -> None:
        host = self._region(host_id)
        hole = _cycle(list(footprint))
        if area2(hole) > 0:
            hole = tuple(reversed(hole))
        errors = validate_loop(hole, role="hole")
        if errors:
            raise PlanarLayoutError(f"hole for {host_id}: {errors[0]}")
        if point_in_loop(hole[0], host.outer) == 0 and point_in_loops(hole[0], [host.outer]) != 1:
            sample = hole[0]
            if point_in_loop(sample, host.outer) != 1 and point_in_loop(sample, host.outer) != -1:
                # centroid-like: require at least one vertex inside or on host
                if not any(point_in_loop(point, host.outer) != 0 for point in hole):
                    raise PlanarLayoutError(f"hole is not inside host {host_id}")
        host.holes = host.holes + (hole,)

    def insert_mass(self, host_id: str, outer_footprint: Iterable[tuple[int, int]], *, mass_id: str) -> str:
        self.carve_hole(host_id, outer_footprint)
        return f"mass:{mass_id}"

    def insert_building_shell(
        self,
        host_id: str,
        *,
        mass_id: str,
        outer_footprint: Iterable[tuple[int, int]],
        inner_footprint: Iterable[tuple[int, int]],
        entrances: Sequence[dict[str, Any]],
        **interior: Any,
    ) -> dict[str, Any]:
        outer = _cycle(list(outer_footprint))
        inner = _cycle(list(inner_footprint))
        if area2(outer) < 0:
            raise PlanarLayoutError("building outer footprint must be clockwise")
        if area2(inner) < 0:
            raise PlanarLayoutError("building inner footprint must be clockwise")
        for point in inner:
            state = point_in_loop(point, outer)
            if state == 0:
                raise PlanarLayoutError("inner footprint is not inside the outer shell")
        self.carve_hole(host_id, outer)
        interior_id = f"region:{mass_id}:interior"
        interior_kwargs = {
            "ceiling_z": interior.get("ceiling_z", -24576),
            "floor_z": interior.get("floor_z", 8192),
            "ceiling_picnum": interior.get("ceiling_picnum", 416),
            "floor_picnum": interior.get("floor_picnum", 2448),
            "wall_picnum": interior.get("wall_picnum", 5),
            "ceiling_shade": interior.get("ceiling_shade", 8),
            "floor_shade": interior.get("floor_shade", 16),
            "wall_shade": interior.get("wall_shade", 8),
            "role": "interior",
        }
        self.add_region(interior_id, inner, **interior_kwargs)
        doors = []
        for entrance in entrances:
            door_id = str(entrance.get("region_id") or f"region:{mass_id}:{entrance['id']}:door")
            oa = (int(entrance["outer_a"][0]), int(entrance["outer_a"][1]))
            ob = (int(entrance["outer_b"][0]), int(entrance["outer_b"][1]))
            ia = (int(entrance["inner_a"][0]), int(entrance["inner_a"][1]))
            ib = (int(entrance["inner_b"][0]), int(entrance["inner_b"][1]))
            quad = [oa, ob, ib, ia]
            if area2(quad) <= 0:
                quad = [oa, ia, ib, ob]
            if area2(quad) <= 0:
                raise PlanarLayoutError(f"doorway {entrance.get('id')} has non-positive area")
            door_kwargs = dict(entrance.get("door_kwargs") or {})
            if entrance.get("gated"):
                door_kwargs.setdefault("type", 600)
                door_kwargs.setdefault("ceiling_z", 8192)
                door_kwargs.setdefault("floor_z", 8192)
            self.add_region(door_id, quad, role="doorway", **door_kwargs)
            if entrance.get("sector_behavior"):
                self.regions[door_id].sector_behavior = dict(entrance["sector_behavior"])
            width = int(hypot(ob[0] - oa[0], ob[1] - oa[1]))
            self.add_connection(
                f"connection:{entrance['id']}:host",
                host_id, door_id, role="doorway", a1=oa, a2=ob,
                gated=bool(entrance.get("gated")),
                min_width=max(512, width),
            )
            inner_width = int(hypot(ib[0] - ia[0], ib[1] - ia[1]))
            self.add_connection(
                f"connection:{entrance['id']}:inner",
                door_id, interior_id, role="doorway", a1=ia, a2=ib,
                gated=bool(entrance.get("gated")),
                min_width=max(512, inner_width),
            )
            doors.append(door_id)
        return {"interior": interior_id, "doors": doors, "mass": f"mass:{mass_id}"}

    def add_connection(
        self,
        connection_id: str,
        region_a: str,
        region_b: str,
        *,
        role: str = "portal",
        a1: Point | None = None,
        a2: Point | None = None,
        **kwargs: Any,
    ) -> str:
        if connection_id in self.connections:
            raise PlanarLayoutError(f"duplicate connection id {connection_id!r}")
        if role not in PORTAL_ROLES:
            raise PlanarLayoutError(f"unknown connection role {role!r}")
        self.connections[connection_id] = ConnectionSpec(
            connection_id=connection_id, region_a=region_a, region_b=region_b,
            role=role, a1=a1, a2=a2, **kwargs,
        )
        return connection_id

    def add_partition(
        self,
        partition_id: str,
        region_a: str,
        region_b: str | None = None,
        *,
        role: str = "thin_partition",
        a1: Point | None = None,
        a2: Point | None = None,
        **kwargs: Any,
    ) -> str:
        if role not in PARTITION_ROLES:
            raise PlanarLayoutError(f"unknown partition role {role!r}")
        self.partitions[partition_id] = PartitionSpec(
            partition_id=partition_id, region_a=region_a, region_b=region_b,
            role=role, a1=a1, a2=a2, **kwargs,
        )
        return partition_id

    def add_sprite(self, placement_id: str, region_id: str, *, x: int, y: int, z: int, **kwargs: Any) -> str:
        self.placements.append(PlacementSpec(
            placement_id=placement_id, region_id=region_id, x=int(x), y=int(y), z=int(z), **kwargs,
        ))
        return placement_id

    def place_on_wall(
        self,
        placement_id: str,
        region_id: str,
        *,
        a1: tuple[int, int],
        a2: tuple[int, int],
        t: float = 0.5,
        height_player_heights: float = 0.65,
        offset_player_widths: float = 0.08,
        facing: str = "into_region",
        **kwargs: Any,
    ) -> str:
        self.placements.append(PlacementSpec(
            placement_id=placement_id, region_id=region_id, x=0, y=0, z=0,
            anchor={
                "kind": "wall", "a1": [int(a1[0]), int(a1[1])], "a2": [int(a2[0]), int(a2[1])],
                "t": float(t), "height_player_heights": float(height_player_heights),
                "offset_player_widths": float(offset_player_widths), "facing": facing,
            },
            **kwargs,
        ))
        return placement_id

    def place_on_floor(
        self,
        placement_id: str,
        region_id: str,
        *,
        local: tuple[float, float] = (0.5, 0.5),
        height_player_heights: float = 0.0,
        **kwargs: Any,
    ) -> str:
        self.placements.append(PlacementSpec(
            placement_id=placement_id, region_id=region_id, x=0, y=0, z=0,
            anchor={
                "kind": "floor", "local": [float(local[0]), float(local[1])],
                "height_player_heights": float(height_player_heights),
            },
            **kwargs,
        ))
        return placement_id

    def place_on_ceiling(
        self,
        placement_id: str,
        region_id: str,
        *,
        local: tuple[float, float] = (0.5, 0.5),
        height_player_heights: float = 0.15,
        **kwargs: Any,
    ) -> str:
        self.placements.append(PlacementSpec(
            placement_id=placement_id, region_id=region_id, x=0, y=0, z=0,
            anchor={
                "kind": "ceiling", "local": [float(local[0]), float(local[1])],
                "height_player_heights": float(height_player_heights),
            },
            **kwargs,
        ))
        return placement_id

    def set_player_start(self, region_id: str, *, x: int, y: int, z: int, angle: int = 0) -> None:
        self.player_start = PlayerStartSpec(region_id=region_id, x=int(x), y=int(y), z=int(z), angle=int(angle))

    def declare_special(self, region_a: str, region_b: str, kind: str) -> None:
        self.special_pairs.append((region_a, region_b, kind))
        if region_a in self.regions:
            self.regions[region_a].stack_pair = region_b
            self.regions[region_a].special = kind
        if region_b in self.regions:
            self.regions[region_b].stack_pair = region_a
            self.regions[region_b].special = kind

    def _region(self, region_id: str) -> RegionSpec:
        try:
            return self.regions[region_id]
        except KeyError as exc:
            raise PlanarLayoutError(f"unknown region {region_id!r}") from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            "$schema": SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "name": self.name,
            "visibility": self.visibility,
            "regions": [
                {
                    "region_id": region.region_id,
                    "outer": [list(point) for point in region.outer],
                    "holes": [[list(point) for point in hole] for hole in region.holes],
                    "ceiling_z": region.ceiling_z,
                    "floor_z": region.floor_z,
                    "ceiling_picnum": region.ceiling_picnum,
                    "floor_picnum": region.floor_picnum,
                    "wall_picnum": region.wall_picnum,
                    "layer": region.layer,
                    "special": region.special,
                    "parallax_ceiling": region.parallax_ceiling,
                    "type": region.type,
                    "role": region.role,
                    "intent": dict(region.intent),
                }
                for region in self.regions.values()
            ],
            "connections": [
                {
                    "connection_id": item.connection_id,
                    "region_a": item.region_a,
                    "region_b": item.region_b,
                    "role": item.role,
                    "interval": None if item.a1 is None else [list(item.a1), list(item.a2 or item.a1)],
                    "gated": item.gated,
                    "face_picnum": item.face_picnum,
                }
                for item in self.connections.values()
            ],
            "partitions": [
                {
                    "partition_id": item.partition_id,
                    "region_a": item.region_a,
                    "region_b": item.region_b,
                    "role": item.role,
                }
                for item in self.partitions.values()
            ],
            "placements": [
                {
                    "placement_id": item.placement_id,
                    "region_id": item.region_id,
                    "x": item.x, "y": item.y, "z": item.z,
                    "type": item.type, "picnum": item.picnum,
                }
                for item in self.placements
            ],
            "player_start": None if self.player_start is None else {
                "region_id": self.player_start.region_id,
                "x": self.player_start.x, "y": self.player_start.y,
                "z": self.player_start.z, "angle": self.player_start.angle,
            },
            "special_pairs": [
                {"region_a": a, "region_b": b, "kind": kind} for a, b, kind in self.special_pairs
            ],
        }

    def compile(self) -> CompiledLayout:
        if self.player_start is None:
            raise PlanarLayoutError("player start has not been assigned")
        self._validate_regions()
        source_edges = self._source_edges()
        split_points = self._collect_split_points(source_edges)
        atomics = self._split_edges(source_edges, split_points)
        conservation = self._conservation(source_edges, atomics)
        if not conservation.conserved:
            raise PlanarLayoutError(
                "geometry conservation failed "
                f"dropped={conservation.dropped_source_edges} duplicated={conservation.duplicated_source_edges}"
            )
        pairs, connection_report, leftover = self._pair_portals(atomics)
        if leftover:
            conservation.unpaired_portal_candidates = leftover
            raise PlanarLayoutError(
                "unexplained unpaired portal candidates: " + ", ".join(leftover[:12])
            )
        level, allocations, wall_from_atomic = self._emit(atomics, pairs)
        builder = LevelBuilder(level)
        for region in self.regions.values():
            sector_id = allocations[region.region_id].sector_id
            if region.sector_behavior:
                builder.set_behavior("sector", sector_id, **region.sector_behavior)
        for connection in self.connections.values():
            if not connection.wall_behavior:
                continue
            realized = [
                item for item in connection_report
                if item["connection_id"] == connection.connection_id and item["status"] == "realized"
            ]
            atomic_ids = [aid for item in realized for aid in item.get("atomic_ids", [])]
            if len(realized) != 1 and connection.attach_policy != "all_atomic":
                raise PlanarLayoutError(
                    f"connection {connection.connection_id} split into {len(realized)} atomic portals; "
                    "refusing to duplicate XWALL (set attach_policy='all_atomic' or tighten the interval)"
                )
            for atomic_id in atomic_ids:
                wall_id = wall_from_atomic[atomic_id]
                builder.set_behavior("wall", wall_id, **connection.wall_behavior)
        for connection in self.connections.values():
            if not _connection_has_face(connection):
                continue
            realized = [
                item for item in connection_report
                if item["connection_id"] == connection.connection_id and item["status"] == "realized"
            ]
            painted: set[int] = set()
            for item in realized:
                for atomic_id in item.get("atomic_ids", []):
                    wall_id = wall_from_atomic[atomic_id]
                    painted.add(wall_id)
                    nxt = int(builder.level.walls[wall_id]["fields"].get("next_wall") or -1)
                    if nxt >= 0:
                        painted.add(nxt)
            for wall_id in painted:
                fields = builder.level.walls[wall_id]["fields"]
                if connection.face_picnum is not None:
                    fields["picnum"] = int(connection.face_picnum)
                if connection.face_over_picnum is not None:
                    fields["over_picnum"] = int(connection.face_over_picnum)
                if connection.face_shade is not None:
                    fields["shade"] = int(connection.face_shade)
                if connection.face_cstat is not None:
                    fields["cstat"] = int(connection.face_cstat)
                if connection.face_x_repeat is not None:
                    fields["x_repeat"] = int(connection.face_x_repeat)
                if connection.face_y_repeat is not None:
                    fields["y_repeat"] = int(connection.face_y_repeat)
        for placement in self.placements:
            region = self.regions[placement.region_id]
            sector_id = allocations[placement.region_id].sector_id
            if placement.anchor:
                from .placement import resolve_anchor
                resolved = resolve_anchor(
                    kind=str(placement.anchor["kind"]),
                    a1=tuple(placement.anchor.get("a1") or (0, 0)),
                    a2=tuple(placement.anchor.get("a2") or (0, 0)),
                    floor_z=region.floor_z,
                    ceiling_z=region.ceiling_z,
                    t=float(placement.anchor.get("t") or 0.5),
                    height_player_heights=float(placement.anchor.get("height_player_heights") or 0.0),
                    offset_player_widths=float(placement.anchor.get("offset_player_widths") or 0.08),
                    facing=str(placement.anchor.get("facing") or "into_region"),
                    local=tuple(placement.anchor["local"]) if placement.anchor.get("local") else None,
                    outer=list(region.outer),
                )
                placement.x, placement.y, placement.z = resolved["x"], resolved["y"], resolved["z"]
                if placement.anchor.get("kind") == "wall":
                    placement.angle = resolved["angle"]
            try:
                sprite_id = builder.add_sprite(
                    sector=sector_id, x=placement.x, y=placement.y, z=placement.z,
                    type=placement.type, picnum=placement.picnum, status=placement.status,
                    angle=placement.angle, cstat=placement.cstat, x_repeat=placement.x_repeat,
                    y_repeat=placement.y_repeat, shade=placement.shade, pal=placement.pal,
                )
            except ConstructionError as exc:
                raise PlanarLayoutError(
                    f"placement {placement.placement_id} in {placement.region_id} "
                    f"at {(placement.x, placement.y, placement.z)}: {exc}"
                ) from exc
            if placement.behavior:
                builder.set_behavior("sprite", sprite_id, **placement.behavior)
        start = self.player_start
        builder.set_player_start(
            sector=allocations[start.region_id].sector_id,
            x=start.x, y=start.y, z=start.z, angle=start.angle,
        )
        native_errors = [item for item in validate_map(builder.level.to_disk_map()) if item.severity == "error"]
        if native_errors:
            first = native_errors[0]
            raise PlanarLayoutError(f"native structure: {first.code} at {first.location}: {first.message}")
        specials = []
        for a, b, kind in self.special_pairs:
            specials.append((allocations[a].sector_id, allocations[b].sector_id, kind))
        for partition in self.partitions.values():
            if partition.region_b and partition.region_a in allocations and partition.region_b in allocations:
                specials.append((
                    allocations[partition.region_a].sector_id,
                    allocations[partition.region_b].sector_id,
                    partition.role,
                ))
        gated_sectors = {
            allocations[region.region_id].sector_id
            for region in self.regions.values()
            if region.type in {600, 602} or region.role in {"doorway", "gated_pocket"}
        }
        zero_exit = {
            allocations[region.region_id].sector_id
            for region in self.regions.values()
            if region.declared_zero_exit or region.special in {"water", "stack", "helper"}
        }
        intended = [(item.region_a, item.region_b) for item in self.connections.values()]
        diagnostics = validate_authored_level(
            builder.level,
            intended_adjacency=intended,
            gated_sectors=gated_sectors,
            declared_zero_exit=zero_exit,
            declared_specials=specials,
            allocations={key: value.sector_id for key, value in allocations.items()},
            connection_report=connection_report,
        )
        try:
            construction_preflight(diagnostics)
        except AuthoredGeometryError as exc:
            raise PlanarLayoutError(str(exc)) from exc
        owners = [-1] * len(builder.level.walls)
        for sector_id, sector in enumerate(builder.level.sectors):
            first = int(sector["fields"]["wall_ptr"])
            count = int(sector["fields"]["wall_count"])
            for wall_id in range(first, first + count):
                if owners[wall_id] != -1:
                    conservation.walls_owned_once = False
                owners[wall_id] = sector_id
        conservation.walls_owned_once = all(owner >= 0 for owner in owners) and -1 not in owners
        conservation.emitted_directed_edges = len(builder.level.walls)
        if not conservation.conserved:
            raise PlanarLayoutError("emitted walls were not owned exactly once")
        # Refresh connection report with native wall ids.
        atomic_to_wall = wall_from_atomic
        for item in connection_report:
            item["walls"] = [atomic_to_wall[aid] for aid in item.get("atomic_ids", []) if aid in atomic_to_wall]
            item["sectors"] = [
                allocations[item["region_a"]].sector_id,
                allocations[item["region_b"]].sector_id,
            ]
        return CompiledLayout(
            level=builder.level,
            allocations=allocations,
            wall_from_atomic=wall_from_atomic,
            conservation=conservation,
            connection_report=connection_report,
            declared_specials=specials,
            layout=self,
        )

    def _validate_regions(self) -> None:
        for region in self.regions.values():
            errors = validate_loop(region.outer, role="outer")
            if errors:
                raise PlanarLayoutError(f"{region.region_id} outer: {errors[0]}")
            if int(region.ceiling_z) > int(region.floor_z):
                raise PlanarLayoutError(f"{region.region_id} ceiling is below its floor")
            for hole in region.holes:
                errors = validate_loop(hole, role="hole")
                if errors:
                    raise PlanarLayoutError(f"{region.region_id} hole: {errors[0]}")
        declared = {frozenset((left, right)) for left, right, _kind in self.special_pairs}
        members = list(self.regions.values())
        for index, left in enumerate(members):
            for right in members[index + 1:]:
                if frozenset((left.region_id, right.region_id)) in declared:
                    continue
                if left.stack_pair == right.region_id or right.stack_pair == left.region_id:
                    continue
                if any(loops_equivalent(left.outer, hole) for hole in right.holes) or any(
                    loops_equivalent(right.outer, hole) for hole in left.holes
                ):
                    continue
                loops_l = [left.outer, *left.holes]
                loops_r = [right.outer, *right.holes]
                if loops_equivalent(left.outer, right.outer):
                    raise PlanarLayoutError(
                        f"independent regions {left.region_id} and {right.region_id} "
                        "have identical XY footprints without a declared stack/water relationship"
                    )
                relation = polygon_relation(loops_l, loops_r)
                kind = str(relation["kind"])
                if kind in {"partial_area_overlap", "full_containment_a_in_b", "full_containment_b_in_a"}:
                    raise PlanarLayoutError(
                        f"independent regions {left.region_id} and {right.region_id} "
                        f"have XY {kind} without a declared special relationship"
                    )
                for a1, a2 in _edges_of(left):
                    for b1, b2 in _edges_of(right):
                        classified = classify_segment_pair(a1, a2, b1, b2)
                        if classified and classified["kind"] == "proper_crossing":
                            crossing = integer_intersection(a1, a2, b1, b2)
                            if crossing is None:
                                raise PlanarLayoutError(
                                    f"proper crossing between {left.region_id} and {right.region_id} "
                                    "does not land on integer Build coordinates"
                                )
                            raise PlanarLayoutError(
                                f"proper crossing between {left.region_id} and {right.region_id} "
                                f"at {crossing}; refuse automatic junction"
                            )

    def _source_edges(self) -> list[SourceEdge]:
        edges: list[SourceEdge] = []
        for region in self.regions.values():
            for index, start in enumerate(region.outer):
                end = region.outer[(index + 1) % len(region.outer)]
                edges.append(SourceEdge(
                    edge_id=f"{region.region_id}:outer:{index}",
                    region_id=region.region_id, a=start, b=end,
                ))
            for hole_index, hole in enumerate(region.holes):
                for index, start in enumerate(hole):
                    end = hole[(index + 1) % len(hole)]
                    edges.append(SourceEdge(
                        edge_id=f"{region.region_id}:hole:{hole_index}:{index}",
                        region_id=region.region_id, a=start, b=end,
                    ))
        return edges

    def _collect_split_points(self, edges: list[SourceEdge]) -> dict[str, set[Point]]:
        points: dict[str, set[Point]] = {edge.edge_id: {edge.a, edge.b} for edge in edges}
        for left in edges:
            for right in edges:
                if left.edge_id >= right.edge_id:
                    continue
                classified = classify_segment_pair(left.a, left.b, right.a, right.b)
                if classified is None:
                    continue
                kind = classified["kind"]
                if kind == "proper_crossing":
                    if left.region_id == right.region_id:
                        continue
                    crossing = integer_intersection(left.a, left.b, right.a, right.b)
                    raise PlanarLayoutError(
                        f"proper crossing {left.edge_id} x {right.edge_id}"
                        + ("" if crossing is None else f" at {crossing}")
                        + ("" if crossing is not None else "; intersection is not an integer lattice point")
                    )
                if kind == "t_junction":
                    point = classified["point"]
                    if on_segment_strict(left.a, left.b, point):
                        points[left.edge_id].add(point)
                    if on_segment_strict(right.a, right.b, point):
                        points[right.edge_id].add(point)
                elif kind in {
                    "partial_collinear_overlap",
                    "exact_reversed_coincident",
                    "exact_same_direction_coincident",
                }:
                    overlap = classified.get("overlap")
                    extra = [left.a, left.b, right.a, right.b]
                    if overlap:
                        extra.extend(overlap)
                    for edge in (left, right):
                        for point in extra:
                            if on_segment_inclusive(edge.a, edge.b, point):
                                points[edge.edge_id].add(point)
        for connection in self.connections.values():
            if connection.a1 is None or connection.a2 is None:
                continue
            for edge in edges:
                if edge.region_id not in {connection.region_a, connection.region_b}:
                    continue
                for point in (connection.a1, connection.a2):
                    if on_segment_strict(edge.a, edge.b, point) or point in {edge.a, edge.b}:
                        if on_segment_inclusive(edge.a, edge.b, point):
                            points[edge.edge_id].add(point)
        for partition in self.partitions.values():
            if partition.a1 is None or partition.a2 is None:
                continue
            for edge in edges:
                if edge.region_id not in {partition.region_a, partition.region_b}:
                    continue
                for point in (partition.a1, partition.a2):
                    if on_segment_inclusive(edge.a, edge.b, point):
                        points[edge.edge_id].add(point)
        return points

    def _split_edges(
        self, edges: list[SourceEdge], split_points: dict[str, set[Point]],
    ) -> list[AtomicEdge]:
        atomics: list[AtomicEdge] = []
        for edge in edges:
            pieces = atomic_subsegments(edge.a, edge.b, split_points[edge.edge_id])
            if not pieces:
                raise PlanarLayoutError(f"source edge {edge.edge_id} produced no atomic segments")
            reconstructed: list[Point] = [pieces[0][0], *(item[1] for item in pieces)]
            if reconstructed[0] != edge.a or reconstructed[-1] != edge.b:
                raise PlanarLayoutError(f"split of {edge.edge_id} does not reconstruct the source edge")
            for index, (start, end) in enumerate(pieces):
                atomics.append(AtomicEdge(
                    atomic_id=f"{edge.edge_id}:{index}",
                    source_id=edge.edge_id,
                    region_id=edge.region_id,
                    a=start, b=end,
                ))
        return atomics

    def _conservation(self, source: list[SourceEdge], atomics: list[AtomicEdge]) -> ConservationReport:
        by_source: dict[str, list[AtomicEdge]] = defaultdict(list)
        for edge in atomics:
            by_source[edge.source_id].append(edge)
        dropped = []
        duplicated = []
        for edge in source:
            pieces = by_source.get(edge.edge_id, [])
            if not pieces:
                dropped.append(edge.edge_id)
                continue
            cursor = edge.a
            for piece in pieces:
                if piece.a != cursor:
                    dropped.append(edge.edge_id)
                    break
                cursor = piece.b
            else:
                if cursor != edge.b:
                    dropped.append(edge.edge_id)
        seen = [edge.atomic_id for edge in atomics]
        if len(seen) != len(set(seen)):
            duplicated = [item for item in seen if seen.count(item) > 1]
        split_count = sum(max(0, len(items) - 1) for items in by_source.values())
        return ConservationReport(
            source_directed_edges=len(source),
            emitted_directed_edges=len(atomics),
            dropped_source_edges=dropped,
            duplicated_source_edges=duplicated,
            unpaired_portal_candidates=[],
            split_count=split_count,
            atomic_segments=len(atomics),
            walls_owned_once=True,
        )

    def _pair_portals(
        self, atomics: list[AtomicEdge],
    ) -> tuple[list[tuple[AtomicEdge, AtomicEdge]], list[dict[str, Any]], list[str]]:
        by_undirected: dict[tuple[Point, Point], list[AtomicEdge]] = defaultdict(list)
        for edge in atomics:
            by_undirected[undirected_key(edge.a, edge.b)].append(edge)
        reverse_index: dict[tuple[str, tuple[Point, Point]], AtomicEdge] = {}
        for edge in atomics:
            reverse_index[(edge.region_id, (edge.b, edge.a))] = edge

        used: set[str] = set()
        pairs: list[tuple[AtomicEdge, AtomicEdge]] = []
        report: list[dict[str, Any]] = []

        def interval_contains(connection: ConnectionSpec, edge: AtomicEdge) -> bool:
            if connection.a1 is None or connection.a2 is None:
                return True
            overlap = collinear_overlap_interval(connection.a1, connection.a2, edge.a, edge.b)
            if overlap is None:
                return False
            return undirected_key(*overlap) == undirected_key(edge.a, edge.b)

        for connection in self.connections.values():
            candidates = []
            for edge in atomics:
                if edge.region_id != connection.region_a:
                    continue
                other = reverse_index.get((connection.region_b, (edge.a, edge.b)))
                if other is None:
                    continue
                if not interval_contains(connection, edge):
                    continue
                candidates.append((edge, other))
            if not candidates:
                report.append({
                    "connection_id": connection.connection_id,
                    "region_a": connection.region_a,
                    "region_b": connection.region_b,
                    "status": "missing",
                    "why": "no reversed coincident atomic segment exists for this intended connection",
                    "atomic_ids": [],
                })
                continue
            for edge, other in candidates:
                if edge.atomic_id in used or other.atomic_id in used:
                    continue
                if not exact_reversed(edge.a, edge.b, other.a, other.b):
                    continue
                used.add(edge.atomic_id)
                used.add(other.atomic_id)
                pairs.append((edge, other))
                width = hypot(edge.b[0] - edge.a[0], edge.b[1] - edge.a[1])
                report.append({
                    "connection_id": connection.connection_id,
                    "region_a": connection.region_a,
                    "region_b": connection.region_b,
                    "role": connection.role,
                    "status": "realized",
                    "atomic_ids": [edge.atomic_id, other.atomic_id],
                    "width": round(width),
                    "wide_enough": width >= connection.min_width,
                })

        allowed_unpaired = set()
        for partition in self.partitions.values():
            owners = {partition.region_a, partition.region_b}
            for edge in atomics:
                if edge.region_id not in owners:
                    continue
                if partition.a1 and partition.a2:
                    overlap = collinear_overlap_interval(partition.a1, partition.a2, edge.a, edge.b)
                    if overlap is None:
                        continue
                allowed_unpaired.add(edge.atomic_id)

        special_regions = set()
        for left_id, right_id, _kind in self.special_pairs:
            special_regions.add(left_id)
            special_regions.add(right_id)
        leftover = []
        for _key, group in by_undirected.items():
            if len(group) < 2:
                continue
            for left in group:
                for right in group:
                    if left.atomic_id >= right.atomic_id:
                        continue
                    if left.region_id in special_regions or right.region_id in special_regions:
                        continue
                    if not exact_reversed(left.a, left.b, right.a, right.b):
                        if left.a == right.a and left.b == right.b:
                            if left.region_id in special_regions or right.region_id in special_regions:
                                continue
                            raise PlanarLayoutError(
                                f"same-direction coincident atomic segments {left.atomic_id} and {right.atomic_id}"
                            )
                        continue
                    if left.atomic_id in used and right.atomic_id in used:
                        continue
                    if left.atomic_id in allowed_unpaired or right.atomic_id in allowed_unpaired:
                        continue
                    leftover.append(f"{left.atomic_id}↔{right.atomic_id}")
        missing = [item for item in report if item["status"] == "missing"]
        if missing:
            leftover.extend(item["connection_id"] for item in missing)
        return pairs, report, leftover

    def _emit(
        self, atomics: list[AtomicEdge], pairs: list[tuple[AtomicEdge, AtomicEdge]],
    ) -> tuple[LevelIR, dict[str, SectorAllocation], dict[str, int]]:
        ir = new_level(visibility=self.visibility)
        by_region: dict[str, list[AtomicEdge]] = defaultdict(list)
        for edge in atomics:
            by_region[edge.region_id].append(edge)
        allocations: dict[str, SectorAllocation] = {}
        wall_from_atomic: dict[str, int] = {}
        for region in self.regions.values():
            loops = [region.outer, *region.holes]
            region_atomics = by_region[region.region_id]
            by_source: dict[str, list[AtomicEdge]] = defaultdict(list)
            for edge in region_atomics:
                by_source[edge.source_id].append(edge)
            build_loops: list[list[AtomicEdge]] = []
            source_ids: list[str] = []
            for index in range(len(region.outer)):
                source_ids.append(f"{region.region_id}:outer:{index}")
            hole_source_groups: list[list[str]] = []
            for hole_index, hole in enumerate(region.holes):
                group = [f"{region.region_id}:hole:{hole_index}:{index}" for index in range(len(hole))]
                hole_source_groups.append(group)

            def _ordered_loop(source_ids_for_loop: list[str]) -> list[AtomicEdge]:
                ordered: list[AtomicEdge] = []
                for source_id in source_ids_for_loop:
                    pieces = by_source.get(source_id, [])
                    if not pieces:
                        raise PlanarLayoutError(f"missing atomics for {source_id}")
                    pieces.sort(key=lambda edge: int(edge.atomic_id.rsplit(":", 1)[1]))
                    ordered.extend(pieces)
                if not ordered:
                    raise PlanarLayoutError(f"failed to reconstruct loop for {region.region_id}")
                return ordered

            build_loops.append(_ordered_loop(source_ids))
            for group in hole_source_groups:
                build_loops.append(_ordered_loop(group))
            wall_base = len(ir.walls)
            wall_ids: list[int] = []
            wall_count = sum(len(loop) for loop in build_loops)
            fields = _empty(SECTOR_FIELDS)
            fields.update(
                wall_ptr=wall_base,
                wall_count=wall_count,
                ceiling_z=int(region.ceiling_z),
                floor_z=int(region.floor_z),
                ceiling_picnum=int(region.ceiling_picnum),
                floor_picnum=int(region.floor_picnum),
                ceiling_shade=int(region.ceiling_shade),
                floor_shade=int(region.floor_shade),
                type=int(region.type),
                extra=-1,
                ceiling_stat=1 if region.parallax_ceiling else 0,
            )
            sector_id = len(ir.sectors)
            ir.sectors.append({"id": sector_id, "fields": fields, "blood": None})
            wall_id = wall_base
            for loop in build_loops:
                loop_start = wall_id
                for index, edge in enumerate(loop):
                    next_id = loop_start if index == len(loop) - 1 else wall_id + 1
                    wall = _empty(WALL_FIELDS)
                    nx, ny = edge.b
                    wall.update(
                        x=edge.a[0], y=edge.a[1], point2=next_id,
                        next_wall=-1, next_sector=-1, extra=-1,
                        picnum=int(region.wall_picnum), shade=int(region.wall_shade),
                        x_repeat=max(1, min(255, round(hypot(nx - edge.a[0], ny - edge.a[1]) / 128))),
                        y_repeat=8,
                    )
                    ir.walls.append({"id": wall_id, "fields": wall, "blood": None})
                    wall_from_atomic[edge.atomic_id] = wall_id
                    wall_ids.append(wall_id)
                    wall_id += 1
            allocations[region.region_id] = SectorAllocation(sector_id, tuple(wall_ids))

        owners = {}
        for region_id, alloc in allocations.items():
            for wall_id in alloc.wall_ids:
                owners[wall_id] = alloc.sector_id
        for left, right in pairs:
            wa, wb = wall_from_atomic[left.atomic_id], wall_from_atomic[right.atomic_id]
            a, b = ir.walls[wa]["fields"], ir.walls[wb]["fields"]
            a_end, b_end = ir.walls[int(a["point2"])]["fields"], ir.walls[int(b["point2"])]["fields"]
            if (a["x"], a["y"], a_end["x"], a_end["y"]) != (b_end["x"], b_end["y"], b["x"], b["y"]):
                raise PlanarLayoutError(
                    f"paired atomics {left.atomic_id} and {right.atomic_id} did not emit reversed coincident walls"
                )
            a.update(next_wall=wb, next_sector=owners[wb])
            b.update(next_wall=wa, next_sector=owners[wa])
        return ir, allocations, wall_from_atomic


def _edges_of(region: RegionSpec) -> list[Segment]:
    edges: list[Segment] = []
    for loop in (region.outer, *region.holes):
        for index, start in enumerate(loop):
            edges.append((start, loop[(index + 1) % len(loop)]))
    return edges


def _on_source(edge: AtomicEdge, start: Point, end: Point) -> bool:
    return on_segment_inclusive(start, end, edge.a) and on_segment_inclusive(start, end, edge.b)
