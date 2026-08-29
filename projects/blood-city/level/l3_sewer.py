"""The sewer network proper: a ring, its branches, and places to go.

The early network was a trunk with three chambers hanging off it -- enough
to prove the stack links, nowhere near the contract.  sewer-patterns.md
asks for a network with its own topology (internal cycle rank 7+, denser
than the street's), a wet share of 0.2-0.4 measured against E3M3, and a
secret branch.

Three things from E3M3 shape what gets built, not just how much:

* its **cross-section** is a ledge beside a channel -- 62 ledge-over-channel
  pairs, the walk one max step (4096) above the water;
* it is **wet**: 29% of its sectors, against DukCity's dry 0-2%;
* it is **lightly wired but restless**: 23 user channels, yet 175 of its 309
  sectors animate their shade.

Geometry rule that keeps the compiler happy, learned the hard way in this
project: two rooms may share an edge only if one face is *exactly* the
other, or *strictly inside* it, and the connection must be anchored from
the smaller face.  Tunnel segments are laid end to end with matching faces;
anything meeting a tunnel mid-run does so through a neck.
"""

from __future__ import annotations

from bloodmap.levelprog import Frame, RECT_FACES, Style

from materials import SEWER, SEWER_WET
from resolution import (PU, SEWER_CHAMBER_CLEAR, SEWER_CLEAR, SEWER_FLOOR,
                        STATION_STACK_PLANE)

COMPASS = dict(zip(RECT_FACES, range(4)))

#: The walk sits one max step above its channel (E3M3's median step).
LEDGE_STEP = 4096
#: E3M3's shallow-water form, the one that reads wet in our own frames.
WATER_DEPTH = 7

#: The ring, directly below Foundry Ward in the city's plan units.  Corner-leg-corner-leg
#: all the way round, faces matching exactly at every join.  The north and
#: south legs are split lengthwise into a walk and a channel: that is the
#: cross-section, not decoration.
RING = [
    ("nw_corner", 32.0, 6.0, 34.0, 8.0),
    ("n_walk", 34.0, 6.0, 51.0, 7.0),
    ("n_channel", 34.0, 7.0, 51.0, 8.0),
    ("ne_corner", 51.0, 6.0, 53.0, 8.0),
    ("e_leg", 51.0, 8.0, 53.0, 32.0),
    ("se_corner", 51.0, 32.0, 53.0, 34.0),
    ("s_channel", 34.0, 32.0, 51.0, 33.0),
    ("s_walk", 34.0, 33.0, 51.0, 34.0),
    ("sw_corner", 32.0, 32.0, 34.0, 34.0),
    ("w_leg", 32.0, 8.0, 34.0, 32.0),
]

#: Ring joins, each anchored from the smaller face.
RING_JOINS = [
    ("n_walk", "west", "nw_corner", "east"),
    ("n_channel", "west", "nw_corner", "east"),
    ("n_walk", "east", "ne_corner", "west"),
    ("n_channel", "east", "ne_corner", "west"),
    ("n_walk", "south", "n_channel", "north"),
    ("ne_corner", "south", "e_leg", "north"),
    ("e_leg", "south", "se_corner", "north"),
    ("s_walk", "east", "se_corner", "west"),
    ("s_channel", "east", "se_corner", "west"),
    ("s_channel", "south", "s_walk", "north"),
    ("s_walk", "west", "sw_corner", "east"),
    ("s_channel", "west", "sw_corner", "east"),
    ("sw_corner", "north", "w_leg", "south"),
    ("w_leg", "north", "nw_corner", "south"),
]

#: Places to go, hanging off the ring: (name, rect, own face, leg, leg face).
CHAMBERS = [
    ("pump_room", 27.0, 12.0, 32.0, 18.0, "east", "w_leg", "west",
     "the pumping chamber: the network's one big room"),
    ("silt_trap", 45.5, 2.0, 50.0, 6.0, "south", "n_walk", "north",
     "a silt trap off the north walk"),
    ("east_annex", 53.0, 14.0, 57.0, 20.0, "west", "e_leg", "east",
     "the annex: an eastern dead end worth the walk for what is in it"),
    ("flooded", 40.0, 34.0, 46.0, 39.0, "north", "s_walk", "south",
     "the flooded branch, waist-deep"),
    ("station_foot", 43.5, 4.0, 45.5, 6.0, "south", "n_walk", "north",
     "the foot of the pumping station's shaft: where the stairs deliver "
     "you, and the way back up"),
]

#: Necks joining the ring to the network that already existed.
NECKS = [
    ("west_adit", 34.0, 11.0, 39.25, 13.0,
     [("west", "w_leg", "east"), ("east", "junction", "west")],
     "the west adit: the ring's way into the junction"),
    ("neck_cistern", 44.0, 31.0, 46.0, 32.0,
     [("north", "cistern", "south"), ("south", "s_channel", "north")],
     "the cistern's overflow into the ring"),
]


def expand(city, sewer, existing: dict) -> dict:
    """Build the ring, its chambers and the necks onto the under-city."""
    import citytree
    rooms: dict = {}

    #: The chambers stand taller than the runs, as E3M3's do: a network
    #: whose every sector is the same height reads as extruded plan, and it
    #: is the tunnels' flat low ceiling that fills our frames.
    chambers = {name for name, *_rest in CHAMBERS}

    # The network has three parts and used to have none: 23 sibling rooms
    # under one `sewer` assembly, a ring leg and a secret chamber and a neck
    # all at the same level.  The parts are what the tables already say.
    parts = {
        "ring": sewer.assembly("ring", note="the circuit: legs, corners, channels"),
        "chambers": sewer.assembly("chambers", note="what the ring passes through"),
        "necks": sewer.assembly("necks", note="the short joins between the two"),
    }

    def room(name, x0, y0, x1, y1, *, part="ring", wet=False, note="",
             role="interior", animate=True):
        material = SEWER_WET if wet else SEWER
        # E3M3 animates 57% of its sectors; animating every plain leg put us
        # at 79%, so the restless light goes to the water and the chambers.
        behavior = {"amplitude": -16, "shade_frequency": 9} if animate else {}
        if wet:
            behavior["depth"] = WATER_DEPTH
        made = parts[part].room(
            name,
            [(0, 0), (int((x1 - x0) * PU), 0),
             (int((x1 - x0) * PU), int((y1 - y0) * PU)),
             (0, int((y1 - y0) * PU))],
            role=role, faces=dict(COMPASS),
            frame=Frame(int(x0 * PU), int(y0 * PU)),
            region_kwargs={**material.region_kwargs(),
                           "sector_behavior": behavior},
            note=note)
        clear = SEWER_CHAMBER_CLEAR if name in chambers else SEWER_CLEAR
        if name == "station_foot":
            # Match the lower ROR half exactly.  The prior chamber roof was
            # 20,480 units higher than the linked mouth, producing a visible
            # ceiling discontinuity at the entrance.
            clear = SEWER_FLOOR - STATION_STACK_PLANE
        made.surfaces(**material.style_kwargs(
            floor_z=SEWER_FLOOR + (LEDGE_STEP if wet else 0),
            clear_height=clear + (LEDGE_STEP if wet else 0),
            floor_shade=38 if wet else 40))
        rooms[name] = made
        return made

    for name, x0, y0, x1, y1 in RING:
        room(name, x0, y0, x1, y1, wet=name.endswith("channel"),
             animate=name.endswith(("channel", "corner")),
             note=f"sewer ring: {name.replace('_', ' ')}")
    for a, fa, b, fb in RING_JOINS:
        citytree.join(rooms[a], rooms[b], at_a=fa, at_b=fb,
                      connection_id=f"connection:ring_{a}_{fa}_{b}")

    for name, x0, y0, x1, y1, own, leg, leg_face, note in CHAMBERS:
        made = room(name, x0, y0, x1, y1, part="chambers",
                    wet=(name == "flooded"), note=note,
                    role="secret" if name == "flooded" else "interior")
        if name == "flooded":
            # SP's secret branch: `secret=True` emits the campaign's own
            # wiring rather than a label (channel 2, command 64, once).
            made.region_kwargs["secret"] = True
        citytree.join(made, rooms[leg], at_a=own, at_b=leg_face,
                      connection_id=f"connection:sewer_{name}")

    for name, x0, y0, x1, y1, joins, note in NECKS:
        made = room(name, x0, y0, x1, y1, part="necks", note=note,
                    role="gateway")
        for own_face, other, other_face in joins:
            target = rooms.get(other) or existing[other]
            sewer.connect(made.face(own_face), target.face(other_face),
                          connection_id=f"connection:{name}_{own_face}")
    return rooms


#: What lives down here, from E3M3's own census: bone eels (17), rats (9),
#: gill beasts (7) -- water dwellers and scavengers, no cultist garrison.
POPULATION = [
    ("pump_room", 220, (0.3, 0.4)),      # rat
    ("pump_room", 220, (0.7, 0.6)),
    ("n_walk", 220, (0.2, 0.5)),
    ("east_annex", 217, (0.5, 0.5)),     # gill beast, guarding the annex
    ("flooded", 218, (0.5, 0.4)),        # bone eel, in the water
    ("s_walk", 220, (0.7, 0.5)),
]

#: Something to find at the end of each walk, so a branch is worth taking.
PICKUPS = [
    ("east_annex", 62, (0.35, 0.5)),
    ("silt_trap", 65, (0.5, 0.5)),
    ("flooded", 60, (0.7, 0.6)),
    ("pump_room", 109, (0.5, 0.75)),
]

#: A brazier at the chambers and the ring's corners, BRACKETED TO A WALL:
#: (room, face, t).  E3M3 is dark but not unlit, and our animated shade
#: needs a source to justify it.
#: The sewer keeps its corner lights: it is a dark ring with four
#: identical turns, and they are the only thing that tells one from
#: another.  Recorded as a deliberate deviation from the 3% rate.
LIT = [("pump_room", "north", 0.5), ("nw_corner", "north", 0.5),
       ("ne_corner", "east", 0.5), ("se_corner", "south", 0.5),
       ("sw_corner", "west", 0.5)]
#: `station_foot` is deliberately unbracketed: its compact chamber is carved
#: by the full spiral shaft, so its remaining wall pieces are circulation
#: surfaces, not a stable place for a flame.

#: Every rectangle in this module, in plan units, so a bracket can find a
#: wall to hang on.
def _rects():
    out = {}
    for name, x0, y0, x1, y1 in RING:
        out[name] = (x0 * PU, y0 * PU, x1 * PU, y1 * PU)
    for name, x0, y0, x1, y1, *_rest in CHAMBERS:
        out[name] = (x0 * PU, y0 * PU, x1 * PU, y1 * PU)
    for name, x0, y0, x1, y1, *_rest in NECKS:
        out[name] = (x0 * PU, y0 * PU, x1 * PU, y1 * PU)
    return out


def populate(layout, rooms, attested, flame_fields,
             flame_stand: float = 0.33) -> list[str]:
    """Put the register, the finds and the braziers into the new network."""
    import props
    placed = []
    for name, type_id, local in POPULATION:
        spec = attested(type_id)
        if spec is None or name not in rooms:
            continue
        layout.place_on_floor(f"sewer:dude_{name}_{type_id}",
                              rooms[name].region_id, local=local,
                              **spec["fields"])
        placed.append(name)
    for index, (name, type_id, local) in enumerate(PICKUPS):
        spec = attested(type_id)
        if spec is None or name not in rooms:
            continue
        layout.place_on_floor(f"sewer:item_{index}", rooms[name].region_id,
                              local=local, **spec["fields"])
    for index, (name, face, t) in enumerate(LIT):
        if name not in rooms:
            continue
        props.mount_on_wall(layout, f"sewer:brazier_{index}",
                            rooms[name], face, t=t)
    # No aquatic dressing here.  `rules_blood.aquatic-sprite-is-under-water`
    # is graded off the corpus -- 664 appears in 82 campaign sectors and every
    # one is submerged, 660 in 142 likewise -- and it wants the sector's
    # XSECTOR `underwater` flag, not merely a shallow `depth`.  These channels
    # are ankle deep.  Weed and bubbles need a real underwater volume, which
    # this sewer does not have and which needs its own link pair to build.
    return placed


#: Which face of each ring segment the detail runs along, and which spans
#: on it are already spoken for.  A leg's necks and chamber mouths are the
#: occupied stretches: the run declines to build there rather than
#: colliding, which is `prefab.alcove_run`'s rule generalised.
#: Only faces that can be PROVEN solid carry a run.
#:
#: The ring's four long legs are missing from this table and that is a
#: recorded limitation, not an oversight: they are joined to their corners
#: and chambers by *face* connections, which carry no explicit span, so
#: neither `runs.occupied_from_layout` nor anything else can say which
#: stretches of a leg wall are free.  Guessing the spans from this module's
#: own tables got the count from twelve hanging sprites down to four and no
#: further, and tightening margins until the number reached zero would be
#: luck rather than knowledge.  Grammar request #11 asks for free-span
#: reporting on a face; until then the legs stay bare.
RUN_FACES = {
    "pump_room": ("north", ()),
    "east_annex": ("east", ()),
    "silt_trap": ("north", ()),
    "flooded": ("south", ()),
    "nw_corner": ("west", ()),
    "ne_corner": ("east", ()),
    "se_corner": ("south", ()),
    "sw_corner": ("west", ()),
    # The two long legs, 24 plan units each and until now completely bare.
    # They are the most repetitive stretch in the city, which is exactly
    # where a rhythm earns its keep.
    "e_leg": ("east", ()),
    "w_leg": ("west", ()),
    # The towpaths on the north and south sides.
    "n_walk": ("north", ()),
    "s_walk": ("south", ()),
}


#: The towpath: which leg carries one, and which side it hugs.  E3M3's
#: ledge is rise 4096 on tile 568 at depth 512, and the two long legs are
#: the only stretches in Gravesend's ring with room for one -- the north and
#: south sides already have their walk as a separate sector.
LEDGES = (("e_leg", "east"), ("w_leg", "west"))
LEDGE_CLEAR = 1024          # kept either side of a chamber mouth


def ledges(sewer, rooms, *, grade: int, host_clear: int) -> dict:
    """Lay E3M3's towpath along the legs, in the stretches that are free.

    The chambers that open off a leg are in this module's own table, so the
    free stretches are computable rather than hand-listed: a run stops short
    of a mouth and picks up again on the far side of it.
    """
    import props
    import sewerkit
    from materials import SEWER

    report = {"legs": 0, "runs": 0, "modules": 0}
    openings = {}
    for cname, cx0, cy0, cx1, cy1, _own, leg, leg_face, _note in CHAMBERS:
        openings.setdefault((leg, leg_face), []).append(
            (cy0 * PU, cy1 * PU) if leg_face in ("east", "west")
            else (cx0 * PU, cx1 * PU))

    for leg, side in LEDGES:
        room = rooms.get(leg)
        if room is None:
            continue
        report["legs"] += 1
        x0, y0, x1, y1 = (int(v) for v in props.room_rect(room))
        depth = 512
        # A towpath hugs its wall, but a carve whose edge lies exactly on the
        # host's outline gives the compiler two coincident same-direction
        # segments and it refuses -- the same rule `templates.shop` learned.
        # 256 units of channel between the ledge and the wall is what E3M3
        # leaves anyway.
        standoff = 256
        across0, across1 = ((x1 - standoff - depth, x1 - standoff)
                            if side == "east"
                            else (x0 + standoff, x0 + standoff + depth))
        taken = sorted(openings.get((leg, side), []))
        cursor, stretches = y0 + LEDGE_CLEAR, []
        for lo, hi in taken:
            if lo - LEDGE_CLEAR > cursor:
                stretches.append((cursor, int(lo - LEDGE_CLEAR)))
            cursor = max(cursor, int(hi + LEDGE_CLEAR))
        if y1 - LEDGE_CLEAR > cursor:
            stretches.append((cursor, y1 - LEDGE_CLEAR))
        for index, (start, end) in enumerate(stretches):
            if end - start < min(  # not even one module
                    __import__("fixtures").LEDGE.widths):
                continue
            node = sewerkit.ledge_along(
                room, f"{leg}_towpath_{index}", axis="y",
                start=start, end=end, across0=across0, across1=across1,
                material=SEWER, grade=grade, host_clear=host_clear,
                connector=None)
            report["runs"] += 1
            report["modules"] += len(node.children)
    return report


def detail_runs(layout, rooms) -> list:
    """One run per ring segment, its length taken from the geometry.

    The declaration is `RUN_FACES`; the emission is a rhythm of drips,
    trusses, railings and plaques along the tunnels.  That asymmetry --
    one line in, a lot out -- is the point of the layer.

    Occupied spans are computed from this module's OWN tables rather than
    from the layout.  The ring is joined with *face* connections, which
    carry no explicit span, so `runs.occupied_from_layout` cannot see them;
    and `props.solid_faces` correctly reports that every leg has a chamber
    on all four of its faces, which would reject every leg outright.  What
    is true is that each chamber covers a short stretch of one face, and
    CHAMBERS says exactly which.
    """
    import props
    import runs as run_layer
    import sewerkit

    attached = {}
    for cname, cx0, cy0, cx1, cy1, own, leg, leg_face, _note in CHAMBERS:
        attached.setdefault(leg, []).append(
            (leg_face, cx0 * PU, cy0 * PU, cx1 * PU, cy1 * PU))
    for nname, nx0, ny0, nx1, ny1, joins, _note in NECKS:
        for _own, other, other_face in joins:
            attached.setdefault(other, []).append(
                (other_face, nx0 * PU, ny0 * PU, nx1 * PU, ny1 * PU))

    out = []
    for name, (face, extra) in RUN_FACES.items():
        room = rooms.get(name)
        if room is None:
            continue
        x0, y0, x1, y1 = props.room_rect(room)
        horizontal = face in ("north", "south")
        lo, hi = (x0, x1) if horizontal else (y0, y1)
        span = max(1, hi - lo)
        length = span / run_layer.PLAN
        if length < 1.0:
            continue
        # RING is stated in city plan units.  Reconcile its local rectangle
        # with the compiled world rectangle before computing fractions; this
        # also keeps the helper valid if a later district supplies a frame.
        # NOT `props.solid_faces`, which is all-or-nothing: it writes off a
        # face that carries any portal at all, and the east leg's face is
        # 24,576 units long with a 6,144-unit annex mouth in it.  A run
        # already models partial occupancy, and `occupied_from_layout` reads
        # the spans the connections actually take, so the free stretches of
        # a face with a door in it stay usable.  That gate alone was why the
        # two 24-plan-unit legs -- the most repetitive stretch in the city --
        # carried no detail at all.
        from_layout = run_layer.occupied_from_layout(layout, room, face)
        if any(lo <= 0.0 and hi >= 1.0 for lo, hi in from_layout):
            continue                    # the whole face is an opening
        local = next((r for r in RING if r[0] == name), None)
        offset = 0 if local is None else (
            (x0 - local[1] * PU) if horizontal else (y0 - local[2] * PU))
        occupied = list(extra) + list(from_layout)
        for aface, ax0, ay0, ax1, ay1 in attached.get(name, ()):
            if aface != face:
                continue
            a_lo, a_hi = (ax0, ax1) if horizontal else (ay0, ay1)
            t0 = (a_lo + offset - lo) / span
            t1 = (a_hi + offset - lo) / span
            occupied.append((min(t0, t1) - 0.12, max(t0, t1) + 0.12))
        out.append(run_layer.Run(
            name=f"sewer_{name}", room=room, face=face,
            length_plan=length, occupied=tuple(occupied),
            elements=sewerkit.TUNNEL))
    return out
