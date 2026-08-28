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
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

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
#: level start (blood.cpp:750).  So a stack marker parked on statnum 10 is
#: deleted before the link is ever registered: no link, solid floor, no way
#: down.  All six stack markers in E3M1 sit on statnum 0 with cstat 128,
#: and warpInit sets the invisible bit itself.  Filed as a grammar request.
STACK_MARKER_STATNUM = 0        # kStatDecoration
STACK_MARKER_CSTAT = 128        # the campaign's stored value

from bloodmap.rules_blood import MIRROR_TILE
import city_plan
from city_plan import plan
from facade_pass import BAY as FACADE_BAY, snap_opening


def facade_pass_bay() -> int:
    return FACADE_BAY
from resolution import (
    CELLAR_DROP, CELLAR_FLOOR, DISTRICT_STYLE, GRADE, PIT_LANDING_DEPTH, PU,
    SEWER_CLEAR, SEWER_FLOOR, SEWER_PARK_D, SKY_TILE, STREET_SKY, WIDTH_UNITS,
    FLOOR_BOARDWALK, FLOOR_GROUND,
)
from materials import FACADES, INTERIORS, MASONRY, SEWER, SEWER_WET

COMPASS = dict(zip(RECT_FACES, range(4)))

#: District bounds in units, seamed on street centerlines (derived from the
#: same L1 grid the plan states; nothing here is a fresh literal).
SEAM_ROW = (city_plan.Y_ROWST + city_plan.ROW / 2) * PU
SEAM_MARKET = (city_plan.Y_MARKST + city_plan.STREET / 2) * PU
SEAM_AVENUE = (city_plan.X_AVENUE + city_plan.AVENUE / 2) * PU
CITY_W = city_plan.CITY_W * PU
CITY_D = city_plan.CITY_D * PU

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


def build():
    data = plan()
    city = LevelProgram(
        "gravesend", name="blood-city-skeleton", visibility=800,
        style=Style(wall_picnum=DISTRICT_STYLE["market_slip"]["wall_picnum"],
                    floor_picnum=FLOOR_BOARDWALK, ceiling_picnum=SKY_TILE,
                    parallax_ceiling=True, floor_z=GRADE,
                    clear_height=STREET_SKY, floor_shade=32),
    )

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
        # The jamb rule (74% of campaign multi-tile rooms): this region's own
        # openings wear the material's opening tile, its field walls the
        # facade.  One statement per district, not per doorway.
        room = assembly.room(
            "streets",
            [(0, 0), (bx1 - bx0, 0), (bx1 - bx0, by1 - by0), (0, by1 - by0)],
            role="exterior", faces=dict(COMPASS),
            frame=Frame(int(bx0), int(by0)),
            region_kwargs=facade.region_kwargs(),
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
                room.carve([(ax0 - bx0, ay0 - by0), (ax1 - bx0, ay0 - by0),
                            (ax1 - bx0, ay1 - by0), (ax0 - bx0, ay1 - by0)])
        streets[district] = room
        district_of[district] = assembly

    # ---- carved areas: the cemetery as a walled, gated ground -------------
    gates = []
    grounds = {}
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

    city.connect(theatre_st.face("south"), oldcross_st.face("north"),
                 connection_id="connection:seam_row")
    city.connect(theatre_st.face("east"), foundry_st.face("west"),
                 connection_id="connection:seam_avenue_north")
    city.connect(oldcross_st.face("east"), foundry_st.face("west"),
                 connection_id="connection:seam_avenue_mid")
    city.connect(oldcross_st.face("south"),
                 market_st.face("north", at=SEAM_AVENUE / (2 * CITY_W),
                                width=SEAM_AVENUE),
                 connection_id="connection:seam_market_west")
    city.connect(foundry_st.face("south"),
                 market_st.face("north", at=(SEAM_AVENUE + CITY_W) / (2 * CITY_W),
                                width=CITY_W - SEAM_AVENUE),
                 connection_id="connection:seam_market_east")

    # ---- the sewer: PARKED geometry, stack-linked entries -----------------
    #
    # Owner sewer directive: the network is separate geometry parked east of
    # the city (Blood's own water-volume pattern; also how DukCity fakes it),
    # connected through ROR stack links at each entry.  Every pair shares one
    # XY translation (the wormhole law -- conformance checks it), and mouths
    # are congruent at the link plane per stacks-v1.  This also dissolves the
    # geometry-audit blocker: parked geometry overlaps nothing.
    s = data["sewer"]
    park_dx, park_dy = SEWER_PARK_D
    sewer = city.assembly(
        "sewer", frame=Frame(int(park_dx), int(park_dy)),
        style=Style(**SEWER.style_kwargs(floor_shade=40, floor_z=SEWER_FLOOR,
                                         clear_height=SEWER_CLEAR)),
        note=s["park"]["note"],
    )

    # The trunk and its two chambers: the part of the network that predates
    # the ring, and the part the two street entries actually land in.
    trunk_part = sewer.assembly(
        "trunk", note="the original trunk, its risers and its two chambers")
    mouths_part = sewer.assembly(
        "mouths", note="the parked lower halves of the three stack links")

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
    landing.surfaces(floor_z=GRADE + UPPER_STEPS * 4096)
    cellar = stair.room(
        "cellar",
        [(0, 0), (3072, 0), (3072, 3072), (0, 3072)],
        role="gateway", faces=dict(COMPASS),
        frame=Frame(int(landing_x0 - 1024),
                    int(top_y0 - LOWER_STEPS * LOWER_TREAD - 3072)),
        region_kwargs=service.region_kwargs(),
        note="the works cellar; its pit is the solid stack into the sewer",
    )
    cellar.surfaces(floor_z=CELLAR_FLOOR)
    top_room.staircase("flight_upper", "west", total_rise=UPPER_STEPS * 4096,
                       tread=UPPER_TREAD, step_rise=4096,
                       arrive_at=landing.region_id,
                       connection={"role": "portal"})
    landing.staircase("flight_lower", "north", total_rise=LOWER_STEPS * 4096,
                      tread=LOWER_TREAD, step_rise=4096,
                      arrive_at=cellar.region_id,
                      connection={"role": "portal"})
    city.connect(top_room.face("east"), foundry_st.face("west"),
                 connection_id="connection:works_stair_mouth")

    # ---- the two stack links (hand-built per stacks-v1; grammar req #7) ---
    def mouth_pair(name, upper_parent, upper_frame_xy, upper_floor,
                   upper_style, landing_depth, see_through):
        """A congruent stack mouth pair: upper pit + parked lower tube.

        The lower tube's ceiling is the link plane (set at compile time by
        the link builder); its floor sits `landing_depth` below the plane --
        deep enough that a standing centre stays below the plane (no warp
        ping-pong), shallow enough to jump back out where intended."""
        ux, uy = upper_frame_xy
        # One room in the space it opens from.  Six of these used to be
        # singleton assemblies at the top of the city -- `yard_grate_mouth`
        # holding `yard_grate_upper`, and nothing else, ever.
        upper = (upper_parent or city).room(
            f"{name}_mouth", [(0, 0), (SHAFT, 0), (SHAFT, SHAFT), (0, SHAFT)],
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
            [(0, 0), (SHAFT, 0), (SHAFT, SHAFT), (0, SHAFT)],
            role="gateway", faces=dict(COMPASS),
            frame=Frame(int(ux + park_dx), int(uy + park_dy)),
            # All 6 paired links in E1M1/E3M1 have an XSector on both
            # halves; a behaviour entry is how ours gets one.
            region_kwargs={"sector_behavior": {"amplitude": -4,
                                               "shade_frequency": 4}},
            note=f"{name}: parked lower mouth, congruent at the plane",
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
    KERB, KERB_RISE = 2048, 1024
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
    kerb.surfaces(**MASONRY.style_kwargs(
        floor_picnum=INTERIORS["service"].floor, floor_shade=28,
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
        SEWER_FLOOR - GRADE, see_through=True)
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

    # ---- the network proper: the ring, its chambers and the necks --------
    # (the yard shaft's foot opens straight onto the ring's east leg)
    # Built after the mouths, because the ring hangs off the grate shaft.
    import l3_sewer
    sewer_net = l3_sewer.expand(city, sewer, {
        "junction": junction, "cistern": cistern,
        "main_duct": main_duct, "grate_lower": grate_lower,
    })
    city.connect(grate_lower.face("east"), sewer_net["e_leg"].face("west"),
                 connection_id="connection:grate_shaft_ring")
    # The towpath, from E3M3's own ledge family.  The two long legs are 24
    # plan units of bare tunnel each and the ring's most repetitive stretch.
    print("sewer towpaths:", l3_sewer.ledges(
        sewer, sewer_net, grade=SEWER_FLOOR, host_clear=SEWER_CLEAR))

    # Cellar pit: solid, the stair's last leg; jump-out depth.
    pit_xy = (int(landing_x0 - 1024 + 1024), int(top_y0 - LOWER_STEPS * LOWER_TREAD - 3072 + 1024))
    cellar.carve([(1024 + dx, 1024 + dy)
                  for dx, dy in ((0, 0), (SHAFT, 0), (SHAFT, SHAFT), (0, SHAFT))])
    pit_upper, pit_lower = mouth_pair(
        "cellar_pit", stair, pit_xy, CELLAR_FLOOR,
        Style(**INTERIORS["service"].style_kwargs(floor_shade=38,
                                                  clear_height=SEWER_CLEAR)),
        # See-through, not solid.  `rules_blood.stack-portal-wears-the-mirror-tile`
        # is an ERROR sourced from mirrors.cpp IsRorSector: without the mirror
        # tile the link still moves the player, who crosses it blind looking at
        # an ordinary floor.  The original "solid where transparency is not
        # wanted" fallback was a choice made before that rule was gradable.
        PIT_LANDING_DEPTH, see_through=True)
    for face in ("north", "east", "south", "west"):
        city.connect(pit_upper.face(face), cellar.face("north"),
                     connection_id=f"connection:cellar_pit_rim_{face}")
    # The pit's parked landing opens into the junction (it sits inside the
    # junction's footprint area -- adjacency via a carved island there).
    junction.carve([(pit_xy[0] - int(jx - jw / 2) + dx,
                     pit_xy[1] - int(jy - jd / 2) + dy)
                    for dx, dy in ((0, 0), (SHAFT, 0), (SHAFT, SHAFT), (0, SHAFT))])
    # All four rims, not just north and south: an edge that coincides and is
    # solid on both sides is a fault no campaign map contains (the
    # discriminator's coincident_solid_pairs is 0.000 across all 43), and it
    # is what the two leftover rims here were.
    for face in ("north", "east", "south", "west"):
        city.connect(pit_lower.face(face), junction.face("north"),
                     connection_id=f"connection:pit_landing_{face}")

    # ---- the pumping station: road-level stairs into the sewer ----------
    import l3_shed
    shed = l3_shed.build(district_of["foundry_ward"], foundry_st,
                         (int(DISTRICT_BOUNDS["foundry_ward"][0]),
                          int(DISTRICT_BOUNDS["foundry_ward"][1])))
    pit_x0, pit_y0, pit_x1, pit_y1 = l3_shed.PIT
    station_upper, station_lower = mouth_pair(
        "station_pit", shed["_assembly"], (pit_x0, pit_y0),
        l3_shed.CELLAR_FLOOR_Z,
        Style(**INTERIORS["service"].style_kwargs(
            floor_shade=38, clear_height=SEWER_CLEAR)),
        l3_shed.PIT_LANDING, see_through=True)
    for face in ("north", "east", "south", "west"):
        city.connect(station_upper.face(face), shed["cellar"].face("north"),
                     connection_id=f"connection:station_pit_rim_{face}")
    # Its parked twin opens off the silt trap, on the ring's north side.
    # The parked twin lands inside the foot chamber, carved from its middle
    # so the shaft is ringed by floor you can stand on and jump from.
    foot = sewer_net["station_foot"]
    ff = foot.world_frame()
    lx0, ly0 = pit_x0 + SEWER_PARK_D[0], pit_y0 + SEWER_PARK_D[1]
    foot.carve([(lx0 - ff.dx, ly0 - ff.dy),
                (lx0 - ff.dx + 1024, ly0 - ff.dy),
                (lx0 - ff.dx + 1024, ly0 - ff.dy + 1024),
                (lx0 - ff.dx, ly0 - ff.dy + 1024)])
    for face in ("north", "east", "south", "west"):
        city.connect(station_lower.face(face), foot.face("north"),
                     connection_id=f"connection:station_pit_sewer_{face}")

    stack_links = [
        {"stack_id": "stack:station_pit", "upper": station_upper.region_id,
         "lower": station_lower.region_id, "link_id": 3,
         "at_upper": ((pit_x0 + pit_x1) // 2, (pit_y0 + pit_y1) // 2),
         "see_through": True},
        {"stack_id": "stack:yard_grate", "upper": grate_upper.region_id,
         "lower": grate_lower.region_id, "link_id": 1,
         "at_upper": (gx, gy), "see_through": True},
        {"stack_id": "stack:cellar_pit", "upper": pit_upper.region_id,
         "lower": pit_lower.region_id, "link_id": 2,
         "at_upper": (pit_xy[0] + SHAFT_HALF, pit_xy[1] + SHAFT_HALF),
         "see_through": False},
    ]


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

    # ---- L3: St Gallow's, the mandatory landmark of Old Crossing --------
    import l3_church
    church_rooms = l3_church.build(district_of["old_crossing"], oldcross_st,
                                   grounds["cemetery"], gates)

    # ---- L3: the Gravesend Arcade (the shopping mall) -------------------
    import l3_mall
    mall_rooms = l3_mall.build(district_of["market_slip"], market_st)

    # ---- L3: Theatre Row's venues (the entertainment district) ----------
    import l3_theatre
    theatre_rooms, door_levers = l3_theatre.build(district_of['theatre_row'], theatre_st)

    # ---- L3: Market Slip's public space (the district the player starts
    # in), furnished from its own L1 `furnish` slots ------------------------
    import l3_market
    plaza = next(a for a in data["areas"] if a["id"] == "market_plaza")
    market_dressing = l3_market.dress(
        district_of["market_slip"], market_st, plaza["rect"],
        city_plan.Y_QUAY, city_plan.CITY_D)


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

    # ---- start: the first circuit leg, on the quay ------------------------
    start = data["circuit"][0]["at"]
    mb = DISTRICT_BOUNDS["market_slip"]
    city.set_start(market_st,
                   local=((start[0] * PU - mb[0]) / (mb[2] - mb[0]),
                          (start[1] * PU - mb[1]) / (mb[3] - mb[1])),
                   angle=1536)
    ctx["street_regions"] = {room.region_id: name
                             for name, room in streets.items()}
    ctx["light_pools"] = ctx_pools
    ctx["market_dressing"] = market_dressing
    ctx["market_street"] = market_st
    ctx["manifest"] = {
        "districts": len(DISTRICT_BOUNDS),
        "carved_areas": sum(1 for a in data["areas"] if a.get("carved")),
        "gates": sum(len(a.get("gates", [])) for a in data["areas"]),
        "stack_mouths_at_grade": 1,          # the yard grate (the pits are indoors)
        "grate_kerb": 1,                     # its raised stone ring
        "light_pools": len(ctx_pools),
        # Fountain, stalls and boards sit within one max step of the
        # street, so they join its walkable component (and cost no
        # walk-around loop -- the census is at its contract ceiling).
        "market_furniture": len(market_dressing["street_joined"]),
        "monument_tiers": len(market_dressing.get("monument_rooms", {})),
    }
    return city, stack_links, gates, ctx, dressing


def build_stack_link(layout, spec, park_d, *, see_through):
    """A displaced stack pair, hand-built per stacks-v1 (grammar req #7:
    room_over_room only places both markers at one point).  Congruent
    mouths, lower ceiling snapped to the upper floor plane, markers paired
    by data_1, translation = the shared park offset (the wormhole law)."""
    upper = layout.regions[spec["upper"]]
    lower = layout.regions[spec["lower"]]
    lower.ceiling_z = int(upper.floor_z)
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
         ax + park_d[0], ay + park_d[1], int(lower.ceiling_z),
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


def main() -> int:
    global LAST_BUILD
    program, stack_links, gates, ctx, dressing = build()
    layout = program.compile()
    for gate_id, region_a, region_b, a1, a2 in gates:
        layout.add_connection(gate_id, region_a, region_b, a1=a1, a2=a2,
                              min_width=1024)
    for spec in stack_links:
        build_stack_link(layout, spec, SEWER_PARK_D,
                         see_through=spec["see_through"])
    import l3_foundry
    l3_foundry.sprinkle(layout, ctx, dressing)
    # Declare the secret count.  A `secret=True` region emits the campaign's
    # per-sector wiring, but the *count* is a separate sprite transmitting
    # 64+n on channel 1 -- E3M1 carries one at command 73 (nine secrets).
    # Without it the player is never told a secret was found.
    layout.place_on_floor(
        "progression:secret_count", ctx["sewer_rooms"]["stash"],
        local=(0.5, 0.5), height_player_heights=0.5,
        type=0, picnum=0, cstat=129, status=0, x_repeat=64, y_repeat=64,
        behavior={"tx_id": 1, "command": 64 + 2})   # stash + flooded branch
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

    # A street lamp in every light pool.  506 is a wall bracket (92% of the
    # campaign's are within 512 units of a solid wall); a light pool is a
    # patch of brighter floor in the middle of a road, with no wall to
    # bracket to -- which is precisely where the owner saw torches flying.
    # Tile 640 is what DWE3M1 stands in its streets: a lamp fixture that
    # sits ON the ground, 593 instances campaign-wide at height +0.00.
    import lightpools
    for index, region_id in enumerate(ctx["light_pools"]):
        layout.place_on_floor(f"light:lamp_{index}", region_id,
                              local=(0.5, 0.5),
                              height_player_heights=props.height_of(props.STREET_LAMP),
                              light_intensity=lightpools.LAMP_INTENSITY,
                              light_height_player_heights=0.5,
                              emits_light=True,
                              **props.fields(props.STREET_LAMP))
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
    for placement_id, region_id, segment, channel in ctx["door_levers"]:
        doorswitch.place(layout, placement_id, region_id, segment, channel)
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
        if index % 2 == 0:
            amb.append((room.region_id, "sewer", (0.5, 0.5)))
    for index, (name, room) in enumerate(ctx["church_rooms"].items()):
        if name.endswith(("_door", "_porch")) or index % 2:
            continue
        amb.append((room.region_id, "church", (0.5, 0.5)))
    for index, (name, room) in enumerate(ctx["theatre_rooms"].items()):
        if (name.endswith(("_door", "_porch")) or name.startswith("furniture")
                or index % 2):
            continue
        amb.append((room.region_id, "interior", (0.5, 0.5)))
    for name, room in ctx["station_rooms"].items():
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
        if _key.endswith(("_door", "_porch", "_window", "_neck")):
            continue
        _fx.signature(layout, f"sig:mall_{_key}", _room.region_id)
        _sig += 1
    for _key, _room in list(ctx["sewer_rooms_new"].items())[:8]:
        _fx.signature(layout, f"sig:sewer_{_key}", _room.region_id)
        _sig += 1
    print(f"signature portholes: {_sig}")

    # The monument, before the generic signage pass: it owns its own face.
    import l3_market
    _mon_rooms = ctx["market_dressing"].get("monument_rooms")
    if _mon_rooms:
        print("monument:", l3_market.dress_monument(layout, _mon_rooms,
                                                 street=ctx["market_street"]))

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

    # Every moving door is a declared aperture, not a zero-height sector with a
    # door tile sprayed over whatever facade happens to face it.  The shared
    # compiler pass preserves each native type-600 sector and its behaviour,
    # adds the two reveal frames, and snaps its open height to whole door-art
    # repeats.  This is the reusable monastery correction, not a city-local
    # shading workaround.
    from bloodmap.aperture import frame_z_doors
    from bloodmap.rules import art_sizes
    door_frames = frame_z_doors(layout, art_sizes=art_sizes())
    ctx["manifest"]["door_frames"] = len(door_frames["doors"])
    print("door frames:", len(door_frames["doors"]))

    compiled = layout.compile()
    # Held for `citytree --cost`: later passes mutate this level in
    # place, so the reference stays current.
    LAST_BUILD = (program, compiled)
    ctx["manifest"]["lighting"] = dict(compiled.lighting_report)
    # Per-building facade variation (E3M1 runs 13 tiles over its street
    # network; one per district read as one repeated building).
    import facade_pass
    print("facades:", facade_pass.apply(compiled.level, compiled,
                                        ctx["street_regions"]))
    print("headers:", facade_pass.align_headers(compiled.level, compiled,
                                                ctx["street_regions"]))
    # Shop glass, after the facade pass so it survives what that painted.
    import glass, l3_theatre, l3_mall
    spans = [(w[3], w[4], w[5], w[6]) for w in l3_theatre.WINDOWS]
    for _unit, wx0, wx1, side, _plinth in l3_mall.WINDOWS:
        wy0, wy1 = (l3_mall.NORTH_BAND if side == "north"
                    else l3_mall.SOUTH_BAND)
        spans.append((wx0, wy0, wx1, wy1))
    print("shop glass:", glass.glaze(compiled.level, spans))

    # The landmark wears its own stone, inside and out, as E1M5's does.
    import l3_church
    print("church face:", facade_pass.face_landmark(
        compiled.level, l3_church.MASS, INTERIORS["church"].wall))

    # Texture alignment.  Blood advances a wall's horizontal texture
    # coordinate by x_repeat*8 along the wall, so a run only continues if
    # the next wall's panning picks up where the last left off.  Without
    # this every wall starts at panning zero and the pattern restarts at
    # every vertex -- including the vertices that are not corners at all,
    # the ones where a long facade was split to hang an entrance off it.
    # Runs first, then floor-anchoring for the walls that tile unevenly.
    # Must come after facade_pass, which decides the picnums.
    from bloodmap.texture_align import (
        align_wall_runs, align_wall_textures, wall_art_sizes)
    art_sizes = wall_art_sizes("reference/blood")
    print("align runs:", align_wall_runs(compiled.level, art_sizes))
    # Street facades override run-continuation with world phase, so the
    # bay grid is the same everywhere in a district (E3M1's own practice).
    print("facade phase:", facade_pass.world_align_facades(
        compiled.level, compiled, ctx["street_regions"]))
    print("align anchor:", align_wall_textures(compiled.level, art_sizes))

    # LightBomb now runs inside ``layout.compile`` from the sources declared by
    # each emitting placement.  Flicker remains a distinct runtime effect: it
    # animates a lamp's generated base shade but does not decide that base.
    from bloodmap.lighting import flicker_lit_sectors
    from l3_foundry import LAMP_TILE
    print("lighting flicker:", flicker_lit_sectors(
        compiled.level, tiles={LAMP_TILE, 506, 640, 1701}))
    print("lighting lightbomb:", compiled.lighting_report)

    # The sewer's mouths.  Tile 194 is E3M3's circular tunnel lining and it
    # uses it in exactly one place: the short opening where one channel
    # meets another, 29 walls of 1,128, with a band of wall above.
    import sewerkit
    _sewer_sectors = {
        int(alloc.sector_id) for region_id, alloc in compiled.allocations.items()
        if region_id.startswith("region:gravesend/sewer/")}
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

    disk = compiled.level.to_disk_map()
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
    # The corpus-graded rule registry, whose severities derive from measured
    # campaign violation rates rather than from anyone's opinion.  It was
    # sitting unused: `evaluate` returns nothing at all unless `rules_blood`
    # has been imported, because the registry is populated by that import's
    # side effect -- so "0 diagnostics" was silence, not a clean map.
    import bloodmap.rules_blood            # noqa: F401  (registers the rules)
    from bloodmap.rules import evaluate as _evaluate_rules
    _diags = _evaluate_rules(disk)
    _by_sev = collections.Counter(d.severity for d in _diags)
    _by_code = collections.Counter((d.severity, d.code) for d in _diags)
    print(f"rules: {len(_diags)} diagnostics {dict(_by_sev)}")
    for (_sev, _code), _n in _by_code.most_common():
        if _sev in ("error", "warning"):
            print(f"    {_sev:8s} {_code:38s} {_n}")
    ctx["manifest"]["rules"] = {
        "total": len(_diags),
        "by_severity": dict(_by_sev),
        "by_code": {f"{a}:{b}": c for (a, b), c in _by_code.items()},
    }
    _lines = ['# Rule registry, at build time', '', '`bloodmap.rules.evaluate`, severities derived from measured campaign', 'violation rates. Requires `bloodmap.rules_blood` to be imported: the', "registry is populated by that import's side effect, so a bare", '`evaluate` returns silence rather than a clean map.', '']
    _lines += [f"- **{d.severity}** `{d.code}` -- {d.message} ({d.location})"
               for d in sorted(_diags, key=lambda d: (d.severity, d.code))]
    (pathlib.Path(__file__).resolve().parents[1] / "reports" / "rules.md").write_text(
        chr(10).join(_lines), encoding="utf-8")
    out_dir = pathlib.Path(__file__).resolve().parent
    write_map(disk, out_dir / "city-skeleton.MAP")
    write_map(disk, out_dir / "blood-city-current.MAP")
    import json
    (out_dir.parents[0] / "reports" / "build-manifest.json").write_text(
        json.dumps(ctx["manifest"], indent=2), encoding="utf-8")
    print(f"sectors {len(disk.sectors)} walls {len(disk.walls)} "
          f"sprites {len(disk.sprites)}")
    print(f"wrote {out_dir / 'city-skeleton.MAP'} (+ blood-city-current.MAP)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
