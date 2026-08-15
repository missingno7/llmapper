from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from .model import DiskMap, DiskObject, LevelIR


class BuildIRError(ValueError):
    pass


@dataclass(frozen=True)
class BuildDiagnostic:
    severity: str
    code: str
    message: str
    location: str


SECTOR_SHARED_FIELDS = (
    "wall_ptr", "wall_count", "ceiling_z", "floor_z", "ceiling_stat", "floor_stat",
    "ceiling_picnum", "ceiling_heinum", "ceiling_shade", "ceiling_pal",
    "ceiling_x_panning", "ceiling_y_panning", "floor_picnum", "floor_heinum",
    "floor_shade", "floor_pal", "floor_x_panning", "floor_y_panning", "visibility",
    "fog_pal", "lotag", "hitag", "extra",
)
WALL_SHARED_FIELDS = (
    "x", "y", "point2", "next_wall", "next_sector", "cstat", "picnum", "over_picnum",
    "shade", "pal", "x_repeat", "y_repeat", "x_panning", "y_panning", "lotag",
    "hitag", "extra",
)
SPRITE_SHARED_FIELDS = (
    "x", "y", "z", "cstat", "picnum", "shade", "pal", "clipdist", "blend",
    "x_repeat", "y_repeat", "x_offset", "y_offset", "sector", "status", "angle",
    "owner", "x_velocity", "y_velocity", "z_velocity", "lotag", "hitag", "extra",
)


_BLOOD_SECTOR_TO_SHARED = {name: name for name in SECTOR_SHARED_FIELDS}
_BLOOD_SECTOR_TO_SHARED.update(fog_pal="filler", lotag="type")
_BLOOD_WALL_TO_SHARED = {name: name for name in WALL_SHARED_FIELDS}
_BLOOD_WALL_TO_SHARED.update(lotag="type")
_BLOOD_SPRITE_TO_SHARED = {name: name for name in SPRITE_SHARED_FIELDS}
_BLOOD_SPRITE_TO_SHARED.update(
    blend="detail", x_velocity="index", y_velocity="y_velocity",
    z_velocity="initial_type", lotag="type", hitag="flags",
)


def _project(fields: dict[str, int], mapping: dict[str, str]) -> dict[str, int]:
    return {shared: int(fields[native]) for shared, native in mapping.items()}


def _overlay(native: dict[str, int], shared: dict[str, int], mapping: dict[str, str]) -> None:
    for shared_name, native_name in mapping.items():
        native[native_name] = int(shared[shared_name])


def _objects(items: list[DiskObject], mapping: dict[str, str]) -> list[dict[str, Any]]:
    return [{"id": index, "fields": _project(item.fields, mapping)} for index, item in enumerate(items)]


@dataclass
class BuildIR:
    """Game-neutral Build geometry plus an opaque, lossless native extension."""

    source_game: str
    map_version: int
    player_start: dict[str, int]
    sectors: list[dict[str, Any]]
    walls: list[dict[str, Any]]
    sprites: list[dict[str, Any]]
    native: dict[str, Any]
    semantic: dict[str, Any] = field(default_factory=dict)
    schema: str = "llmapper.build-ir"
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "$schema": self.schema,
            "schema_version": self.schema_version,
            "source_game": self.source_game,
            "map_version": self.map_version,
            "player_start": self.player_start,
            "sectors": self.sectors,
            "walls": self.walls,
            "sprites": self.sprites,
            "native": self.native,
            "semantic": self.semantic,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "BuildIR":
        if value.get("$schema") != "llmapper.build-ir" or int(value.get("schema_version", -1)) != 1:
            raise BuildIRError("unsupported BuildIR schema")
        return cls(
            source_game=str(value["source_game"]),
            map_version=int(value["map_version"]),
            player_start={key: int(item) for key, item in value["player_start"].items()},
            sectors=value["sectors"], walls=value["walls"], sprites=value["sprites"],
            native=value["native"], semantic=value.get("semantic", {}),
        )

    def translate(self, dx: int, dy: int, dz: int = 0) -> None:
        dx, dy, dz = int(dx), int(dy), int(dz)
        self.player_start["x"] += dx
        self.player_start["y"] += dy
        self.player_start["z"] += dz
        for wall in self.walls:
            wall["fields"]["x"] += dx
            wall["fields"]["y"] += dy
        for sprite in self.sprites:
            sprite["fields"]["x"] += dx
            sprite["fields"]["y"] += dy
            sprite["fields"]["z"] += dz
        for sector in self.sectors:
            sector["fields"]["ceiling_z"] += dz
            sector["fields"]["floor_z"] += dz

        # Blood extensions contain additional absolute positions and motion Z
        # destinations. Keep those native-only semantics coherent when present.
        if self.source_game == "blood" and self.native.get("adapter") == "blood-level-ir-v1":
            level = LevelIR.from_dict(copy.deepcopy(self.native["document"]))
            level.translate(dx, dy, dz)
            self.native["document"] = level.to_dict()

    def rotate_quarter_turns(self, turns: int, pivot_x: int = 0, pivot_y: int = 0) -> None:
        turns %= 4
        if turns == 0:
            return

        def rotate(x: int, y: int) -> tuple[int, int]:
            x, y = x - pivot_x, y - pivot_y
            for _ in range(turns):
                x, y = -y, x
            return x + pivot_x, y + pivot_y

        self.player_start["x"], self.player_start["y"] = rotate(
            self.player_start["x"], self.player_start["y"]
        )
        self.player_start["angle"] = (self.player_start["angle"] + turns * 512) & 2047
        for wall in self.walls:
            fields = wall["fields"]
            fields["x"], fields["y"] = rotate(fields["x"], fields["y"])
        for sprite in self.sprites:
            fields = sprite["fields"]
            fields["x"], fields["y"] = rotate(fields["x"], fields["y"])
            fields["angle"] = (fields["angle"] + turns * 512) & 2047
        if self.source_game == "blood" and self.native.get("adapter") == "blood-level-ir-v1":
            level = LevelIR.from_dict(copy.deepcopy(self.native["document"]))
            level.rotate_quarter_turns(turns, pivot_x, pivot_y)
            self.native["document"] = level.to_dict()

    def to_native_disk_map(self):
        if self.source_game == "blood":
            return build_ir_to_blood(self)
        if self.source_game == "duke3d":
            return build_ir_to_duke(self)
        raise BuildIRError(f"no native adapter for {self.source_game!r}")

    def validate(self) -> list[BuildDiagnostic]:
        return validate_build_ir(self)


def validate_build_ir(build: BuildIR) -> list[BuildDiagnostic]:
    """Validate the shared Build topology without interpreting game tags."""
    out: list[BuildDiagnostic] = []

    def emit(severity: str, code: str, message: str, location: str) -> None:
        out.append(BuildDiagnostic(severity, code, message, location))

    ns, nw, nsp = len(build.sectors), len(build.walls), len(build.sprites)
    for label, count, maximum in (("sectors", ns, 4096), ("walls", nw, 16384), ("sprites", nsp, 16384)):
        if count > maximum:
            emit("error", "count-limit", f"{count} {label} exceeds the supported Build limit {maximum}", "header")
    start_sector = int(build.player_start["sector"])
    if not 0 <= start_sector < ns:
        emit("error", "start-sector", f"start sector {start_sector} is outside 0..{ns - 1}", "header")
    angle = int(build.player_start["angle"])
    if not 0 <= angle < 2048:
        emit("error", "start-angle", f"start angle {angle} is outside 0..2047", "header")

    owners: list[int | None] = [None] * nw
    for sector_id, sector in enumerate(build.sectors):
        fields = sector["fields"]
        first, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        if first < 0 or count <= 0 or first + count > nw:
            emit("error", "sector-wall-range", f"wall range [{first}, {first + count}) is invalid", f"sector[{sector_id}]")
            continue
        if count < 3:
            emit("warning", "degenerate-sector", f"sector has only {count} walls", f"sector[{sector_id}]")
        for wall_id in range(first, first + count):
            if owners[wall_id] is not None:
                emit("error", "wall-multiple-sectors", f"also owned by sector {owners[wall_id]}", f"wall[{wall_id}]")
            owners[wall_id] = sector_id
            point2 = int(build.walls[wall_id]["fields"]["point2"])
            if not first <= point2 < first + count:
                emit("error", "point2-sector-range", f"point2 {point2} leaves owning sector", f"wall[{wall_id}]")
        unseen = set(range(first, first + count))
        while unseen:
            start = min(unseen)
            current, visited = start, set()
            while current in unseen and current not in visited:
                visited.add(current)
                unseen.remove(current)
                current = int(build.walls[current]["fields"]["point2"])
            if current != start:
                emit("error", "wall-loop-open", f"wall chain from {start} closes at {current}", f"sector[{sector_id}]")

    for wall_id, owner in enumerate(owners):
        if owner is None:
            emit("error", "wall-unowned", "wall is outside every sector range", f"wall[{wall_id}]")
    for wall_id, wall in enumerate(build.walls):
        fields = wall["fields"]
        point2, next_wall, next_sector = (
            int(fields["point2"]), int(fields["next_wall"]), int(fields["next_sector"]),
        )
        if not 0 <= point2 < nw:
            emit("error", "point2", f"point2 {point2} is outside 0..{nw - 1}", f"wall[{wall_id}]")
        if (next_wall == -1) != (next_sector == -1):
            emit("error", "portal-pair", "next_wall and next_sector must both be -1 or valid", f"wall[{wall_id}]")
        if next_wall != -1:
            if not 0 <= next_wall < nw:
                emit("error", "next-wall", f"next wall {next_wall} is out of range", f"wall[{wall_id}]")
            if not 0 <= next_sector < ns:
                emit("error", "next-sector", f"next sector {next_sector} is out of range", f"wall[{wall_id}]")
            if 0 <= next_wall < nw:
                other = build.walls[next_wall]["fields"]
                if int(other["next_wall"]) != wall_id:
                    emit("warning", "portal-nonreciprocal-wall", f"wall {next_wall} points to {other['next_wall']}", f"wall[{wall_id}]")
                if 0 <= next_sector < ns and owners[next_wall] != next_sector:
                    # Classic Build loaders range-check sector wall spans but do
                    # not require portal ownership to be reciprocal. Duke E2L6
                    # contains this accepted original-map construction.
                    emit("warning", "portal-owner", f"next wall {next_wall} is not owned by sector {next_sector}", f"wall[{wall_id}]")
    for sprite_id, sprite in enumerate(build.sprites):
        sector = int(sprite["fields"]["sector"])
        if not 0 <= sector < ns:
            emit("error", "sprite-sector", f"sector {sector} is outside 0..{ns - 1}", f"sprite[{sprite_id}]")
    return out


def build_ir_from_blood(disk: DiskMap) -> BuildIR:
    level = disk.to_level_ir()
    return BuildIR(
        source_game="blood",
        map_version=int(disk.version),
        player_start=dict(level.player_start),
        sectors=_objects(disk.sectors, _BLOOD_SECTOR_TO_SHARED),
        walls=_objects(disk.walls, _BLOOD_WALL_TO_SHARED),
        sprites=_objects(disk.sprites, _BLOOD_SPRITE_TO_SHARED),
        native={"adapter": "blood-level-ir-v1", "document": level.to_dict()},
    )


def build_ir_to_blood(build: BuildIR) -> DiskMap:
    if build.native.get("adapter") != "blood-level-ir-v1":
        raise BuildIRError("BuildIR does not contain a lossless Blood native extension")
    level = LevelIR.from_dict(copy.deepcopy(build.native["document"]))
    if not (len(level.sectors) == len(build.sectors) and len(level.walls) == len(build.walls) and len(level.sprites) == len(build.sprites)):
        raise BuildIRError("shared/native Blood object counts disagree")
    level.player_start = {key: int(value) for key, value in build.player_start.items()}
    for native, shared in zip(level.sectors, build.sectors):
        _overlay(native["fields"], shared["fields"], _BLOOD_SECTOR_TO_SHARED)
    for native, shared in zip(level.walls, build.walls):
        _overlay(native["fields"], shared["fields"], _BLOOD_WALL_TO_SHARED)
    for native, shared in zip(level.sprites, build.sprites):
        _overlay(native["fields"], shared["fields"], _BLOOD_SPRITE_TO_SHARED)
    return level.to_disk_map()


def build_ir_from_duke(disk) -> BuildIR:
    return BuildIR(
        source_game="duke3d",
        map_version=int(disk.version),
        player_start={
            "x": int(disk.header["start_x"]), "y": int(disk.header["start_y"]),
            "z": int(disk.header["start_z"]), "angle": int(disk.header["start_angle"]),
            "sector": int(disk.header["start_sector"]),
        },
        sectors=_objects(disk.sectors, {name: name for name in SECTOR_SHARED_FIELDS}),
        walls=_objects(disk.walls, {name: name for name in WALL_SHARED_FIELDS}),
        sprites=_objects(disk.sprites, {name: name for name in SPRITE_SHARED_FIELDS}),
        native={
            "adapter": "duke-v7",
            "header": dict(disk.header),
            "sectors": [dict(item.fields) for item in disk.sectors],
            "walls": [dict(item.fields) for item in disk.walls],
            "sprites": [dict(item.fields) for item in disk.sprites],
            "trailing_data_hex": disk.trailing_data.hex(),
        },
    )


def build_ir_to_duke(build: BuildIR):
    from .duke import DukeDiskMap

    native = build.native
    if native.get("adapter") != "duke-v7":
        raise BuildIRError("BuildIR does not contain a lossless Duke native extension")
    if not (
        len(native["sectors"]) == len(build.sectors)
        and len(native["walls"]) == len(build.walls)
        and len(native["sprites"]) == len(build.sprites)
    ):
        raise BuildIRError("shared/native Duke object counts disagree")
    header = {key: int(value) for key, value in native["header"].items()}
    header.update(
        start_x=int(build.player_start["x"]), start_y=int(build.player_start["y"]),
        start_z=int(build.player_start["z"]), start_angle=int(build.player_start["angle"]),
        start_sector=int(build.player_start["sector"]), version=7,
    )

    def overlay_items(originals: list[dict[str, int]], shared: list[dict[str, Any]]) -> list[DiskObject]:
        result: list[DiskObject] = []
        for original, item in zip(originals, shared):
            fields = {key: int(value) for key, value in original.items()}
            fields.update({key: int(value) for key, value in item["fields"].items()})
            result.append(DiskObject(fields))
        return result

    return DukeDiskMap(
        version=7,
        header=header,
        sectors=overlay_items(native["sectors"], build.sectors),
        walls=overlay_items(native["walls"], build.walls),
        sprites=overlay_items(native["sprites"], build.sprites),
        trailing_data=bytes.fromhex(native.get("trailing_data_hex", "")),
    )
