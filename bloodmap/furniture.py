"""What a thing is, named rather than numbered.

The companion to `bloodmap.surfaces`. A level said

    decor(506, 128, 1.5, aspect=1.0, shade=-128)

which is four facts about Blood's ART and one about what the author wanted. It
now says ``furnish("torch")``, and the four come from the corpus:

``picnum`` and ``cstat``
    what the tile is and how it is mounted. The mounting is the part that keeps
    going wrong: cstat bit 0x30 is an *alignment*, and a tile whose canonical
    value is 0x20 is a flat plate that lies on a surface. Read as decoration and
    hung on a wall it becomes a disc floating edge-on in the air, which happened
    eleven times before anything could see it.

``height``
    the median the campaign draws that tile at, from
    ``knowledge/blood/design/sprite-heights-v1.json``. Not a number the author
    invents: four trees authored at "about three times a person" came out at 2.8
    to 3.4 player heights against Blood's own 7.2 to 8.5, and read as saplings.

``habitat``
    dry land, under water, or either. 664 appears in 82 campaign sectors and
    every single one is under water; 660 in 142, likewise. Both were being used
    across this level as creepers and pot plants.

Sprites are drawn square: 16,746 of the campaign's 18,858 use ``x_repeat ==
y_repeat``, and the ratio's q1, median and q3 are all exactly 1.00. The tile's
own pixels carry its shape, so scaling the two axes differently squashes it
twice. Only a fence leaf overrides that, and only because it is sized to the
opening it has to fill.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .player_space import PLAYER_PROFILES

#: One standing human, from the player profile. Never hardcode this: it was
#: 0x1600 in a dozen modules, which is `POSTURE.eyeAboveZ` -- an offset from
#: the sprite's centre, not a body -- and every height in the project was
#: denominated in a unit 3x too small.
PLAYER_HEIGHT = PLAYER_PROFILES["blood"].standing_height

#: cstat 0x30: 0x00 faces the viewer, 0x10 lies along a wall, 0x20 lies flat.
ALIGNMENT_MASK = 0x30
FACING, WALL_ALIGNED, FLOOR_ALIGNED = 0x00, 0x10, 0x20

_HEIGHTS_FILE = (Path(__file__).resolve().parent.parent
                 / "knowledge" / "blood" / "design" / "sprite-heights-v1.json")


class FurnitureError(ValueError):
    """A thing described in a way Blood would draw wrongly."""


def campaign_heights() -> dict[int, float]:
    """Median drawn height per tile, in player heights."""
    try:
        raw = json.loads(_HEIGHTS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {int(k): float(v["median"]) for k, v in raw.get("tiles", {}).items()}


_HEIGHTS = campaign_heights()


@dataclass(frozen=True)
class Furniture:
    """One nameable thing, with its mounting and its size settled."""

    name: str
    picnum: int
    cstat: int
    mounting: str                  # "wall", "floor", "ceiling" or "free"
    habitat: str = "any"           # "dry", "wet" or "any"
    shade: int = -8
    aspect: float = 1.0
    height: float | None = None    # overrides the campaign median
    note: str = ""

    def __post_init__(self) -> None:
        if self.mounting == "wall" and self.cstat & ALIGNMENT_MASK == FLOOR_ALIGNED:
            raise FurnitureError(
                f"{self.name}: tile {self.picnum} is floor-aligned (cstat "
                f"{self.cstat}) and cannot hang on a wall")
        if self.mounting not in ("wall", "floor", "ceiling", "free"):
            raise FurnitureError(f"{self.name}: unknown mounting {self.mounting!r}")
        if self.habitat not in ("dry", "wet", "any"):
            raise FurnitureError(f"{self.name}: unknown habitat {self.habitat!r}")

    def player_heights(self) -> float:
        if self.height is not None:
            return self.height
        found = _HEIGHTS.get(self.picnum)
        if found is None:
            raise FurnitureError(
                f"{self.name}: tile {self.picnum} has no campaign height and none "
                "was given; run tools.mine_sprite_heights or state one")
        return found

    def repeats(self, tile_height: int) -> dict[str, int]:
        y = max(4, min(255, round(self.player_heights() * PLAYER_HEIGHT
                                  / (tile_height * 4))))
        return {"y_repeat": y, "x_repeat": max(4, min(255, round(y * self.aspect)))}


FURNITURE: dict[str, Furniture] = {}


def _define(item: Furniture) -> Furniture:
    FURNITURE[item.name] = item
    return item


def furnish(name: str, art_sizes: dict[int, tuple[int, int]] | None = None,
            **overrides: Any) -> dict[str, Any]:
    """Sprite keyword arguments for a named thing."""
    try:
        item = FURNITURE[name]
    except KeyError:
        raise FurnitureError(
            f"nothing named {name!r}; known: {', '.join(sorted(FURNITURE))}"
        ) from None
    out: dict[str, Any] = {
        "type": 0, "picnum": item.picnum, "cstat": item.cstat, "shade": item.shade,
    }
    if art_sizes and item.picnum in art_sizes:
        out.update(item.repeats(int(art_sizes[item.picnum][1])))
    out.update(overrides)
    return out


def wet_only() -> set[int]:
    """Tiles that belong under water and nowhere else."""
    return {f.picnum for f in FURNITURE.values() if f.habitat == "wet"}


def dry_only() -> set[int]:
    return {f.picnum for f in FURNITURE.values() if f.habitat == "dry"}


# -- light -----------------------------------------------------------------
_define(Furniture("torch", 506, FACING | 128, "wall", shade=-128,
                  note="drawn fullbright in 89% of its 150 uses: it is on fire"))
_define(Furniture("chandelier", 1701, FACING | 128 | 256, "ceiling", shade=-128))
_define(Furniture("lantern", 641, FACING | 128, "ceiling", shade=-128,
                  note="a chain with a lit lamp on it; casts light but does not "
                       "gutter -- 3% of its sectors animate against a torch's 63%"))
_define(Furniture("sconce", 510, WALL_ALIGNED | 128 | 64, "wall",
                  note="a bracket, not a flame: only 25% are drawn bright"))

# -- masonry and fittings ---------------------------------------------------
_define(Furniture("plaque", 915, WALL_ALIGNED | 128 | 64, "wall"))
_define(Furniture("plank", 68, FACING | 128 | 64 | 256, "wall"))
_define(Furniture("grille", 1044, 1 | 4 | 8 | 128 | 256, "floor", aspect=0.73,
                  note="the one thing here that is not drawn square, because a "
                       "fence leaf is sized to the opening it fills"))
_define(Furniture("ceiling_plate", 795, FLOOR_ALIGNED | 128 | 64 | 8, "ceiling",
                  note="floor-aligned: a flat plate, which lies on a surface and "
                       "cannot hang on a wall"))

# -- growing things ---------------------------------------------------------
_define(Furniture("bush", 599, 1 | 128 | 256, "floor", habitat="dry", shade=6))
_define(Furniture("oak", 541, 1 | 128 | 256, "floor", habitat="dry", shade=10))
_define(Furniture("elm", 542, 1 | 128 | 256, "floor", habitat="dry", shade=10))
_define(Furniture("deadwood", 543, 1 | 128 | 256, "floor", habitat="dry", shade=10))
_define(Furniture("pine", 547, 1 | 128 | 256, "floor", habitat="dry", shade=10))

# -- under water ------------------------------------------------------------
_define(Furniture("bubbles", 668, FACING | 128, "floor", habitat="wet", shade=-24,
                  note="a rising column; 41 uses, every one of them submerged"))
_define(Furniture("seaweed", 546, 1 | 128 | 256, "floor", habitat="wet", shade=10))
_define(Furniture("waterweed", 660, FACING | 128, "floor", habitat="wet", shade=10,
                  note="142 campaign sectors, all of them under water"))
_define(Furniture("kelp", 664, FACING | 128, "floor", habitat="wet", shade=10,
                  note="82 campaign sectors, all of them under water"))

# -- the graveyard ----------------------------------------------------------
_define(Furniture("headstone_rip", 701, 1 | 128 | 256, "floor", habitat="dry", shade=8))
_define(Furniture("headstone_cross", 703, 1 | 128 | 256, "floor", habitat="dry", shade=8))
_define(Furniture("headstone_flame", 704, 1 | 128 | 256, "floor", habitat="dry", shade=8))
_define(Furniture("tomb", 706, 1 | 128 | 256, "floor", habitat="dry", shade=8))

# -- the garden -------------------------------------------------------------
_define(Furniture("statue", 536, 1 | 128 | 256, "floor", habitat="dry", shade=4))
_define(Furniture("urn", 537, 1 | 128 | 256, "floor", shade=8))
