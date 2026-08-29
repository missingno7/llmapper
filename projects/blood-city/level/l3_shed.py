"""The pumping station: a road-level way into the sewer, with stairs.

The grate is a one-way drop -- 3.14 player heights, which the engine
forgives (kFallDamageFloor covers anything under 3.70) but which nobody can
climb back up.  The works stair is the way out, and it is tucked inside a
superblock where a player will not find it.

So this is the entrance the owner asked for and the one Blood itself
builds: a small technical building standing on the street, a door, and
stairs going down.  It is a lean-to on the works' east wall rather than a
free-standing hut, because a free-standing mass in the street would add a
tenth walk-around loop and the loop census is at its contract ceiling of
nine.

The descent is real geometry all the way: a straight flight reaches the
cellar, then a 270-degree spiral falls 20,480 units into the sewer directly
below it.  The shaft is cut through both volumes instead of being an ROR
teleport, so its walls and every tread have physical clearance.
"""

from __future__ import annotations

from bloodmap.doors import z_motion_door
from bloodmap.levelprog import Frame, RECT_FACES, Style

from materials import FACADES, INTERIORS, MASONRY
from resolution import (GRADE, PU, STATION_STACK_LANDING_DEPTH,
                        STATION_STACK_PLANE, STREET_SKY)

COMPASS = dict(zip(RECT_FACES, range(4)))

#: The station sits INSIDE the works mass with its door on the rail spur.
#: A lean-to bumped out of the works was tried first: `carve` adds a second
#: hole rather than unioning with the works hole, so the two holes ended up
#: sharing an edge, which is not a legal boundary.  Inside the mass the
#: rooms live in void that is already there, and the door on the spur reads
#: the same from the street.
SHED = (50 * PU, 5 * PU, 53 * PU, 8 * PU)   # x1 is the works' east face

#: One bay wide, on the bay grid, like every other opening in the city.
MOUTH_Y0, MOUTH_H = 6 * PU, 1024
DOOR_D, PORCH_D = 512, 512
#: A door-height porch so the facade owns the wall above the opening.
# Campaign z-motion doors open to a median of 31,744 -- 1.87 player
# heights, measured over 1,269 of them; even their 10th percentile is
# 17,408.  Ours were 16,384, which is 0.97 of a player height: the owner
# called them "short like for midgets" and the census agrees.  Blood has
# no door TEXTURE to lean on (E3M1's own door leaves wear 379 and 449,
# plain wall stone), so an opening reads as a door through its proportion
# and its reveal -- which makes this number the whole fix.
DOOR_HEIGHT = 31744

#: Eight risers of one max step land exactly on the spiral's cellar plane.
STEP, TREAD = 4096, 512
FLIGHT = 8           # one straight run; the works void is long enough
STAIR_W = 1024
CELLAR_FLOOR_Z = STATION_STACK_PLANE
assert CELLAR_FLOOR_Z == GRADE + FLIGHT * STEP

#: The spiral's axis: strictly inside both the cellar and the receiving foot
#: chamber under the ring's north walk.
PIT = (45056, 4608, 46080, 5632)
# The eight-riser flight ends at x=47,616; keep the cellar flush with that
# arrival edge rather than leaving a one-bay unpaired gap after changing the
# shared ROR plane.
# The north edge stops exactly at the sewer walk's south wall.  The former
# extra plan unit intruded into that under-city tunnel at the cellar's own z;
# a real shaft must meet the tunnel at a boundary, never share its air.
CELLAR = (44032, 3584, 47616, 6144)
PIT_LANDING = STATION_STACK_LANDING_DEPTH


def build(district, foundry_st, foundry_origin):
    city = district
    """The shed, its stair, and the cellar that holds the pit."""
    fx0, fy0 = foundry_origin
    sx0, sy0, sx1, sy1 = SHED

    service = INTERIORS["service"]
    shed = city.assembly(
        "pump_station",
        # Lit like a room someone works in, not like the sewer.  The source
        # declarations below now provide that readability; keeping a blanket
        # manual shade here would prevent LightBomb from deriving falloff.
        style=Style(**service.style_kwargs(floor_z=GRADE,
                                           clear_height=32768)),
        note="the pumping station: the sewer's road-level entrance",
    )

    def room(name, x0, y0, x1, y1, *, floor_z=GRADE, role="interior",
             clear=32768, note="", rk=None):
        made = shed.room(
            name, [(0, 0), (x1 - x0, 0), (x1 - x0, y1 - y0), (0, y1 - y0)],
            role=role, faces=dict(COMPASS), frame=Frame(int(x0), int(y0)),
            region_kwargs={**service.region_kwargs(), **(rk or {})},
            note=note)
        # Keep these base surfaces unprotected so declared fixtures own the
        # illumination.  Use a direct shade only for a deliberate local
        # art-direction override.
        made.surfaces(**service.style_kwargs(floor_z=floor_z,
                                             clear_height=clear))
        return made

    # Street -> porch -> door -> hall.
    porch = room("porch", sx1 - PORCH_D, MOUTH_Y0, sx1, MOUTH_Y0 + MOUTH_H,
                 role="gateway", clear=DOOR_HEIGHT,
                 note="the station's reveal, so the facade owns the wall above")
    porch.surfaces(wall_picnum=MASONRY.wall, ceiling_picnum=MASONRY.wall,
                   floor_z=GRADE, clear_height=DOOR_HEIGHT)
    door = room("door", sx1 - PORCH_D - DOOR_D, MOUTH_Y0,
                sx1 - PORCH_D, MOUTH_Y0 + MOUTH_H, role="doorway", clear=0,
                rk={"type": 600, "door_face": 22, "inherit_finish": "both",
                    "sector_behavior": z_motion_door(GRADE, GRADE - DOOR_HEIGHT)},
                note="the station door")
    door.surfaces(wall_picnum=MASONRY.wall, floor_z=GRADE, clear_height=0)
    hall = room("hall", sx0 + 512, sy0, sx1 - PORCH_D - DOOR_D, sy1 - 512,
                note="the station floor: the stair head is in here")

    city.connect(porch.face("east"), foundry_st.face("west"),
                 connection_id="connection:pump_station_street")
    shed.connect(door.face("east"), porch.face("west"),
                 connection_id="connection:pump_door_porch")
    shed.connect(door.face("west"), hall.face("east"),
                 connection_id="connection:pump_door_hall")

    # One straight flight west into the works void, then the cellar.
    # The stair uses the hall's southern bay, so it arrives entirely above the
    # shortened cellar rather than into the sewer walk beyond its north wall.
    stair_y0 = sy0
    cellar = room("cellar", *CELLAR, floor_z=CELLAR_FLOOR_Z, clear=20480,
                  role="gateway",
                  note="the station cellar; its pit drops into the sewer")

    # The stair is one bay wide, taken from a sub-span of the hall's west
    # face: anchored to the whole face it would be three plan units wide and
    # would run straight through the rail-yard backdrop box.
    face_len = (sy1 - 512) - sy0
    # The west face is wound south-to-north, so its anchor fraction runs in
    # the opposite direction to the room's local y coordinate.
    at = 1.0 - ((stair_y0 + STAIR_W / 2) - sy0) / face_len
    hall.staircase(
        "pump_flight", "west", at=at, width=STAIR_W,
        total_rise=FLIGHT * STEP, tread=TREAD, step_rise=STEP,
        arrive_at=cellar.region_id, connection={"role": "portal"})

    # The caller cuts the curved opening for the sewer spiral.  Leaving the
    # carve here would create a second, disconnected hole beside the stair.
    # `_assembly` lets the caller keep that spiral inside the station rather
    # than at the top of the city.
    return {"hall": hall, "cellar": cellar, "_assembly": shed}
