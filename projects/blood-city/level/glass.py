"""Shop windows: the city's call into the promoted glass constructor.

The recipe, the E6M1 reading and the NBlood citation all moved to
`bloodmap.glass` -- a constructor only one project can call is not a
promotion, and the zoo's conformance rule says a public constructor owes an
exhibit, which this could not have while it lived in a level.

What stays here is the city's own use of it: which spans are windows. The
behaviour is unchanged, and `glaze` is re-exported so no call site moves.
"""

from __future__ import annotations

from bloodmap.glass import (                                # noqa: F401
    GLASS_CSTAT, GLASS_REPEATS, GLASS_TILE, GLASS_XWALL, GlassError,
    attach_xwall, breaks_to, glaze, holder, pane_faults,
)


# ---- the shopfront: a pane in a frame ----------------------------------------
#
# Owner, 2026-11-17, walking the city: "the glass should sit in an
# aperture/frame so glass texture scaling won't be colliding with facade
# texture".
#
# What they saw is a record law.  A wall record has ONE x_repeat/y_repeat, and
# it scales the record's masked middle and its step bands alike.  Every window
# here was a display box glazed on its street-side wall -- the wall whose step
# bands are the facade's lintel over the pane and the riser under it -- so the
# pane's scale was also the facade's across that span: the stonework above
# each window was drawn several times larger than the same tile beside it
# (`experiments/shopfronts-streets/before/pawn_front`).
#
# So the pane goes where there are no bands.  From the street inward:
#
#   street | REVEAL | SASH, one per bay | display box | shop
#
# The reveal, every sash and the box share one floor and one ceiling.  The
# street-side record is two-sided to the reveal and carries the facade's
# lintel and riser at the facade's own scale.  The pane hangs between a sash
# and the box, where both sides stand at the same heights, so that record is
# glass and nothing else.  Sashes are divided by solid mullions, which the
# reveal shows as its own back wall, so each pane sits in a pocket with a
# jamb either side of it; and a mullion never reaches the street face, where
# it would be a slice of the facade's painted windows.

#: Depth of the reveal and of the sash pocket behind it.
REVEAL_DEPTH = 128
SASH_DEPTH = 128
#: The widest single sheet, and the pier between two.  E6M1's own panes are
#: 4096; a display that long with nothing dividing it read as "a grey sheet".
BAY_WIDEST = 2560
MULLION = 256
#: The stall riser under a shop window.  E6M1 lifts its display 8192; this
#: city's shops are lower-ceilinged, so half that leaves a mannequin headroom.
SILL = 4096
#: The owner's tile for "the inside faces of jambs" (owner-anchors, 195).
JAMB_TILE = 195


def _bays(a0: int, a1: int, *, widest: int = BAY_WIDEST,
          mullion: int = MULLION, grid: int = 64) -> list[tuple[int, int]]:
    """Divide a window's length into equal bays with mullions between."""
    length = int(a1) - int(a0)
    count = 1
    while (length - (count - 1) * mullion) / count > widest:
        count += 1
    bay = ((length - (count - 1) * mullion) // count) // grid * grid
    slack = length - count * bay - (count - 1) * mullion
    #: any remainder from the grid goes into the mullions' share at the ends
    start = int(a0) + (slack // 2) // grid * grid
    out = []
    for index in range(count):
        b0 = start + index * (bay + mullion)
        out.append((b0, b0 + bay))
    if count == 1:
        out = [(int(a0), int(a1))]
    return out


def shopfront(rect: Sequence[int], outward: str, *,
              reveal: int = REVEAL_DEPTH, sash: int = SASH_DEPTH) -> dict:
    """Where the reveal, the sashes, the box and the panes of a window go.

    `rect` is the whole window volume, facade line to shop; `outward` is the
    compass side the street (or concourse) is on.  Everything is returned as
    (x0, y0, x1, y1), plus the face names a caller needs to join them.
    """
    x0, y0, x1, y1 = (int(v) for v in rect)
    if outward not in ("north", "south", "east", "west"):
        raise GlassError(f"a shopfront faces a compass side, not {outward!r}")
    along_x = outward in ("north", "south")
    depth = (y1 - y0) if along_x else (x1 - x0)
    if depth < reveal + sash + 128:
        raise GlassError(f"a window {depth} deep cannot hold a {reveal} "
                         f"reveal, a {sash} sash and a display")
    inward = {"north": "south", "south": "north",
              "east": "west", "west": "east"}[outward]
    #: `lo` layers start at the low coordinate, `hi` ones at the high.
    low = outward in ("north", "west")

    def layer(d0: int, d1: int, a0: int, a1: int):
        if along_x:
            ya, yb = (y0 + d0, y0 + d1) if low else (y1 - d1, y1 - d0)
            return (a0, ya, a1, yb)
        xa, xb = (x0 + d0, x0 + d1) if low else (x1 - d1, x1 - d0)
        return (xa, a0, xb, a1)

    a0, a1 = (x0, x1) if along_x else (y0, y1)
    bays = _bays(a0, a1)
    plane = reveal + sash
    panes = []
    for b0, b1 in bays:
        #: a thin box round the pane's plane: `glaze` takes a wall whose
        #: midpoint lies inside a span, and nothing else here does
        panes.append(layer(plane - 16, plane + 16, b0 + 16, b1 - 16))
    return {
        "reveal": layer(0, reveal, a0, a1),
        "sashes": [layer(reveal, plane, b0, b1) for b0, b1 in bays],
        "box": layer(plane, depth, a0, a1),
        "panes": panes,
        "outward": outward, "inward": inward,
    }



# ---- the surround: a riser, a fascia, a name, a lamp ------------------------
#
# DukCity, stood in for the first time on 2026-11-17 (`references/
# dukcity-transfer.md`): a shop is a band of a SECOND material at the foot of
# its building -- a stall riser under the glass, a fascia over it with the
# shop's name on it -- and on a dark street the room behind the glass is lit.
# Measured in both games: DukCity3's street floor is at shade 37 and its rooms
# behind glass at 24; E3M1's are 32 and 24.  Gravesend's were 32 and 32, its
# shops were named on their own INSIDE walls, and its facades were one tile
# from pavement to sky.
#
# None of that needs a new sector.  The reveal already stands between the
# street and the sash pockets.  Give it the street's floor and a ceiling a
# fascia's height over the window's head, and:
#
#   * the band under each pane (grade to sill) and the band over it (head to
#     the reveal's ceiling) are the step bands of the reveal-to-sash wall,
#     drawn from the REVEAL's record: the riser and the fascia, in the shop's
#     own material;
#   * the solid wall between two sashes is the reveal's own back wall: a
#     pilaster, floor to fascia;
#   * the street's record over the mouth starts above the fascia and is the
#     facade's, at the facade's scale, as before;
#   * the pane still hangs between a sash and the box, which share one floor
#     and one ceiling, so the glass rule is untouched.

#: The fascia: 0.72 of a body over the window's head.  A campaign sign letter
#: hangs a median 2.54 bodies over the street (n=86, range 1.69 to 5.13);
#: over a head at 1.45 this puts the band's middle at 1.81, inside the range.
FASCIA = 12288

#: What each kind of shop is fronted in, from the owner's tile sheet:
#: (surround, pilaster, the style its name is lettered in).
#:   105 "coffered wood panelling", 88 "wooden column/pilaster with base and
#:   capital", 215 "pressed metal", 195 "metal rail/track -- the inside faces
#:   of jambs", 84 "wooden paneling / wainscot", 179 "wooden panel".
SURROUNDS = {
    "pawn": (84, 88, "fascia"),
    "hall": (215, 195, "fascia"),
    "arcade": (105, 88, "label"),
}

#: The lamp in a display: the owner's "lamp hanging on a chain" (641).
DISPLAY_LAMP = 641
#: 641 is 128 texels tall; a sprite's z height is texels * y_repeat * 4.
#: The chain is cut to the display: the lamp hangs in its upper third.  At a
#: fixed length of a body a blind reviewer found one "dropping almost to the
#: floor" of an arcade unit and another "mid-doorway at eye level".
DISPLAY_LAMP_SHARE = 0.34


def lamp_repeats(clear: int) -> tuple[int, int]:
    y = max(8, min(32, int(clear * DISPLAY_LAMP_SHARE) // 512))
    return (max(16, y), y)

#: How strong a display's lamp and a shop's own light are, as LightBomb
#: sources.  An indoor bracket is 1.0 and a street lamp 2.0
#: (`lightpools.LAMP_INTENSITY`); at 1.0 six display lamps moved their rooms
#: two shade steps, against the eight to thirteen that DukCity3 and E3M1
#: hold between a dark street and the rooms behind its glass.
DISPLAY_LIGHT = 5.0
SHOP_LIGHT = 10.0

#: Every shopfront built, for the passes that run after the venues: the
#: names, the lamps, the pilasters and the what-if tags.
FRONTS: list[dict] = []


def surround(front: dict, *, name: str, kind: str, reveal, box, shop,
             grade: int, sill: int, box_clear: int, words: str | None = None,
             lit: bool = True) -> None:
    """Make a window's reveal its shop's surround, and remember the front.

    `reveal`, `box` and `shop` are the rooms; `box_clear` is the display's
    own clear height, so the window's head stands `sill + box_clear` over
    the pavement and the fascia over that.
    """
    if kind not in SURROUNDS:
        raise GlassError(f"no shopfront is fronted in {kind!r}")
    tile, pilaster, style = SURROUNDS[kind]
    head = int(sill) + int(box_clear)
    reveal.surfaces(wall_picnum=tile, floor_z=int(grade),
                    clear_height=head + FASCIA)
    reveal.intent.update({"kind": "shopfront", "shop": name})
    box.intent.update({"kind": "shop_display", "shop": name})
    if lit:
        #: A source where the lamp hangs; the lamp itself is a sprite, placed
        #: once the layout exists (`hang_lamps`).  And the surfaces it falls
        #: on are GENERATED: a room that states its own floor shade is
        #: protected from LightBomb (`planar_layout`), which is right for a
        #: room and wrong for one with a lamp in it.  The first build hung
        #: six lamps and lit nothing: every display stayed at 32.
        lit_surfaces = ["floor", "ceiling", "wall"]
        box.intent["generated_surfaces"] = lit_surfaces
        shop.intent["generated_surfaces"] = lit_surfaces
    x0, y0, x1, y1 = front["reveal"]
    out = front["outward"]
    #: the reveal's back wall: where the sashes open and the name is written
    #: ordered so the reveal lies on the side `wallplane` offsets a sprite to
    back = {"north": ((x1, y1), (x0, y1)), "south": ((x0, y0), (x1, y0)),
            "west": ((x1, y0), (x1, y1)), "east": ((x0, y1), (x0, y0))}[out]
    FRONTS.append({
        "name": name, "kind": kind, "words": words, "style": style,
        "pilaster": pilaster, "lit": lit,
        "reveal": reveal.region_id, "box": box.region_id,
        "shop": shop.region_id, "back": back,
        "head_bodies": head / 16960.0,
        "fascia_bodies": FASCIA / 16960.0,
        "box_rect": front["box"],
    })


def write_names(layout) -> dict:
    """Letter each shop's name on its fascia."""
    import wallplane

    report = {"written": [], "no_room": []}
    for front in FRONTS:
        if not front["words"]:
            continue
        a1, a2 = front["back"]
        centre = front["head_bodies"] + front["fascia_bodies"] / 2.0
        ids = wallplane.text(
            layout, f"sign:fascia_{front['name']}", front["reveal"], a1, a2,
            words=front["words"], style=front["style"],
            height_player_heights=centre, over_steps=True)
        (report["written"] if ids else report["no_room"]).append(
            front["words"])
    return report


def hang_lamps(layout) -> int:
    """A chain lamp in each lit display, hung from its ceiling."""
    hung = 0
    lit_shops: set = set()
    for front in FRONTS:
        if not front["lit"]:
            continue
        region = layout.regions[front["box"]]
        x0, y0, x1, y1 = front["box_rect"]
        ceiling = int(region.ceiling_z)
        repeats = lamp_repeats(int(region.floor_z) - ceiling)
        drop = 128 * repeats[1] * 4
        #: the source is where the lamp's flame is, and its strength is a
        #: property of the lamp (`DISPLAY_LIGHT`)
        layout.add_light_source(
            f"light:display_{front['name']}", front["box"],
            x=(x0 + x1) // 2, y=(y0 + y1) // 2,
            #: at the display's middle height, not at the lantern: a source
            #: up under the ceiling lights the ceiling, and shortening the
            #: chains (as the reviewer asked) took the displays from eleven
            #: shade steps under the street back to four
            z=(ceiling + int(region.floor_z)) // 2, intensity=DISPLAY_LIGHT)
        shop = layout.regions[front["shop"]]
        if front["shop"] not in lit_shops:
            lit_shops.add(front["shop"])
            xs = [point[0] for point in shop.outer]
            ys = [point[1] for point in shop.outer]
            layout.add_light_source(
                f"light:shop_{front['name']}", front["shop"],
                x=(min(xs) + max(xs)) // 2, y=(min(ys) + max(ys)) // 2,
                z=int(shop.floor_z) - 20000, intensity=SHOP_LIGHT)
        layout.add_sprite(
            f"lamp:display_{front['name']}", front["box"],
            x=(x0 + x1) // 2, y=(y0 + y1) // 2,
            z=ceiling + drop, picnum=DISPLAY_LAMP, cstat=0,
            shade=-32, x_repeat=repeats[0], y_repeat=repeats[1], status=0)
        hung += 1
    return hung


def stand_pilasters(level, allocations) -> int:
    """The solid wall between two sashes wears the shop's pilaster."""
    painted = 0
    for front in FRONTS:
        allocation = allocations.get(front["reveal"])
        if allocation is None:
            continue
        fields = level.sectors[allocation.sector_id]["fields"]
        start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        (ax, ay), (bx, by) = front["back"]
        for wall_id in range(start, start + count):
            wall = level.walls[wall_id]["fields"]
            if int(wall.get("next_sector", -1)) >= 0:
                continue
            after = level.walls[int(wall["point2"])]["fields"]
            #: on the back wall's line, not a jamb
            on_back = ((ax == bx == int(wall["x"]) == int(after["x"]))
                       or (ay == by == int(wall["y"]) == int(after["y"])))
            if on_back:
                wall["picnum"] = int(front["pilaster"])
                painted += 1
    return painted
