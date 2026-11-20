"""How much of a place one rendered view shows, measured from the observer's surface list.

The owner, 2026-11-20, on the first GRAVESEND collage: "some of them are
good and some of them are not really showing stuff." A frame square on one
wall, a frame of a column's face, a frame of sky: each renders without an
error and shows nothing. This module turns one view of an observation
manifest (`bloodmap.visual`) into numbers a ranking can stand on, before any
reader is asked:

``subject``   the share of the frame drawn by surfaces of the place itself:
              a wall, floor or ceiling whose sector or wall midpoint lies
              within the place's radius of its focus, or a sprite standing
              there
``things``    how many sprites of the place fill at least 0.1% of the frame
``variety``   how many tiles each fill at least 0.5% of it
``dominant``  the largest share any single surface takes (one wall face, one
              floor): a frame that is mostly one surface shows one surface
``sky``       the share that is parallax sky
``unwritten`` the share no surface wrote (a void, a render fault)

`score` folds them into one number. It is a first round, not a verdict:
the readers decide among the views it keeps, and how often they agree
with it is how it earns its weights.
"""

from __future__ import annotations

from typing import Any, Mapping

#: shares of a frame below which a sprite or a tile is not "shown"
THING_SHARE, TILE_SHARE, SECTOR_SHARE = 0.001, 0.005, 0.005


def _sector_centres(level) -> dict[int, tuple[float, float]]:
    out: dict[int, tuple[float, float]] = {}
    for index, sector in enumerate(level.sectors):
        fields = sector["fields"]
        start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        pts = [(int(level.walls[w]["fields"]["x"]), int(level.walls[w]["fields"]["y"]))
               for w in range(start, start + count)]
        if pts:
            out[index] = (sum(p[0] for p in pts) / len(pts),
                          sum(p[1] for p in pts) / len(pts))
    return out


class Subject:
    """Which sectors, walls and sprites of a level belong to one place.

    A place is a focus point and a radius: anything whose position falls
    inside the circle is the place's, whichever side of a wall it was
    drawn from. That counts a church's facade, seen from the street, as
    the church's even though the wall belongs to the street's sector.
    An optional floor band keeps a sewer under the avenue out of the
    avenue's subject.
    """

    def __init__(self, level, focus: tuple[int, int], radius: int,
                 floor_band: tuple[int, int] | None = None):
        fx, fy = focus
        r2 = radius * radius
        centres = _sector_centres(level)

        def near(x: float, y: float) -> bool:
            return (x - fx) ** 2 + (y - fy) ** 2 <= r2

        def in_band(sector: int) -> bool:
            if floor_band is None:
                return True
            z = int(level.sectors[sector]["fields"]["floor_z"])
            return floor_band[0] <= z <= floor_band[1]

        self.sectors = {s for s, (x, y) in centres.items() if near(x, y) and in_band(s)}
        self.walls: set[int] = set()
        for index, sector in enumerate(level.sectors):
            if not in_band(index):
                continue
            fields = sector["fields"]
            start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
            for w in range(start, start + count):
                a = level.walls[w]["fields"]
                b = level.walls[int(a["point2"])]["fields"]
                if near((int(a["x"]) + int(b["x"])) / 2, (int(a["y"]) + int(b["y"])) / 2):
                    self.walls.add(w)
        self.sprites = {i for i, sprite in enumerate(level.sprites)
                        if near(int(sprite["fields"]["x"]), int(sprite["fields"]["y"]))
                        and in_band(int(sprite["fields"]["sector"]))}

    def owns(self, surface: Mapping[str, Any]) -> bool:
        kind = surface["kind"]
        if kind == "sprite":
            return surface.get("sprite") in self.sprites
        if kind in ("wall", "upper", "lower"):
            return surface.get("wall") in self.walls
        if kind == "sky":
            return False
        return surface.get("sector") in self.sectors


def measure_view(view: Mapping[str, Any], subject: Subject) -> dict[str, float]:
    """The numbers of one manifest view against one place."""
    frame = view.get("frame") or {}
    surfaces = view.get("surfaces") or []
    #: a surface's pixels count what it painted, including what a nearer
    #: surface later painted over, so shares are of everything painted
    total = float(sum(int(s.get("pixels") or 0) for s in surfaces)
                  or frame.get("pixels") or 640 * 480)
    shown = float(frame.get("pixels") or 640 * 480)
    own = 0
    things = set()
    tiles: dict[int, int] = {}
    sectors: dict[int, int] = {}
    dominant = 0
    for surface in surfaces:
        pixels = int(surface.get("pixels") or 0)
        if surface["kind"] == "sky":
            continue
        dominant = max(dominant, pixels)
        tiles[surface["picnum"]] = tiles.get(surface["picnum"], 0) + pixels
        sectors[surface["sector"]] = sectors.get(surface["sector"], 0) + pixels
        if subject.owns(surface):
            own += pixels
            if surface["kind"] == "sprite" and pixels >= THING_SHARE * total:
                things.add(surface["sprite"])
    return {
        "subject": round(own / total, 4),
        "things": len(things),
        "variety": sum(1 for p in tiles.values() if p >= TILE_SHARE * total),
        "sectors": sum(1 for p in sectors.values() if p >= SECTOR_SHARE * total),
        "dominant": round(dominant / total, 4),
        "sky": round(sum(int(s.get("pixels") or 0) for s in surfaces
                         if s["kind"] == "sky") / total, 4),
        "unwritten": round(float(frame.get("unwritten") or 0) / shown, 4),
    }


def score(m: Mapping[str, float]) -> float:
    """One number for a view: the place, its things, and not one wall.

    Each factor is 1 for an unremarkable frame. The weights are a first
    guess, written so a reader's ranking can be held against them.
    """
    # Fitted to the Gravesend showcase's readers (`tools.showcase calibrate`):
    # over 73 rankings of eight finalists (rounds 1-14), against the reader's
    # order variety +0.20, sectors in view +0.17, things +0.11, and the
    # subject's share -0.19 (a place in its surroundings beats a place
    # filling the frame); a little unwritten void +0.21, because it comes
    # with wide views, so only a real void is penalised. These weights took
    # the score's agreement with the reader from 0.11 to 0.28 and its first
    # pick from 10 to 16 of 73 (chance is about 9) -- in sample; the next
    # rounds are the test.
    value = min(m["subject"] / 0.25, 1.0)
    value *= 1.0 - 0.6 * max(0.0, m["subject"] - 0.6)
    value *= min(1.0 + 0.08 * m["things"], 2.0)
    value *= min(m["variety"] / 6.0, 2.5)
    value *= min(0.6 + 0.08 * m["sectors"], 1.6)
    value *= max(0.0, 1.0 - 1.2 * max(0.0, m["dominant"] - 0.3))
    value *= max(0.0, 1.0 - max(0.0, m["sky"] - 0.45))
    value *= max(0.0, 1.0 - 3.0 * max(0.0, m["unwritten"] - 0.1))
    return round(value, 4)
