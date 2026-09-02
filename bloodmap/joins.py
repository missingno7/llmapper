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
                 frame="independent",
                 evidence="E3M1 11/11 road-side records wear tile 6, step "
                          "2048 without exception"),
        JoinRule(PAVEMENT, PAVEMENT, EQUAL,
                 evidence="E3M1 s10/s11: a pavement-only path between "
                          "abutting islands, and shadow cuts across a band"),
        JoinRule(PAVEMENT, FACADE, ONE_SIDED, b_shows="facade run",
                 frame="independent",
                 evidence="the facade's frame is world-anchored, so it does "
                          "not take the pavement's"),
        JoinRule(ROAD, END_WALL, B_ABOVE, a_shows="lower band, facade stone",
                 cstat=1, frame="boundary",
                 evidence="E3M1 s0/s339/s343: blocking, y_repeat 8, the "
                          "district's own stone; the end wall's faces carry "
                          "their own frame"),
        JoinRule(PAVEMENT, END_WALL, B_ABOVE, a_shows="lower band, facade stone",
                 cstat=1, frame="boundary",
                 evidence="E3M1 s339 to s2/s3/s4, same dialect as the road"),
        #: E6M1, the shopfront ---------------------------------------------
        JoinRule(FACADE, OPENING, ONE_SIDED,
                 a_shows="upper band, pegged cstat 4, continues the facade",
                 b_shows="the insert's own frame", frame="continues",
                 holder=True,
                 evidence="E6M1 s4/s64: a 512-deep recess, sill 8192 up, head "
                          "77824 down; the facade crosses the mouth"),
        #: The map edge ----------------------------------------------------
        JoinRule(SHORE, SEA, EQUAL, frame="independent",
                 evidence="DWE3M10: the shore meets the sea at equal z and "
                          "neither record draws; the sea carries its own "
                          "panning frame"),
        JoinRule(SEA, HORIZON, EQUAL, frame="independent",
                 evidence="DWE3M10 s404: floor AND ceiling both tile 3678 "
                          "with the parallax bit on both, a zero-height "
                          "sector at the sea's own z"),
        JoinRule(BUILDING_BACK, VOID, ONE_SIDED, a_shows="one-sided, no facade",
                 frame="boundary",
                 evidence="a building's back is not a facade and takes no "
                          "facade run"),
        JoinRule(PAVEMENT, CHASM, B_BELOW, a_shows="lower band, rock",
                 cstat=1, frame="boundary",
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


def is_water(sector: Any) -> bool:
    """Does this surface behave and read as water?"""
    fields = sector["fields"] if isinstance(sector, dict) else sector.fields
    extra = getattr(sector, "extra", None)
    extra = dict(extra.fields) if extra is not None else {}
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
#: The chasm: rock, and a depth. DWE3M1's floor spread is 30.6 player heights
#: and its outermost floor sits 26.9 below the median.
CHASM_TILES = (274, 270, 411)
CHASM_DEPTH_BODIES = (26.0, 28.0)
