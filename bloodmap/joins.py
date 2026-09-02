"""How two surfaces meet: the other half of the representation.

Things are one table; joins are the other. A kerb is not an object -- it is
what the join road|pavement looks like, the texture on the inner face of the
road record, and whether it is a sector at all is a separate question.
Different pairs meet differently: road|road simply continues, road|pavement
makes a kerb, road|end wall stops the street, facade|opening carries a run
across a hole. The principle is Wave Function Collapse's: not only the pieces
but the rules for how pieces may meet.

This subsumes four things that were separate special cases -- the holder law
(P13's one record, one frame), the kerb (P14's `HeightIsland`), terminations
(`street.end_wall`), and continuity across cuts (P11/P13's frames). Each is a
ROW here rather than a branch somewhere.

**A pair with no rule is a loud failure, never a default.** That is the whole
value: the compiler stops asking "what should this wall wear" and starts
asking "what kind of join is this", and a join nobody has described is a
question for a person rather than an inherited tile. Gravesend's kerbs wore
the houses precisely because an undescribed join fell through to whatever the
region happened to carry.

The reader half is the same table backwards: a two-sided wall whose records
match a rule is evidence of that join, which is how surfaces are recovered
from originals.

A correction the corpus forced, and it is about reading rather than water
=========================================================================

Tile **2490 is stone**. It appears to be water because Blood palettises it:
of its 34 campaign sectors, **25 carry floor palette 10 and pan (water), 8
carry palette 0 and do not (stone)**, and one is blue but still. So the test
for "this surface is water" is the PALETTE and the panning, never the tile --
and a census that excluded 2490 as a material would throw away 8 legitimate
stone faces along with the 25 wet ones.

It matters here because the shore rows below are about a surface kind, and
surface kind is not readable from a tile. Excluding water by palette and
panning removes 136 of 1046 outdoor step records (13%) from the kerb census;
2490 still tops what remains, at 55, as stone.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

# --- surface kinds ---------------------------------------------------------

ROAD = "road"
PAVEMENT = "pavement"
FACADE = "facade"
OPENING = "opening"
END_WALL = "end_wall"
BUILDING_BACK = "building_back"
SHORE = "shore"
SEA = "sea"
HORIZON = "horizon"
CHASM = "chasm"
ENCLOSURE_BACKDROP = "enclosure_backdrop"
#: The inside of a shell. Not a ground surface: the sun does not reach it and
#: the light domain refuses it for the plainest of Rule 2's reasons -- it has
#: no sky.
INTERIOR = "interior"
VOID = "void"
GATE = "gate"

#: The map-edge family: the kinds a city may end with. Three are measured and
#: one is not yet located (`ENCLOSURE_BACKDROP` -- walls ringing the city with
#: fake masses beyond and no interiors; no corpus precedent found yet, so it
#: carries no row and asking for one fails loudly rather than guessing).
EDGE_KINDS = frozenset({END_WALL, CHASM, HORIZON, ENCLOSURE_BACKDROP})

# --- height relations ------------------------------------------------------

EQUAL = "equal"
B_ABOVE = "b_above"
B_BELOW = "b_below"
ONE_SIDED = "one_sided"

#: How a STEP's face is shaded, relative to the floor shade of the surface
#: that owns the record. Measured on E3M1's eleven kerb records, which are the
#: only place the campaign states this relation: the six standing on road at
#: floor shade 32 read a median 38, and the five standing on road at 8 read a
#: median 8. Median delta over all eleven **+6**, quartiles -8 and +10.
#:
#: It matters because a step face that keeps the base while the surfaces
#: around it darken is the one thing in an outdoor scene that does not obey
#: the sun. The other step rows below carry the same offset, and the corpus
#: measures it only at the kerb -- that extension is stated, not measured.
KERB_SHADE_OFFSET = 6

#: What a record may show. `NOTHING` is not "no rule": it is the rule that
#: this join draws no band, which is what a road/road cut and a shore/sea meet
#: both do and what makes their frames continue.
NOTHING = "nothing"


class JoinError(ValueError):
    """A pair of surfaces nobody has described meeting."""


@dataclass(frozen=True)
class JoinRule:
    """What each side of one kind of join shows, and what happens to frames.

    `a_shows` and `b_shows` name the band and its tile class, `cstat` the bits
    the record carries, `frame` whether the surface frame CONTINUES across the
    edge or the edge is a boundary between two frames, and `holder` whether
    the join needs a sector of its own to exist at all (P13's law: a material
    with its own scale needs a record no other surface uses).
    """

    a: str
    b: str
    height: str
    a_shows: str = NOTHING
    b_shows: str = NOTHING
    cstat: int = 0
    frame: str = "continues"
    holder: bool = False
    #: What the STEP's own face is shaded, relative to the floor shade of the
    #: surface that owns the record. A step record is not lit by the surfaces
    #: it separates for free -- it is a wall, and its shade is written -- so
    #: the join that draws the band says what the band is shaded too.
    shade_offset: int | None = None
    evidence: str = ""

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.a, self.b, self.height)


def _rows() -> tuple[JoinRule, ...]:
    return (
        #: E3M1, the outdoor rows -----------------------------------------
        JoinRule(ROAD, ROAD, EQUAL, evidence="E3M1 s3|s8, s7|s8, s8|s45: a "
                 "shadow or junction cut draws nothing and the road's frame "
                 "runs through it"),
        JoinRule(ROAD, PAVEMENT, B_ABOVE, a_shows="lower band, kerb class",
                 frame="independent", shade_offset=KERB_SHADE_OFFSET,
                 evidence="E3M1 11/11 road-side records wear tile 6, step "
                          "2048 without exception; those same 11 records are "
                          "shaded a median +6 from the road floor they stand "
                          "on -- 38 where the road reads 32, 8 where it "
                          "reads 8 -- so the face follows the field and does "
                          "not sit at the base"),
        JoinRule(PAVEMENT, PAVEMENT, EQUAL,
                 evidence="E3M1's shadow-cut pavement bands: where the sun's "
                          "iso-line crosses a pavement the two pieces meet at "
                          "equal z and draw nothing, which is the same "
                          "meeting a path between two abutting islands makes. "
                          "(The row used to cite s10/s11; those are masses, "
                          "not a path -- P15's reader found it.)"),
        JoinRule(PAVEMENT, FACADE, ONE_SIDED, b_shows="facade run",
                 frame="independent",
                 evidence="the facade's frame is world-anchored, so it does "
                          "not take the pavement's"),
        JoinRule(ROAD, END_WALL, B_ABOVE, a_shows="lower band, facade stone",
                 cstat=1, frame="boundary", shade_offset=KERB_SHADE_OFFSET,
                 evidence="E3M1 s0/s339/s343: blocking, y_repeat 8, the "
                          "district's own stone; the end wall's faces carry "
                          "their own frame"),
        JoinRule(PAVEMENT, END_WALL, B_ABOVE, a_shows="lower band, facade "
                 "stone", cstat=1, frame="boundary",
                 shade_offset=KERB_SHADE_OFFSET,
                 evidence="E3M1 s339 to s2/s3/s4, same dialect as the road"),
        JoinRule(PAVEMENT, FACADE, B_ABOVE, a_shows="lower band, facade "
                 "class", cstat=1, frame="boundary",
                 shade_offset=KERB_SHADE_OFFSET,
                 evidence="E3M1: the one-sided records of its outdoor sectors "
                          "ARE its facades -- 122 of them, every one at "
                          "y_repeat 8, weighted by length 401 (27.6%), 417 "
                          "(21.5%), 181 (11.6%) and 400 (8.7%); and its "
                          "records stepping up from the ground into a "
                          "building wear the same family, 417 on the road's "
                          "two at 100352 and 67584 and 400 on five pavement "
                          "records. The ground's frame stops at the wall"),
        JoinRule(ROAD, FACADE, B_ABOVE, a_shows="lower band, facade class",
                 cstat=1, frame="boundary", shade_offset=KERB_SHADE_OFFSET,
                 evidence="E3M1's road stepping up into a building: two "
                          "records, tile 417, at 100352 and 67584"),
        #: E6M1, the shopfront ---------------------------------------------
        JoinRule(FACADE, OPENING, ONE_SIDED,
                 a_shows="upper band, pegged cstat 4, continues the facade",
                 b_shows="the insert's own frame", frame="continues",
                 holder=True,
                 evidence="E6M1 s4/s64: a 512-deep recess, sill 8192 up, head "
                          "77824 down; the facade crosses the mouth"),
        #: The shell: facade, opening, interior -----------------------------
        JoinRule(PAVEMENT, OPENING, EQUAL, frame="boundary",
                 evidence="E6M1 s4/s64: the threshold of a shopfront recess "
                          "is at the pavement's own z and draws no band; the "
                          "insert's frame is its own and does not continue "
                          "the ground's"),
        JoinRule(OPENING, INTERIOR, EQUAL, frame="boundary",
                 evidence="E6M1: past the mouth the floor runs on unchanged "
                          "into the room, and the room's frame is the room's"),
        JoinRule(OPENING, FACADE, B_ABOVE, b_shows="upper band, facade class",
                 frame="continues", holder=True,
                 evidence="E6M1 s4/s64: the head of the recess is 77824 down "
                          "from the facade above it and the FACADE'S run "
                          "crosses the mouth -- that is the one record the "
                          "holder law is about, and it belongs to the facade "
                          "and not to the opening"),
        JoinRule(INTERIOR, FACADE, B_ABOVE, b_shows="upper band, facade class",
                 cstat=1, frame="boundary",
                 evidence="E3M1: its records from the ground up into a "
                          "building wear the same facade family, blocking, "
                          "and the building's frame is not the street's"),
        #: The map edge ----------------------------------------------------
        JoinRule(SHORE, SEA, EQUAL, frame="independent",
                 evidence="DWE3M10: the shore meets the sea at equal z and "
                          "neither record draws; the sea carries its own "
                          "panning frame"),
        JoinRule(SEA, SEA, EQUAL,
                 evidence="DWE3M10: its 18 sea sectors meet one another at "
                          "equal z on 150 records and the meeting draws no "
                          "band -- the cut set there is the water's own, and "
                          "here it is the light field's"),
        JoinRule(SHORE, SHORE, EQUAL,
                 evidence="DWE3M10 s120/s403 meet the same way: one shore cut "
                          "in two is still one shore"),
        JoinRule(SHORE, PAVEMENT, B_ABOVE, a_shows="lower band, quay class",
                 frame="independent", shade_offset=KERB_SHADE_OFFSET,
                 evidence="DWE3M10 s120/s403: the shore's landward neighbour "
                          "stands above it and the band is on the SHORE side "
                          "-- 4 records step 35840 to tile 255 and 2 to tile "
                          "21 wearing 55/28 with two of them blocking, and "
                          "one gentle record steps 3072 to tile 21 wearing 28 "
                          "and does not block. 3072 is inside Blood's 4096 "
                          "autostep, so the gentle case is the walkable one"),
        JoinRule(SEA, HORIZON, EQUAL, frame="independent",
                 evidence="DWE3M10 s404: floor AND ceiling both tile 3678 "
                          "with the parallax bit on both, a zero-height "
                          "sector at the sea's own z"),
        JoinRule(BUILDING_BACK, VOID, ONE_SIDED, a_shows="one-sided, no facade",
                 frame="boundary",
                 evidence="a building's back is not a facade and takes no "
                          "facade run"),
        JoinRule(PAVEMENT, CHASM, B_BELOW, a_shows="lower band, rock",
                 cstat=1, frame="boundary", shade_offset=KERB_SHADE_OFFSET,
                 evidence="DWE3M1: its deepest sectors sit 26.9 player "
                          "heights below the median floor (z 526336 against "
                          "70656) wearing rock 274, 270 and 411"),
    )


ROWS: dict[tuple[str, str, str], JoinRule] = {}
for _rule in _rows():
    ROWS[_rule.key] = _rule


def rule(a: str, b: str, height: str) -> JoinRule:
    """The rule for this join, or a loud failure.

    Symmetric in the pair: asking `(pavement, road, b_below)` finds the
    `(road, pavement, b_above)` row with its sides swapped, because a join is
    one thing seen from two records.
    """
    found = ROWS.get((a, b, height))
    if found is not None:
        return found
    flipped = ROWS.get((b, a, _flip(height)))
    if flipped is not None:
        return JoinRule(a=flipped.b, b=flipped.a, height=height,
                        a_shows=flipped.b_shows, b_shows=flipped.a_shows,
                        cstat=flipped.cstat, frame=flipped.frame,
                        holder=flipped.holder, evidence=flipped.evidence)
    raise JoinError(
        f"no rule for {a!r} meeting {b!r} at {height!r}. A join nobody has "
        f"described is a question for a person, not a tile inherited from "
        f"whichever region happened to own the record -- which is how "
        f"Gravesend's kerbs came to wear the houses")


def _flip(height: str) -> str:
    return {B_ABOVE: B_BELOW, B_BELOW: B_ABOVE}.get(height, height)


def height_relation(a_floor_z: int, b_floor_z: int, *, one_sided: bool = False,
                    tolerance: int = 0) -> str:
    """Which height relation two surfaces are in. Blood's z grows downward."""
    if one_sided:
        return ONE_SIDED
    delta = int(b_floor_z) - int(a_floor_z)
    if abs(delta) <= tolerance:
        return EQUAL
    #: b standing HIGHER is a smaller z
    return B_ABOVE if delta < 0 else B_BELOW


def described(pairs: Iterable[tuple[str, str, str]]) -> list[str]:
    """Which of these joins the table cannot describe.

    The gate: run it over every shared edge a build produced and a non-empty
    answer names the joins somebody has to decide.
    """
    out = []
    for a, b, height in pairs:
        try:
            rule(a, b, height)
        except JoinError as error:
            out.append(str(error).split(".")[0])
    return out


# --- reading a surface's kind ---------------------------------------------

#: Blood palettises stone to make water. Tile 2490 is the case that proves it:
#: 25 of its 34 campaign sectors carry palette 10 and pan, 8 carry palette 0
#: and do not. So water is a palette and a behaviour, never a tile.
WATER_PALETTES = frozenset({10})


def _x(item: Any) -> dict[str, Any]:
    """A sector's Blood extra, read the way both shapes store it.

    `assembly._x` has had this since it was written and this had not: a
    `LevelIR` sector carries its XSECTOR under the key `"blood"` and a
    `DiskObject` carries it on an `extra` attribute, so `getattr(sector,
    "extra", None)` is `None` for every decompiled level. On DWE3M10 -- the
    map the shore and sea rows were mined from -- that lost 4 of its 22
    panning sectors, the ones at palette 0 whose only evidence is that they
    move.
    """
    extra = item["blood"] if isinstance(item, dict) else getattr(
        item, "extra", None)
    if extra is None:
        return {}
    return dict(extra["fields"] if isinstance(extra, dict) else extra.fields)


def is_water(sector: Any) -> bool:
    """Does this surface behave and read as water?"""
    fields = sector["fields"] if isinstance(sector, dict) else sector.fields
    extra = _x(sector)
    panning = any(int(extra.get(name, 0)) for name in
                  ("pan_floor", "pan_always", "pan_velocity", "drag"))
    return panning or int(fields.get("floor_pal", 0)) in WATER_PALETTES

# --- the waterfront, measured on DWE3M10 -----------------------------------

#: The sea: tile 2490 under palette 10, panning at velocity 10 on angle 900,
#: with `drag` so it carries a body. Eighteen sectors, all identical.
SEA_TILE = 2490
SEA_PALETTE = 10
SEA_PAN_VELOCITY = 10
SEA_PAN_ANGLE = 900
#: The horizon: a ZERO-HEIGHT sector -- floor_z equals ceiling_z -- with tile
#: 3678 on both surfaces and the parallax bit on both. DWE3M10 s404 sits at
#: the sea's own z (21504) and meets the quay at delta 0; s201 and s202 are
#: the same trick elsewhere in the map.
HORIZON_TILE = 3678
#: What the shore wears where it meets the sea, by frequency: sand 433 (33),
#: 21 (20), the horizon tile itself (16), 255 (7), 181 (4), concrete 416.
SHORE_TILES = (433, 21, 255, 181, 416)
#: The shore stands below the quay by one walkable step. DWE3M10's gentle
#: case is 3072, which is inside Blood's 4096 autostep; its other seven
#: records step 35840, which is a quay wall rather than a shore.
SHORE_STEP = 3072
#: The chasm: rock, and a depth. DWE3M1's floor spread is 30.6 player heights
#: and its outermost floor sits 26.9 below the median.
CHASM_TILES = (274, 270, 411)
CHASM_DEPTH_BODIES = (26.0, 28.0)


# --- the compiler side: apply the table at every shared edge ---------------

#: What a rule's `a_shows` names, resolved to a tile. The table says the tile
#: CLASS ("lower band, kerb class") because a class is what the corpus
#: attests; which member of the class a level uses is the level's choice, and
#: Gravesend's is E3M1's.
TILE_CLASSES = {
    "kerb class": 6,
    "facade stone": 400,
    "rock": 274,
    #: DWE3M10's shore-side band where the land stands above the sand: 28 on
    #: 3 records and 55 on 4, so the class has two members and 28 is the one
    #: the gentle, walkable step wears.
    "quay class": 28,
    #: E3M1's facade family, weighted by the LENGTH each tile covers rather
    #: than by its record count, because a long wall shows more of itself:
    #: 401 at 27.6%, 417 at 21.5%, 181 at 11.6%, 400 at 8.7%. 401 is the
    #: class's representative; the four together are 69.4% of the facade.
    "facade class": 401,
}

#: The four the census leaves standing, in order of the length they cover.
FACADE_FAMILY = (401, 417, 181, 400)
#: Without exception on all 122 of E3M1's facade records.
FACADE_Y_REPEAT = 8
#: What a roof wears: E3M1's own, on the 29 records where the street looks up
#: into a building.
ROOF_TILE = 379


def _face(item: Any) -> Any:
    if isinstance(item, dict):
        return item["fields"] if "fields" in item else item
    return getattr(item, "fields", item)


def shared_edges(level: Any, owners: Iterable[int] | None = None):
    """Every two-sided record, with the sector on each side.

    Yields `(wall_id, here, there)`. Both records of a pair are yielded, once
    each, because a join has two sides and each side's rule is about its own
    record.
    """
    if owners is None:
        from .texture_frame import sector_index

        owners = sector_index(level)
    for wall_id, wall in enumerate(level.walls):
        nxt = int(_face(wall)["next_sector"])
        if nxt >= 0:
            yield wall_id, owners[wall_id], nxt


def apply(level: Any, kinds: dict[int, str], *,
          owners: Iterable[int] | None = None,
          tiles: dict[str, int] | None = None,
          strict: bool = True) -> dict[str, Any]:
    """Write what the table says at every shared edge.

    `kinds` maps sector id to surface kind. Every two-sided record whose two
    sides have kinds is looked up, and the rule decides what that record
    shows and which cstat bits it carries. **A pair with no row raises** under
    `strict`, which is the point: the compiler stops asking "what should this
    wall wear" and starts asking "what kind of join is this".

    Returns what it wrote and what it could not answer, so a build can print
    both rather than discovering later that a join was silently defaulted.
    """
    from .texture_frame import sector_index

    owners = list(owners) if owners is not None else sector_index(level)
    tiles = dict(TILE_CLASSES if tiles is None else tiles)
    written = 0
    unknown: list[str] = []
    applied: list[dict[str, Any]] = []
    for wall_id, here, there in shared_edges(level, owners):
        a_kind, b_kind = kinds.get(here), kinds.get(there)
        if a_kind is None or b_kind is None:
            continue
        height = height_relation(
            int(_face(level.sectors[here])["floor_z"]),
            int(_face(level.sectors[there])["floor_z"]))
        try:
            found = rule(a_kind, b_kind, height)
        except JoinError as error:
            unknown.append(str(error).split(".")[0])
            if strict:
                raise
            continue
        face = _face(level.walls[wall_id])
        shows = found.a_shows
        if shows != NOTHING:
            tile = next((value for name, value in tiles.items()
                         if name in shows), None)
            if tile is not None:
                face["picnum"] = int(tile)
                written += 1
        if found.cstat:
            face["cstat"] = int(face["cstat"]) | int(found.cstat)
        if found.shade_offset is not None:
            #: The step's face follows the field, because the floor it stands
            #: on already has. Read from the OWNER's floor, which by this pass
            #: has the sun's and the lamps' contributions summed into it.
            face["shade"] = (int(_face(level.sectors[here])["floor_shade"])
                             + int(found.shade_offset))
        applied.append({"wall": wall_id, "a": a_kind, "b": b_kind,
                        "height": height, "shows": shows,
                        "frame": found.frame})
    return {"records": len(applied), "written": written,
            "unknown": sorted(set(unknown)), "applied": applied,
            "frame_boundaries": sum(1 for row in applied
                                    if row["frame"] == "boundary")}
