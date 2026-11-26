"""A hole blown through a wall, shaped the way Blood shapes one: ragged pieces with tilted sills and tops.

The owner, 2026-11-22: "Blown out holes are usually using sloped floor and
ceiling and usually aren't regular, our look too blocky." Measured over the
campaign's 185 sectors a wall crack opens (`knowledge/blood/findings/probes/sewer-study_breach_shapes.json`):

* a hole is one to three sectors side by side across the wall (of 96
  holes, 46 are one piece, 23 two, 20 three, 5 four, and one each of five
  and eight);
* 137 of the 185 have an edge on the slant: the seams between the pieces
  and the jambs at the ends cut across the wall's thickness at an angle
  (E1M1 sector 25: a 1,792-wide hole whose west jamb runs 192 along over
  256 through);
* 116 slope their floor and 123 their ceiling, mostly by 512-1,536 -- and
  each about a slanted edge, so the slope runs ACROSS the hole's width: the
  top is a zigzag and the sill rises and falls (E1M2 channel 104: three
  pieces, tops at -112,640, -109,568 and -116,736, ceilings pitched both
  ways);
* a hole shuts by its ceiling coming down: in 87 pieces onto a floor that
  stays, in 98 with floor and ceiling meeting between. 178 of the 185 keep
  the ceiling slope at least the floor slope, so the shut piece is solid
  everywhere and not only along its hinge (`ragged` builds the first kind);
* the sill is above the floor it opens from (E1M2: 2,048-3,072; E1M1's
  are window holes, 7,168 up).

This module is the geometry and the heights only, in the hole's own frame:
`u` along the wall from 0 to `width`, `v` through it from 0 (the near side,
where the blast came from) to `depth`. Each piece's outline is wound like a
`rect_room`'s, so any of its edges is a valid hinge with the inside on the
positive side, and Build's ``z = z0 + heinum * distance / 256`` reads as:
a positive heinum goes DOWN going in.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .player_space import PLAYER_PROFILES

#: what a piece's open height must leave over a standing body, everywhere in it
HEADROOM = 512
#: the sill above the near floor, at its lowest and highest anywhere in a piece
SILL_MIN, SILL_MAX = 256, 2560
#: floor and ceiling slopes the campaign's holes use (heinum, z per 256 across)
FLOOR_HEINUMS = (256, 512, 768)
CEILING_EXTRA = (512, 1024, 1536)
#: a piece no narrower than this at either face (a body is 384 wide)
MIN_FACE = 192
#: a hole's pieces are about this wide: narrow enough that their tops make a
#: zigzag, as E1M2 channel 104's three pieces of 1,024-1,152 do across 2,432
PIECE_WIDTH = 384
#: THE SHOULDERS. A hole of three pieces or more keeps its end pieces low:
#: rubble the blast did not clear, a sill up to this much higher than the
#: middle's and a top this share of the way down from the middle's,
#: falling away from the middle -- the broken outline of E1M2's and
#: E1M1's holes, where a hole of pieces all a body tall reads as a door.
SHOULDER_SILL = 1536
SHOULDER_DROP = (0.3, 0.55)
SHOULDER_CEILING = (1536, 2048, 2560)
#: and leaves this much open even at its lowest
SHOULDER_GAP = 2048


@dataclass
class Piece:
    """One sector of a blown hole, in the hole's frame."""

    outline: list[tuple[int, int]]       # near-left, near-right, far-right, far-left
    hinge: tuple[tuple[int, int], tuple[int, int]]
    sill: int                            # floor at the hinge, ABOVE the near floor
    floor_heinum: int
    ceiling_heinum: int
    opening: int                         # open height at the hinge
    #: edge index of each face: "near" 0, "right" 1, "far" 2, "left" 3
    faces: dict

    def clearance(self) -> float:
        """The least open height anywhere in the piece."""
        far = max(_distance(p, self.hinge) for p in self.outline)
        return self.opening - (self.ceiling_heinum - self.floor_heinum) * far / 256


def _distance(point, hinge) -> float:
    (ax, ay), (bx, by) = hinge
    dx, dy = bx - ax, by - ay
    return (dx * (point[1] - ay) - dy * (point[0] - ax)) / math.hypot(dx, dy)


def ragged(width: int, depth: int, *, seed: str, pieces: int | None = None,
           sill: tuple[int, int] = (SILL_MIN, SILL_MAX), top: int | None = None,
           headroom: int = HEADROOM) -> list[Piece]:
    """The pieces of a hole `width` along a wall `depth` thick, the same every time for one `seed`.

    The middle pieces clear a standing body plus `headroom` everywhere; the
    end pieces of a hole of three or more are its shoulders (`SHOULDER_*`),
    low and falling away from the middle. `sill`
    bounds its floor above the near floor, anywhere in it. `top` is the
    highest its ceiling may reach above the near floor: under a low ceiling
    on the near side the hole's ragged top must sit below it, or that
    ceiling's straight edge is all that shows.
    """
    rng = random.Random(seed)
    standing = PLAYER_PROFILES["blood"].standing_height
    if pieces is None:
        pieces = max(1, min(5, round(width / PIECE_WIDTH)))
    slant = depth * 0.6
    # the seams and the jambs: where each crosses the near face and the far
    for _attempt in range(64):
        near = [0] + [0] * (pieces - 1) + [width]
        far = [0] + [0] * (pieces - 1) + [width]
        # one end of each jamb is set in from the wall's edge
        for end, inward in ((0, 1), (pieces, -1)):
            setback = int(rng.uniform(96, max(97, slant)))
            if rng.random() < 0.5:
                near[end] += inward * setback
            else:
                far[end] += inward * setback
        for k in range(1, pieces):
            at = width * k / pieces + rng.uniform(-0.15, 0.15) * width / pieces
            lean = rng.uniform(-slant, slant)
            near[k], far[k] = int(at - lean / 2), int(at + lean / 2)
        if all(near[k + 1] - near[k] >= MIN_FACE and far[k + 1] - far[k] >= MIN_FACE
               for k in range(pieces)):
            break
    else:
        near = far = [int(width * k / pieces) for k in range(pieces + 1)]
    out = []
    for k in range(pieces):
        outline = [(near[k], 0), (near[k + 1], 0), (far[k + 1], depth), (far[k], depth)]
        if pieces >= 3 and k in (0, pieces - 1):
            continue                      # the shoulders, once the middle is made
        out.append(_passable(rng, outline, standing + headroom - HEADROOM, sill, top, seed))
    if pieces >= 3:
        middle_top = min(p.sill + p.opening for p in out)
        middle_sill = max(p.sill for p in out)
        left = _shoulder(rng, [(near[0], 0), (near[1], 0), (far[1], depth), (far[0], depth)],
                         1, middle_top, middle_sill, sill, top, seed)
        right = _shoulder(rng, [(near[-2], 0), (near[-1], 0), (far[-1], depth), (far[-2], depth)],
                          3, middle_top, middle_sill, sill, top, seed)
        out = [left] + out + [right]
    return out


FACES = {"near": 0, "right": 1, "far": 2, "left": 3}


def _passable(rng, outline, standing, sill, top, seed) -> Piece:
    """A piece a body walks through: random pitch, clear everywhere, under `top`."""
    side = rng.choice((1, 3))
    hinge = (outline[side], outline[(side + 1) % 4])
    reach = max(_distance(p, hinge) for p in outline)
    sign = rng.choice((-1, 1))
    need = standing + HEADROOM
    for fh in (sign * rng.choice(FLOOR_HEINUMS), sign * FLOOR_HEINUMS[0], 0):
        # the floor's height above the near floor goes from `s` at the
        # hinge to `s - fh * reach / 256` across: both inside `sill`
        drop = fh * reach / 256
        low, high = sill[0] + max(0.0, drop), sill[1] + min(0.0, drop)
        if low > high:
            continue
        s = int(rng.uniform(low, high)) // 128 * 128
        if s < low:
            s += 128
        extras = list(CEILING_EXTRA)
        rng.shuffle(extras)
        for extra in extras + [256, 0]:
            ch = fh + extra
            lo = need + extra * reach / 256
            # the top, `s + opening - ch * d / 256`, is highest at the
            # hinge or across, by the sign of the ceiling's slope
            hi = lo + 2048 if top is None else top - max(s, s - ch * reach / 256)
            if lo <= hi:
                opening = int(math.ceil(rng.uniform(lo, min(hi, lo + 2048))))
                return Piece(outline=outline, hinge=hinge, sill=s, floor_heinum=int(fh),
                             ceiling_heinum=int(ch), opening=opening, faces=dict(FACES))
    raise ValueError(f"{seed}: no piece clears a body under a top of {top} over a sill of {sill}")


def _shoulder(rng, outline, inner, middle_top, middle_sill, sill, top, seed) -> Piece:
    """An end piece: hinged on its seam with the middle, its top falling and its floor rising outward."""
    hinge = (outline[inner], outline[(inner + 1) % 4])
    reach = max(_distance(p, hinge) for p in outline)
    s = int(rng.uniform(middle_sill, middle_sill + SHOULDER_SILL)) // 128 * 128
    s = max(sill[0], s)
    # the floor rises going out (negative: up), the ceiling falls (positive);
    # the ceiling's heinum is still at least the floor's, so it shuts solid
    fh = -rng.choice(FLOOR_HEINUMS)
    at_seam = middle_top - (middle_top - s) * rng.uniform(*SHOULDER_DROP)
    if top is not None:
        at_seam = min(at_seam, top)
    opening = int(at_seam - s)
    choices = list(SHOULDER_CEILING)
    rng.shuffle(choices)
    for ch in choices + [1024, 512, 0]:
        if opening - (ch - fh) * reach / 256 >= SHOULDER_GAP:
            return Piece(outline=outline, hinge=hinge, sill=s, floor_heinum=int(fh),
                         ceiling_heinum=int(ch), opening=opening, faces=dict(FACES))
    raise ValueError(f"{seed}: a shoulder {opening} open cannot keep {SHOULDER_GAP} over {reach:.0f}")


def world(piece: Piece, origin, along, through) -> tuple[list, tuple]:
    """A piece's outline and hinge on a wall in the world.

    `origin` is where the hole's frame starts (u 0 on the near face),
    `along` the unit step along the wall and `through` the step through it,
    away from the near side. The two must turn the way a `rect_room` winds
    (``along x through = +1``), or every slope's sign would flip with it.
    """
    ax, ay = along
    tx, ty = through
    if ax * ty - ay * tx != 1:
        raise ValueError(f"along {along} and through {through} wind the hole the wrong way round")

    def place(p):
        return (int(origin[0] + ax * p[0] + tx * p[1]), int(origin[1] + ay * p[0] + ty * p[1]))

    return [place(p) for p in piece.outline], (place(piece.hinge[0]), place(piece.hinge[1]))


def lay(assembly, name: str, pieces: list[Piece], *, origin, along, through, near_floor: int,
        region_kwargs: dict, rx_id: int, note: str, surfaces: dict | None = None) -> list:
    """The pieces as rooms of a `levelprog` assembly, each a Z-motion sector shut on its floor, seams joined.

    The floor never moves; the ceiling lies on it until `rx_id` fires and
    then rises `opening` (`bloodmap.doors.z_motion_door`, once). Each room
    has the faces "near", "far", "left" and "right"; the caller joins near
    and far, wires the channel's sender, and types the rooms 600 after any
    door pass (a framed door is not a hole).
    """
    from .doors import z_motion_door
    from .levelprog import Frame
    from .slope import SlopeSpec

    rooms = []
    for k, piece in enumerate(pieces):
        outline, hinge = world(piece, origin, along, through)
        fx, fy = min(p[0] for p in outline), min(p[1] for p in outline)
        floor = int(near_floor) - piece.sill
        room = assembly.room(
            f"{name}_{k}", [(x - fx, y - fy) for x, y in outline], role="doorway",
            faces=dict(piece.faces), frame=Frame(fx, fy),
            region_kwargs={**region_kwargs,
                           "floor_slope": SlopeSpec(hinge=hinge, heinum=piece.floor_heinum),
                           "ceiling_slope": SlopeSpec(hinge=hinge, heinum=piece.ceiling_heinum),
                           "sector_behavior": {
                               **z_motion_door(floor, floor - piece.opening, interaction="remote",
                                               rx_id=rx_id, open_time=1),
                               "trigger_once": 1}},
            note=f"{note}: piece {k + 1} of {len(pieces)}")
        room.surfaces(**{**(surfaces or {}), "floor_z": floor, "clear_height": 0})
        if rooms:
            assembly.connect(rooms[-1].face("right"), room.face("left"),
                             connection_id=f"connection:{name}_seam_{k}")
        rooms.append(room)
    return rooms


def face_middle(room, face: str = "near") -> tuple[float, float]:
    """The middle of a laid piece's "near" or "far" face, in the world: where it meets that side."""
    points = room.world_outline()
    index = FACES[face]
    (ax, ay), (bx, by) = points[index], points[(index + 1) % len(points)]
    return (ax + bx) / 2, (ay + by) / 2
