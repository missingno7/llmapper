"""A local frame for a bay, so a branch can run perpendicular to the hub.

The owner's layout note: branches must run **perpendicular** to the main
corridor, not alongside it, and the corridor must shrink to hub scale. v3 did
the opposite -- each section was a wide shallow slab hugging the spine for up
to forty thousand units, so the "corridor" was forty thousand units long and
every branch ran parallel to it.

Rotating the sections is easy; rotating the *builders* is not. Every exhibit
builder reasons in one frame -- x runs away from the room into its back box,
y runs across the bay -- and that frame is baked into a dozen helpers and
thirty builders. Rewriting them all to be axis-generic would be a large
change with nothing to show for it but a different set of arithmetic bugs.

So the builders keep their frame and the *layout* is rotated underneath them.
`Framed` is a proxy that wraps `PlanarLayout` and maps every point a builder
passes through one affine transform. A bay on the north wall of an
east-running branch hands its builder the same local rectangle it would have
had before; the walls come out ninety degrees around.

Only the methods a builder actually calls with coordinates are wrapped, and
anything else is forwarded untouched -- including the calls the mechanism
constructors make, since they receive this proxy as their `layout`.
"""

from __future__ import annotations

from math import atan2, cos, pi, sin
from typing import Any

#: Build's angle unit: 2048 to the turn.
BUILD_TURN = 2048


class Framed:
    """`PlanarLayout` seen through one rotation, for one bay.

    `origin` is where the bay's local (0, 0) sits in the world, `forward` is
    the world direction local +x points in, and `across` the direction local
    +y points in. Both are unit vectors on an axis, so the transform stays
    exact in integers -- Build has no floating point and a rotated wall that
    lands half a unit off is a hole in the map.
    """

    def __init__(self, layout: Any, origin: tuple[int, int],
                 forward: tuple[int, int], across: tuple[int, int]) -> None:
        self._layout = layout
        self._origin = (int(origin[0]), int(origin[1]))
        self._forward = (int(forward[0]), int(forward[1]))
        self._across = (int(across[0]), int(across[1]))
        #: Half of the four frames are reflections, not rotations: their
        #: determinant is -1, and a reflection reverses a loop's winding.
        #: Build requires an outer loop to be clockwise in screen space, so a
        #: reflected frame hands back the outline reversed.
        self._flip = (self._forward[0] * self._across[1]
                      - self._forward[1] * self._across[0]) < 0

    # -- the transform ----------------------------------------------------
    def point(self, p) -> tuple[int, int]:
        x, y = int(p[0]), int(p[1])
        return (self._origin[0] + self._forward[0] * x + self._across[0] * y,
                self._origin[1] + self._forward[1] * x + self._across[1] * y)

    def points(self, seq):
        return [self.point(p) for p in seq]

    def angle(self, value: int) -> int:
        """A Build angle, turned the way this frame turns.

        A frame that moves a sprite's POSITION and leaves its ANGLE alone
        breaks every construct whose meaning is the relation between the two.
        The turnstile is the worked example: its four blades are two vanes,
        each extending PERPENDICULAR to its own face normal, and rotating
        only the positions turned the cross into a square. Nothing else
        noticed -- not validation, not the usage laws, not the self-reading
        gate, not thirty-one renders -- and the owner saw it immediately.
        """
        radians = int(value) % BUILD_TURN * 2.0 * pi / BUILD_TURN
        dx, dy = cos(radians), sin(radians)
        wx = self._forward[0] * dx + self._across[0] * dy
        wy = self._forward[1] * dx + self._across[1] * dy
        turned = atan2(wy, wx) * BUILD_TURN / (2.0 * pi)
        return int(round(turned)) % BUILD_TURN

    def box(self, b) -> tuple[int, int, int, int]:
        """A local rectangle, as a world rectangle in min/max order."""
        corners = self.points(((b[0], b[1]), (b[2], b[1]),
                               (b[2], b[3]), (b[0], b[3])))
        xs = [p[0] for p in corners]
        ys = [p[1] for p in corners]
        return (min(xs), min(ys), max(xs), max(ys))

    # -- the wrapped calls ------------------------------------------------
    def add_region(self, region_id, outline, **kwargs):
        points = self.points(outline)
        if self._flip:
            points.reverse()
        return self._layout.add_region(region_id, points, **kwargs)

    def add_connection(self, connection_id, a, b, *, a1=None, a2=None,
                       **kwargs):
        return self._layout.add_connection(
            connection_id, a, b,
            a1=self.point(a1) if a1 is not None else None,
            a2=self.point(a2) if a2 is not None else None, **kwargs)

    def add_partition(self, partition_id, a, b=None, *, a1=None, a2=None,
                      **kwargs):
        return self._layout.add_partition(
            partition_id, a, b,
            a1=self.point(a1) if a1 is not None else None,
            a2=self.point(a2) if a2 is not None else None, **kwargs)

    def stack_link(self, link_id, upper_region, lower_region, *,
                   upper_at, lower_at, **kwargs):
        return self._layout.stack_link(
            link_id, upper_region, lower_region,
            upper_at=self.point(upper_at), lower_at=self.point(lower_at),
            **kwargs)

    def paint_wall(self, region_id, a1, a2, **fields):
        return self._layout.paint_wall(region_id, self.point(a1),
                                       self.point(a2), **fields)

    def carry_wall(self, region_id, a1, a2, **kwargs):
        return self._layout.carry_wall(region_id, self.point(a1),
                                       self.point(a2), **kwargs)

    #: Blood's engine-instruction statnum. A sprite on it is not a thing in
    #: the world and its `angle` is not a facing.
    MARKER_STATNUM = 10

    def add_sprite(self, placement_id, region_id, *, x, y, **kwargs):
        wx, wy = self.point((x, y))
        #: A MARKER's angle is a parameter of the motion, not a direction it
        #: faces: for a Marked slide `TranslateSector` interpolates marker0's
        #: angle to marker1's and ROTATES the dragged walls by the result, and
        #: for a rotate it is the turn itself. Turning it with the frame
        #: therefore injects a ninety-degree spin into every slid sector --
        #: which is what the swept gate caught in the casket, whose hole came
        #: out with zero area from the first frame.
        if "angle" in kwargs and int(kwargs.get("status", 0)) != self.MARKER_STATNUM:
            kwargs["angle"] = self.angle(kwargs["angle"])
        return self._layout.add_sprite(placement_id, region_id, x=wx, y=wy,
                                       **kwargs)

    def place_on_floor(self, placement_id, region_id, **kwargs):
        if "angle" in kwargs:
            kwargs["angle"] = self.angle(kwargs["angle"])
        return self._layout.place_on_floor(placement_id, region_id, **kwargs)

    def _oriented(self, a1, a2):
        """The world pair whose off-wall normal points where the local one did.

        `place_on_wall` offsets a sprite along the normal of a1->a2, so the
        ORDER of the pair decides which side of the wall it lands on. Half of
        the four frames are reflections, and under a reflection a normal
        computed the same way comes out reversed -- which put the crack
        sprite outside its branch and every label 46 units above the roof.

        Rather than reason about signs, this transports the LOCAL normal and
        picks whichever world ordering agrees with it.
        """
        d = (a2[0] - a1[0], a2[1] - a1[1])
        n_local = (-d[1], d[0])
        n_world = (self._forward[0] * n_local[0] + self._across[0] * n_local[1],
                   self._forward[1] * n_local[0] + self._across[1] * n_local[1])
        first, second = self.point(a1), self.point(a2)
        dw = (second[0] - first[0], second[1] - first[1])
        candidate = (-dw[1], dw[0])
        if candidate[0] * n_world[0] + candidate[1] * n_world[1] < 0:
            first, second = second, first
        return first, second

    def place_on_wall(self, placement_id, region_id, *, a1, a2, **kwargs):
        first, second = self._oriented(a1, a2)
        return self._layout.place_on_wall(
            placement_id, region_id, a1=first, a2=second, **kwargs)

    def write_on_wall_pair(self, a1, a2):
        """The same ordering fix, for callers that letter a wall."""
        return self._oriented(a1, a2)

    #: `place_on_floor` and `place_on_ceiling` take a fraction of the region
    #: they place into, which is already in world terms. Nothing to rotate.
    def __getattr__(self, name):
        return getattr(self._layout, name)
