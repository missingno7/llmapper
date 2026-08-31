"""Gravesend's materials: surfaces named by ROLE, not picked per room.

The systemic texture fault the owner's "textures don't fit" verdict named:
every region in the city inherited one district wall tile, so interiors and
the sewer wore street facades (arched windows underground) and Market Slip
wore tile 414 -- which a contact sheet shows is *wood boarding*, not a
facade, hence the black slabs on the quay.

Tiles here are measured, not remembered.  Two passes stand behind them:

* a role-separated census of E3M1 / DWE3M1 / TEDE1M2 / E3M3 (walls weighted
  by length, split by whether the sector they face is street, interior or
  underground; floors and ceilings weighted by area), and
* a contact sheet rendered from Blood's own ART through
  `bloodmap.art.tile_to_rgb`, so every id below was looked at.

E3M1's facade census, for the record: 417 (55k units of street-facing wall),
400 (40k), 401 (27k), 414 (27k), 380 (26k), 393 (21k).  Its interiors run on
108/100 walls, floor 304, ceiling 454 -- a completely different register,
which is the point.

The opening/jamb tile is a property of the material, not a per-room choice:
of the 8,320 campaign rooms with more than one wall tile, 74% put a
different tile on their two-sided walls than on their solid ones.  Every
material here therefore carries one, and the compiler applies it through
`portal_wall_picnum`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Material:
    """One named surface set.  `opening` dresses this material's own jambs."""
    wall: int
    floor: int
    ceiling: int
    opening: int
    sky: bool = False
    note: str = ""

    def style_kwargs(self, **overrides) -> dict:
        """The Style fields this material implies."""
        out = {
            "wall_picnum": self.wall,
            "floor_picnum": self.floor,
            "ceiling_picnum": self.ceiling,
            "parallax_ceiling": self.sky,
        }
        out.update(overrides)
        return out

    def region_kwargs(self) -> dict:
        """Region fields that are not Style fields (the jamb rule)."""
        return {"portal_wall_picnum": self.opening}

    def facade_region_kwargs(self) -> dict:
        """The street-facing half of an aperture keeps the facade continuous.

        A street is the exterior shell, not the reveal behind a door or a
        display pane.  Its portal-side record therefore carries ``wall``;
        the thin porch/window sector on the other side keeps ``opening`` for
        the jamb.  This is the Build-sector equivalent of a wall sandwich.
        """
        return {"portal_wall_picnum": self.wall}


#: E3M1's night sky: all 45 of its parallax sectors name 3491, and a
#: side-by-side of our street against E3M1 sector 6 confirms the same red
#: cloud -- checked and NOT a fault, recorded so it is not re-litigated.
SKY = 3491

#: The street floors, and a correction.  E3M1's street runs three surfaces
#: in near-equal thirds by area -- 352 (37%), 4 (34%), 379 (29%) -- and a
#: contact sheet says which is which:
#:
#:   352  red-brown COBBLESTONE -- the roadway
#:     4  grey flagstone slabs  -- the pavement/walk
#:   379  grey streaked concrete
#:
#: We had these backwards.  ROADWAY was 4, so the whole city was paved in
#: E3M1's *sidewalk* tile, and a side-by-side against E3M1 sector 6 shows
#: what that costs: the reference frame is more than a third warm red cobble
#: and ours is grey wall to wall.  352 was meanwhile named BOARDWALK on the
#: strength of its name rather than its pixels -- the same mistake tile 414
#: taught, made again.
#:
#: The real boardwalk is 28: DWE3M10's pier promenade is 64% of it by area,
#: and it is plank, which is also why it works as the saloon's wall.
#:
#: One roadway for the whole city, deliberately: district seams run down
#: street centerlines, so a per-district floor puts a material change down
#: the middle of the avenue -- found by a pose that landed on the seam.
ROADWAY = 352
WALK = 4
BOARDWALK = 28

FACADES = {
    # One articulated facade per district identity (ID card), all from
    # E3M1's own facade census, each visually distinct on the contact sheet.
    "theatre_row": Material(
        wall=400, floor=ROADWAY, ceiling=SKY, opening=417, sky=True,
        note="grey ashlar with cornice and sash window: the grand street"),
    "old_crossing": Material(
        wall=384, floor=ROADWAY, ceiling=SKY, opening=417, sky=True,
        note="red brick with a small window: the humbler pre-boom quarter"),
    "market_slip": Material(
        wall=380, floor=ROADWAY, ceiling=SKY, opening=417, sky=True,
        note="stone with pilaster and lattice window: the civic river gate "
             "(replaces 414, which the contact sheet shows is boarding)"),
    "foundry_ward": Material(
        wall=393, floor=ROADWAY, ceiling=SKY, opening=417, sky=True,
        note="brown brick with the big arched industrial window"),
}

#: Masonry with no opening: yard walls, dock backs, boundary walls.
MASONRY = Material(wall=417, floor=ROADWAY, ceiling=SKY, opening=28, sky=True,
                   note="grimy stone-and-brick: E3M1's most-used street wall")

#: Boarding, now honestly employed: fences and hoardings, never a facade.
HOARDING = Material(wall=414, floor=ROADWAY, ceiling=SKY, opening=417,
                    sky=True, note="plank boarding (the retired 'facade')")

#: One material per interior ROLE, because a city's rooms are not one room.
#:
#: The first venues built came back as the same brown box four times over --
#: right register, no differentiation.  A per-building census of the town
#: maps says why that reads wrong: E3M1 puts 20 interior palettes in 337
#: sectors, TEDE1M2 35 in 613, E3M2 29 in 473.  A building's palette is how
#: you know which building you are in.
#:
#: Each entry below is one campaign building's own triple, taken whole
#: rather than assembled from parts, then looked at on a contact sheet:
#:
#:   common   E3M1's largest complex (123 sectors)   108 / 304 / 454
#:   saloon   E3M1 building 3 (56 sectors)            28 / 390 /  40
#:   parlor   E3M1 building 4 (63 sectors)           100 / 294 /  20
#:   theatre  E3M2 building 4 (28 sectors)           119 / 300 / 422
#:   shop     E6M1's shop, the venue reference        2294 / 290 / 40
#:   service  E3M1 building 5 (20 sectors)           379 / 304 / 379
INTERIORS = {
    "common": Material(wall=108, floor=304, ceiling=454, opening=100,
                       note="E3M1 interior: papered wall, coffered ceiling"),
    "saloon": Material(wall=28, floor=390, ceiling=40, opening=100,
                       note="plank walls over a wood floor under slate: "
                            "E3M1's drinking room"),
    "parlor": Material(wall=100, floor=294, ceiling=20, opening=68,
                       note="rust plaster over chequered tile: the cheap "
                            "amusement register"),
    "theatre": Material(wall=119, floor=300, ceiling=422, opening=203,
                        note="red-and-gold tapestry with a carved base "
                             "course, patterned carpet, medallion ceiling"),
    "shop": Material(wall=2294, floor=290, ceiling=40, opening=2293,
                     note="brick over wainscot: E6M1's shop, the open-front "
                          "reference"),
    "service": Material(wall=379, floor=304, ceiling=379, opening=28,
                        note="plain stone: stairs, cellars, back-of-house"),
    # The church, from Blood's own church.  E1M5's main interior is 194 of
    # its 283 interior sectors and runs 406 / 110 / 120; the 12-sector
    # register it keeps for its chancel runs 409 / 307 / 263, and 409 is a
    # Greek-key frieze while 307 is a mosaic medallion -- sanctuary tiles,
    # not nave tiles.  E1M1's mausoleum galleries are 421 / 253 / 253.
    "church": Material(wall=406, floor=110, ceiling=120, opening=93,
                       note="E1M5's nave: moulded pale stone over rubble"),
    "sanctuary": Material(wall=409, floor=307, ceiling=263, opening=406,
                          note="E1M5's chancel: meander frieze, mosaic floor"),
    "crypt": Material(wall=421, floor=253, ceiling=253, opening=1011,
                      note="E1M1's mausoleum galleries: mossy green brick"),
}

#: E3M3, Blood's own sewer: wall 492 dominates its solid walls, 255 its
#: jambs and ceilings, 568 its floors, 1120 the wet ones.
SEWER = Material(wall=492, floor=568, ceiling=255, opening=255,
                 note="E3M3 sewer register")
SEWER_WET = Material(wall=492, floor=1120, ceiling=255, opening=255,
                     note="E3M3 wet floor (mossy 1120)")

#: A backdrop box is a street seen through an opening, so it wears street
#: masonry under the sky -- never an interior material.
BACKDROP = MASONRY
