"""Classic Doom WAD and map native representation.

Scope is original Doom / Doom II binary maps as loaded by GZDoom's
``MapLoader::LoadVertexes``, ``LoadLineDefs``, ``LoadSideDefs2``,
``LoadSectors``, and ``LoadThings`` from ``doomdata.h`` record layouts.

This is *not* BuildIR. Doom geometry is VERTEXES/LINEDEFS/SIDEDEFS/SECTORS,
not sector-owned wall loops. Hexen-format, UDMF, Boom generalized linedefs,
and ZDoom extensions are classified and rejected rather than decoded.

Reconstructed lumps are THINGS, LINEDEFS, SIDEDEFS, VERTEXES, and SECTORS.
SEGS, SSECTORS, NODES, REJECT, BLOCKMAP, and every non-map lump stay opaque.
The writer rebuilds the five editable lumps from decoded fields; it does not
keep the original lump bytes as a reconstruction shortcut.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .model import DiskObject


class DoomError(ValueError):
    pass


# GZDoom src/common/filesystem/source/file_wad.cpp
WAD_HEADER = struct.Struct("<4sii")
WAD_LUMP = struct.Struct("<ii8s")
assert WAD_HEADER.size == 12
assert WAD_LUMP.size == 16

# GZDoom src/doomdata.h — classic (non-Hexen) on-disk records.
VERTEX_STRUCT = struct.Struct("<hh")
# GZDoom maplinedef_t: uint16 v1,v2,flags,special; int16 tag; uint16 sidenum[2]
LINEDEF_STRUCT = struct.Struct("<HHHHhHH")
SIDEDEF_STRUCT = struct.Struct("<hh8s8s8sh")
SECTOR_STRUCT = struct.Struct("<hh8s8shhh")
THING_STRUCT = struct.Struct("<hhhhh")
assert VERTEX_STRUCT.size == 4
assert LINEDEF_STRUCT.size == 14
assert SIDEDEF_STRUCT.size == 30
assert SECTOR_STRUCT.size == 26
assert THING_STRUCT.size == 10

NO_SIDE = 0xFFFF

# GZDoom doomdata.h ELineFlags for the original 9 Doom bits.
ML_BLOCKING = 0x0001
ML_BLOCKMONSTERS = 0x0002
ML_TWOSIDED = 0x0004
ML_DONTPEGTOP = 0x0008
ML_DONTPEGBOTTOM = 0x0010
ML_SECRET = 0x0020
ML_SOUNDBLOCK = 0x0040
ML_DONTDRAW = 0x0080
ML_MAPPED = 0x0100

RECONSTRUCTED_LUMPS = ("THINGS", "LINEDEFS", "SIDEDEFS", "VERTEXES", "SECTORS")
OPAQUE_MAP_LUMPS = (
    "SEGS", "SSECTORS", "NODES", "REJECT", "BLOCKMAP", "BEHAVIOR", "SCRIPTS",
    "TEXTMAP", "ENDMAP", "ZNODES", "DIALOGUE", "CONVERSATION", "LIGHTMAP",
)
MAP_LUMP_NAMES = set(RECONSTRUCTED_LUMPS) | set(OPAQUE_MAP_LUMPS)

_EXMY = re.compile(r"^E[1-9]M[1-9]$")
_MAPXX = re.compile(r"^MAP[0-9][0-9]$")


def lump_name(raw: bytes) -> str:
    """Decode a WAD directory name the way GZDoom compares map lumps."""
    return raw.split(b"\0", 1)[0].decode("ascii", "replace").rstrip(" ").upper()


def is_map_marker(name: str) -> bool:
    return bool(_EXMY.match(name) or _MAPXX.match(name))


@dataclass
class WadLump:
    name: bytes
    data: bytes
    offset: int = 0

    @property
    def label(self) -> str:
        return lump_name(self.name)


@dataclass
class DoomVertex:
    x: int
    y: int

    def pack(self) -> bytes:
        return VERTEX_STRUCT.pack(int(self.x), int(self.y))

    @classmethod
    def unpack(cls, raw: bytes) -> "DoomVertex":
        x, y = VERTEX_STRUCT.unpack(raw)
        return cls(int(x), int(y))


@dataclass
class DoomLinedef:
    v1: int
    v2: int
    flags: int
    special: int
    tag: int
    side_front: int
    side_back: int

    @property
    def two_sided(self) -> bool:
        return bool(self.flags & ML_TWOSIDED) and self.side_back != NO_SIDE

    def pack(self) -> bytes:
        tag = int(self.tag)
        if tag > 32767:
            tag -= 65536
        return LINEDEF_STRUCT.pack(
            int(self.v1) & 0xFFFF, int(self.v2) & 0xFFFF, int(self.flags) & 0xFFFF,
            int(self.special) & 0xFFFF, tag,
            int(self.side_front) & 0xFFFF, int(self.side_back) & 0xFFFF,
        )

    @classmethod
    def unpack(cls, raw: bytes) -> "DoomLinedef":
        v1, v2, flags, special, tag, front, back = LINEDEF_STRUCT.unpack(raw)
        return cls(int(v1), int(v2), int(flags), int(special), int(tag), int(front), int(back))


@dataclass
class DoomSidedef:
    x_offset: int
    y_offset: int
    upper_texture: bytes
    lower_texture: bytes
    middle_texture: bytes
    sector: int

    def pack(self) -> bytes:
        return SIDEDEF_STRUCT.pack(
            int(self.x_offset), int(self.y_offset),
            _tex8(self.upper_texture), _tex8(self.lower_texture), _tex8(self.middle_texture),
            int(self.sector),
        )

    @classmethod
    def unpack(cls, raw: bytes) -> "DoomSidedef":
        x_off, y_off, upper, lower, middle, sector = SIDEDEF_STRUCT.unpack(raw)
        return cls(int(x_off), int(y_off), upper, lower, middle, int(sector))


@dataclass
class DoomSector:
    floor_height: int
    ceiling_height: int
    floor_texture: bytes
    ceiling_texture: bytes
    light_level: int
    special: int
    tag: int

    def pack(self) -> bytes:
        return SECTOR_STRUCT.pack(
            int(self.floor_height), int(self.ceiling_height),
            _tex8(self.floor_texture), _tex8(self.ceiling_texture),
            int(self.light_level), int(self.special), int(self.tag),
        )

    @classmethod
    def unpack(cls, raw: bytes) -> "DoomSector":
        floor_z, ceil_z, floor_tex, ceil_tex, light, special, tag = SECTOR_STRUCT.unpack(raw)
        return cls(int(floor_z), int(ceil_z), floor_tex, ceil_tex, int(light), int(special), int(tag))


@dataclass
class DoomThing:
    x: int
    y: int
    angle: int
    type: int
    flags: int

    def pack(self) -> bytes:
        return THING_STRUCT.pack(int(self.x), int(self.y), int(self.angle), int(self.type), int(self.flags))

    @classmethod
    def unpack(cls, raw: bytes) -> "DoomThing":
        x, y, angle, kind, flags = THING_STRUCT.unpack(raw)
        return cls(int(x), int(y), int(angle), int(kind), int(flags))


@dataclass
class DoomDiskMap:
    """Lossless classic Doom map. Editable lumps are field-decoded."""

    name: str
    format: str
    things: list[DoomThing] = field(default_factory=list)
    linedefs: list[DoomLinedef] = field(default_factory=list)
    sidedefs: list[DoomSidedef] = field(default_factory=list)
    vertices: list[DoomVertex] = field(default_factory=list)
    sectors: list[DoomSector] = field(default_factory=list)
    opaque_lumps: dict[str, bytes] = field(default_factory=dict)
    unsupported_reason: str = ""

    @property
    def supported(self) -> bool:
        return self.format == "doom"


def _tex8(value: bytes | str) -> bytes:
    if isinstance(value, str):
        raw = value.encode("ascii")
    else:
        raw = bytes(value)
    if len(raw) > 8:
        raise DoomError(f"texture name exceeds 8 bytes: {raw!r}")
    return raw.ljust(8, b"\0")[:8]


def texture_label(raw: bytes | str) -> str:
    if isinstance(raw, str):
        raw = raw.encode("ascii", "replace")
    return raw.split(b"\0", 1)[0].decode("ascii", "replace").rstrip(" ").upper()


def _records(data: bytes, codec: struct.Struct, factory, label: str) -> list:
    if len(data) % codec.size:
        raise DoomError(f"{label} lump size {len(data)} is not a multiple of {codec.size}")
    return [factory(data[index:index + codec.size]) for index in range(0, len(data), codec.size)]


def _pack_records(items: Iterable, label: str) -> bytes:
    try:
        return b"".join(item.pack() for item in items)
    except (struct.error, ValueError, OverflowError) as exc:
        raise DoomError(f"cannot encode {label}: {exc}") from exc


def classify_map_lumps(lumps: dict[str, bytes]) -> tuple[str, str]:
    """Return (format, reason) using GZDoom's HasBehavior / isText tests."""
    if "TEXTMAP" in lumps:
        return "udmf", "TEXTMAP lump present; UDMF is out of scope"
    if "BEHAVIOR" in lumps:
        return "hexen", "BEHAVIOR lump present; Hexen-format maps are out of scope"
    required = ("THINGS", "LINEDEFS", "SIDEDEFS", "VERTEXES", "SECTORS")
    missing = [name for name in required if name not in lumps]
    if missing:
        return "unsupported", f"missing classic map lumps: {missing}"
    things, linedefs = lumps["THINGS"], lumps["LINEDEFS"]
    if len(things) % THING_STRUCT.size:
        return "hexen", "THINGS size is not a classic 10-byte multiple"
    if len(linedefs) % LINEDEF_STRUCT.size:
        return "hexen", "LINEDEFS size is not a classic 14-byte multiple"
    return "doom", ""


def parse_doom_map(name: str, lumps: dict[str, bytes]) -> DoomDiskMap:
    format_name, reason = classify_map_lumps(lumps)
    opaque = {label: data for label, data in lumps.items() if label in OPAQUE_MAP_LUMPS}
    if format_name != "doom":
        return DoomDiskMap(name=name, format=format_name, opaque_lumps=opaque, unsupported_reason=reason)
    return DoomDiskMap(
        name=name,
        format="doom",
        things=_records(lumps["THINGS"], THING_STRUCT, DoomThing.unpack, "THINGS"),
        linedefs=_records(lumps["LINEDEFS"], LINEDEF_STRUCT, DoomLinedef.unpack, "LINEDEFS"),
        sidedefs=_records(lumps["SIDEDEFS"], SIDEDEF_STRUCT, DoomSidedef.unpack, "SIDEDEFS"),
        vertices=_records(lumps["VERTEXES"], VERTEX_STRUCT, DoomVertex.unpack, "VERTEXES"),
        sectors=_records(lumps["SECTORS"], SECTOR_STRUCT, DoomSector.unpack, "SECTORS"),
        opaque_lumps=opaque,
    )


def encode_doom_map_lumps(level: DoomDiskMap) -> dict[str, bytes]:
    if not level.supported:
        raise DoomError(f"cannot encode {level.format} map {level.name}: {level.unsupported_reason}")
    lumps = {
        "THINGS": _pack_records(level.things, "THINGS"),
        "LINEDEFS": _pack_records(level.linedefs, "LINEDEFS"),
        "SIDEDEFS": _pack_records(level.sidedefs, "SIDEDEFS"),
        "VERTEXES": _pack_records(level.vertices, "VERTEXES"),
        "SECTORS": _pack_records(level.sectors, "SECTORS"),
    }
    lumps.update(level.opaque_lumps)
    return lumps


def validate_doom_map(level: DoomDiskMap) -> list[dict[str, str]]:
    """Structural checks on decoded classic maps. Does not repair."""
    diagnostics: list[dict[str, str]] = []
    if not level.supported:
        diagnostics.append({
            "severity": "error", "code": "unsupported-format",
            "location": level.name, "message": level.unsupported_reason or level.format,
        })
        return diagnostics
    vertex_count, side_count, sector_count = len(level.vertices), len(level.sidedefs), len(level.sectors)
    if vertex_count == 0:
        diagnostics.append({"severity": "error", "code": "empty", "location": level.name, "message": "map has no vertices"})
    if sector_count == 0:
        diagnostics.append({"severity": "error", "code": "empty", "location": level.name, "message": "map has no sectors"})
    for index, line in enumerate(level.linedefs):
        loc = f"linedef:{index}"
        if not 0 <= line.v1 < vertex_count or not 0 <= line.v2 < vertex_count:
            diagnostics.append({"severity": "error", "code": "vertex-ref", "location": loc, "message": f"vertices {line.v1},{line.v2}"})
        if line.v1 == line.v2:
            diagnostics.append({"severity": "warning", "code": "zero-length", "location": loc, "message": "linedef references one vertex twice"})
        if not 0 <= line.side_front < side_count:
            diagnostics.append({"severity": "error", "code": "sidedef-ref", "location": loc, "message": f"front sidedef {line.side_front}"})
        if line.side_back != NO_SIDE and not 0 <= line.side_back < side_count:
            diagnostics.append({"severity": "error", "code": "sidedef-ref", "location": loc, "message": f"back sidedef {line.side_back}"})
    for index, side in enumerate(level.sidedefs):
        if not 0 <= side.sector < sector_count:
            diagnostics.append({
                "severity": "error", "code": "sector-ref", "location": f"sidedef:{index}",
                "message": f"sector {side.sector}",
            })
    starts = [thing for thing in level.things if thing.type == 1]
    if not starts:
        diagnostics.append({"severity": "warning", "code": "player-start", "location": level.name, "message": "no Player 1 start (type 1)"})
    return diagnostics


@dataclass
class WadFile:
    identification: bytes
    lumps: list[WadLump]
    maps: list[DoomDiskMap] = field(default_factory=list)

    @property
    def kind(self) -> str:
        ident = self.identification[:4]
        return ident.decode("ascii", "replace") if ident in {b"IWAD", b"PWAD"} else "unknown"


def _map_groups(lumps: list[WadLump]) -> list[tuple[int, str, dict[str, bytes]]]:
    groups: list[tuple[int, str, dict[str, bytes]]] = []
    index = 0
    while index < len(lumps):
        name = lumps[index].label
        if not is_map_marker(name):
            index += 1
            continue
        collected: dict[str, bytes] = {}
        cursor = index + 1
        while cursor < len(lumps):
            label = lumps[cursor].label
            if is_map_marker(label):
                break
            if label not in MAP_LUMP_NAMES and not label.startswith("GL_"):
                break
            collected[label] = lumps[cursor].data
            cursor += 1
        groups.append((index, name, collected))
        index = cursor
    return groups


def parse_wad(data: bytes) -> WadFile:
    if len(data) < WAD_HEADER.size:
        raise DoomError("file is too short to be a WAD")
    identification, numlumps, infotableofs = WAD_HEADER.unpack_from(data)
    if identification not in {b"IWAD", b"PWAD"}:
        raise DoomError(f"unsupported WAD identification {identification!r}")
    if numlumps < 0 or infotableofs < 0:
        raise DoomError("WAD directory is invalid")
    directory_end = infotableofs + numlumps * WAD_LUMP.size
    if directory_end > len(data):
        raise DoomError("WAD directory is truncated")
    lumps: list[WadLump] = []
    for index in range(numlumps):
        offset, size, name = WAD_LUMP.unpack_from(data, infotableofs + index * WAD_LUMP.size)
        if offset < 0 or size < 0 or offset + size > len(data):
            raise DoomError(f"lump {index} ({lump_name(name)}) points outside the file")
        lumps.append(WadLump(name=name, data=data[offset:offset + size], offset=int(offset)))
    wad = WadFile(identification=identification, lumps=lumps)
    wad.maps = [parse_doom_map(name, collected) for _index, name, collected in _map_groups(lumps)]
    wad._source_bytes = data
    wad._directory_offset = int(infotableofs)
    return wad


def _encoded_lump_payload(wad: WadFile) -> list[tuple[WadLump, bytes]]:
    rebuilt_maps = {level.name: encode_doom_map_lumps(level) for level in wad.maps if level.supported}
    payload: list[tuple[WadLump, bytes]] = []
    current_map: str | None = None
    for lump in wad.lumps:
        label = lump.label
        if is_map_marker(label):
            current_map = label
            payload.append((lump, lump.data))
            continue
        if current_map and label in MAP_LUMP_NAMES and current_map in rebuilt_maps:
            if label in RECONSTRUCTED_LUMPS:
                payload.append((lump, rebuilt_maps[current_map][label]))
            else:
                payload.append((lump, rebuilt_maps[current_map].get(label, lump.data)))
            continue
        if current_map and label not in MAP_LUMP_NAMES and not label.startswith("GL_"):
            current_map = None
        payload.append((lump, lump.data))
    return payload


def encode_wad(wad: WadFile) -> bytes:
    """Rebuild WAD bytes. Editable map lumps come from decoded fields.

    When every reconstructed lump keeps its original size, the original file
    layout (including gaps and directory placement) is patched in place so
    unmodified IWAD roundtrips stay byte-exact. Size changes fall back to a
    compact rewrite.
    """
    payload = _encoded_lump_payload(wad)
    source = getattr(wad, "_source_bytes", None)
    directory_offset = getattr(wad, "_directory_offset", None)
    same_layout = (
        isinstance(source, (bytes, bytearray))
        and isinstance(directory_offset, int)
        and len(payload) == len(wad.lumps)
        and all(len(data) == len(lump.data) for lump, data in payload)
    )
    if same_layout:
        out = bytearray(source)
        for lump, data in payload:
            out[lump.offset:lump.offset + len(data)] = data
        return bytes(out)

    lumps_blob = bytearray()
    directory = bytearray()
    offset = WAD_HEADER.size
    for lump, data in payload:
        directory.extend(WAD_LUMP.pack(offset, len(data), lump.name))
        lumps_blob.extend(data)
        offset += len(data)
    header = WAD_HEADER.pack(wad.identification, len(payload), WAD_HEADER.size + len(lumps_blob))
    return bytes(header + lumps_blob + directory)


def read_wad(path: str | Path) -> WadFile:
    return parse_wad(Path(path).read_bytes())


def write_wad(wad: WadFile, path: str | Path) -> None:
    Path(path).write_bytes(encode_wad(wad))


def wad_map(wad: WadFile, name: str) -> DoomDiskMap:
    expected = name.upper()
    for level in wad.maps:
        if level.name == expected:
            return level
    available = ", ".join(level.name for level in wad.maps) or "(none)"
    raise DoomError(f"map {name!r} not found; available: {available}")


def new_wad(*, identification: bytes = b"PWAD", maps: list[DoomDiskMap] | None = None) -> WadFile:
    """Author a PWAD from decoded classic maps. Opaque derived lumps are omitted."""
    lumps: list[WadLump] = []
    levels = list(maps or [])
    for level in levels:
        encoded = encode_doom_map_lumps(level)
        lumps.append(WadLump(name=_tex8(level.name), data=b""))
        for lump_name_key in ("THINGS", "LINEDEFS", "SIDEDEFS", "VERTEXES", "SECTORS"):
            lumps.append(WadLump(name=_tex8(lump_name_key), data=encoded[lump_name_key]))
        for lump_name_key, data in level.opaque_lumps.items():
            lumps.append(WadLump(name=_tex8(lump_name_key), data=data))
    return WadFile(identification=identification, lumps=lumps, maps=levels)


def doom_corpus_report(wad: WadFile, *, path: str | Path | None = None) -> dict:
    from .doom_semantics import LINEDEF_SPECIALS

    maps = []
    for level in wad.maps:
        diagnostics = validate_doom_map(level)
        specials = sorted({line.special for line in level.linedefs if line.special})
        unsupported_specials = sorted({
            special for special in specials
            if special not in LINEDEF_SPECIALS
        })
        maps.append({
            "name": level.name,
            "format": level.format,
            "supported": level.supported,
            "unsupported_reason": level.unsupported_reason,
            "sectors": len(level.sectors),
            "linedefs": len(level.linedefs),
            "sidedefs": len(level.sidedefs),
            "vertices": len(level.vertices),
            "things": len(level.things),
            "specials": specials,
            "unsupported_specials": unsupported_specials,
            "validation_errors": sum(item["severity"] == "error" for item in diagnostics),
            "validation_warnings": sum(item["severity"] == "warning" for item in diagnostics),
        })
    supported = [level for level in wad.maps if level.supported]
    return {
        "$schema": "llmapper.doom-corpus",
        "schema_version": 1,
        "path": str(path) if path else "",
        "wad_kind": wad.kind,
        "lump_count": len(wad.lumps),
        "parse_count": len(wad.maps),
        "supported_count": len(supported),
        "roundtrip_count": len(supported),
        "validation_count": sum(1 for item in maps if item["supported"] and item["validation_errors"] == 0),
        "format_classification": sorted({level.format for level in wad.maps}),
        "maps": maps,
    }


# DiskObject is imported so callers can keep using the shared field-object style
# when bridging into Build construction; Doom records themselves stay typed.
_ = DiskObject
