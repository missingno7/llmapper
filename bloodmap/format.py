from __future__ import annotations

import struct
import zlib
from pathlib import Path
from typing import Iterable

from .model import DiskMap, DiskObject, ExtraHeader, PackedExtra


SIGNATURE = b"BLM\x1a"
MATT_ID_NEW = 0x7474614D


class BloodMapError(ValueError):
    pass


MAIN_FIELDS = [
    ("start_x", "i"), ("start_y", "i"), ("start_z", "i"),
    ("start_angle", "h"), ("start_sector", "h"), ("sky_bits", "h"),
    ("visibility", "i"), ("matt_id", "i"), ("sky_type", "b"),
    ("revision", "i"), ("num_sectors", "h"), ("num_walls", "h"),
    ("num_sprites", "h"),
]
MAIN_STRUCT = struct.Struct("<" + "".join(code for _, code in MAIN_FIELDS))
assert MAIN_STRUCT.size == 37

SECTOR_FIELDS = [
    ("wall_ptr", "h"), ("wall_count", "h"), ("ceiling_z", "i"), ("floor_z", "i"),
    ("ceiling_stat", "H"), ("floor_stat", "H"), ("ceiling_picnum", "h"),
    ("ceiling_heinum", "h"), ("ceiling_shade", "b"), ("ceiling_pal", "B"),
    ("ceiling_x_panning", "B"), ("ceiling_y_panning", "B"), ("floor_picnum", "h"),
    ("floor_heinum", "h"), ("floor_shade", "b"), ("floor_pal", "B"),
    ("floor_x_panning", "B"), ("floor_y_panning", "B"), ("visibility", "B"),
    ("filler", "B"), ("type", "h"), ("hitag", "h"), ("extra", "h"),
]
WALL_FIELDS = [
    ("x", "i"), ("y", "i"), ("point2", "h"), ("next_wall", "h"),
    ("next_sector", "h"), ("cstat", "H"), ("picnum", "h"), ("over_picnum", "h"),
    ("shade", "b"), ("pal", "B"), ("x_repeat", "B"), ("y_repeat", "B"),
    ("x_panning", "B"), ("y_panning", "B"), ("type", "h"), ("hitag", "h"),
    ("extra", "h"),
]
SPRITE_FIELDS = [
    ("x", "i"), ("y", "i"), ("z", "i"), ("cstat", "H"), ("picnum", "h"),
    ("shade", "b"), ("pal", "B"), ("clipdist", "B"), ("detail", "B"),
    ("x_repeat", "B"), ("y_repeat", "B"), ("x_offset", "b"), ("y_offset", "b"),
    ("sector", "h"), ("status", "h"), ("angle", "h"), ("owner", "h"),
    ("index", "h"), ("y_velocity", "h"), ("initial_type", "h"), ("type", "h"),
    ("flags", "h"), ("extra", "h"),
]


def _record_struct(fields: list[tuple[str, str]], size: int) -> struct.Struct:
    value = struct.Struct("<" + "".join(code for _, code in fields))
    assert value.size == size, (value.size, size)
    return value


SECTOR_STRUCT = _record_struct(SECTOR_FIELDS, 40)
WALL_STRUCT = _record_struct(WALL_FIELDS, 32)
SPRITE_STRUCT = _record_struct(SPRITE_FIELDS, 44)

# (neutral field name, bit width, signed). Order is the authoritative on-disk order.
XSECTOR_SCHEMA = [
    ("reference", 14, True), ("state", 1, False), ("busy", 17, False),
    ("data", 16, False), ("tx_id", 10, False), ("busy_wave_a", 3, False),
    ("busy_wave_b", 3, False), ("rx_id", 10, False), ("command", 8, False),
    ("trigger_on", 1, False), ("trigger_off", 1, False), ("busy_time_a", 12, False),
    ("wait_time_a", 12, False), ("rest_state", 1, False), ("interruptable", 1, False),
    ("amplitude", 8, True), ("shade_frequency", 8, False), ("retrigger_a", 1, False),
    ("retrigger_b", 1, False), ("shade_phase", 8, False), ("shade_wave", 4, False),
    ("shade_always", 1, False), ("shade_floor", 1, False), ("shade_ceiling", 1, False),
    ("shade_walls", 1, False), ("shade", 8, True), ("pan_always", 1, False),
    ("pan_floor", 1, False), ("pan_ceiling", 1, False), ("drag", 1, False),
    ("underwater", 1, False), ("depth", 3, False), ("pan_velocity", 8, False),
    ("pan_angle", 11, False), ("unused_1", 1, False), ("decoupled", 1, False),
    ("trigger_once", 1, False), ("is_triggered", 1, False), ("key", 3, False),
    ("trigger_push", 1, False), ("trigger_vector", 1, False),
    ("trigger_reserved", 1, False), ("trigger_enter", 1, False),
    ("trigger_exit", 1, False), ("trigger_wall_push", 1, False),
    ("colored_lights", 1, False), ("unused_2", 1, False), ("busy_time_b", 12, False),
    ("wait_time_b", 12, False), ("stop_on", 1, False), ("stop_off", 1, False),
    ("ceiling_pal_2", 4, False), ("off_ceiling_z", 32, True), ("on_ceiling_z", 32, True),
    ("off_floor_z", 32, True), ("on_floor_z", 32, True), ("marker_0", 16, True),
    ("marker_1", 16, True), ("crush", 1, False), ("ceiling_x_pan_fraction", 8, False),
    ("ceiling_y_pan_fraction", 8, False), ("floor_x_pan_fraction", 8, False),
    ("damage_type", 3, False), ("floor_pal_2", 4, False),
    ("floor_y_pan_fraction", 8, False), ("locked", 1, False), ("wind_velocity", 10, False),
    ("wind_angle", 11, False), ("wind_always", 1, False), ("dude_lockout", 1, False),
    ("bob_theta", 11, False), ("bob_z_range", 5, False), ("bob_speed", 12, True),
    ("bob_always", 1, False), ("bob_floor", 1, False), ("bob_ceiling", 1, False),
    ("bob_rotate", 1, False),
]
XWALL_SCHEMA = [
    ("reference", 14, True), ("state", 1, False), ("busy", 17, False),
    ("data", 16, True), ("tx_id", 10, False), ("unused_1", 6, False),
    ("rx_id", 10, False), ("command", 8, False), ("trigger_on", 1, False),
    ("trigger_off", 1, False), ("busy_time", 12, False), ("wait_time", 12, False),
    ("rest_state", 1, False), ("interruptable", 1, False), ("pan_always", 1, False),
    ("pan_x_velocity", 8, True), ("pan_y_velocity", 8, True), ("decoupled", 1, False),
    ("trigger_once", 1, False), ("is_triggered", 1, False), ("key", 3, False),
    ("trigger_push", 1, False), ("trigger_vector", 1, False), ("trigger_touch", 1, False),
    ("unused_2", 2, False), ("x_pan_fraction", 8, False), ("y_pan_fraction", 8, False),
    ("locked", 1, False), ("dude_lockout", 1, False), ("unused_3", 4, False),
    ("unused_4", 32, False),
]
XSPRITE_SCHEMA = [
    ("reference", 14, True), ("state", 1, False), ("busy", 17, False),
    ("tx_id", 10, False), ("rx_id", 10, False), ("command", 8, False),
    ("trigger_on", 1, False), ("trigger_off", 1, False), ("wave", 2, False),
    ("busy_time", 12, False), ("wait_time", 12, False), ("rest_state", 1, False),
    ("interruptable", 1, False), ("unused_1", 2, False), ("respawn_pending", 2, False),
    ("unused_2", 1, False), ("launch_team", 1, False), ("drop_item", 8, False),
    ("decoupled", 1, False), ("trigger_once", 1, False), ("is_triggered", 1, False),
    ("key", 3, False), ("trigger_push", 1, False), ("trigger_vector", 1, False),
    ("trigger_impact", 1, False), ("trigger_pickup", 1, False), ("trigger_touch", 1, False),
    ("trigger_sight", 1, False), ("trigger_proximity", 1, False), ("unused_3", 2, False),
    ("launch_skill", 5, False), ("launch_single", 1, False), ("launch_bloodbath", 1, False),
    ("launch_coop", 1, False), ("dude_lockout", 1, False), ("data_1", 16, True),
    ("data_2", 16, True), ("data_3", 16, True), ("goal_angle", 11, False),
    ("dodge_direction", 2, True), ("locked", 1, False), ("medium", 2, False),
    ("respawn", 2, False), ("data_4", 16, False), ("unused_4", 6, False),
    ("lock_message", 8, False), ("health", 12, False), ("dude_deaf", 1, False),
    ("dude_ambush", 1, False), ("dude_guard", 1, False), ("dude_flag_4", 1, False),
    ("target", 16, True), ("target_x", 32, True), ("target_y", 32, True),
    ("target_z", 32, True), ("burn_time", 16, False), ("burn_source", 16, True),
    ("height", 16, False), ("state_timer", 16, False),
]

assert sum(bits for _, bits, _ in XSECTOR_SCHEMA) == 60 * 8
assert sum(bits for _, bits, _ in XWALL_SCHEMA) == 24 * 8
assert sum(bits for _, bits, _ in XSPRITE_SCHEMA) == 52 * 8


def crypt(data: bytes, key: int) -> bytes:
    return bytes(byte ^ ((key + i) & 0xFF) for i, byte in enumerate(data))


def _unpack_struct(data: bytes, fields: list[tuple[str, str]], codec: struct.Struct) -> dict[str, int]:
    return dict(zip((name for name, _ in fields), codec.unpack(data)))


def _pack_struct(values: dict[str, int], fields: list[tuple[str, str]], codec: struct.Struct) -> bytes:
    try:
        return codec.pack(*(values[name] for name, _ in fields))
    except (KeyError, struct.error) as exc:
        raise BloodMapError(f"cannot encode record: {exc}") from exc


def _unpack_bits(data: bytes, schema: list[tuple[str, int, bool]], kind: str) -> PackedExtra:
    bit_pos = 0
    values: dict[str, int] = {}
    raw = int.from_bytes(data, "little")
    for name, width, signed in schema:
        mask = (1 << width) - 1
        value = (raw >> bit_pos) & mask
        if signed and value & (1 << (width - 1)):
            value -= 1 << width
        values[name] = value
        bit_pos += width
    byte_pos = (bit_pos + 7) // 8
    return PackedExtra(kind=kind, fields=values, opaque_tail=data[byte_pos:])


def _pack_bits(extra: PackedExtra, schema: list[tuple[str, int, bool]], size: int) -> bytes:
    raw = 0
    bit_pos = 0
    for name, width, _signed in schema:
        try:
            value = int(extra.fields[name])
        except KeyError as exc:
            raise BloodMapError(f"missing {extra.kind} field {name}") from exc
        minimum = -(1 << (width - 1)) if _signed else 0
        maximum = (1 << (width - (1 if _signed else 0))) - 1 if _signed else (1 << width) - 1
        if not minimum <= value <= maximum:
            raise BloodMapError(f"{extra.kind}.{name}={value} does not fit {_signed and 'signed ' or ''}{width} bits")
        raw |= (value & ((1 << width) - 1)) << bit_pos
        bit_pos += width
    known = raw.to_bytes((bit_pos + 7) // 8, "little")
    value = known + extra.opaque_tail
    if len(value) != size:
        raise BloodMapError(f"{extra.kind} encoded size is {len(value)}, expected {size}")
    return value


def _parse_extra_header(data: bytes) -> ExtraHeader:
    if len(data) != 128:
        raise BloodMapError("extra header must be 128 bytes")
    xsprite_size, xwall_size, xsector_size = struct.unpack_from("<iii", data, 64)
    sig, hv, flags, width, height, palette, repeat, visibility = struct.unpack_from("<3sbbhhbbi", data, 76)
    return ExtraHeader(
        copyright=data[:64], xsprite_size=xsprite_size, xwall_size=xwall_size,
        xsector_size=xsector_size, xmp_signature=sig, xmp_header_version=hv,
        xmp_map_flags=flags, xmp_board_width=width, xmp_board_height=height,
        xmp_palette=palette, xmp_sky_repeat_count=repeat, xmp_sky_visibility=visibility,
        reserved=data[91:],
    )


def _pack_extra_header(header: ExtraHeader) -> bytes:
    if len(header.copyright) != 64 or len(header.xmp_signature) != 3 or len(header.reserved) != 37:
        raise BloodMapError("invalid extra header component length")
    return b"".join([
        header.copyright,
        struct.pack("<iii", header.xsprite_size, header.xwall_size, header.xsector_size),
        struct.pack("<3sbbhhbbi", header.xmp_signature, header.xmp_header_version,
                    header.xmp_map_flags, header.xmp_board_width, header.xmp_board_height,
                    header.xmp_palette, header.xmp_sky_repeat_count, header.xmp_sky_visibility),
        header.reserved,
    ])


def _take(data: bytes, offset: int, size: int, label: str) -> tuple[bytes, int]:
    end = offset + size
    if end > len(data):
        raise BloodMapError(f"truncated {label} at 0x{offset:x}: need {size} bytes")
    return data[offset:end], end


def parse_map(data: bytes, *, verify_crc: bool = True) -> DiskMap:
    if len(data) < 10:
        raise BloodMapError("file is too short to be a Blood MAP")
    if data[:4] != SIGNATURE:
        raise BloodMapError(f"invalid signature {data[:4]!r}")
    version = struct.unpack_from("<H", data, 4)[0]
    major = version >> 8
    if major not in {6, 7}:
        raise BloodMapError(f"unsupported Blood MAP version 0x{version:04x}")
    stored_crc = struct.unpack_from("<I", data, len(data) - 4)[0]
    actual_crc = zlib.crc32(data[:-4]) & 0xFFFFFFFF
    if verify_crc and stored_crc != actual_crc:
        raise BloodMapError(f"CRC mismatch: stored {stored_crc:08x}, computed {actual_crc:08x}")

    offset = 6
    raw, offset = _take(data, offset, MAIN_STRUCT.size, "main header")
    if major == 7:
        raw = crypt(raw, MATT_ID_NEW)
    header = _unpack_struct(raw, MAIN_FIELDS, MAIN_STRUCT)
    for name in ("num_sectors", "num_walls", "num_sprites"):
        if header[name] < 0:
            raise BloodMapError(f"negative {name}: {header[name]}")
    sky_bits = header["sky_bits"]
    if not 0 <= sky_bits <= 8:
        raise BloodMapError(f"unsafe sky_bits value {sky_bits}")

    extra_header = None
    if major == 7:
        raw, offset = _take(data, offset, 128, "extra header")
        extra_header = _parse_extra_header(crypt(raw, header["num_walls"]))
        sizes = (extra_header.xsector_size, extra_header.xwall_size, extra_header.xsprite_size)
        if sizes[0] < 60 or sizes[1] < 24 or sizes[2] < 52:
            raise BloodMapError(f"unsupported truncated extended record sizes {sizes}")
    else:
        sizes = (60, 24, 56)

    sky_count = 1 << sky_bits
    raw, offset = _take(data, offset, sky_count * 2, "sky offsets")
    if major == 7:
        raw = crypt(raw, len(raw))
    sky_offsets = list(struct.unpack("<" + "h" * sky_count, raw))

    def parse_objects(
        count: int, fields: list[tuple[str, str]], codec: struct.Struct,
        key: int, extra_size: int, schema: list[tuple[str, int, bool]], kind: str,
    ) -> list[DiskObject]:
        nonlocal offset
        result = []
        for index in range(count):
            raw_record, offset = _take(data, offset, codec.size, f"{kind.lower()}[{index}]")
            if major == 7:
                raw_record = crypt(raw_record, key)
            values = _unpack_struct(raw_record, fields, codec)
            extra = None
            if values["extra"] > 0:
                raw_extra, offset = _take(data, offset, extra_size, f"{kind.lower()}[{index}] {kind}")
                extra = _unpack_bits(raw_extra, schema, kind)
            result.append(DiskObject(fields=values, extra=extra))
        return result

    revision = header["revision"]
    sectors = parse_objects(header["num_sectors"], SECTOR_FIELDS, SECTOR_STRUCT,
                            revision * SECTOR_STRUCT.size, sizes[0], XSECTOR_SCHEMA, "XSECTOR")
    walls = parse_objects(header["num_walls"], WALL_FIELDS, WALL_STRUCT,
                          (revision * SECTOR_STRUCT.size) | MATT_ID_NEW,
                          sizes[1], XWALL_SCHEMA, "XWALL")
    sprites = parse_objects(header["num_sprites"], SPRITE_FIELDS, SPRITE_STRUCT,
                            (revision * SPRITE_STRUCT.size) | MATT_ID_NEW,
                            sizes[2], XSPRITE_SCHEMA, "XSPRITE")
    if offset != len(data) - 4:
        raise BloodMapError(f"unexpected {len(data) - 4 - offset} bytes before CRC at 0x{offset:x}")
    return DiskMap(
        version=version, header=header, extra_header=extra_header, sky_offsets=sky_offsets,
        sectors=sectors, walls=walls, sprites=sprites, source_crc32=stored_crc,
        source_size=len(data),
    )


def read_map(path: str | Path, *, verify_crc: bool = True) -> DiskMap:
    return parse_map(Path(path).read_bytes(), verify_crc=verify_crc)


def encode_map(disk: DiskMap) -> bytes:
    major = disk.version >> 8
    if major not in {6, 7}:
        raise BloodMapError(f"unsupported Blood MAP version 0x{disk.version:04x}")
    header = dict(disk.header)
    header.update(num_sectors=len(disk.sectors), num_walls=len(disk.walls), num_sprites=len(disk.sprites))
    sky_count = 1 << header["sky_bits"]
    if len(disk.sky_offsets) != sky_count:
        raise BloodMapError(f"sky has {len(disk.sky_offsets)} offsets, expected {sky_count}")
    parts = [SIGNATURE, struct.pack("<H", disk.version)]
    raw_header = _pack_struct(header, MAIN_FIELDS, MAIN_STRUCT)
    parts.append(crypt(raw_header, MATT_ID_NEW) if major == 7 else raw_header)

    if major == 7:
        if disk.extra_header is None:
            raise BloodMapError("version 7 map is missing its extra header")
        eh = disk.extra_header
        sizes = (eh.xsector_size, eh.xwall_size, eh.xsprite_size)
        parts.append(crypt(_pack_extra_header(eh), len(disk.walls)))
    else:
        sizes = (60, 24, 56)
    sky_raw = struct.pack("<" + "h" * sky_count, *disk.sky_offsets)
    parts.append(crypt(sky_raw, len(sky_raw)) if major == 7 else sky_raw)

    def append_objects(
        items: Iterable[DiskObject], fields: list[tuple[str, str]], codec: struct.Struct,
        key: int, size: int, schema: list[tuple[str, int, bool]], kind: str,
    ) -> None:
        for index, obj in enumerate(items):
            raw = _pack_struct(obj.fields, fields, codec)
            parts.append(crypt(raw, key) if major == 7 else raw)
            has_extra = obj.fields["extra"] > 0
            if has_extra != (obj.extra is not None):
                raise BloodMapError(f"{kind.lower()}[{index}] extra reference/object disagree")
            if obj.extra is not None:
                parts.append(_pack_bits(obj.extra, schema, size))

    revision = header["revision"]
    append_objects(disk.sectors, SECTOR_FIELDS, SECTOR_STRUCT, revision * 40,
                   sizes[0], XSECTOR_SCHEMA, "XSECTOR")
    append_objects(disk.walls, WALL_FIELDS, WALL_STRUCT, (revision * 40) | MATT_ID_NEW,
                   sizes[1], XWALL_SCHEMA, "XWALL")
    append_objects(disk.sprites, SPRITE_FIELDS, SPRITE_STRUCT, (revision * 44) | MATT_ID_NEW,
                   sizes[2], XSPRITE_SCHEMA, "XSPRITE")
    content = b"".join(parts)
    return content + struct.pack("<I", zlib.crc32(content) & 0xFFFFFFFF)


def write_map(disk: DiskMap, path: str | Path) -> None:
    Path(path).write_bytes(encode_map(disk))


def locate_offset(disk: DiskMap, target: int) -> str:
    """Describe the smallest decoded structure containing a byte offset."""
    if target < 0:
        return "before file"
    if target < 6:
        return "signature/version"
    offset = 6
    if target < offset + 37:
        return "main header"
    offset += 37
    major = disk.version >> 8
    if major == 7:
        if target < offset + 128:
            return "extra header"
        offset += 128
    sky_size = len(disk.sky_offsets) * 2
    if target < offset + sky_size:
        return f"sky offset[{(target - offset) // 2}]"
    offset += sky_size

    sizes = (60, 24, 56)
    if disk.extra_header is not None:
        sizes = (disk.extra_header.xsector_size, disk.extra_header.xwall_size, disk.extra_header.xsprite_size)
    for label, items, record_size, extra_size in (
        ("sector", disk.sectors, 40, sizes[0]), ("wall", disk.walls, 32, sizes[1]),
        ("sprite", disk.sprites, 44, sizes[2]),
    ):
        for index, obj in enumerate(items):
            if target < offset + record_size:
                return f"{label}[{index}] record +0x{target-offset:x}"
            offset += record_size
            if obj.extra is not None:
                if target < offset + extra_size:
                    return f"{label}[{index}] {obj.extra.kind} +0x{target-offset:x}"
                offset += extra_size
    if target < offset + 4:
        return "CRC-32"
    return "after file"
