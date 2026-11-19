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

#: E1M4's fairground kit.  Dark Carnival is built out of three repeated
#: small sectors and nothing else: a booth counter, a low ride platform and
#: a row of stanchions.  All three are already parametric in the map --
#: rise and tile pinned, length free -- which is why they belong here rather
#: than in a project module.
BOOTH = Family("booth", rise=16384, tile=452, depth=512,
               widths=(512, 1024),
               source="E1M4 rise-16384/tile-452 family, 9 occurrences")

STAGE = Family("stage", rise=4096, tile=438, depth=2048,
               widths=(2048, 3584),
               source="E1M4 rise-4096/tile-438 family, 9 occurrences")

STANCHION = Family("stanchion", rise=11264, tile=41, depth=512,
                   widths=(512,),
                   source="E1M4 rise-11264/tile-41 family, 6 occurrences")

#: E3M3's towpath: the ledge that carries the player along the channel.
#: rise 4096 on tile 568, depth pinned at 512, built at 2048 seven times and
#: 2304 three times -- length free, like every family here.
LEDGE = Family("ledge", rise=4096, tile=568, depth=512,
               widths=(2048, 2304),
               source="E3M3 rise-4096/tile-568 family, 10 occurrences")

#: What Blood's towns stand their goods on. `tools/mine_stands.py` over
#: seven town maps: the 91 fixtures that carry a standing thing (25 islands,
#: 33 ledges, 33 niches) rise a median 0.48 body over the floor beside them
#: -- 8,192 is 0.483 -- and 35 of them are topped with tile 34, the owner's
#: "wood, usable e.g. for counter/cabinet sides"; the commonest riser on an
#: island or a ledge is 28, the owner's "wooden wall". COUNTER above is not
#: wrong, it is low: a 0.18-body block reads as a bench ("bench-like
#: blocks", a blind reviewer, 2026-11-18), and nothing in the town maps
#: keeps a bottle on one.
BAR = Family("bar", rise=8192, tile=34, depth=768,
             widths=(1024, 2048),
             source="seven town maps, 91 thing-carrying fixtures: median "
                    "rise 0.48 body, top 34 (tools/mine_stands.py)")
BAR_FACE = 28

FAMILIES = {f.name: f for f in (COUNTER, PEDESTAL, PANEL,
                                BOOTH, STAGE, STANCHION, LEDGE, BAR)}

#: A shelf let into a wall: E1M2 sector 213, E3M2 82 and 87, E1M4 167
#: (`references/town-fixtures.png`). Its floor is a bar's height; its head
#: is 0.725 body over that (E1M2 213's own 12,288), which leaves the wall
#: over it for the shop's name; a quarter to half a player width deep.
SHELF_RISE = BAR.rise
SHELF_CLEAR = 12288
SHELF_DEPTH = 384
#: Its back and cheeks: the owner's "wood" (20), the niche back of two of
#: the mined ones. The shelf itself is 34.
SHELF_BACK = 20
SHELF_INTENT = "shelf_niche"
#: A trade whose stock is a WALL in Blood: the owner's "bookcase front"
#: (31, 32, 33). There is no book sprite in the town maps; books are a
#: surface.
SHELF_BACKS = {"books": 32}

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
          host_clear: int, connector=None, into=None, wall_picnum: int | None = None):
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
        face_picnum=wall_picnum if wall_picnum is not None else material.wall,
        note=f"{family} ({fam.source})")
    # The family pins the TILE as well as the rise and the depth.  Without
    # it the fixture inherits its room's floor and eight of these read as
    # eight blocks rather than as one thing repeated, which is the whole
    # reason the family is a family.
    style = {"floor_picnum": fam.tile, "floor_z": grade - fam.rise,
             "clear_height": host_clear - fam.rise}
    if wall_picnum is not None:
        style["wall_picnum"] = int(wall_picnum)
    piece.surfaces(**style)
    # A fixture is carved into its host and all four edges are real portals.
    # Build therefore reads the *portal* wall for the visible riser, not the
    # sector's field wall.  Keep the requested family tile on that riser too;
    # otherwise a crate/shelf has its own top but inherits the shop doorway
    # tile on every side (the old sector-157 half-crate symptom).
    piece.region_kwargs["portal_wall_picnum"] = int(
        wall_picnum if wall_picnum is not None else material.wall)
    return piece


def shelf_niche(room, name: str, face: str, *, width: int, at: float = 0.5,
                depth: int = SHELF_DEPTH, rise: int = SHELF_RISE,
                clear: int = SHELF_CLEAR, sells: str = ""):
    # (the back of a bookseller's shelf is the owner's "bookcase front")
    """A shelf let into one face of a room, for a row of stock.

    Not a block on the floor: the room keeps its floor and the wall keeps
    its plane, which is what the town maps do with a wall that has nothing
    behind it. The caller must know the wall has `depth` of void behind
    that stretch; the compiler refuses the level if it has not.

    The riser under the shelf and the band over its head are the ROOM's
    wall, drawn by the room's own record, so the room's material runs on
    past the shelf unbroken.
    """
    if width < 1024:
        raise FixtureError(f"{name}: a {width}-unit shelf holds no row")
    return room.recess(
        f"{name}", face, at=at, width=int(width), depth=int(depth),
        floor_delta=-int(rise), clear_height=int(clear),
        floor_picnum=BAR.tile, ceiling_picnum=BAR.tile,
        wall_picnum=SHELF_BACKS.get(sells, SHELF_BACK),
        intent={"kind": SHELF_INTENT, "sells": sells,
                "source": "E1M2 s213, E3M2 s82/s87 (tools/mine_stands.py)"})


#: tiles that are a PICTURE of a thing (a bookcase front) and must be shown
#: whole, against plain boards that only need an origin
SHELF_PICTURES = {31, 32, 33}


def frame_shelves(level, compiled, layout, art_sizes) -> dict:
    """Give every shelf niche's walls an origin and a scale of their own.

    The owner, 2026-11-18: "In the shops shelves aren't sometimes aligned
    with textures." A niche's back wore its tile wherever the room's run
    happened to leave the panning: the ironmonger's boards began 24 texels
    in, and the bookseller's "bookcase front", 128 texels tall, showed its
    top 48 in a niche 12,288 high -- a slice of a bookcase. A niche is one
    framed thing: its walls begin at their own left end, stand on the
    niche's own floor, and a picture tile is scaled to be seen whole.
    """
    report = {"niches": 0, "walls": 0, "pictures": 0}
    for region_id, region in layout.regions.items():
        if (getattr(region, "intent", None) or {}).get("kind") != SHELF_INTENT:
            continue
        allocation = compiled.allocations.get(region_id)
        if allocation is None:
            continue
        sector = level.sectors[allocation.sector_id]
        sector = sector.get("fields", sector) if isinstance(sector, dict) \
            else sector.fields
        clear = abs(int(sector["floor_z"]) - int(sector["ceiling_z"]))
        report["niches"] += 1
        start, count = int(sector["wall_ptr"]), int(sector["wall_count"])
        for wall_id in range(start, start + count):
            wall = level.walls[wall_id]
            wall = wall.get("fields", wall) if isinstance(wall, dict) \
                else wall.fields
            if int(wall["next_sector"]) >= 0:
                continue
            other = level.walls[int(wall["point2"])]
            other = other.get("fields", other) if isinstance(other, dict) \
                else other.fields
            length = (abs(int(other["x"]) - int(wall["x"]))
                      + abs(int(other["y"]) - int(wall["y"])))
            size = art_sizes.get(int(wall["picnum"]))
            if size is None or not length:
                continue
            width, height = size
            wall["x_panning"] = 0
            wall["y_panning"] = 0
            wall["cstat"] = int(wall["cstat"]) | 4      # stands on its floor
            if int(wall["picnum"]) in SHELF_PICTURES:
                #: the whole tile top to bottom, and its width kept in
                #: proportion: 2,048 z a texel at y_repeat 1
                y_repeat = max(1, round(2048 * height / clear))
                squash = y_repeat / 8.0
                repeats = max(1, round(length * squash / (width * 16)))
                wall["y_repeat"] = y_repeat
                wall["x_repeat"] = min(255, max(1, repeats * width // 8))
                report["pictures"] += 1
            else:
                repeats = max(1, round(length / (width * 16)))
                #: whole boards across the back; a cheek keeps its scale
                if length >= width * 16:
                    wall["x_repeat"] = min(255, repeats * width // 8)
            report["walls"] += 1
    return report


def run_along(name, host, *, axis: str, start: int, end: int,
              across0: int, across1: int, family: str, material,
              grade: int, host_clear: int, gap: int = 512,
              connector=None, wall_picnum: int | None = None,
              whole: bool = False):
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
        #: `whole`: one piece from end to end. A bar is one bar; modules
        #: with gaps between them are a row of benches.
        width = (end - start) if whole else \
            fam.widths[_roll(f"{name}:{index}", len(fam.widths))]
        if cursor + width > end:
            width = end - cursor
        if width < min(fam.widths):
            break
        rect = ((cursor, across0, cursor + width, across1) if axis == "x"
                else (across0, cursor, across1, cursor + width))
        place(f"{name}_{index}", host, rect, material, into=node,
              family=family, grade=grade, host_clear=host_clear,
              connector=connector, wall_picnum=wall_picnum)
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
