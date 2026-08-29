"""The prop catalogue, loaded from measurement, plus how to mount one.

Owner: "that style, decorations and sprites selection is still hit and
miss -- get better understanding of style combination and what it suppose
to mean and be used for."  Three faults, all of them measurable, and all
of them caused by mining MARGINALS instead of the joint distribution:

**1. We drew from a third of the vocabulary.**  `tools/mine_prop_catalogue.py`
classifies all 263 props the campaign uses more than rarely by their own
cstat alignment bits: 142 are **wall-aligned** (they lie flat on a wall --
paintings, posters, signs, windows), 77 stand on the floor, 40 are floor
decals, 4 are brackets.  The old dressing pass excluded wall-aligned tiles
outright because it had no wall anchor, so more than half of Blood's
decoration was unreachable and rooms got blood and crates instead.

**2. We lit rooms with sprites; Blood lights them with shade.**  Only
**3%** of campaign rooms contain a light-emitting prop (shade <= -20).  We
had put a brazier in essentially every venue and church room.

**3. We chose props by a ceiling-tile lookup, not by what goes with what.**
`tools/mine_style_combinations.py` mines the joint distribution and gives
each prop the surfaces it actually keeps company with, by PMI over a
support floor.  That is what a prop MEANS:

    580  candelabra      wall:100 (n=23), wall:119 (n=8)   our parlor, our theatre
    269  framed painting ceiling:40 (n=6)                  our saloon, our shop
    965  window view     ceiling:454 (n=8)                 our common interiors
    1701 chandelier      floor:110 (n=6)                   our church
    54/694/672           floor:568, ceiling:255            our sewer
    540  dead tree       outdoors, hug 0.18, sky 0.61      the cemetery

`ASSOCIATIONS` below is read from that mining, not typed in.
"""

from __future__ import annotations

import hashlib

import json
import math
import pathlib

PLAYER_HEIGHT = 16960
_REF = pathlib.Path(__file__).resolve().parents[1] / "references"

with (_REF / "prop-catalogue.json").open(encoding="utf-8") as handle:
    CATALOGUE = {int(k): v for k, v in json.load(handle).items()}

with (_REF / "style-combinations.json").open(encoding="utf-8") as handle:
    _COMBOS = json.load(handle)

#: surface key ("wall:108") -> [(pmi, n, tile)], strongest first.
ASSOCIATIONS: dict[str, list[tuple[float, int, int]]] = {}
for _prop, _rows in _COMBOS["prop_associations"].items():
    for _row in _rows:
        ASSOCIATIONS.setdefault(_row["surface"], []).append(
            (_row["pmi"], _row["n"], int(_prop)))
for _key in ASSOCIATIONS:
    ASSOCIATIONS[_key].sort(reverse=True)

#: A tile that is really a SURFACE, occasionally pressed into service as a
#: sprite (a board over a hole, a panel).  Mechanically detected: used 200+
#: times as a wall/floor/ceiling picnum campaign-wide.  Tile 68 has 5,197
#: such uses and 568 has 10,151, and both were turning up as free-standing
#: decoration in our rooms -- a wall texture standing in the middle of a
#: bar.  Using one as a prop is an authored trick, not something a
#: dressing pass should reach for.
with (_REF / "surface-tiles.json").open(encoding="utf-8") as handle:
    SURFACE_TILES = {int(k) for k in json.load(handle)}

#: Blood's alphabet: tiles 3808 (`A`) to 3833 (`Z`).  These are a TEXT
#: primitive, not decoration, and the association miner had no way to know
#: it -- so the dressing pass was scattering single random letters through
#: the sewer as grime.  They belong to `signage.py` and to nothing else.
ALPHABET = range(3808, 3834)

#: The six key emblems -- 2540 skull, 2541 eye, 2542 flame, 2543 dagger,
#: 2544 spider, 2545 moon.  `knowledge/blood/design/keys-v1.json` (mined by
#: the authoring-loop agent across 43 maps) shows what they are for: they
#: are **placards**, hung beside a door that needs that key, and 80% of the
#: campaign's 265 keyed things carry one.  The emblem is the message.
#:
#: This pass had placed the eye and the flame as wall ornaments in a city
#: with no keyed door anywhere -- a sign promising a lock that does not
#: exist.  They belong to `keysign.py` and to nothing else.
KEY_EMBLEMS = frozenset(range(2540, 2546))

#: Aquatic tiles, from `bloodmap.furniture.wet_only()`.  They are weed and
#: bubbles, and `rules_blood.aquatic-sprite-is-under-water` wants the
#: sector's XSECTOR `underwater` flag -- not merely a shallow `depth`.
#: Gravesend has no true underwater volume, so nothing here may use them.
def _wet_only():
    from bloodmap.furniture import wet_only
    return frozenset(wet_only())


WET_ONLY = _wet_only()

#: Terrain.  This one is a judgement, not a measurement, and is written
#: down as such: rocks and boulders genuinely co-occur with plank walls in
#: the campaign (they share rustic and cave spaces), so association alone
#: put a boulder on the saloon's bar.  Co-occurrence is not meaning, and no
#: statistic in the corpus separates "rock" from "furniture".
TERRAIN = {805, 808, 809, 810, 2621}

#: A prop that emits light.  Blood puts one in 3% of its rooms.
LIGHTS = {tile for tile, spec in CATALOGUE.items() if spec["shade"] <= -20}

#: The campaign's own rates, for rooms of at least a plan unit square and
#: over 1.2 player heights: 12% carry grime, and when they do the count
#: runs median 2 / p75 3 / p90 5.
GRIME_ROOM_SHARE = 0.12
GRIME_COUNTS = (1, 1, 2, 2, 2, 3, 3, 4, 5, 5, 7)

FLAME = 506           # the one true bracket: hug 0.92, shade -128
STREET_LAMP = 640     # stands on the ground, 62% of it outdoors
CANDELABRA = 580
DEAD_TREE = 540
CHANDELIER = 1701

# A wall sprite has no depth buffer separation from another sprite hung on the
# same plane.  Keeping their anchors at least one player body width apart avoids
# view-angle-dependent painter-order flicker while still allowing a deliberately
# dense authored composition to opt out at the direct layout level.
MIN_WALL_PROP_SPACING = 384


def fields(tile: int, **overrides) -> dict:
    """The sprite fields the campaign gives this tile."""
    spec = CATALOGUE[tile]
    out = {"type": 0, "picnum": tile, "cstat": spec["cstat"],
           "x_repeat": spec["x_repeat"], "y_repeat": spec["y_repeat"],
           "shade": spec["shade"], "status": 0}
    out.update(overrides)
    return out


def height_of(tile: int) -> float:
    return CATALOGUE[tile]["height"]


def kind_of(tile: int) -> str:
    return CATALOGUE[tile]["kind"]


def props_for(wall: int, floor: int, ceiling: int, *, limit: int = 8,
              exclude_lights: bool = True, sky: bool | None = None) -> list[int]:
    """The props the campaign actually keeps in a room made of these.

    Empty is a legitimate answer, and a common one: most surfaces have no
    prop associated with them above the support floor, which is exactly
    why 88% of campaign rooms are bare.

    `sky` gates on context, which association alone cannot supply: tile 540
    is a dead tree, it associates strongly with plank walls, and it turned
    up inside the saloon the first time this ran.  The catalogue records
    each prop's `sky_share` -- 540 is 0.61, a tree stands outdoors; 269, a
    framed painting, is 0.00 and never does.
    """
    seen: dict[int, float] = {}
    for key in (f"wall:{wall}", f"floor:{floor}", f"ceiling:{ceiling}"):
        for pmi, _n, tile in ASSOCIATIONS.get(key, []):
            if tile not in CATALOGUE:
                continue
            if exclude_lights and tile in LIGHTS:
                continue
            if (tile in SURFACE_TILES or tile in TERRAIN
                    or tile in ALPHABET or tile in KEY_EMBLEMS
                    or tile in WET_ONLY):
                continue
            share = CATALOGUE[tile]["sky_share"]
            if sky is True and share < 0.25:
                continue          # an indoor prop left out in the road
            if sky is False and share > 0.50:
                continue          # a tree in the saloon
            seen[tile] = max(seen.get(tile, -99), pmi)
    return [t for t, _ in sorted(seen.items(), key=lambda kv: -kv[1])][:limit]


def room_rect(room):
    """A room's bounding rectangle in WORLD units.

    Taken from the object itself, not from a module's table: an assembly
    can carry a frame offset (the sewer currently uses the city frame), and
    a rect computed from local coordinates lands outside its sector.

    Accepts either a levelprog Room (`world_outline`) or a compiled layout
    region (`outer`) -- the dressing pass holds the latter, and every
    wall-aligned prop it tried to hang was failing on the difference.
    """
    outline = (room.world_outline() if hasattr(room, "world_outline")
               else list(room.outer))
    xs = [pt[0] for pt in outline]
    ys = [pt[1] for pt in outline]
    return (min(xs), min(ys), max(xs), max(ys))


def free_local(region, local, *, tries=25):
    """A local this region really contains, starting from the one asked for.

    A room that has been furnished is a room with holes in it, and a table
    of hand-chosen locals written before the furniture arrived will land on
    it.  Rather than move the numbers every time a template changes, ask.
    Returns None if nothing in the room is free.
    """
    from dressing import _free_point
    if _free_point(region, *local) is not None:
        return tuple(local)
    u0, v0 = float(local[0]), float(local[1])
    for step in range(1, tries):
        radius = 0.06 * step
        for du, dv in ((0, radius), (0, -radius), (radius, 0), (-radius, 0),
                       (radius, radius), (-radius, -radius),
                       (radius, -radius), (-radius, radius)):
            u, v = min(0.92, max(0.08, u0 + du)), min(0.92, max(0.08, v0 + dv))
            if _free_point(region, u, v) is not None:
                return (u, v)
    return None


def place_id(room) -> str:
    """A room's identity as a PLACE rather than as a label.

    `Room.region_id` is `"region:" + path()`, so it changes the moment a
    room moves in the tree -- and any pass seeded from it reshuffles when
    the program is reorganised, which makes a restructure impossible to
    tell apart from a redesign.  A place is where it is: its world outline
    and its floor.  Move the same room to a different parent and this is
    unchanged; move the room itself and it changes, which is correct.
    """
    outline = (room.world_outline() if hasattr(room, "world_outline")
               else list(getattr(room, "outer", ())))
    floor = int(getattr(room, "floor_z", 0) or 0)
    blob = repr((sorted((int(x), int(y)) for x, y in outline), floor))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def face_segment(rect, face: str, *, inset: int = 256):
    """The wall segment of one face of a rectangular room.

    Wound so the region lies to the segment's left, which is what
    `place_on_wall` needs to face a prop into the room.  Inset ALONG the
    face only -- insetting perpendicular to it as well put the segment
    inside the room, and anchors resolved against it landed on whatever
    wall the engine found, portals included.
    """
    x0, y0, x1, y1 = (int(v) for v in rect)
    return {
        "north": ((x0 + inset, y0), (x1 - inset, y0)),
        "east":  ((x1, y0 + inset), (x1, y1 - inset)),
        "south": ((x1 - inset, y1), (x0 + inset, y1)),
        "west":  ((x0, y1 - inset), (x0, y0 + inset)),
    }[face]


def mount_on_wall(layout, placement_id: str, room, face: str,
                  tile: int = FLAME, *, t: float = 0.5,
                  emits_light: bool | None = None,
                  light_intensity: float | None = None,
                  required: bool = False, **overrides):
    """Hang a prop on one face of a rectangular room, at its own height.

    Returns None when the wall has no free rectangle this size -- a full
    wall is a legitimate answer for decoration, and the alternative is
    hanging the prop through whatever is already there.  Pass
    `required=True` for something that must appear.

    A flame is also an authored lighting source unless the caller explicitly
    says otherwise.  This keeps the visual prop and the LightBomb source in one
    declaration instead of rediscovering light from tile ids in a finishing
    pass.
    """
    import wallplane

    a1, a2 = face_segment(room_rect(room), face)
    region_id = getattr(room, "region_id", None) or room.id
    if emits_light is None:
        emits_light = tile == FLAME
    spec = fields(tile, **overrides)
    # A wall is a 2D surface, and this asks it for a free rectangle the size
    # of the thing being hung -- along AND down, so a prop may stack above or
    # below another one but may not cover it.  What this replaced reserved a
    # flat 384 units of the supporting LINE around every existing anchor,
    # which is the same reservation for a 128-wide decal and a 2,048-wide
    # hanging, and no reservation at all in z.
    got = wallplane.sprite(
        layout, placement_id, region_id, a1, a2,
        tile=tile, x_repeat=spec["x_repeat"], y_repeat=spec["y_repeat"],
        cstat=spec["cstat"], t=t,
        height_player_heights=height_of(tile),
        offset_player_widths=0.10,
        emits_light=emits_light, light_intensity=light_intensity,
        shade=spec["shade"], status=spec.get("status", 0),
        **{k: v for k, v in spec.items()
           if k not in ("type", "picnum", "cstat", "x_repeat", "y_repeat",
                        "shade", "status")})
    if got is None and required:
        raise WallFull(
            f"{placement_id}: no free rectangle on {face} of "
            f"{region_id} for tile {tile}")
    return got


class WallFull(ValueError):
    """This wall has no free rectangle the size of the thing being hung."""


def safe_wall_fraction(layout, region_id: str, a1, a2, preferred: float,
                       *, spacing: float = MIN_WALL_PROP_SPACING) -> float:
    """One-dimensional anchor spacing.  Superseded by `wallplane`.

    Kept because `runs.py` and a couple of direct callers still reach for
    it, and because it documents what was wrong: it reserves a fixed run of
    the supporting LINE and knows nothing about how wide or tall the sprite
    is, nor about z at all.  Prefer `wallplane.find_slot`, which reserves
    the rectangle the sprite actually draws.

    Wall-aligned sprites are coplanar by design.  If two placements overlap on
    one wall, Build's painter order can make them swap in front of each other as
    the view moves.  Existing wall anchors on that physical wall (including
    signs and anchors whose logical regions compile into one sector) therefore
    reserve a short run of their supporting line.  This is only an automatic
    safeguard for ordinary props; a specialised composition can call
    ``layout.place_on_wall`` directly and state its own layering deliberately.
    """
    ax, ay = (float(a1[0]), float(a1[1]))
    bx, by = (float(a2[0]), float(a2[1]))
    dx, dy = bx - ax, by - ay
    length = math.hypot(dx, dy)
    if length <= 1.0:
        return float(preferred)
    ux, uy = dx / length, dy / length

    reserved: list[float] = []
    for placement in layout.placements:
        if not placement.anchor:
            continue
        anchor = placement.anchor
        if anchor.get("kind") != "wall":
            continue
        px = float(anchor["a1"][0]) + (
            float(anchor["a2"][0]) - float(anchor["a1"][0])
        ) * float(anchor.get("t", 0.5))
        py = float(anchor["a1"][1]) + (
            float(anchor["a2"][1]) - float(anchor["a1"][1])
        ) * float(anchor.get("t", 0.5))
        # The point must lie on this infinite supporting line and within this
        # segment's useful extent.  That also catches a sign whose segment is a
        # differently inset copy of the same wall.
        normal = abs((px - ax) * uy - (py - ay) * ux)
        along = (px - ax) * ux + (py - ay) * uy
        if normal <= 1.0 and -spacing <= along <= length + spacing:
            reserved.append(along)
    if not reserved:
        return max(0.0, min(1.0, float(preferred)))

    candidates = [max(0.12, min(0.88, float(preferred)))]
    candidates.extend(i / 10 for i in range(1, 10))
    best = max(
        candidates,
        key=lambda value: min(abs(value * length - other) for other in reserved),
    )
    return float(best)


def stand_on_floor(layout, placement_id: str, region_id: str,
                   local=(0.5, 0.5), tile: int = STREET_LAMP,
                   **overrides) -> str:
    """Stand a prop on the floor at its measured height."""
    return layout.place_on_floor(
        placement_id, region_id, local=local,
        height_player_heights=height_of(tile),
        **fields(tile, **overrides))


def solid_faces(layout, region_id: str, rect) -> list[str]:
    """Which of a rectangular room's four faces carry no portal.

    A prop hung on a two-sided wall has nothing behind it, and the
    compiler rightly refuses: "wall sprites hang over an opening".  The
    layout knows where every portal is before it compiles -- each
    `ConnectionSpec` carries the span it occupies -- so the honest way to
    choose a wall is to ask, rather than to guess a face and hope.
    """
    x0, y0, x1, y1 = (int(v) for v in rect)
    # "A rectangular room's four faces" is a precondition, and it was never
    # checked.  The light pools are diamonds: their four edges are all
    # portals to the street, but none of them lies on a bounding-box line,
    # so every face read as solid and a prop hung on one landed outside the
    # sector -- which the compiler catches, several hundred sprites later,
    # as "sprite position is outside its sector".  A room that is not an
    # axis-aligned rectangle offers no compass face to hang anything on.
    region = getattr(layout, "regions", {}).get(region_id)
    if region is not None:
        outer = [(int(px), int(py)) for px, py in region.outer]
        if len(outer) != 4 or {(px, py) for px, py in outer} != {
                (x0, y0), (x1, y0), (x1, y1), (x0, y1)}:
            return []
    lines = {"north": ("y", y0), "south": ("y", y1),
             "west": ("x", x0), "east": ("x", x1)}
    used = set()
    for connection in layout.connections.values():
        if region_id not in (connection.region_a, connection.region_b):
            continue
        a1, a2 = connection.a1, connection.a2
        if a1 is None or a2 is None:
            continue
        for face, (axis, value) in lines.items():
            index = 0 if axis == "x" else 1
            if abs(a1[index] - value) <= 1 and abs(a2[index] - value) <= 1:
                used.add(face)
    return [face for face in ("north", "east", "south", "west")
            if face not in used]
