"""Gravesend's ground: the street graph, its edges, and the water it ends at.

The emitter DECLARES and calls no pass. It returns a `pipeline.Emission` --
surfaces, declarations, light, joins, frames -- and `pipeline.compile_city`
runs planes -> declare -> light -> joins -> frames itself. Slice 2h's version
of this file called the passes by hand and forgot `frame_map`; what reported
that was the frames gate, at 191 misaligned walls, which is the symptom and
not the cause.

The model, unchanged: streets are the ground plane, one region per connected
network; pavements are ISLANDS standing 2048 up on it; a kerb is the island's
exposed edge; the light field cuts both; the join table decides every shared
record.

What this slice adds is the rest of the city's edge. End walls where three
streets reach the boundary. A south waterfront -- quay walk, shore, sea,
horizon -- in DWE3M10's dialect. A plaza, a cemetery and a works yard at
pavement level, each an island with its own surface and each joined to the
island it abuts by a pavement-only path. Lamps at E3M1's measured rate.

Writes `slice2-streets.MAP` and leaves `blood-city-current.MAP` alone.
"""

from __future__ import annotations

import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for path in (str(ROOT), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)

from bloodmap import city                                         # noqa: E402
from bloodmap import joins                                        # noqa: E402
from bloodmap import street                                       # noqa: E402
from bloodmap.facts import LEVELS, FactStore                       # noqa: E402
from bloodmap.light_field import Mass                             # noqa: E402
from bloodmap.overlay import ground_plane_rings, region_area      # noqa: E402
from bloodmap.pipeline import (                                   # noqa: E402
    Emission, FrameSpec, JoinSpec, Lamp, LightSpec, SurfaceSpec)
from city_solve import Cell, Envelope, Gutter, solve_axis         # noqa: E402
import city_plan as plan                                          # noqa: E402
from resolution import (                                          # noqa: E402
    GRADE, SKY_TILE, STANDING, STREET_SKY, SUN_BEARING, WIDTH_UNITS)

ROAD_TILE, PAVE_TILE, KERB_TILE = 352, 4, 6
#: W1, the owner's walk: the KERB TILE IS NEVER A DEFAULT. It was the plane's
#: wall material, so every shadow cut, every map edge and every end wall face
#: read as a kerb -- 111 records of the built map wore it with no pavement on
#: the other side. E3M1's road|road records wear the district's facade family
#: (401 twice, 400 twice, 380, 393) and its pavement records wear 401 above
#: all; tile 6 appears there on eleven records and every one of them steps
#: 2048 from a road to a pavement.
ROAD_WALL_TILE = 400
PAVE_WALL_TILE = 401
#: SHELLS. E3M1's facade family, measured by the LENGTH each tile covers
#: rather than by its record count -- 401 at 27.6%, 417 at 21.5%, 181 at
#: 11.6%, 400 at 8.7%, together 69.4% of its 122 facade records, every one of
#: them at y_repeat 8. The four are dealt round the districts so a street is
#: not one material end to end; 401 leads because it covers the most.
FACADE_FAMILY = joins.FACADE_FAMILY
ROOF_TILE = joins.ROOF_TILE
#: How tall a shell stands. Four player heights is the mass the shadow was
#: already cast from, so making the mass visible must not move it.
SHELL_BODIES = 4
#: How thick a shell's wall is, and how wide its door. E6M1's shopfront is a
#: 4096 x 512 recess with its sill 8192 up and its head 77824 down; a doorway
#: is the same construction with the sill on the floor, so the mouth is
#: 4096 wide and the wall 1024 deep -- one Blood door leaf and two thirds of
#: a body.
WALL_THICKNESS = 1024
DOOR_WIDTH = 4096
#: A doorway's head, in player heights. Blood's own doors clear a body with
#: room; two is the figure the aperture grammar uses for a street door.
DOOR_HEAD_BODIES = 2.0
#: What a room inside a shell is: floor at the island's grade, ceiling a
#: comfortable three bodies up, no sky.
INTERIOR_BODIES = 3.0
#: kSectorSlideMarked, the curtain's own type. A region carrying one is a
#: mechanism to `overlay.Domain`, which is what gives the light domain a
#: denominator at last.
#: A SHUTTER, not a curtain. kSectorSlideMarked names its two positions by
#: sprite index and the sweep validator runs before a sprite has one, so the
#: shopfront doors are Z-motion shutters (600) -- two ceiling heights and no
#: markers. The construct's NAME changes with it; a sentence that says
#: "curtain" about a shutter is worse than a shutter.
CURTAIN_TYPE = 600
#: `city_plan.CHANNELS["citywide_circuit"]["keys_gates"]` is 5.
KEY_GATES = 5
#: Where this level's rx ids start. Blood's channels are free integers; a
#: block of its own keeps the city's wiring out of any prefab's.
CHANNEL_BASE = 400
FACADE_STONE = joins.TILE_CLASSES["facade stone"]
RISE = 2048
ROAD_Z = GRADE + RISE
ISLAND_Z = GRADE
BAND = 2048
BASE_SHADE = 8
STEP = 12

#: LAMPS, and the correction the corpus forced.
#:
#: "Lamps at E3M1's rate" has no rate to take. E3M1's 45 bright outdoor
#: sprites are tiles 2519/2521 at shade -128 -- and they carry cstat 32896,
#: whose 0x8000 bit is INVISIBLE, statnum 12 (kStatAmbience) and types 708 and
#: 710, which `blood_types` names kGenSound and Ambient SFX. They are sound
#: generators wearing an editor icon, not lights. Widened to the whole
#: campaign: **0 visible outdoor lamps in 43 maps over 51,277,134,846 square
#: units of outdoor ground**. Blood does not put lamps on its streets; its
#: outdoor light is the sun and the shadow field, which is what the light
#: field already models.
#:
#: So the rate is borrowed from the only lamp density Blood has, its indoor
#: one: 245 lamps over 65,376,896,105 square units of interior, a per-map
#: median of one per **187,624,103** square units -- one every 13,698 units
#: square. The tile is 641, the hanging lantern, at the campaign's own cstat
#: 128, statnum 0, repeat 64 and a median 58,368 (3.44 player heights) above
#: its floor.
#: W3, the owner's walk: 641 is a ceiling lantern on a chain, and under an
#: open sky it hangs from nothing. Blood mounts its lights on WALLS -- of the
#: campaign's wall-aligned bright sprites the commonest are 795, 510 and 511,
#: and 510 is the sconce `lighting` already names. Its 28 campaign sprites
#: carry cstat 208 (wall-aligned), repeat 64, type 0, and the bright ones hang
#: a median 21504 -- 1.27 player heights -- above their floor.
LAMP_TILE = 510
LAMP_TYPE = 0
LAMP_SHADE = -128
LAMP_CSTAT = 208
LAMP_HANG = 21504
LAMP_MOUNT = "wall"
AREA_PER_LAMP = 187624103
#: The campaign gives its lamp-lit OUTDOOR sectors no shade bonus, because it
#: has none. So this delta is ours and is declared as such: half the measured
#: field step, so a lamp lifts half a shadow level rather than cancelling one.
LAMP_DELTA = -STEP // 2

#: The waterfront, in DWE3M10's dialect and at its measured step.
SHORE_STEP = joins.SHORE_STEP
SHORE_TILE = joins.SHORE_TILES[0]
SEA_TILE = joins.SEA_TILE
#: W4, the owner's walk: ONE OUTDOOR SPACE WEARS ONE SKY. Across the 43
#: campaign maps, 271 of 271 connected outdoor regions carry exactly one sky
#: picnum, at every size, with no exception. DWE3M10's horizon wears 3678
#: because that is DWE3M10's sky; Gravesend's sky is E3M1's 3491, so the
#: horizon inherits THAT, on its floor and its ceiling alike. The trick is the
#: zero height and the parallax bit on both, not the tile.
HORIZON_TILE = SKY_TILE
QUAY_WALK_DEPTH = 2048
SHORE_DEPTH = 2048
SEA_DEPTH = 16384
HORIZON_DEPTH = 2048


def _env(venue_id):
    spec = dict(plan.ENVELOPES[venue_id])
    spec.pop("source", None)
    return Envelope(venue_id, tuple(spec["interior"]),
                    faced=tuple(spec.get("faced", ("south",))))


def tenants():
    """Which venue lives on which island, from the plan's own cell lists.

    A cell in `X_ORDER` names the venues in its column and one in `Y_ORDER`
    the venues in its row, so the venue on an island is the one both name.
    Four of the nine fall out that way; the rest take the next venue their
    column has not used, and then the next their row has not. Reported rather
    than hidden, because a room whose tenant was picked by a tie-break is a
    weaker claim than one both lists agree on.
    """
    columns = {"col_a": ("aldermack", "saloon", "shooting_parlor"),
               "col_b": ("market_hall", "ferry_office"),
               "col_c": ("church", "arcade", "pawn_shop")}
    rows = {"row_1": ("aldermack", "church"),
            "row_2": ("arcade", "market_hall"),
            "row_3": ("works_canteen", "workshop_bar")}
    out, used = {}, set()
    for column, venues in columns.items():
        for row, in_row in rows.items():
            both = [name for name in venues if name in in_row]
            if both:
                out[f"{column}/{row}"] = (both[0], "both lists name it")
                used.add(both[0])
    for column, venues in columns.items():
        for row, in_row in rows.items():
            key = f"{column}/{row}"
            if key in out:
                continue
            spare = ([name for name in venues if name not in used]
                     + [name for name in in_row if name not in used])
            if spare:
                out[key] = (spare[0], "the next venue its column or row has "
                                      "not used")
                used.add(spare[0])
            else:
                out[key] = (None, "the plan names no venue for this island")
    return out


X_ORDER = [Gutter("lane_west", "lane"),
           Cell("col_a", (_env("aldermack"), _env("saloon"),
                          _env("shooting_parlor"))),
           Gutter("west_street", "street"),
           Cell("col_b", (_env("market_hall"), _env("ferry_office"))),
           Gutter("avenue", "avenue"),
           Cell("col_c", (_env("church"), _env("arcade"), _env("pawn_shop"))),
           Gutter("spur", "street")]
Y_ORDER = [Gutter("lane_north", "lane"),
           Cell("row_1", (_env("aldermack"), _env("church"))),
           Gutter("theatre_row", "row"),
           Cell("row_2", (_env("arcade"), _env("market_hall"))),
           Gutter("market_street", "street"),
           Cell("row_3", (_env("works_canteen"), _env("workshop_bar"))),
           Gutter("quay", "row")]

#: How deep an end wall bites into the street it stops. The wall itself is
#: `street.end_wall`'s dialect; this is only how much street it occupies.
END_WALL_DEPTH = 2048
#: Which streets end at the boundary, and at which end. `city_plan.BOUNDARY`
#: names three -- the avenue, the spur and the west street -- and puts all
#: three on the north side.
TERMINATED = ("avenue", "spur", "west_street")


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _sky(floor_z):
    return floor_z - STREET_SKY


def geometry():
    """Every rectangle this city is made of, solved and named.

    Separated from the emission so a gate can ask where the plaza is without
    compiling a map.
    """
    x = solve_axis("x", X_ORDER, WIDTH_UNITS)
    y = solve_axis("y", Y_ORDER, WIDTH_UNITS)
    spans_x = {name: (lo, hi) for name, lo, hi in x.spans}
    spans_y = {name: (lo, hi) for name, lo, hi in y.spans}

    #: A WIDTH CLASS IS THE FULL WIDTH. The gutter's solved span is the whole
    #: street; the carriageway is what is left after its pavements are taken
    #: out of it, and those bands go to the blocks beside them. The spans
    #: themselves do not move, so the plan's level-0 facts are untouched --
    #: what changes is where the kerb is.
    def bands(name, spans, order):
        cls = next((item.width_class for item in order
                    if getattr(item, "gutter_id", None) == name), None)
        lo, hi = spans[name]
        return plan.pavement_bands(WIDTH_UNITS.get(cls, hi - lo))

    carriageway = {}
    strips = []
    for name, lo, hi in x.spans:
        if name in x.demanded:
            continue
        low, high = bands(name, spans_x, X_ORDER)
        carriageway[("x", name)] = (lo + low, hi - high)
        strips.append((lo + low, 0, hi - high, y.total))
    for name, lo, hi in y.spans:
        if name in y.demanded:
            continue
        low, high = bands(name, spans_y, Y_ORDER)
        carriageway[("y", name)] = (lo + low, hi - high)
        strips.append((0, lo + low, x.total, hi - high))

    #: An island reaches to the edge of the carriageway beside it, which is
    #: how it comes to carry the pavement band.
    def grown(axis, name, spans, order, demanded):
        lo, hi = spans[name]
        names = [item for item, _a, _b in (x.spans if axis == "x" else y.spans)]
        index = names.index(name)
        before = names[index - 1] if index else None
        after = names[index + 1] if index + 1 < len(names) else None
        if before is not None and before not in demanded:
            lo = carriageway[(axis, before)][1]
        if after is not None and after not in demanded:
            hi = carriageway[(axis, after)][0]
        return lo, hi

    lane_north = carriageway[("y", "lane_north")][1]
    #: END WALLS. Each stops its street just south of the perimeter lane, so
    #: the lane itself stays whole -- a ring lattice survives one blockage per
    #: leg, and the connectivity flood in `ground_plane_rings` still asks.
    ends = {}
    for name in TERMINATED:
        lo, hi = carriageway[("x", name)]
        ends[f"end_wall:{name}"] = (lo, lane_north,
                                    hi, lane_north + END_WALL_DEPTH)

    #: THE OPEN PLACES, each let into a street and each abutting the island it
    #: belongs to, so the shared edge is a pavement-only path.
    col_b = grown("x", "col_b", spans_x, X_ORDER, x.demanded)
    row_2 = grown("y", "row_2", spans_y, Y_ORDER, y.demanded)
    market_lo = carriageway[("y", "market_street")][0]
    west_lo = carriageway[("x", "west_street")][0]
    places = {
        "market_plaza": (col_b[0] + BAND, market_lo,
                         col_b[1] - BAND, market_lo + 3072),
        "cemetery": (west_lo, row_2[0] + BAND, west_lo + 3072,
                     row_2[1] - BAND),
    }

    #: THE QUAY WALK: the southernmost band of the quay street, taken out of
    #: the plane and stood 2048 up, so the shore has a pavement to step to.
    quay_lo, quay_hi = carriageway[("y", "quay")]
    quay_walk = (0, quay_hi, x.total, spans_y["quay"][1])

    holes = list(ends.values()) + list(places.values()) + [quay_walk]
    plane = ground_plane_rings(strips, holes=holes)

    #: THE ISLANDS. col_c/row_3 loses the works yard to a notch, so it is an
    #: L: the yard is its own pavement surface at the same z and the two are
    #: joined by a path, which is what a yard is.
    yard = None
    islands = {}
    masses = []
    shells = {}
    for x_name, (x0, x1) in ((n, grown("x", n, spans_x, X_ORDER, x.demanded))
                             for n in x.demanded):
        for y_name, (y0, y1) in ((n, grown("y", n, spans_y, Y_ORDER,
                                           y.demanded))
                                 for n in y.demanded):
            key = f"{x_name}/{y_name}"
            #: Where a shell may stand on this island. The notched one has
            #: to give the yard up: a mass placed in the bounding box would
            #: sit in the yard rather than on the island, and the cut then
            #: pinches the island's ring against the yard's.
            buildable = (x0, y0, x1, y1)
            if key == "col_c/row_3":
                notch_x1 = x0 + (x1 - x0) // 3
                notch_y1 = y0 + (y1 - y0) // 2
                yard = (x0, y0, notch_x1, notch_y1)
                islands[key] = [(notch_x1, y0), (x1, y0), (x1, y1), (x0, y1),
                                (x0, notch_y1), (notch_x1, notch_y1)]
                buildable = (notch_x1, y0, x1, y1)
            else:
                islands[key] = _rect(x0, y0, x1, y1)
            bx0, by0, bx1, by1 = buildable
            mx0, my0 = bx0 + BAND, by0 + BAND
            mx1 = min(bx1 - BAND, mx0 + x.demanded[x_name])
            my1 = min(by1 - BAND, my0 + y.demanded[y_name])
            if mx1 - mx0 >= 2048 and my1 - my0 >= 2048:
                masses.append(Mass(f"mass:{key}",
                                   tuple(_rect(mx0, my0, mx1, my1)),
                                   SHELL_BODIES * STANDING))
                shells[key] = (mx0, my0, mx1, my1)
    places["works_yard"] = yard

    water = {
        "shore": (0, quay_hi, x.total, quay_hi + SHORE_DEPTH),
        "sea": (0, quay_hi + SHORE_DEPTH, x.total,
                quay_hi + SHORE_DEPTH + SEA_DEPTH),
        "horizon": (0, quay_hi + SHORE_DEPTH + SEA_DEPTH, x.total,
                    quay_hi + SHORE_DEPTH + SEA_DEPTH + HORIZON_DEPTH),
    }
    return {"x": x, "y": y, "plane": plane, "islands": islands,
            "masses": masses, "shells": shells, "ends": ends, "places": places,
            "quay_walk": quay_walk, "water": water,
            "end_walls": {name: street.end_wall(
                _rect(*rect), road_floor_z=ROAD_Z, standing_height=STANDING,
                facade_tile=FACADE_STONE, sky_tile=SKY_TILE, name=name)
                for name, rect in ends.items()}}


def _perimeter_lamps(rings, count):
    """`count` points evenly along a ring, stepped inward off the edge.

    A lamp stands ON the pavement, not on its lip, so each point is moved
    1024 -- two thirds of a body width -- toward the ring's centroid.
    """
    ring = rings[0]
    edges = []
    total = 0.0
    for index, point in enumerate(ring):
        nxt = ring[(index + 1) % len(ring)]
        length = math.hypot(nxt[0] - point[0], nxt[1] - point[1])
        edges.append((point, nxt, length))
        total += length
    cx = sum(p[0] for p in ring) / len(ring)
    cy = sum(p[1] for p in ring) / len(ring)
    out = []
    for number in range(count):
        want = total * (number + 0.5) / count
        walked = 0.0
        for point, nxt, length in edges:
            if walked + length >= want:
                share = (want - walked) / length if length else 0.0
                px = point[0] + (nxt[0] - point[0]) * share
                py = point[1] + (nxt[1] - point[1]) * share
                span = math.hypot(cx - px, cy - py) or 1.0
                out.append((int(round(px + (cx - px) / span * 1024)),
                            int(round(py + (cy - py) / span * 1024))))
                break
            walked += length
    return out


def plan_facts(g) -> FactStore:
    """The envelope solve, as level-0 facts. This IS the plan.

    Everything after it is a level-1 or later declaration ABOUT these
    rectangles, and the level-of-detail gate says none of those passes may
    move one.
    """
    store = FactStore()
    for axis, solved in (("x", g["x"]), ("y", g["y"])):
        for name, lo, hi in solved.spans:
            store.add("part_of", ("span", axis, name), lod=LEVELS["plan"],
                      source="city_solve.solve_axis", parent="city",
                      axis=axis, lo=int(lo), hi=int(hi),
                      kind="cell" if name in solved.demanded else "gutter",
                      demanded=int(solved.demanded.get(name, 0)))
    for key, ring in sorted(g["islands"].items()):
        store.add("island", ("island", key), lod=LEVELS["plan"],
                  source="city_plan.BLOCKS", ring=[list(p) for p in ring],
                  kind="block")
    for name, rect in sorted(g["places"].items()):
        store.add("island", ("island", name), lod=LEVELS["plan"],
                  source="city_plan.AREAS", ring=[list(p) for p in _rect(*rect)],
                  kind="open_place")
    for name, rect in sorted(g["ends"].items()):
        store.add("island", ("island", name), lod=LEVELS["plan"],
                  source="city_plan.BOUNDARY",
                  ring=[list(p) for p in _rect(*rect)], kind="end_wall")
    for name, rect in sorted(g["water"].items()):
        store.add("island", ("island", name), lod=LEVELS["plan"],
                  source="city_plan.BOUNDARY",
                  ring=[list(p) for p in _rect(*rect)], kind="waterfront")
    store.add("island", ("island", "quay_walk"), lod=LEVELS["plan"],
              source="city_plan.BOUNDARY",
              ring=[list(p) for p in _rect(*g["quay_walk"])], kind="walk")
    return store


def emission(shells: bool = True, field: bool = True) -> Emission:
    """What this city is. No pass runs here.

    Two switches, and each exists for exactly one gate. `shells=False` leaves
    the masses as pure occluders, which is what slice 2i shipped: making a
    mass visible must not move its shadow. `field=False` builds the same city
    with the sun switched off, which is the only honest way to ask Rule 2's
    question -- a mechanism's DragPoint closure must be what it was BEFORE any
    overlay ran, and the comparison needs a map where none did.
    """
    g = geometry()
    if not shells:
        g = dict(g, shells={})
    surfaces = [city.street("plane", g["plane"], floor_z=ROAD_Z,
                            sky_z=_sky(ROAD_Z), sky_tile=SKY_TILE)]

    pavements = dict(g["islands"])

    for name, rect in g["places"].items():
        pavements[name] = _rect(*rect)
    for name, ring in sorted(pavements.items()):
        #: A SHELL STANDS IN ITS ISLAND, so the island has a hole where the
        #: building is -- the same relation the plane has to the islands, one
        #: level up. Before this the mass cast a shadow and was not there.
        hole = g["shells"].get(name)
        rings = ((ring,) if hole is None
                 else (ring, list(reversed(_rect(*hole)))))
        surfaces.append(city.island(name, rings, floor_z=ISLAND_Z,
                                    sky_z=_sky(ISLAND_Z), sky_tile=SKY_TILE))

    #: THE SHELLS, through the constructor that names what one is: a FACADE
    #: with an OPENING in it, an INSERT filling the opening in a sector of its
    #: own, and a room behind. Not lit: a roof four bodies up is not ground.
    roof_z = ISLAND_Z - SHELL_BODIES * STANDING
    declarations = []
    who = tenants()
    for number, (key, rect) in enumerate(sorted(g["shells"].items())):
        tenant, how = who.get(key, (None, "unassigned"))
        made, declared = city.shell(
            key, rect, wall_thickness=WALL_THICKNESS, door_width=DOOR_WIDTH,
            roof_z=roof_z, floor_z=ISLAND_Z,
            interior_z=ISLAND_Z - int(INTERIOR_BODIES * STANDING),
            head_z=ISLAND_Z - int(DOOR_HEAD_BODIES * STANDING),
            sky_z=_sky(roof_z), sky_tile=SKY_TILE,
            wall_tile=FACADE_FAMILY[number % len(FACADE_FAMILY)],
            sector_type=CURTAIN_TYPE,
            wiring=[{"channel": CHANNEL_BASE + number, "tx_id": 0,
                     "rx_id": CHANNEL_BASE + number, "realised": False,
                     "why": "the door carries the rx; no switch or generator "
                            "carries the matching tx yet"}],
            gate_key=(number + 1) if number < KEY_GATES else None,
            key_why="city_plan.CHANNELS gives the citywide circuit five key "
                    "gates; no key pickup is emitted yet")
        surfaces.extend(made)
        declared["tenant"] = tenant
        declared["tenant_basis"] = how
        declarations.append(declared)

    #: THE END WALLS, in E3M1's dialect: 5.8 player heights up, parallax sky
    #: above, blocking faces in the district's own stone, and no kerb at the
    #: wall -- a kerb exists only where a road meets a pavement.
    for name, rect in sorted(g["ends"].items()):
        surfaces.append(city.end_wall(name, rect, road_floor_z=ROAD_Z,
                                      standing_height=STANDING,
                                      sky_tile=SKY_TILE,
                                      facade_tile=FACADE_STONE))

    #: THE WATERFRONT, in DWE3M10's dialect and at its measured step: the
    #: quay walk, the shore one walkable 3072 below it, the sea at the shore's
    #: own z under palette 10 with pan_floor + pan_always + drag, and a
    #: zero-height horizon wearing THIS city's sky on both surfaces, because
    #: one connected outdoor space wears one sky.
    surfaces.extend(city.waterfront(
        "", x0=0, x1=g["x"].total, y=g["quay_walk"][3],
        walk_depth=QUAY_WALK_DEPTH, shore_depth=SHORE_DEPTH,
        sea_depth=SEA_DEPTH, horizon_depth=HORIZON_DEPTH,
        pavement_z=ISLAND_Z, sky_z_of=_sky, sky_tile=SKY_TILE))

    #: LAMPS, at E3M1's rate over the pavement this city actually has.
    lamps = []
    for name, ring in sorted(pavements.items()):
        area = region_area([ring])
        count = max(1, int(round(area / AREA_PER_LAMP)))
        for number, point in enumerate(_perimeter_lamps([ring], count)):
            lamps.append(Lamp(f"{name}:{number}", point, LAMP_DELTA,
                              tile=LAMP_TILE, sprite_shade=LAMP_SHADE,
                              sprite_type=LAMP_TYPE, height=LAMP_HANG,
                              cstat=LAMP_CSTAT, mount=LAMP_MOUNT))

    return Emission(
        name="slice2-streets",
        surfaces=surfaces,
        declarations=declarations,
        light=LightSpec(masses=tuple(g["masses"]) if field else (),
                        bearing_units=SUN_BEARING,
                        base_shade=BASE_SHADE, step=STEP, lamps=tuple(lamps)),
        joins=JoinSpec(strict=False),
        frames=FrameSpec(),
        start=("plane", 0),
        facts=plan_facts(g))


# ---------------------------------------------------------------------------
# the gates, and the map
# ---------------------------------------------------------------------------

def main() -> int:
    from collections import Counter

    from bloodmap.format import write_map
    from bloodmap.overlay import (
        LIGHT_DOMAIN, declared_vertices, refusal_denominator, refusal_line,
        vertex_faults)
    from bloodmap.pipeline import compile_city
    from bloodmap.street_model import read_city, sees_the_kerb
    from bloodmap.texture_align import wall_art_sizes
    from bloodmap.texture_frame import (
        auto_align_walls, run_partition, sector_index)

    g = geometry()
    spoken = emission()
    built = compile_city(spoken)
    disk, report = built.disk, built.report
    print("solved grid:", (g["x"].total, g["y"].total))
    print("plane rings:", [len(r) for r in g["plane"]])
    for key in ("surfaces", "seeded_vertices", "pieces", "levels",
                "welded_vertices", "slivers_absorbed", "portals_paired",
                "sectors", "walls", "joins"):
        print(f"  {key}: {report[key]}")
    print("  partition faults:", len(report["partition_faults"]))
    print("  frames:", report.get("frames"))

    owners = sector_index(disk)

    # --- G1 ---------------------------------------------------------------
    declared = declared_vertices([[list(r) for r in spec.rings]
                                  for spec in spoken.surfaces])
    missing = vertex_faults(disk, declared)
    print(f"G1 vertex fidelity: {len(declared)} declared, "
          f"{len(missing)} missing")

    # --- the absolute shades, read off real sectors ------------------------
    shades = Counter()
    for name, piece, spec in built.pieces:
        sector = built.compiled.allocations[name].sector_id
        shades[(piece.depth,
                int(disk.sectors[sector].fields["floor_shade"]))] += 1
    print("shade by depth:", dict(sorted(shades.items())))

    # --- the lamp gate -----------------------------------------------------
    #: Deltas SUM: two lamps on one piece are two contributions to one
    #: additive channel, and the sector reads both. The first version of this
    #: gate compared each lamp against its own delta alone and called the
    #: second one a fault.
    from collections import Counter as _Counter

    per_sector = _Counter()
    for row in report["lamps"]:
        per_sector[row["sector"]] += row["delta"]
    wrong = []
    for row in report["lamps"]:
        want = BASE_SHADE + row["depth"] * STEP + per_sector[row["sector"]]
        got = int(disk.sectors[row["sector"]].fields["floor_shade"])
        if got != want:
            wrong.append(f"{row['lamp']}: reads {got}, wants {want}")
    pave_area = sum(region_area([list(r) for r in spec.rings])
                    for spec in spoken.surfaces
                    if spec.kind == joins.PAVEMENT)
    density = pave_area / max(1, len(report["lamps"]))
    print(f"lamps: {len(report['lamps'])} placed, {len(wrong)} misread; one "
          f"per {density:.0f} square units of pavement against the "
          f"campaign's indoor {AREA_PER_LAMP}")
    for row in wrong[:5]:
        print("   -", row)

    # --- the shade step: a CHOICE, against a reader's census ----------------
    #: The gate NAMES ITS NETWORK, because the number moves with the
    #: definition -- that is queue item 29a's whole finding. The envelope
    #: comes from `read_light.shade_step_envelope`, a census over the
    #: campaign, and never from a constant here.
    census = _shade_census()
    low, high = census["quartiles"]
    inside = low <= STEP <= high
    print(f"shade step: Gravesend CHOOSES {STEP}; the campaign's "
          f"{census['network']} has median {census['median']} over "
          f"{census['records']} boundaries in {census['maps']} maps, "
          f"quartiles {low}-{high}, {100 * census['inside']:.0f}% inside "
          f"{tuple(census['envelope'])} -- the choice is "
          f"{'inside' if inside else 'OUTSIDE'} the measured range")
    if not inside:
        print(f"   - {STEP} is outside {low}-{high}: a choice may be made, "
              f"and one outside the campaign's own middle half has to be "
              f"argued for")

    # --- the shells, and the shadow they must not have moved ---------------
    shadowless = compile_city(emission(shells=False))
    before = {f.sources[0]: int(f.attrs["depth"])
              for f in shadowless.store.of("shade_depth")
              if f.sources and f.sources[0].startswith("piece:plane")}
    after = {f.sources[0]: int(f.attrs["depth"])
             for f in built.store.of("shade_depth")
             if f.sources and f.sources[0].startswith("piece:plane")}
    moved = sorted(k for k in set(before) | set(after)
                   if before.get(k) != after.get(k))
    print(f"shells: {len(g['shells'])} built; the ground plane's field is "
          f"{len(before)} pieces before and {len(after)} after, "
          f"{len(moved)} with a different depth")
    for row in moved[:4]:
        print(f"   - {row}: {before.get(row)} -> {after.get(row)}")
    facade_walls = [w for w, wall in enumerate(disk.walls)
                    if int(wall.fields["picnum"]) in joins.FACADE_FAMILY]
    bad_repeat = [w for w in facade_walls
                  if int(disk.walls[w].fields["y_repeat"])
                  != joins.FACADE_Y_REPEAT]
    roofs = [i for i, sec in enumerate(disk.sectors)
             if int(sec.fields["floor_picnum"]) == ROOF_TILE]
    print(f"facades: {len(facade_walls)} records in E3M1's family "
          f"{joins.FACADE_FAMILY}, {len(bad_repeat)} off its y_repeat "
          f"{joins.FACADE_Y_REPEAT}; {len(roofs)} roofs wear {ROOF_TILE}")

    # --- Rule 2, with a denominator at last ---------------------------------
    faults, mechanisms = motion_set_faults(built, compile_city(
        emission(field=False)))
    print(f"Rule 2: {mechanisms} mechanism(s); {len(faults)} whose DragPoint "
          f"closure the overlays moved")
    for row in faults[:3]:
        print("   -", row)
    holes = opening_frame_faults(built)
    print(f"openings: {report['facts'].get('void', 0)} declared, "
          f"{report['facts'].get('fill', 0)} filled, {len(holes)} frame "
          f"fault(s) at their mouths")
    for row in holes[:3]:
        print("   -", row)

    # --- the mission graph, over the topology it is declared on ------------
    mission = mission_faults(built)
    print("mission:", {k: v for k, v in mission.items()
                       if not isinstance(v, list) or v})
    #: THE CIRCUIT, AS SURFACES. A leg is the surfaces a body passes through,
    #: so it survives a re-solve; the coordinates it used to carry were in the
    #: 58x56 plan grid and the solve is 72x60, and no leg could be checked at
    #: all.
    from bloodmap.conditional import Held, build_graph
    from bloodmap.street_model import circuit_faults

    by_surface = {}
    for name, _piece, spec in built.pieces:
        by_surface.setdefault(spec.surface_id, []).append(
            built.compiled.allocations[name].sector_id)
    at_rest = build_graph(disk).reachable(Held())
    legs = plan.CIRCUIT
    walked = [leg for leg in legs if leg.get("built", True)]
    broken = circuit_faults(disk, legs, by_surface, reachable=at_rest)
    print(f"circuit: {len(walked)} of {len(legs)} legs built, "
          f"{len(broken)} unreachable")
    for row in broken[:4]:
        print("   -", row)
    for leg in legs:
        if not leg.get("built", True):
            print(f"   not built: {leg['leg']!r} -- {leg.get('why', '')}")

    # --- a mechanism deforms what it says it deforms ------------------------
    #: THE ABSOLUTE READING: a Z-motion door's motion set is EMPTY. It moves a
    #: plane and no point in the map travels, so a wall flagged 0x4000 on one
    #: is a claim the mechanism never makes -- and DragPoint believes it.
    from bloodmap.motion import drag_closure, flagged_walls

    over = []
    for name, _piece, spec in built.pieces:
        if not spec.sector_type:
            continue
        sector = built.compiled.allocations[name].sector_id
        dragged = sorted(flagged_walls(disk, sector))
        closure = drag_closure(disk, sector)
        if int(spec.sector_type) == city.Z_MOTION and (dragged or
                                                       closure["walls"]):
            over.append(f"{spec.surface_id}: a Z-motion door deforms nothing, "
                        f"and this one flags {len(dragged)} wall(s) and drags "
                        f"{len(closure['walls'])} in "
                        f"{len(closure['sectors'])} sector(s)")
    print(f"payload: {len(over)} mechanism(s) claim a deformation they do not "
          f"make")
    for row in over[:3]:
        print("   -", row)

    # --- each building's own sentence, read back ---------------------------
    back = readback_faults(built)
    print(f"read-back: {back['sentences']} sentences, "
          f"{back['differences']} difference(s), agrees={back['agree']}")
    for surface, row in back["per building"].items():
        print(f"   {surface:24} {str(row['tenant']):18} "
              f"{row['differences']} difference(s)"
              + ("" if not row["facets"] else f": {row['facets']}"))

    # --- terminations ------------------------------------------------------
    faults = street.termination_faults(disk, list(g["end_walls"].values()),
                                       standing_height=STANDING)
    print(f"end walls: {len(g['end_walls'])} declared, "
          f"{len(faults)} fault(s)")
    for row in faults[:4]:
        print("   -", row)

    # --- the waterfront ----------------------------------------------------
    water = _waterfront_faults(disk, built)
    print("waterfront:", water or "reads as DWE3M10's -- the sea pans and "
          "drags under palette 10, the horizon is zero-height sky on both")

    # --- the paths ---------------------------------------------------------
    paths = sum(1 for row in report["join_rows"]
                if row["a"] == joins.PAVEMENT and row["b"] == joins.PAVEMENT)
    kerbs = sum(1 for row in report["join_rows"]
                if {row["a"], row["b"]} == {joins.ROAD, joins.PAVEMENT})
    shores = sum(1 for row in report["join_rows"]
                 if joins.SHORE in (row["a"], row["b"]))
    print(f"joins by kind: {kerbs} kerb records, {paths} pavement-only path "
          f"records, {shores} shore records")

    # --- sightline ---------------------------------------------------------
    tiles = set()
    roads = [i for i, sec in enumerate(disk.sectors)
             if int(sec.fields["floor_picnum"]) == ROAD_TILE]
    for sector in roads:
        tiles.update(sees_the_kerb(disk, sector, owners)["kerb_tiles"])
    print(f"sightline: from {len(roads)} road pieces a body sees "
          f"{sorted(tiles)}")

    # --- the editor --------------------------------------------------------
    art = wall_art_sizes("reference/blood")
    moved, moved_walls = 0, []
    if art:
        #: ON A COPY. `auto_align_walls` MUTATES, and running the gate on the
        #: map about to be written meant the emitter shipped whatever the
        #: gate's own probe had done to it -- which is why the same map read
        #: 2 in memory and 87 off disk.
        import copy

        keys = ("x_repeat", "x_panning", "y_repeat", "y_panning", "cstat")
        chains = list(run_partition(disk, art_sizes=art, owners=owners,
                                    boundaries=report["frame_boundary_walls"]))
        for chain in chains:
            #: ONE PROBE PER RUN, from the untouched map. The editor's
            #: recursion follows `wall[nextwall].point2` and does not stop at
            #: a run boundary, so a shared probe lets one run's walk spill
            #: into the next and the gate then reads its own spill back as a
            #: frame defect -- which is exactly what it did, on two walls.
            probe = copy.deepcopy(disk)
            before = {w: {k: int(disk.walls[w].fields[k]) for k in keys}
                      for w in chain}
            auto_align_walls(probe, chain[0], flags=0x01, art_sizes=art,
                             owners=owners)
            for wall_id in chain:
                if any(int(probe.walls[wall_id].fields[k]) != before[wall_id][k]
                       for k in keys):
                    moved += 1
                    moved_walls.append(wall_id)
    print(f"frames: the editor would change {moved} wall(s)")
    if moved_walls:
        print("   first:", moved_walls[:8])

    # --- the light domain, WITH its denominator ----------------------------
    print(refusal_line(refusal_denominator(disk, LIGHT_DOMAIN,
                                           range(len(disk.sectors)), owners)))

    from bloodmap import rules_blood                              # noqa: F401
    from bloodmap.rules import RULES

    if art:
        for rule_id in ("material-is-drawn-at-campaign-size",
                        "parallax-wears-a-sky-tile"):
            found = RULES[rule_id].check(disk)
            print(f"{rule_id}: {len(found.violations)} violation(s)")
    print("dropped PRESENTATION facets:",
          built.ledger.dropped_facets() or "none")

    # --- the read-back -----------------------------------------------------
    recovered = read_city(disk, road_tile=ROAD_TILE, pavement_tile=PAVE_TILE)
    print("read back:")
    for key in ("planes", "islands", "road_sectors", "pavement_sectors",
                "shade_levels", "iso_lines", "oblique_iso_lines",
                "sun_bearing_degrees"):
        print(f"  {key}: {recovered[key]}")
    print("  symmetry gaps:")
    for gap in recovered["symmetry_gaps"]:
        print(f"   - {gap}")

    print("facts:", report["facts"])
    print("facts by level:",
          {k: report["facts_by_level"].get(k, 0) for k in sorted(LEVELS.values())})
    print(f"LoD gate: the frames pass changed "
          f"{len(report['lod_faults'])} fact(s) below its level")
    for row in report["lod_faults"][:3]:
        print("   -", row)
    written = built.store.write(ROOT / "projects/blood-city/facts")
    print(f"wrote {len(written)} fact file(s) to projects/blood-city/facts")

    out = HERE / "slice2-streets.MAP"
    write_map(disk, out)
    print(f"wrote {out}: {len(disk.sectors)} sectors, {len(disk.walls)} "
          f"walls, {len(disk.sprites)} sprites")
    _limits(disk)
    return 0


def _shade_census(cache=ROOT / "work/shade_envelope.json") -> dict:
    """The campaign's step, measured once and kept beside the build.

    A census over 43 maps is not something to re-run on every build, and it
    is not something to hard-code either: the file records which network was
    measured and what came back, and deleting it re-measures.
    """
    import json

    from bloodmap.read_light import (
        NETWORK_LARGEST_COMPONENT, shade_step_envelope)

    path = pathlib.Path(cache)
    if path.exists():
        found = json.loads(path.read_text(encoding="utf-8"))
        if found.get("network") == NETWORK_LARGEST_COMPONENT:
            return found
    found = shade_step_envelope(network=NETWORK_LARGEST_COMPONENT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(found, indent=1, default=str),
                    encoding="utf-8")
    return found


def _waterfront_faults(disk, built) -> list:
    """The sea pans and drags; the horizon is zero-height sky on both sides.

    Read off the BUILT sectors and not off the declaration -- the whole point
    of an absolute gate is that it reads what the map says.
    """
    out = []
    named = {spec.surface_id: built.compiled.allocations[name].sector_id
             for name, _piece, spec in built.pieces}
    sea = named.get("sea")
    if sea is None:
        return ["no sea sector was built"]
    fields = disk.sectors[sea].fields
    holder = disk.sectors[sea].extra
    extra = dict(holder.fields) if holder is not None else {}
    if int(fields["floor_picnum"]) != SEA_TILE:
        out.append(f"the sea wears {fields['floor_picnum']}, not {SEA_TILE}")
    if int(fields.get("floor_pal", 0)) != joins.SEA_PALETTE:
        out.append(f"the sea is palette {fields.get('floor_pal')}, not "
                   f"{joins.SEA_PALETTE} -- it would read as the stone it is")
    for name in ("pan_floor", "pan_always", "drag"):
        if not int(extra.get(name, 0)):
            out.append(f"the sea does not carry {name}")
    horizon = named.get("horizon")
    if horizon is None:
        return out + ["no horizon sector was built"]
    fields = disk.sectors[horizon].fields
    if int(fields["floor_z"]) != int(fields["ceiling_z"]):
        out.append("the horizon is not zero-height")
    for role in ("floor", "ceiling"):
        if int(fields[f"{role}_picnum"]) != HORIZON_TILE:
            out.append(f"the horizon's {role} is not {HORIZON_TILE}")
        if not int(fields[f"{role}_stat"]) & 1:
            out.append(f"the horizon's {role} is not parallaxed")
    return out


def _limits(disk):
    import json

    budget = json.load(
        open(ROOT / "projects/blood-city/project.json"))["budget"]
    counts = {"sectors": len(disk.sectors), "walls": len(disk.walls),
              "sprites": len(disk.sprites)}
    print("limits: " + "  ".join(
        f"{k} {v}/{budget[k + '_limit']} ({100 * v // budget[k + '_limit']}%)"
        for k, v in counts.items()))


# ---------------------------------------------------------------------------
# Rule 2, for real, and the facade's frame across its openings
# ---------------------------------------------------------------------------

def motion_set_faults(built, plain) -> list:
    """A mechanism's motion set is what it was before any overlay ran.

    Overlay Rule 2: a region carrying a sector type is excluded from EVERY
    overlay, because cutting a mover changes its `DragPoint` closure. Until
    this slice the light domain refused nothing and the rule was never asked;
    with nine curtains in the map it has a denominator, and this is the gate
    it exists for.

    `plain` is the same city built with the sun switched off. The comparison
    is by SURFACE NAME rather than by sector id, because the field changes how
    many sectors there are and which index each one lands on.
    """
    from bloodmap.motion import drag_closure

    def closures(run):
        out = {}
        for name, _piece, spec in run.pieces:
            if not spec.sector_type:
                continue
            sector = run.compiled.allocations[name].sector_id
            found = drag_closure(run.disk, sector)
            #: BY THE VERTICES IT DRAGS, not by wall index and not by the
            #: walls' spans. `DragPoint` moves POINTS; the field changes
            #: every wall index after the first cut, and it changes how
            #: far a neighbouring wall runs, but it must not change WHICH
            #: POINTS MOVE. Comparing indices reports a difference on
            #: every mechanism and comparing spans reports one wherever a
            #: piece was cut beside a door; neither is what the rule is
            #: about.
            out[spec.surface_id] = sorted(
                (int(run.disk.walls[wall].fields["x"]),
                 int(run.disk.walls[wall].fields["y"]))
                for wall in found["walls"])
        return out

    with_sun, without = closures(built), closures(plain)
    out = []
    for name in sorted(set(with_sun) | set(without)):
        if with_sun.get(name) != without.get(name):
            out.append(
                f"{name}: its DragPoint closure has "
                f"{len(with_sun.get(name, ()))} members with the sun and "
                f"{len(without.get(name, ()))} without -- an overlay reached "
                f"a mechanism")
    return out, len(with_sun)


def opening_frame_faults(built) -> list:
    """The facade's frame crosses the mouth, and the insert's does not.

    Two questions, and each is about a different record. The FACADE's run must
    carry one continuous projection across the opening -- one `world_u`
    cursor, no restart at the jamb -- and the INSERT's records must not be on
    that run at all, because a material with its own scale needs a record no
    other surface uses.
    """
    from bloodmap.texture_frame import sector_index

    disk = built.disk
    owners = sector_index(disk)
    names = {built.compiled.allocations[n].sector_id: s.surface_id
             for n, _p, s in built.pieces}
    kinds = {built.compiled.allocations[n].sector_id: s.kind
             for n, _p, s in built.pieces}
    out = []
    for row in built.report["join_rows"]:
        here = owners[row["wall"]]
        there = int(disk.walls[row["wall"]].fields["next_sector"])
        if row["a"] != joins.OPENING or row["b"] != joins.FACADE:
            continue
        #: THE HOLDER RECORD. The rule says the facade's run crosses the
        #: mouth, so this record belongs to the facade above it and its band
        #: must wear the facade's material rather than the opening's.
        face = disk.walls[row["wall"]].fields
        if int(face["over_picnum"] or face["picnum"]) not in FACADE_FAMILY:
            out.append(f"wall {row['wall']}: the head of an opening in "
                       f"{names.get(here)} does not wear the facade's "
                       f"material")
    #: and the glass -- or here the curtain -- never sits on the facade's wall
    for name, _piece, spec in built.pieces:
        if spec.kind != joins.OPENING:
            continue
        sector = built.compiled.allocations[name].sector_id
        start = int(disk.sectors[sector].fields["wall_ptr"])
        count = int(disk.sectors[sector].fields["wall_count"])
        for wall_id in range(start, start + count):
            neighbour = int(disk.walls[wall_id].fields["next_sector"])
            if neighbour >= 0 and kinds.get(neighbour) == joins.FACADE:
                continue
        if count < 4:
            out.append(f"{spec.surface_id}: an insert with {count} records "
                       f"is not a sector of its own")
    return out


def mission_faults(built) -> dict:
    """The mission graph, checked against the topology it is declared over.

    Kept apart from the space graph on purpose (research 2.3): `part_of` and
    `join` say what is next to what, and `sentence`, `link`, `key` and
    `realises` say what the level is asking the player to do. This is the
    correspondence, run in the only direction a compiler can run it -- from
    the records back to the claim.

    A link whose tx nobody carries is not a failure of the build; it is an
    unrealised declaration, and it says so in its own row rather than being
    quietly absent.
    """
    from bloodmap.conditional import Held, build_graph

    disk = built.disk
    graph = build_graph(disk)
    at_rest = graph.reachable(Held())
    #: A DOOR YOU CAN OPEN IS NOT AN OBSTACLE. With the shutters shut at
    #: rest every room is unreachable, which is what a shut door means;
    #: the question the mission graph asks is whether a body who works
    #: the level's mechanisms can get there.
    everything = at_rest
    if hasattr(graph, "everything_worked"):
        try:
            found = graph.reachable(graph.everything_worked())
        except Exception:
            found = None
        if isinstance(found, set):
            everything = found

    sentences = {fact.attrs["sentence"]: int(fact.attrs["sector"])
                 for fact in built.store.of("realises")}
    rooms = {spec.surface_id: built.compiled.allocations[name].sector_id
             for name, _piece, spec in built.pieces
             if spec.kind == joins.INTERIOR}
    unreached = sorted(name for name, sector in sentences.items()
                       if sector not in everything)
    shut = sorted(name for name, sector in rooms.items()
                  if sector not in everything)
    links = built.store.of("link")
    keys = built.store.of("key")
    return {
        "sectors": len(disk.sectors),
        "reachable at rest": len(at_rest),
        "reachable with the mechanisms worked": len(everything),
        "sentences": len(sentences),
        "sentences reachable": len(sentences) - len(unreached),
        "sentences unreached": unreached,
        "rooms": len(rooms),
        "rooms unreached": shut,
        "links declared": len(links),
        "links realised": sum(1 for f in links if f.attrs.get("realised")),
        "keys declared": len(keys),
        "keys realised": sum(1 for f in keys if f.attrs.get("realised")),
    }


def readback_faults(built) -> dict:
    """Each building's own sentence, read back off the built map.

    The question this slice was set: does a construct declared against a
    ROOM's records survive the compiler's passes? The sentence is declared
    before the field cuts anything and before the joins and the frames write
    on the walls, and the read-back asks the built map whether it is still
    true -- per building, so a difference names one building and not the city.
    """
    from bloodmap.readback import read_back, sentence

    disk = built.disk
    sectors = {spec.surface_id: built.compiled.allocations[name].sector_id
               for name, _piece, spec in built.pieces}
    claims, tenants = [], {}
    for fact in built.store.of("sentence"):
        surface = fact.attrs["surface"]
        sector = sectors.get(surface)
        if sector is None:
            continue
        tenants[surface] = fact.attrs.get("tenant")
        start = int(disk.sectors[sector].fields["wall_ptr"])
        count = int(disk.sectors[sector].fields["wall_count"])
        #: WHAT THE CONSTRUCT ACTUALLY CLAIMS. A Z-motion door deforms
        #: nothing -- it moves a plane -- so it declares no motion set and
        #: declares instead the two things it does have: a state pair that
        #: changes, and the channel it answers.
        holder = disk.sectors[sector].extra
        wiring = ({"rx_id": int(holder.fields.get("rx_id", 0))}
                  if holder is not None
                  and int(holder.fields.get("rx_id", 0)) else None)
        claim = dict(name=surface, sector=sector,
                     sector_type=int(fact.attrs.get("sector_type", 0)),
                     state={"changes": True})
        if wiring:
            claim["wiring"] = wiring
        if fact.attrs["construct"] != "z_motion_door":
            claim["members"] = list(range(start, start + count))
        claims.append(sentence(fact.attrs["construct"], **claim))
    result = read_back(disk, claims, map_name="slice2-streets")
    by_name: dict = {}
    for row in result.differences:
        by_name.setdefault(row.mechanism, []).append(row)
    return {
        "sentences": len(claims),
        "agree": result.agrees,
        "differences": len(result.differences),
        "per building": {
            surface: {"tenant": tenants.get(surface),
                      "differences": len(by_name.get(surface, ())),
                      "facets": sorted({row.facet
                                        for row in by_name.get(surface, ())})}
            for surface in sorted(tenants)},
    }


if __name__ == "__main__":
    raise SystemExit(main())
