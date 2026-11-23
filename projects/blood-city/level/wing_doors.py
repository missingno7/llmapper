"""A pair of mirrored wooden doors that swing, alone in an open bay of the room they open into.

E2M5's doors (sectors 569 and 570): leaves 64 thick and 24,576 tall, the
owner's wooden door (30) edged with wood (20), knobs meeting in the middle.
Built first as the Aldermack's stage doors; the owner, 2026-11-23, of the
two sliding slabs on its front: "Shouldn't the front door be like mirror wings
to each other? ... they are slightly cropped, these previous two wing doors
you had were what I would expect".

The bay is a sector of its own at the room's floor and ceiling, big enough
for the whole sweep: "moving or rotating sector can never leave it's parent
sector". Nothing else is built in it.

Everything is laid out from the opening: `v` runs from the wall's face into
the bay, `u` along the wall from the opening's middle.
"""

from __future__ import annotations

from bloodmap import motion, wiring
from bloodmap.levelprog import RECT_FACES

LEAF_HEIGHT = 24576
THICKNESS = 64
OVERLAP = 32                 # a shut leaf laps its jamb; the two meet, as E2M5's do
SET_IN = 8                   # the leaves stand this far off the wall's face: at 32 daylight showed beside them
MARGIN = 96                  # clear of an open leaf, inside the bay
FACE, EDGE = 30, 20          # the owner's wooden door; wood
COMPASS = dict(zip(RECT_FACES, range(4)))
#: which way is into the bay, for a wall on that side of it
INWARD = {"east": (-1, 0), "west": (1, 0), "south": (0, -1), "north": (0, 1)}
#: the bay's other three sides, where the room goes on
OPEN_SIDES = {side: [s for s in RECT_FACES if s != side] for side in RECT_FACES}


class Pair:
    """Where everything stands: the wall's side of the bay, a point on its face, and half the opening."""

    def __init__(self, name, wall_side, middle, half, depth=None):
        self.name, self.side, self.middle, self.half = name, wall_side, middle, int(half)
        self.n = INWARD[wall_side]
        #: a quarter turn of `n`, so that every pair is a rotation of one drawing and no mirror image
        self.t = (self.n[1], -self.n[0])
        self.hinge = self.half + OVERLAP
        self.depth = depth or 896

    def at(self, u, v):
        return (self.middle[0] + u * self.t[0] + v * self.n[0],
                self.middle[1] + u * self.t[1] + v * self.n[1])

    def rect(self, u0, u1, v0, v1):
        (ax, ay), (bx, by) = self.at(u0, v0), self.at(u1, v1)
        return min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)

    def bay(self):
        reach = self.hinge + THICKNESS + MARGIN
        return self.rect(-reach, reach, 0, self.depth)

    def frame(self, thickness):
        return self.rect(-self.half, self.half, -thickness, 0)


def _ring(rect):
    x0, y0, x1, y1 = rect
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def build(venue, pair: Pair, *, room, room_faces: dict, outside, outside_face: str, wall: int,
          material, bay_style: dict, frame_style: dict, room_clear: int, grade: int) -> dict:
    """The bay, the frame through the wall and the two leaves in their open pose.

    `room_faces` names the room's own faces round the bay, by the bay's side:
    the room's outline already has the notch. `outside` is what the doors
    open from, across `wall` units of masonry.
    """
    import citytree

    name = pair.name
    # in world coordinates, as the leaves carved out of it are
    bay = venue.room(f"{name}_bay", _ring(pair.bay()), role="interior", faces=dict(COMPASS),
                     region_kwargs=material.region_kwargs(),
                     note="The doors' bay: the room's own space, holding both leaves' whole swing.")
    bay.surfaces(**bay_style)
    for side in OPEN_SIDES[pair.side]:
        citytree.join(bay, room, at_a=side, at_b=room_faces[side],
                      connection_id=f"connection:{name}_bay_{side}", min_opening=room_clear)
    frame = venue.room(f"{name}_frame", _ring(pair.frame(wall)), role="gateway", faces=dict(COMPASS),
                       region_kwargs=material.region_kwargs(),
                       note="The doors' frame, through the wall they close.")
    frame.surfaces(**frame_style)
    facing = {"east": "west", "west": "east", "north": "south", "south": "north"}
    citytree.join(frame, bay, at_a=facing[pair.side], at_b=pair.side,
                  connection_id=f"connection:{name}_in", min_opening=LEAF_HEIGHT)
    citytree.join(frame, outside, at_a=pair.side, at_b=outside_face,
                  connection_id=f"connection:{name}_out", min_opening=0)

    leaves = []
    for label, sense in (("a", 1), ("b", -1)):
        near, far = -sense * pair.hinge, -sense * (pair.hinge + THICKNESS)
        rect = pair.rect(near, far, SET_IN, SET_IN + pair.hinge)
        outline = _ring(rect)
        hole = len(bay.holes)
        bay.carve(outline)
        leaf = venue.room(
            f"{name}_leaf_{label}", outline, role="doorway", faces=dict(COMPASS),
            region_kwargs={"type": 617, "sector_behavior": {
                "busy_time_a": 15, "busy_time_b": 15, "interruptable": 1, "drag": 1}},
            note="Wooden hinged leaf, saved open and initialized shut.")
        # As E2M5's 50 and 51: the raised floor is the leaf's top, under the
        # room's own ceiling, with the XWALL on the surrounding loop.
        leaf.surfaces(**material.style_kwargs(
            floor_z=grade - LEAF_HEIGHT, clear_height=room_clear - LEAF_HEIGHT))
        for face in RECT_FACES:
            citytree.join(bay, leaf, at_a=bay.hole_face(hole, face), at_b=face,
                          connection_id=f"connection:{name}_leaf_{label}_{face}",
                          min_width=1, min_opening=0, gated=True)
        leaves.append((leaf, outline, pair.at(near, SET_IN), sense * 512))
    return {"pair": pair, "room": room, "bay": bay, "frame": frame, "leaves": leaves, "grade": grade}


def furnish(layout, built: dict, wire) -> dict:
    """Bind each leaf's axis, and put repeatable Push on every exposed face."""
    surround = built["bay"].region_id
    n = built["pair"].n
    for leaf, outline, (x, y), angle in built["leaves"]:
        region = leaf.region_id
        # DOOR-SWINGINGD axis sprites 206/213, including the signed quarter-turn.
        layout.add_sprite(
            f"placement:{leaf.node_id}:axis", region, x=x, y=y, z=built["grade"] - LEAF_HEIGHT,
            type=motion.MARKER_AXIS, picnum=motion.MARKER_PICNUM, status=motion.MARKER_STATNUM,
            cstat=motion.MARKER_CSTAT, x_repeat=64, y_repeat=64, angle=angle, marker_owner=region)
        wire.then(wiring.region(region))
        layout.declare_motion(region, [region, surround])
        for a, b in zip(outline, outline[1:] + outline[:1]):
            into = (b[0] - a[0]) * n[0] + (b[1] - a[1]) * n[1]
            broad = into != 0
            # E2M5 sector 569's repeats, its far face mirrored
            layout.paint_wall(surround, a, b, picnum=FACE if broad else EDGE,
                              x_repeat=8 if broad else 1, y_repeat=10 if broad else 8,
                              cstat=8 if into < 0 else 0, fixed_frame=True)
            wire.when(wiring.face(surround, a, b), "push", on=True, off=True)
    return {"threshold": surround, "leaves": [leaf.region_id for leaf, *_ in built["leaves"]],
            "wire": wire.name}
