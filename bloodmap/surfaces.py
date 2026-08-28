"""What a surface is made of, named rather than numbered.

The name is deliberately `surfaces` and not `materials`: `bloodmap.materials`
already exists and does something else entirely -- it mines Blood's ART and
forms unlabelled clusters from measured appearance. This is the small, hand-held
vocabulary a level authors in.

A level should be able to say that a room is a cloister and have the tiles
follow. This project's could not: every region named three raw picnums, every
decoration named a picnum and a cstat bitfield, and every one of those numbers
was a fact about Blood's ART that the author had to carry in their head and that
nothing could check.

The numbers do not go away -- Build renders picnums -- but they stop being the
representation. A material here carries:

``wall`` / ``floor`` / ``ceiling``
    the three surfaces.

``opening``
    the tile this material dresses its own doorways in. Blood does not paint a
    room in one material: of the 8,320 campaign rooms that use more than one wall
    tile, 74% put a different tile on their two-sided walls than on their solid
    ones -- ashlar at the jambs, rubble in the spans. That is a property of the
    material, not a decision per room, so it lives here.

``sky``
    whether the ceiling is the sky. Not a separate flag an author can forget:
    three of this level's doorways inherited a neighbour's 64x400 sky panel
    without it and had it drawn as an ordinary ceiling, where Build samples it as
    64x256 and never draws the rest.

Two engine rules are checked when this module is imported, so a material that
breaks them cannot reach a map:

* a non-sky floor or ceiling tile must have **power-of-two sides**, because
  `tileUpdatePicSiz` rounds each dimension down to one and the floor rasteriser
  masks with the result. The campaign obeys this on 99.97% of its 26,383
  non-parallax surfaces.
* a sky ceiling must name the **first of sixteen** panels, because a parallax
  ceiling's picnum is the base of a run and Blood's own maps always start one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: The first panel of the night sky. A parallax ceiling names the first of
#: sixteen, and the run beginning at 504 -- which this project used for a year --
#: is not sky at all: it contains torches and trim, tiles that are 10 to 89%
#: transparent, which the renderer paints as raw magenta.
SKY_PANEL = 2500


class SurfaceError(ValueError):
    """A material that Build would draw wrongly."""


def _power_of_two(value: int) -> bool:
    return value > 0 and (value & (value - 1)) == 0


@dataclass(frozen=True)
class Material:
    """One coherent set of surfaces, named for what it is."""

    name: str
    wall: int
    floor: int
    ceiling: int
    opening: int | None = None
    sky: bool = False
    note: str = ""

    def region(self, **overrides: Any) -> dict[str, Any]:
        """Keyword arguments for `PlanarLayout.add_region`."""
        out: dict[str, Any] = {
            "wall_picnum": self.wall,
            "floor_picnum": self.floor,
            "ceiling_picnum": SKY_PANEL if self.sky else self.ceiling,
            "parallax_ceiling": self.sky,
        }
        if self.opening is not None:
            out["portal_wall_picnum"] = self.opening
        out.update(overrides)
        return out


#: The monastery's materials.
#:
#: The ``opening`` tiles are the campaign's own pairings, taken from which tiles
#: actually share a room with which: 91 with 90 in 25% of the rooms 91 appears
#: in, 180 with 110 in 38%, 427 with 556 in 21%. 110 goes with 5 -- attested in
#: both directions, and right for the building besides, since 110 is rubble and 5
#: is dressed ashlar, which is what holds an opening up.
MATERIALS: dict[str, Material] = {}


#: Every flat surface any material declares, for `check` to hold to the
#: power-of-two rule once somebody supplies the ART.
_FLAT: list[tuple[str, str, int]] = []


def _define(material: Material) -> Material:
    for surface in ("floor", "ceiling"):
        if surface == "ceiling" and material.sky:
            continue                    # the sky is not sampled as a surface
        _FLAT.append((material.name, surface, getattr(material, surface)))
    MATERIALS[material.name] = material
    return material


def check(art_sizes: dict[int, tuple[int, int]]) -> list[str]:
    """Every material's flat tiles, against Build's power-of-two rule.

    Returns the complaints rather than raising, so a caller without the game's
    ART can carry on and a caller with it can fail loudly.
    """
    out = []
    for name, surface, tile in _FLAT:
        size = art_sizes.get(tile)
        if size is None:
            continue
        width, height = int(size[0]), int(size[1])
        if not (_power_of_two(width) and _power_of_two(height)):
            out.append(
                f"material {name!r}: {surface} tile {tile} is {width}x{height}, "
                "which Build cannot sample on a flat surface")
    return out


def material(name: str, **overrides: Any) -> dict[str, Any]:
    """Region keyword arguments for a named material."""
    try:
        found = MATERIALS[name]
    except KeyError:
        raise SurfaceError(
            f"no material named {name!r}; known: {', '.join(sorted(MATERIALS))}"
        ) from None
    return found.region(**overrides)


# -- outside ---------------------------------------------------------------
_define(Material("approach", wall=427, floor=270, ceiling=285, opening=556,
                 note="the dressed way up to the gate"))
_define(Material("courtyard", wall=110, floor=2448, ceiling=0, opening=5, sky=True,
                 note="rubble walls round an open court"))
_define(Material("garth", wall=110, floor=270, ceiling=0, opening=5, sky=True,
                 note="the open square inside the cloister"))
_define(Material("planting", wall=110, floor=270, ceiling=0, opening=5, sky=True,
                 note="a raised bed; earth rather than paving"))

# -- the church ------------------------------------------------------------
_define(Material("nave", wall=5, floor=294, ceiling=454,
                 note="dressed ashlar, the best masonry in the building"))
_define(Material("aisle", wall=80, floor=294, ceiling=285,
                 note="darker stone flanking the nave"))
_define(Material("sanctuary", wall=5, floor=44, ceiling=4,
                 note="the chancel and apse, floored differently from the nave"))

# -- below -----------------------------------------------------------------
_define(Material("crypt", wall=194, floor=568, ceiling=67, opening=80,
                 note="the vaulted hall under the church"))
_define(Material("crypt_stair", wall=194, floor=568, ceiling=255, opening=80))
_define(Material("charnel", wall=1097, floor=1097, ceiling=255,
                 note="bone, walls and floor alike"))
_define(Material("vault", wall=194, floor=255, ceiling=255, opening=80,
                 note="a plain chamber off the crypt"))
_define(Material("sludge", wall=194, floor=1120, ceiling=255, opening=80,
                 note="a floor that hurts and drifts, and looks like it"))
_define(Material("plinth", wall=194, floor=452, ceiling=67))
_define(Material("flooded", wall=449, floor=358, ceiling=67,
                 note="the drowned run under the well"))
#: The two flooded shafts look *up* at the underside of the pool they hang from,
#: so their ceiling is the water surface rather than rock. 2915 is nine frames of
#: rippling blue and is 64x64, so it is legal on a flat surface.
#: A well head or a pool mouth, looked at from above: the floor you see is the
#: water surface you dive through, so it wears the water tile.
_define(Material("well_head", wall=449, floor=2915, ceiling=67,
                 note="the surface you dive through, seen from the dry side"))
_define(Material("flooded_shaft", wall=449, floor=358, ceiling=2915,
                 note="under a pool: the ceiling is the surface you came through"))

# -- the water garden -------------------------------------------------------
_define(Material("lawn", wall=110, floor=270, ceiling=0, opening=5, sky=True,
                 note="the sunken garden; the same ground as the garth"))
_define(Material("hedge", wall=568, floor=568, ceiling=0, sky=True,
                 note="a planter too tall to step onto, grown over"))
_define(Material("paving", wall=538, floor=538, ceiling=0, sky=True,
                 note="dressed cobbles: the shrine steps and the garden stair"))
_define(Material("porch", wall=110, floor=538, ceiling=416, opening=5,
                 note="roofed, cobbled, open at one end"))
_define(Material("rubble", wall=110, floor=110, ceiling=0, sky=True,
                 note="fallen masonry, wearing the wall it fell out of"))
#: The same stone, roofed. A gap through a thick wall joins two open spaces whose
#: skies are at different heights, and an open ceiling there draws the difference
#: as a band of wall hanging in the air: 94% of the campaign's adjacent
#: open-to-open sector pairs hold their sky at an identical z. Roofing the gap is
#: the division that lets the two skies differ -- and a breach with masonry still
#: standing over it is what a collapsed wall looks like anyway.
_define(Material("rubble_roofed", wall=110, floor=110, ceiling=110,
                 note="a gap through a wall, with the wall still above it"))
_define(Material("basin", wall=568, floor=2915, ceiling=0, sky=True,
                 note="standing water under the open sky"))
_define(Material("grotto", wall=568, floor=568, ceiling=568,
                 note="cut into rock, roofed by the rock above it"))

# -- the ranges ------------------------------------------------------------
_define(Material("cloister", wall=110, floor=2448, ceiling=285, opening=5,
                 note="the covered walk round the garth"))
_define(Material("arch", wall=427, floor=2448, ceiling=285, opening=556,
                 note="a threshold, dressed like the approach"))
_define(Material("gallery", wall=91, floor=44, ceiling=455, opening=90,
                 note="brick, which nothing else in the level is"))
_define(Material("undercroft", wall=194, floor=290, ceiling=296, opening=80))
_define(Material("tower", wall=91, floor=568, ceiling=255, opening=90,
                 note="the bell tower stair and belfry"))
