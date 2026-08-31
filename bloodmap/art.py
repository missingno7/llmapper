from __future__ import annotations

import math
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class ArtError(ValueError):
    pass


# EDuke32 / Ken Build picanm_t packed into the ART int32 table.
# bits 0-5 frames, 6-7 type, 8-15 xofs, 16-23 yofs, 24-27 speed, 28-31 extra.
ANIM_NONE, ANIM_OSCILLATE, ANIM_FORWARD, ANIM_BACKWARD = 0, 1, 2, 3
ANIM_NAMES = {0: "none", 1: "oscillate", 2: "forward", 3: "backward"}
FEATURE_WEIGHTS = (3.0, 0.35, 2.0, 2.0, 2.0, 1.5, *(1.0,) * 8, *(0.25,) * 16)


@dataclass(frozen=True)
class ArtTile:
    tile: int
    width: int
    height: int
    pixels: bytes
    picanm: int = 0

    @property
    def animation(self) -> dict[str, int | str]:
        return decode_picanm(self.picanm)


def decode_picanm(packed: int) -> dict[str, int | str]:
    value = int(packed) & 0xFFFFFFFF
    frames = value & 63
    animtype = (value >> 6) & 3
    xofs = (value >> 8) & 255
    yofs = (value >> 16) & 255
    if xofs >= 128:
        xofs -= 256
    if yofs >= 128:
        yofs -= 256
    return {
        "frames": frames,
        "type": ANIM_NAMES[animtype],
        "type_id": animtype,
        "xofs": xofs,
        "yofs": yofs,
        "speed": (value >> 24) & 15,
        "extra": (value >> 28) & 15,
        "packed": value,
    }


def encode_picanm(
    *,
    frames: int = 0,
    type_id: int = 0,
    xofs: int = 0,
    yofs: int = 0,
    speed: int = 0,
    extra: int = 0,
) -> int:
    return (
        (frames & 63)
        | ((type_id & 3) << 6)
        | ((xofs & 255) << 8)
        | ((yofs & 255) << 16)
        | ((speed & 15) << 24)
        | ((extra & 15) << 28)
    )


def read_palette(path: str | Path) -> tuple[tuple[int, int, int], ...]:
    data = Path(path).read_bytes()
    if len(data) < 768:
        raise ArtError(f"palette {path} is shorter than 768 bytes")
    data = data[:768]
    scale = 4 if max(data) <= 63 else 1
    return tuple(
        tuple(min(255, data[index + channel] * scale) for channel in range(3))
        for index in range(0, 768, 3)
    )


def write_palette(path: str | Path, colors: Iterable[tuple[int, int, int]]) -> None:
    entries = list(colors)
    if len(entries) != 256:
        raise ArtError(f"palette must contain 256 RGB triples, not {len(entries)}")
    Path(path).write_bytes(bytes(channel for color in entries for channel in color))


def read_art_directory(directory: str | Path) -> dict[int, ArtTile]:
    result: dict[int, ArtTile] = {}
    paths = sorted(Path(directory).glob("[Tt][Ii][Ll][Ee][Ss]*.[Aa][Rr][Tt]"))
    if not paths:
        raise ArtError(f"no TILES*.ART files found under {directory}")
    for path in paths:
        result.update(read_art_file(path))
    return result


def read_art_file(path: str | Path) -> dict[int, ArtTile]:
    data = Path(path).read_bytes()
    if len(data) < 16:
        raise ArtError(f"ART file {path} is truncated")
    version, _num_tiles, first, last = struct.unpack_from("<4i", data)
    if version != 1 or first < 0 or last < first:
        raise ArtError(f"unsupported ART header in {path}")
    count = last - first + 1
    table_end = 16 + count * 8
    if table_end > len(data):
        raise ArtError(f"ART tables in {path} are truncated")
    widths = struct.unpack_from(f"<{count}H", data, 16)
    heights = struct.unpack_from(f"<{count}H", data, 16 + count * 2)
    picanms = struct.unpack_from(f"<{count}i", data, 16 + count * 4)
    result: dict[int, ArtTile] = {}
    offset = table_end
    for local, (width, height, picanm) in enumerate(zip(widths, heights, picanms)):
        size = width * height
        end = offset + size
        if end > len(data):
            raise ArtError(f"tile {first + local} pixels in {path} are truncated")
        if size:
            result[first + local] = ArtTile(
                first + local, width, height, data[offset:end], int(picanm) & 0xFFFFFFFF,
            )
        offset = end
    return result


def write_art_file(path: str | Path, tiles: dict[int, ArtTile], *, first: int | None = None) -> None:
    if not tiles:
        raise ArtError("cannot write an empty ART file")
    ids = sorted(tiles)
    start = ids[0] if first is None else int(first)
    last = ids[-1]
    count = last - start + 1
    widths, heights, picanms, pixels = [], [], [], []
    for tile_id in range(start, last + 1):
        tile = tiles.get(tile_id)
        if tile is None:
            widths.append(0)
            heights.append(0)
            picanms.append(0)
            continue
        widths.append(tile.width)
        heights.append(tile.height)
        picanms.append(tile.picanm)
        pixels.append(tile.pixels)
    header = struct.pack("<4i", 1, count, start, last)
    table = (
        struct.pack(f"<{count}H", *widths)
        + struct.pack(f"<{count}H", *heights)
        + struct.pack(f"<{count}i", *picanms)
    )
    Path(path).write_bytes(header + table + b"".join(pixels))


def transparency_stats(tile: ArtTile) -> dict[str, float | int | bool]:
    total = len(tile.pixels)
    transparent = tile.pixels.count(255)
    opaque = total - transparent
    ratio = (transparent / total) if total else 0.0
    return {
        "width": tile.width,
        "height": tile.height,
        "pixels": total,
        "transparent_pixels": transparent,
        "opaque_pixels": opaque,
        "transparent_ratio": round(ratio, 6),
        "has_mask": transparent > 0 and opaque > 0,
        "fully_transparent": total > 0 and opaque == 0,
        "fully_opaque": transparent == 0,
    }


def art_feature(tile: ArtTile, palette: tuple[tuple[int, int, int], ...]) -> tuple[float, ...]:
    # Build ART stores columns. A small luminance thumbnail plus global colour
    # moments gives a deterministic, dependency-free cross-game similarity cue.
    samples = [value for value in tile.pixels if value != 255]
    if not samples:
        samples = [0]
    colors = [palette[value] for value in samples]
    count = len(colors)
    means = tuple(sum(color[channel] for color in colors) / (255 * count) for channel in range(3))
    luminances = [(77 * r + 150 * g + 29 * b) / (256 * 255) for r, g, b in colors]
    mean_luma = sum(luminances) / count
    deviation = math.sqrt(sum((value - mean_luma) ** 2 for value in luminances) / count)
    histogram = [0.0] * 8
    for value in luminances:
        histogram[min(7, int(value * 8))] += 1 / count
    thumbnail: list[float] = []
    for gy in range(4):
        y = min(tile.height - 1, (2 * gy + 1) * tile.height // 8)
        for gx in range(4):
            x = min(tile.width - 1, (2 * gx + 1) * tile.width // 8)
            color = palette[tile.pixels[x * tile.height + y]]
            thumbnail.append((77 * color[0] + 150 * color[1] + 29 * color[2]) / (256 * 255))
    return (
        math.log2(max(tile.width, 1) / max(tile.height, 1)),
        math.log2(max(tile.width, tile.height, 1)),
        *means,
        deviation,
        *histogram,
        *thumbnail,
    )


def feature_distance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return math.sqrt(
        sum(weight * (a - b) ** 2 for weight, a, b in zip(FEATURE_WEIGHTS, left, right))
    )


def animation_families(tiles: dict[int, ArtTile]) -> list[dict[str, object]]:
    """Native ART animation sequences. Members are consecutive tile IDs."""
    families = []
    claimed: set[int] = set()
    for tile_id in sorted(tiles):
        if tile_id in claimed:
            continue
        info = tiles[tile_id].animation
        frames = int(info["frames"])
        if frames <= 0 or info["type"] == "none":
            continue
        members = [tile_id + offset for offset in range(frames + 1) if tile_id + offset in tiles]
        if len(members) < 2:
            continue
        claimed.update(members)
        families.append({
            "id": f"anim:{members[0]}-{members[-1]}",
            "kind": "native_animation",
            "provenance": "VERIFIED",
            "members": [str(item) for item in members],
            "animation": info,
            "basis": "ART picanm frames/type on the first tile of the run",
        })
    return families


def tile_to_rgb(tile: ArtTile, palette: tuple[tuple[int, int, int], ...]) -> bytes:
    rgb = bytearray(tile.width * tile.height * 3)
    for x in range(tile.width):
        column = x * tile.height
        for y in range(tile.height):
            index = tile.pixels[column + y]
            color = (0, 0, 0) if index == 255 else palette[index]
            offset = (y * tile.width + x) * 3
            rgb[offset:offset + 3] = color
    return bytes(rgb)


#: How far above the mean row-to-row change a course line has to stand.
COURSE_SIGMA = 2.0


def row_luminance(tile: ArtTile,
                  palette: tuple[tuple[int, int, int], ...]) -> list[float]:
    """Mean perceived brightness of each row of a tile, top row first."""
    rgb = tile_to_rgb(tile, palette)
    out = []
    for y in range(tile.height):
        total = 0
        for x in range(tile.width):
            index = (y * tile.width + x) * 3
            total += rgb[index] * 299 + rgb[index + 1] * 587 + rgb[index + 2] * 114
        out.append(total / (tile.width * 1000.0) if tile.width else 0.0)
    return out


def course_rows(tile: ArtTile, palette: tuple[tuple[int, int, int], ...], *,
                sigma: float = COURSE_SIGMA) -> list[int]:
    """Rows where a wall tile changes horizontally: its painted courses.

    A cornice, a plinth, the band a shopfront sign sits on -- Blood paints
    them into the tile rather than building them, so they live at fixed
    texture rows. Given a wall's `y_repeat` and anchor, `texture_align`
    turns a row into a world z.

    Returned as the row *below* each change, so row 0 is never a course: an
    edge is between two rows and belongs to the lower one.
    """
    lum = row_luminance(tile, palette)
    if len(lum) < 2:
        return []
    edges = [abs(lum[y] - lum[y - 1]) for y in range(1, len(lum))]
    mean = sum(edges) / len(edges)
    spread = (sum((e - mean) ** 2 for e in edges) / len(edges)) ** 0.5
    if spread <= 0:
        return []          # an even gradient, or a flat tile: no row stands out
    cut = mean + float(sigma) * spread
    return [y + 1 for y, edge in enumerate(edges) if edge >= cut]


def rgb_png(width: int, height: int, rgb: bytes) -> bytes:
    if width <= 0 or height <= 0:
        raise ArtError("PNG dimensions must be positive")
    if len(rgb) != width * height * 3:
        raise ArtError("RGB buffer size does not match dimensions")
    rows = b"".join(b"\x00" + rgb[y * width * 3:(y + 1) * width * 3] for y in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(rows, 9))
        + _png_chunk(b"IEND", b"")
    )


def tile_preview_png(
    tile: ArtTile,
    palette: tuple[tuple[int, int, int], ...],
    *,
    max_size: int = 64,
) -> bytes:
    rgb = tile_to_rgb(tile, palette)
    width, height = tile.width, tile.height
    if max(width, height) > max_size:
        scale = max(width, height) / max_size
        out_w, out_h = max(1, int(width / scale)), max(1, int(height / scale))
        scaled = bytearray(out_w * out_h * 3)
        for y in range(out_h):
            src_y = min(height - 1, y * height // out_h)
            for x in range(out_w):
                src_x = min(width - 1, x * width // out_w)
                src = (src_y * width + src_x) * 3
                dst = (y * out_w + x) * 3
                scaled[dst:dst + 3] = rgb[src:src + 3]
        rgb, width, height = bytes(scaled), out_w, out_h
    return rgb_png(width, height, rgb)


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(tag)
    checksum = zlib.crc32(data, checksum) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", checksum)


def _feature(tile: ArtTile, palette: tuple[tuple[int, int, int], ...]) -> tuple[float, ...]:
    return art_feature(tile, palette)


def nearest_art_tiles(
    source_tiles: Iterable[int],
    target_tiles: Iterable[int],
    *,
    source_art: str | Path,
    target_art: str | Path,
    source_palette: str | Path,
    target_palette: str | Path,
    target_weights: dict[int, int] | None = None,
) -> dict[int, dict[str, float | int]]:
    source_library, target_library = read_art_directory(source_art), read_art_directory(target_art)
    source_pal, target_pal = read_palette(source_palette), read_palette(target_palette)
    candidates = sorted(set(int(value) for value in target_tiles) & set(target_library))
    if not candidates:
        raise ArtError("target material candidate set is empty")
    target_features = {tile: art_feature(target_library[tile], target_pal) for tile in candidates}
    result: dict[int, dict[str, float | int]] = {}
    for source in sorted(set(int(value) for value in source_tiles)):
        if source not in source_library:
            continue
        feature = art_feature(source_library[source], source_pal)
        ranked = []
        for target, other in target_features.items():
            distance = feature_distance(feature, other) ** 2
            if target_weights:
                distance /= 1.0 + 0.2 * math.log2(1.0 + max(0, int(target_weights.get(target, 0))))
            ranked.append((distance, target))
        distance, target = min(ranked)
        result[source] = {"blood_tile": target, "distance": round(math.sqrt(distance), 6)}
    return result
