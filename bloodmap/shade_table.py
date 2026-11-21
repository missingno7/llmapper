"""Blood's palette and shade table, read from BLOOD.RFF: how bright a tile is actually drawn at each shade.

A shade number is not a brightness. The engine draws pixel `p` of a tile at
shade `s` as palette colour `PLU[s][p]`: a lookup table of 64 rows, one per
shade, that the artists built by hand. How much darker shade 8 is than shade
0 depends on that table and on the tile's own colours, so a step that is
plain on a bright stone wall can vanish on dark brick. `brightness(tile, s)`
answers it from the game's own data; nothing here is a curve fitted by eye.

The archive reading follows the observer's (`xmapedit/src_blood/observe/
obs_main.c`): a version-3 directory is XOR-encrypted, and an entry flagged
0x10 has its first 256 bytes encrypted the same way. Decrypted, row 0 of
NORMAL.PLU is the identity map, which is what shade 0 has to be.
"""

from __future__ import annotations

import pathlib
import struct
from functools import lru_cache
from typing import Any

RESOURCES = pathlib.Path("reference/blood")
SHADES = 64


def _crypt(data: bytearray, start: int, length: int, key: int) -> None:
    for i in range(length):
        data[start + i] ^= ((key + i) >> 1) & 0xFF


def read_rff(path: str | pathlib.Path) -> dict[tuple[str, int, str], bytes]:
    """Every entry of an RFF archive: (type, id, name) -> payload, decrypted."""
    data = bytearray(pathlib.Path(path).read_bytes())
    if data[:4] != b"RFF\x1a":
        raise ValueError(f"{path} is not an RFF archive")
    version = struct.unpack_from("<H", data, 4)[0]
    dir_off, count = struct.unpack_from("<II", data, 8)
    if (version & 0xFF00) == 0x300:
        _crypt(data, dir_off, count * 48, (dir_off + (version & 0xFF) * dir_off) & 0xFFFF)
    out = {}
    for i in range(count):
        e = dir_off + i * 48
        off, size = struct.unpack_from("<II", data, e + 16)
        flags = data[e + 32]
        kind = bytes(data[e + 33:e + 36]).rstrip(b"\0").decode("latin-1")
        name = bytes(data[e + 36:e + 44]).rstrip(b"\0").decode("latin-1")
        ident = struct.unpack_from("<i", data, e + 44)[0]
        payload = bytearray(data[off:off + size])
        if flags & 0x10:
            for k in range(min(size, 256)):
                payload[k] ^= (k >> 1) & 0xFF
        out[(kind, ident, name)] = bytes(payload)
    return out


@lru_cache(maxsize=2)
def tables(resource_dir: str = str(RESOURCES)) -> dict[str, Any]:
    """Blood's palette (256 RGB, eight-bit) and NORMAL.PLU (64 rows of 256)."""
    entries = read_rff(pathlib.Path(resource_dir) / "BLOOD.RFF")
    pal = next(v for (kind, ident, _), v in entries.items() if kind == "PAL" and ident == 0)
    plu = next(v for (kind, ident, _), v in entries.items() if kind == "PLU" and ident == 0)
    if len(plu) != SHADES * 256:
        raise ValueError(f"PLU 0 is {len(plu)} bytes, not {SHADES} rows of 256")
    palette = [(pal[i * 3], pal[i * 3 + 1], pal[i * 3 + 2]) for i in range(256)]
    if max(max(c) for c in palette) < 64:           # six-bit, as VGA keeps it
        palette = [(r << 2, g << 2, b << 2) for r, g, b in palette]
    return {"palette": palette, "plu": plu}


def luminance(rgb: tuple[int, int, int]) -> float:
    """Relative luminance, 0..255 (Rec. 601 weights, as a screen is read)."""
    r, g, b = rgb
    return 0.299 * r + 0.587 * g + 0.114 * b


def clamp_shade(shade: int) -> int:
    """The row the engine draws from: below 0 is row 0, past the table its last."""
    return max(0, min(SHADES - 1, int(shade)))


@lru_cache(maxsize=4096)
def _tile_pixels(picnum: int) -> tuple[int, ...]:
    from .art import read_art_directory

    art = _art()
    tile = art.get(int(picnum))
    if tile is None or not tile.pixels:
        return ()
    return tuple(p for p in tile.pixels if p != 255)


@lru_cache(maxsize=1)
def _art():
    from .art import read_art_directory

    return read_art_directory(RESOURCES)


def brightness(picnum: int, shade: int) -> float:
    """Mean luminance (0..255) of a tile drawn at a shade, as the game draws it."""
    pixels = _tile_pixels(picnum)
    if not pixels:
        return 0.0
    t = tables()
    row = clamp_shade(shade) * 256
    plu, palette = t["plu"], t["palette"]
    lum = [luminance(palette[plu[row + i]]) for i in range(256)]
    return sum(lum[p] for p in pixels) / len(pixels)


def curve(picnum: int) -> list[float]:
    """A tile's brightness at every shade 0..63."""
    return [brightness(picnum, s) for s in range(SHADES)]
