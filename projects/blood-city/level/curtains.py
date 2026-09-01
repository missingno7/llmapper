"""The Aldermack's stage curtains, and the light that follows them.

The city speaks the levelprog TREE and `mechanism.curtain` speaks
PlanarLayout, so this follows the route `turnstiles.py` already established:
take the constructor's FACTS -- `mechanism.curtain_spec` -- and build the
geometry in the tree, then furnish on the compiled layout. Re-deriving the fin
here instead is how two curtains come to disagree about what a curtain is.

**The curtain is a fin**, per `maps/blood/mechanism/Vanilla/DOOR-CURTAINS.map`:
eight walls, the four sides of the proscenium plus a narrow tab hanging from
the anchored edge, and only the tab's free end is flagged. Drawing it across
stretches the tab's two sides, and that stretch is the fabric.

**The repeat is authored for the CLOSED span.** The geometry is saved at the
ON pose, so the fabric in the file is the gathered bundle; sizing the texture
to what the file shows is what left the zoo's curtain at forty-eight times
natural stretch. `curtain_spec` returns the repeats for the span the cloth
hangs ACROSS.

**The stage light follows the curtain** by a command-5 Link, which is the
E1M1 s125 -> s124 pattern and DOOR-CURTAINS s21 -> s20. kCmdLink is excluded
from `SetSpriteState`'s edge guards precisely because it couples state
CONTINUOUSLY rather than firing once: the light does not switch when the
curtain finishes, it tracks it.

That link is also where the single-slot problem bites. The curtain's sector
already spends its rx on the channel that opens it, and a sector has ONE tx.
So the arbiter is asked before the link is wired, and its decision is
reported rather than assumed.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from bloodmap import motion
from bloodmap.arbiter import Claim, FUNCTION, PRESENTATION, arbitrate, report
from bloodmap.levelprog import RECT_FACES, Frame
from bloodmap.mechanism import CURTAIN_PICNUM, curtain_spec

COMPASS = dict(zip(RECT_FACES, range(4)))

#: How deep the proscenium band is: the doorway the fin hangs in. Wide enough
#: that a 64 tab sits inside it with reveal either side.
PROSCENIUM = 256
#: Fifteen tenths each way, which is what every tutorial curtain uses.
BUSY = 15
#: The channel the curtain answers, and the one it drives.
CH_CURTAIN = 340
CH_STAGE_LIGHT = 341
#: The shade wave the stage light runs when the curtain is open. Negative
#: amplitude BRIGHTENS in Blood.
STAGE_AMPLITUDE = -24


def _on_rect(point, rect, tol: int = 1) -> bool:
    """Is this point on the boundary of `rect`?"""
    x, y = point
    x0, y0, x1, y1 = rect
    on_x = abs(x - x0) <= tol or abs(x - x1) <= tol
    on_y = abs(y - y0) <= tol or abs(y - y1) <= tol
    inside = x0 - tol <= x <= x1 + tol and y0 - tol <= y <= y1 + tol
    return inside and (on_x or on_y)


def hang(auditorium, district, stage_rect, *, grade: int, clear: int,
         name: str = "stage_curtain"):
    """Cut the proscenium fin out of the auditorium and stand it there.

    Returns the spec and the region name so the furnishing pass can find it.
    The fin is carved from the auditorium and matches that hole exactly,
    which is the compiler's rule for anything standing in a carved opening.
    """
    sx0, sy0, sx1, sy1 = (int(v) for v in stage_rect)
    #: JUST IN FRONT of the stage's front edge, not flush on it. The stage is
    #: its own region -- a raised solid inside the auditorium -- so a band
    #: starting exactly at `sy1` shares a boundary with it, and two regions
    #: that share a boundary must be a portal. The curtain is a portal to the
    #: HOUSE, not to the stage, so it hangs one band clear and the proscenium
    #: line stays the stage's own.
    opening = (sx0, sy1 + PROSCENIUM, sx1, sy1 + 2 * PROSCENIUM)
    spec = curtain_spec(opening=opening, axis="x", anchored="high")

    behavior = {
        "busy_time_a": BUSY, "busy_time_b": BUSY,
        "rx_id": CH_CURTAIN,
    }
    #: In the AUDITORIUM's own coordinates. It is framed at its own origin
    #: -- `make` builds every theatre room as a local rect at Frame(x0, y0) --
    #: so a world-coordinate carve puts the hole thousands of units outside
    #: the room it is meant to be in. The compiler then sees a curtain
    #: contained in an auditorium with no matching hole, which is exactly the
    #: error it reported.
    origin = auditorium.world_frame()
    ox, oy = int(getattr(origin, "dx", 0)), int(getattr(origin, "dy", 0))
    #: THE HOLE IS THE DOORWAY, NOT THE FIN.
    #:
    #: Carving the fin's own outline is what broke the first build, and it
    #: broke it twice over. The hole and the room were then the SAME polygon,
    #: so all eight walls coincided and all eight paired as portals into the
    #: house -- the slot included. That made the motion drag the auditorium
    #: (DragPoint walks nextwall, triggers.cpp:817-854) AND made the fabric
    #: invisible, because a two-sided unmasked wall draws its picnum only on
    #: the step bands (engine.cpp:4938-4940).
    #:
    #: DOOR-CURTAINS s3 does it the other way: the slot is a NOTCH cut out of
    #: the doorway rect, and the space inside the notch belongs to nobody. Its
    #: three walls are one-sided (`next -1`), which is why the fabric is the
    #: wall and draws everywhere a body can see it.
    #:
    #: So the house gives up the DOORWAY RECT, the fin stands inside it, and
    #: the notch is left as solid void.
    ox0, oy0, ox1, oy1 = (min(opening[0], opening[2]), min(opening[1], opening[3]),
                          max(opening[0], opening[2]), max(opening[1], opening[3]))
    auditorium.carve([(ox0 - ox, oy0 - oy), (ox1 - ox, oy0 - oy),
                      (ox1 - ox, oy1 - oy), (ox0 - ox, oy1 - oy)])
    room = district.room(
        #: EVERY edge is named, not just four. `faces` is a name -> outline
        #: edge index map, and a fin has eight edges: the compass names cover
        #: the doorway's rectangle and leave the tab's four unnamed, so half
        #: the portal candidates had no way to be declared.
        name, spec["outline"], role="doorway",
        faces={f"e{index}": index for index in range(len(spec["outline"]))},
        frame=Frame(0, 0),
        region_kwargs={"type": 614, "sector_behavior": behavior},
        note=("the Aldermack's stage curtain: a fin across the proscenium, "
              "drawn across at rest and gathering when it opens"),
        intent={"kind": "curtain", "venue": "aldermack"},
    )
    room.surfaces(floor_z=grade, clear_height=clear)
    #: Declare the fin's edges as portals to the house. All eight pair on
    #: their own once the relationship exists -- the compiler had matched
    #: every one of them and refused only because nothing said they were
    #: meant to be a way through.
    import citytree

    #: Only the DOORWAY's four edges are portals. The notch's three walls
    #: face the void the notch leaves behind and stay one-sided, which is the
    #: whole point.
    doorway_edges = [index for index, point in enumerate(spec["outline"])
                     if _on_rect(point, (ox0, oy0, ox1, oy1))
                     and _on_rect(spec["outline"][(index + 1)
                                                  % len(spec["outline"])],
                                  (ox0, oy0, ox1, oy1))]
    for index in doorway_edges:
        citytree.join(room, auditorium, at_a=f"e{index}", at_b="north",
                      connection_id=f"connection:{name}_e{index}")
    return {"spec": spec, "room": room, "name": name,
            "channel": CH_CURTAIN, "opening": opening}


def furnish(layout, built, *, stage_region: str, grade: int) -> dict:
    """Markers, flags, fabric and wiring, once the layout exists.

    Everything here needs compiled walls, which is why it is a second pass --
    the same split `turnstiles.populate` uses.
    """
    spec = built["spec"]
    region = built["room"].region_id
    out = {"leaves": spec["leaves"], "slot": spec["slot"], "markers": 0,
           "flagged": 0, "fabric": 0, "buttons": 0}

    #: STATE-ANCHORED markers: type 3 is the position for state OFF and type
    #: 4 for state ON. The geometry is saved at the ON pose and `state`
    #: decides the snap, so with no state the curtain comes up CLOSED.
    for kind, point in ((motion.MARKER_OFF, spec["off_at"]),
                        (motion.MARKER_ON, spec["on_at"])):
        layout.add_sprite(
            f"placement:{built['name']}:marker{kind}", region,
            x=int(point[0]), y=int(point[1]), z=int(grade),
            type=int(kind), status=motion.MARKER_STATNUM,
            picnum=motion.MARKER_PICNUM, cstat=motion.MARKER_CSTAT,
            x_repeat=64, y_repeat=64, angle=0)
        out["markers"] += 1

    #: Only each leaf's free END is flagged -- that is what makes the payload
    #: "part of the sector travels" rather than a leaf sliding aside. Two
    #: leaves carry OPPOSITE flags so they converge instead of travelling
    #: together.
    for flag in spec["flagged"]:
        edge = flag["edge"]
        layout.carry_wall(region, edge[0], edge[1], moves=flag["moves"])
        out["flagged"] += 1

    #: The fabric, sized for the span it hangs ACROSS.
    for edge, repeat in zip(spec["fabric"], spec["x_repeats"]):
        layout.paint_wall(region, edge[0], edge[1],
                          picnum=int(CURTAIN_PICNUM), x_repeat=int(repeat))
        out["fabric"] += 1
        #: and each fabric face is a button, the way the tutorial wires a
        #: shove: an XWALL on the cloth, not `trigger_wall_push` on the
        #: sector, so pushing the proscenium arch does nothing.
        motion.wall_button(layout, region, edge, channel=CH_CURTAIN,
                           command=motion.CMD_TOGGLE, receiver_state=0)
        out["buttons"] += 1

    return out


def link_stage_light(layout, built, *, stage_region: str) -> dict:
    """Wire the stage light to follow the curtain, arbitrating the collision.

    The curtain's sector has ONE tx and its rx is already spent on the
    channel that opens it. The link needs a transmitter, so this is a real
    single-slot collision and it is decided rather than assumed.
    """
    claims = [
        Claim("curtain:opens", "curtain sector", "rx", FUNCTION,
              "the channel that draws the curtain"),
        Claim("curtain:drives_light", "curtain sector", "tx", FUNCTION,
              "the command-5 Link the stage light follows"),
        Claim("stage:shade_wave", "stage sector", "shade wave", PRESENTATION,
              "the light the curtain drives"),
    ]
    decisions, _survivors = arbitrate(claims)

    #: The curtain transmits the Link. kCmdLink is sent OUTSIDE the edge
    #: guards, so it needs no trigger_on -- it couples state continuously,
    #: which is what "the light follows the curtain" means.
    #:
    #: A region's `sector_behavior` is the XSECTOR the compiler will write,
    #: and it is still open between the program's compile and the layout's --
    #: which is exactly the window this pass runs in.
    curtain_region = layout.regions[built["room"].region_id]
    curtain_region.sector_behavior.update(
        {"tx_id": CH_STAGE_LIGHT, "command": motion.CMD_LINK})
    stage = layout.regions.get(stage_region)
    if stage is None:
        payload = report(decisions)
        payload["wired"] = None
        payload["refused"] = f"no region {stage_region!r} to light"
        return payload
    stage.sector_behavior.update(
        {"rx_id": CH_STAGE_LIGHT, "amplitude": STAGE_AMPLITUDE,
         "shade_floor": 1, "shade_ceiling": 1, "shade_walls": 1})
    payload = report(decisions)
    payload["wired"] = {"channel": CH_STAGE_LIGHT,
                        "command": motion.CMD_LINK,
                        "from": built["room"].region_id,
                        "to": stage_region}
    return payload
