from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtraHeader:
    copyright: bytes
    xsprite_size: int
    xwall_size: int
    xsector_size: int
    xmp_signature: bytes
    xmp_header_version: int
    xmp_map_flags: int
    xmp_board_width: int
    xmp_board_height: int
    xmp_palette: int
    xmp_sky_repeat_count: int
    xmp_sky_visibility: int
    reserved: bytes


@dataclass
class PackedExtra:
    kind: str
    fields: dict[str, int]
    opaque_tail: bytes = b""

    def __getattr__(self, name: str) -> int:
        try:
            fields = object.__getattribute__(self, "fields")
            return fields[name]
        except (AttributeError, KeyError) as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        if name in {"kind", "fields", "opaque_tail"} or "fields" not in self.__dict__:
            object.__setattr__(self, name, value)
        elif name in self.fields:
            self.fields[name] = int(value)
        else:
            object.__setattr__(self, name, value)


@dataclass
class DiskObject:
    fields: dict[str, int]
    extra: PackedExtra | None = None

    def __getattr__(self, name: str) -> int:
        try:
            fields = object.__getattribute__(self, "fields")
            return fields[name]
        except (AttributeError, KeyError) as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        if name in {"fields", "extra"} or "fields" not in self.__dict__:
            object.__setattr__(self, name, value)
        elif name in self.fields:
            self.fields[name] = int(value)
        else:
            object.__setattr__(self, name, value)


@dataclass
class DiskMap:
    version: int
    header: dict[str, int]
    extra_header: ExtraHeader | None
    sky_offsets: list[int]
    sectors: list[DiskObject]
    walls: list[DiskObject]
    sprites: list[DiskObject]
    source_crc32: int
    source_size: int
    format_name: str = "Blood MAP"

    def to_level_ir(self) -> "LevelIR":
        return LevelIR.from_disk_map(self)

    def to_build_ir(self):
        """Project Blood disk truth into the shared Build representation."""
        from .build_ir import build_ir_from_blood

        return build_ir_from_blood(self)


@dataclass
class LevelIR:
    """Canonical editable JSON representation, schema version 1."""

    metadata: dict[str, Any]
    player_start: dict[str, int]
    sky: dict[str, Any]
    sectors: list[dict[str, Any]]
    walls: list[dict[str, Any]]
    sprites: list[dict[str, Any]]
    schema: str = "bloodmap.level-ir"
    schema_version: int = 1

    @staticmethod
    def _extra_to_dict(extra: PackedExtra | None) -> dict[str, Any] | None:
        if extra is None:
            return None
        return {
            "kind": extra.kind,
            "fields": dict(extra.fields),
            "opaque_tail_hex": extra.opaque_tail.hex(),
        }

    @classmethod
    def from_disk_map(cls, disk: DiskMap) -> "LevelIR":
        eh = disk.extra_header
        extra_header = None
        if eh is not None:
            extra_header = {
                "copyright_hex": eh.copyright.hex(),
                "xsprite_size": eh.xsprite_size,
                "xwall_size": eh.xwall_size,
                "xsector_size": eh.xsector_size,
                "xmp_signature_hex": eh.xmp_signature.hex(),
                "xmp_header_version": eh.xmp_header_version,
                "xmp_map_flags": eh.xmp_map_flags,
                "xmp_board_width": eh.xmp_board_width,
                "xmp_board_height": eh.xmp_board_height,
                "xmp_palette": eh.xmp_palette,
                "xmp_sky_repeat_count": eh.xmp_sky_repeat_count,
                "xmp_sky_visibility": eh.xmp_sky_visibility,
                "reserved_hex": eh.reserved.hex(),
            }

        def objects(items: list[DiskObject]) -> list[dict[str, Any]]:
            return [
                {"id": i, "fields": dict(obj.fields), "blood": cls._extra_to_dict(obj.extra)}
                for i, obj in enumerate(items)
            ]

        h = disk.header
        return cls(
            metadata={
                "format": disk.format_name,
                "map_version": disk.version,
                "visibility": h["visibility"],
                "matt_id": h["matt_id"],
                "sky_type": h["sky_type"],
                "revision": h["revision"],
                "source_crc32": f"{disk.source_crc32:08x}",
                "extra_header": extra_header,
            },
            player_start={
                "x": h["start_x"], "y": h["start_y"], "z": h["start_z"],
                "angle": h["start_angle"], "sector": h["start_sector"],
            },
            sky={"bits": h["sky_bits"], "offsets": list(disk.sky_offsets)},
            sectors=objects(disk.sectors),
            walls=objects(disk.walls),
            sprites=objects(disk.sprites),
        )

    @staticmethod
    def _dict_to_extra(value: dict[str, Any] | None) -> PackedExtra | None:
        if value is None:
            return None
        return PackedExtra(
            kind=str(value["kind"]),
            fields={k: int(v) for k, v in value["fields"].items()},
            opaque_tail=bytes.fromhex(value.get("opaque_tail_hex", "")),
        )

    def to_disk_map(self) -> DiskMap:
        if self.schema != "bloodmap.level-ir" or self.schema_version != 1:
            raise ValueError(f"unsupported IR schema {self.schema!r} version {self.schema_version}")
        eh_data = self.metadata.get("extra_header")
        eh = None
        if eh_data is not None:
            eh = ExtraHeader(
                copyright=bytes.fromhex(eh_data["copyright_hex"]),
                xsprite_size=int(eh_data["xsprite_size"]),
                xwall_size=int(eh_data["xwall_size"]),
                xsector_size=int(eh_data["xsector_size"]),
                xmp_signature=bytes.fromhex(eh_data["xmp_signature_hex"]),
                xmp_header_version=int(eh_data["xmp_header_version"]),
                xmp_map_flags=int(eh_data["xmp_map_flags"]),
                xmp_board_width=int(eh_data["xmp_board_width"]),
                xmp_board_height=int(eh_data["xmp_board_height"]),
                xmp_palette=int(eh_data["xmp_palette"]),
                xmp_sky_repeat_count=int(eh_data["xmp_sky_repeat_count"]),
                xmp_sky_visibility=int(eh_data["xmp_sky_visibility"]),
                reserved=bytes.fromhex(eh_data["reserved_hex"]),
            )

        def objects(values: list[dict[str, Any]]) -> list[DiskObject]:
            return [
                DiskObject(
                    fields={k: int(v) for k, v in item["fields"].items()},
                    extra=self._dict_to_extra(item.get("blood")),
                )
                for item in values
            ]

        p = self.player_start
        header = {
            "start_x": int(p["x"]), "start_y": int(p["y"]), "start_z": int(p["z"]),
            "start_angle": int(p["angle"]), "start_sector": int(p["sector"]),
            "sky_bits": int(self.sky["bits"]), "visibility": int(self.metadata["visibility"]),
            "matt_id": int(self.metadata["matt_id"]), "sky_type": int(self.metadata["sky_type"]),
            "revision": int(self.metadata["revision"]),
        }
        sectors, walls, sprites = objects(self.sectors), objects(self.walls), objects(self.sprites)
        header.update(num_sectors=len(sectors), num_walls=len(walls), num_sprites=len(sprites))
        crc_text = str(self.metadata.get("source_crc32", "0"))
        return DiskMap(
            version=int(self.metadata["map_version"]), header=header, extra_header=eh,
            sky_offsets=[int(v) for v in self.sky["offsets"]], sectors=sectors, walls=walls,
            sprites=sprites, source_crc32=int(crc_text, 16), source_size=0,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "$schema": self.schema,
            "schema_version": self.schema_version,
            "metadata": self.metadata,
            "player_start": self.player_start,
            "sky": self.sky,
            "sectors": self.sectors,
            "walls": self.walls,
            "sprites": self.sprites,
        }

    def extract(self, sector_ids: Any) -> Any:
        """Extract sectors into a dependency-classified LevelFragment."""
        from .fragment import extract_fragment

        return extract_fragment(self, sector_ids)

    def extract_closed(self, sector_ids: Any, **options: Any) -> Any:
        """Extract a room closed over resolvable Blood gameplay dependencies."""
        from .fragment import extract_behavior_closed_fragment

        return extract_behavior_closed_fragment(self, sector_ids, **options)

    def insert(self, fragment: Any, **options: Any) -> Any:
        """Insert a LevelFragment with deterministic allocation."""
        from .composition import insert_fragment

        return insert_fragment(self, fragment, **options)

    def attach(self, fragment: Any, **options: Any) -> Any:
        """Align, insert, and portal-connect a LevelFragment."""
        from .composition import attach_fragment

        return attach_fragment(self, fragment, **options)

    def connect_portals(self, wall_a: int, wall_b: int) -> "LevelIR":
        """Connect reversed coincident one-sided walls."""
        from .composition import connect_portals

        return connect_portals(self, wall_a, wall_b)

    def connect_pathway(self, wall_a: int, wall_b: int, **options: Any) -> Any:
        """Generate a checked corridor/stair connection between free room walls."""
        from .composition import connect_with_pathway

        return connect_with_pathway(self, wall_a, wall_b, **options)

    def observe(self, sector_ids: Any = None) -> dict[str, Any]:
        """Return an LLM-friendly semantic observation derived directly from this IR."""
        from .semantics import observe_level

        return observe_level(self, sector_ids)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "LevelIR":
        return cls(
            schema=value["$schema"], schema_version=int(value["schema_version"]),
            metadata=value["metadata"], player_start=value["player_start"], sky=value["sky"],
            sectors=value["sectors"], walls=value["walls"], sprites=value["sprites"],
        )

    def translate(self, dx: int, dy: int, dz: int = 0) -> None:
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
            blood = sprite.get("blood")
            if blood is not None:
                fields = blood["fields"]
                fields["target_x"] += dx
                fields["target_y"] += dy
                fields["target_z"] += dz
        for sector in self.sectors:
            blood = sector.get("blood")
            if blood is not None and dz:
                fields = blood["fields"]
                for name in ("off_ceiling_z", "on_ceiling_z", "off_floor_z", "on_floor_z"):
                    fields[name] += dz
            sector["fields"]["ceiling_z"] += dz
            sector["fields"]["floor_z"] += dz

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
        self.player_start["angle"] = (self.player_start["angle"] + 512 * turns) & 2047
        for wall in self.walls:
            f = wall["fields"]
            f["x"], f["y"] = rotate(f["x"], f["y"])
        for sprite in self.sprites:
            f = sprite["fields"]
            f["x"], f["y"] = rotate(f["x"], f["y"])
            f["angle"] = (f["angle"] + 512 * turns) & 2047
            blood = sprite.get("blood")
            if blood is not None:
                xf = blood["fields"]
                xf["target_x"], xf["target_y"] = rotate(xf["target_x"], xf["target_y"])
                xf["goal_angle"] = (xf["goal_angle"] + 512 * turns) & 2047
        for sector in self.sectors:
            blood = sector.get("blood")
            if blood is not None:
                xf = blood["fields"]
                xf["pan_angle"] = (xf["pan_angle"] + 512 * turns) & 2047
                xf["wind_angle"] = (xf["wind_angle"] + 512 * turns) & 2047
