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

    strips = []
    for name, lo, hi in x.spans:
        if name not in x.demanded:
            strips.append((lo, 0, hi, y.total))
    for name, lo, hi in y.spans:
        if name not in y.demanded:
            strips.append((0, lo, x.total, hi))

    lane_north = spans_y["lane_north"][1]
    #: END WALLS. Each stops its street just south of the perimeter lane, so
    #: the lane itself stays whole -- a ring lattice survives one blockage per
    #: leg, and the connectivity flood in `ground_plane_rings` still asks.
    ends = {}
    for name in TERMINATED:
        lo, hi = spans_x[name]
        ends[f"end_wall:{name}"] = (lo, lane_north,
                                    hi, lane_north + END_WALL_DEPTH)

    #: THE OPEN PLACES, each let into a street and each abutting the island it
    #: belongs to, so the shared edge is a pavement-only path.
    plaza_x0, plaza_x1 = spans_x["col_b"][0] + BAND, spans_x["col_b"][1] - BAND
    plaza_y0 = spans_y["market_street"][0]
    places = {
        "market_plaza": (plaza_x0, plaza_y0, plaza_x1, plaza_y0 + 3072),
        "cemetery": (spans_x["west_street"][0], spans_y["row_2"][0] + BAND,
                     spans_x["west_street"][0] + 3072,
                     spans_y["row_2"][1] - BAND),
    }

    #: THE QUAY WALK: the southernmost band of the quay street, taken out of
    #: the plane and stood 2048 up, so the shore has a pavement to step to.
    quay_lo, quay_hi = spans_y["quay"]
    quay_walk = (0, quay_hi - QUAY_WALK_DEPTH, x.total, quay_hi)

    holes = list(ends.values()) + list(places.values()) + [quay_walk]
    plane = ground_plane_rings(strips, holes=holes)

    #: THE ISLANDS. col_c/row_3 loses the works yard to a notch, so it is an
    #: L: the yard is its own pavement surface at the same z and the two are
    #: joined by a path, which is what a yard is.
    yard = None
    islands = {}
    masses = []
    for x_name, (x0, x1) in ((n, spans_x[n]) for n in x.demanded):
        for y_name, (y0, y1) in ((n, spans_y[n]) for n in y.demanded):
            key = f"{x_name}/{y_name}"
            if key == "col_c/row_3":
                notch_x1 = x0 + (x1 - x0) // 3
                notch_y1 = y0 + (y1 - y0) // 2
                yard = (x0, y0, notch_x1, notch_y1)
                islands[key] = [(notch_x1, y0), (x1, y0), (x1, y1), (x0, y1),
                                (x0, notch_y1), (notch_x1, notch_y1)]
            else:
                islands[key] = _rect(x0, y0, x1, y1)
            mx0, my0 = x0 + BAND, y0 + BAND
            mx1 = min(x1 - BAND, mx0 + x.demanded[x_name])
            my1 = min(y1 - BAND, my0 + y.demanded[y_name])
            if mx1 - mx0 >= 2048 and my1 - my0 >= 2048:
                masses.append(Mass(f"mass:{key}",
                                   tuple(_rect(mx0, my0, mx1, my1)),
                                   4 * STANDING))
    places["works_yard"] = yard

    water = {
        "shore": (0, quay_hi, x.total, quay_hi + SHORE_DEPTH),
        "sea": (0, quay_hi + SHORE_DEPTH, x.total,
                quay_hi + SHORE_DEPTH + SEA_DEPTH),
        "horizon": (0, quay_hi + SHORE_DEPTH + SEA_DEPTH, x.total,
                    quay_hi + SHORE_DEPTH + SEA_DEPTH + HORIZON_DEPTH),
    }
    return {"x": x, "y": y, "plane": plane, "islands": islands,
            "masses": masses, "ends": ends, "places": places,
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


def emission() -> Emission:
    """What this city is. No pass runs here."""
    g = geometry()
    surfaces = [SurfaceSpec(
        surface_id="plane", rings=tuple(g["plane"]), floor_z=ROAD_Z,
        ceiling_z=_sky(ROAD_Z), floor_tile=ROAD_TILE, ceiling_tile=SKY_TILE,
        wall_tile=ROAD_WALL_TILE, kind=joins.ROAD)]

    pavements = dict(g["islands"])
    pavements["quay_walk"] = _rect(*g["quay_walk"])
    for name, rect in g["places"].items():
        pavements[name] = _rect(*rect)
    for name, ring in sorted(pavements.items()):
        surfaces.append(SurfaceSpec(
            surface_id=name, rings=(ring,), floor_z=ISLAND_Z,
            ceiling_z=_sky(ISLAND_Z), floor_tile=PAVE_TILE,
            ceiling_tile=SKY_TILE, wall_tile=PAVE_WALL_TILE,
            kind=joins.PAVEMENT))

    #: THE END WALLS, in E3M1's dialect: floor 379, parallax sky above,
    #: blocking faces in the district's facade stone. Not lit, because a
    #: thing standing at the end of a street is not ground.
    for name, record in sorted(g["end_walls"].items()):
        surfaces.append(SurfaceSpec(
            surface_id=name, rings=(record["outline"],),
            floor_z=record["floor_z"], ceiling_z=record["ceiling_z"],
            floor_tile=record["floor_picnum"],
            ceiling_tile=record["ceiling_picnum"],
            wall_tile=FACADE_STONE, kind=joins.END_WALL, lit=False))

    #: THE WATERFRONT. The shore stands one walkable step (3072, inside
    #: Blood's 4096 autostep) below the quay walk, the sea meets it at equal
    #: z, and the horizon is a zero-height sector at the sea's own z wearing
    #: the sky tile on BOTH surfaces with the parallax bit on both.
    water = g["water"]
    shore_z = ISLAND_Z + SHORE_STEP
    surfaces.append(SurfaceSpec(
        surface_id="shore", rings=(_rect(*water["shore"]),), floor_z=shore_z,
        ceiling_z=_sky(shore_z), floor_tile=SHORE_TILE,
        ceiling_tile=SKY_TILE, wall_tile=joins.TILE_CLASSES["quay class"],
        kind=joins.SHORE))
    surfaces.append(SurfaceSpec(
        surface_id="sea", rings=(_rect(*water["sea"]),), floor_z=shore_z,
        ceiling_z=_sky(shore_z), floor_tile=SEA_TILE, ceiling_tile=SKY_TILE,
        wall_tile=joins.TILE_CLASSES["quay class"], kind=joins.SEA,
        finish={"floor_pal": joins.SEA_PALETTE},
        behavior={"pan_floor": 1, "pan_always": 1, "drag": 1,
                  "pan_velocity": joins.SEA_PAN_VELOCITY,
                  "pan_angle": joins.SEA_PAN_ANGLE}))
    surfaces.append(SurfaceSpec(
        surface_id="horizon", rings=(_rect(*water["horizon"]),),
        floor_z=shore_z, ceiling_z=shore_z, floor_tile=SKY_TILE,
        ceiling_tile=SKY_TILE, wall_tile=SKY_TILE,
        kind=joins.HORIZON, floor_stat=1, lit=False,
        declared_zero_exit=True))

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
        declarations=[],
        light=LightSpec(masses=tuple(g["masses"]), bearing_units=SUN_BEARING,
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
    wrong = []
    for row in report["lamps"]:
        want = BASE_SHADE + row["depth"] * STEP + row["delta"]
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
        chains = list(run_partition(disk, art_sizes=art, owners=owners))
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


if __name__ == "__main__":
    raise SystemExit(main())
