"""What gives light in Blood and how each is set down: the tiles, whether each may be a texture or only a sprite, where on it the light sits, and how strong it is.

The owner, 2026-11-20, after a first pass that hung wall torches everywhere:
"you should be using different types of light sources, check existing levels
... Torches should be used only where it makes sense", and of the tiles:
"501, 2290, 2288, 796 can be used as textures, 261 and 511 can also be
textures, but they are not direct light sources. rest of them would be
sprite only". How the campaign sets each down is measured by
`tools/light_sources.py` (knowledge/blood/light-sources.json):

* a PANEL is a small sector the size of the light, its ceiling recessed
  1024 above the room's and shaded 0 (124 in the campaign); 2290 is one
  tile at 512 x 1024, 501 1024 x 1024, the tubes 2288 and 796 long strips;
* a CEILING SPRITE lies flat against the ceiling (795, the commonest light
  in the game: 1,068 uses in 42 maps);
* HANGING, STANDING and WALL lights are flames and lamps drawn fullbright.

`point` is where on the drawn sprite its light sits, as a share of its
drawn height from the top: a street lamp's light is in its head, a chain
lamp's at the foot of its chain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .model import record_fields as _f


@dataclass(frozen=True)
class LightKind:
    tile: int
    name: str
    form: str                 # "panel", "ceiling", "hanging", "standing", "wall" or "window"
    texture: bool             # may be a ceiling or wall texture
    sprite: bool              # may be a sprite
    point: float = 0.5        # light point, share of the drawn height from its top
    intensity: float = 1.0    # against a wall torch
    panel: tuple = ()         # (width, length) in plan units: one whole tile, or a strip


KINDS: dict[int, LightKind] = {k.tile: k for k in (
    # textures (the owner: these four may be textures)
    LightKind(2290, "fluorescent light", "panel", True, True, intensity=1.4, panel=(512, 1024)),
    LightKind(2288, "fluorescent light, vertical", "panel", True, True, intensity=1.4, panel=(512, 2048)),
    LightKind(501, "technical light", "panel", True, True, intensity=1.2, panel=(1024, 1024)),
    LightKind(796, "fluorescent tube", "panel", True, True, intensity=1.0, panel=(256, 2048)),
    # sprites only
    LightKind(795, "flat round light", "ceiling", False, True, point=0.5, intensity=1.0),
    LightKind(676, "round glass lamp", "ceiling", False, True, point=0.5, intensity=1.0),
    LightKind(677, "round glass lamp", "ceiling", False, True, point=0.5, intensity=1.0),
    LightKind(641, "lamp hanging on a chain", "hanging", False, True, point=0.92, intensity=1.0),
    LightKind(1701, "hanging chain lamp", "hanging", False, True, point=0.85, intensity=1.1),
    LightKind(945, "brass hanging lamp", "hanging", False, True, point=0.85, intensity=1.0),
    LightKind(640, "street lamp post", "standing", False, True, point=0.08, intensity=1.6),
    LightKind(2493, "street lamp", "standing", False, True, point=0.08, intensity=1.6),
    LightKind(506, "burning wall torch", "wall", False, True, point=0.15, intensity=1.0),
    LightKind(570, "wooden torch bracket", "wall", False, True, point=0.2, intensity=0.8),
    LightKind(554, "wooden wall sconce", "wall", False, True, point=0.2, intensity=0.7),
    LightKind(580, "standing candelabrum", "standing", False, True, point=0.1, intensity=0.8),
    LightKind(560, "tall candle stand", "standing", False, True, point=0.1, intensity=0.5),
    LightKind(938, "lit candle", "standing", False, True, point=0.15, intensity=0.4),
    LightKind(550, "brazier", "standing", False, True, point=0.2, intensity=1.0),
    LightKind(2101, "small flame", "standing", False, True, point=0.4, intensity=1.0),
    LightKind(3566, "bonfire", "standing", False, True, point=0.4, intensity=1.6),
    # in the city and missed by the first list (found by name, 2026-11-20)
    LightKind(908, "flame", "standing", False, True, point=0.4, intensity=1.0),
    LightKind(2183, "recessed wall lamp, lit", "wall", False, True, point=0.5, intensity=1.0),
    LightKind(693, "lit brass lantern", "standing", False, True, point=0.5, intensity=0.8),
    # windows: daylight through glass, into the room the glass hangs in (the
    # owner, 2026-11-21: "the stained glass should be giving some light in")
    # (the owner, on the first strength, 0.7 and 1.2: "it looks little bit
    # too much light for the church")
    LightKind(569, "stained glass lancet", "window", False, True, point=0.5, intensity=0.35),
    LightKind(265, "stained glass, a haloed figure", "window", False, True, point=0.5, intensity=0.6),
)}

#: textures that look lit but give no light (the owner)
NOT_LIGHTS = frozenset({261, 511})
#: a panel ceiling counts as lit at or below this shade
PANEL_SHADE = 8
#: a window's light stands this far inside the glass (plan units): far enough
#: that the wall it hangs on stops it from lighting the far side
WINDOW_INSET = 512


def is_lamp(picnum: int) -> bool:
    """A light someone hung or set down, as against daylight through a window."""
    kind = KINDS.get(int(picnum))
    return kind is not None and kind.form != "window"


def _drawn(f, art) -> tuple[int, int]:
    from .placement import drawn_extent

    tile = art.get(int(f["picnum"]))
    if tile is None or not tile.height:
        return int(f["z"]), int(f["z"])
    return drawn_extent(tile.height, int(tile.animation["yofs"]), int(f["y_repeat"]),
                        int(f["cstat"]), int(f["z"]))


def sprite_lights(disk, art=None) -> list[tuple]:
    """(x, y, z, sector, intensity) for every visible light sprite, at its light point; a window adds the way it faces."""
    if art is None:
        from .shade_table import _art
        art = _art()
    # what the game never draws gives no light: an exploder wears the flame
    # tile (908) and lit the bricked-up room it waits in
    from .visual import HIDDEN_STATUS, HIDDEN_TYPES
    out = []
    for sprite in disk.sprites:
        f = _f(sprite)
        kind = KINDS.get(int(f["picnum"]))
        if kind is None or not kind.sprite or int(f["cstat"]) & 0x8000 or int(f["sector"]) < 0:
            continue
        if int(f["type"]) in HIDDEN_TYPES or int(f["status"]) in HIDDEN_STATUS:
            continue
        if kind.form == "window":
            light = _window(disk, f, art, kind)
            if light is not None:
                out.append(light)
            continue
        if int(f["cstat"]) & 48 == 32:                   # flat: the light is where it lies
            z = int(f["z"])
        else:
            top, bottom = _drawn(f, art)
            z = top + (bottom - top) * kind.point
        out.append((float(f["x"]), float(f["y"]), float(z), int(f["sector"]), kind.intensity))
    return out


def _window(disk, f, art, kind):
    """Glass on a roofed room's wall lets daylight in: a light just inside it; glass under the sky gives none."""
    import math

    from shapely.geometry import Point, Polygon

    from .sector_geom import outline_and_holes

    sector = int(f["sector"])
    if int(_f(disk.sectors[sector])["ceiling_stat"]) & 1:
        return None
    try:
        outline, holes = outline_and_holes(disk, sector)
    except Exception:
        return None
    room = Polygon(outline, holes)
    top, bottom = _drawn(f, art)
    z = top + (bottom - top) * kind.point
    a = int(f["angle"]) * 2 * math.pi / 2048
    x, y = float(f["x"]), float(f["y"])
    for sign in (1, -1):                                 # into the room, whichever way the glass faces
        ix, iy = sign * math.cos(a), sign * math.sin(a)
        px, py = x + ix * WINDOW_INSET, y + iy * WINDOW_INSET
        if room.contains(Point(px, py)):
            # daylight through glass travels in and down (z grows downward)
            down = math.sqrt(0.5)
            return (px, py, float(z), sector, kind.intensity, (ix * down, iy * down, down))
    return None


def panel_lights(disk) -> list[tuple[float, float, float, int, float]]:
    """A light at the middle of every lit panel ceiling, as strong as the panel is large."""
    from .sector_geom import outline_and_holes
    from shapely.geometry import Polygon

    out = []
    for index, sector in enumerate(disk.sectors):
        f = _f(sector)
        kind = KINDS.get(int(f["ceiling_picnum"]))
        if (kind is None or not kind.texture or int(f["ceiling_stat"]) & 1
                or int(f["ceiling_shade"]) > PANEL_SHADE):
            continue
        try:
            outline, holes = outline_and_holes(disk, index)
        except Exception:
            continue
        poly = Polygon(outline, holes)
        if poly.area > 4 * 2048 * 2048:                   # a whole lit ceiling, not a panel
            continue
        c = poly.representative_point()
        size = max(0.5, poly.area / (512 * 1024))
        out.append((c.x, c.y, float(int(f["ceiling_z"]) + 512), index, kind.intensity * min(size, 4.0) ** 0.5))
    return out


def lights(disk, art=None) -> list[tuple[float, float, float, int, float]]:
    return sprite_lights(disk, art) + panel_lights(disk)
