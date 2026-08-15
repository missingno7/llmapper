from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .model import DiskObject


class DukeMapError(ValueError):
    pass


HEADER_FIELDS = [
    ("version", "i"), ("start_x", "i"), ("start_y", "i"), ("start_z", "i"),
    ("start_angle", "h"), ("start_sector", "h"),
]
SECTOR_FIELDS = [
    ("wall_ptr", "h"), ("wall_count", "h"), ("ceiling_z", "i"), ("floor_z", "i"),
    ("ceiling_stat", "H"), ("floor_stat", "H"), ("ceiling_picnum", "h"),
    ("ceiling_heinum", "h"), ("ceiling_shade", "b"), ("ceiling_pal", "B"),
    ("ceiling_x_panning", "B"), ("ceiling_y_panning", "B"), ("floor_picnum", "h"),
    ("floor_heinum", "h"), ("floor_shade", "b"), ("floor_pal", "B"),
    ("floor_x_panning", "B"), ("floor_y_panning", "B"), ("visibility", "B"),
    ("fog_pal", "B"), ("lotag", "h"), ("hitag", "h"), ("extra", "h"),
]
WALL_FIELDS = [
    ("x", "i"), ("y", "i"), ("point2", "h"), ("next_wall", "h"),
    ("next_sector", "h"), ("cstat", "H"), ("picnum", "h"), ("over_picnum", "h"),
    ("shade", "b"), ("pal", "B"), ("x_repeat", "B"), ("y_repeat", "B"),
    ("x_panning", "B"), ("y_panning", "B"), ("lotag", "h"), ("hitag", "h"),
    ("extra", "h"),
]
SPRITE_FIELDS = [
    ("x", "i"), ("y", "i"), ("z", "i"), ("cstat", "H"), ("picnum", "h"),
    ("shade", "b"), ("pal", "B"), ("clipdist", "B"), ("blend", "B"),
    ("x_repeat", "B"), ("y_repeat", "B"), ("x_offset", "b"), ("y_offset", "b"),
    ("sector", "h"), ("status", "h"), ("angle", "h"), ("owner", "h"),
    ("x_velocity", "h"), ("y_velocity", "h"), ("z_velocity", "h"),
    ("lotag", "h"), ("hitag", "h"), ("extra", "h"),
]


def _codec(fields: list[tuple[str, str]], size: int) -> struct.Struct:
    codec = struct.Struct("<" + "".join(kind for _name, kind in fields))
    assert codec.size == size, (codec.size, size)
    return codec


HEADER_STRUCT = _codec(HEADER_FIELDS, 20)
SECTOR_STRUCT = _codec(SECTOR_FIELDS, 40)
WALL_STRUCT = _codec(WALL_FIELDS, 32)
SPRITE_STRUCT = _codec(SPRITE_FIELDS, 44)


def _unpack(raw: bytes, fields: list[tuple[str, str]], codec: struct.Struct) -> dict[str, int]:
    return dict(zip((name for name, _kind in fields), codec.unpack(raw)))


def _pack(values: dict[str, int], fields: list[tuple[str, str]], codec: struct.Struct) -> bytes:
    try:
        return codec.pack(*(int(values[name]) for name, _kind in fields))
    except (KeyError, ValueError, struct.error) as exc:
        raise DukeMapError(f"cannot encode Duke record: {exc}") from exc


def _take(data: bytes, offset: int, size: int, label: str) -> tuple[bytes, int]:
    end = offset + size
    if end > len(data):
        raise DukeMapError(f"truncated {label} at 0x{offset:x}: need {size} bytes")
    return data[offset:end], end


@dataclass
class DukeDiskMap:
    version: int
    header: dict[str, int]
    sectors: list[DiskObject]
    walls: list[DiskObject]
    sprites: list[DiskObject]
    trailing_data: bytes = b""
    source_size: int = 0
    format_name: str = "Duke Nukem 3D MAP"

    def to_build_ir(self):
        from .build_ir import build_ir_from_duke

        return build_ir_from_duke(self)


def parse_duke_map(data: bytes) -> DukeDiskMap:
    if len(data) < HEADER_STRUCT.size + 6:
        raise DukeMapError("file is too short to be a Duke3D MAP")
    header = _unpack(data[:HEADER_STRUCT.size], HEADER_FIELDS, HEADER_STRUCT)
    version = header["version"]
    if version != 7:
        raise DukeMapError(f"unsupported Duke3D MAP version {version}; only classic v7 is supported")
    offset = HEADER_STRUCT.size

    def count(label: str) -> int:
        nonlocal offset
        raw, offset = _take(data, offset, 2, label)
        value = struct.unpack("<H", raw)[0]
        return value

    def records(
        amount: int, fields: list[tuple[str, str]], codec: struct.Struct, label: str,
    ) -> list[DiskObject]:
        nonlocal offset
        result: list[DiskObject] = []
        for index in range(amount):
            raw, offset = _take(data, offset, codec.size, f"{label}[{index}]")
            result.append(DiskObject(_unpack(raw, fields, codec)))
        return result

    sectors = records(count("sector count"), SECTOR_FIELDS, SECTOR_STRUCT, "sector")
    walls = records(count("wall count"), WALL_FIELDS, WALL_STRUCT, "wall")
    sprites = records(count("sprite count"), SPRITE_FIELDS, SPRITE_STRUCT, "sprite")
    return DukeDiskMap(
        version=version,
        header=header,
        sectors=sectors,
        walls=walls,
        sprites=sprites,
        trailing_data=data[offset:],
        source_size=len(data),
    )


def read_duke_map(path: str | Path) -> DukeDiskMap:
    return parse_duke_map(Path(path).read_bytes())


def encode_duke_map(disk: DukeDiskMap) -> bytes:
    if int(disk.version) != 7:
        raise DukeMapError(f"unsupported Duke3D MAP version {disk.version}")
    header = dict(disk.header)
    header["version"] = 7
    parts = [_pack(header, HEADER_FIELDS, HEADER_STRUCT)]

    def append(items: Iterable[DiskObject], fields: list[tuple[str, str]], codec: struct.Struct) -> None:
        values = list(items)
        if len(values) > 65535:
            raise DukeMapError("Duke3D object count exceeds the v7 uint16 limit")
        parts.append(struct.pack("<H", len(values)))
        for item in values:
            if item.extra is not None:
                raise DukeMapError("Duke3D v7 records cannot carry Blood packed extras")
            parts.append(_pack(item.fields, fields, codec))

    append(disk.sectors, SECTOR_FIELDS, SECTOR_STRUCT)
    append(disk.walls, WALL_FIELDS, WALL_STRUCT)
    append(disk.sprites, SPRITE_FIELDS, SPRITE_STRUCT)
    parts.append(bytes(disk.trailing_data))
    return b"".join(parts)


def write_duke_map(disk: DukeDiskMap, path: str | Path) -> None:
    Path(path).write_bytes(encode_duke_map(disk))
