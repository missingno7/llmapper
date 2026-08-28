"""Iteration 7: the east wing, authored in frames, runs and one stamp.

This iteration adds geometry to the monastery without writing a single global
coordinate for it, which is the point. Everything new here is expressed as:

* **a run along one axis** (`bloodmap.layout`) -- the wing is a sequence of
  parts, one of them flexible, so inserting the oratory moved exactly one
  number and that number was the walk's;
* **a stamp** (`bloodmap.vocabulary.stamp`) -- the chapter house is turned 30
  degrees off the grid, composed in floating point and rounded once, before the
  planar overlay ever sees it;
* **derived geometry** -- the splay's diagonal edge is not written down at all.
  It *is* the chapter house's stamped west edge, read back out of the stamped
  outline, so the two sides of the shared boundary are the same two integers by
  construction rather than by the author matching them.

Why the level needed it
-----------------------

The candidate measured at the 0th percentile of the campaign for orientation
variety. Everything in it is axis-aligned; the arcs added in v5 curve but do not
*turn*, so every wall still meets every other at a right angle. A single
genuinely diagonal room changes the reading of the whole east side, because the
splay that gets you into it is the first place in the level where a wall runs at
an angle the player has to walk around.

Why 30 degrees
--------------

Not 45. A 45-degree room reads as a rotated square and its corners land back on
the grid, which is most of the reason a level made of 45s still looks like a
grid. 30 is unambiguously off-axis and its long walls are still long enough that
the stamp's half-unit rounding is nothing against them -- the shortest edge of
the chapter house is 1536 units, and `stamp` refuses anything under 32.

On the vertical scale
---------------------

The level's own height quantum is still the pre-correction one: `candidate_v6`
defines ``PH = 0x1600`` and every ceiling in the monastery is a multiple of it.
That number is `POSTURE.eyeAboveZ`, not a standing body, and the real body is
16960 -- but re-deriving every height in the level is a change to every room in
it, not something to slip into a wing. This wing therefore matches its
neighbours rather than being right on its own: it reuses v6's `tex()` so the
chapter house is the same height as the garden court it opens off. The rescale
is owed, and it is owed to the whole level at once.
"""

from __future__ import annotations

import importlib.util
import math
import pathlib
from typing import Any

from bloodmap.keys import sign_the_locks
from bloodmap.layout import Fixed, Flex, Wall, run
from bloodmap.planar_layout import PlanarLayout
from bloodmap.slope import SlopeSpec
from bloodmap.surfaces import material
from bloodmap.vocabulary import stamp, stamp_alignment, stamp_angle

_HERE = pathlib.Path(__file__).resolve().parent


def _v6() -> Any:
    spec = importlib.util.spec_from_file_location(
        "candidate_v6", _HERE / "candidate_v6.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V6 = _v6()
U = V6.U

#: The garden court's east wall, which is what the wing grows from. Read off the
#: region rather than written down: if the court moves or is resized, the wing
#: follows, which is the whole argument for references over coordinates.
COURT_REGION = "region:garden_court"

#: How far east the wing reaches. This is the one extent the wing is *given*;
#: everything inside it is divided by the run.
WING_SPAN = 24 * U

#: The chapter house before it is turned: written around its own origin, so it
#: is the same source whatever angle it ends up at.
HOUSE_LENGTH = 12 * U
HOUSE_WIDTH = 8 * U

#: How far off the grid. See the module docstring for why not 45.
HOUSE_DEGREES = 30.0

#: How high a wall sconce hangs. Not seated off the floor: see the note in
#: `_light_the_wing` about `seat="floor"` and sloped sectors.
SCONCE_HEIGHT = 4096

#: The splay's depth along the run. It has to be deep enough that the turn from
#: cardinal to 30 degrees happens over a wall the player can see, rather than at
#: a single corner.
SPLAY_DEPTH = 3 * U


def _oratory_room(layout: PlanarLayout, east: int, mid: int, placed: Any,
                  half: int, floor_z: int, ceiling_z: int) -> None:
    """The inserted part: a small oratory on the walk, with a sealed reliquary
    behind it.

    The reliquary is where a `Wall` earns its place. It is a chamber the player
    never enters -- seen through a grate in its west wall -- so the mass between
    it and the oratory is real, and thin on purpose. Naming the reason is what
    the grammar asks for instead of letting the number be whatever was left.
    """
    from bloodmap.layout import Fixed, Wall, run as cross_run

    layout.add_region(
        "region:east_oratory",
        [(east + placed.offset, mid - half), (east + placed.end, mid - half),
         (east + placed.end, mid + half), (east + placed.offset, mid + half)],
        role="gameplay", floor_z=floor_z, ceiling_z=ceiling_z,
        **material("cloister"),
        intent={"purpose": "oratory inserted into the east walk; the whole "
                           "insertion cost one number, the walk's",
                "classification": "OPTIONAL"},
    )

    # A cross run, north from the oratory's north wall: the mass, then the
    # sealed chamber. `Wall` refuses to be this thin without `thin_because`.
    depth = cross_run(
        "run:reliquary",
        Wall(name="grate", extent=64, thin_because="grate"),
        Fixed(name="reliquary", extent=2 * U),
        total=64 + 2 * U)
    slot = {p.name: p for p in depth.resolve()}
    north = mid - half
    back = north - slot["reliquary"].extent
    inset = 96
    layout.add_region(
        "region:east_reliquary",
        [(east + placed.offset + inset, back),
         (east + placed.end - inset, back),
         (east + placed.end - inset, north - slot["grate"].extent),
         (east + placed.offset + inset, north - slot["grate"].extent)],
        role="detail", floor_z=floor_z, ceiling_z=ceiling_z - 2048,
        **material("crypt"),
        # Sealed on purpose: the player sees it and never stands in it, which
        # the compiler would otherwise read as a room it forgot to connect.
        declared_zero_exit=True,
        intent={"purpose": "sealed reliquary behind a grate; never entered",
                "classification": "OPTIONAL"},
    )


def _house_local() -> list[tuple[int, int]]:
    """The chapter house in its own coordinates, west edge first.

    An octagon-ended hall: the cut corners are what make the rotation legible
    from inside, because a plain rectangle at 30 degrees reads as a rectangle
    until you find a corner.
    """
    half = HOUSE_WIDTH // 2
    chamfer = 2 * U
    return [
        (0, -half + chamfer),              # west edge, north end
        (chamfer, -half),
        (HOUSE_LENGTH - chamfer, -half),
        (HOUSE_LENGTH, -half + chamfer),
        (HOUSE_LENGTH, half - chamfer),
        (HOUSE_LENGTH - chamfer, half),
        (chamfer, half),
        (0, half - chamfer),               # west edge, south end
    ]


def east_wing(layout: PlanarLayout, *, oratory: int | None = 2 * U) -> dict[str, Any]:
    """Build the east wing onto whatever the garden court currently is.

    `oratory` is the insertion this iteration exists to demonstrate. Pass None
    for the wing without it and the only number that differs anywhere in the
    output is the walk's length -- see `insertion_note`.
    """
    court = layout.regions[COURT_REGION]
    east = max(point[0] for point in court.outer)
    ys = [point[1] for point in court.outer if point[0] == east]
    court_mid = (min(ys) + max(ys)) // 2
    floor_z = int(court.floor_z)
    ceiling_z = int(court.ceiling_z)

    # ---- the run -----------------------------------------------------------
    # One axis, east from the court wall. The walk is the flexible part because
    # a walk is the thing whose job is to be however long the rest leaves it;
    # the chapter house is fixed because a chapter house is a size.
    # Every part of this run is a room the player walks through, in order, so
    # there is no `Wall` in it -- a wall is the mass between parts that do *not*
    # connect, and none of these are. The reliquary is the exception and it gets
    # its own cross-axis run below.
    parts: list[Any] = [Flex(name="walk", low=4 * U)]
    if oratory is not None:
        parts += [Fixed(name="oratory", extent=int(oratory))]
    parts += [Fixed(name="splay", extent=SPLAY_DEPTH),
              Fixed(name="house", extent=HOUSE_LENGTH)]
    wing = run("run:east_wing", *parts, total=WING_SPAN)
    placed = {p.name: p for p in wing.resolve()}

    walk_half = 2 * U
    walk = placed["walk"]

    # ---- the chapter house, stamped once -----------------------------------
    # Turned about its own west edge midpoint so that the point the walk has to
    # meet is the point the rotation holds still.
    house_hinge = (0, 0)
    house = stamp(
        _house_local(), HOUSE_DEGREES,
        about=house_hinge,
        offset=(east + placed["house"].offset, court_mid),
    )
    if oratory is not None:
        _oratory_room(layout, east, court_mid, placed["oratory"], walk_half,
                      floor_z, ceiling_z)
    layout.add_region(
        "region:east_chapter", house, role="gameplay",
        floor_z=floor_z, ceiling_z=ceiling_z,
        **material("cloister"),
        # The floor is pitched, and a pitched floor is exactly the case the
        # campaign turns relative alignment on for -- 43.2% against an 11.0%
        # baseline for flat ones. The slope direction references the first wall
        # and so does the texture; leaving the texture world-aligned slides it
        # against its own gradient.
        floor_slope=SlopeSpec(hinge=(house[0], house[1]), rise_z=-2048),
        relative_alignment="floor",
        intent={"purpose": "chapter house, turned 30 degrees off the monastery grid",
                "classification": "OPTIONAL"},
    )

    # ---- the splay ---------------------------------------------------------
    # The transition from the cardinal walk to the diagonal house. Its diagonal
    # edge is *not written*: it is read back out of the stamped outline, so both
    # sides of the shared boundary are the same two integers.
    diagonal_a, diagonal_b = house[-1], house[0]
    splay_west = east + placed["splay"].offset
    splay = [
        (splay_west, court_mid - walk_half),
        diagonal_b,
        diagonal_a,
        (splay_west, court_mid + walk_half),
    ]
    layout.add_region(
        "region:east_splay", splay, role="gateway",
        floor_z=floor_z, ceiling_z=ceiling_z,
        **material("cloister"),
        intent={"purpose": "splay turning the walk onto the chapter house's angle",
                "classification": "MANDATORY"},
    )

    # ---- the walk ----------------------------------------------------------
    layout.add_region(
        "region:east_walk",
        [(east + walk.offset, court_mid - walk_half),
         (east + walk.end, court_mid - walk_half),
         (east + walk.end, court_mid + walk_half),
         (east + walk.offset, court_mid + walk_half)],
        role="gameplay", floor_z=floor_z, ceiling_z=ceiling_z,
        **material("cloister"),
        intent={"purpose": "east walk; the wing's flexible part",
                "classification": "MANDATORY"},
    )

    layout.add_connection(
        "connection:court_east_walk", COURT_REGION, "region:east_walk",
        a1=(east, court_mid - walk_half), a2=(east, court_mid + walk_half),
        min_width=1536)
    after_walk = "region:east_oratory" if oratory is not None else "region:east_splay"
    layout.add_connection(
        "connection:east_walk_next", "region:east_walk", after_walk,
        a1=(east + walk.end, court_mid - walk_half),
        a2=(east + walk.end, court_mid + walk_half),
        min_width=1536)
    if oratory is not None:
        layout.add_connection(
            "connection:east_oratory_splay", "region:east_oratory",
            "region:east_splay",
            a1=(east + placed["oratory"].end, court_mid - walk_half),
            a2=(east + placed["oratory"].end, court_mid + walk_half),
            min_width=1536)
    layout.add_connection(
        "connection:east_splay_chapter", "region:east_splay", "region:east_chapter",
        a1=diagonal_b, a2=diagonal_a, min_width=1536)

    _light_the_wing(layout, house, east, court_mid, walk, walk_half, floor_z)

    return {
        "run": {p.name: {"offset": p.offset, "extent": p.extent,
                         "flexible": p.flexible} for p in wing.resolve()},
        "house_outline": house,
        "degrees": HOUSE_DEGREES,
    }


def _light_the_wing(layout: PlanarLayout, house: list, east: int, mid: int,
                    walk: Any, half: int, floor_z: int) -> None:
    """Torches, placed off the geometry rather than at written coordinates.

    The chapter house's brackets sit on its own stamped corners and face inward,
    so their angles come from `stamp_angle` -- a sprite is the one thing a
    rotated outline does not carry with it, because its angle is absolute. A
    bracket that kept its unrotated angle would point at the wall the room used
    to have.
    """
    torch = V6.decor(506, 128, 1.5, shade=-128)
    inward = 96

    # One torch per *wall*, at its midpoint -- not one per vertex.
    #
    # Per vertex was the first version and the render showed it: the chamfered
    # corners put two vertices 1043 units apart against 2937 along the long
    # walls, so the torches came out in pairs with a gap between the pairs. A
    # corner is not a place, an edge is.
    cx = sum(p[0] for p in house) // len(house)
    cy = sum(p[1] for p in house) // len(house)
    midpoints = []
    for index in range(len(house)):
        ax, ay = house[index]
        bx, by = house[(index + 1) % len(house)]
        if math.hypot(bx - ax, by - ay) < 3 * U:
            continue                       # a chamfer is too short to light
        midpoints.append(((ax + bx) // 2, (ay + by) // 2))
    for index, (px, py) in enumerate(midpoints):
        towards = math.atan2(cy - py, cx - px)
        x = int(px + math.cos(towards) * inward)
        y = int(py + math.sin(towards) * inward)
        layout.add_sprite(
            "east_chapter_torch_%d" % index, "region:east_chapter",
            # Not `seat="floor"`: seating computes z from the sector's nominal
            # floor_z, which a sloped floor is no longer at. It put every one of
            # these outside the sector. A sconce is on the wall anyway, so it
            # takes an explicit height and the gap in seating is left recorded
            # rather than worked around silently.
            x=x, y=y, z=floor_z - SCONCE_HEIGHT,
            # Local angle 0 means "pointing along +x" in the unrotated room;
            # the stamp turns it with everything else.
            angle=stamp_angle(int(round(towards * 1024 / math.pi)) % 2048,
                              HOUSE_DEGREES),
            **torch)

    # The walk: a pair facing each other across it.
    for tag, offset in (("n", -half + inward), ("s", half - inward)):
        layout.add_sprite(
            "east_walk_torch_%s" % tag, "region:east_walk",
            x=east + walk.offset + walk.extent // 2, y=mid + offset,
            z=floor_z - SCONCE_HEIGHT, angle=512 if tag == "n" else 1536,
            **torch)


def insertion_note() -> dict[str, Any]:
    """The before/after this iteration is the acceptance test for.

    Resolves the wing's run with and without the oratory and reports what moved.
    The claim being checked is not that the walk shrank -- of course it did --
    but that *nothing else did*.
    """
    def resolve(oratory: int | None):
        parts: list[Any] = [Flex(name="walk", low=4 * U)]
        if oratory is not None:
            parts += [Fixed(name="oratory", extent=int(oratory))]
        parts += [Fixed(name="splay", extent=SPLAY_DEPTH),
                  Fixed(name="house", extent=HOUSE_LENGTH)]
        return {p.name: p.extent
                for p in run("run:east_wing", *parts, total=WING_SPAN).resolve()}

    before = resolve(None)
    after = resolve(2 * U)
    changed = {name: (before[name], after[name])
               for name in before if before.get(name) != after.get(name)}
    return {
        "before": before,
        "after": after,
        "changed": changed,
        "added": sorted(set(after) - set(before)),
    }


#: Every Z-motion door in the level, with the two edges it opens between.
#: Read off the layout at build time rather than written here -- the pairs come
#: from the connections that already name them.
def _frame_the_doors(layout: PlanarLayout) -> list[dict[str, Any]]:
    """Give every door a frame, and size its leaf tile to draw once.

    The fault, measured before the fix: all eight of the level's door faces
    painted the room facade rather than a leaf, at 2.00 to 11.00 vertical
    repeats of the tile. The chapel door showed eleven stacked plank-and-iron
    doors on a courtyard wall 5.31 standing humans tall, because a shut Z-door
    has zero height and the band above it therefore runs to the room's ceiling.

    See `bloodmap.aperture.framed_door` for who owns which band and why the
    frame fixes it.
    """
    from bloodmap.aperture import framed_door
    from bloodmap.rules import art_sizes

    sizes = art_sizes()
    built = []
    doors = [name for name, region in layout.regions.items()
             if int(region.type) in (600, 602)]
    for name in doors:
        region = layout.regions[name]
        edges = [(c.a1, c.a2) for c in layout.connections.values()
                 if name in (c.region_a, c.region_b) and c.a1 and c.a2]
        if len(edges) != 2:
            continue                       # not a straight-through door
        face = int(region.door_face or region.wall_picnum)
        tile = sizes.get(face)
        if not tile:
            continue
        # The leaf's head is where the door opens to, which the level already
        # decided when it wired the Z-motion endpoints.
        leaf = LEAF_HEIGHT_Z
        built.append(framed_door(
            layout, name, near_edge=edges[0], far_edge=edges[1],
            leaf_height_z=leaf, face_picnum=face, face_tile_height=tile[1],
            jamb_picnum=int(region.wall_picnum)))
    return built


#: How tall a leaf is aimed to be, before it is snapped to a whole number of
#: tile repeats. The campaign's median aperture leaf is 1.93 standing humans,
#: and tile 22 at the y_repeat the campaign pins it to spans 8192 z -- so four
#: repeats is 32768, which *is* 1.93 humans. The art's grid and the campaign's
#: door height are the same number.
LEAF_HEIGHT_Z = 32768


def _wall_is_spoken_for(layout: PlanarLayout, region_id: str,
                        a: tuple, b: tuple) -> bool:
    """Does this wall already carry something, or open through?

    Turning a wall into a parapet mouth turns it into a portal, and anything
    mounted on it is then hanging over a hole. The first wide pass put a walk
    across the sanctum lettering -- six letter sprites left floating in the
    opening -- and across a doorway the room already used.
    """
    from bloodmap.prefab import _along, _on_segment, _wall_mounted_points

    for point in _wall_mounted_points(layout, region_id):
        if _on_segment(a, b, point, tolerance=48):
            return True
    for connection in layout.connections.values():
        if region_id not in (connection.region_a, connection.region_b):
            continue
        if not (connection.a1 and connection.a2):
            continue
        if (_on_segment(a, b, tuple(connection.a1), tolerance=8)
                and _on_segment(a, b, tuple(connection.a2), tolerance=8)):
            return True
    return False


def _free_strip(layout: PlanarLayout, a: tuple, b: tuple, depth: int,
                skip: set[str]) -> bool:
    """Is the mass just outside this wall empty enough to build into?"""
    from bloodmap.planar_geom import point_in_loop

    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    if length <= 0:
        return False
    nx, ny = dy / length, -dx / length          # the Anchor's outward side
    for along in (0.15, 0.35, 0.5, 0.65, 0.85):
        for out in (0.25, 0.6, 1.0, 1.4):
            px = a[0] + dx * along + nx * depth * out
            py = a[1] + dy * along + ny * depth * out
            for name, region in layout.regions.items():
                if name in skip:
                    continue
                if point_in_loop((int(px), int(py)), list(region.outer)) > 0:
                    return False
    return True


#: Which spaces get looked down into. Naming three by hand produced three
#: overlooks against E6M6's 78, so the choice is made over every space big
#: enough to be composed -- the free-mass test then decides which of its walls
#: can actually carry a walk, and most cannot.
#:
#: The corpus does not parapet everything: 42% of E6M6's big spaces have one,
#: 26% of E1M1's. `PARAPET_TARGET` keeps this the same side of that.
PARAPET_TARGET = 0.40

#: Big enough to be worth looking down into, in square humans -- the same
#: threshold `tools.mine_patterns` counts with.
PARAPET_MIN_AREA = 5.0


def _region_area(region: Any) -> float:
    outline = list(region.outer)
    total = 0
    for index in range(len(outline)):
        a, b = outline[index], outline[(index + 1) % len(outline)]
        total += a[0] * b[1] - b[0] * a[1]
    human = 16960 / 16.0
    return abs(total) / 2.0 / (human * human)


def _reachable_neighbour(layout: PlanarLayout, walk, floor_z: int,
                         exclude: set) -> tuple[str, tuple, tuple] | None:
    """An existing region this walk could genuinely open into.

    This is the check that was missing, and its absence is the whole bug. The
    first version called `staircase` off the walk's flank, and counted "it did
    not raise" as "there is a way off". What it built was a flight of eight
    steps running out into solid rock, connected to the walk at one end and to
    nothing at the other -- nine of them, 72 sectors of stair to nowhere, in the
    starting area and underwater among other places.

    A way off is not a stair that exists. It is a boundary shared with somewhere
    the player can already be, at a height a body can cross.
    """
    from bloodmap.prefab import _on_segment

    edges = []
    outline = list(layout.regions[walk.regions[0]].outer)
    for index in range(len(outline)):
        edges.append((outline[index], outline[(index + 1) % len(outline)]))

    for name, region in layout.regions.items():
        if name in exclude or name in walk.regions:
            continue
        if abs(int(region.floor_z) - int(floor_z)) > 4096:   # one step
            continue
        theirs = list(region.outer)
        for index in range(len(theirs)):
            ta, tb = theirs[index], theirs[(index + 1) % len(theirs)]
            for ea, eb in edges:
                if (_on_segment(ta, tb, ea, tolerance=16)
                        and _on_segment(ta, tb, eb, tolerance=16)
                        and (ea != eb)):
                    return name, ea, eb
    return None


#: Hosts a parapet has no business being built on.
#:
#: `role="start"` because the player spawns there and a raised walk over the
#: spawn is not a composition, it is furniture in the doorway. The submerged
#: rooms because an overlook is something you look down from, and underwater
#: there is no down to look from -- the corpus's 309 overlooks include none.
PARAPET_FORBIDDEN_ROLES = {"start"}


def _add_parapets(layout: PlanarLayout) -> list[dict[str, Any]]:
    """Raised walks over the big spaces.

    The gap this closes, measured over the eight corpus maps closest to this
    level by palette: they carry 309 overlooks between them -- E6M6 alone has 78
    -- and the candidate had **one**. Its height differences were 23 kerbs under
    half a body and two whole storeys, with almost nothing in the 0.5-to-3.0
    band where you can see a man standing and he can see you.

    `bloodmap.prefab.parapet` carries the measured recipe. This chooses where,
    and refuses far more often than it builds: a walk goes in only where the
    wall is free, carries nothing already, is not the spawn or underwater, and
    -- the part the first version got wrong -- opens onto somewhere the player
    can already stand.
    """
    from bloodmap.prefab import PARAPET_DEPTH, PARAPET_RISE, parapet
    from bloodmap.vocabulary import Anchor, VocabularyError

    want = int(4.67 * U)
    built = []
    hosts = sorted(
        ((name, region) for name, region in layout.regions.items()
         if _region_area(region) >= PARAPET_MIN_AREA
         and not str(name).startswith("region:parapet")),
        key=lambda kv: -_region_area(kv[1]))
    budget = max(1, int(len(hosts) * PARAPET_TARGET))
    for host_id, host in hosts:
        if sum(1 for b in built if b.get("regions")) >= budget:
            break
        if getattr(host, "role", None) in PARAPET_FORBIDDEN_ROLES:
            built.append({"host": host_id, "skipped": "the player spawns here"})
            continue
        if getattr(host, "special", None) in ("water", "goo"):
            built.append({"host": host_id, "skipped": "submerged"})
            continue
        outline = list(host.outer)
        best = None
        for index in range(len(outline)):
            a, b = outline[index], outline[(index + 1) % len(outline)]
            run = math.hypot(b[0] - a[0], b[1] - a[1])
            if run < want:
                continue
            if not _free_strip(layout, a, b, PARAPET_DEPTH, {host_id}):
                continue
            if _wall_is_spoken_for(layout, host_id, a, b):
                continue
            if best is None or run > best[0]:
                best = (run, a, b)
        if best is None:
            built.append({"host": host_id, "skipped": "no free wall"})
            continue
        run, a, b = best
        # Centre the walk on the wall, on the wall's OWN integer lattice.
        #
        # Rounding each component of an interpolated point independently takes
        # it off the line unless the wall is axis-aligned. The courtyard's
        # chamfer lies on x + y = 6912; the first version of this put both
        # anchor points at 6911, one unit clear of the wall, and the parapet
        # compiled as a region touching nothing -- an unpaired portal with no
        # geometric explanation.
        #
        # Every integer point on the segment is a + k * (d / gcd), so step along
        # that instead of interpolating.
        dx, dy = b[0] - a[0], b[1] - a[1]
        step = math.gcd(abs(dx), abs(dy)) or 1
        ux, uy = dx // step, dy // step
        k0 = int(round(step * (run - want) / 2.0 / run))
        k1 = step - k0
        pa = (a[0] + ux * k0, a[1] + uy * k0)
        pb = (a[0] + ux * k1, a[1] + uy * k1)
        if pa == pb:
            continue
        # Match the host's sky. Roofing a walk over an open courtyard drops the
        # courtyard's own sky below a neighbouring roof, which grades as an
        # engine error at a 0.30% campaign rate -- and 38% of the corpus's
        # overlooks are open to the sky anyway.
        open_air = bool(host.parallax_ceiling)
        finish = dict(material("courtyard" if open_air else "cloister"))
        tag = host_id.split(":", 1)[-1]
        try:
            walk = parapet(layout, "parapet_%s" % tag,
                           anchor=Anchor(host_id, pa, pb),
                           head=None if open_air else PARAPET_HEAD_CLEAR,
                           **finish)
        except (VocabularyError, Exception) as error:
            built.append({"host": host_id, "skipped": str(error)})
            continue
        record = {"host": host_id, "regions": list(walk.regions),
                  "rise_z": PARAPET_RISE, "edge_units": want,
                  "another_way_off": False}
        landing = _reachable_neighbour(
            layout, walk, layout.regions[walk.regions[0]].floor_z, {host_id})
        if landing is None:
            _withdraw(layout, walk.regions)
            record["skipped"] = "nothing at its level to open onto"
            record["regions"] = []
        else:
            name, ea, eb = landing
            layout.add_connection("connection:parapet_%s_off" % tag,
                                  walk.regions[0], name, a1=ea, a2=eb,
                                  min_width=512)
            record["another_way_off"] = True
            record["opens_onto"] = name
        built.append(record)
    return built


def _withdraw(layout: PlanarLayout, regions) -> None:
    """Take back regions and every connection that referenced them."""
    doomed = set(regions)
    for name in doomed:
        layout.regions.pop(name, None)
    for cid in [c for c, spec in layout.connections.items()
                if spec.region_a in doomed or spec.region_b in doomed]:
        layout.connections.pop(cid, None)
    layout.placements[:] = [p for p in layout.placements
                            if p.region_id not in doomed]


#: Head clearance on a parapet stair. The corpus median head over an overlook is
#: 2.17 humans; a stair under it wants no less.
PARAPET_HEAD_CLEAR = 36864


def make_layout() -> PlanarLayout:
    layout = V6.make_layout()
    east_wing(layout)
    _frame_the_doors(layout)
    layout.parapets = _add_parapets(layout)

    # Say which key the locked door wants.
    #
    # v6 deleted all six emblem tiles because they had been hung as ordinary
    # wall furniture -- a key symbol on the chapter house, the reliquary and the
    # ossuary, signposting eight doors when the level holds one key. That
    # stopped the lying and left the one real lock unmarked, which is the other
    # half of the same fault: the campaign puts a placard on 80.4% of its keyed
    # things, and this level was at 0%.
    layout.keys_signed = sign_the_locks(layout)

    # Framing a door moves the wall the room faces, so three decorations that
    # were against masonry now sit over an opening. All three are the case the
    # flag exists for -- a grille set in a breach, a plank nailed across it, and
    # the crack the breach broke through -- so they are declared as spanning
    # rather than shuffled sideways onto whatever wall is still solid.
    spanning = {"crack_crypt", "dec_crypt_grille_west", "dec_aisle_s_plank"}
    marked = {p.placement_id for p in layout.placements
              if p.placement_id in spanning}
    if marked != spanning:
        raise ValueError("placements not found: %s" % sorted(spanning - marked))
    for placement in layout.placements:
        if placement.placement_id in spanning:
            placement.spans_opening = True
    return layout


if __name__ == "__main__":
    from bloodmap.format import encode_map

    note = insertion_note()
    print("inserting the oratory changed:", note["changed"])
    print("and added:", note["added"])
    built = make_layout().compile()
    out = _HERE / "candidate-v7.MAP"
    out.write_bytes(encode_map(built.level.to_disk_map()))
    print("wrote", out)
