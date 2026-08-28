"""E3M3's sewer, as constructors.

Gravesend's sewer is correct and bare: a ring of near-identical turns, which
is the most repetitive space in the city and therefore the one where
parametric detail pays most. E3M3 is the campaign's own sewer -- 309
sectors, 2,227 walls, 519 sprites -- and everything below is measured off
it.

**The register was already right.** `materials.SEWER` is wall 492, floor
568, ceiling 255, water 1120, and E3M3's own commonest are wall 492 (460
walls), floor 568 (115 sectors), ceiling 255 (222), water 1120 (78). What
Gravesend lacked is not the palette but the things built out of it.

**The mouth.** Tile **194** is the circular tunnel lining, and E3M3 uses it
in one specific place: 29 of its 76 uses are on **two-sided walls** -- the
opening where one channel meets another -- and 47 on the solid wall around
them. It is not a general wall tile; it is what a channel mouth is made of.

**The ledge.** rise 4096 on tile 568, depth **512**, at (512x2048) seven
times and (512x2304) three times: the towpath that carries the player along
the channel. Length free, depth and rise pinned -- already a family.

**What hangs in a tunnel**, with E3M3's own heights in player heights:

| tile | what | alignment | height |
|---|---|---|---|
| 54 | dripping water | wall | 1.21 |
| 793 | hanging moss | wall | 0.97 |
| 191 | drain grate | floor-aligned | 1.99 |
| 795 | round grate | floor-aligned | 1.93 |
| 668 | bubbles | face | 0.00 |
| 660 | kelp | face | 0.00 |
| 546 | reeds | face | 0.00 |
| 515 | debris | floor-aligned | 1.81 |

Two of those disagree with the corpus-wide catalogue and E3M3 wins here,
because this is E3M3's register: 793 hangs at 0.97 where the catalogue's
median across 13 maps is 2.72, and 191 sits at 1.99 against 1.87.

Nothing in this module places anything by itself. It is families, element
tables and one wall treatment, for `runs.py` and `fixtures.py` to emit.
"""

from __future__ import annotations

from runs import Element

#: The circular tunnel lining. E3M3: 29 two-sided walls, 47 solid.
MOUTH_TILE = 194

#: E3M3's other masonry, in the order it uses them: 492 is the field wall
#: (460), 487 the rusted streak (148), 488 and 486 the block variants.
BLOCK, STREAK, BLOCK_B, BLOCK_C = 492, 487, 488, 486


class SewerKitError(ValueError):
    """A sewer piece this kit will not build."""


#: What runs along a tunnel WALL. Both wall-aligned in E3M3 and in the
#: catalogue, so a run may hang them without argument.
TUNNEL_WALL = (
    Element(54, note="dripping water, E3M3 x9 at 1.21 player heights"),
    Element(793, note="hanging moss, E3M3 x4 at 0.97 -- lower than the "
                      "corpus median of 2.72, because this is a tunnel"),
)

#: What a vault carries overhead. Floor-aligned, so they lie flat against
#: the ceiling rather than facing the player.
VAULT = (
    Element(191, note="drain grate, E3M3 x18 at 1.99 -- and one of the "
                      "campaign's walkable floor-sprite decks, so it is a "
                      "surface as well as a detail"),
    Element(795, note="round grate, E3M3 x15 at 1.93"),
)

#: What stands in the water. Face sprites at the floor, all three of them.
WATERLINE = (
    Element(668, note="bubbles, E3M3 x22 at the floor"),
    Element(660, note="kelp, E3M3 x12"),
    Element(546, note="reeds, E3M3 x9"),
)

#: What settles out of it.
SILT = (
    Element(515, note="debris, E3M3 x23, floor-aligned"),
)

#: Every element above, for a run that wants the whole register.
TUNNEL = TUNNEL_WALL + VAULT + SILT

ELEMENTS = {"wall": TUNNEL_WALL, "vault": VAULT, "water": WATERLINE,
            "silt": SILT, "tunnel": TUNNEL}


def elements_for(kind: str):
    if kind not in ELEMENTS:
        raise SewerKitError(
            f"no sewer element set named {kind!r}; known: "
            f"{', '.join(sorted(ELEMENTS))}")
    return ELEMENTS[kind]


def cost(kind: str, beats: int) -> dict:
    """Declared before emission. Every element here is a sprite, not a wall."""
    return {"set": kind, "sprites": int(beats), "walls": 0,
            "source": "E3M3, the campaign's own sewer"}


#: A mouth is SHORT and has a band above it.  E3M3 wears 194 on 29 of its
#: 1,128 two-sided walls -- 2.6% -- and those 29 have a median length of
#: **201 units** against 1,024 for the rest, with ceiling steps of 65,536 to
#: 98,304 above them.  Lining every shared edge would be lining the network.
MOUTH_MAX_LENGTH = 1024
MOUTH_MIN_BAND = 8192

#: A gap between consecutive ledge modules.  It would be nicer at zero -- a
#: towpath is continuous -- but a run cannot declare portals between its own
#: modules (grammar request #14: a run node sits under a room, and
#: `all_connections` does not walk past a room), so abutting carves come out
#: as coincident same-direction segments and the compiler refuses them.
#: 256 units is a step across, not a gap to fall down.
LEDGE_GAP = 256


def line_mouths(level, sectors, *, tile: int = MOUTH_TILE,
                max_length: int = MOUTH_MAX_LENGTH,
                min_band: int = MOUTH_MIN_BAND) -> dict:
    """Line the openings between two sewer sectors with the tunnel tile.

    Only the ones that are mouths: short, with a real band of wall above
    them.  `sectors` is the set of sector ids the sewer occupies, so a
    mouth onto a stack link or the street keeps its own treatment.
    """
    import math

    report = {"lined": 0, "too_long": 0, "no_band": 0, "outside": 0,
              "tile": int(tile)}
    inside = {int(s) for s in sectors}

    def fields_of(record):
        return record["fields"] if isinstance(record, dict) else record

    for index, sector in enumerate(level.sectors):
        sector_fields = fields_of(sector)
        if index not in inside:
            continue
        start = int(sector_fields["wall_ptr"])
        for offset in range(int(sector_fields["wall_count"])):
            wall = fields_of(level.walls[start + offset])
            neighbour = int(wall["next_sector"])
            if neighbour < 0:
                continue
            if neighbour not in inside:
                report["outside"] += 1
                continue
            other = fields_of(level.sectors[neighbour])
            far = fields_of(level.walls[int(wall["point2"])])
            length = math.hypot(far["x"] - wall["x"], far["y"] - wall["y"])
            if length > max_length:
                report["too_long"] += 1
                continue
            band = max(abs(int(other["ceiling_z"]) - int(sector_fields["ceiling_z"])),
                       abs(int(other["floor_z"]) - int(sector_fields["floor_z"])))
            if band < min_band:
                report["no_band"] += 1
                continue
            wall["picnum"] = int(tile)
            report["lined"] += 1
    return report


def ledge_along(host, name: str, *, axis: str, start: int, end: int,
                across0: int, across1: int, material, grade: int,
                host_clear: int, connector=None):
    """The towpath: E3M3's own ledge family, at whatever length it is given.

    `fixtures.run_along` does the emitting; this names the family and the
    provenance so a caller does not have to know either.
    """
    import fixtures
    return fixtures.run_along(
        name, host, axis=axis, start=start, end=end,
        across0=across0, across1=across1, family="ledge",
        material=material, grade=grade, host_clear=host_clear,
        gap=LEDGE_GAP, connector=connector)
