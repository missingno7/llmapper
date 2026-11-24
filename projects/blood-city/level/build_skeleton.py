"""Phase 1c: derive the L2 massing skeleton from the L1 schematic plan.

This file is a *generator*, not a level: it reads level/city_plan.py (L1)
and level/resolution.py (the class->units table) and emits the massing
geometry through the levelprog grammar -- district assemblies with inherited
style, one street region per district with blocks carved as holes (the E2M6
precedent), the sewer at depth under Foundry Ward as declared true-ROR
stacks, and the two sewer entries walkable.  No facades, no interiors, no
dressing.  A hand edit to its output is a bug by definition
(references/design-layers.md).

    python projects/blood-city/level/build_skeleton.py

writes level/city-skeleton.MAP and refreshes level/blood-city-current.MAP.
"""

from __future__ import annotations

import collections
import pathlib
import sys
import time
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from bloodmap import motion
from bloodmap.format import write_map
from bloodmap.levelprog import Frame, LevelProgram, RECT_FACES, Style
from bloodmap.roomoverroom import (
    MARKER_UP_STACK, MARKER_LOW_STACK, MIRROR_TILE,
)

#: NOT bloodmap.roomoverroom.MARKER_TILE (3997).  Censused across the whole
#: campaign: all 273 link markers use picnum **2332 on the upper half and
#: 2331 on the lower**, 100% of instances of every family (link 6/7,
#: water 9/10, stack 11/12).  This project's own working example agrees --
#: reasoned-authoring-v1's water links are 2332/2331.  Tile 3997 is drawn
#: by XMapEdit as a torch, which is exactly what a map built with it looks
#: like in the editor: a normal sector with a torch instead of a link.
MARKER_TILE_UPPER = 2332
MARKER_TILE_LOWER = 2331

#: NOT bloodmap.roomoverroom.MARKER_STATNUM (10 = kStatMarker).  Read from
#: NBlood: db.cpp `PropagateMarkerReferences` walks every sprite on
#: kStatMarker and DeleteSprite()s any whose type is not kMarkerOff/Axis/
#: WarpDest/On -- which includes kMarkerUpStack(11) and kMarkerLowStack(12).
#: It runs at the end of dbLoadMap (db.cpp:1325); warpInit runs later, at
#: level start (blood.cpp:750).  So a stack marker placed on statnum 10 is
#: deleted before the link is ever registered: no link, solid floor, no way
#: down.  All six stack markers in E3M1 sit on statnum 0 with cstat 128,
#: and warpInit sets the invisible bit itself.  Filed as a grammar request.
STACK_MARKER_STATNUM = 0        # kStatDecoration
STACK_MARKER_CSTAT = 128        # the campaign's stored value

from bloodmap.rules_blood import MIRROR_TILE
import city_plan
from city_plan import plan
from facade_pass import BAY as FACADE_BAY, snap_opening


#: How far a lamp post keeps from a door: a body and a half each way.
LAMP_DOOR_CLEAR = 1536


def facade_pass_bay() -> int:
    return FACADE_BAY
from resolution import (
    CELLAR_DROP, CELLAR_FLOOR, DISTRICT_STYLE, GRADE, PIT_LANDING_DEPTH, PU,
    SEWER_CHAMBER_CLEAR, SEWER_CLEAR, SEWER_FLOOR, SEWER_CITY_D, SKY_TILE,
    STREET_SKY, WIDTH_UNITS,
    FLOOR_BOARDWALK, FLOOR_GROUND,
)
from materials import FACADES, INTERIORS, MASONRY, SEWER, SEWER_WET

COMPASS = dict(zip(RECT_FACES, range(4)))

#: District bounds in units, seamed on street centerlines (derived from the
#: same L1 grid the plan states; nothing here is a fresh literal).
SEAM_ROW = (city_plan.Y_ROWST + city_plan.ROW / 2) * PU
SEAM_MARKET = (city_plan.Y_MARKST + city_plan.STREET / 2) * PU
SEAM_AVENUE = (city_plan.X_AVENUE + city_plan.AVENUE / 2) * PU
#: The light the finished map is drawn in, last of all:
#:
#: * "model" -- the map lit as a 3D scene (`bloodmap.light_stage`): lights of
#:   the kind each place wants, in rows (`level/lights.py`), sun, lamps and a
#:   bounce traced, floors and long walls cut where their light changes,
#:   every shade written, one sky. The owner walked it on 2026-11-21 ("It is
#:   good") and asked that it not make the map harder to change: it is
#:   derived from the finished map on every build, never written into the
#:   layout, and "faces" or None builds the map without it.
#: * "faces" -- each building's tone and a step by facing
#:   (`bloodmap.sunlight.apply`), the pass before it.
#: * None -- the shades the passes set.
LIGHTING = "model"
#: EXPERIMENTAL, off. The sun's shadow on the open ground
#: (`bloodmap.sunlight.cast_shadows`), laid as overlays cut into the finished
#: map (`bloodmap.overlays`). The owner, 2026-11-20: "keep that shadows
#: sector splitting as separate experimental thing for now" -- it was not
#: walked by him. Known when it was set aside: shadows fall where masses
#: throw them (work/shadow/check_plan.py: 0 of 848 shadow points without a
#: caster), a blind reader preferred it in 19 of 23 street views, but the
#: city-wide sunlit shift took the sea from 38 to 24 (the harbour study's
#: floor), and pieces break tests that find a place by one sector (the ship's
#: deck, the jetty, a crate). The read-back gate does not run on the cut map.
GROUND_SHADOWS = False
#: (shadow, sunlit) floor shade offsets when it is on
GROUND_SUN = (12, -14)
CITY_W = city_plan.CITY_W * PU
CITY_D = city_plan.CITY_D * PU

#: E3M1 s0/s339/s343: the shade of an end wall's face.
END_WALL_SHADE = -8

DISTRICT_BOUNDS = {
    "theatre_row": (0, 0, SEAM_AVENUE, SEAM_ROW),
    "old_crossing": (0, SEAM_ROW, SEAM_AVENUE, SEAM_MARKET),
    "foundry_ward": (SEAM_AVENUE, 0, CITY_W, SEAM_MARKET),
    "market_slip": (0, SEAM_MARKET, CITY_W, CITY_D),
}

#: Sewer chamber footprints (units); corridors take the alley width.
CHAMBER = {"junction": (5120, 6144), "cistern": (6144, 4096)}
CORRIDOR_W = WIDTH_UNITS["alley"]
SHAFT = 1024
#: Works stair: 8 + 3 risers of 4096 = CELLAR_DROP; treads chosen so each
#: flight's run is a whole number of units bridging its rooms exactly.
UPPER_STEPS, UPPER_TREAD = 8, 512
LOWER_STEPS, LOWER_TREAD = 3, 1024
assert (UPPER_STEPS + LOWER_STEPS) * 4096 == CELLAR_DROP


GRID = 256

#: The manhole pit: a bump of the works hole into the yard, derived from the
#: L1 drop-entry position (its shaft pair must be exact-coincident -- the
#: only stacked form the geometry audit accepts today; grammar request #6).
def _manhole_tab():
    entry = next(e for e in city_plan.SEWER["entries"] if e["form"] == "drop")
    ex, ey = int(entry["at"][0] * PU), int(entry["at"][1] * PU)
    return (ex - 512, ey - 512, ex + 512, ey + 512)

MANHOLE_TAB = _manhole_tab()


#: How far back a building's outside corner is cut.  Gravesend measured at
#: **7% diagonal walls** against E3M1's 35%, DukCity's 23-34% and TEDE1M2's
#: 32% -- and 72% of its sectors were plain axis-aligned rectangles against
#: their 30-59%.  We were three to five times more rectangular than any
#: reference.  A chamfered corner is where most of a Build city's diagonals
#: come from, and it costs one wall per corner.
CHAMFER = 512


def chamfer_corners(loop, size=CHAMFER):
    """Cut back every convex corner of a traced mass outline.

    Only convex corners -- the ones that stick out into the street -- and
    only where both edges are long enough to lose `size` and still exist.
    """
    n = len(loop)
    if n < 4:
        return loop
    area = sum(loop[i][0] * loop[(i + 1) % n][1] - loop[(i + 1) % n][0] * loop[i][1]
               for i in range(n))
    turn = 1 if area > 0 else -1
    out = []
    for i in range(n):
        a, b, c = loop[i - 1], loop[i], loop[(i + 1) % n]
        v1 = (b[0] - a[0], b[1] - a[1])
        v2 = (c[0] - b[0], c[1] - b[1])
        cross = v1[0] * v2[1] - v1[1] * v2[0]
        len1 = abs(v1[0]) + abs(v1[1])
        len2 = abs(v2[0]) + abs(v2[1])
        if (cross * turn > 0 and len1 >= 2 * size and len2 >= 2 * size):
            u1 = (0 if v1[0] == 0 else (1 if v1[0] > 0 else -1),
                  0 if v1[1] == 0 else (1 if v1[1] > 0 else -1))
            u2 = (0 if v2[0] == 0 else (1 if v2[0] > 0 else -1),
                  0 if v2[1] == 0 else (1 if v2[1] > 0 else -1))
            out.append((b[0] - u1[0] * size, b[1] - u1[1] * size))
            out.append((b[0] + u2[0] * size, b[1] + u2[1] * size))
        else:
            out.append(b)
    return out


def mass_outline(rect_pu, notch_rects_pu, refill_rects_units=(), chamfer=True):
    """A rectangle minus a union of rectangles, as one exact polygon.

    Every L1 coordinate is a multiple of 0.25 pu = 256 units, so the region
    is traced on a 256-unit cell grid with no rounding: fill the rectangle,
    subtract the notches, walk the boundary, merge collinear runs.  Handles
    every composition the plan produces -- mid-edge bites, corner bites, and
    solids attached to other solids (the church with its mausoleum row).
    The region must be simply connected (no enclosed courts -- those are
    holes, carved separately)."""
    x0, y0, x1, y1 = (int(v * PU) for v in rect_pu)
    cols = (x1 - x0) // GRID
    rows = (y1 - y0) // GRID
    filled = [[True] * cols for _ in range(rows)]
    for notch in notch_rects_pu:
        nx0, ny0, nx1, ny1 = (int(v * PU) for v in notch)
        for r in range(max(0, (ny0 - y0) // GRID), min(rows, (ny1 - y0) // GRID)):
            for c in range(max(0, (nx0 - x0) // GRID), min(cols, (nx1 - x0) // GRID)):
                filled[r][c] = False

    for refill in refill_rects_units:
        nx0, ny0, nx1, ny1 = (int(v) for v in refill)
        for r in range((ny0 - y0) // GRID, (ny1 - y0) // GRID):
            for c in range((nx0 - x0) // GRID, (nx1 - x0) // GRID):
                if 0 <= r < rows and 0 <= c < cols:
                    filled[r][c] = True

    def cell(r, c):
        return 0 <= r < rows and 0 <= c < cols and filled[r][c]

    segments = defaultdict(list)
    def add(a, b):
        segments[a].append(b)
        segments[b].append(a)
    for r in range(rows):
        for c in range(cols):
            if not filled[r][c]:
                continue
            px, py = x0 + c * GRID, y0 + r * GRID
            if not cell(r - 1, c):
                add((px, py), (px + GRID, py))
            if not cell(r + 1, c):
                add((px, py + GRID), (px + GRID, py + GRID))
            if not cell(r, c - 1):
                add((px, py), (px, py + GRID))
            if not cell(r, c + 1):
                add((px + GRID, py), (px + GRID, py + GRID))

    start = min(segments)
    loop = [start]
    prev = None
    current = start
    while True:
        options = [p for p in segments[current] if p != prev]
        # At a corner-touch there can be two continuations; prefer the one
        # that keeps turning (either is a valid boundary; the plan produces
        # no pinch points, asserted by closure below).
        nxt = options[0]
        if nxt == start and len(loop) > 2:
            break
        loop.append(nxt)
        prev, current = current, nxt
        if len(loop) > rows * cols * 8:
            raise ValueError("boundary trace did not close; region not simply connected")
    cleaned = []
    for p in loop:
        if len(cleaned) >= 2:
            a, b = cleaned[-2], cleaned[-1]
            if (a[0] == b[0] == p[0]) or (a[1] == b[1] == p[1]):
                cleaned[-1] = p
                continue
        cleaned.append(p)
    # Close-the-loop collinearity: a vertex is redundant if its two loop
    # neighbours share its x or its y.
    changed = True
    while changed and len(cleaned) > 4:
        changed = False
        last, first, second = cleaned[-1], cleaned[0], cleaned[1]
        if (last[0] == first[0] == second[0]) or (last[1] == first[1] == second[1]):
            cleaned.pop(0)
            changed = True
            continue
        prev2, last, first = cleaned[-2], cleaned[-1], cleaned[0]
        if (prev2[0] == last[0] == first[0]) or (prev2[1] == last[1] == first[1]):
            cleaned.pop()
            changed = True
    return chamfer_corners(cleaned) if chamfer else cleaned



def alley_notch_rect(alley, block_rect):
    """A dead-end alley as a notch rect on its block, from the L1 record."""
    x0, y0, x1, y1 = block_rect
    width = WIDTH_UNITS[alley["width_class"]] / PU
    depth = alley["depth_pu"]
    if alley["edge"] == "north":
        cx = x0 + (x1 - x0) * alley["at"]
        return (cx - width / 2, y0, cx + width / 2, y0 + depth)
    if alley["edge"] == "west":
        cy = y0 + (y1 - y0) * alley["at"]
        return (x0, cy - width / 2, x0 + depth, cy + width / 2)
    if alley["edge"] == "south":
        cx = x0 + (x1 - x0) * alley["at"]
        return (cx - width / 2, y1 - depth, cx + width / 2, y1)
    if alley["edge"] == "east":
        cy = y0 + (y1 - y0) * alley["at"]
        return (x1 - depth, cy - width / 2, x1 + depth * 0, cy + width / 2)
    raise ValueError(alley["edge"])


class _Stages:
    """The build's stages in the order they run, each one timed.

    A stage starts at a `STAGE("name", "what it does")` line and ends at the
    next. Nothing is moved into a function for it: the call marks a place in
    a two-thousand-line build so an agent can be told "the windows are made
    in `doors-and-windows`" and open the file there. `status.py --stages`
    lists them with their lines; the names that ran go into the manifest and
    the seconds into `work/`, which is not committed, so a build that makes
    the same map writes the same manifest.
    """

    def __init__(self) -> None:
        self.rows: list[dict] = []
        self._since = time.perf_counter()

    def begin(self) -> None:
        self.rows, self._since = [], time.perf_counter()

    def __call__(self, name: str, says: str) -> None:
        now = time.perf_counter()
        if self.rows:
            self.rows[-1]["seconds"] = round(now - self._since, 2)
        self.rows.append({"name": name, "says": says})
        self._since = now

    def close(self) -> list[dict]:
        """End the last stage; what ran, without the seconds."""
        if self.rows and "seconds" not in self.rows[-1]:
            self.rows[-1]["seconds"] = round(time.perf_counter() - self._since, 2)
        return [{"name": row["name"], "says": row["says"]} for row in self.rows]


STAGE = _Stages()

#: Where the underpass's bars stand, set as the passage is built.
UNDERPASS: dict = {}


def build():
    STAGE.begin()
    STAGE("districts",
          "the plan as district assemblies: one street region each, blocks carved out")
    # The level's wiring, declared: `wires.py` names every wire and what it
    # is for; each module declares the ends where it builds them.
    import wires as _wires
    _wires.begin()
    import glass as _glass
    _glass.FRONTS.clear()
    data = plan()
    city = LevelProgram(
        "gravesend", name="blood-city-skeleton", visibility=800,
        style=Style(wall_picnum=DISTRICT_STYLE["market_slip"]["wall_picnum"],
                    floor_picnum=FLOOR_BOARDWALK, ceiling_picnum=SKY_TILE,
                    parallax_ceiling=True, floor_z=GRADE,
                    clear_height=STREET_SKY, floor_shade=32, layer="street"),
    )
    import l3_church
    l3_church.declare_layers(city)
    # The street's band reaches to the top of the one thing taller than its
    # sky: St Gallow's tower, whose ring of raised sky stands on the street.
    city.declare_layer("street",
                       ceiling_z=GRADE - max(STREET_SKY, l3_church.TOWER_HEIGHT),
                       floor_z=16384,
                       note="the open city at grade")
    # The sea lies 1.75 bodies under the quay (the harbour study), which is
    # deeper than the street's band goes: it is a layer of its own, open to
    # the same sky.
    city.declare_layer("sea",
                       ceiling_z=GRADE - max(STREET_SKY, l3_church.TOWER_HEIGHT),
                       floor_z=GRADE + 29696 + 4096,
                       note="the harbour's water and its horizon")
    city.declare_layer("sewer", ceiling_z=SEWER_FLOOR - SEWER_CHAMBER_CLEAR,
                       floor_z=SEWER_FLOOR + 4096,
                       note="the wet undercity beneath Foundry Ward")
    import l3_sewer as _l3_sewer_layers
    city.declare_layer(_l3_sewer_layers.HALL_LAYER,
                       ceiling_z=SEWER_FLOOR - _l3_sewer_layers.WALK_CLEAR,
                       floor_z=_l3_sewer_layers.HALL_WATER,
                       note="the settling hall under the plaza: tanks below the sewer's level")
    import cabal_rite
    city.declare_layer(cabal_rite.LAYER, ceiling_z=cabal_rite.SHAFT, floor_z=cabal_rite.FLOOR + 1024,
                       note="the Cabal's storm chamber behind the settling hall")
    import arcade
    city.declare_layer(arcade.LAYER, ceiling_z=arcade.SKY, floor_z=arcade.COURT,
                       note="the Gravesend Arcade's court, a body and a half below the street")
    import phantom_terminus
    city.declare_layer("ghost_station", ceiling_z=SEWER_FLOOR - 24576,
                       floor_z=phantom_terminus.WATER_FLOOR,
                       note="the Phantom Terminus and its descending service stair")

    areas = {a["id"]: a for a in data["areas"]}
    alleys = {a["id"]: a for a in data["dead_end_alleys"]}

    streets = {}
    district_of = {}
    for district, bounds in DISTRICT_BOUNDS.items():
        bx0, by0, bx1, by1 = bounds
        facade = FACADES[district]
        # The district's frame lives on its STREET, not on the district.
        # A district is a grouping -- the thing that sits at (bx0, by0) is
        # the street.  Putting the offset on the assembly meant everything
        # later nested inside it (its venues, its light pools, its stair)
        # would have to be restated in district-local coordinates, and the
        # first thing that happened when the venues moved in was that the
        # whole of Old Crossing slid by its own origin.
        # `floor_shade` is the PAVEMENT's, not the district's, and it stays
        # on the street for the same reason the frame does: everything now
        # nested in the district would otherwise inherit the brightness of
        # the road it stands beside.  The facade wall and the ground tile do
        # belong to the district -- they are its register, and an interior
        # that wants its own restates them, which every one of them does.
        district_style = {key: value
                          for key, value in DISTRICT_STYLE[district].items()
                          if key != "floor_shade"}
        assembly = city.assembly(
            district,
            style=Style(**district_style),
            note=data["districts"][district],
        )
        # The street is the exterior layer of every doorway/window sandwich.
        # Its portal-side record continues the facade; the thin porch, door
        # frame or display volume behind it owns the distinct jamb material.
        # Otherwise each portal splits a long street face with an opening-tile
        # stripe (wall 733 was the visible example).
        room = assembly.room(
            "streets",
            [(0, 0), (bx1 - bx0, 0), (bx1 - bx0, by1 - by0), (0, by1 - by0)],
            role="exterior", faces=dict(COMPASS),
            frame=Frame(int(bx0), int(by0)),
            region_kwargs=facade.facade_region_kwargs(),
            intent={"district": district},
        )
        room.surfaces(floor_shade=DISTRICT_STYLE[district]["floor_shade"])
        for block in data["blocks"]:
            if block["district"] != district or block.get("inside_area"):
                continue
            notches = []
            for notch_id in block["notches"]:
                if notch_id in areas:
                    notches.append(areas[notch_id]["rect"])
                elif notch_id in alleys:
                    notches.append(alley_notch_rect(alleys[notch_id], block["rect"]))
            outline = mass_outline(block["rect"], notches)
            room.carve([(x - bx0, y - by0) for x, y in outline])
        # A carved area (the cemetery) is its own gated region, not street:
        # its whole footprint leaves the street region here and the area's
        # room is built below.
        for area in data["areas"]:
            if area["district"] == district and area.get("carved"):
                ax0, ay0, ax1, ay1 = (v * PU for v in area["rect"])
                hole = [(ax0, ay0), (ax1, ay0), (ax1, ay1), (ax0, ay1)]
                if area["id"] == "cemetery":
                    # The church's eaves and tower are aprons standing in the
                    # street's space, so the street gives that ground up too.
                    import l3_church
                    hole = l3_church.street_hole((ax0, ay0, ax1, ay1))
                room.carve([(x - bx0, y - by0) for x, y in hole])
        streets[district] = room
        district_of[district] = assembly


    STAGE("cemetery",
          "the cemetery as a walled, gated ground carved from its district")
    # ---- carved areas: the cemetery as a walled, gated ground -------------
    gates = []
    gate_rects: dict = {}
    grounds = {}
    green_reports = {}
    ctx_greens = {}
    for area in data["areas"]:
        if not area.get("carved"):
            continue
        solids = [b["rect"] for b in data["blocks"]
                  if b.get("inside_area") == area["id"]]
        solids += list(area.get("attached_masses", []))
        # The ground sits inside a real wall: inset half a plan-quarter (512
        # units) from the carved footprint on every side, so the boundary is
        # masonry, not a zero-thickness seam; the gates bridge the wall with
        # their own small rooms.
        wall_t = 2 * GRID / PU
        rx0, ry0, rx1, ry1 = area["rect"]
        inset = (rx0 + wall_t, ry0 + wall_t, rx1 - wall_t, ry1 - wall_t)
        outline = mass_outline(inset, solids)
        ground = district_of[area["district"]].assembly(
            area["id"],
            style=Style(**MASONRY.style_kwargs(floor_picnum=FLOOR_GROUND,
                                               floor_shade=34)),
            note=area["note"],
        ).room(
            "ground", outline, role="exterior",
            region_kwargs=MASONRY.region_kwargs(),
            intent={"kind": area["kind"], "district": area["district"]},
        )
        grounds[area["id"]] = ground
        # ---- the green ---------------------------------------------------
        # The cemetery was a flat empty floor wearing tile 352 -- the ROADWAY
        # tile -- behind a lychgate. `park.green` makes it turf, cuts the
        # trodden path across it as its own dirt surface, and `park.plant`
        # fills slots derived from the ground's own size. E1M1's cemetery is
        # the grammar: an enclosed green you enter through a gate.
        if area["kind"] == "cemetery":
            import park

            green_report, green_box, green_area = park.green(
                city, ground, district=district_of[area["district"]],
                grade=GRADE,
                solids=[tuple(int(v * PU) for v in rect) for rect in
                        ([b["rect"] for b in data["blocks"]
                          if b.get("inside_area") == area["id"]]
                         + list(area.get("attached_masses", [])))])
            green_reports[area["id"]] = (green_report, green_box, green_area)
            ctx_greens[area["id"]] = (green_report, green_box, green_area)
        ax0, ay0, ax1, ay1 = (int(v * PU) for v in area["rect"])
        wall_units = int(wall_t * PU)
        # Two bays wide, on the bay grid, so the gate lands between the
        # windows painted on the wall rather than slicing one (the same
        # rule the venue entrances follow).
        gate_w = 2 * facade_pass_bay()
        for gate in area.get("gates", []):
            name = gate["name"].replace(" ", "_").replace("-", "_")
            if gate["edge"] in ("west", "east"):
                y, gate_w = snap_opening(
                    ay0 + (ay1 - ay0) * gate["at"] - gate_w / 2, gate_w)
                gx0 = ax0 if gate["edge"] == "west" else ax1 - wall_units
                frame = Frame(gx0, int(y))
                shape = [(0, 0), (wall_units, 0), (wall_units, gate_w), (0, gate_w)]
            else:
                x, gate_w = snap_opening(
                    ax0 + (ax1 - ax0) * gate["at"] - gate_w / 2, gate_w)
                gy0 = ay0 if gate["edge"] == "north" else ay1 - wall_units
                frame = Frame(int(x), gy0)
                shape = [(0, 0), (gate_w, 0), (gate_w, wall_units), (0, wall_units)]
            gate_room = ground.parent.room(
                f"gate_{name}", shape, role="gateway", faces=dict(COMPASS),
                frame=frame, region_kwargs=MASONRY.region_kwargs(),
                note=f"{gate['name']} through the boundary wall",
            )
            # Raw connections on the two shared edges (the ground's notched
            # outline has no compass faces): outer edge to the street, inner
            # edge to the ground.
            fx, fy = frame.dx, frame.dy
            if gate["edge"] in ("west", "east"):
                outer_x = fx if gate["edge"] == "west" else fx + wall_units
                inner_x = fx + wall_units if gate["edge"] == "west" else fx
                street_span = ((outer_x, fy), (outer_x, fy + gate_w))
                ground_span = ((inner_x, fy), (inner_x, fy + gate_w))
            else:
                outer_y = fy if gate["edge"] == "north" else fy + wall_units
                inner_y = fy + wall_units if gate["edge"] == "north" else fy
                street_span = ((fx, outer_y), (fx + gate_w, outer_y))
                ground_span = ((fx, inner_y), (fx + gate_w, inner_y))
            gate_rects.setdefault(area["id"], []).append(
                (frame.dx, frame.dy, frame.dx + shape[2][0],
                 frame.dy + shape[2][1], gate_room.region_id))
            gates.append((f"connection:{area['id']}_{name}_street",
                          gate_room.region_id,
                          streets[area["district"]].region_id,
                          street_span[0], street_span[1]))
            gates.append((f"connection:{area['id']}_{name}_ground",
                          gate_room.region_id, ground.region_id,
                          ground_span[0], ground_span[1]))

    theatre_st = streets["theatre_row"]
    oldcross_st = streets["old_crossing"]
    foundry_st = streets["foundry_ward"]
    market_st = streets["market_slip"]

    #: THE SEAMS ARE NOT DECLARED HERE ANY MORE.  Five connections used to
    #: join the four district streets along their whole shared edges.  A
    #: carriageway that lies on a seam is now notched out of both streets'
    #: outlines (`streets.lay`), so what two streets share is whatever the
    #: roads leave, and `streets.lay` -- which runs last and knows -- writes
    #: one gate per stretch.

    STAGE("sewer",
          "the sewer declared at depth beneath Foundry Ward")
    # ---- the sewer: directly beneath Foundry Ward --------------------------
    #
    # The sewer occupies the same XY footprint as the city.  Its depth is
    # carried by a distinct layer, not by a parking offset.  The remaining
    # ROR mouths are vertically aligned; the pump station uses physical
    # treads all the way down.
    s = data["sewer"]
    park_dx, park_dy = SEWER_CITY_D
    sewer = city.assembly(
        "sewer", frame=Frame(int(park_dx), int(park_dy)),
        style=Style(**SEWER.style_kwargs(floor_shade=40, floor_z=SEWER_FLOOR,
                                         clear_height=SEWER_CLEAR, layer="sewer")),
        note=s["under_city"]["note"],
    )

    # The trunk and its two chambers: the part of the network that predates
    # the ring, and the part the two street entries actually land in.
    trunk_part = sewer.assembly(
        "trunk", note="the original trunk, its risers and its two chambers")
    mouths_part = sewer.assembly(
        "mouths", note="the lower halves of the two vertical ROR links")

    def sroom(name, x0, y0, x1, y1, note, role="interior", **kw):
        kw.setdefault("region_kwargs", {}).update(SEWER.region_kwargs())
        return trunk_part.room(
            name, [(0, 0), (x1 - x0, 0), (x1 - x0, y1 - y0), (0, y1 - y0)],
            role=role, faces=dict(COMPASS), frame=Frame(int(x0), int(y0)),
            note=note, **kw,
        )

    jx, jy = (v * PU for v in s["nodes"]["junction"])
    jw, jd = CHAMBER["junction"]
    cx, cy = (v * PU for v in s["nodes"]["cistern"])
    cw, cd = CHAMBER["cistern"]
    junction = sroom("junction", jx - jw / 2, jy - jd / 2,
                     jx + jw / 2, jy + jd / 2, "L1 sewer node junction",
                     region_kwargs={"sector_behavior": {
                         "amplitude": -16, "shade_frequency": 8}})
    cistern = sroom("cistern", cx - cw / 2, cy - cd / 2,
                    cx + cw / 2, cy + cd / 2,
                    "L1 sewer node cistern; Phase 4 dive link closes the ring")

    grate_entry = next(e for e in s["entries"] if e["form"] == "drop")
    gx, gy = (int(v * PU) for v in grate_entry["at"])
    stair_entry = next(e for e in s["entries"] if e["form"] == "stair")

    SHAFT_HALF = SHAFT // 2
    trunk_y0, trunk_y1 = gy - SHAFT_HALF, gy + SHAFT_HALF
    main_duct = sroom("main_duct", jx - jw / 2, trunk_y0 - 512,
                      gx - SHAFT_HALF, trunk_y1 + 512,
                      "the trunk; both mouths hang off it (E3M3: wet, "
                      "restless light)",
                      region_kwargs={"floor_picnum": SEWER_WET.floor,
                                     "sector_behavior": {
                                         "amplitude": -20,
                                         "shade_frequency": 12,
                                         "depth": 3}})
    duct_j = sroom("duct_junction", jx - jw / 2, jy + jd / 2,
                   jx - jw / 2 + 1536, trunk_y0 - 512,
                   "north riser to the junction")
    duct_c = sroom("duct_cistern", cx - 768, trunk_y1 + 512, cx + 768,
                   cy - cd / 2, "south fall to the cistern")
    sewer.connect(duct_j.face("north"), junction.face("south"),
                  connection_id="connection:sewer_junction_riser")
    sewer.connect(duct_j.face("south"), main_duct.face("north"),
                  connection_id="connection:sewer_riser_trunk")
    sewer.connect(duct_c.face("north"), main_duct.face("south"),
                  connection_id="connection:sewer_trunk_fall")
    sewer.connect(duct_c.face("south"), cistern.face("north"),
                  connection_id="connection:sewer_fall_cistern")

    # A secret stash off the trunk.  The campaign declares a median of 5
    # secrets and we declared none; `secret=True` emits the campaign's own
    # wiring (channel 2, command 64, trigger-once) rather than a label.
    stash = sroom("stash", jx - jw / 2 - 3072, trunk_y0 - 512,
                  jx - jw / 2, trunk_y1 + 512,
                  "the stash: SP's secret branch, one room of it",
                  role="secret", region_kwargs={"secret": True})
    sewer.connect(stash.face("east"), main_duct.face("west"),
                  connection_id="connection:sewer_stash")

    STAGE("works-stair",
          "the first way down: the works stair, in flights, to the cellar")
    # ---- entry 1: the works stair, flights down to the cellar -------------
    yard = areas["works_yard"]["rect"]
    yard_face_x = yard[0] * PU
    service = INTERIORS["service"]
    stair = district_of["foundry_ward"].assembly(
        "works_stair",
        style=Style(**service.style_kwargs(floor_shade=38,
                                           clear_height=SEWER_CLEAR)),
        note="flights from the yard down to the works cellar (SP stair entry)",
    )
    mid = (yard[1] + yard[3]) / 2 * PU
    top_y0 = int(mid - CORRIDOR_W / 2)
    top_room = stair.room(
        "top", [(0, 0), (CORRIDOR_W, 0), (CORRIDOR_W, CORRIDOR_W), (0, CORRIDOR_W)],
        role="gateway", faces=dict(COMPASS),
        frame=Frame(int(yard_face_x - CORRIDOR_W), top_y0),
        region_kwargs=service.region_kwargs(),
        note="stair head behind the works face; mouth on the yard",
    )
    top_room.surfaces(floor_z=GRADE)
    landing_x0 = yard_face_x - CORRIDOR_W - UPPER_STEPS * UPPER_TREAD - CORRIDOR_W
    landing = stair.room(
        "landing", [(0, 0), (CORRIDOR_W, 0), (CORRIDOR_W, CORRIDOR_W), (0, CORRIDOR_W)],
        role="gateway", faces=dict(COMPASS),
        frame=Frame(int(landing_x0), top_y0),
        region_kwargs=service.region_kwargs(),
        note="switchback landing",
    )
    # THE UNDERPASS (owner, 2026-11-19/20: rethink the yard as an underground
    # passageway for a future metro, with a service hatch to the sewers; "you
    # can do your own style ... just do a passageway"). The study is
    # `knowledge/blood/studies/underpass`. The landing is the passage's
    # level: 16,384 below the street. It is its own LAYER, because it runs
    # over the sewer's trunk: `bloodmap.layers` lets two plans share ground
    # only when their height bands are apart, and the sewer's band starts
    # at 28,672, so the passage's floor and its bore's bed stay above that.
    # The yard flight keeps its eight treads and takes them at 2,048 each.
    # The lower flight and the works cellar it reached were the service stair
    # to the cellar pit, the sewer entrance the owner had removed
    # (2026-11-21: "We can ditch that underground passage sewer
    # enterance"); they went with it.
    PASSAGE_Z = GRADE + 16384
    PASSAGE_LEN, PASSAGE_CLEAR = 5120, 32768
    city.declare_layer("underpass", ceiling_z=PASSAGE_Z - PASSAGE_CLEAR,
                       floor_z=PASSAGE_Z,
                       note="the passage under the works, between street and sewer")
    landing.surfaces(floor_z=PASSAGE_Z)
    top_room.staircase("flight_upper", "west", total_rise=PASSAGE_Z - GRADE,
                       tread=UPPER_TREAD, step_rise=2048,
                       arrive_at=landing.region_id,
                       connection={"role": "portal"})
    # The passage: south from the landing, over the sewer's trunk, in E1M2's
    # passage materials (brick 417, stone 281, clay tiles 120), two bodies
    # clear because no street lies over it.
    passage = stair.room(
        "passage", [(0, 0), (CORRIDOR_W, 0), (CORRIDOR_W, PASSAGE_LEN), (0, PASSAGE_LEN)],
        role="interior", faces=dict(COMPASS),
        frame=Frame(int(landing_x0), top_y0 + CORRIDOR_W),
        region_kwargs=service.region_kwargs(),
        note="the underpass: a public way under the works, yard to avenue",
    )
    passage.surfaces(layer="underpass", floor_z=PASSAGE_Z, clear_height=PASSAGE_CLEAR,
                     wall_picnum=417, floor_picnum=281, ceiling_picnum=120,
                     floor_shade=26, ceiling_shade=26, wall_shade=24)
    city.connect(landing.face("south"), passage.face("north"),
                 connection_id="connection:underpass_from_yard_stair")
    from l3_foundry import build_loading_shutter
    UNDERPASS["loading"] = build_loading_shutter(
        city, stair, passage, east=int(landing_x0) + CORRIDOR_W,
        middle=top_y0 + CORRIDOR_W + PASSAGE_LEN - 832, floor=PASSAGE_Z)
    # The avenue stair. It is half the corridor's width and stands one
    # width in from the works' west face, because a flight laid ALONG the
    # block's edge makes every tread a neighbour of the street: the compiler
    # refused eight unpaired portal candidates. A porch at the face joins the
    # street to its head.
    west_y = top_y0 + CORRIDOR_W + PASSAGE_LEN - CORRIDOR_W
    # ... and a wall's thickness (512) clear of the yard stair's landing and
    # of the passage, which stand at other heights: two rooms that share an
    # edge and no doorway are refused too. A short neck joins its foot to
    # the passage.
    half, wall = CORRIDOR_W // 2, 512
    stair_x = int(landing_x0 - half - wall)

    def box(wide, deep):
        return [(0, 0), (wide, 0), (wide, deep), (0, deep)]

    west_landing = stair.room(
        "west_landing", box(half, CORRIDOR_W), role="gateway",
        faces=dict(COMPASS), frame=Frame(stair_x, west_y),
        region_kwargs=service.region_kwargs(), note="foot of the avenue stair")
    west_landing.surfaces(layer="underpass", floor_z=PASSAGE_Z, clear_height=PASSAGE_CLEAR,
                          wall_picnum=417, floor_picnum=281, ceiling_picnum=120,
                          floor_shade=26, ceiling_shade=26, wall_shade=24)
    neck = stair.room(
        "west_neck", box(wall, CORRIDOR_W), role="gateway",
        faces=dict(COMPASS), frame=Frame(stair_x + half, west_y),
        region_kwargs=service.region_kwargs(),
        note="through the wall between the avenue stair and the passage")
    neck.surfaces(layer="underpass", floor_z=PASSAGE_Z, clear_height=PASSAGE_CLEAR,
                  wall_picnum=417, floor_picnum=281, ceiling_picnum=120,
                  floor_shade=26, ceiling_shade=26, wall_shade=24)
    city.connect(west_landing.face("east"), neck.face("west"),
                 connection_id="connection:underpass_stair_neck")
    city.connect(neck.face("east"), passage.face("west"),
                 connection_id="connection:underpass_to_avenue_stair")
    west_top = stair.room(
        "west_top", box(half, CORRIDOR_W), role="gateway",
        faces=dict(COMPASS), frame=Frame(stair_x, top_y0),
        region_kwargs=service.region_kwargs(),
        note="head of the avenue stair")
    west_top.surfaces(floor_z=GRADE)
    west_top.staircase("flight_west", "south", total_rise=PASSAGE_Z - GRADE,
                       tread=(west_y - top_y0 - CORRIDOR_W) // 8, step_rise=2048,
                       arrive_at=west_landing.region_id,
                       connection={"role": "portal"})
    west_porch = stair.room(
        "west_porch", box(wall, CORRIDOR_W), role="gateway",
        faces=dict(COMPASS), frame=Frame(stair_x - wall, top_y0),
        region_kwargs=service.region_kwargs(),
        note="the underpass's mouth in the works' avenue face")
    west_porch.surfaces(floor_z=GRADE)
    city.connect(west_porch.face("east"), west_top.face("west"),
                 connection_id="connection:underpass_porch_stair")
    city.connect(west_porch.face("west"), foundry_st.face("west"),
                 connection_id="connection:underpass_avenue_mouth")
    # The unfinished metro: a short dark bore off the passage's south end,
    # laid with track, behind iron bars (`bloodmap.glass.grille`, in
    # `main`). Seen, not entered. Its bed is level with the passage: bars
    # hang on a wall whose two sides stand at one floor and one ceiling,
    # and a bed half a step down was refused by that law.
    bore = stair.room(
        "metro_bore", [(0, 0), (CORRIDOR_W, 0), (CORRIDOR_W, CORRIDOR_W), (0, CORRIDOR_W)],
        role="detail", faces=dict(COMPASS),
        frame=Frame(int(landing_x0), top_y0 + CORRIDOR_W + PASSAGE_LEN),
        region_kwargs={**service.region_kwargs(), "declared_zero_exit": True},
        note="the metro that was begun and never finished",
    )
    # Lit enough to be read through the bars: the owner, walking it, "these
    # bars are just bars, you can't really tell what it is". What says
    # "metro" hangs in it and beside it (`dress_underpass`, in `main`).
    bore.surfaces(layer="underpass", floor_z=PASSAGE_Z, clear_height=PASSAGE_CLEAR,
                  wall_picnum=417, floor_picnum=1129, ceiling_picnum=120,
                  floor_shade=30, ceiling_shade=34, wall_shade=28)
    city.connect(bore.face("north"), passage.face("south"),
                 connection_id="connection:underpass_metro_mouth")
    UNDERPASS.update(
        passage=passage.region_id, bore=bore.region_id,
        x0=int(landing_x0), x1=int(landing_x0) + CORRIDOR_W,
        y0=top_y0 + CORRIDOR_W, y1=top_y0 + CORRIDOR_W + PASSAGE_LEN,
        y2=top_y0 + CORRIDOR_W + PASSAGE_LEN + CORRIDOR_W)
    UNDERPASS["bars"] = (int(landing_x0) - 16, top_y0 + CORRIDOR_W + PASSAGE_LEN - 16,
                         int(landing_x0) + CORRIDOR_W + 16,
                         top_y0 + CORRIDOR_W + PASSAGE_LEN + 16)
    city.connect(top_room.face("east"), foundry_st.face("west"),
                 connection_id="connection:works_stair_mouth")

    STAGE("stack-links",
          "the two room-over-room links between street and sewer")
    # ---- the two stack links (hand-built per stacks-v1; grammar req #7) ---
    def mouth_pair(name, upper_parent, upper_frame_xy, upper_floor,
                   upper_style, landing_depth, see_through, size=SHAFT):
        """A congruent stack mouth pair: upper pit + aligned lower tube.

        The lower tube's ceiling is the link plane (set at compile time by
        the link builder); its floor sits `landing_depth` below the plane --
        deep enough that a standing centre stays below the plane (no warp
        ping-pong), shallow enough to jump back out where intended."""
        ux, uy = upper_frame_xy
        # One room in the space it opens from.  Six of these used to be
        # singleton assemblies at the top of the city -- `yard_grate_mouth`
        # holding `yard_grate_upper`, and nothing else, ever.
        upper = (upper_parent or city).room(
            f"{name}_mouth", [(0, 0), (size, 0), (size, size), (0, size)],
            role="gateway", faces=dict(COMPASS), frame=Frame(int(ux), int(uy)),
            note=f"{name}: upper mouth (link plane at its floor)",
        )
        upper.style = upper_style
        # The mirror tile is what makes the far side draw: rules_blood's
        # `stack-portal-wears-the-mirror-tile` is an ERROR sourced from
        # mirrors.cpp IsRorSector.  `see_through` was accepted by this
        # function and never used -- the flag was inert, and the cellar pit
        # wore an ordinary service floor while claiming to be a portal.
        import citytree
        lower = mouths_part.room(
            f"{name}_mouth_below",
            [(0, 0), (size, 0), (size, size), (0, size)],
            role="gateway", faces=dict(COMPASS),
            frame=Frame(int(ux + park_dx), int(uy + park_dy)),
            # All 6 paired links in E1M1/E3M1 have an XSector on both
            # halves; a behaviour entry is how ours gets one.
            region_kwargs={"sector_behavior": {"amplitude": -4,
                                               "shade_frequency": 4}},
            note=f"{name}: aligned lower mouth, congruent at the plane",
        )
        lower.frame = Frame(lower.frame.dx - park_dx, lower.frame.dy - park_dy)
        lower.style = Style(**SEWER.style_kwargs(
            floor_shade=40, floor_z=upper_floor + landing_depth,
            clear_height=landing_depth))
        # The mirror tile is what makes the far side draw: rules_blood's
        # `stack-portal-wears-the-mirror-tile` is an ERROR sourced from
        # mirrors.cpp IsRorSector.  `see_through` was accepted by this
        # function and never used -- the flag was inert, and the cellar pit
        # wore an ordinary service floor while claiming to be a portal.
        upper.surfaces(floor_z=upper_floor,
                       **({"floor_picnum": MIRROR_TILE} if see_through else {}))
        if see_through:
            lower.surfaces(ceiling_picnum=MIRROR_TILE)
        return upper, lower

    # Yard grate: see-through, one-way drop.  A bare square in the paving
    # reads as nothing, so the mouth gets a KERB -- a ring of raised stone
    # you step over, which frames the hole and says "something opens here"
    # from across the yard.  The ring is a sector with the shaft as its
    # hole; both are carved out of the street together.
    # THE GRATE IS A GRATE NOW, NOT A HOLE. The owner, playing it on
    # 2026-11-19: "this weird rectangle hole with posters on the ground
    # looks weird ... entrances to the sewers basically next to each other".
    # It was a see-through room-over-room drop, its floor the mirror tile,
    # inside a raised kerb. The link is gone, the ring lies flush as a stone
    # apron, and an iron sewer grate lies on the mouth
    # (`l3_foundry.sprinkle`). The shaft below stays, as the sewer's riser.
    KERB, KERB_RISE = 2048, 0
    foundry_local_gx = gx - int(SEAM_AVENUE)
    kerb_half = KERB // 2
    foundry_st.carve([(foundry_local_gx - kerb_half + dx, gy - kerb_half + dy)
                      for dx, dy in ((0, 0), (KERB, 0), (KERB, KERB), (0, KERB))])
    kerb = district_of["foundry_ward"].room(
        "grate_kerb", [(0, 0), (KERB, 0), (KERB, KERB), (0, KERB)],
        role="detail", faces=dict(COMPASS),
        frame=Frame(gx - kerb_half, gy - kerb_half),
        region_kwargs=MASONRY.region_kwargs(),
        note="the raised stone ring around the yard grate: stepped over, "
             "not climbed -- 1024 against a 4096 max step",
    )
    # the yard's own paving: the red service floor it wore read, flush, as
    # "posters on the ground"
    kerb.surfaces(**MASONRY.style_kwargs(
        floor_picnum=FACADES["foundry_ward"].floor, floor_shade=28,
        floor_z=GRADE - KERB_RISE, clear_height=STREET_SKY - KERB_RISE))
    kerb.carve([(kerb_half - SHAFT_HALF + dx, kerb_half - SHAFT_HALF + dy)
                for dx, dy in ((0, 0), (SHAFT, 0), (SHAFT, SHAFT), (0, SHAFT))])
    for face in ("north", "east", "south", "west"):
        city.connect(kerb.face(face), foundry_st.face("east"),
                     connection_id=f"connection:kerb_street_{face}")
    grate_upper, grate_lower = mouth_pair(
        "yard_grate", district_of["foundry_ward"],
        (gx - SHAFT_HALF, gy - SHAFT_HALF), GRADE,
        Style(**MASONRY.style_kwargs(clear_height=STREET_SKY)),
        SEWER_FLOOR - GRADE, see_through=False)
    # With no link the shaft is a sewer room like any other and has to keep
    # to the sewer's band: a riser a little taller than the runs, not a
    # tube to the street.
    grate_lower.style = Style(**SEWER.style_kwargs(
        floor_shade=40, floor_z=SEWER_FLOOR, clear_height=SEWER_CLEAR + 8192))
    grate_upper.surfaces(floor_picnum=FACADES["foundry_ward"].floor, floor_shade=34)
    # The shaft's rim now meets the kerb ring, not the street: the ring is
    # what surrounds it.  A hole is wound opposite to its outer loop, but
    # _compass_edges still names each edge by where it lies, so the names
    # correspond directly.
    for face in ("north", "east", "south", "west"):
        city.connect(grate_upper.face(face), kerb.hole_face(0, face),
                     connection_id=f"connection:yard_grate_rim_{face}")
    # The trunk's east end and the ring's east leg both meet the shaft
    # foot, so the drop lands on a junction rather than in a dead end.
    city.connect(grate_lower.face("west"), main_duct.face("east"),
                 connection_id="connection:grate_shaft_trunk")

    STAGE("sewer-network",
          "the sewer's ring, its chambers and the necks between them")
    # ---- the network proper: the ring, its chambers and the necks --------
    # (the yard shaft's foot opens straight onto the ring's east leg)
    # Built after the mouths, because the ring hangs off the grate shaft.
    import l3_sewer
    sewer_net = l3_sewer.expand(city, sewer, {
        "junction": junction, "cistern": cistern,
        "main_duct": main_duct, "grate_lower": grate_lower,
    })
    # The station foot joins the silt trap in l3_sewer's chamber list.  That
    # puts the lower approach on the long, east-facing side of the final tread
    # instead of asking the player to turn through a short wall.
    city.connect(grate_lower.face("east"),
                 l3_sewer.edge(sewer_net, "e_leg", "west", at=gy / PU).face("west"),
                 connection_id="connection:grate_shaft_ring")
    # The towpath, from E3M3's own ledge family.  The two long legs are 24
    # plan units of bare tunnel each and the ring's most repetitive stretch.
    print("sewer towpaths:", l3_sewer.ledges(
        sewer, sewer_net, grade=SEWER_FLOOR, host_clear=SEWER_CLEAR))

    # The cellar pit is gone: a shaft from the works cellar into the junction,
    # a third way down within a few units of the pump station's spiral and
    # the yard. The owner, 2026-11-21: "You are always putting these sewers
    # enterances so close to each other ... We can ditch that underground
    # passage sewer enterance, keep the pump station one". The stair still
    # reaches the cellar; the ways down are the spiral and the manholes.

    STAGE("pumping-station",
          "the second way down: the pumping station's stairs")
    # ---- the pumping station: road-level stairs into the sewer ----------
    import l3_shed
    shed = l3_shed.build(district_of["foundry_ward"], foundry_st,
                         (int(DISTRICT_BOUNDS["foundry_ward"][0]),
                          int(DISTRICT_BOUNDS["foundry_ward"][1])))
    # E3M1 and Duke E1L1 use the same topology: four-wall treads around an
    # uncovered solid newel, plus one ordinary tread-width corridor at each
    # end.  The prior version carved the entire C-shaped stair annulus out of
    # sectors 85 and 179.  Those sectors then wrapped round the staircase,
    # sharing solid edges with it and producing both a zero-thickness wall and
    # an unusably narrow lower turn.  The two dedicated corridor rooms are
    # defined by l3_shed.CELLAR and l3_sewer.station_foot instead.
    spiral_axis = l3_shed.SPIRAL_AXIS
    SPIRAL_RADIUS, SPIRAL_EXIT = l3_shed.SPIRAL_RADIUS, 270.0

    from bloodmap.spiral import spiral_stair

    def wind_into_sewer(layout, _room):
        foot = sewer_net["station_foot"]
        helix = spiral_stair(
            layout, "pump_station_spiral", axis=spiral_axis,
            base_floor_z=l3_shed.CELLAR_FLOOR_Z,
            rise=SEWER_FLOOR - l3_shed.CELLAR_FLOOR_Z,
            entry_angle=0.0, exit_angle=SPIRAL_EXIT, radius=SPIRAL_RADIUS,
            layer="sewer", **SEWER.style_kwargs(floor_shade=40))
        entry, exit = helix.flanks
        layout.add_connection("connection:pump_spiral_in",
                              shed["cellar"].region_id, entry.region_id,
                              a1=entry.a, a2=entry.b, min_width=512)
        layout.add_connection("connection:pump_spiral_out",
                              exit.region_id, foot.region_id,
                              a1=exit.a, a2=exit.b, min_width=512)
        return helix

    shed["cellar"].raw(
        "spiral: the pump station cellar down into the under-city",
        wind_into_sewer)
    import phantom_terminus
    phantom_terminus.build(sewer, sewer_net["silt_trap"])

    stack_links = []

    STAGE("manholes",
          "drain covers in the streets that a blast opens onto a shaft into the sewer")
    # ---- manholes (`l3_sewer.MANHOLES`): a shaft from a street into the
    # sewer; its cover is laid with the set pieces. The street keeps its
    # level; the shaft drops a recess to a see-through link plane, and the
    # landing below is the sewer's floor, a fall `conformance` checks does
    # no harm.
    manhole_mouths = {}
    for link_id, (name, mx0, my0, size, district, how, leg, leg_face, _note) in enumerate(
            l3_sewer.MANHOLES, start=10):
        ux, uy = int(mx0 * PU), int(my0 * PU)
        host = streets[district]
        ox, oy = (int(v) for v in DISTRICT_BOUNDS[district][:2])
        host.carve([(ux - ox + dx, uy - oy + dy)
                    for dx, dy in ((0, 0), (size, 0), (size, size), (0, size))])
        # the shaft lands in water, one step below the walks, running fast
        # toward the ring (the owner: "You should fall into water")
        water_floor = SEWER_FLOOR + l3_sewer.CHANNEL_DROP
        m_upper, m_lower = mouth_pair(
            name, district_of[district], (ux, uy),
            GRADE + l3_sewer.MANHOLE_RECESS,
            Style(**MASONRY.style_kwargs(
                clear_height=STREET_SKY + l3_sewer.MANHOLE_RECESS)),
            water_floor - GRADE - l3_sewer.MANHOLE_RECESS,
            see_through=True, size=size)
        run = (l3_sewer.flow_behavior(
            {"east": 1024, "west": 0, "north": 512, "south": 1536}[leg_face],
            *l3_sewer.LANDING_FLOW) if how == "beside"
            else l3_sewer.flow_behavior(*l3_sewer.FLOW[leg]))
        m_lower.region_kwargs["sector_behavior"].update(
            {"depth": l3_sewer.WATER_DEPTH, **run})
        m_lower.style = Style(**SEWER_WET.style_kwargs(
            floor_shade=38, floor_z=water_floor,
            clear_height=water_floor - GRADE - l3_sewer.MANHOLE_RECESS))
        if leg == "stockyard_drain":
            m_lower.surfaces(wall_picnum=l3_sewer.STOCKYARD_WET.wall)
            sewer_net["stockyard_landing"] = m_lower
        for face in ("north", "east", "south", "west"):
            city.connect(m_upper.face(face), host.face("east"),
                         connection_id=f"connection:{name}_rim_{face}")
        if how == "inside":
            # it lands in the water of a room it lies within: an island cut
            # out of that room, open on all four sides
            rx0, ry0, _rx1, _ry1 = l3_sewer._rects()[leg]
            sewer_net[leg].carve([(ux - int(rx0) + dx, uy - int(ry0) + dy)
                                  for dx, dy in ((0, 0), (size, 0), (size, size), (0, size))])
            for face in ("north", "east", "south", "west"):
                city.connect(m_lower.face(face), sewer_net[leg].face("north"),
                             connection_id=f"connection:{name}_landing_{face}")
            stack_links.append({
                "stack_id": f"stack:{name}", "upper": m_upper.region_id,
                "lower": m_lower.region_id, "link_id": link_id,
                "at_upper": (ux + size // 2, uy + size // 2), "see_through": True,
                "recess": 0})
            manhole_mouths[name] = m_upper
            continue
        opposite = {"east": "west", "west": "east",
                    "north": "south", "south": "north"}
        # the landing opens off the leg through a short passage across the
        # gap between the leg's wall and the shaft
        lx0, ly0, lx1, ly1 = l3_sewer._rects()[leg]
        span = {"east": (lx1, uy, ux, uy + size), "west": (ux + size, uy, lx0, uy + size),
                "north": (ux, uy + size, ux + size, ly0),
                "south": (ux, ly1, ux + size, uy)}[leg_face]
        px0, py0, px1, py1 = (int(v) for v in span)
        if px1 - px0 > 0 and py1 - py0 > 0:
            passage = mouths_part.room(
                f"{name}_passage",
                [(0, 0), (px1 - px0, 0), (px1 - px0, py1 - py0), (0, py1 - py0)],
                role="gateway", faces=dict(COMPASS), frame=Frame(px0, py0),
                region_kwargs={"sector_behavior": {
                    "depth": l3_sewer.WATER_DEPTH, "amplitude": -4,
                    "shade_frequency": 4, **run}},
                note=f"{name}: the shaft's water running onto the {leg}")
            passage.style = Style(**SEWER_WET.style_kwargs(
                floor_shade=38, floor_z=water_floor,
                clear_height=SEWER_CLEAR + l3_sewer.CHANNEL_DROP))
            city.connect(passage.face(opposite[leg_face]),
                         sewer_net[leg].face(leg_face),
                         connection_id=f"connection:{name}_passage_leg")
            city.connect(m_lower.face(opposite[leg_face]),
                         passage.face(leg_face),
                         connection_id=f"connection:{name}_landing")
        else:
            city.connect(m_lower.face(opposite[leg_face]),
                         sewer_net[leg].face(leg_face),
                         connection_id=f"connection:{name}_landing")
        stack_links.append({
            "stack_id": f"stack:{name}", "upper": m_upper.region_id,
            "lower": m_lower.region_id, "link_id": link_id,
            "at_upper": (ux + size // 2, uy + size // 2), "see_through": True})
        manhole_mouths[name] = m_upper
    print("manholes:", sorted(manhole_mouths))


    STAGE("light-pools",
          "patches of lit floor in the streets, declared as regions")
    # ---- light pools: shade variation a district-sized sector cannot have -
    # Placed where a city lights itself: venue mouths, gates, stair heads,
    # junctions.  Rate follows street-furniture's lamp norm.
    import lightpools
    yard_rect = areas["works_yard"]["rect"]
    yard_x0, yard_y0, yard_x1, yard_y1 = (int(v * PU) for v in yard_rect)
    pool_sites = [
        ("yard_stair", foundry_st, "foundry_ward",
         yard_x0 + 1024, (yard_y0 + yard_y1) // 2),
        ("yard_gate", foundry_st, "foundry_ward",
         yard_x1 - 1024, (yard_y0 + yard_y1) // 2 - 2048),
        ("spur_junction", foundry_st, "foundry_ward",
         int((city_plan.X_SPUR + 1.5) * PU), int(city_plan.Y_ROWST * PU) - 3072),
        ("avenue_north", theatre_st, "theatre_row",
         int((city_plan.X_AVENUE + 2) * PU), int((city_plan.Y_R1 + 3) * PU)),
        ("forecourt", theatre_st, "theatre_row",
         int((city_plan.X_AVENUE - 1.25) * PU), int((city_plan.Y_ROWST - 2) * PU)),
        ("lychgate", oldcross_st, "old_crossing",
         int((city_plan.X_STREET_W + 2.5) * PU), int((city_plan.Y_R2 + 7) * PU)),
        ("well_square", oldcross_st, "old_crossing",
         int((city_plan.X_STREET_W - 0.5) * PU), int((city_plan.Y_R2 + 6) * PU)),
        ("plaza_east", market_st, "market_slip",
         int((city_plan.X_C - 2) * PU), int((city_plan.Y_R3 + 5) * PU)),
        ("quay_gate", market_st, "market_slip",
         int((city_plan.X_AVENUE + 1) * PU), int((city_plan.Y_QUAY + 2) * PU)),
    ]
    lit = []
    for name, street_room, district, px, py in pool_sites:
        facade = FACADES[district]
        lit.append(lightpools.pool(
            district_of[district], street_room, name, x=px, y=py, floor_z=GRADE,
            clear_height=STREET_SKY, floor_picnum=facade.floor,
            wall_picnum=facade.opening, ceiling_picnum=facade.ceiling,
            sky=True,
            size=lightpools.POOL))
    ctx_pools = [room.region_id for room in lit]

    STAGE("church",
          "St Gallow's: nave, tower, crypt")
    # ---- L3: St Gallow's, the mandatory landmark of Old Crossing --------
    import l3_church
    church_rooms = l3_church.build(district_of["old_crossing"], oldcross_st,
                                   grounds["cemetery"], gates,
                                   tuple(int(v * PU) for v in areas["cemetery"]["rect"]),
                                   gate_rects.get("cemetery", ()))
    # The crypt's cracked wall is the sewer trunk's west wall, seen from
    # the other side: 512 of earth under the avenue's kerb.
    from bloodmap import breach as _breach
    for _index, _name in enumerate(l3_church.BREACH_ROOMS):
        _piece = church_rooms[_name]
        city.connect(_piece.face("far"),
                     l3_sewer.edge(sewer_net, "w_leg", "west",
                                   at=_breach.face_middle(_piece, "far")[1] / PU).face("west"),
                     connection_id=f"connection:crypt_breach_sewer_{_index}")

    STAGE("arcade",
          "the Gravesend Arcade and its shops")
    # ---- L3: the Gravesend Arcade (the shopping mall) -------------------
    import l3_mall
    mall_rooms = l3_mall.build(district_of["market_slip"], market_st)

    STAGE("theatre",
          "Theatre Row: the Aldermack, the saloon, the pawnshop")
    # ---- L3: Theatre Row's venues (the entertainment district) ----------
    import l3_theatre
    theatre_rooms, door_levers, aldermack_house = l3_theatre.build(
        district_of['theatre_row'], theatre_st)
    fire_doors = l3_theatre.add_fire_doors(theatre_rooms)

    STAGE("station",
          "Gravesend Station behind the north wall")
    # ---- L3: Gravesend Station, behind the city's north wall ------------
    import l3_station
    station_rooms = l3_station.build(city, theatre_st)

    STAGE("market",
          "Market Slip: the quay, the harbour and the ship")
    # ---- L3: Market Slip's public space (the district the player starts
    # in), furnished from its own L1 `furnish` slots ------------------------
    import l3_market
    plaza = next(a for a in data["areas"] if a["id"] == "market_plaza")
    market_dressing = l3_market.dress(
        district_of["market_slip"], market_st, plaza["rect"],
        city_plan.Y_QUAY, city_plan.CITY_D)


    STAGE("foundry",
          "Foundry Ward, the pilot district, with its machine hall")
    # ---- L3: the pilot district (Foundry Ward), dressed -------------------
    ctx = {
        "foundry_st": foundry_st,
        "yard_rect_pu": areas["works_yard"]["rect"],
        "grate_upper": grate_upper,
        "foundry_origin": (int(DISTRICT_BOUNDS["foundry_ward"][0]),
                           int(DISTRICT_BOUNDS["foundry_ward"][1])),
        "sewer_rooms": {"trunk": main_duct.region_id,
                        "junction": junction.region_id,
                        "cistern": cistern.region_id,
                        "stash": stash.region_id},
        "sewer_rooms_new": sewer_net,
        "manholes": manhole_mouths,
        "station_rooms": shed,
        "theatre_rooms": theatre_rooms,
        "door_levers": door_levers,
        "church_rooms": church_rooms,
        "mall_rooms": mall_rooms,
        "stair_top_y0": top_y0,
    }
    import l3_foundry
    dressing = l3_foundry.dress(district_of["foundry_ward"], ctx)
    dressing["stash"] = stash.region_id

    STAGE("undeclared-venues",
          "venues on the plan that nobody has built, declared as such")
    # ---- L1 venues nobody has built yet, declared as such -----------------
    #
    # A named empty node is the honest way to say "this space is planned and
    # its contents are not made": it is findable, it is legible as a plan,
    # and `conformance.py` can hold the tree to the plan in both directions.
    # An ABSENT node says nothing at all, which is how three of the plan's
    # ten venues went missing without anything noticing.
    import citytree
    block_district = {b["id"]: b["district"] for b in data["blocks"]}
    # Venues AND free-standing masses.  The monument was declared as a block
    # and never built for as long as the plan has existed, and the kiosk and
    # the gatehouse still are: the plaza carved their holes and the holes
    # stayed holes.  A block with a role is a thing the plan asked for, so
    # the correspondence covers both classes.
    slots = list(data["venues"]) + [
        dict(block, type=block["role"], block=block["id"])
        for block in data["blocks"] if block["role"] == "free_standing"]
    for slot in slots:
        if any(getattr(node, "l1_venue", None) == slot["id"]
               for node, _d in citytree.walk(city)):
            continue
        district = block_district.get(slot["block"])
        if district not in district_of:
            continue
        placeholder = citytree.plan(
            district_of[district], slot["id"],
            slot.get("note") or f"L1 {slot['type']} on {slot['block']}")
        citytree.declare_venue(placeholder, slot["id"], slot["type"],
                               built_by="(planned)")

    STAGE("start",
          "the player's start on the quay, and the manifest begins")
    # ---- start: the first circuit leg, on the quay ------------------------
    start = data["circuit"][0]["at"]
    mb = DISTRICT_BOUNDS["market_slip"]
    city.set_start(market_st,
                   local=((start[0] * PU - mb[0]) / (mb[2] - mb[0]),
                          (start[1] * PU - mb[1]) / (mb[3] - mb[1])),
                   angle=1536)
    ctx["street_regions"] = {room.region_id: name
                             for name, room in streets.items()}
    ctx["aldermack_house"] = aldermack_house
    ctx["fire_doors"] = fire_doors
    ctx["greens"] = ctx_greens
    ctx["light_pools"] = ctx_pools
    ctx["market_dressing"] = market_dressing
    ctx["market_street"] = market_st
    ctx["theatre_street"] = theatre_st
    ctx["manifest"] = {
        "districts": len(DISTRICT_BOUNDS),
        "carved_areas": sum(1 for a in data["areas"] if a.get("carved")),
        "gates": sum(len(a.get("gates", [])) for a in data["areas"]),
        "stack_mouths_at_grade": 1,          # the yard grate (the pits are indoors)
        "grate_kerb": 1,                     # its raised stone ring
        "light_pools": len(ctx_pools),
        # The church's eaves, churchyard wall and tower gables: open ground
        # at grade, street in everything but the height of its sky.
        "sky_aprons": len(l3_church.APRONS),
        # Fountain, stalls and boards sit within one max step of the
        # street, so they join its walkable component (and cost no
        # walk-around loop -- the census is at its contract ceiling).
        "market_furniture": len(market_dressing["street_joined"]),
        "monument_tiers": len(market_dressing.get("monument_rooms", {})),
    }

    STAGE("street-anatomy",
          "pavement, carriageway and kerb along every street")
    # ---- street anatomy: pavement, carriageway, kerb ---------------------
    # LAST, deliberately. The district street was one open region at one
    # level wearing one tile; `streets.lay` gives each run of the
    # circulation graph a carriageway dropped a measured kerb below the
    # pavement it keeps -- E3M1's grammar, tile 352 at 2048 down. Running it
    # here means every other claim on the street -- light pools, the grate
    # kerb, market furniture, the venue thresholds -- is already carved, and
    # a road is cut around them rather than through them. A road that has to
    # yield to a lamp post is the correct precedence: the pavement was there
    # first.
    import streets as street_anatomy
    from resolution import WIDTH_UNITS

    blocks_by_district = collections.defaultdict(list)
    for block in data["blocks"]:
        if not block.get("inside_area"):
            blocks_by_district[block["district"]].append(block)
    ctx["manifest"]["streets"] = street_anatomy.lay(
        city, data, WIDTH_UNITS, DISTRICT_BOUNDS, streets, district_of,
        grade=GRADE, street_sky=STREET_SKY,
        blocks_by_district=blocks_by_district, unit=PU, seam_gates=gates)
    ctx["manifest"]["roadways"] = len(ctx["manifest"]["streets"]["laid"])

    STAGE("street-ends",
          "the walls where the main streets stop")
    # ---- where the main streets stop ------------------------------------
    # The avenue, Theatre Row and the market street ran out at the city's
    # blank perimeter wall, 11.6 bodies of masonry: every long view ended in
    # a black slab.  E3M1 ends a street in a low wall with the sky behind it
    # (`streets.end_walls`).  The mouth of each is its run's width, centred
    # where the run meets the edge.
    from materials import FACADES as _FACADES

    def _mouth(centre, kind):
        half = WIDTH_UNITS[kind] // 2
        return (int(centre - half), int(centre + half))

    # The avenue no longer ends in a wall: Gravesend Station fronts it
    # (`l3_station.avenue_front`), a forecourt and two arches across the
    # mouth the end wall closed.
    import l3_station as _station
    assert _mouth(SEAM_AVENUE, "avenue") == (_station.FORECOURT[0][0], _station.FORECOURT[-1][1]), \
        "the station front must span the avenue's mouth exactly"
    ctx["manifest"]["station_front"] = _station.avenue_front(
        city, streets, district_of, DISTRICT_BOUNDS, gates, grade=GRADE,
        street_sky=STREET_SKY, sky_tile=_FACADES["theatre_row"].ceiling)
    ends = [
        ("Theatre_Row", "west", *_mouth(SEAM_ROW, "row")),
        ("market_street_west", "west", *_mouth(SEAM_MARKET, "street")),
        ("market_street_east", "east", *_mouth(SEAM_MARKET, "street")),
    ]
    ctx["manifest"]["street_ends"] = street_anatomy.end_walls(
        city, ends, streets, district_of, DISTRICT_BOUNDS, gates,
        grade=GRADE, street_sky=STREET_SKY,
        facade_of={name: material.wall for name, material in _FACADES.items()},
        sky_tile=_FACADES["theatre_row"].ceiling)
    ctx["manifest"]["end_walls"] = sum(
        2 * len(row["districts"]) for row in ctx["manifest"]["street_ends"])

    return city, stack_links, gates, ctx, dressing


def dress_underpass(layout) -> dict:
    """What tells a player the barred bore is a metro, and which way is out.

    Blood's own boards, hung where his own metro (DNE3L6 s371) hangs them:
    the arrivals board on the wall the eye lands on, TICKETS beside the way
    to the trains, EXIT toward the stairs.
    """
    import props

    u = UNDERPASS
    hung = {}
    for name, region, a1, a2, t, tile in (
            # the bore's back wall, straight ahead through the bars
            ("arrivals", u["bore"], (u["x1"], u["y2"]), (u["x0"], u["y2"]), 0.5, 431),
            # beside the bars, on the passage's east wall
            ("tickets", u["passage"], (u["x1"], u["y0"]), (u["x1"], u["y1"]), 0.88, 943),
            # toward the stairs, on the same wall and on the one facing it
            ("exit_yard", u["passage"], (u["x1"], u["y0"]), (u["x1"], u["y1"]), 0.12, 761),
            ("exit_avenue", u["passage"], (u["x0"], u["y1"]), (u["x0"], u["y0"]), 0.62, 761)):
        if name == "tickets":
            # Beside the loading recess, on the remaining solid east wall.
            t = 0.55
        layout.place_on_wall(
            f"underpass:{name}", region, a1=a1, a2=a2, t=t,
            # the campaign hangs EXIT at 1.85 bodies; under a ceiling 1.93
            # up that put a tenth of the sign through it
            height_player_heights=min(props.height_of(tile), 1.5),
            offset_player_widths=0.06, **props.fields(tile))
        hung[name] = tile
    return hung


def build_stack_link(layout, spec, offset_d, *, see_through):
    """A stack pair, hand-built per stacks-v1 (grammar req #7:
    room_over_room only places both markers at one point).  Congruent
    mouths, lower ceiling snapped to the upper floor plane, markers paired
    by data_1, translation = their explicit planar offset."""
    upper = layout.regions[spec["upper"]]
    lower = layout.regions[spec["lower"]]
    from bloodmap.roomoverroom import align_lower_mouth
    # a landing that is an island in a room's water keeps that water's level
    # (`recess` 0); the default keeps a drop 2048 below its neighbours
    lower_ceiling, _lower_floor = align_lower_mouth(
        layout, spec["upper"], spec["lower"], recess=spec.get("recess", 2048))
    if see_through:
        upper.floor_picnum = MIRROR_TILE
        lower.ceiling_picnum = MIRROR_TILE
    layout.declare_special(spec["upper"], spec["lower"], "stack")
    ax, ay = spec["at_upper"]
    # Marker family matters: the campaign's walkable room-over-room floors
    # are the STACK family (kMarkerUpStack 11 / kMarkerLowStack 12) -- every
    # paired link in E1M1 and E3M1 reads as "stack".  Types 7/6 are the
    # "link" family, a different mechanism; built with those, the player
    # never falls through and the mirror floor shows the far side's sprites
    # without its geometry, which is what "flying torches" looks like.
    for tag, region_id, marker_type, x, y, z, marker_tile in (
        ("upper", spec["upper"], MARKER_UP_STACK, ax, ay, int(upper.floor_z),
         MARKER_TILE_UPPER),
        ("lower", spec["lower"], MARKER_LOW_STACK,
         ax + offset_d[0], ay + offset_d[1], int(lower_ceiling),
         MARKER_TILE_LOWER),
    ):
        layout.add_sprite(
            f"{spec['stack_id']}_{tag}", region_id, x=int(x), y=int(y), z=z,
            type=int(marker_type), status=STACK_MARKER_STATNUM,
            picnum=marker_tile, cstat=STACK_MARKER_CSTAT,
            x_repeat=64, y_repeat=64, angle=0,
            behavior={"data_1": int(spec["link_id"])},
        )


#: The last full build: `(program, compiled)`.  `citytree --cost` needs
#: the compiled level AFTER the sprite passes, and there is no other
#: way to get it without running them twice.
LAST_BUILD = None


def _seat_actors(layout) -> int:
    """Write every dude standing on its floor, as the campaign does.

    The layout seats nothing here (it is built without the game's ART), so
    a dude's z was its floor's, and with bit 128 it is drawn about its z:
    half of every zombie was under the floor in the editor. The game moves
    a dude to the floor when it spawns, which is why nobody saw it in play.
    """
    import wallplane
    from bloodmap.placement import drawn_lift

    sizes = wallplane.art()
    seated = 0
    for placement in layout.placements:
        anchor = placement.anchor or {}
        if not 200 <= int(placement.type) <= 260:
            continue
        size = sizes.get(int(placement.picnum))
        if size is None:
            continue
        _width, height, _xofs, yofs = size
        lift = drawn_lift(height, yofs, placement.y_repeat, placement.cstat)
        if not anchor:
            #: placed at a world point with its z on the floor
            region = layout.regions.get(placement.region_id)
            if (region is not None and lift > 0
                    and int(placement.z) == int(region.floor_z)):
                placement.z = int(region.floor_z) - lift
                seated += 1
            continue
        if anchor.get("kind") != "floor" or float(
                anchor.get("height_player_heights", 0.0)):
            continue
        if lift > 0:
            anchor["height_player_heights"] = lift / 16960.0
            seated += 1
    return seated


def _drop_flat_overlaps(layout) -> list:
    """Two flat sprites at one height in one place lie through each other.

    The sewer's runs each put their floor things on the room's centre line,
    so a room with a run on two faces got two of everything in one spot,
    and a drain grate 2,048 across swallowed its neighbours. The first one
    placed stays; a later one that would cover it is not placed, and says
    so. `tools/sprite_fit.flat_overlaps` holds the result.
    """
    import props
    import wallplane

    sizes = wallplane.art()
    taken: dict = {}
    dropped, keep = [], []
    for placement in layout.placements:
        anchor = placement.anchor or {}
        size = sizes.get(int(placement.picnum))
        region = layout.regions.get(placement.region_id)
        if (anchor.get("kind") not in ("floor", "ceiling") or size is None
                or region is None or int(placement.cstat) & 48 != 32
                or int(placement.cstat) & 0x8000 or "local" not in anchor):
            keep.append(placement)
            continue
        x0, y0, x1, y1 = props.room_rect(region)
        x = x0 + float(anchor["local"][0]) * (x1 - x0)
        y = y0 + float(anchor["local"][1]) * (y1 - y0)
        half = min(size[0] * int(placement.x_repeat),
                   size[1] * int(placement.y_repeat)) / 8.0
        key = (placement.region_id, anchor["kind"])
        lifted = float(anchor.get("height_player_heights", 0.0))
        if not region.parallax_ceiling:
            #: the compiler presses a thing asked for above the ceiling
            #: against it, so a porthole "at 3.38" and a grate "at 1.99"
            #: are one plane in a sewer two bodies high
            lifted = min(lifted, abs(int(region.floor_z)
                                     - int(region.ceiling_z)) / 16960.0)
        clash = None
        for ox, oy, ohalf, oid, olifted in taken.get(key, ()):
            #: (a grate at 1.99 bodies and one at 1.93 are both pressed to
            #: the same sewer ceiling by the compiler)
            if abs(olifted - lifted) > 0.15:
                continue
            wide = min(x + half, ox + ohalf) - max(x - half, ox - ohalf)
            deep = min(y + half, oy + ohalf) - max(y - half, oy - ohalf)
            if wide > 0 and deep > 0 and (
                    wide * deep > 0.15 * 4.0 * min(half, ohalf) ** 2):
                clash = oid
                break
        if clash is not None:
            dropped.append(f"{placement.placement_id} (tile "
                           f"{placement.picnum}) would lie through {clash}")
            continue
        taken.setdefault(key, []).append(
            (x, y, half, placement.placement_id, lifted))
        keep.append(placement)
    layout.placements[:] = keep
    return dropped


def main() -> int:
    global LAST_BUILD
    program, stack_links, gates, ctx, dressing = build()
    STAGE("connect",
          "the program becomes a planar layout; gates join the regions")
    layout = program.compile()
    # The circuit was begun with the program; its names are this layout's.
    from bloodmap import wiring as _wiring
    import wires as _wires
    circuit = ctx["circuit"] = _wires.circuit().bind(layout)
    import caleb
    caleb.level_opening(layout)
    for gate in gates:
        gate_id, region_a, region_b, a1, a2 = gate[:5]
        # A sixth field states a narrower span on purpose: a roof's edge or a
        # boundary wall's end is not a doorway and need not admit a body.
        layout.add_connection(gate_id, region_a, region_b, a1=a1, a2=a2,
                              min_width=gate[5] if len(gate) > 5 else 1024)
    # A roof that is seen over forbids a door beneath it (`bloodmap.skyline`).
    # Checked on the source, so the fault never reaches a frame.
    from bloodmap import skyline as _skyline
    leaks = _skyline.leaks_under_roofs(layout)
    print("rooms opening under a see-over roof:", leaks or "none")
    if leaks:
        raise SystemExit(f"{len(leaks)} room(s) under a see-over roof open "
                         f"onto the air that sees it: {leaks}")
    for spec in stack_links:
        build_stack_link(layout, spec, SEWER_CITY_D,
                         see_through=spec["see_through"])

    STAGE("set-pieces",
          "what each venue is furnished with: curtain, flames, sewer runs, pews, stock")
    import aldermack_house
    import l3_theatre
    ctx["manifest"]["fire_doors"] = l3_theatre.furnish_fire_doors(
        layout, ctx["fire_doors"])

    ctx["manifest"].update(aldermack_house.furnish(layout, ctx["aldermack_house"]))
    print("stage curtain:", ctx["manifest"]["stage_curtain"])
    print("west box curtain:", ctx["manifest"]["box_curtain"])
    print("stage light:", ctx["manifest"]["stage_light"].get("lines"))
    import l3_foundry
    l3_foundry.sprinkle(layout, ctx, dressing)
    ctx["manifest"]["loading_shutter"] = l3_foundry.furnish_loading_shutter(
        layout, UNDERPASS["loading"])
    # Declare the secret count.  A `secret=True` region emits the campaign's
    # per-sector wiring, but the *count* is a separate sprite transmitting
    # 64+n on channel 1 -- E3M1 carries one at command 73 (nine secrets).
    # Without it the player is never told a secret was found.
    layout.place_on_floor(
        "progression:secret_count", ctx["sewer_rooms"]["stash"],
        local=(0.5, 0.5), height_player_heights=0.5,
        type=0, picnum=0, cstat=129, status=0, x_repeat=64, y_repeat=64,
        # `motion.secret_total` rather than the fields by hand: this one was
        # missing `trigger_on`, so `SetSpriteState` never called evSend for it
        # and the count was never actually declared -- the player would never
        # have been told a secret was found. The rule caught it; the helper
        # cannot forget it.
        # The stash, flooded branch, arcade cache, Old Molly's Nest,
        # Plague Pit and Rat King's Shrine.
        behavior=motion.secret_total(8))
    # A flame in every light pool.  Three tiles were measured before this
    # one was chosen, and the measurements decided it:
    #   908  -- E3M1 puts it in streets 154 times, but a type census shows
    #           every instance is a kTrapExploder trap, not a lamp;
    #   641  -- a hall torch: 73 instances, all mounted 57k-64k above the
    #           floor (3.4 player heights) on walls.  Placed at head height
    #           in a pool it rendered as a thin floating sliver;
    #   506  -- 150 instances, modal repeats 64/64, cstat 128, and a height
    #           distribution from the floor up (median 18.8k ~ 1.1 player
    #           heights): the campaign's floor-standing flame.
    from bloodmap.decoration import DECORATION
    from bloodmap.art import read_art_directory
    flame_tile = 506
    flame = DECORATION[flame_tile]
    torch_fields = {"type": 0, "picnum": flame_tile,
                    "x_repeat": flame["x_repeat"], "y_repeat": flame["y_repeat"],
                    "cstat": 128, "shade": flame["shade"]}
    # A face sprite's z is its CENTRE, so a prop that stands on the ground
    # sits at half its own height -- not at the campaign's median height
    # above the floor, which is measured in rooms twice as tall as our
    # tunnels and left the flame hanging with its top through the ceiling.
    _art = read_art_directory("reference/blood")
    _flame_h = _art[flame_tile].height * flame["y_repeat"] * 4
    FLAME_STAND = (_flame_h / 2) / 16960
    # The sewer's own register, finds and flames.
    import l3_sewer

    def _attested_or_none(type_id):
        for source in ("E3M3", "E3M1", "E1M1"):
            try:
                return l3_foundry._attested(source, type_id)
            except LookupError:
                continue
        return None

    l3_sewer.populate(layout, ctx["sewer_rooms_new"], _attested_or_none,
                      torch_fields, flame_stand=FLAME_STAND)
    print("manhole covers:", l3_sewer.cover_manholes(layout, ctx["manholes"]))
    # Parametric detail runs along the sewer ring: the declaration is a
    # table of faces, the emission is a rhythm along the whole network.
    import runs as run_layer
    _sewer_runs = l3_sewer.detail_runs(layout, ctx["sewer_rooms_new"])
    _planned = [run_layer.estimate(r) for r in _sewer_runs]
    print(f"sewer runs planned: {len(_sewer_runs)} runs, "
          f"{sum(p['beats'] for p in _planned)} beats, "
          f"{sum(p['walls'] for p in _planned)} walls")
    print("sewer runs:", run_layer.emit_all(layout, _sewer_runs))

    import l3_church
    import l3_station as _station
    print("station:", _station.furnish(
        layout, ctx["theatre_street"].region_id, _attested_or_none))
    import l3_theatre as _saloon
    print("saloon stools:", _saloon.stools(layout, ctx["theatre_rooms"]))
    import l3_market as _harbour
    print("ship flag:", _harbour.fly_flag(layout))
    print("crypt breach:", l3_church.crack(
        layout, ctx["church_rooms"],
        l3_sewer.edge(ctx["sewer_rooms_new"], "w_leg", "west",
                      at=sum(__import__("props").room_rect(ctx["church_rooms"]["crypt"])[1::2]) / 2 / PU
                      ).region_id))
    print("church populated:", l3_church.populate(
        layout, ctx["church_rooms"], _attested_or_none, torch_fields,
        FLAME_STAND))
    import l3_mall
    print("arcade:", l3_mall.dress(layout, ctx["mall_rooms"],
                                   _attested_or_none))
    import l3_theatre
    print("theatre venues populated:", l3_theatre.populate(
        layout, ctx["theatre_rooms"], _attested_or_none, torch_fields,
        FLAME_STAND))

    # The station is a working building: give it braziers of its own,
    # bracketed to a wall like the campaign brackets them.
    import props
    station = ctx["station_rooms"]
    for name, room_obj, face in (("cellar", station["cellar"], "north"),):
        props.mount_on_wall(layout, f"light:station_{name}", room_obj, face)

    STAGE("street-lamps",
          "a lamp in every light pool and along every run")
    # A street lamp in every light pool.  506 is a wall bracket (92% of the
    # campaign's are within 512 units of a solid wall); a light pool is a
    # patch of brighter floor in the middle of a road, with no wall to
    # bracket to -- which is precisely where the owner saw torches flying.
    # Tile 640 is what DWE3M1 stands in its streets: a lamp fixture that
    # sits ON the ground, 593 instances campaign-wide at height +0.00.
    import lightpools
    #: A post does not stand in a doorway. A pool laid before a door keeps
    #: its light and gets no post: at 2.1 bodies the canteen's stood square
    #: in front of its door.
    from shapely.geometry import Point as _Pt, Polygon as _Poly
    _doors = [_Poly(_r.outer) for _r in layout.regions.values()
              if getattr(_r, "role", "") in ("doorway", "gateway")]
    ctx["manifest"]["pool_lamps"] = {"posts": 0, "light_only": 0}
    for index, region_id in enumerate(ctx["light_pools"]):
        _pool = layout.regions[region_id]
        _cx = sum(p[0] for p in _pool.outer) / len(_pool.outer)
        _cy = sum(p[1] for p in _pool.outer) / len(_pool.outer)
        if any(_d.distance(_Pt(_cx, _cy)) < LAMP_DOOR_CLEAR for _d in _doors):
            layout.add_light_source(
                f"light:pool_{index}", region_id, x=int(_cx), y=int(_cy),
                z=int(_pool.floor_z - props.STREET_LAMP_LIGHT * 16960),
                intensity=lightpools.LAMP_INTENSITY)
            ctx["manifest"]["pool_lamps"]["light_only"] += 1
            continue
        ctx["manifest"]["pool_lamps"]["posts"] += 1
        layout.place_on_floor(f"light:lamp_{index}", region_id,
                              local=(0.5, 0.5),
                              height_player_heights=props.height_of(props.STREET_LAMP),
                              light_intensity=lightpools.LAMP_INTENSITY,
                              light_height_player_heights=props.STREET_LAMP_LIGHT,
                              emits_light=True,
                              **props.fields(
                                  props.STREET_LAMP,
                                  x_repeat=props.STREET_LAMP_REPEAT,
                                  y_repeat=props.STREET_LAMP_REPEAT))
    # ---- street lamps into the derived slots -----------------------------
    # Wave 1 derived lamp positions from run length and placed nothing in
    # them; the slots were computed, reported and ignored. Same fixture as
    # the light-pool lamps -- tile 640, DWE3M1's ground-standing street lamp
    # -- but positioned by the street constructor rather than by a pool: one
    # per mined service interval along each roaded run, inset half a pavement
    # band so none overhangs the kerb.
    #
    # A slot is only used if it lands in a sector at all. A run's pavement is
    # not guaranteed to be there -- the road may have been cut around a light
    # pool or a threshold -- and a lamp in the void is worse than no lamp.
    lamp_slots = ctx["manifest"].get("streets", {}).get("lamp_slots", [])
    laid = ctx["manifest"].get("streets", {}).get("laid", [])
    district_of_run = {row["run"]: row["district"] for row in laid}
    street_of = {district: region_id
                 for region_id, district in ctx["street_regions"].items()}
    placed_lamps, skipped_lamps = 0, 0
    for slot in lamp_slots:
        #: The district the slot STANDS in.  A run on a seam has a pavement
        #: in each of two districts, and asking the run for its district put
        #: half its lamps outside the street they were handed to.
        district = next(
            (name for name, b in DISTRICT_BOUNDS.items()
             if b[0] < slot["x"] < b[2] and b[1] < slot["y"] < b[3]), None)
        region_id = street_of.get(district)
        if region_id is None:
            skipped_lamps += 1
            continue
        bounds = DISTRICT_BOUNDS[district]
        local = ((slot["x"] - bounds[0]) / (bounds[2] - bounds[0]),
                 (slot["y"] - bounds[1]) / (bounds[3] - bounds[1]))
        if not (0.0 <= local[0] <= 1.0 and 0.0 <= local[1] <= 1.0):
            skipped_lamps += 1
            continue
        #: ...and not in, or hard against, anything carved out of the
        #: street: a block, a porch, the church tower's ring, a carriageway.
        #: `place_on_floor` accepts the point and the compiler refuses the
        #: map, so the question is asked here.
        from shapely.geometry import Point, Polygon
        here = Point(slot["x"], slot["y"])
        _street = layout.regions[region_id]
        if (not Polygon(_street.outer).contains(here)
                or Polygon(_street.outer).exterior.distance(here) < 192
                or any(Polygon(hole).distance(here) < 192
                       for hole in _street.holes)
                #: ...nor before a door (a blind reviewer: "the lamp by the
                #: door stands almost in the doorway")
                or any(_d.distance(here) < LAMP_DOOR_CLEAR for _d in _doors)):
            skipped_lamps += 1
            continue
        try:
            layout.place_on_floor(
                f"light:street_lamp:{slot['id'].replace(':', '_')}", region_id,
                local=local,
                height_player_heights=props.height_of(props.STREET_LAMP),
                light_intensity=lightpools.LAMP_INTENSITY,
                light_height_player_heights=props.STREET_LAMP_LIGHT,
                emits_light=True,
                **props.fields(props.STREET_LAMP,
                               x_repeat=props.STREET_LAMP_REPEAT,
                               y_repeat=props.STREET_LAMP_REPEAT))
            placed_lamps += 1
        except Exception:
            skipped_lamps += 1
    ctx["manifest"]["street_lamps"] = {"placed": placed_lamps,
                                       "skipped": skipped_lamps,
                                       "slots": len(lamp_slots)}
    print("street lamps:", ctx["manifest"]["street_lamps"])

    STAGE("street-dressing",
          "levers by doors, ambient sound, the signature porthole, the monument")
    # Grime, last of the sprite passes so it fills whatever the district
    # modules left bare.  Sprites per sector was 0.60 against a campaign
    # 1.60-4.06; a room with one cultist and one flame in it reads as built
    # rather than lived in.
    # Signage before grime, so a sign owns its wall and the dressing pass
    # sees it as taken.  Blood's alphabet is a text primitive, not
    # decoration -- see signage.py.
    # Levers beside the street doors.  Blood has no door texture, so this
    # is the only thing on the facade that says the wall opens.
    import doorswitch
    print("underpass boards:", dress_underpass(layout))
    for placement_id, region_id, segment, channel in ctx["door_levers"]:
        doorswitch.place(layout, placement_id, region_id, segment, channel)
        _wires.by_channel(channel).when(_wiring.placement(placement_id), "push")
    print(f"door levers: {len(ctx['door_levers'])}")

    # Ambience.  The Blood campaign runs 23.6 ambient emitters per hundred
    # sectors; Gravesend had one.  Contexts are declared, not guessed.
    import ambience
    amb = []
    # The campaign's rate is 23.6 per hundred sectors, so at 159 sectors
    # the budget is about 38.  One emitter per room overshoots it by two
    # thirds; every other room lands on it.
    for region_id in ctx["street_regions"]:
        for spot in ((0.25, 0.3), (0.5, 0.6), (0.75, 0.35)):
            amb.append((region_id, "street", spot))
    for index, (name, room) in enumerate(ctx["sewer_rooms_new"].items()):
        _shut = layout.regions.get(room.region_id)
        if _shut is not None and int(_shut.ceiling_z) >= int(_shut.floor_z):
            continue                      # shut at rest: a blown hole's pieces
        if index % 2 == 0:
            amb.append((room.region_id, "sewer", (0.5, 0.5)))
    for index, (name, room) in enumerate(ctx["church_rooms"].items()):
        if name != "nave":
            continue
        if name.endswith(("_door", "_porch")) or index % 2:
            continue
        amb.append((room.region_id, "church", (0.5, 0.5)))
    amb.append((ctx["church_rooms"]["crypt"].region_id, "crypt", (0.5, 0.5)))
    for index, (name, room) in enumerate(ctx["theatre_rooms"].items()):
        if (name.endswith(("_door", "_porch")) or name.startswith("furniture")
                or index % 2):
            continue
        amb.append((room.region_id, "interior", (0.5, 0.5)))
    for name, room in ctx["station_rooms"].items():
        if name != "machine_hall":
            continue
        if name.startswith("_"):
            continue                      # the assembly handle, not a room
        amb.append((room.region_id, "works", (0.5, 0.5)))
    print("ambience:", ambience.fill(layout, amb))

    # The signature element: one thing repeated across the whole city is
    # what makes it read as one place.  DWE3M10 repeats its porthole 125
    # times; Gravesend had no such element at all.
    import fixtures as _fx
    _sig = 0
    for _key, _room in list(ctx["mall_rooms"].items())[:6]:
        if _key.endswith(("_door", "_porch")) or _key.startswith("service"):
            continue
        _fx.signature(layout, f"sig:mall_{_key}", _room.region_id)
        _sig += 1
    # not in a corridor's walk: its ceiling slopes, and the porthole hangs
    # from a flat ceiling's height
    _sewer_sig = [(k, r) for k, r in ctx["sewer_rooms_new"].items() if "_walk" not in k]
    for _key, _room in _sewer_sig[:8]:
        _fx.signature(layout, f"sig:sewer_{_key}", _room.region_id)
        _sig += 1
    print(f"signature portholes: {_sig}")

    # The monument, before the generic signage pass: it owns its own face.
    import l3_market
    _mon_rooms = ctx["market_dressing"].get("monument_rooms")
    if _mon_rooms:
        print("monument:", l3_market.dress_monument(layout, _mon_rooms,
                                                 street=ctx["market_street"]))
    _supermarket_rooms = ctx["market_dressing"].get("supermarket_rooms")
    if _supermarket_rooms:
        print("supermarket:", l3_market.dress_supermarket(
            layout, _supermarket_rooms))

    STAGE("green",
          "what stands on the turf, then every sign in the city")
    # ---- plant the green -------------------------------------------------
    # The ground is turf now; this is what stands on it. Every position comes
    # from a slot derived from the ground's own footprint, so a bigger green
    # is a fuller one and nothing is written out by hand.
    import park

    for area_id, (green_report, green_box, green_area) in ctx.get(
            "greens", {}).items():
        planted = park.plant(layout, green_report["ground"], green_box,
                             green_area, prefix=f"green:{area_id}",
                             solids=green_report.get("solids", ()),
                             outline=green_report.get("outline"))
        green_report["planted"] = planted
        print(f"green {area_id}:", planted, green_report["refused"])
    ctx["manifest"]["greens"] = {
        area_id: report for area_id, (report, _b, _a)
        in ctx.get("greens", {}).items()}

    import signage
    sign_rooms = {}
    for prefix, table in (("mall", ctx["mall_rooms"]),
                          ("theatre", ctx["theatre_rooms"]),
                          ("church", ctx["church_rooms"]),
                          ("sewer", ctx["sewer_rooms_new"]),
                          ("station", ctx["station_rooms"])):
        for name, room in table.items():
            if name.startswith("_"):
                continue
            sign_rooms[f"{prefix}:{name}"] = room
    # Street signs address the street region directly, by district name.
    for region_id, district in ctx["street_regions"].items():
        sign_rooms[f"street:{district}"] = region_id
    print("signage:", signage.write(layout, sign_rooms))
    STAGE("shops-and-goods",
          "fascia names, display lamps, venue detail, goods on fixtures, grime")
    # A shop is named on its fascia and lit behind its glass
    # (`glass.surround`; DukCity and E3M1, `references/dukcity-transfer.md`).
    import glass as _shopfronts
    print("fascia names:", _shopfronts.write_names(layout))
    print("display lamps:", _shopfronts.hang_lamps(layout))

    # Named interiors deliberately receive a small, coherent signature set;
    # the generic grime pass remains sparse.  The detail pass chooses only
    # props associated with each room's mined material combination and makes a
    # wall bracket the source of the station hall's generated light.
    import venue_detail
    venue_details = venue_detail.apply(layout, {
        "theatre": ctx["theatre_rooms"],
        "mall": ctx["mall_rooms"],
        "church": ctx["church_rooms"],
        "station": ctx["station_rooms"],
    })
    ctx["manifest"]["venue_details"] = venue_details
    print("venue detail:", venue_details)
    # AFTER the venues' own detail, so what was composed for a wall keeps
    # it: run before, two show bills took the Aldermack's board off its
    # foyer wall.
    # What stands on the counters, hangs on the walls and is posted in the
    # street: Blood's own town maps' decoration, set down as they set it
    # down (`goods.py`; owner, 2026-11-18: "more variety of assets").
    import goods as _goods
    _dressed = _goods.dress(layout, ctx["street_regions"], DISTRICT_BOUNDS)
    ctx["manifest"]["goods"] = _dressed
    print("goods:", {k: v for k, v in _dressed.items() if k != "refused"})
    for _line in _dressed["refused"]:
        print("   goods refused:", _line)

    # Goods, on the fixtures that carry any.  The composition chain ends
    # here: retail_row -> shop -> run -> fixture -> goods, and the last
    # step is one in seven, because the median fixture in all four detail
    # sources carries nothing.
    import templates, citytree
    from materials import INTERIORS as _INT
    _stocked = {"nodes": 0, "fixtures": 0, "stocked": 0}
    for _node, _depth in citytree.walk(program):
        if _node.node_id != "fittings":
            continue
        _shop = _INT["shop"]
        _got = templates.stock(layout, _node, wall=_shop.wall,
                               floor=_shop.floor, ceiling=_shop.ceiling)
        _stocked["nodes"] += 1
        _stocked["fixtures"] += _got["fixtures"]
        _stocked["stocked"] += _got["stocked"]
    print("goods:", _stocked)

    import dressing
    print("dressing:", dressing.dress(layout))
    # LAST of what is placed: it looks for free floor among all the rest
    import gameplay
    ctx["manifest"]["gameplay"] = gameplay.place(layout)
    print("gameplay:", ctx["manifest"]["gameplay"])

    STAGE("doors-and-windows",
          "door frames, detail panels, windows, building backs, actors seated")
    # Every moving door is a declared aperture, not a zero-height sector with a
    # door tile sprayed over whatever facade happens to face it.  The shared
    # compiler pass preserves each native type-600 sector and its behaviour,
    # adds the two reveal frames, and snaps its open height to whole door-art
    # repeats.  This is the reusable monastery correction, not a city-local
    # shading workaround.
    from bloodmap.aperture import frame_z_doors
    from bloodmap.rules import art_sizes
    house = ctx["aldermack_house"]
    cloth_reveals = frozenset(room.region_id for room in (house["curtain"], *house["wing_doors"]))
    import cabal_rite
    cloth_reveals |= cabal_rite.movers()                   # a well that sinks and flesh that parts are no doors
    cloth_reveals |= frozenset(_station.AVENUE_FRONT.get("gates", ()))   # one gate across two half arches: its own frame
    door_frames = frame_z_doors(layout, art_sizes=art_sizes(), already_framed=cloth_reveals)
    ctx["manifest"]["door_frames"] = len(door_frames["doors"])
    print("door frames:", len(door_frames["doors"]))
    import l3_shed as _late_shed
    import l3_station as _late_station
    import l3_mall as _late_mall
    for _region_id, _type in {**l3_church.LATE_TYPES,
                              **l3_sewer.LATE_TYPES,
                              **_late_mall.LATE_TYPES,
                              **_late_shed.LATE_TYPES,
                              **_late_station.LATE_TYPES}.items():
        layout.regions[_region_id].type = _type

    import facade_pass
    _backs = facade_pass.split_backs(layout, ctx["street_regions"])
    import detailing as _detailing
    print("detail panels:", _detailing.split(layout))
    import windows as _windows
    # (The blind recesses in the edge buildings, `_windows.cut`, are no
    # longer cut: the owner wants windows one can look through, and a blind
    # reviewer read the recesses as "a protrusion with misaligned texture".)
    _windows.NICHES.clear()
    ctx["manifest"]["windows"] = _windows.cut_through(
        layout, ctx["street_regions"], grade=GRADE)
    print("windows:", ctx["manifest"]["windows"])
    ctx["manifest"]["building_backs"] = _backs
    print("building backs:", _backs)
    ctx["manifest"]["seated_actors"] = _seat_actors(layout)
    ctx["manifest"]["flat_dropped"] = _drop_flat_overlaps(layout)
    print("actors seated:", ctx["manifest"]["seated_actors"],
          "flat sprites dropped for lying through another:",
          len(ctx["manifest"]["flat_dropped"]))

    STAGE("compile",
          "the layout becomes sectors, walls and sprites")
    # The light bomb is retired here (the owner, 2026-11-24): the light stage
    # writes the shades at the end, and of the 734 walls the bomb still
    # decided all but 21 were openings with nothing drawn on them.
    layout.lit_when_finished = LIGHTING == "model"
    _idle = _wires.close()
    if _idle:
        print("wires in the plan that nothing declared an end of:", _idle)
    ctx["manifest"]["wires"] = {"declared": circuit.apply(), "idle": _idle}
    print("wires declared:", [f"{row['name']} on {row['channel']}"
                              for row in ctx["manifest"]["wires"]["declared"]])
    if GROUND_SHADOWS:
        from bloodmap import sunlight as _sun_ground
        ctx["manifest"]["ground_shadows"] = _sun_ground.cast_shadows(
            layout, shade=GROUND_SUN[0], sunlit=GROUND_SUN[1])
        print("ground shadows:", {k: v for k, v in ctx["manifest"]["ground_shadows"].items()
                                   if k not in ("skipped", "shadowed")})
    compiled = layout.compile()
    # Held for `citytree --cost`: later passes mutate this level in
    # place, so the reference stays current.
    LAST_BUILD = (program, compiled)
    ctx["manifest"]["lighting"] = dict(compiled.lighting_report)
    STAGE("faces",
          "what every wall wears: facades, shop glass, the landmark's stone, the sea")
    # Per-building facade variation (E3M1 runs 13 tiles over its street
    # network; one per district read as one repeated building).
    import facade_pass
    print("facades:", facade_pass.apply(compiled.level, compiled,
                                        ctx["street_regions"],
                                        edge=_backs["edge"]))
    print("headers:", facade_pass.align_headers(compiled.level, compiled,
                                                ctx["street_regions"]))
    # Shop glass, after the facade pass so it survives what that painted.
    import aldermack_front, glass, l3_theatre, l3_market
    #: Only the pane's own plane, at the back of each sash pocket.  The
    #: street-side record of a window is the facade's (owner, 2026-11-17).
    spans = aldermack_front.glass_spans()
    for w in l3_theatre.WINDOWS:
        spans += glass.shopfront((w[3], w[4], w[5], w[6]), w[2])["panes"]
    import arcade
    spans += arcade.panes()
    for span, outward in zip(l3_market.SUPERMARKET_WINDOWS,
                             l3_market.SUPERMARKET_WINDOW_FACES):
        spans += glass.shopfront(span, outward)["panes"]
    #: ONE RECORD, ONE OWNER. The ledger is shared with the texture-frame
    #: pass below, so a record a pane claims is one the facade's surface frame
    #: will not re-derive. Without it the two passes overwrote each other and
    #: the order decided per record: fifteen of these 24 kept the scale
    #: `glaze` asked for and nine got the facade's.
    from bloodmap.surface import RecordOwner

    records = RecordOwner()
    report = glass.glaze(compiled.level, spans, owner="insert:shop_glass",
                         records=records, fit=True)
    #: E6M1 holds its glass in a 512-deep display recess with a sill 8192 up
    #: and a head 77824 down (s4/s64 against s52), so the facade crosses the
    #: mouth as a lintel band and the street never meets the pane. These spans
    #: are glazed on the room's own outward face instead, which is the owner's
    #: "shop glass sits directly on the facade line". Counted at every build
    #: rather than left to a report nobody re-runs; the carve is a tree change
    #: and is not done (roadmap, P13).
    from bloodmap.glass import panes_without_a_recess

    from bloodmap.glass import grille as _grille
    print("grilles:", _grille(compiled.level,
                              [l3_theatre.PAWN_GRILLE, UNDERPASS["bars"],
                               l3_foundry.CAGE["bars"]],
                              tile=l3_theatre.GRILLE_TILE))
    flush = panes_without_a_recess(compiled.level)
    report["panes_on_the_facade_line"] = len(flush)
    print("shop glass:", report)

    # The landmark wears its own stone, inside and out, as E1M5's does.
    import l3_church
    from resolution import CELLAR_FLOOR as _CELLAR_FLOOR
    print("church face:", facade_pass.face_landmark(
        compiled.level, l3_church.MASS, INTERIORS["church"].wall,
        deepest=_CELLAR_FLOOR))
    # ...and its roofs and yard wall wear theirs on the side that sees them.
    from bloodmap import skyline
    print("church roofs:", skyline.dress_steps(compiled.level, {
        compiled.allocations[region_id].sector_id: tile
        for region_id, tile in l3_church.ROOF_FACES.items()
        if region_id in compiled.allocations}))

    # ...and so does everything else that stands up out of a street: a market
    # stall, the fountain's rim, the monument's steps.  Each declares its own
    # wall tile and none of them ever wore it, because the side of a raised
    # floor is drawn from the record on the LOWER side -- the street's, which
    # carries the district's facade.  A stall's edge was therefore a slice of
    # a tenement: the cornice while the facade happened to hang from the top
    # of its run, the brick base once it stood on its floor.  Roofs are
    # dressed above; a carriageway is the lower side and wears its own kerb.
    _street_ids = set(ctx["street_regions"])
    _stands = {}
    for _region_id, _region in layout.regions.items():
        if (_region_id in _street_ids or not _region.parallax_ceiling
                or _region_id not in compiled.allocations
                or (getattr(_region, "intent", None) or {}).get("kind")
                in ("roof", "sky_apron", "roadway", "sky_backing")):
            continue
        _stands[compiled.allocations[_region_id].sector_id] = int(
            _region.wall_picnum)
    _street_sectors = {compiled.allocations[r].sector_id for r in _street_ids
                       if r in compiled.allocations}
    print("standing edges:", skyline.dress_steps(
        compiled.level, _stands, only_from=_street_sectors))
    # The ship's sides, from the water, the deck and each other: nothing
    # that looks up at a hull is a street.
    import l3_shed as _shed
    print("machines:", _shed.dress(compiled.level, compiled))
    from bloodmap.rules import art_sizes as _panel_sizes
    print("harbour flanks follow:", l3_market.flank_follow(
        compiled.level, compiled, ctx["market_street"].region_id,
        CITY_D, (4 * PU, 52 * PU)))
    print("detail paint:", _detailing.paint(compiled.level, compiled,
                                            _panel_sizes()))
    # The quay's face to the sea: dark planks, seen from the water.
    print("bulkhead:", skyline.dress_steps(
        compiled.level,
        {compiled.allocations[ctx["market_street"].region_id].sector_id:
         l3_market.BULKHEAD},
        only_from={compiled.allocations[l3_market.SEA["near"]].sector_id}))
    import l3_station as _station_dress
    print("station faces:", skyline.dress_steps(compiled.level, {
        compiled.allocations[region_id].sector_id: tile
        for region_id, tile in _station_dress.FACES.items()
        if region_id in compiled.allocations}))
    _ghost_track = (region_id for region_id, region in layout.regions.items()
                    if region.layer == "ghost_station" and region.floor_picnum == _station_dress.TRACK)
    print("station:", _station_dress.dress(compiled.level, compiled, keep_tracks=_ghost_track))
    import phantom_terminus as _phantom_finish
    _phantom_finish.apply_surface_palette(layout, compiled)
    print("sarcophagus faces:", skyline.dress_steps(compiled.level, {
        compiled.allocations[region_id].sector_id: tile
        for region_id, tile in l3_church.CRYPT_FACES.items()
        if region_id in compiled.allocations}))
    print("ship sides:", skyline.dress_steps(compiled.level, {
        compiled.allocations[region_id].sector_id: tile
        for region_id, tile in l3_market.SHIP_FACES.items()
        if region_id in compiled.allocations}))
    print("outer sea:", l3_market.close_outer_sea(compiled.level, compiled))
    # An end wall's face is LIT and BLOCKING, as E3M1's are: its three street
    # ends (s0, s339, s343) wear their facade at shade -8, cstat 1, on every
    # face a road or a pavement sees, against 24 to 34 on the masonry beside
    # them.  It is the thing at the end of a long view; at the street's own
    # shade a blind reviewer still saw "an untextured dark block".
    _ends = {compiled.allocations[_region_id].sector_id
             for _region_id, _region in layout.regions.items()
             if (getattr(_region, "intent", None) or {}).get("kind")
             == "end_wall" and _region_id in compiled.allocations}
    _lit = 0
    for _wall in compiled.level.walls:
        _fields = _wall["fields"]
        if int(_fields.get("next_sector", -1)) in _ends:
            _nxt = int(_fields.get("next_wall") or -1)
            _owner_is_end = False
            if _nxt >= 0:
                _owner_is_end = int(compiled.level.walls[_nxt]["fields"].get(
                    "next_sector", -1)) in _ends
            if _owner_is_end:
                continue                       # the join between two masses
            _fields["shade"] = END_WALL_SHADE
            _fields["cstat"] = int(_fields["cstat"]) | 1
            _lit += 1
    print("end wall faces lit:", _lit)

    STAGE("alignment",
          "one texture frame per run of walls; who owns each wall record")
    # Texture alignment.  Blood advances a wall's horizontal texture
    # coordinate by x_repeat*8 along the wall, so a run only continues if
    # the next wall's panning picks up where the last left off.  Without
    # this every wall starts at panning zero and the pattern restarts at
    # every vertex -- including the vertices that are not corners at all,
    # the ones where a long facade was split to hang an entrance off it.
    # Runs first, then floor-anchoring for the walls that tile unevenly.
    # Must come after facade_pass, which decides the picnums.
    from bloodmap.texture_align import wall_art_sizes
    from bloodmap.texture_frame import frame_map, frame_raised_solids
    art_sizes = wall_art_sizes("reference/blood")
    # ONE FRAME PER RUN, resolved in closed form from world coordinates.
    #
    # This replaces `align_wall_runs` and the floor-anchored `align_wall_
    # textures` pass together, and the reason is the owner walk: those two
    # fought each other. The run pass carried x inside a sector loop and
    # refused every portal-to-portal join but one opted-in concourse; the
    # anchor pass then set y from each wall's OWN sector height, which breaks
    # the vertical phase at every kerb, sill and lintel -- 31% of this map's
    # bend solid-portal joins continued in y against the campaign's 61%.
    #
    # A run here is what the editor's traversal says it is (`ED32_AutoAlign
    # Walls`, xmapedit/src_blood/xmpmaped.cpp:3096-3144): it steps across
    # `next_wall` into the neighbouring sector, so a facade continues past a
    # doorway instead of restarting at it. The concourse needs no opt-in any
    # more, because portal walls were never the exception -- they were the
    # case the old pass could not express.
    # THE DISTRICT FRAME (owner queue item 16, resolved). `world_align_facades`
    # used to run after this and phase every street wall from its own world
    # coordinate -- which is what makes a bay grid exist, and which fought the
    # run carry for the same field with no decision between them. The two were
    # never really in conflict: a run whose U-ORIGIN is a world point gives the
    # district-wide bay grid AND accumulates across its own doorways. So the
    # street fronts are named here and `frame_map` gives them a world u0.
    district_walls = set()
    for region_id in ctx["street_regions"]:
        allocation = compiled.allocations.get(region_id)
        if allocation is not None:
            district_walls.update(int(w) for w in allocation.wall_ids)
    #: ...and every material STANDS ON ITS FLOOR (owner, 2026-11-17: "be
    #: careful about meaningful texture alignment"). The run's vertical
    #: origin used to be its first wall's peg, an accident of wall order: the
    #: market hall wore its dado under the ceiling, and a facade's arched
    #: ground storey began wherever the run did.
    #: ...and a wall drawn in two bands hangs both from its own ceiling,
    #: BEFORE the frames read where each wall hangs from.
    from bloodmap.texture_frame import peg_split_bands
    _bands = peg_split_bands(compiled.level, records=records,
                             owner="surface:facade")
    ctx["manifest"]["split_bands"] = {k: v for k, v in _bands.items()
                                      if k != "walls"}
    print("walls in two bands hung from their own ceiling:",
          ctx["manifest"]["split_bands"])
    print("texture frames:", frame_map(compiled.level, art_sizes=art_sizes,
                                       world_phase=district_walls,
                                       records=records, owner="surface:facade",
                                       v_anchor="floor"))
    print("record owners:", records.report())
    # Crate tops start their tile at the crate's own corner. 71% of the
    # campaign's 110 raised crate tops do; this map's eleven did not, so a
    # 1024 box off the 1024 world grid wore a cut tile.
    print("crate tops:", frame_raised_solids(compiled.level, art_sizes=art_sizes))
    print("carriage records kept:", _station_dress.keep(compiled.level))
    print("harbour flanks aligned:", l3_market.flank_align(
        compiled.level, GRADE, art_sizes))

    # LightBomb now runs inside ``layout.compile`` from the sources declared by
    # each emitting placement.  Flicker remains a distinct runtime effect: it
    # animates a lamp's generated base shade but does not decide that base.
    from bloodmap.lighting import flicker_lit_sectors
    from l3_foundry import LAMP_TILE
    print("lighting flicker:", flicker_lit_sectors(
        compiled.level, tiles={LAMP_TILE, 506, 640, 1701}))
    print("lighting lightbomb:", compiled.lighting_report)

    STAGE("apertures",
          "openings: sewer mouths, lintels, pilasters, niches, wall sprites")
    # The sewer's mouths.  Tile 194 is E3M3's circular tunnel lining and it
    # uses it in exactly one place: the short opening where one channel
    # meets another, 29 walls of 1,128, with a band of wall above.
    import sewerkit
    _sewer_sectors = {
        int(alloc.sector_id) for region_id, alloc in compiled.allocations.items()
        if region_id.startswith("region:gravesend/sewer/")
        # the railway is under the sewer and no part of its tunnels
        and not region_id.startswith("region:gravesend/sewer/ghost_station/")}
    _mouths = sewerkit.line_mouths(compiled.level, _sewer_sectors)
    print("sewer mouths:", _mouths)
    ctx["manifest"]["sewer_mouths"] = _mouths

    # Openings, against the grammar's own audit.  `frame_z_doors` above
    # builds the reveals; this is the other half -- reading the finished map
    # back and repainting the band above every mouth with the wall it
    # interrupts, which is what 47% of Blood's apertures do.
    import apertures
    _before = apertures.report(compiled.level.to_disk_map())
    print("apertures before:", _before)
    print("lintels:", apertures.continue_lintels(compiled.level,
                                                 compiled.level.to_disk_map()))
    print("the rite's rims put back:", cabal_rite.keep(compiled.level, compiled))
    import settling_hall
    print("the settling hall's stone put back:", settling_hall.keep(compiled.level, compiled))
    print("the arcade's fronts put back:", arcade.keep(compiled.level, compiled))
    # AFTER the lintel pass, which takes a sector's solid wall for its
    # facade: stood before it, one pilaster outvoted two short jambs and the
    # pawnbroker's whole surround was repainted in the pilaster tile.
    print("pilasters:", glass.stand_pilasters(compiled.level,
                                              compiled.allocations))

    import fixtures as _fixtures
    from bloodmap.rules import art_sizes as _art_sizes
    print("window niche walls:", _windows.paint(compiled.level, compiled))
    print("window glass and bars:", _windows.glaze(compiled.level))
    print("shelf frames:", _fixtures.frame_shelves(
        compiled.level, compiled, layout, _art_sizes()))
    disk = compiled.level.to_disk_map()
    import motion_sounds
    ctx["manifest"]["motion_sounds"] = motion_sounds.apply(disk, compiled.allocations, circuit)
    # Wall sprites, as rectangles on the surfaces they hang from.  This was
    # 18.86 clashing pairs per 100 against a campaign 0.0-8.0, with 26
    # sprites entirely hidden behind another where no campaign map has more
    # than 4 -- St Gallow's sign was written straight through its hanging.
    # `wallplane` reserves the rectangle each sprite actually draws, so the
    # number is a standing check rather than a one-off fix.
    import tools.mine_wall_sprites as _walls
    _wall_report = _walls.survey(disk, _walls._art())
    print(f"wall sprites: {_wall_report['wall_sprites']} on "
          f"{_wall_report['planes']} planes, "
          f"{_wall_report['clashing_pairs']} clashing pairs "
          f"({_wall_report['clash_rate_per_100_wall_sprites']} per 100), "
          f"{_wall_report['fully_hidden']} fully hidden")
    ctx["manifest"]["wall_sprites"] = {
        k: v for k, v in _wall_report.items() if k != "worst"}
    _after = apertures.report(disk)
    print("apertures after:", _after)
    ctx["manifest"]["apertures"] = _after
    STAGE("gates",
          "nothing is built: rules, read-back, swept closure, sprite fit, character")
    # The corpus-graded rule registry, whose severities derive from measured
    # campaign violation rates rather than from anyone's opinion.  It was
    # sitting unused: `evaluate` returns nothing at all unless `rules_blood`
    # has been imported, because the registry is populated by that import's
    # side effect -- so "0 diagnostics" was silence, not a clean map.
    import bloodmap.rules_blood            # noqa: F401  (registers the rules)
    from bloodmap.rules import RULES
    from bloodmap.rules import evaluate as _evaluate_rules
    _diags = _evaluate_rules(disk)
    _by_sev = collections.Counter(d.severity for d in _diags)
    _by_code = collections.Counter((d.severity, d.code) for d in _diags)
    # The authoring-loop law: read every mechanism back through the same
    # conformance the zoo uses and compare it against what it was meant to
    # be. A deviation is a finding about the level or about our template, and
    # both get reported rather than papered over.
    from bloodmap.conformance import measure_curtain

    _curtains = []
    for _index, _sector in enumerate(disk.sectors):
        if int(_sector.fields["type"]) != 614:
            continue
        _start = int(_sector.fields["wall_ptr"])
        _count = int(_sector.fields["wall_count"])
        if not any(int(disk.walls[w].fields["picnum"]) == 146
                   for w in range(_start, _start + _count)):
            continue
        _found = measure_curtain(disk, _index)
        _curtains.append({"sector": _index, "measured": _found.measured,
                          "deviations": [str(d) for d in _found.deviations]})
    if _curtains:
        ctx["manifest"]["curtain_conformance"] = _curtains
        for _read in _curtains:
            print(f"curtain s{_read['sector']}: {_read['measured']}")
            for _line in _read["deviations"]:
                print(f"    DEVIATES {_line}")

    # The swept-state gate over the FINAL disk, DragPoint closure included.
    # `layout.compile()` ran it before the facade passes split walls, and it
    # sweeps everything a motion DRAGS (triggers.cpp:817-854 walks nextwall,
    # so the auditorium's hole loop moves with the curtain's tips). A
    # neighbour that turns inside out at any pose fails the build here.
    from bloodmap.swept_state import run as _swept_run
    _swept = _swept_run(disk)
    ctx["manifest"]["swept_closure"] = {
        "mechanisms": _swept["mechanisms"], "sound": _swept["sound"],
        "deforming_neighbours": _swept["deforming_neighbours"],
        "problems": _swept["problems"], "notes": _swept["notes"]}
    print(f"swept closure: {_swept['mechanisms']} mechanisms, "
          f"{_swept['deforming_neighbours']} deform a neighbour, "
          f"{len(_swept['problems'])} problem(s)")
    for _line in _swept["problems"]:
        print(f"    BREAKS {_line}")
    if _swept["problems"]:
        print("FAIL: a mechanism breaks geometry it drags; the map was not written")
        return 1

    # THE AUTHORING-LOOP LAW, over every mechanism this level declared.  The
    # curtain check above asks one construct one question; this reads the
    # FINISHED disk back against what every region declared -- sector type,
    # XSECTOR, declared motion set, the DragPoint closure over the whole
    # travel, the fabric's visible band, and the state pair -- and refuses
    # the build on a difference.  It runs HERE, after the facade passes have
    # split walls and after the lintel and wall-sprite passes have edited the
    # compiled level, because the gate inside `layout.compile()` looked at
    # the geometry before all of that.
    from bloodmap.readback import lost_tiles_as_differences, read_back
    from bloodmap.readback import sentences_from_layout

    _claims = sentences_from_layout(compiled, layout=layout)
    _checked = read_back(disk, _claims, map_name="blood-city-current.MAP")
    ctx["manifest"]["readback"] = _checked.to_dict()
    print(_checked.report())
    if not _checked.agrees:
        print(f"FAIL: {len(_checked.differences)} read-back difference(s); "
              f"the map was not written")
        return 1

    print(f"rules: {len(_diags)} diagnostics {dict(_by_sev)}")
    for (_sev, _code), _n in _by_code.most_common():
        if _sev in ("error", "warning"):
            print(f"    {_sev:8s} {_code:38s} {_n}")
    ctx["manifest"]["rules"] = {
        "total": len(_diags),
        "by_severity": dict(_by_sev),
        "by_code": {f"{a}:{b}": c for (a, b), c in _by_code.items()},
        # Where each error and warning is, so `status.py` can hand an agent
        # the finding and not only the count of them.
        "open": [{"severity": d.severity, "code": d.code, "at": d.location,
                  "says": d.message}
                 for d in _diags if d.severity in ("error", "warning")],
    }
    # The rendering law, called out by name rather than left inside the
    # diagnostic count.  `bloodmap.render_slots` says which band the engine
    # draws each wall tile on; a tile the map authors on walls and shows on
    # no band anywhere is a material that was chosen and then lost.  This is
    # how the stage curtain's fabric vanished, and the same reading finds the
    # districts' `opening` tiles on flush doorway thresholds.  It is printed
    # and recorded, not fatal, because five of those thresholds are still
    # outstanding -- see reports/owner-review-queue.md.
    _lost = RULES["wall-tile-is-drawn-somewhere"].check(disk)
    ctx["manifest"]["lost_wall_tiles"] = {
        "population": _lost.population,
        "tiles": [v.location for v in _lost.violations],
    }
    # These are READ-BACK DIFFERENCES, not style warnings: the map claims a
    # material and the engine draws something else.  Printed in the same
    # vocabulary as every other difference so they cannot be read as one
    # diagnostic among hundreds -- which is how the stage curtain's fabric
    # stayed invisible through every gate the project had.  Non-blocking
    # ONLY because five flush doorway thresholds are still outstanding with
    # the owner (reports/owner-review-queue.md item 9); the moment that is
    # decided, this list belongs above the `return 1`.
    _lost_diffs = lost_tiles_as_differences(_lost, mechanism="(whole map)")
    ctx["manifest"]["lost_wall_tiles"]["as_readback_differences"] = [
        str(_d) for _d in _lost_diffs]
    print(f"READ-BACK DIFF (non-blocking, owner-queue item 9): "
          f"{len(_lost.violations)} of {_lost.population} authored wall "
          f"tiles are drawn on no band anywhere")
    for _d in _lost_diffs:
        print(f"    DIFF {_d}")
    _lines = ['# Rule registry, at build time', '', '`bloodmap.rules.evaluate`, severities derived from measured campaign', 'violation rates. Requires `bloodmap.rules_blood` to be imported: the', "registry is populated by that import's side effect, so a bare", '`evaluate` returns silence rather than a clean map.', '']
    _lines += [f"- **{d.severity}** `{d.code}` -- {d.message} ({d.location})"
               for d in sorted(_diags, key=lambda d: (d.severity, d.code))]
    (pathlib.Path(__file__).resolve().parents[1] / "reports" / "rules.md").write_text(
        chr(10).join(_lines), encoding="utf-8")
    # Does every sprite fit where it was put, as the engine DRAWS it? The
    # owner found sunk goods, a statue through a shelf's head and letters
    # written through pictures by walking the map; nothing here could have
    # said so (`tools/sprite_fit.py`, thresholds from the town maps).
    from tools import sprite_fit as _fit
    _lint = _fit.lint(disk)
    ctx["manifest"]["sprite_fit"] = {
        "rates": _lint["rates"],
        **{kind: [{k: row[k] for k in ("sprite", "tile", "sector")
                   if k in row} for row in _lint[kind]]
           for kind in ("sunk", "through", "squeezed", "lifted")},
        "overlaps": [{"sprites": [o["a"], o["b"]], "tiles": list(o["tiles"]),
                      "sector": o["sector"]} for o in _lint["overlaps"]],
        "flat_overlaps": [{"sprites": [o["a"], o["b"]],
                           "tiles": list(o["tiles"]), "sector": o["sector"]}
                          for o in _lint["flat_overlaps"]],
        "sunk_actors": _lint["sunk_actors"],
        "on_travelling_floor": _lint["on_travelling_floor"]}
    # What this map does that the campaign and the owner's maps never show
    # (`bloodmap.tile_contexts.novel`): each is a discovery to catalogue
    # with `tools.tile_contexts record`, or a mistake to fix. The owner,
    # 2026-11-20: "agents should be able to discover things, catalogise them
    # and easily browse them".
    from bloodmap import tile_contexts as _contexts
    _novel = _contexts.novel(disk)
    _new = [r for r in _novel if r["evidence"] is None]
    _outside = [r for r in _novel if r["evidence"] is not None]
    ctx["manifest"]["tile_contexts"] = {
        "new": [{k: r[k] for k in ("tile", "slot", "place", "count", "first")}
                for r in _new],
        "outside": [{"tile": r["tile"], "slot": r["slot"], "place": r["place"],
                     "count": r["count"], "source": r["evidence"]["source"],
                     "maps": r["evidence"].get("maps")} for r in _outside],
        "misfit": [{"tile": r["tile"], "slot": r["slot"], "place": r["place"],
                    "count": r["count"], "first": r["first"], "said": r["misfit"]}
                   for r in _novel if r.get("misfit")]}
    print("tile uses nobody has shown:", len(_new), "shown only outside the campaign:",
          len(_outside), "(python -m tools.tile_contexts discover <MAP>)")
    print("decoration on a travelling floor:",
          len(_lint["on_travelling_floor"]))
    print("sprite fit:", _lint["rates"], "overlapping pairs:",
          len(_lint["overlaps"]), "flat pairs:", len(_lint["flat_overlaps"]),
          "sunk actors:", len(_lint["sunk_actors"]))
    from tools import catalog as _catalog
    ctx["manifest"]["directional_floors"] = _catalog.directional_floor_faults(disk)
    print("floors laid across their run:", ctx["manifest"]["directional_floors"])
    print("papers and boards hung on no wall:", _lint.get("unbacked", []))
    import character as _character
    _sheet = _character.sheet(disk)
    # The wiring read back off the finished map with the campaign's reader:
    # where it and the declarations differ, what is wired and can never
    # send, and every channel nobody declared the purpose of.
    _wires = circuit.read_back(compiled, disk)
    ctx["manifest"]["wires"].update(_wires)
    print(f"wires: {len(_wires['wires'])} declared, "
          f"{'agree' if _wires['agrees'] else 'DISAGREE'} with the map; "
          f"{len(_wires['undeclared'])} channel(s) nobody declared; "
          f"{len(_wires['silent'])} sender(s) that can never send")
    ctx["manifest"]["character"] = _sheet
    for _name, _row in _sheet["places"].items():
        print(f"character: {_name}: {_row['layer_count']} layers "
              f"(campaign p25 {_row['campaign_p25']}, p50 "
              f"{_row['campaign_p50']}); lacks {_row['missing'] or 'nothing'}")
    for _name, _row in _sheet["places"].items():
        print(f"scale: {_name}: {_row['metres'][0]} x {_row['metres'][1]} m, "
              f"{_row['metres'][2]} m high; cramped: "
              f"{_row['cramped'] or 'no'}")
    print("character: built without a study:", _sheet["unstudied"])
    print("character: thin", _sheet["thin"], "unfound", _sheet["unfound"],
          "dangling channels", _sheet["dangling_channels"])
    print("character: engine channels used as the level's own wire:",
          _sheet["engine_channels_wired"] or "none")
    STAGE("write",
          "the map, its sector tags, the manifest and the status")
    # THE OVERLAYS (the sun's shadows on the ground, declared on the layout
    # before compile): cut into the finished map here, after every pass and
    # gate has seen each region whole (`bloodmap.overlays`). Every other
    # sector keeps its index. The cut is then held to the same gates: it may
    # add no rule warning or error and break no mechanism's sweep.
    _overlay_report = {}
    if layout.overlays:
        from bloodmap import overlays as _overlays
        _overlay_report = _overlays.lay(disk, compiled)
        _cut_diags = _evaluate_rules(disk)
        _cut_by = collections.Counter((d.severity, d.code) for d in _cut_diags
                                      if d.severity in ("error", "warning"))
        _was_by = collections.Counter((d.severity, d.code) for d in _diags
                                      if d.severity in ("error", "warning"))
        _added = _cut_by - _was_by
        _cut_swept = _swept_run(disk)
        print("overlays laid:", {k: v for k, v in _overlay_report.items()
                                 if k not in ("parent", "refused")},
              "refused:", len(_overlay_report["refused"]))
        if _added or _cut_swept["problems"]:
            print("FAIL: the overlays added", dict(_added), "and broke",
                  _cut_swept["problems"], "; the map was not written")
            return 1
        ctx["manifest"]["overlays"] = {
            k: v for k, v in _overlay_report.items() if k != "parent"}
    # THE LIGHT ON THE FACES (owner, 2026-11-20: "there is no real direction
    # of natural light and shadows in the city exterior"). Last, so nothing
    # after it repaints a wall. `bloodmap.sunlight` says what the campaign
    # does and why the first version (one sun at 45 degrees, facades
    # darkened to the ground) was preferred by a blind reader in only 4 and 8
    # of 23 views; the second, at a step of 8 on facades at shade 9, was
    # invisible. The owner asked for it rebuilt at the measured scale.
    from bloodmap import sunlight as _sun
    _lit_parent: dict = {}
    if LIGHTING == "model":
        # THE LIGHT AS A SCENE (`bloodmap.light_stage`), from the finished
        # map: which room each sector is in comes from the compiled layout,
        # its kind of light from `lights.py`. It cuts only sectors that
        # carry nothing but their shade, and is held to the same gates.
        from bloodmap import light_stage as _light_stage
        import lights as _lights
        import cabal_rite as _cabal
        _region_of = {_a.sector_id: _rid for _rid, _a in sorted(compiled.allocations.items())}
        for _piece, _parent in sorted(_overlay_report.get("parent", {}).items()):
            _region_of[int(_piece)] = _region_of.get(int(_parent), "")
        _was_by = collections.Counter((d.severity, d.code) for d in _evaluate_rules(disk)
                                      if d.severity in ("error", "warning"))
        _lit = _light_stage.run(disk, _region_of, _lights.rule_for, keep=_lights.own_light,
                                    lamp_scale=_lights.lamp_scale, room_key=_lights.room_key,
                                    groups=_phantom_finish.light_groups(compiled) + _cabal.light_groups(compiled))
        print("lamps that switch:", _lit["switched"])
        print("floors under fangs evened:", _cabal.even(disk, compiled))
        _cut_parent = {int(k): int(v) for k, v in _overlay_report.get("parent", {}).items()}
        _lit_parent = {int(k): _cut_parent.get(int(v), int(v)) for k, v in _lit["parent"].items()}
        _lit_by = collections.Counter((d.severity, d.code) for d in _evaluate_rules(disk)
                                      if d.severity in ("error", "warning"))
        _lit_added = _lit_by - _was_by
        _lit_swept = _swept_run(disk)
        _unnamed = _lights.unnamed(_lit["rooms"])
        ctx["manifest"]["light_stage"] = {
            **{k: v for k, v in _lit.items() if k != "parent"},
            "pieces": len(_lit_parent), "default_rooms": _unnamed}
        print("light stage:", {k: _lit[k] for k in ("sectors_before", "sectors", "walls_before",
                                                     "walls", "sprites_before", "sprites")},
              "rooms lit:", len(_lit["rooms"]), "by the default:", _unnamed or "none")
        if _lit_added or _lit_swept["problems"]:
            print("FAIL: the light stage added", dict(_lit_added), "and broke",
                  _lit_swept["problems"], "; the map was not written")
            return 1
        _measured = _sun.measure(disk)
        _light = {"before": _measured, "after": _measured}
    elif LIGHTING == "faces":
        _light = _sun.apply(disk)
    else:
        _measured = _sun.measure(disk)
        _light = {"before": _measured, "after": _measured}
    ctx["manifest"]["sunlight"] = {
        "mode": LIGHTING,
        **{k: v for k, v in _light.items() if k not in ("before", "after")},
        "before": _light["before"], "after": _light["after"]}
    print("sunlight:", LIGHTING, {k: _light["after"][k] for k in (
        "wall_sd", "corner_equal", "corner_step", "within_building", "tile_sd")})
    out_dir = pathlib.Path(__file__).resolve().parent
    write_map(disk, out_dir / "city-skeleton.MAP")
    write_map(disk, out_dir / "blood-city-current.MAP")
    # What each sector IS, beside the map, so `tools/whatif.py` can make a
    # variant by name ("the shop displays", "the carriageways") instead of
    # by a list of sector numbers that changes with every build.
    import json as _json
    import glass as _glass_tags
    _tags: dict = {}
    for _region_id, _region in layout.regions.items():
        _kind = (getattr(_region, "intent", None) or {}).get("kind")
        _allocation = compiled.allocations.get(_region_id)
        if _kind and _allocation is not None:
            _tags.setdefault(str(_kind), []).append(_allocation.sector_id)
        if _allocation is not None and _region.layer == "ghost_station":
            _tags.setdefault("phantom_terminus", []).append(_allocation.sector_id)
        if _allocation is not None and _region.layer == "rite":
            _tags.setdefault("cabal_rite", []).append(_allocation.sector_id)
    # a sector the overlays cut off its region is still that region
    for _piece, _parent in list(_overlay_report.get("parent", {}).items()) + sorted(_lit_parent.items()):
        for _sectors in _tags.values():
            if int(_parent) in _sectors:
                _sectors.append(int(_piece))
    _tags["lit_shop"] = sorted({
        compiled.allocations[_front["shop"]].sector_id
        for _front in _glass_tags.FRONTS
        if _front["lit"] and _front["shop"] in compiled.allocations})
    for _name in ("city-skeleton", "blood-city-current"):
        (out_dir / f"{_name}.tags.json").write_text(
            _json.dumps({k: sorted(v) for k, v in sorted(_tags.items())},
                        indent=1), "utf-8")
    import json
    # The stages that ran, by name. Their seconds are this machine's and this
    # run's, so they go beside the suite's log and not into what is committed.
    ctx["manifest"]["stages"] = STAGE.close()
    _timings = ROOT / "work" / "blood-city-stages.json"
    _timings.parent.mkdir(exist_ok=True)
    _timings.write_text(json.dumps(STAGE.rows, indent=1) + "\n", encoding="utf-8")
    _slow = sorted(STAGE.rows, key=lambda row: -row["seconds"])[:4]
    print(f"stages: {len(STAGE.rows)} in "
          f"{sum(row['seconds'] for row in STAGE.rows):.0f} s; slowest "
          + ", ".join(f"{row['name']} {row['seconds']:.1f}" for row in _slow)
          + "  (python projects/blood-city/level/status.py --stages)")
    (out_dir.parents[0] / "reports" / "build-manifest.json").write_text(
        json.dumps(ctx["manifest"], indent=2), encoding="utf-8")
    print(f"sectors {len(disk.sectors)} walls {len(disk.walls)} "
          f"sprites {len(disk.sprites)}")
    print(f"wrote {out_dir / 'city-skeleton.MAP'} (+ blood-city-current.MAP)")
    # Last, where it all stands, as data: every place and every open item,
    # for the agent that starts the next session knowing none of the above.
    import status as _status
    _stand = _status.write()
    print(f"status: {len(_stand['places'])} places, {len(_stand['open'])} open "
          f"{_stand['open_by_kind']} -> reports/status.json, reports/STATUS.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
