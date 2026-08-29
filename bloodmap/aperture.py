"""A way through a wall, as a thing rather than an absence.

Why this type exists
--------------------

An opening used to be whatever was left over when two sectors of different
heights happened to touch. Nothing in the source said how tall a door was: the
leaf fell out of the two room heights, so a door into a tall hall became a door
as tall as the hall. Nothing owned the band of wall above the mouth either, so
whether it continued the room's masonry or jumped to some other tile depended on
which of five optional flags an author had remembered to set --
``door_face``, ``portal_wall_picnum``, ``PartitionSpec.opaque``,
``PlacementSpec.spans_opening`` and ``ConnectionSpec.face_*``. Each of those was
added after somebody looked at a render and saw something wrong, and each is a
shadow of the object that was missing.

So an aperture here has three parts, and all three are said in the source:

    leaf         the hole a body goes through
    mediation    what brings facade scale down to leaf scale
    reveal       the thickness the hole is cut in

What the engine actually does
-----------------------------

Build draws a two-sided wall in three bands. The **upper** section runs from the
lower of the two ceilings up to this sector's own; the **lower** section runs
from the higher of the two floors down to its own; the **leaf** is the gap left
between them, and it is the only part a body passes through::

    leaf   = min(floor_a, floor_b) - max(ceiling_a, ceiling_b)
    lintel = max(ceiling_a, ceiling_b) - ceiling_here
    step   = floor_here - min(floor_a, floor_b)

The band above the opening takes **this wall's own** ``picnum``, not the
neighbour's -- ``overpicnum`` is only consulted for masked one-way walls. That
one fact decides ownership: the lintel belongs to the facade it is *seen from*,
so it is the viewing room's material by construction and never the author's
problem. A door tile named on a region's ``wall_picnum`` lands on the inside of
the frame, where nobody stands; that is what ``door_face`` was invented to work
around, and it is folded into `Leaf.face` here.

What the campaign does
----------------------

``knowledge/blood/design/apertures-v1.json``, from all 43 campaign maps. Of
56,624 walkable two-sided walls, only 22,181 are apertures at all -- 45% are
*seams*, two sectors of one continuous space meeting, with no wall there to carry
anything. Among the apertures, in standing humans:

===================  ====  ======  ====  ====
measure                q1  median    q3   p95
===================  ====  ======  ====  ====
leaf height          1.57    1.93  3.32  5.80
leaf width (widths)  1.33    2.67  4.01  8.54
facade height        1.93    2.90  3.98  8.12
lintel (when there)  0.24    0.50  1.87  3.98
===================  ====  ======  ====  ====

47% of apertures carry a lintel, and **70% of those continue the facade's own
wall tile across it** -- the single measurement that makes lintel ownership a
compiled property rather than a suggestion.

Of the openings a region owns, 74% of campaign rooms with more than one wall
tile put a different tile on their two-sided walls than on their solid ones:
dressed jambs, undressed field. That is `Material.opening`, and `pierce` reaches
for it without being asked.

Naming the monumental ones
--------------------------

Full-height openings are real -- 40% of campaign apertures have no lintel and no
step, because a corridor mouth between two rooms of one height needs neither.
So height alone cannot be an error. What the grammar refuses is a *silent* one:
a leaf taller than `DOOR_MAX` must be given a word, and the word appears in the
source where a reader sees it. 28% of campaign apertures are over three humans
tall; they are cathedral portals and cargo doors and they are supposed to be.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping

from .player_space import PLAYER_PROFILES

#: One standing human and one body width, from the player profile.
PLAYER_HEIGHT = PLAYER_PROFILES["blood"].standing_height
PLAYER_WIDTH = PLAYER_PROFILES["blood"].body_width

#: The tallest leaf that needs no name. The campaign's apertures run a median of
#: 1.93 humans and a q3 of 3.32, so this sits just past the middle of the range:
#: an ordinary door passes unremarked, and anything monumental has to say so.
DOOR_MAX = 2.5

#: Each name and the band it may span, in standing humans. `full_height` has no
#: ceiling because it is defined by running the whole facade, not by a number.
LEAF_NAMES: dict[str, tuple[float, float]] = {
    "door": (0.0, DOOR_MAX),
    "arch": (DOOR_MAX, 4.0),
    "gate": (4.0, 6.5),
    "full_height": (0.0, math.inf),
}

#: A facade taller than the leaf by less than this is not worth mediating; it is
#: within the noise of a floor that steps. The campaign's lintels start at 0.24
#: humans at q1, so anything under that is not a lintel anybody built.
MEDIATION_SLACK = 0.25

#: What can bridge facade scale to leaf scale.
#:
#: ``lintel``     the facade simply continues above the opening. Cheapest, and
#:                what 47% of campaign apertures do. Needs no extra geometry:
#:                the viewing room keeps its own ceiling and the doorway's is
#:                lower, so Build draws the band and paints it from the room's
#:                own wall.
#: ``frame``      a dressed reveal -- the jamb wears the material's `opening`
#:                tile while the field around it keeps `wall`. What 74% of
#:                multi-tile campaign rooms do to their two-sided walls.
#: ``vestibule``  a recessed approach, an actual small room in front of the
#:                opening. `vocabulary.recess` builds the geometry.
MEDIATIONS = ("lintel", "frame", "vestibule")


class ApertureError(ValueError):
    """An aperture the grammar will not compile.

    Always names the fix, because the point of the type is to teach the rule at
    the moment it is broken rather than to be right in silence.
    """


@dataclass(frozen=True)
class Leaf:
    """The hole itself, in units of the body that goes through it.

    `height` and `width` are the *player's* units -- standing humans and body
    widths -- so the author never writes a z coordinate. A leaf shorter than one
    human is refused outright: Blood clips a body by its whole sprite extent
    (`blood_terrain.cpp` `clearanceFor` returns Standing only when
    ``freeHeight >= body.height``), so a passage under that is a wall with a
    decorative gap in it, not a way through.
    """

    width: float = 2.67
    height: float = 1.93
    name: str = "door"
    #: The tile the *rooms* see when they look at this opening -- the door leaf
    #: itself, if it has one. Goes on both sides of the portal wall, which is
    #: where Build reads it from. Was `RegionSpec.door_face`.
    face: int | None = None

    def __post_init__(self) -> None:
        if self.name not in LEAF_NAMES:
            raise ApertureError(
                "leaf name %r is not a word this grammar knows. Use one of: %s"
                % (self.name, ", ".join(sorted(LEAF_NAMES))))
        low, high = LEAF_NAMES[self.name]
        if self.height > high:
            fits = sorted(n for n, (a, b) in LEAF_NAMES.items()
                          if b >= self.height and n != "full_height")
            raise ApertureError(
                "a %s is at most %.2f humans tall and this one is %.2f, so it "
                "has to be named. %s Left unnamed a leaf takes whatever height "
                "the rooms happen to have, which is how a doorway becomes a "
                "door into the sky."
                % (self.name, high, self.height,
                   ("Call it a %r." % fits[0]) if fits else
                   "Nothing this tall is a door; if it really runs the whole "
                   "facade, call it 'full_height'."))
        if self.height < 1.0:
            raise ApertureError(
                "a leaf %.2f humans tall cannot be walked through -- Blood clips "
                "a body by its whole sprite extent, so a standing player needs a "
                "full 1.0. Lower it deliberately with a crouch passage, or raise "
                "it." % self.height)
        if self.width < 1.0:
            raise ApertureError(
                "a leaf %.2f body widths wide cannot be walked through; the "
                "player is %d units across." % (self.width, PLAYER_WIDTH))

    @property
    def height_z(self) -> int:
        return int(round(self.height * PLAYER_HEIGHT))

    @property
    def width_units(self) -> int:
        return int(round(self.width * PLAYER_WIDTH))


@dataclass(frozen=True)
class Aperture:
    """A leaf, what mediates it to the facade, and how thick the cut is.

    `mediation` is required whenever the facade stands more than
    `MEDIATION_SLACK` above the leaf. There is no default: the whole failure this
    type exists to prevent is a tall room quietly donating its height to a door,
    and a default would be that failure with better manners.
    """

    id: str
    leaf: Leaf = field(default_factory=Leaf)
    mediation: str | None = None
    #: How deep the opening is cut, in body widths. Only meaningful for `frame`
    #: and `vestibule`; a `lintel` is a plane.
    reveal: float = 0.0
    #: Set when the opening is a hole in a solid mass rather than a doorway
    #: between two finished rooms -- a breach, a collapse. Suppresses the
    #: dressed jamb, which would read as masonry somebody built.
    ragged: bool = False

    def __post_init__(self) -> None:
        if self.mediation is not None and self.mediation not in MEDIATIONS:
            raise ApertureError(
                "%s: %r is not a mediation. Use one of: %s"
                % (self.id, self.mediation, ", ".join(MEDIATIONS)))
        if self.mediation in ("frame", "vestibule") and self.reveal <= 0:
            raise ApertureError(
                "%s: a %s is a thickness, so it needs a reveal greater than 0 "
                "body widths. A reveal of 0 is a plane, which is a 'lintel'."
                % (self.id, self.mediation))

    def check_against(self, facade: float) -> None:
        """Refuse a facade this leaf cannot meet unaided.

        `facade` is the viewing room's own height in standing humans.
        """
        if facade <= self.leaf.height + MEDIATION_SLACK:
            return
        if self.mediation is None:
            raise ApertureError(
                "%s: the wall around this opening is %.2f humans tall and the "
                "leaf is %.2f, leaving %.2f of facade above the mouth with "
                "nothing to carry it.\n"
                "  Name what bridges them:\n"
                "    mediation='lintel'     the room's own wall continues above "
                "the opening (what 47%% of Blood's apertures do)\n"
                "    mediation='frame'      a dressed reveal in the material's "
                "opening tile; set reveal=0.5 or so\n"
                "    mediation='vestibule'  a recessed approach in front of it\n"
                "  Or, if the opening is genuinely meant to run the whole wall, "
                "say so: leaf=Leaf(height=%.2f, name='full_height')."
                % (self.id, facade, self.leaf.height,
                   facade - self.leaf.height, facade))


def facade_of(layout: Any, region_id: str) -> float:
    """A room's own height, in standing humans."""
    region = layout.regions[region_id]
    return abs(int(region.floor_z) - int(region.ceiling_z)) / float(PLAYER_HEIGHT)


def pierce(layout: Any, aperture: Aperture, region_a: str, region_b: str, *,
           a1: tuple[int, int], a2: tuple[int, int],
           through: str | None = None,
           material: Any = None) -> dict[str, Any]:
    """Open `aperture` between two regions, and own everything above and below it.

    `through` names a doorway region sitting between the two -- the sector the
    player passes *through* rather than stands in. When given, its ceiling is set
    from the leaf rather than inherited, which is the whole point: the leaf is
    the author's number and the rooms no longer decide it.

    Returns what was decided, so the audit can compare intent against the map.
    """
    for region_id in (region_a, region_b):
        if region_id not in layout.regions:
            raise ApertureError(f"{aperture.id}: unknown region {region_id!r}")

    # The facade on each side has to be able to meet this leaf.
    facades = {side: facade_of(layout, side) for side in (region_a, region_b)}
    for side, facade in facades.items():
        try:
            aperture.check_against(facade)
        except ApertureError as error:
            raise ApertureError("%s (seen from %s)" % (error, side)) from None

    decided: dict[str, Any] = {
        "aperture": aperture.id,
        "leaf": {"name": aperture.leaf.name,
                 "height_humans": aperture.leaf.height,
                 "width_widths": aperture.leaf.width,
                 "height_z": aperture.leaf.height_z},
        "mediation": aperture.mediation,
        "facades": {k: round(v, 2) for k, v in facades.items()},
        "regions": [region_a, region_b],
    }

    if through is not None:
        if through not in layout.regions:
            raise ApertureError(f"{aperture.id}: unknown doorway region {through!r}")
        doorway = layout.regions[through]
        # The leaf sets the doorway's ceiling. Before this type existed the
        # doorway inherited a neighbour's ceiling and the leaf was whatever that
        # left over -- which is how a doorway into a courtyard ended up open to
        # the sky.
        doorway.ceiling_z = int(doorway.floor_z) - aperture.leaf.height_z
        if int(doorway.__dict__.get("parallax_ceiling", 0) or 0):
            raise ApertureError(
                "%s: the doorway %s is open to the sky. A leaf is a built "
                "surface; a parallax ceiling inside an opening puts sky under a "
                "roof, which the engine draws as a hole in the world."
                % (aperture.id, through))
        decided["doorway"] = {
            "region": through,
            "ceiling_z": int(doorway.ceiling_z),
            "floor_z": int(doorway.floor_z),
        }
        # The jamb is this doorway's own solid wall, and it is dressed unless the
        # opening is meant to look torn.
        if material is not None and not aperture.ragged:
            opening_tile = getattr(material, "opening", None)
            if opening_tile:
                doorway.portal_wall_picnum = int(opening_tile)
                decided["jamb_picnum"] = int(opening_tile)

    if aperture.leaf.face is not None:
        # Both sides of every portal, which is where Build reads a door face
        # from. `door_face` on the doorway region does exactly this.
        target = through if through is not None else region_a
        layout.regions[target].door_face = int(aperture.leaf.face)
        decided["face_picnum"] = int(aperture.leaf.face)

    connection_id = "c:%s" % aperture.id.split(":", 1)[-1]
    if through is not None:
        layout.add_connection(connection_id + "_a", region_a, through,
                              a1=a1, a2=a2,
                              min_width=aperture.leaf.width_units,
                              min_opening=aperture.leaf.height_z)
        decided["connections"] = [connection_id + "_a"]
    else:
        layout.add_connection(connection_id, region_a, region_b,
                              a1=a1, a2=a2,
                              min_width=aperture.leaf.width_units,
                              min_opening=aperture.leaf.height_z)
        decided["connections"] = [connection_id]
    return decided


def audit(disk: Any, *, player_height: int | None = None) -> list[dict[str, Any]]:
    """Read a built map back and say what the grammar would have required.

    This is the acceptance test for the type: run it over a map authored before
    the grammar existed and every finding should be something a person can see
    in a frame. Findings are *interpreted* -- the grammar's opinion -- except
    `leaf_humans`, `facade_humans` and `lintel_continues_facade`, which are
    measured off the map.
    """
    from tools.mine_apertures import observe

    height = float(player_height or PLAYER_HEIGHT)
    findings = []
    for row in observe("candidate", disk):
        if not row["aperture"]:
            continue
        leaf = row["leaf_player_heights"] * (PLAYER_HEIGHT / height)
        facade = row["facade_player_heights"] * (PLAYER_HEIGHT / height)
        wants = []
        if leaf > DOOR_MAX:
            wants.append("name the leaf (%.2f humans): arch, gate or full_height"
                         % leaf)
        if facade > leaf + MEDIATION_SLACK and row["lintel_player_heights"] <= 0:
            wants.append("mediation: %.2f humans of facade above a %.2f leaf, "
                         "with no lintel" % (facade - leaf, leaf))
        if row["lintel_player_heights"] > 0 and not row["lintel_continues_facade"]:
            wants.append("the band above the mouth does not continue the "
                         "facade's tile (%d vs the room's %d)"
                         % (row["wall_picnum"], row["facade_picnum"]))
        if not wants:
            continue
        findings.append({
            "sector": row["sector"],
            "next_sector": row["next_sector"],
            "wall": row["wall"],
            "kind": row["kind"],
            "leaf_humans": round(leaf, 2),
            "facade_humans": round(facade, 2),
            "lintel_humans": round(row["lintel_player_heights"], 2),
            "lintel_continues_facade": row["lintel_continues_facade"],
            "grammar_requires": wants,
        })
    return findings


# ---------------------------------------------------------------------------
# Framed doors: a leaf that is a leaf, and a facade that stays facade
# ---------------------------------------------------------------------------

def tile_span_z(tile_height: int, y_repeat: int) -> int:
    """A wall tile's vertical extent in z: ``tilesizy * y_repeat * 8``."""
    return int(tile_height) * int(y_repeat) * 8


def snap_leaf(tile_height: int, y_repeat: int, target_z: int,
              *, at_least: int = 2) -> tuple[int, int]:
    """A leaf height that is a whole number of tile repeats.

    Returns ``(height_z, repeats)``.

    Two corrections live in this function, both of them against the obvious fix.

    The obvious fix for "the door tile draws five and a half times" is to
    stretch the tile until it draws once. **The campaign says no.** Of the ten
    commonest ``(x_repeat, y_repeat)`` pairings Blood uses for tile 22, nine pin
    ``y_repeat`` at 8 and vary only the horizontal; the tile is planking, and
    Blood tiles it a median of 3.0 times up a door. Forcing ``y_repeat`` to 44
    to make one giant leaf stretches a tile in a way the campaign never does.

    So the repeat stays at whatever the tile is used at, and the *opening* is
    sized to a whole number of them instead. The half-repeat is the real fault:
    5.50 spans means the top course of planks is sliced through the middle of
    its iron band.

    The arithmetic then lands somewhere worth noticing. Tile 22 at ``y_repeat``
    8 spans 8192 z, and four of those is 32768 -- which is 1.93 standing humans,
    *exactly* the campaign's median aperture leaf. The tile's own grid and the
    campaign's door height are the same number, which is not a coincidence: the
    height came from the art.
    """
    span = tile_span_z(tile_height, y_repeat)
    if span <= 0:
        raise ApertureError("a tile with no vertical span cannot size a leaf")
    repeats = max(int(at_least), int(round(abs(target_z) / float(span))))
    return repeats * span, repeats


def _match_edge(outline: list, edge: tuple) -> tuple[int, int]:
    """Which two outline vertices an edge names."""
    index = {tuple(point): position for position, point in enumerate(outline)}
    try:
        return index[tuple(edge[0])], index[tuple(edge[1])]
    except KeyError:
        raise ApertureError(
            "edge %r is not two corners of the outline %r" % (edge, outline))


def framed_door(layout: Any, door_region: str, *, near_edge: tuple,
                far_edge: tuple, leaf_height_z: int, face_picnum: int,
                face_tile_height: int, jamb_picnum: int,
                face_y_repeat: int = 8, reveal: float = 0.34) -> dict[str, Any]:
    """Split a door sector into frame / leaf / frame, and size the leaf's tile.

    Why this exists
    ---------------

    A Z-motion door shuts by bringing its ceiling down to its floor, so its
    sector has zero height when closed. The wall a room shows toward it is then
    one unbroken upper band running from the *room's* ceiling all the way down,
    and Build draws that band from the room's own wall picnum -- which
    `door_face` had set to the door tile. In a courtyard five standing humans
    tall that painted eleven stacked copies of a plank-and-iron door onto the
    facade. Measured on the monastery: all eight of its door faces did this, at
    2.00 to 11.00 repeats.

    The fix is the one an architect would give: the door does not open straight
    out of the field wall, it sits in a *frame*. Inserting a sector whose
    ceiling is at the leaf's head height changes who owns what --

        room  -> frame   the band above is the room's, so it stays facade
        frame -> leaf    the band above is the frame's, and it is one leaf tall

    -- and the door tile is then sized, by `leaf_repeat`, to draw exactly once
    over it.

    `near_edge` and `far_edge` are the two connection edges of the door's
    rectangle, each a pair of its corners. `reveal` is the share of the door's
    depth given to each frame; the middle keeps the moving sector.
    """
    if door_region not in layout.regions:
        raise ApertureError(f"unknown door region {door_region!r}")
    door = layout.regions[door_region]
    outline = [tuple(point) for point in door.outer]
    if len(outline) != 4:
        raise ApertureError(
            "%s has %d corners; a framed door splits a rectangle"
            % (door_region, len(outline)))
    if not 0.0 < reveal < 0.5:
        raise ApertureError("reveal must leave the leaf some depth")

    near = _match_edge(outline, near_edge)
    far = _match_edge(outline, far_edge)
    # Pair each near corner with the far corner it shares a side with.
    pairs = []
    for n in near:
        partner = min(far, key=lambda f: (outline[f][0] - outline[n][0]) ** 2
                      + (outline[f][1] - outline[n][1]) ** 2)
        pairs.append((n, partner))
    if len({p[1] for p in pairs}) != 2:
        raise ApertureError("%s: could not pair its two connection edges"
                            % door_region)

    def between(t: float) -> list:
        return [(int(round(outline[n][0] + (outline[f][0] - outline[n][0]) * t)),
                 int(round(outline[n][1] + (outline[f][1] - outline[n][1]) * t)))
                for n, f in pairs]

    at_near, at_far = between(reveal), between(1.0 - reveal)
    near_pts = [outline[pairs[0][0]], outline[pairs[1][0]]]
    far_pts = [outline[pairs[0][1]], outline[pairs[1][1]]]

    leaf_z, repeats = snap_leaf(face_tile_height, face_y_repeat, leaf_height_z)
    head_z = int(door.floor_z) - leaf_z

    from .planar_geom import area2

    want = area2(outline) > 0

    def wound(ring: list) -> list:
        """Slices cut off a rectangle can come out either way round; Build wants
        every outer loop the same way, so match the door we cut them from."""
        return ring if (area2(ring) > 0) == want else list(reversed(ring))

    # The leaf keeps the moving sector, the door tile and the behaviour.
    door.outer = tuple(wound([at_near[0], at_near[1], at_far[1], at_far[0]]))
    door.door_face = None                 # the frames show the leaf now
    door.wall_picnum = int(face_picnum)
    door.inherit_finish = None

    built = {}
    flats: dict[str, tuple[int, int]] = {}
    neighbours = {}
    for connection in layout.connections.values():
        if door_region not in (connection.region_a, connection.region_b):
            continue
        if not (connection.a1 and connection.a2):
            continue
        other = (connection.region_b if connection.region_a == door_region
                 else connection.region_a)
        first = tuple(connection.a1)
        side = ("near" if first in {tuple(near_pts[0]), tuple(near_pts[1])}
                else "far")
        neighbours[side] = other

    for tag, ring, edge in (("near", [near_pts[0], near_pts[1], at_near[1], at_near[0]],
                             near_pts),
                            ("far", [at_far[0], at_far[1], far_pts[1], far_pts[0]],
                             far_pts)):
        frame_id = "%s_frame_%s" % (door_region, tag)
        # A frame is lit like the wall it is cut into, not like a fresh
        # interior. The neighbour's own shade is usually unset -- the level
        # derives shades rather than writing them -- so derive the same answer
        # from the same description instead of copying an empty field.
        room = layout.regions.get(neighbours.get(tag, ""))
        shade = None
        if room is not None:
            if room.wall_shade is not None:
                shade = int(room.wall_shade)
            else:
                from .lighting import derived_shade
                xs = [point[0] for point in room.outer]
                ys = [point[1] for point in room.outer]
                area = (max(xs) - min(xs)) * (max(ys) - min(ys)) / (384.0 * 384.0)
                shade = derived_shade(outdoor=bool(room.parallax_ceiling),
                                      area_player_widths=area)["wall_shade"]
        # The flats come from the room, not from the leaf.
        #
        # A door sector's floor is walked on and its ceiling is the soffit you
        # pass under; neither is the door. The campaign agrees by a wide margin:
        # of its 1,284 Z-motion door sectors, **75.9% take their floor picnum
        # from a neighbour** and 74.4% do not use any of their own wall tiles on
        # it, with the ceiling at 74.1% and 70.8%. Inheriting the door face put
        # plank-and-iron on the floor of every reveal in this level.
        #
        # The ceiling is the exception to the exception: a room open to the sky
        # cannot lend its ceiling to a roofed frame without putting sky under a
        # roof, which `sky-is-never-below-a-roof` grades as an engine error at a
        # 0.30% campaign rate. Those take the jamb's masonry instead.
        floor_tile = int(room.floor_picnum) if room is not None else int(door.floor_picnum)
        if room is not None and not room.parallax_ceiling:
            ceiling_tile = int(room.ceiling_picnum)
        else:
            ceiling_tile = int(jamb_picnum)
        flats[tag] = (floor_tile, ceiling_tile)
        layout.add_region(
            frame_id, wound(ring), role="doorway",
            floor_z=int(door.floor_z), ceiling_z=head_z,
            wall_picnum=int(jamb_picnum),
            floor_picnum=floor_tile,
            ceiling_picnum=ceiling_tile,
            # The frame is what shows the leaf: its wall toward the moving
            # sector is the band the player reads as "a door".
            portal_wall_picnum=int(face_picnum),
            # A frame is a few hundred units of reveal in somebody else's wall,
            # so it is lit like that wall. Derived on its own it comes out a
            # roofed interior -- shade 32 against a courtyard's 5 -- and the
            # door reads as a black slot rather than a door in daylight.
            wall_shade=shade, floor_shade=shade, ceiling_shade=shade,
            intent={"purpose": "door frame; carries the leaf so the facade above "
                               "stays facade",
                    "classification": "MANDATORY"},
        )
        built[tag] = frame_id

    # The leaf walks on the same floor as the frames, for the same reason.
    if flats:
        near_flats = flats.get("near") or next(iter(flats.values()))
        door.floor_picnum, door.ceiling_picnum = near_flats

    # Rewire. The connections that used to run room <-> door now run
    # room <-> frame, and two new ones carry frame <-> leaf. Doing it here
    # rather than asking the author to is the point: the frame is an
    # implementation of "this is a door", not a thing to remember to wire.
    def side_of(edge: tuple) -> str:
        first = tuple(edge[0])
        return "near" if first in {tuple(near_pts[0]), tuple(near_pts[1])} else "far"

    for connection in list(layout.connections.values()):
        if door_region not in (connection.region_a, connection.region_b):
            continue
        if not (connection.a1 and connection.a2):
            continue
        tag = side_of((connection.a1, connection.a2))
        frame_id = built[tag]
        if connection.region_a == door_region:
            connection.region_a = frame_id
        else:
            connection.region_b = frame_id

    for tag, ring in (("near", at_near), ("far", at_far)):
        layout.add_connection(
            "connection:%s_leaf_%s" % (door_region.split(":", 1)[-1], tag),
            built[tag], door_region,
            a1=tuple(ring[0]), a2=tuple(ring[1]),
            min_width=1024,
            # The leaf keeps the repeat the campaign uses for this tile; it is
            # the *opening* that was resized, to a whole number of them.
            face_picnum=int(face_picnum), face_y_repeat=int(face_y_repeat))

    return {
        "door": door_region,
        "frames": built,
        "head_z": head_z,
        "leaf_height_z": leaf_z,
        "leaf_repeats": repeats,
        "face_y_repeat": int(face_y_repeat),
        "basis": ("all 8 of the monastery's door faces painted the room facade; "
                  "the campaign's own median leaf is 1.93 standing humans"),
    }


def frame_z_doors(layout: Any, *, art_sizes: Mapping[int, tuple[int, int]],
                  door_types: tuple[int, ...] = (600, 602),
                  face_y_repeat: int = 8, reveal: float = 0.34,
                  strict: bool = True) -> dict[str, Any]:
    """Apply :func:`framed_door` to every declared Z-door in a layout.

    This is the project-boundary adapter for a level whose room program has
    already declared type-600/602 door regions.  It keeps the native motion
    sector, but makes the visual aperture implementation a compiler decision:
    two named connections become frame -> leaf -> frame, the leaf is snapped
    to its art grid, and its open endpoint is updated to that same height.

    Authors still choose a deliberately unusual aperture by calling
    :func:`framed_door` themselves.  ``strict=True`` is the normal generated
    level setting: a door with an unknown face tile, a non-rectangular outline,
    or anything other than two named edges is a missing declaration, not a
    reason to silently fall back to the old broken style.
    """
    built: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for region_id, door in tuple(layout.regions.items()):
        if int(door.type) not in {int(value) for value in door_types}:
            continue
        edges = [
            (connection.a1, connection.a2)
            for connection in layout.connections.values()
            if region_id in (connection.region_a, connection.region_b)
            and connection.a1 is not None and connection.a2 is not None
        ]
        face = int(door.door_face or door.wall_picnum)
        tile = art_sizes.get(face)
        reason = None
        if len(edges) != 2:
            reason = "needs exactly two named connection edges"
        elif tile is None:
            reason = "has no known face-tile size"
        elif "on_ceiling_z" not in door.sector_behavior:
            reason = "has no Z-motion open endpoint"
        if reason is not None:
            message = f"{region_id}: {reason}"
            if strict:
                raise ApertureError(message)
            skipped.append({"door": region_id, "reason": reason})
            continue

        target = abs(int(door.floor_z) - int(door.sector_behavior["on_ceiling_z"]))
        if target <= 0:
            message = f"{region_id}: Z-motion open endpoint does not open a leaf"
            if strict:
                raise ApertureError(message)
            skipped.append({"door": region_id, "reason": message})
            continue
        item = framed_door(
            layout, region_id, near_edge=(tuple(edges[0][0]), tuple(edges[0][1])),
            far_edge=(tuple(edges[1][0]), tuple(edges[1][1])),
            leaf_height_z=target, face_picnum=face,
            face_tile_height=int(tile[1]), jamb_picnum=int(door.wall_picnum),
            face_y_repeat=face_y_repeat, reveal=reveal,
        )
        # Art-grid snapping is structural, not merely visual: motion must open
        # to the same head height the two frames expose.
        door.sector_behavior["on_ceiling_z"] = int(item["head_z"])
        built.append(item)
    return {"doors": built, "skipped": skipped}
