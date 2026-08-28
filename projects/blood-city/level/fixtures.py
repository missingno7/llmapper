"""The fixture kit: shop and street detail as parametric constructors.

Every venue in Gravesend has been hand-built, which is why the pawn shop
renders as an empty box: the shop grammar was documented in
`references/venue-patterns.md` and written down exactly once, inline, in
the canteen. This is that grammar as code, so every venue composes from the
same parts.

**Fixtures come in families, not sizes.** `knowledge/blood/design/fixtures-v1.json`
mines the four detail sources and the families are unmistakable. DWE3M10
builds one counter eight times at **rise 3072, tile 345, depth 1024** and
two widths, 512 and 1024 -- rise, tile and depth pinned, **width free**.
DWE3M1 builds a panel run fourteen times at **rise 21504, tile 1666**. So a
constructor here takes a length and pins the rest, rather than existing in
eight hand-placed copies.

**Goods are an accent, not a rule.** The median fixture in all four sources
carries **zero** sprites -- 143 of DWE3M1's 171 are bare, 41 of E6M1's 43.
Putting merchandise on every pedestal would be wrong, and was the plan
before this was measured. `GOODS_SHARE` is that measurement.

**A shutter and a window are the same wall.** DWE3M10 draws tile 1060 as
the `over_picnum` of a two-sided masked wall ten times; all four sources
draw glass (266) the same way. So closing a shopfront and glazing one are
one constructor with a different tile -- which is how a city shows more
units than it furnishes.

**Elements attested in BOTH Death Wish maps** are preferred over one map's
whim: 624 (globe), 640 (lamp), 660 (kelp), 795 (porthole), 1060 (shutter).
795 is the signature element the city lacks -- 124 uses in DWE3M10 alone.

Provenance is recorded per constructor so its output can be rendered
against its own precedent under identical conditions.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from bloodmap.levelprog import Frame, RECT_FACES, Style

import setpieces
from materials import INTERIORS

COMPASS = dict(zip(RECT_FACES, range(4)))
PLAN = 1024
PLAYER = 16960


@dataclass(frozen=True)
class Family:
    """A fixture family: what is pinned, what is free, and where it is from."""
    name: str
    rise: int
    tile: int
    depth: int                  # pinned across the family
    widths: tuple               # the attested free dimension
    source: str                 # map plus sector list
    walls: int = 8              # carve + fill, both loops

    def clamp(self, width: int) -> int:
        """A length inside the family's attested range, snapped to its grid."""
        lo, hi = min(self.widths), max(self.widths)
        step = min(self.widths)
        width = max(lo, min(hi * 4, int(width)))
        return max(lo, (width // step) * step)


#: DWE3M10 sectors 8 of one family: rise 3072, tile 345, depth 1024, widths
#: 512 and 1024. The canonical parametric fixture in the whole source set.
COUNTER = Family("counter", rise=3072, tile=345, depth=1024,
                 widths=(512, 1024),
                 source="DWE3M10 rise-3072/tile-345 family, 8 occurrences")

#: E6M1's display module: 512 square at rise 2048.
PEDESTAL = Family("pedestal", rise=2048, tile=452, depth=512,
                  widths=(512,),
                  source="E6M1 512x512 rise-2048 family, 4 occurrences")

#: DWE3M1's panel run: rise 21504 on tile 1666, fourteen occurrences, built
#: at 256 wide and at lengths from 1536 to 3584. Length is the free one.
PANEL = Family("panel", rise=21504, tile=1666, depth=256,
               widths=(256, 512, 1024, 2048),
               source="DWE3M1 rise-21504/tile-1666 family, 14 occurrences")

FAMILIES = {f.name: f for f in (COUNTER, PEDESTAL, PANEL)}

#: The share of fixtures that carry any merchandise at all. Measured across
#: the four sources: 28/171, 11/136, 2/43, 1/62 -- call it one in seven.
GOODS_SHARE = 0.14

#: Glazing and closing are the same masked two-sided wall.
GLASS_TILE = 266
SHUTTER_TILE = 1060
GRILLE_TILE = 1044

#: The signature element the city has none of.  Attested in both Death Wish
#: maps -- but NOT in the same form, which is worth stating rather than
#: averaging: DWE3M10 mounts it 125 times floor-aligned at **+3.38 player
#: heights**, cstat 160, repeats 32x32, shade **-30** -- a lit porthole in
#: the ceiling; DWE3M1 mounts its 16 wall-aligned at +0.12, cstat 208,
#: shade 0.  One tile, two conventions.  Gravesend takes the pier form,
#: because 125 repetitions of one element is what makes a place read as one
#: place and that is the property the city is missing.
PORTHOLE = 795
PORTHOLE_FIELDS = {
    "type": 0, "picnum": 795, "cstat": 160, "shade": -30,
    "x_repeat": 32, "y_repeat": 32, "status": 0,
}
PORTHOLE_HEIGHT = 3.38          # player heights, DWE3M10's own median


def signature(layout, placement_id: str, region_id: str, local=(0.5, 0.5)):
    """One porthole, at the height and shade DWE3M10 gives all 125 of its.

    It hangs at 3.38 player heights, well over anything standing on the
    floor -- but a sprite is still assigned to a sector by its XY, so a
    porthole over the middle of a furnished room is a porthole over a hole
    in that room.  Ask where the floor is before hanging it.
    """
    import props
    region = layout.regions.get(region_id)
    if region is not None:
        local = props.free_local(region, local)
        if local is None:
            return None
    return layout.place_on_floor(
        placement_id, region_id, local=local,
        height_player_heights=PORTHOLE_HEIGHT, **PORTHOLE_FIELDS)

#: Street furniture, all attested in both Death Wish maps.
STREET_KIT = {"lamp": 640, "globe": 624, "porthole": 795, "kelp": 660}
#: Attested in DWE3M10 only; use where the waterfront register is wanted.
WATERFRONT_KIT = {"news": 743, "notice": 742, "chain": 694, "rope": 754,
                  "shrub": 599}


class FixtureError(ValueError):
    """A fixture the kit will not build, naming the fix."""


def _roll(seed: str, n: int) -> int:
    """Stable choice: the same fixture rebuilds identically."""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % max(1, n)


def cost(family: str, count: int) -> dict:
    """Declared before anything is emitted, so a planner can budget."""
    fam = FAMILIES[family]
    return {"family": family, "count": count, "walls": fam.walls * count,
            "source": fam.source}


def place(name, host, rect, material, *, family: str, grade: int,
          host_clear: int, connector=None, into=None):
    """One fixture of a family: length from `rect`, everything else pinned.

    The rise, the tile and the depth are the family's, not the caller's --
    that is what makes eight of these read as one thing repeated rather
    than eight unrelated blocks.

    The piece lands **in** its host, not beside it: `host.children` is how
    "what is in this bar" gets an answer.  `into` overrides the parent for
    a fixture that belongs to a run rather than straight to the room.
    """
    fam = FAMILIES[family]
    x0, y0, x1, y1 = (int(v) for v in rect)
    if x1 <= x0 or y1 <= y0:
        raise FixtureError(f"{name}: {rect} has no extent")
    piece = setpieces.raised_solid(
        into if into is not None else host,
        name, host, (x0, y0, x1, y1), material,
        grade=grade, rise=fam.rise, host_clear=host_clear,
        connector=connector,
        note=f"{family} ({fam.source})")
    # The family pins the TILE as well as the rise and the depth.  Without
    # it the fixture inherits its room's floor and eight of these read as
    # eight blocks rather than as one thing repeated, which is the whole
    # reason the family is a family.
    piece.surfaces(floor_picnum=fam.tile, floor_z=grade - fam.rise,
                   clear_height=host_clear - fam.rise)
    return piece


def run_along(name, host, *, axis: str, start: int, end: int,
              across0: int, across1: int, family: str, material,
              grade: int, host_clear: int, gap: int = 512,
              connector=None):
    """A shelf or counter run: modules at the family's own widths.

    The run prefab shape -- given a length, emit modules at campaign
    spacing -- with the module's width taken from the family and varied
    deterministically between its attested sizes.

    **The run is a node, not a list.**  It owns its modules, so a reader
    standing on the bar sees one counter run rather than six loose blocks,
    and a template that places a run can hand that node back to its own
    parent.  `.children` are the modules; the return value is the node.
    """
    import citytree
    fam = FAMILIES[family]
    span = end - start
    if span <= 0:
        raise FixtureError(f"{name}: run from {start} to {end} has no length")
    node = citytree.sub(host, name, note=f"{family} run: {fam.source}")
    cursor, index = start, 0
    while cursor < end:
        width = fam.widths[_roll(f"{name}:{index}", len(fam.widths))]
        if cursor + width > end:
            width = end - cursor
        if width < min(fam.widths):
            break
        rect = ((cursor, across0, cursor + width, across1) if axis == "x"
                else (across0, cursor, across1, cursor + width))
        place(f"{name}_{index}", host, rect, material, into=node,
              family=family, grade=grade, host_clear=host_clear,
              connector=connector)
        cursor += width + gap
        index += 1
    return node


def goods_on(index: int, name: str) -> bool:
    """Whether this fixture carries merchandise. Usually it does not.

    Median goods per fixture is zero in every source; one in seven carries
    anything. Deterministic, so the same shop rebuilds identically.
    """
    return _roll(f"{name}:goods:{index}", 100) < int(GOODS_SHARE * 100)


def close_front(level, spans, *, tile: int = SHUTTER_TILE) -> dict:
    """Shutter a shopfront: the same masked wall glass uses, different tile.

    `glass.glaze` already emits the construction; this names the other
    tile it takes, which is what lets a city show more units than it
    furnishes.
    """
    import glass
    return glass.glaze(level, spans, tile=tile)
