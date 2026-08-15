from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class ArtError(ValueError):
    pass


@dataclass(frozen=True)
class ArtTile:
    tile: int
    width: int
    height: int
    pixels: bytes


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


def read_art_directory(directory: str | Path) -> dict[int, ArtTile]:
    result: dict[int, ArtTile] = {}
    paths = sorted(Path(directory).glob("[Tt][Ii][Ll][Ee][Ss]*.[Aa][Rr][Tt]"))
    if not paths:
        raise ArtError(f"no TILES*.ART files found under {directory}")
    for path in paths:
        data = path.read_bytes()
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
        offset = table_end
        for local, (width, height) in enumerate(zip(widths, heights)):
            size = width * height
            end = offset + size
            if end > len(data):
                raise ArtError(f"tile {first + local} pixels in {path} are truncated")
            if size:
                result[first + local] = ArtTile(first + local, width, height, data[offset:end])
            offset = end
    return result


def _feature(tile: ArtTile, palette: tuple[tuple[int, int, int], ...]) -> tuple[float, ...]:
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
        math.log2(tile.width / tile.height),
        math.log2(max(tile.width, tile.height)),
        *means,
        deviation,
        *histogram,
        *thumbnail,
    )


def nearest_art_tiles(
    source_tiles: Iterable[int],
    target_tiles: Iterable[int],
    *,
    source_art: str | Path,
    target_art: str | Path,
    source_palette: str | Path,
    target_palette: str | Path,
) -> dict[int, dict[str, float | int]]:
    source_library, target_library = read_art_directory(source_art), read_art_directory(target_art)
    source_pal, target_pal = read_palette(source_palette), read_palette(target_palette)
    candidates = sorted(set(int(value) for value in target_tiles) & set(target_library))
    if not candidates:
        raise ArtError("target material candidate set is empty")
    target_features = {tile: _feature(target_library[tile], target_pal) for tile in candidates}
    weights = (3.0, 0.35, 2.0, 2.0, 2.0, 1.5, *(1.0,) * 8, *(0.25,) * 16)
    result: dict[int, dict[str, float | int]] = {}
    for source in sorted(set(int(value) for value in source_tiles)):
        if source not in source_library:
            continue
        feature = _feature(source_library[source], source_pal)
        ranked = []
        for target, other in target_features.items():
            distance = sum(weight * (left - right) ** 2 for weight, left, right in zip(weights, feature, other))
            ranked.append((distance, target))
        distance, target = min(ranked)
        result[source] = {"blood_tile": target, "distance": round(math.sqrt(distance), 6)}
    return result
