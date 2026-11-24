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
from bloodmap.spiral import INNER_RADIUS

from materials import SEWER, SEWER_WET, Material
from resolution import (PU, SEWER_CHAMBER_CLEAR, SEWER_CLEAR, SEWER_FLOOR,
                        STATION_STACK_PLANE)

COMPASS = dict(zip(RECT_FACES, range(4)))

#: The walk sits one max step above its channel (E3M3's median step).
LEDGE_STEP = 4096
#: Legs that carry water, not only the channels split off the long sides:
#: the east leg is a channel with its towpath beside it, so the water that
#: falls in at the east manhole has somewhere to go.
WET_LEGS = frozenset({"e_leg", "w_leg", "sw_corner", "se_corner"})
#: Which way the water runs, and how fast. The owner, 2026-11-21: "add water
#: path from where you fall into with moving water towards the main shafts,
#: and we can even make the water to flow certain meaningful way in a
#: sewers". The ring drains one way round, toward its south-west corner,
#: where the settling hall's inflow will be (`references/sewer-design.md`):
#: along the north channel east, down the east leg south, along the south
#: channel west. A Build angle (0 east, 512 south, 1024 west, 1536 north),
#: the floor's pan velocity (E3M3's ledge channels pan at 8, its fast race at
#: 32), and whether the current carries a body (E1M8's River Ride: drag on).
FLOW = {
    "n_channel": (0, 8, False),
    "e_leg": (512, 8, False),
    "s_channel": (1024, 8, False),
    "w_leg": (512, 8, False),
    "nw_corner": (512, 8, False),
    "ne_corner": (512, 8, False),
    "sw_corner": (512, 8, False),
    "se_corner": (1024, 8, False),
    # the brook runs east into the ring; the south-east branch west and
    # north into the ring's south-east corner
    "graves_brook": (0, 8, False),
    "se_spur": (1024, 8, False),
    "se_drain": (1536, 8, False),
    # south, to the fall into the sampling chamber (the owner, 2026-11-23:
    # "the rest of the water is going the other direction than the waterfall
    # would suggest"); it ran north into the ring before the chamber sank
    "stockyard_drain": (512, 60, True),
    # the sampling chamber, from the fall and the pipe to its east culverts
    "sampling": (0, 24, False),
    # out of the ring under the plaza: the outfall south, the basin west
    # toward the river
    "outfall": (512, 24, False),
    "gallery": (1024, 8, False),
    # the tanks barely move: that is what settling is
    "tank_1": (1024, 2, False), "tank_2": (1024, 2, False), "tank_3": (1024, 2, False),
}
#: The branches off the ring, each under a street (the owner agreed the
#: layout on 2026-11-21: "Looks reasonable"; `references/sewer-design.md`):
#: the outfall south from the south-west corner into the settling basin
#: under the plaza by the memorial; GRAVES BROOK, the old culvert, west
#: under the row street past the church to the city's west edge (the owner:
#: "We can also extend sewers towards west part of the city"); and the
#: south-east branch under the market road. (name, x0, y0, x1, y1 in plan
#: units, the room it opens from, that room's face, its own face, part, note)
BRANCHES = [
    ("outfall", 32.0, 34.0, 34.0, 41.0, "sw_corner", "south", "north", "ring",
     "the outfall: the ring's water running south under the plaza"),
    ("gallery", 20.0, 41.0, 35.0, 43.0, None, None, None, "ring",
     "the settling hall's gallery: the outfall's water running west along "
     "the hall's north wall, over the tanks"),
    # south of the pump room, which reaches y 18 at this depth
    ("graves_brook", 1.0, 18.5, 32.0, 20.5, "w_leg", "west", "east", "ring",
     "Graves Brook: the stream the town is named for, culverted in rubble "
     "under the row street, running east into the ring past the church"),
    ("se_drain", 51.0, 34.0, 53.0, 36.5, "se_corner", "south", "north", "ring",
     "the south-east drain, north into the ring's corner"),
    ("se_spur", 53.0, 34.5, 56.0, 36.5, "se_drain", "east", "west", "ring",
     "the south-east spur under the market road's north pavement, to its manhole"),
    ("stockyard_drain", 48.75, 34.0, 50.75, 55.75, "s_channel", "south", "north", "ring",
     "the slaughterhouse race: the ring's overflow running south past the carcass rack to the fall"),
]
SOUTH = BRANCHES
#: Graves Brook is older than the ring and looks it: the crypt's rubble
#: walls (110, E1M1's crypt) and its dark worked stone overhead (253).
STOCKYARD_WET = Material(wall=296, floor=1120, ceiling=1030, opening=296,
                         note="the stockyard race: grimy tile over a blood current")
BRANCH_MATERIAL = {
    "graves_brook": Material(wall=110, floor=1120, ceiling=253, opening=110,
                             note="Graves Brook: rubble culvert, older than the ring"),
    "stockyard_drain": STOCKYARD_WET,
}
#: A manhole's landing and its passage run fast toward the ring and carry
#: whoever fell in onto it.
LANDING_FLOW = (24, True)


def flow_behavior(angle: int, velocity: int, drag: bool) -> dict:
    """The XSECTOR fields of a floor that runs one way: Blood's own panning current."""
    out = {"pan_floor": 1, "pan_always": 1, "pan_velocity": int(velocity),
           "pan_angle": int(angle) & 2047}
    if drag:
        out["drag"] = 1
    return out
#: E3M3's shallow-water form, the one that reads wet in our own frames.
WATER_DEPTH = 7

# The lower counterpart of the pumping-station stair is a corridor, not a
# chamber with a C-shaped hole.  The ten 22.5-degree treads leave at 270
# degrees: their final radial edge runs from (45,568, 4,120) to
# (45,568, 4,872), and the corridor continues east, perpendicular to it, to
# the silt trap.  This is deliberately the long side of a tread, just as the
# E3M1 end sectors are.
SPIRAL_AXIS = (45568, 5120)
SPIRAL_RADIUS = 1000
SPIRAL_FOOT_X0 = SPIRAL_AXIS[0] / PU
SPIRAL_FOOT_Y0 = (SPIRAL_AXIS[1] - SPIRAL_RADIUS) / PU
SPIRAL_FOOT_X1 = (SPIRAL_AXIS[0] + 1024) / PU
SPIRAL_FOOT_Y1 = (SPIRAL_AXIS[1] - INNER_RADIUS) / PU

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
    ("station_foot", SPIRAL_FOOT_X0, SPIRAL_FOOT_Y0,
     SPIRAL_FOOT_X1, SPIRAL_FOOT_Y1,
     "east", "silt_trap", "west",
     "the foot of the pumping-station spiral: a tread-width landing that "
     "opens directly into the silt-trap approach"),
]

#: Manholes: a drain cover lying in a street over a shaft into the sewer,
#: which a blast destroys and the player drops through. The owner,
#: 2026-11-21: "a floor aligned sprite over hole as a cover that is
#: destructible by explosion, not wall crack. Like a normal manhole on the
#: street you can drop into". The campaign builds exactly that once: E4M3
#: sprite 130, a flat type 417 (tile 191, cstat 417, repeat 48) lying 3072
#: above a see-through link floor, and a fall of 3.9 bodies below; community
#: maps do it in the street (SLUMS2C sprite 62, BCE3M5 sprite 141 on tile
#: 219). (name, x0, y0 of the shaft in plan units, side in units, the ring
#: room its landing opens off, that room's face, note)
#: The owner, 2026-11-21: "You are always putting these sewers enterances
#: so close to each other ... keep the pump station one and these manholes
#: should be on the far sides of sewers", and "There can be for example
#: manhole near memorial and church". So the ways in are the pump station's
#: spiral (north) and three manholes, east, west and south: (name, x0, y0
#: of the shaft in plan units, side in units, the street's district, how it
#: lands -- "beside" a ring room through a channel, or "inside" one -- that
#: room, its face, note).
MANHOLES = [
    # a pavement's width out from the works' east wall (the street's hole 0,
    # on x = 53; the owner: "It doesn't have to be that much close to the
    # building"), so its landing runs 1.5 units of channel to the leg
    # one way in per quarter of the city, at the far ends of the branches
    # (the east and church manholes are gone: too near the others)
    ("west_manhole", 1.5, 19.125, 768, "old_crossing", "inside", "graves_brook", None,
     "a drain cover at the west end of the row street, over Graves Brook"),
    # on the pavement at the corner where the market road meets the east
    # street: the road itself is sunk 2048 and a cover laid at the street's
    # level would float over it
    ("se_manhole", 53.75, 35.125, 768, "foundry_ward", "inside", "se_spur", None,
     "a drain cover on the corner where the market road meets the east street"),
    # in the plaza east of the memorial, over the settling hall's gallery:
    # its water, not the tanks 2.7 bodies further down (a fall that far hurts)
    ("memorial_manhole", 31.0, 41.625, 768, "market_slip", "inside", "gallery", None,
     "a drain cover in the plaza beside the memorial, over the settling hall's gallery"),
    ("stockyard_manhole", 49.375, 51.0, 768, "market_slip", "inside", "stockyard_drain", None,
     "a drain cover on the east quay's landward pavement, just below the stockyard intake"),
]
#: The cover: the owner's tile 219 ("drain", round), laid flat and blocking
#: at street level, wider than the shaft is across its corners (768 square,
#: 1086 corner to corner; 64 texels x 72 / 4 = 1152) so no edge of the hole
#: shows. The record is E4M3 sprite 130's (type 417, `data_1` 5 metal
#: debris, `data_4` 314 the grate's break sound) on our tile and size. Type
#: 417 takes damage from explosions and tesla and none from bullets, kicks,
#: falls or fire (NBlood `thingInfo`); blast damage ignores the hitscan bit,
#: so this cover opens only to a blast. (The owner would take one that
#: anything breaks: type 416.)
#: The cover breaks into metal shards, as E4M9's floor-lying vent grate does
#: (sprite 290: data_1 5 = gib type 4, gib.cpp gibList), but only to an
#: explosion: type 417, whose thingInfo takes damage from explosions (256)
#: and tesla (128) and nothing else, where a 416 also takes bullets and falls
#: (actor.cpp, "Gib Object" and "Explode Object"). The owner, 2026-11-23:
#: "Manhole covers are breakable now, I would try to make them explosion
#: breakable only if it will work".
MANHOLE_COVER = {"source": ("E4M9", 416, 218), "type": 417, "picnum": 219,
                 "cstat": 1 | 32 | 128 | 256, "repeat": 72}
#: The shaft drops this far below the street to its link plane, so the cover
#: lies ABOVE its sector's floor, as a flat sprite must to hold a player up
#: (E4M3 and E1M4 lay theirs 3072 above).
MANHOLE_RECESS = 4096


#: Necks joining the ring to the network that already existed.
NECKS = [
    ("west_adit", 34.0, 11.0, 39.25, 13.0,
     [("west", "w_leg", "east"), ("east", "junction", "west")],
     "the west adit: the ring's way into the junction"),
    ("neck_cistern", 44.0, 31.0, 46.0, 32.0,
     [("north", "cistern", "south"), ("south", "s_channel", "north")],
     "the cistern's overflow into the ring"),
]


#: E3M3's sewer corridor, measured across its width (E3M3 sectors 136 | 120 |
#: 117 and 135 | 129 | 144; `work/sewer-study/e3m3_section.py`): 2048 wide, a
#: WALK of 512 each side of a CHANNEL of 1024 that runs 2048 lower; the walks'
#: ceilings slope down to the wall (heinum 4096 over 512: a fall of 8192) and
#: the channel's is flat, 28,672 over the walks -- the vault. The owner,
#: 2026-11-21: "I would like to do sewers more like in E3M3, there is that
#: flowing water in the middle and sewers has that sloped ceiling".
WALK = 512
CHANNEL_DROP = 2048
WALK_CLEAR = 28672
VAULT = 8192

#: Cutouts in the walks' outer walls, each with something in it. The owner,
#: 2026-11-21: "I think we add some decorative elements and cutouts with
#: something to make it more interesting". (the corridor, the side whose
#: outer wall it is cut into, where along the corridor in plan units, what
#: it holds). A niche that would overlap anything else at the sewer's depth
#: is skipped and reported.
NICHES = [
    ("n_channel", "low", 37.0, "valve"), ("n_channel", "low", 41.0, "barrels"),
    ("e_leg", "high", 10.5, "pipes"), ("e_leg", "high", 25.5, "bones"),
    ("s_channel", "high", 36.0, "pipes"), ("s_channel", "high", 48.0, "valve"),
    ("w_leg", "low", 10.0, "barrels"), ("w_leg", "low", 23.0, "bones"),
    ("graves_brook", "low", 8.0, "bones"), ("graves_brook", "high", 12.0, "barrels"),
    ("graves_brook", "low", 15.0, "pipes"), ("graves_brook", "high", 20.0, "bones"),
]
#: A niche is a plan unit along and half a unit deep, a step up from the walk
#: (2048: what stands in it stands on a shelf, as the town maps keep their
#: goods -- `tools.mine_stands` reads it as a niche), its ceiling under the
#: vault's low edge so a lintel shows.
NICHE_LONG, NICHE_DEEP, NICHE_CLEAR, NICHE_RISE = 1.0, 0.5, 16384, 2048
#: A bones niche is tall inside, up to the sewer's band (a deep alcove behind
#: the low mouth), so a skeleton on its chain hangs in it whole: E1M2's 689 is
#: two bodies of chain and bones at its campaign size, and a sprite may not
#: stand above its sector's ceiling.
NICHE_CLEAR_OF = {"bones": 30720}
#: What each kind wears on its walls: the owner's "technical wall with
#: pipes, valve box" (499); E3M3's field wall (492); twin pipes (211).
NICHE_WALL = {"valve": 499, "bones": 492, "barrels": 492, "pipes": 211}


def _niches():
    """The niches that fit: (name, rect in plan units, the corridor, its side, kind)."""
    corridors = {c[0]: c for c in _corridors()}
    taken = ([e["rect"] for e in plan_rooms()] + [(x0, y0, x1, y1) for _n, x0, y0, x1, y1, _k in HALL]
             + [tuple(r[1:5]) for r in SECRET_ROOMS] + list(lair_rects().values()))
    out = []
    for k, (channel, side, at, kind) in enumerate(NICHES):
        _c, (x0, y0, x1, y1), axis, _walks, _part, _l, _h = corridors[channel]
        half = NICHE_LONG / 2
        if axis == "x":
            rect = ((at - half, y0 - NICHE_DEEP, at + half, y0) if side == "low"
                    else (at - half, y1, at + half, y1 + NICHE_DEEP))
        else:
            rect = ((x0 - NICHE_DEEP, at - half, x0, at + half) if side == "low"
                    else (x1, at - half, x1 + NICHE_DEEP, at + half))

        def overlaps(r):
            return min(rect[2], r[2]) > max(rect[0], r[0]) and min(rect[3], r[3]) > max(rect[1], r[1])

        if any(overlaps(r) for r in taken):
            continue
        taken.append(rect)
        out.append((f"niche_{k}_{kind}", rect, channel, side, kind))
    return out


#: The ring's corners: where the channels meet, a pool at the water's level.
CORNERS = [
    ("nw_corner", 32.0, 6.0, 34.0, 8.0),
    ("ne_corner", 51.0, 6.0, 53.0, 8.0),
    ("se_corner", 51.0, 32.0, 53.0, 34.0),
    ("sw_corner", 32.0, 32.0, 34.0, 34.0),
]
#: The ring's sides, each an E3M3 corridor: (its channel, x0, y0, x1, y1 in
#: plan units, the axis it runs along, its walks (the low side's, the high
#: side's), what its low end opens onto, what its high end opens onto).
SIDES = [
    ("n_channel", 34.0, 6.0, 51.0, 8.0, "x", ("n_walk", "n_walk_in"),
     ("nw_corner", "east"), ("ne_corner", "west")),
    ("e_leg", 51.0, 8.0, 53.0, 32.0, "y", ("e_leg_walk_w", "e_leg_walk_e"),
     ("ne_corner", "south"), ("se_corner", "north")),
    ("s_channel", 34.0, 32.0, 51.0, 34.0, "x", ("s_walk_in", "s_walk"),
     ("sw_corner", "east"), ("se_corner", "west")),
    ("w_leg", 32.0, 8.0, 34.0, 32.0, "y", ("w_leg_walk_w", "w_leg_walk_e"),
     ("nw_corner", "south"), ("sw_corner", "north")),
]
RING = CORNERS
#: Branches that are rooms, not corridors.
BRANCH_ROOMS = frozenset()
#: THE SECRET ROOMS (`references/sewer-design.md`, its legends). Off Graves
#: Brook, which runs under the old quarter and the churchyard:
#:
#: * OLD MOLLY'S NEST -- the toshers' tale of a woman who lived in the brook
#:   and took what the water brought. A crawl-height arch in the brook's
#:   south wall (crouching clears 13,376) into a low lair of bones; she is a
#:   gill beast now.
#: * THE PLAGUE PIT -- where the parish put its plague dead when the
#:   churchyard was full, and bricked them in. A cracked stretch of the
#:   brook's wall beside the churchyard; a blast opens it, the way the
#:   church's crypt breach does (E1M2's and E3M4's blown walls), onto a vault
#:   half a step down. The hole is ragged (`bloodmap.breach`): three pieces
#:   with slanted seams, each with its own tilted sill and top.
#:
#: Both count as secrets. (name, x0, y0, x1, y1 in plan units, floor below
#: the walk, clear height, what it is, the room it opens from and that
#: room's face, where along it)
SECRET_ROOMS = [
    ("molly_crawl", 4.5, 20.5, 5.5, 21.5, 0, 14336, "crawl",
     ("graves_brook", "south", 5.0), "the crawl into Old Molly's nest"),
    ("molly_nest", 3.0, 21.5, 7.0, 24.5, 0, 20480, "lair",
     ("molly_crawl", "south", None), "Old Molly's nest: a low lair of bones off Graves Brook"),
    ("plague_pit", 22.5, 21.0, 27.5, 25.0, 2048, 30720, "vault",
     None, "the plague pit under the churchyard: a secret"),
    ("plague_seal", 24.375, 20.5, 25.875, 21.0, 0, 0, "seal",
     ("graves_brook", "south", 25.125), "the bricked-up wall of the plague pit: blown open, once"),
]
#: The blown hole (`bloodmap.breach.ragged`): its sills 256-1,536 over the
#: walk, so the pit's floor (2,048 under the walk) is a step from any of
#: them; and its ragged top under the brook walk's vault where that meets
#: the wall (20,480 over the walk), or the vault's straight edge is all that
#: shows of it.
SEAL_SILL = (256, 1536)
SEAL_TOP = WALK_CLEAR - VAULT - 512
SECRET_MATERIAL = {
    "crawl": Material(wall=110, floor=1120, ceiling=253, opening=110, note="the crawl: the brook's rubble"),
    "lair": Material(wall=110, floor=1120, ceiling=253, opening=110, note="Molly's nest: the brook's rubble"),
    # the broken faces of the hole are the wall's own stone, top and bottom
    "seal": Material(wall=110, floor=110, ceiling=110, opening=110, note="the seal: the brook's own wall"),
    # the crypt's stone and earth (`l3_church.CRYPT_WALL`, `CRYPT_EARTH`)
    "vault": Material(wall=110, floor=270, ceiling=253, opening=110, note="the plague pit: earth and stone"),
}

#: THE WEAVER'S CELLARS (`knowledge/blood/studies/spider-lair`): the cellars
#: of the old tannery under the saloon row, which the spiders took. The
#: owner, 2026-11-22: "We can also add spider lair somewhere, similar to
#: E2M8". A passage climbs from Graves Brook's north walk, a web across its
#: mouth (E2M8's 410 on 1069: shoot it through), into a cellar hall of
#: cobblestone (411) and earth (270) with its corners knocked off, four
#: brood alcoves walled in silk (1057) with a cocoon each, wrapped victims
#: and web hanging from the ceiling, and spiders on it, upside down, their
#: mother among them (E2M8:52 and CHORROR:414's lair, transcribed).
LAIR_LAYER_PART = "lair"
#: the hall, in plan units, wound like a `rect_room`: its south edge is the
#: passage's, its west, north and east the alcoves'
LAIR_HALL = [(10.0, 17.0), (8.5, 15.5), (8.5, 12.5), (10.0, 11.0), (14.0, 11.0),
             (16.0, 12.5), (16.0, 15.5), (13.5, 17.0)]
LAIR_HALL_FACES = {"southwest": 0, "west": 1, "northwest": 2, "north": 3,
                   "northeast": 4, "east": 5, "southeast": 6, "south": 7}
#: the hall's height: E2M8:52's (1.9 bodies), all the sewer's layer allows
LAIR_CLEAR = 32768
#: (name, x0, y0, x1, y1 in plan units, the hall's face it opens off)
#: E2M8:52's are 1,024 deep and up to 3,072 wide, sized to its cocoon: an egg
#: 1.6 bodies tall and 1,152 wide at the campaign's repeat. The north one is
#: THE NEST (round 1's comparison reader: "one deep nest recess holding a
#: cluster of several cocoons ... instead of single eggs in shallow, clean,
#: boxed niches"): deep and lower, its eggs clustered and of three sizes,
#: Blood's carved spider panel over its mouth (E1M5 sprite 421).
#: (name, x0, y0, x1, y1, the hall's face, its rise, its clear height, its
#: cocoons as (share across, share deep, repeat))
#: Round 2's readers: the side alcoves' single eggs on flat silk "read as
#: painted shapes" and "ghosts"; so every alcove is a nest now, deep and
#: low, its eggs clustered and of several sizes, webs hung from its lintel.
LAIR_ALCOVES = [
    ("brood_west", 7.0, 13.0, 8.5, 15.0, "west", 512, 22528,
     [(0.35, 0.55, 46), (0.6, 0.35, 30), (0.72, 0.72, 38)]),
    ("brood_nest", 10.75, 9.0, 13.25, 11.0, "north", 512, 22528,
     [(0.3, 0.45, 40), (0.55, 0.3, 46), (0.75, 0.55, 30), (0.45, 0.75, 24)]),
    ("brood_east", 16.0, 13.0, 17.5, 15.0, "east", 512, 22528,
     [(0.55, 0.3, 44), (0.78, 0.62, 28)]),
]
#: a rough stone pillar in the hall's middle, hung with silk: round 1's
#: comparison reader, "solid stone masses that block the view ... so the
#: room cannot be seen at once"; its use reader could not tell one view of
#: the hall from another. (plan units, wound as a hole is)
LAIR_PILLAR = [(11.95, 13.6), (12.55, 13.6), (12.75, 13.8), (12.75, 14.4), (12.55, 14.6),
               (11.95, 14.6), (11.75, 14.4), (11.75, 13.8)]
#: the passage up from the brook: (x0, y0, x1, y1), its clear height, under
#: the walk's vault at the wall so a lintel shows
LAIR_PASSAGE = (11.25, 17.0, 12.25, 18.5)
LAIR_PASSAGE_CLEAR = 18432
LAIR_MATERIAL = {
    "hall": Material(wall=411, floor=270, ceiling=253, opening=110, note="the cellar: cobblestone and earth"),
    # the hall's rough stone and earth: in silk (1057) the nests read, to
    # round 6's readers, as "flat grey boxes", "museum vitrines"; the
    # eggs, the lintel webs and the strands inside say what they are
    "alcove": Material(wall=411, floor=270, ceiling=253, opening=411, note="a nest: rough stone, earth, eggs"),
    # the hall's own stone (round 3: "the tunnel's brick does not match")
    "passage": Material(wall=411, floor=270, ceiling=253, opening=110, note="the passage: the cellar's stone"),
}


def lair_rects() -> dict:
    """Every room of the lair, as its bounding rectangle in plan units."""
    xs, ys = [p[0] for p in LAIR_HALL], [p[1] for p in LAIR_HALL]
    out = {"lair_hall": (min(xs), min(ys), max(xs), max(ys)), "lair_passage": LAIR_PASSAGE}
    out.update({name: (x0, y0, x1, y1) for name, x0, y0, x1, y1, *_r in LAIR_ALCOVES})
    return out


#: A corridor's other end, where it meets the side of another corridor: (the
#: corridor, which end, the corridor it enters, that one's face).
THROUGH = [("outfall", "end", "gallery", "north")]

#: THE SETTLING HALL (`references/sewer-design.md`): under the plaza beside
#: the memorial, where the ring's water settles before the river. Blood's
#: big wastewater halls get their size from tiers (E3M3:15, a pool under walks
#: and catwalks; E1M8:243, walks over a sea of sewage), so it is deeper than
#: the sewer, its own layer: the gallery at the sewer's level along its north
#: wall, three settling tanks 2.7 bodies below it with walks between, a quay
#: down the west side, and the south quay where the Cabal keeps its circle.
#: A stair of ten steps climbs from the south quay to the gallery in a
#: column of its own. (name, x0, y0, x1, y1 in plan units, kind)
HALL_LAYER = "settling_hall"
HALL_WATER = SEWER_FLOOR + 45056          # the tanks' surface: 106,496
HALL_WALK = HALL_WATER - 4096             # the walks and quays: one step up
HALL = [
    ("west_quay", 20.0, 43.0, 21.0, 48.0, "walk"),
    ("tank_1", 21.0, 43.0, 32.5, 44.25, "tank"),
    ("divider_1", 21.0, 44.25, 32.5, 45.0, "walk"),
    ("tank_2", 21.0, 45.0, 32.5, 46.25, "tank"),
    ("divider_2", 21.0, 46.25, 32.5, 47.0, "walk"),
    ("tank_3", 21.0, 47.0, 32.5, 48.0, "tank"),
    ("circle_quay", 20.0, 48.0, 35.0, 50.0, "walk"),
]
#: (a, its face, b, its face): each anchored from the smaller face
HALL_JOINS = [
    ("tank_1", "south", "divider_1", "north"), ("divider_1", "south", "tank_2", "north"),
    ("tank_2", "south", "divider_2", "north"), ("divider_2", "south", "tank_3", "north"),
    ("tank_1", "west", "west_quay", "east"), ("divider_1", "west", "west_quay", "east"),
    ("tank_2", "west", "west_quay", "east"), ("divider_2", "west", "west_quay", "east"),
    ("tank_3", "west", "west_quay", "east"),
    ("tank_3", "south", "circle_quay", "north"), ("west_quay", "south", "circle_quay", "north"),
]
#: The stair: down from the gallery's south walk at x 33.5, a column 1024
#: wide clear of the tanks (which end at 32.5), onto the circle quay.
HALL_STAIR = {"at_x": 33.5, "width": 1024, "tread": 512, "step_rise": 4096}
#: The last metre of the tank's north edge, just west of the ring's outfall.
HALL_OUTFALL = (31.5, 32.5)

# The shaft is west of the dry quay and gallery walk. Its two east openings
# are offset along the shaft, with solid wall between them. The upper lobby
# turns at a raised sill before opening onto the shaft.
HALL_LIFT_SHAFT = (17.5, 41.25, 19.0, 45.0)
HALL_LIFT_UPPER_JAMB = 19.1875
HALL_LIFT_UPPER_MOUTH = (41.75, 42.5)
HALL_LIFT_UPPER = [
    (HALL_LIFT_UPPER_JAMB, 41.5), (19.75, 41.5), (19.75, 42.5), (20, 42.5),
    (20, 43), (19.75, 43), (19.75, 43.25), (HALL_LIFT_UPPER_JAMB, 43.25),
    (HALL_LIFT_UPPER_JAMB, HALL_LIFT_UPPER_MOUTH[1]), (19, HALL_LIFT_UPPER_MOUTH[1]),
    (19, HALL_LIFT_UPPER_MOUTH[0]), (HALL_LIFT_UPPER_JAMB, HALL_LIFT_UPPER_MOUTH[0]),
]
HALL_LIFT_LOWER = (19.0, 43.5, 20.0, 44.75)
HALL_LIFT_WIRE = "sewer:settling-hall-lift"
TROLLEY_WIRE = "sewer:stockyard-trolley"
TROLLEY_LAYER = "stockyard_sampling"
#: The owner, after playing it: "that whole room has too low ceiling. Rails
#: it moves through are really short", and: "If there is no room to raise
#: ceiling you can probably just put it lower and connect it with stairs".
#: The harbour's sea layer reaches down to 41,984 over its west half, so the
#: roof stays a slab under that (43,008) and the chamber SINKS two full steps
#: (4,096 each, the most a body climbs: the Settling Hall's stair) down from
#: the drain's west walk, the blood pouring over the drop into the inlet:
#: 26,624 clear, 1.57 bodies, where it was 18,432.
TROLLEY_CEILING = 41984 + 1024
TROLLEY_STEP = 4096
TROLLEY_SINK = 2 * TROLLEY_STEP
TROLLEY_FLOOR = SEWER_FLOOR + TROLLEY_SINK

#: Graves Brook's walks: E3M3's stone walk (568) between rubble walls. (Not
#: the crypt's earth, 270: at the crypt's own depth that is what makes the
#: crypt the crypt.)
BRANCH_DRY = {
    "graves_brook": Material(wall=110, floor=568, ceiling=253, opening=110,
                             note="Graves Brook's walks: stone between rubble walls"),
    "stockyard_drain": Material(wall=296, floor=291, ceiling=1030, opening=296,
                                note="the stockyard's blood-stained tiled walks"),
}

# E1M8's pipe and River Ride, and the candle shelves in E1M5's chapel.
STOCKYARD_RACK = Material(wall=296, floor=291, ceiling=255, opening=296,
                          note="the tiled carcass rack beside the intake")
SHRINE_PIPE = Material(wall=194, floor=438, ceiling=194, opening=194,
                       note="the old pipe mouth off the tiled walk")
SHRINE_STONE = Material(wall=406, floor=253, ceiling=286, opening=405,
                        note="the shrine's worked stone and temple trim")
# Rectangles in plan units. Floors rise in two steps to the offering.
STOCKYARD_ROOMS = [
    ("stockyard_rack", (47.25, 51.75, 48.75, 54.25), STOCKYARD_RACK, 0, WALK_CLEAR, "interior"),
    ("rat_king_pipe", (50.75, 46.375, 52.0, 47.125), SHRINE_PIPE, 0, 18432, "gateway"),
    ("rat_king_shrine", (52.0, 45.0, 55.25, 48.75), SHRINE_STONE, 0, SEWER_CHAMBER_CLEAR, "secret"),
    ("rat_king_step", (55.25, 45.625, 55.625, 48.125), SHRINE_STONE, 3072, SEWER_CHAMBER_CLEAR, "interior"),
    ("rat_king_altar", (55.625, 45.625, 56.75, 48.125), SHRINE_STONE, 6144, SEWER_CHAMBER_CLEAR, "interior"),
]

# The terminal chamber is wider than the race. The west walk continues
# along it to the tail, and the opposing berth is the inspection alcove.
STOCKYARD_TROLLEY_ROOMS = (
    ("trolley_inlet", (49.25, 55.75, 60.125, 57.25), "blood at the end of the race"),
    ("trolley_track", (52.125, 57.25, 60.125, 59.25), "straight rail at the waterline"),
    ("trolley_tail", (52.125, 59.25, 60.125, 61.0), "blood below the slaughterhouse pipe"),
    ("trolley_step", (47.5, 55.75, 49.25, 57.25), "a step down from the drain's walk, beside the inlet"),
    ("trolley_walk", (47.5, 57.25, 49.25, 61.0), "the continuous dry maintenance walk"),
    ("trolley_ledge", (49.25, 57.25, 52.125, 61.0), "dry west boarding ledge"),
    ("trolley_alcove", (60.125, 57.25, 62.125, 59.25), "dry sampling and inspection alcove"),
)
#: Where the chamber's water goes: a low barred culvert at the east end of
#: each pool, out under the river. (name, rect, the pool it drains)
SAMPLING_CULVERTS = (
    ("trolley_culvert_north", (60.125, 55.875, 60.875, 57.125), "trolley_inlet"),
    ("trolley_culvert_south", (60.125, 59.375, 60.875, 60.875), "trolley_tail"),
)
CULVERT_CLEAR, CULVERT_MOUTH = 8192, 128
#: the owner's "sewer grate" (502) as E4M6 hangs it on a two-sided wall (3275:
#: masked, blocking, bottom-aligned, hitscan)
CULVERT_GRATE = {"over_picnum": 502, "cstat": 1 | 4 | 16 | 64}
#: Blood enters the race at the carcass rack (its mouth is y 51.75 to 54.25);
#: upstream of it the water is the ring's own.
RACE_BLOOD_FROM = 52.0

#: A channel's water falling down a drop into a lower room. The owner,
#: 2026-11-22: "you will have stairs down and waterfall between them ...
#: some sort of technical junction ... can add more depth". The falling
#: tile and its downward pan go on the LOWER room's own wall, the face seen
#: from below, as the campaign's falls do (E2M7 wall 482 and E4M3 wall 59:
#: tile 1005, pan_always, y velocity -80 / -120). The first version painted
#: the upper wall and showed it below by bottom swap, as E3M3 does under a
#: lintel; but that wall's tile is also the band above the opening, and the
#: lintel pass repainted it the drain's tile 296: the owner, "the waterfall
#: has no muddy water texture on the front, without it looks cutoff". The
#: tile stays E3M3's muddy 1120 (E1M8 wall 1309 pans it down too, at -85).
#: (the falling wall's map and index; the sound's map, sprite and sector)
#: E1M8's 1120 fall pans at -85 -- E3M3's at -20 read as standing still
POUR_SOURCE = ("E1M8", 1309, "E3M3", 393, 174)


def _waterfall(upper, face: str, lower, wall, *, pal: int = 0, bottom_swap: bool = False):
    from bloodmap.model import record_extra, record_fields

    finish = {key: record_fields(wall)[key] for key in
              ("picnum", "type", "x_repeat", "y_repeat", "x_panning", "y_panning")}
    if pal:
        finish["pal"] = int(pal)
    pan = {key: record_extra(wall)[key] for key in
           ("pan_always", "pan_x_velocity", "pan_y_velocity", "x_pan_fraction", "y_pan_fraction")}

    def spill(layout, room):
        a, b = (upper.world_frame().apply(p) for p in upper.local_edge(face))
        wet_side = upper if bottom_swap else lower
        layout.paint_wall(wet_side.region_id, a, b, fixed_frame=True, **finish)
        layout.wire_wall(wet_side.region_id, a, b, **pan)
        if bottom_swap:
            # The lower sector has a lintel as well as a drop on this edge.
            # The lower band borrows the water-facing record from the feeder.
            layout.paint_wall(lower.region_id, a, b, cstat=2, fixed_frame=True)

    upper.raw("falling water on the receiving wall", spill)


def _foam_at_foot(upper, face: str, lower, name: str):
    """E3M6's animated waterline across the foot of a drop."""
    from bloodmap.placement import build_angle, inward_normal

    def foam(layout, room):
        a, b = (upper.world_frame().apply(p) for p in upper.local_edge(face))
        nx, ny = inward_normal(*b, *a)
        # E3M6 sprite 157: 1037's centred ART offset puts its visible foot at z.
        layout.add_sprite(f"sewer:{name}_foam", room.region_id, picnum=1037,
                          x=round((a[0] + b[0]) / 2 + 32 * nx),
                          y=round((a[1] + b[1]) / 2 + 32 * ny),
                          z=layout.regions[room.region_id].floor_z,
                          angle=build_angle(nx, ny), cstat=210,
                          x_repeat=28, y_repeat=32, shade=-33)

    lower.raw("E3M6 sprite 157: foam at the fall's foot", foam)


def pour(upper, face: str, lower, *, pal: int = 0, sound_id: str, sound_at: float = 0.5):
    """Make the drop on `upper`'s `face` into `lower` a fall of water (or, at pal 7, blood).

    `upper` is the room the water comes from, `lower` the room under the
    drop it falls into; their faces must be joined. The lower wall wears
    E1M8's panned falling-water finish and the sound stands at its foot,
    `sound_at` along the face.
    """
    from bloodmap.corpus import corpus_map_path
    from bloodmap.format import read_map
    from bloodmap.model import record_extra, record_fields

    source, wall_id, sound_source, sound_sprite, sound_sector = POUR_SOURCE
    wall = read_map(corpus_map_path(source)).walls[wall_id]
    _waterfall(upper, face, lower, wall, pal=pal)
    example = read_map(corpus_map_path(sound_source))
    sound = example.sprites[sound_sprite]
    sound_fields = {key: record_fields(sound)[key] for key in
                    ("picnum", "type", "cstat", "status", "shade", "x_repeat", "y_repeat")}
    sound_behavior = {key: record_extra(sound)[key] for key in
                      ("state", "busy", "data_1", "data_2", "data_3", "data_4")}
    sound_height = record_fields(example.sectors[sound_sector])["floor_z"] - record_fields(sound)["z"]

    def foot(layout, room):
        a, b = (upper.world_frame().apply(p) for p in upper.local_edge(face))
        x = a[0] + (b[0] - a[0]) * sound_at
        y = a[1] + (b[1] - a[1]) * sound_at
        # half a unit into the lower room
        cx, cy = (sum(p[0] for p in room.world_outline()) / len(room.outline),
                  sum(p[1] for p in room.world_outline()) / len(room.outline))
        norm = ((cx - x) ** 2 + (cy - y) ** 2) ** 0.5 or 1.0
        x, y = x + (cx - x) / norm * 512, y + (cy - y) / norm * 512
        floor = layout.regions[room.region_id].floor_z
        layout.add_sprite(sound_id, room.region_id, x=int(x), y=int(y),
                          z=int(floor - sound_height), behavior=sound_behavior, **sound_fields)

    lower.raw(f"{sound_source} sprite {sound_sprite}: falling water sound at the foot", foot)


def stockyard_trolley(city, sewer, rooms: dict) -> None:
    """Extend the stockyard race with the sampling chamber and its two berths."""
    import citytree

    # The terminal basin reaches under Market Slip's river. Leave a slab
    # between the harbour's band and the sampling chamber's flat roof.
    city.declare_layer(TROLLEY_LAYER, ceiling_z=TROLLEY_CEILING,
                       floor_z=TROLLEY_FLOOR + CHANNEL_DROP,
                       note="the stockyard sampling chamber under the river")
    part = sewer.assembly("sampling", style=Style(layer=TROLLEY_LAYER),
                          note="the stockyard's cross-channel sampling chamber")
    for name, rect, note in STOCKYARD_TROLLEY_ROOMS:
        x0, y0, x1, y1 = (round(v * PU) for v in rect)
        dry = name in {"trolley_step", "trolley_walk", "trolley_ledge", "trolley_alcove"}
        material = BRANCH_DRY["stockyard_drain"] if dry else STOCKYARD_WET
        room = part.rect_room(
            name, origin=(x0, y0), size=(x1 - x0, y1 - y0),
            role="interior", note=note, intent={"kind": "furnished"},
            region_kwargs=material.region_kwargs())
        drop = 0 if dry else CHANNEL_DROP
        floor = (SEWER_FLOOR + TROLLEY_STEP if name == "trolley_step" else TROLLEY_FLOOR) + drop
        room.surfaces(**material.style_kwargs(
            ceiling_picnum=253,
            floor_z=floor, clear_height=floor - TROLLEY_CEILING,
            floor_shade=24 if dry else 30))
        if name in {"trolley_inlet", "trolley_tail"}:
            room.region_kwargs["sector_behavior"] = {"depth": 1, **flow_behavior(*FLOW["sampling"])}
        if name in {"trolley_ledge", "trolley_alcove"}:
            room.light_source("work_light", local=(0.5, (58.25 - rect[1]) / (rect[3] - rect[1])),
                              height_player_heights=1.0)
        if name == "trolley_alcove":
            room.surfaces(wall_picnum=499)
        rooms[name] = room

    for a, face_a, b, face_b in (
        ("stockyard_drain", "south", "trolley_inlet", "north"),
        ("stockyard_drain_walk_b", "south", "trolley_inlet", "north"),
        ("stockyard_drain_walk_a", "south", "trolley_step", "north"),
        ("trolley_walk", "north", "trolley_step", "south"),
        ("trolley_inlet", "west", "trolley_step", "east"),
        ("trolley_track", "north", "trolley_inlet", "south"),
        ("trolley_tail", "north", "trolley_track", "south"),
        ("trolley_ledge", "west", "trolley_walk", "east"),
        ("trolley_ledge", "north", "trolley_inlet", "south"),
        ("trolley_track", "west", "trolley_ledge", "east"),
        ("trolley_tail", "west", "trolley_ledge", "east"),
        ("trolley_track", "east", "trolley_alcove", "west"),
    ):
        citytree.join(rooms[a], rooms[b], at_a=face_a, at_b=face_b,
                      connection_id=f"connection:{a}_{b}")
    for name, rect, pool in SAMPLING_CULVERTS:
        x0, y0, x1, y1 = (round(v * PU) for v in rect)
        # The bars hang just inside the mouth, between two lengths of one
        # culvert: at the mouth itself the grate would share its wall record,
        # and so its repeats, with the tiled band over the opening.
        before = rooms[pool]
        for part_name, left, right in ((f"{name}_mouth", x0, x0 + CULVERT_MOUTH), (name, x0 + CULVERT_MOUTH, x1)):
            culvert = part.rect_room(
                part_name, origin=(left, y0), size=(right - left, y1 - y0), role="interior",
                intent={"kind": "furnished"}, note="a barred culvert draining the sampling chamber under the river",
                region_kwargs={**STOCKYARD_WET.region_kwargs(), "declared_zero_exit": True,
                               "sector_behavior": {"depth": 1, **flow_behavior(*FLOW["sampling"])}})
            culvert.surfaces(**STOCKYARD_WET.style_kwargs(
                ceiling_picnum=253, floor_z=TROLLEY_FLOOR + CHANNEL_DROP, clear_height=CULVERT_CLEAR,
                floor_shade=44, wall_shade=48))
            rooms[part_name] = culvert
            citytree.join(culvert, before, at_a="west", at_b="east",
                          connection_id=f"connection:{part_name}", min_opening=0)
            before = culvert
        culvert.raw("bars across the culvert, inside its mouth",
                    lambda layout, room, outer=rooms[f"{name}_mouth"]: _bar_culvert(layout, room, outer))
    # the drain's blood falls over the sunk chamber's edge beside the stair
    # down: a pour in E1M8's blood palette (7)
    pour(rooms["stockyard_drain"], "south", rooms["trolley_inlet"], pal=7,
         sound_id="placement:stockyard:pour_sound")
    rooms["trolley_track"].raw(
        "#2WAYCAR: full-wall slide, dry calls, and a carried departure button",
        lambda layout, track: _furnish_trolley(layout, track, rooms))


def _bar_culvert(layout, culvert, outer) -> None:
    """Hang the grate across a culvert, on both faces of the line it shares with `outer`."""
    a, b = (culvert.world_frame().apply(p) for p in culvert.local_edge("west"))
    repeat = max(1, round(abs(a[1] - b[1]) / 128))          # 16 units to the pixel
    for room in (culvert, outer):
        layout.paint_wall(room.region_id, a, b, x_repeat=repeat, y_repeat=8, **CULVERT_GRATE)


def _furnish_trolley(layout, track, rooms: dict) -> None:
    """Fit the moving floor, mount its controls and dress the fixed berths."""
    from bloodmap import mechanism, motion, wiring
    from bloodmap.placement import drawn_extent
    from bloodmap.player_space import PLAYER_PROFILES
    from bloodmap.shade_table import _art
    from l3_foundry import _attested
    import props
    import wires

    body = PLAYER_PROFILES["blood"]
    x0, y0, x1, y1 = props.room_rect(track)
    cy = (y0 + y1) // 2
    deck_id = track.region_id + "_deck"
    rail_to_berth = 96
    length, width = 1280, 1024
    deck_x = x0 + rail_to_berth
    deck = (deck_x, cy - width // 2, deck_x + length, cy + width // 2)

    wire = wires.wire(TROLLEY_WIRE)
    wire.then(wiring.region(deck_id))
    mechanism.slide_shuttle(
        layout, "stockyard_trolley", host_region=track.region_id, deck_region=deck_id,
        footprint=deck, travel=(length + 2 * rail_to_berth - (x1 - x0), 0),
        channel=wire.channel, floor_z=TROLLEY_FLOOR,
        wall_picnum=499, portal_wall_picnum=499, floor_picnum=209, ceiling_picnum=253,
        wall_shade=22, floor_shade=22, ceiling_shade=30, intent={"kind": "furnished"})

    call = _attested("E1M4", 21, 1046)
    drive = _attested("E1M2", 20, 1046)
    lamp = _attested("E3M4", 0, 501)
    for end, name, state, face in (
        ("west", "trolley_ledge", motion.CMD_ON, "south"),
        ("east", "trolley_alcove", motion.CMD_OFF, "east"),
    ):
        berth = rooms[name]
        bx0, by0, bx1, by1 = props.room_rect(berth)
        if face == "south":
            a, b, t = (bx1, by1), (bx0, by1), 0.25
        else:
            a, b, t = (bx1, by0), (bx1, by1), (cy - by0) / (by1 - by0)
        button = f"sewer:trolley_call_{end}"
        wire.when(wiring.placement(button), "push", command=state, wait_time=1)
        layout.place_on_wall(
            button, berth.region_id, a1=a, a2=b, t=t,
            height_player_heights=0.62, shade=-12,
            behavior={**call["behavior"], "data_2": 0}, **call["fields"])
        lamp_at = (0.5, (cy - by0) / (by1 - by0))
        layout.place_on_ceiling(f"sewer:trolley_light_{end}", berth.region_id, local=lamp_at,
                                **{**lamp["fields"], "x_repeat": 30, "y_repeat": 30, "shade": -16})

    cx = deck_x + length // 2
    rider = "sewer:trolley_depart"
    wire.when(wiring.placement(rider), "push", command=motion.CMD_TOGGLE, off=True)
    # The button is on the inside face of the north railing. Both ends
    # of the deck stay clear for boarding.
    layout.add_sprite(
        rider, deck_id, x=cx, y=cy - 352, z=TROLLEY_FLOOR - 7936, angle=512,
        shade=-12, behavior=dict(drive["behavior"]),
        **{**drive["fields"], "cstat": drive["fields"]["cstat"] | mechanism.CARRY_WITH})

    rail = _attested("E2M5", 0, 155)
    wheels = _attested("E1M2", 0, 708)
    for end, side, angle in (("north", -1, 1536), ("south", 1, 512)):
        for label, spec, inset, repeats, flags in (
            ("rail", rail, 416, (76, 40), 16 | 128 | 1),
            ("wheels", wheels, 480, (49, 16), 16 | 64 | 128),
        ):
            fields = {**spec["fields"], "x_repeat": repeats[0], "y_repeat": repeats[1],
                      "cstat": flags | mechanism.CARRY_WITH}
            art = _art()[fields["picnum"]]
            _, bottom = drawn_extent(art.height, art.animation["yofs"],
                                     fields["y_repeat"], fields["cstat"])
            layout.add_sprite(
                f"sewer:trolley_{label}_{end}", deck_id, x=cx, y=cy + side * inset,
                z=TROLLEY_FLOOR - 8 - bottom, angle=angle, shade=12,
                behavior=dict(spec["behavior"]), **fields)

    for name in ("trolley_inlet", "trolley_tail", *(n for row in SAMPLING_CULVERTS for n in (row[0], f"{row[0]}_mouth"))):
        wet = layout.regions[rooms[name].region_id]
        layout.add_overlay(f"blood:{name}", wet.region_id, wet.outer, floor_pal=7)
    # The station paints over track tile on raised floors during its trim
    # pass. Lay this floor finish afterwards, over the whole moving hole's
    # host without cutting it. Relative alignment centres the half-scale rails.
    bed = layout.regions[track.region_id]
    layout.add_overlay("sewer:trolley_rail_bed", bed.region_id, bed.outer,
                       floor_picnum=1129, floor_stat=64 | 8)

_FACES = {"x": {"low": "north", "high": "south", "start": "west", "end": "east"},
          "y": {"low": "west", "high": "east", "start": "north", "end": "south"}}


def _strips(x0, y0, x1, y1, axis):
    """A corridor's three strips across its width: low walk, channel, high walk."""
    w = WALK / PU
    if axis == "x":
        return [(x0, y0, x1, y0 + w), (x0, y0 + w, x1, y1 - w), (x0, y1 - w, x1, y1)]
    return [(x0, y0, x0 + w, y1), (x0 + w, y0, x1 - w, y1), (x1 - w, y0, x1, y1)]


def _corridors():
    """Every corridor: (channel, rect, axis, (low walk, high walk), part, low end, high end)."""
    out = []
    for channel, x0, y0, x1, y1, axis, walks, low_end, high_end in SIDES:
        out.append((channel, (x0, y0, x1, y1), axis, walks, "ring", low_end, high_end))
    through = {(c, which): (o, f) for c, which, o, f in THROUGH}
    for name, x0, y0, x1, y1, other, other_face, own, part, _note in BRANCHES:
        if name in BRANCH_ROOMS:
            continue
        axis = "x" if (x1 - x0) > (y1 - y0) else "y"
        end = (other, other_face) if other else None
        low = end if own in ("west", "north") else through.get((name, "start"))
        high = end if own in ("east", "south") else through.get((name, "end"))
        out.append((name, (x0, y0, x1, y1), axis, (f"{name}_walk_a", f"{name}_walk_b"),
                    part, low, high))
    return out


def _gaps():
    """Where a branch's channel enters a corridor from the side: (corridor, side) -> [(lo, hi, branch)]."""
    corridors = {c[0]: c for c in _corridors()}
    out = {}
    rows = [(n, x0, y0, x1, y1, o, f) for n, x0, y0, x1, y1, o, f, *_r in BRANCHES]
    rects = {n: (x0, y0, x1, y1) for n, x0, y0, x1, y1, *_r in BRANCHES}
    rows += [(c, *rects[c], o, f) for c, _which, o, f in THROUGH]
    for name, x0, y0, x1, y1, other, other_face in rows:
        if other not in corridors:
            continue
        axis = corridors[other][2]
        side = next((s for s, f in _FACES[axis].items() if f == other_face and s in ("low", "high")), None)
        if side is None:
            continue                       # it meets the corridor's end, not its side
        lo, hi = (x0, x1) if axis == "x" else (y0, y1)
        out.setdefault((other, side), []).append((lo, hi, name))
    return out


def _pieces(rect, axis, gaps):
    """A walk cut where branches cross it: [(kind, rect)] in order along the axis; kind 'walk' or 'ford'."""
    x0, y0, x1, y1 = rect
    start, end = (x0, x1) if axis == "x" else (y0, y1)

    def sub(a, b):
        return (a, y0, b, y1) if axis == "x" else (x0, a, x1, b)

    out, cursor = [], start
    for lo, hi, branch in sorted(gaps):
        if lo > cursor:
            out.append(("walk", sub(cursor, lo), None))
        out.append(("ford", sub(lo, hi), branch))
        cursor = hi
    if end > cursor:
        out.append(("walk", sub(cursor, end), None))
    return out


def plan() -> list[dict]:
    """Every room of the sewer network this module builds, with its rectangle in plan units and its kind."""
    out = plan_rooms()
    for name, rect, channel, side, kind in _niches():
        out.append({"name": name, "rect": rect, "kind": "niche", "part": "chambers", "wet": False,
                    "flow": None, "niche": kind, "of": channel, "side": side})
    return out


def plan_rooms() -> list[dict]:
    """The network without its niches."""
    out = []
    for name, x0, y0, x1, y1 in CORNERS:
        out.append({"name": name, "rect": (x0, y0, x1, y1), "kind": "corner", "part": "ring",
                    "wet": True, "flow": name})
    gaps = _gaps()
    for channel, rect, axis, walks, part, _low, _high in _corridors():
        low_rect, chan_rect, high_rect = _strips(*rect, axis)
        out.append({"name": channel, "rect": chan_rect, "kind": "channel", "part": part,
                    "wet": True, "flow": channel, "corridor": channel, "axis": axis})
        for side, base, wrect in (("low", walks[0], low_rect), ("high", walks[1], high_rect)):
            walk_n = ford_n = 0
            for kind, prect, branch in _pieces(wrect, axis, gaps.get((channel, side), [])):
                if kind == "walk":
                    walk_n += 1
                    pname = base if walk_n == 1 else f"{base}_{walk_n}"
                    out.append({"name": pname, "rect": prect, "kind": "walk", "part": part,
                                "wet": False, "corridor": channel, "axis": axis, "side": side,
                                "walk": base})
                else:
                    ford_n += 1
                    pname = f"{base}_ford" if ford_n == 1 else f"{base}_ford_{ford_n}"
                    out.append({"name": pname, "rect": prect, "kind": "ford", "part": part,
                                "wet": True, "flow": branch, "corridor": channel, "axis": axis,
                                "side": side, "walk": base, "branch": branch})
    for name, x0, y0, x1, y1, *_rest in BRANCHES:
        if name in BRANCH_ROOMS:
            out.append({"name": name, "rect": (x0, y0, x1, y1), "kind": "chamber",
                        "part": "chambers", "wet": True, "flow": name})
    for name, x0, y0, x1, y1, *_rest in CHAMBERS:
        out.append({"name": name, "rect": (x0, y0, x1, y1), "kind": "chamber", "part": "chambers",
                    "wet": name == "flooded", "flow": None})
    for name, x0, y0, x1, y1, *_rest in NECKS:
        out.append({"name": name, "rect": (x0, y0, x1, y1), "kind": "neck", "part": "necks",
                    "wet": False, "flow": None})
    return out


def edge(rooms: dict, leg: str, face: str, at: float | None = None):
    """The room that a face of a ring room or corridor is, at a point along it (plan units).

    A corridor's long face is one of its walks, cut where branches cross it:
    `edge(rooms, "w_leg", "west", at=27.5)` is the piece of the west leg's
    west walk that stands at y 27.5. Anything else is the room itself.
    """
    entries = {e["name"]: e for e in plan()}
    corridors = {c[0]: c for c in _corridors()}
    walk = None
    if leg in corridors:
        axis = corridors[leg][2]
        side = next((s for s in ("low", "high") if _FACES[axis][s] == face), None)
        if side is not None:
            walk = corridors[leg][3][0 if side == "low" else 1]
    elif any(e.get("walk") == leg for e in entries.values()):
        walk = leg
    if walk is None:
        return rooms[leg]
    pieces = [e for e in plan() if e.get("walk") == walk and e["kind"] == "walk"]
    if at is None:
        return rooms[pieces[0]["name"]]
    for e in pieces:
        x0, y0, x1, y1 = e["rect"]
        lo, hi = (x0, x1) if e["axis"] == "x" else (y0, y1)
        if lo <= at <= hi:
            return rooms[e["name"]]
    return rooms[min(pieces, key=lambda e: abs(at - sum(e["rect"][i] for i in ((0, 2) if e["axis"] == "x" else (1, 3))) / 2))["name"]]


def hall(sewer, rooms: dict) -> dict:
    """Build the tanks, gallery outfall, stair and service lift."""
    from dataclasses import replace

    from bloodmap.corpus import corpus_map_path
    from bloodmap.format import read_map
    from bloodmap.model import record_extra, record_fields
    import citytree

    part = sewer.assembly(HALL_LAYER, note="the settling hall: tanks under the gallery")
    for name, x0, y0, x1, y1, kind in HALL:
        wet = kind == "tank"
        material = SEWER_WET if wet else SEWER
        behavior = {"amplitude": -4, "shade_frequency": 4} if wet else {}
        if wet and name in FLOW:
            behavior.update(flow_behavior(*FLOW[name]))
        wx0, wy0, wx1, wy1 = (int(v * PU) for v in (x0, y0, x1, y1))
        made = part.room(
            name, [(0, 0), (wx1 - wx0, 0), (wx1 - wx0, wy1 - wy0), (0, wy1 - wy0)],
            role="interior", faces=dict(COMPASS), frame=Frame(wx0, wy0),
            region_kwargs={**material.region_kwargs(), "sector_behavior": behavior},
            note=f"the settling hall: {name.replace('_', ' ')}")
        floor = HALL_WATER if wet else HALL_WALK
        made.surfaces(layer=HALL_LAYER, **material.style_kwargs(
            floor_z=floor, clear_height=floor - (SEWER_FLOOR - WALK_CLEAR),
            floor_shade=38 if wet else 40))
        rooms[name] = made
    for a, fa, b, fb in HALL_JOINS:
        citytree.join(rooms[a], rooms[b], at_a=fa, at_b=fb,
                      connection_id=f"connection:hall_{a}_{fa}_{b}")
    # Route the channel across the south walk through E3M3's low spillway.
    ledge = edge(rooms, "gallery", "south", 26.0)
    x0, y0, x1, y1 = next(e["rect"] for e in plan() if e["name"] == ledge_name(rooms, ledge))
    wx0, wy0, wx1, wy1 = (round(v * PU) for v in (x0, y0, x1, y1))
    left, right = (round(x * PU) for x in HALL_OUTFALL)
    depth = wy1 - wy0
    slope = ledge.region_kwargs["ceiling_slope"]
    ledge.outline = [(0, 0), (left - wx0, 0), (left - wx0, depth), (0, depth)]
    ledge.region_kwargs["ceiling_slope"] = replace(slope, hinge=((wx0, wy0), (left, wy0)))
    east = ledge.parent.rect_room(
        "gallery_walk_east", origin=(right, wy0), size=(wx1 - right, depth),
        role=ledge.role, style=ledge.style,
        region_kwargs={**ledge.region_kwargs, "ceiling_slope":
                       replace(slope, hinge=((right, wy0), (wx1, wy0)))},
        note="the gallery walk at the head of the settling hall stair")

    example = read_map(corpus_map_path("E3M3"))
    feed = record_fields(example.sectors[173])
    floor = SEWER_FLOOR + CHANNEL_DROP
    mouth = part.rect_room(
        "outfall_mouth", origin=(left, wy0), size=(right - left, depth),
        role="interior", note="the gallery's low outfall into the first settling tank",
        region_kwargs={**SEWER_WET.region_kwargs(), "sector_behavior":
                       flow_behavior(512, record_extra(example.sectors[173])["pan_velocity"], False)})
    mouth.surfaces(layer=ledge.effective_style()["layer"], **SEWER_WET.style_kwargs(
        floor_z=floor, clear_height=feed["floor_z"] - feed["ceiling_z"],
        floor_shade=38))

    tank = rooms["tank_1"]
    for a, fa, b, fb in (
        (rooms["west_quay"], "north", ledge, "south"),
        (east, "north", rooms["gallery"], "south"),
        (mouth, "north", rooms["gallery"], "south"),
        (mouth, "west", ledge, "east"),
        (mouth, "east", east, "west"),
        (mouth, "south", tank, "north"),
    ):
        citytree.join(a, b, at_a=fa, at_b=fb,
                      connection_id=f"connection:hall_{a.node_id}_{fa}_{b.node_id}")
    north_a, north_b = tank.local_edge("north")
    tank_width = north_b[0] - north_a[0]
    dry_width = left - tank.frame.dx
    citytree.join(tank, ledge,
                  at_a=tank.face("north", at=dry_width / (2 * tank_width), width=dry_width),
                  at_b="south", connection_id="connection:hall_tank_1_gallery")

    # Bottom swap gives the water its own texture frame below the metal lintel.
    source = example.walls[1307]
    mouth_finish = {key: record_fields(source)[key] for key in
                    ("picnum", "type", "x_repeat", "y_repeat", "x_panning", "y_panning")}
    pan = {key: record_extra(source)[key] for key in
           ("pan_always", "pan_x_velocity", "pan_y_velocity", "x_pan_fraction", "y_pan_fraction")}
    pool_cstat = record_fields(example.walls[1319])["cstat"]

    def spill(layout, room):
        a, b = (room.world_frame().apply(p) for p in room.local_edge("south"))
        layout.paint_wall(room.region_id, a, b, fixed_frame=True, **mouth_finish)
        layout.wire_wall(room.region_id, a, b, **pan)
        layout.paint_wall(tank.region_id, a, b, cstat=pool_cstat)

    mouth.raw("E3M3 walls 1307/1319: panned sewage beneath a metal lintel", spill)
    _foam_at_foot(mouth, "south", tank, "settling_spillway")

    sample = example.sprites[393]
    sound = record_fields(sample)
    sound_fields = {key: sound[key] for key in
                    ("picnum", "type", "cstat", "status", "shade", "x_repeat", "y_repeat")}
    sound_behavior = {key: record_extra(sample)[key] for key in
                      ("state", "busy", "data_1", "data_2", "data_3", "data_4")}
    sound_height = record_fields(example.sectors[174])["floor_z"] - sound["z"]

    def water_sound(layout, room):
        x, y = mouth.world_frame().apply(((right - left) // 2, depth + 512))
        z = room.world_frame().apply_z(HALL_WATER - sound_height)
        layout.add_sprite("placement:settling_hall:outfall_sound", room.region_id,
                          x=x, y=y, z=z, behavior=sound_behavior, **sound_fields)

    tank.raw("E3M3 sprite 393: falling water sound at the foot", water_sound)

    east.staircase(
        # a south face runs east to west: `at` is measured from its east end
        "hall_stair", "south", at=(x1 - HALL_STAIR["at_x"]) / (x1 - HALL_OUTFALL[1]),
        width=HALL_STAIR["width"],
        total_rise=HALL_WALK - SEWER_FLOOR, tread=HALL_STAIR["tread"],
        step_rise=HALL_STAIR["step_rise"], arrive_at=rooms["circle_quay"].region_id,
        connection={"role": "portal"})
    _hall_service_lift(part, ledge, rooms["west_quay"])
    return rooms


def _hall_service_lift(part, gallery, quay) -> None:
    """Join the dry walk and quay through a fixed shaft with a moving deck."""
    from bloodmap import mechanism, motion, wiring
    from bloodmap.player_space import PLAYER_PROFILES
    from l3_foundry import _attested
    import citytree
    import wires

    body = PLAYER_PROFILES["blood"]
    high_z, low_z = (room.effective_style()["floor_z"] for room in (gallery, quay))
    ceiling_z = SEWER_FLOOR - WALK_CLEAR
    shaft_id = f"region:{part.path()}/service_lift"
    sx0, sy0, sx1, sy1 = (round(v * PU) for v in HALL_LIFT_SHAFT)
    uy0, uy1 = (round(v * PU) for v in HALL_LIFT_UPPER_MOUTH)
    upper_jamb = round(HALL_LIFT_UPPER_JAMB * PU)
    lx0, ly0, lx1, ly1 = (round(v * PU) for v in HALL_LIFT_LOWER)

    upper = part.room(
        "lift_gallery", [(round(x * PU), round(y * PU)) for x, y in HALL_LIFT_UPPER],
        role="gateway", faces={"gallery": 3}, intent={"kind": "furnished"},
        note="the lift's upper landing: a return wall and a raised sill at the shaft")
    upper.surfaces(layer=gallery.effective_style()["layer"],
                   **SEWER.style_kwargs(floor_z=high_z - 2048,
                                        clear_height=22528, floor_shade=24))
    lower = part.rect_room(
        "lift_quay", origin=(lx0, ly0), size=(lx1 - lx0, ly1 - ly0),
        role="gateway", intent={"kind": "furnished"},
        note="the lift's lower landing: a dry loading bay off the west quay")
    lower.surfaces(layer=HALL_LAYER, **SEWER.style_kwargs(
        floor_z=low_z, clear_height=SEWER_CLEAR, floor_shade=24))
    lamp_at = (0.47, 0.45)
    for landing in (upper, lower):
        landing.light_source("work_light", local=lamp_at, height_player_heights=1.15)
    citytree.join(upper, gallery, at_a="gallery", at_b="west",
                  connection_id="connection:hall_lift_gallery_walk",
                  min_opening=body.standing_height)
    citytree.join(lower, quay, at_a="east", at_b="west",
                  connection_id="connection:hall_lift_west_quay",
                  min_opening=body.standing_height)

    wire = wires.wire(HALL_LIFT_WIRE)
    upper_call = "sewer:hall_lift_upper_call"
    lower_call = "sewer:hall_lift_lower_call"
    rider = "sewer:hall_lift_rider"
    # A momentary OneWay reports its press, then silently resets. Both
    # buttons address the same receiver with explicit destination commands.
    wire.when(wiring.placement(upper_call), "push", command=motion.CMD_ON, wait_time=1)
    wire.when(wiring.placement(lower_call), "push", command=motion.CMD_OFF, wait_time=1)
    wire.when(wiring.placement(rider), "push", command=motion.CMD_TOGGLE, off=True)
    wire.then(wiring.region(shaft_id))

    def furnish(layout, _room):
        mechanism.lift(
            layout, "settling hall service lift", footprint=(sx0, sy0, sx1, sy1),
            region=shaft_id, low_z=low_z, high_z=high_z, ceiling_z=ceiling_z,
            channel=wire.channel, route="remote", busy_up=24, busy_down=24,
            layer=HALL_LAYER, wall_picnum=499, floor_picnum=209, ceiling_picnum=438,
            wall_shade=26, floor_shade=24, ceiling_shade=28)
        # The city's type-600 door pass would otherwise turn the deck into a door.
        LATE_TYPES[shaft_id] = layout.regions[shaft_id].type
        layout.regions[shaft_id].type = 0

        for landing, end, y0, y1 in ((upper, "upper", uy0, uy1),
                                     (lower, "lower", ly0, ly1)):
            layout.add_connection(
                f"connection:hall_lift_{end}_shaft", landing.region_id, shaft_id,
                a1=(sx1, y1), a2=(sx1, y0), min_width=body.body_width,
                min_opening=body.standing_height)

        call = _attested("E1M4", 21, 1046)
        drive = _attested("E1M2", 20, 1046)
        lamp = _attested("E3M4", 0, 501)
        for placement, landing, wall in (
            (upper_call, upper, ((upper_jamb, round(43.25 * PU)), (upper_jamb, uy1))),
            (lower_call, lower, ((lx0, ly0), (lx1, ly0))),
        ):
            layout.place_on_wall(
                placement, landing.region_id, a1=wall[0], a2=wall[1],
                height_player_heights=body.eye_height / body.standing_height,
                shade=-12, behavior={**call["behavior"], "data_2": 0}, **call["fields"])
            layout.place_on_ceiling(
                f"sewer:hall_lift_{landing.node_id}_light", landing.region_id,
                local=lamp_at,
                **{**lamp["fields"], "x_repeat": 30, "y_repeat": 30, "shade": -16})
        layout.place_on_wall(
            rider, shaft_id, a1=(sx0, sy1), a2=(sx0, sy0),
            height_player_heights=body.eye_height / body.standing_height,
            shade=-12, behavior=drive["behavior"],
            **{**drive["fields"], "cstat": drive["fields"]["cstat"] | mechanism.CARRY_WITH})

    upper.raw("MACHINERY-LIFT: two dry landings, two calls and a deck switch", furnish)


#: region id -> sector type, set by the build once the doors are framed
LATE_TYPES: dict = {}


def secret_rooms(sewer, rooms: dict) -> dict:
    """Old Molly's nest and the plague pit, off Graves Brook (`SECRET_ROOMS`)."""
    import citytree

    part = sewer.assembly("secrets", note="the sewer's secret rooms: the legends")
    for name, x0, y0, x1, y1, sunk, clear, kind, joined, note in SECRET_ROOMS:
        if kind == "seal":
            blown_hole(part, rooms, name, (x0, y0, x1, y1), joined, note)
            continue
        material = SECRET_MATERIAL[kind]
        region_kwargs = material.region_kwargs()
        floor = SEWER_FLOOR + sunk
        if kind in ("lair", "vault"):
            region_kwargs["secret"] = True
            # the pit's one way out is the seal, shut until it is blown
            region_kwargs["declared_zero_exit"] = kind == "vault"
            region_kwargs["sector_behavior"] = {"amplitude": -12, "shade_frequency": 7}
        wx0, wy0, wx1, wy1 = (int(v * PU) for v in (x0, y0, x1, y1))
        made = part.room(
            name, [(0, 0), (wx1 - wx0, 0), (wx1 - wx0, wy1 - wy0), (0, wy1 - wy0)],
            role={"crawl": "gateway", "seal": "doorway"}.get(kind, "secret"),
            faces=dict(COMPASS), frame=Frame(wx0, wy0), region_kwargs=region_kwargs, note=note)
        made.surfaces(**material.style_kwargs(floor_z=floor, clear_height=clear,
                                              floor_shade=44 if kind in ("lair", "vault") else 40))
        rooms[name] = made
        if joined is None:
            continue
        other, face, at = joined
        target = edge(rooms, other, face, at) if at is not None else rooms[other]
        own = {"north": "south", "south": "north", "east": "west", "west": "east"}[face]
        RESOLVED[(name, own)] = (target, face)
        # anchored from the smaller face: the narrow way in, never the room
        small, big = (made, target) if at is not None else (target, made)
        citytree.join(small, big, at_a=own if small is made else face,
                      at_b=face if small is made else own,
                      connection_id=f"connection:sewer_secret_{name}")
    return rooms


def spider_lair(sewer, rooms: dict) -> dict:
    """The Weaver's Cellars: the hall, its brood alcoves and the passage up from the brook."""
    import citytree

    part = sewer.assembly(LAIR_LAYER_PART, note="the Weaver's Cellars: a spider lair under the old quarter")
    ox = int(min(p[0] for p in LAIR_HALL) * PU)
    oy = int(min(p[1] for p in LAIR_HALL) * PU)
    material = LAIR_MATERIAL["hall"]
    hall_room = part.room(
        "lair_hall", [(int(x * PU) - ox, int(y * PU) - oy) for x, y in LAIR_HALL],
        role="interior", faces=dict(LAIR_HALL_FACES), frame=Frame(ox, oy),
        region_kwargs=material.region_kwargs(),
        note="the cellar hall: cobblestone, earth, its corners knocked off",
        #: furnished by `dress_lair`, not by the city's generic dressing,
        #: which stood a shovel in a nest (round 3 and 4's "dark rod")
        intent={"kind": "furnished"})
    hall_room.surfaces(**material.style_kwargs(floor_z=SEWER_FLOOR, clear_height=LAIR_CLEAR, floor_shade=40))
    hall_room.carve([(int(x * PU) - ox, int(y * PU) - oy) for x, y in LAIR_PILLAR])
    rooms["lair_hall"] = hall_room
    material = LAIR_MATERIAL["alcove"]
    for name, x0, y0, x1, y1, face, rise, clear, _eggs in LAIR_ALCOVES:
        wx0, wy0, wx1, wy1 = (int(v * PU) for v in (x0, y0, x1, y1))
        made = part.room(
            name, [(0, 0), (wx1 - wx0, 0), (wx1 - wx0, wy1 - wy0), (0, wy1 - wy0)],
            role="interior", faces=dict(COMPASS), frame=Frame(wx0, wy0),
            region_kwargs=material.region_kwargs(), note="a nest walled in silk, its cocoons in it",
            intent={"kind": "furnished"})
        made.surfaces(**material.style_kwargs(floor_z=SEWER_FLOOR - rise,
                                              clear_height=clear, floor_shade=40))
        rooms[name] = made
        own = {"west": "east", "east": "west", "north": "south", "south": "north"}[face]
        citytree.join(made, hall_room, at_a=own, at_b=face,
                      connection_id=f"connection:sewer_lair_{name}")
    material = LAIR_MATERIAL["passage"]
    wx0, wy0, wx1, wy1 = (int(v * PU) for v in LAIR_PASSAGE)
    passage = part.room(
        "lair_passage", [(0, 0), (wx1 - wx0, 0), (wx1 - wx0, wy1 - wy0), (0, wy1 - wy0)],
        role="gateway", faces=dict(COMPASS), frame=Frame(wx0, wy0),
        region_kwargs=material.region_kwargs(), note="the passage up from Graves Brook, a web across it")
    passage.surfaces(**material.style_kwargs(floor_z=SEWER_FLOOR, clear_height=LAIR_PASSAGE_CLEAR,
                                             floor_shade=40))
    rooms["lair_passage"] = passage
    citytree.join(passage, hall_room, at_a="north", at_b="south",
                  connection_id="connection:sewer_lair_passage_hall")
    walk = edge(rooms, "graves_brook", "north", (LAIR_PASSAGE[0] + LAIR_PASSAGE[2]) / 2)
    RESOLVED[("lair_passage", "south")] = (walk, "north")
    citytree.join(passage, walk, at_a="south", at_b="north",
                  connection_id="connection:sewer_lair_passage_brook")
    return rooms


def stockyard_side_rooms(sewer, rooms: dict) -> None:
    """Build the carcass rack and the counted shrine off the drain's walks."""
    import citytree

    part = sewer.assembly("stockyard", note="the slaughterhouse intake and the Rat King's Shrine")
    for name, rect, material, rise, clear, role in STOCKYARD_ROOMS:
        x0, y0, x1, y1 = (int(v * PU) for v in rect)
        room = part.rect_room(
            name, origin=(x0, y0), size=(x1 - x0, y1 - y0),
            role=role, note=material.note, intent={"kind": "furnished"},
            region_kwargs={**material.region_kwargs(), "secret": role == "secret"})
        room.surfaces(**material.style_kwargs(floor_z=SEWER_FLOOR - rise,
                                              clear_height=clear - rise, floor_shade=38))
        rooms[name] = room

    walk = edge(rooms, "stockyard_drain", "east", 46.75)
    shrine = rooms["rat_king_shrine"]
    joins = [
        ("stockyard_rack", "east", edge(rooms, "stockyard_drain", "west", 53.0), "west"),
        ("rat_king_pipe", "west", walk, "east"),
        ("rat_king_pipe", "east", shrine, "west"),
        ("rat_king_step", "west", shrine, "east"),
        ("rat_king_step", "east", rooms["rat_king_altar"], "west"),
    ]
    for name, face, other, other_face in joins:
        citytree.join(rooms[name], other, at_a=face, at_b=other_face,
                      connection_id=f"connection:sewer_{name}_{face}")
    stockyard_pipe_bevels(part, rooms["rat_king_pipe"], walk, shrine)


def stockyard_pipe_bevels(part, pipe, walk, shrine) -> None:
    """Slope both sides of the old pipe so its mouth has bevelled corners."""
    import citytree
    from bloodmap.slope import SlopeSpec

    x0, y0 = pipe.frame.dx, pipe.frame.dy
    width, depth = pipe.outline[2]
    x1, y1 = x0 + width, y0 + depth
    band = 128
    for end, y, hinge, pipe_face in (
        ("north", y0 - band, ((x1, y0), (x0, y0)), "north"),
        ("south", y1, ((x0, y1), (x1, y1)), "south"),
    ):
        name = f"rat_king_pipe_{end}"
        bevel = part.rect_room(
            name, origin=(x0, y), size=(width, band), style=pipe.style,
            role="detail", intent={"kind": "furnished"},
            region_kwargs={**SHRINE_PIPE.region_kwargs(),
                           "floor_slope": SlopeSpec(hinge, rise_z=-3072),
                           "ceiling_slope": SlopeSpec(hinge, rise_z=5120)})
        inner = "south" if end == "north" else "north"
        for face, other, other_face in (("west", walk, "east"), ("east", shrine, "west"),
                                        (inner, pipe, pipe_face)):
            citytree.join(bevel, other, at_a=face, at_b=other_face,
                          connection_id=f"connection:sewer_{name}_{face}")


def blown_hole(part, rooms: dict, name: str, rect, joined, note: str) -> list:
    """The plague pit's seal: a ragged hole through the brook's south wall, shut until it is blown.

    The pieces lie side by side along the wall (`bloodmap.breach.ragged`,
    laid by `breach.lay`), each a Z-motion sector whose ceiling lies on its
    floor until the crack fires the wire; each slopes its floor and ceiling
    about a slanted edge. They are typed after the door pass, like the
    church's breach: a blown hole is not a door, and framed as one it stood
    a head two bodies tall.
    """
    import citytree
    import wires
    from bloodmap import breach, wiring

    other, face, _at = joined
    x0, y0, x1, y1 = (int(v * PU) for v in rect)
    material = SECRET_MATERIAL["seal"]
    pieces = breach.ragged(x1 - x0, y1 - y0, seed=f"sewer:{name}", sill=SEAL_SILL, top=SEAL_TOP)
    made = breach.lay(part, name, pieces, origin=(x0, y0), along=(1, 0), through=(0, 1),
                      near_floor=SEWER_FLOOR, region_kwargs=material.region_kwargs(),
                      rx_id=wires.channel("sewer:plague-pit"), note=note,
                      surfaces=material.style_kwargs(floor_z=SEWER_FLOOR, clear_height=0, floor_shade=40))
    for k, room in enumerate(made):
        rooms[room.node_id] = room
        wires.wire("sewer:plague-pit").then(wiring.region(room.region_id))
        LATE_TYPES[room.region_id] = 600
        walk = edge(rooms, other, face, breach.face_middle(room, "near")[0] / PU)
        RESOLVED[(room.node_id, "near")] = (walk, face)
        citytree.join(room, walk, at_a="near", at_b=face,
                      connection_id=f"connection:sewer_secret_{name}_{k}_near")
        citytree.join(room, rooms["plague_pit"], at_a="far", at_b="north",
                      connection_id=f"connection:sewer_secret_{name}_{k}_far")
    return made


def ledge_name(rooms: dict, room) -> str:
    return next(name for name, r in rooms.items() if r is room)


#: The chamber and neck joins as built: (room, its face) -> the room it opens onto.
RESOLVED: dict = {}


def _brook_feeder(part, brook):
    """A low cross-street culvert feeding the west end of Graves Brook."""
    import citytree
    from bloodmap.corpus import corpus_map_path
    from bloodmap.format import read_map

    material = Material(wall=110, floor=1120, ceiling=253, opening=194)
    feeder = part.rect_room(
        "brook_feeder", origin=(PU // 2, 19 * PU), size=(PU // 2, PU),
        role="interior", note="a low culvert feeding Graves Brook from the west",
        region_kwargs={**material.region_kwargs(),
                       "sector_behavior": flow_behavior(0, 30, False)})
    feeder.surfaces(**material.style_kwargs(floor_z=SEWER_FLOOR + CHANNEL_DROP - 6144,
                                            clear_height=8192, floor_shade=32))
    citytree.join(feeder, brook, at_a="east", at_b="west",
                  connection_id="connection:sewer_brook_feeder")
    wall = read_map(corpus_map_path(POUR_SOURCE[0])).walls[POUR_SOURCE[1]]
    _waterfall(feeder, "east", brook, wall, bottom_swap=True)
    _foam_at_foot(feeder, "east", brook, "brook_feeder")
    return feeder


def expand(city, sewer, existing: dict) -> dict:
    """Build the ring, its branches, its chambers and the necks onto the under-city."""
    import citytree
    from bloodmap.slope import SlopeSpec

    rooms: dict = {}
    parts = {
        "ring": sewer.assembly("ring", note="the circuit: corners, channels and their walks"),
        "chambers": sewer.assembly("chambers", note="what the ring passes through"),
        "necks": sewer.assembly("necks", note="the short joins between the two"),
    }
    corridor_of = {c[0]: c for c in _corridors()}

    def build(entry, note):
        name, (x0, y0, x1, y1), kind = entry["name"], entry["rect"], entry["kind"]
        corridor = entry.get("corridor")
        wet = entry["wet"]
        if kind == "walk" and corridor in BRANCH_DRY:
            material = BRANCH_DRY[corridor]
        elif corridor in BRANCH_MATERIAL or name in BRANCH_MATERIAL:
            material = BRANCH_MATERIAL.get(corridor) or BRANCH_MATERIAL[name]
        else:
            material = SEWER_WET if wet else SEWER
        behavior = {}
        if wet:
            # E3M3's water: a faint shimmer (shade wave, amplitude -4,
            # frequency 4) and a current
            behavior = {"amplitude": -4, "shade_frequency": 4}
            if entry.get("flow") in FLOW:
                behavior.update(flow_behavior(*FLOW[entry["flow"]]))
            if kind == "chamber" or entry.get("flow") == "stockyard_drain":
                behavior["depth"] = WATER_DEPTH
        elif kind == "chamber":
            behavior = {"amplitude": -16, "shade_frequency": 9}
        region_kwargs = {**material.region_kwargs(), "sector_behavior": behavior}
        wx0, wy0, wx1, wy1 = (int(v * PU) for v in (x0, y0, x1, y1))
        if kind == "walk":
            # the vault: the walk's ceiling falls from the channel's edge to
            # the wall, hinged on the edge it shares with the channel
            inner = {("x", "low"): ((wx1, wy1), (wx0, wy1)), ("x", "high"): ((wx0, wy0), (wx1, wy0)),
                     ("y", "low"): ((wx1, wy0), (wx1, wy1)), ("y", "high"): ((wx0, wy1), (wx0, wy0))}
            region_kwargs["ceiling_slope"] = SlopeSpec(
                hinge=inner[(entry["axis"], entry["side"])], rise_z=VAULT)
        made = parts[entry["part"]].room(
            name, [(0, 0), (wx1 - wx0, 0), (wx1 - wx0, wy1 - wy0), (0, wy1 - wy0)],
            role="secret" if name == "flooded" else ("gateway" if kind == "neck" else "interior"),
            intent={"kind": "furnished"} if corridor == "stockyard_drain" else None,
            faces=dict(COMPASS), frame=Frame(wx0, wy0), region_kwargs=region_kwargs, note=note)
        if name == "flooded":
            # SP's secret branch: `secret=True` emits the campaign's own
            # wiring rather than a label (channel 2, command 64, once).
            made.region_kwargs["secret"] = True
        if kind == "niche":
            material = Material(wall=NICHE_WALL[entry["niche"]], floor=568, ceiling=255,
                                opening=492, note=f"a {entry['niche']} niche")
            made.surfaces(**material.style_kwargs(
                floor_z=SEWER_FLOOR - NICHE_RISE,
                clear_height=NICHE_CLEAR_OF.get(entry["niche"], NICHE_CLEAR), floor_shade=40))
            rooms[name] = made
            return made
        if kind in ("walk", "channel", "ford", "corner"):
            ceiling = SEWER_FLOOR - WALK_CLEAR
            floor = SEWER_FLOOR + (CHANNEL_DROP if wet else 0)
            clear = floor - ceiling
        else:
            clear = SEWER_CHAMBER_CLEAR if kind == "chamber" else SEWER_CLEAR
            if name in {"station_foot", "silt_trap"}:
                # The spiral's foot and its receiving approach sit under the
                # station's straight flight: their roof begins at that
                # flight's final floor, leaving a real slab between the two.
                clear = SEWER_FLOOR - STATION_STACK_PLANE
            floor = SEWER_FLOOR + (CHANNEL_DROP if wet else 0)
            clear += CHANNEL_DROP if wet else 0
        made.surfaces(**material.style_kwargs(floor_z=floor, clear_height=clear,
                                              floor_shade=38 if wet else 40))
        rooms[name] = made
        return made

    notes = {name: note for name, *_r, note in BRANCHES}
    notes.update({name: note for name, *_r, note in CHAMBERS})
    notes.update({name: note for name, *_r, note in NECKS})
    entries = plan()
    for entry in entries:
        if entry["kind"] in ("chamber", "neck", "niche") and entry["name"] not in BRANCH_ROOMS:
            continue
        build(entry, notes.get(entry.get("corridor") or entry["name"],
                               f"sewer: {entry['name'].replace('_', ' ')}"))

    def join(a, fa, b, fb, tag):
        citytree.join(rooms[a], rooms[b], at_a=fa, at_b=fb,
                      connection_id=f"connection:sewer_{tag}_{a}_{fa}_{b}")

    # each corridor: its walks onto its channel, piece to piece, ends to what they meet
    by_corridor = {}
    for e in entries:
        if e.get("corridor"):
            by_corridor.setdefault(e["corridor"], []).append(e)
    for channel, members in by_corridor.items():
        _c, _rect, axis, walks, _part, low_end, high_end = corridor_of[channel]
        f = _FACES[axis]
        ends = {"start": [channel], "end": [channel]}
        for side in ("low", "high"):
            pieces = [e for e in members if e.get("side") == side]
            for e in pieces:
                own = f["high"] if side == "low" else f["low"]
                join(e["name"], own, channel, f[side], "strip")
            for a, b in zip(pieces, pieces[1:]):
                join(a["name"], f["end"], b["name"], f["start"], "walk")
            ends["start"].append(pieces[0]["name"])
            ends["end"].append(pieces[-1]["name"])
        for which, meets in (("start", low_end), ("end", high_end)):
            if meets is None:
                continue
            other, other_face = meets
            if other in corridor_of and other_face in (_FACES[corridor_of[other][2]]["low"],
                                                      _FACES[corridor_of[other][2]]["high"]):
                # it enters the other corridor from the side: through its ford
                target = next(e["name"] for e in entries if e["kind"] == "ford"
                              and e["corridor"] == other and e["branch"] == channel)
            else:
                target = other
            for strip in ends[which]:
                join(strip, f[which], target, other_face, "end")
    # a ford is in the walk's line: onto the walk pieces either side of it
    for e in entries:
        if e["kind"] != "ford":
            continue
        f = _FACES[e["axis"]]
        line = [p for p in entries if p.get("walk") == e["walk"]]
        index = line.index(e)
        if index > 0:
            join(line[index - 1]["name"], f["end"], e["name"], f["start"], "ford")
        if index + 1 < len(line):
            join(e["name"], f["end"], line[index + 1]["name"], f["start"], "ford")
    # a branch that is a room: onto the end of the corridor it opens from
    for name, x0, y0, x1, y1, other, other_face, own, _part, _note in BRANCHES:
        if name not in BRANCH_ROOMS:
            continue
        _c, _rect, axis, _walks, _p, _l, _h = corridor_of[other]
        which = "start" if _FACES[axis]["start"] == other_face else "end"
        strips = [other] + [p["name"] for p in entries
                            if p.get("corridor") == other and p["kind"] in ("walk", "ford")]
        line_ends = []
        for side in ("low", "high"):
            pieces = [p["name"] for p in entries if p.get("corridor") == other and p.get("side") == side]
            line_ends.append(pieces[0] if which == "start" else pieces[-1])
        for strip in [other] + line_ends:
            join(strip, other_face, name, own, "room")

    for entry in entries:
        if entry["kind"] not in ("chamber", "neck") or entry["name"] in BRANCH_ROOMS:
            continue
        build(entry, notes.get(entry["name"], ""))
    for name, x0, y0, x1, y1, own, leg, leg_face, _note in CHAMBERS:
        at = (y0 + y1) / 2 if leg_face in ("east", "west") else (x0 + x1) / 2
        target = edge(rooms, leg, leg_face, at)
        RESOLVED[(name, own)] = (target, leg_face)
        citytree.join(rooms[name], target, at_a=own, at_b=leg_face,
                      connection_id=f"connection:sewer_{name}")
    for name, x0, y0, x1, y1, joins, _note in NECKS:
        for own_face, other, other_face in joins:
            at = (y0 + y1) / 2 if other_face in ("east", "west") else (x0 + x1) / 2
            target = (edge(rooms, other, other_face, at) if other in rooms or other in corridor_of
                      else existing[other])
            RESOLVED[(name, own_face)] = (target, other_face)
            sewer.connect(rooms[name].face(own_face), target.face(other_face),
                          connection_id=f"connection:{name}_{own_face}")
    rooms["brook_feeder"] = _brook_feeder(parts["ring"], rooms["graves_brook"])
    hall(sewer, rooms)
    secret_rooms(sewer, rooms)
    spider_lair(sewer, rooms)
    # the niches, into the outer wall of the walk piece they stand beside
    for entry in entries:
        if entry["kind"] != "niche":
            continue
        build(entry, f"a {entry['niche']} niche off the {entry['of'].replace('_', ' ')}")
        axis = corridor_of[entry["of"]][2]
        outer = _FACES[axis][entry["side"]]
        inner = _FACES[axis]["high" if entry["side"] == "low" else "low"]
        x0, y0, x1, y1 = entry["rect"]
        at = (x0 + x1) / 2 if axis == "x" else (y0 + y1) / 2
        target = edge(rooms, entry["of"], outer, at)
        RESOLVED[(entry["name"], inner)] = (target, outer)
        citytree.join(rooms[entry["name"]], target, at_a=inner, at_b=outer,
                      connection_id=f"connection:sewer_{entry['name']}")
    stockyard_side_rooms(sewer, rooms)
    stockyard_trolley(city, sewer, rooms)
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
    out = {e["name"]: tuple(v * PU for v in e["rect"]) for e in plan()}
    out.update({n: (x0 * PU, y0 * PU, x1 * PU, y1 * PU) for n, x0, y0, x1, y1, _k in HALL})
    out.update({r[0]: tuple(v * PU for v in r[1:5]) for r in SECRET_ROOMS})
    out.update({n: tuple(v * PU for v in r) for n, r in lair_rects().items()})
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
    placed += dress_niches(layout, rooms)
    placed += dress_circle(layout, rooms)
    placed += dress_secrets(layout, rooms, attested)
    placed += dress_lair(layout, rooms, attested)
    placed += dress_stockyard(layout, rooms)
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
    # The corridors' outer walks carry low details below the vault.
    "n_walk": ("north", (), "walkside"),
    "s_walk": ("south", (), "walkside"),
    "e_leg_walk_e": ("east", (), "walkside"),
    "w_leg_walk_w": ("west", (), "walkside"),
    "w_leg_walk_w_2": ("west", (), "walkside"),
    "graves_brook_walk_a": ("north", (), "walkside"),
    "graves_brook_walk_b": ("south", (), "walkside"),
    "gallery_walk_a": ("north", (), "walkside"),
    "outfall_walk_a": ("west", (), "walkside"),
    "outfall_walk_b": ("east", (), "walkside"),
}


def ledges(sewer, rooms, *, grade: int, host_clear: int) -> dict:
    """No towpaths: every corridor has a walk each side of its channel now (E3M3's section, `plan`)."""
    return {"legs": 0, "runs": 0, "modules": 0}


def cover_manholes(layout, mouths: dict) -> list[str]:
    """Lay each manhole's cover over its shaft: one flat drain, blocking, at street level."""
    from l3_foundry import _attested
    from resolution import PROFILE

    source, type_id, tile = MANHOLE_COVER["source"]
    spec = _attested(source, type_id, picnum=tile)
    # Use the metal grate break from E3M4 in place of E4M9's record scratch.
    spec = {**spec, "behavior": {**spec["behavior"], "data_4": 314}}
    placed = []
    for name, upper in sorted(mouths.items()):
        size = next(m[3] for m in MANHOLES if m[0] == name)
        layout.place_on_floor(
            f"sewer:{name}_cover", upper.region_id,
            # the middle of the shaft (local is a share of the room)
            local=(0.5, 0.5),
            # the shaft's floor is the recess below the street: the cover
            # lies across its rim, at the street's own level
            height_player_heights=MANHOLE_RECESS / PROFILE.standing_height,
            type=MANHOLE_COVER["type"], picnum=MANHOLE_COVER["picnum"],
            cstat=MANHOLE_COVER["cstat"], x_repeat=MANHOLE_COVER["repeat"],
            y_repeat=MANHOLE_COVER["repeat"], angle=1536, shade=16,
            # on the thing list (4), as every campaign breakable is: damage
            # reaches only dudes and things (actor.cpp actRadiusDamage, 2728
            # and 2762), and on status 0 the owner found "Manhole covers
            # can't be destroyed by explosion".
            status=4,
            behavior=dict(spec["behavior"]))
        placed.append(name)
    return placed


#: What each niche holds: (a campaign map, its type, its tile, where in the
#: niche (along, across from the walk), how it is placed). Every record is
#: copied from that map (`l3_foundry._attested`); the cart wheel was E3M3's
#: valve switch and stands here as decoration.
NICHE_DRESS = {
    "valve": [("E3M3", 20, 982, (0.5, 0.9), "wall")],
    # the skeleton at the campaign's size, its feet a little over the
    # niche's floor and its chain running up into the ceiling (the owner,
    # 2026-11-21: "That skeleton on chain can be lifted up so part of the
    # chain goes inside ceiling")
    "bones": [("E1M2", 416, 689, (0.5, 0.55), "hang", {"rise": 0.04, "x_repeat": 60, "y_repeat": 60}),
              ("E1M2", 417, 515, (0.3, 0.5), "floor")],
    # both barrels' art stands on its middle: lifted by half its drawn
    # height, or half of each is under the floor
    "barrels": [("E1M2", 417, 925, (0.3, 0.6), "floor", {"lift": True}),
                ("E3M4", 416, 201, (0.7, 0.6), "floor", {"lift": True})],
    "pipes": [("E3M3", 0, 54, (0.3, 0.9), "wall"), ("E3M3", 0, 54, (0.7, 0.9), "wall")],
}


def dress_niches(layout, rooms) -> list[str]:
    """Put each niche's things in it."""
    import props
    from l3_foundry import _attested

    placed = []
    for name, rect, channel, side, kind in _niches():
        room = rooms.get(name)
        if room is None:
            continue
        x0, y0, x1, y1 = rect
        axis = "x" if (x1 - x0) > (y1 - y0) else "y"
        for index, (source, type_id, tile, (along, back), how, *more) in enumerate(NICHE_DRESS[kind]):
            try:
                spec = _attested(source, type_id, picnum=tile)
            except LookupError:
                continue
            fields = dict(spec["fields"])
            extra = dict(more[0]) if more else {}
            lift = extra.pop("lift", False)
            rise = extra.pop("rise", 0.0)
            fields.update(extra)
            height = float(rise)
            if lift:
                import wallplane
                from resolution import PROFILE
                tile_h = wallplane.art()[tile][1]
                height = tile_h * fields["y_repeat"] * 4 / 2 / PROFILE.standing_height
            if type_id == 20:
                fields["type"] = 0              # a wheel to see, not a switch
            # local is (x, y) within the niche: `along` runs with the
            # corridor, `back` from the walk toward the back wall
            near_walk = {("x", "low"): 1.0, ("x", "high"): 0.0, ("y", "low"): 1.0, ("y", "high"): 0.0}
            across = back if near_walk[(axis, side)] == 0.0 else 1.0 - back
            local = (along, across) if axis == "x" else (across, along)
            pid = f"sewer:{name}_{index}"
            if how == "hang":
                floor = SEWER_FLOOR - NICHE_RISE
                _hang(layout, pid, room, rect, local, fields, spec, floor,
                      floor - NICHE_CLEAR_OF.get(kind, NICHE_CLEAR), height)
                placed.append(pid)
                continue
            if how == "ceiling":
                layout.place_on_ceiling(pid, room.region_id, local=local, **fields,
                                        behavior=dict(spec["behavior"]))
            elif how == "wall":
                import wallplane
                # the back wall, wound so the sprite faces into the niche
                wx0, wy0, wx1, wy1 = (int(v * PU) for v in rect)
                a1, a2 = {("x", "low"): ((wx0, wy0), (wx1, wy0)), ("x", "high"): ((wx1, wy1), (wx0, wy1)),
                          ("y", "low"): ((wx0, wy1), (wx0, wy0)),
                          ("y", "high"): ((wx1, wy0), (wx1, wy1))}[(axis, side)]
                heights = {982: 0.55, 54: 0.75}
                got = wallplane.sprite(
                    layout, pid, room.region_id, a1, a2, tile=tile,
                    x_repeat=fields["x_repeat"], y_repeat=fields["y_repeat"],
                    cstat=fields["cstat"], t=along, height_player_heights=heights.get(tile, 0.6),
                    offset_player_widths=0.02, shade=-8 if tile == 982 else 0)
                if got:
                    placed.append(pid)
                continue
            else:
                layout.place_on_floor(pid, room.region_id, local=local, **fields,
                                      height_player_heights=height,
                                      behavior=dict(spec["behavior"]))
            placed.append(pid)
    return placed


def _hang(layout, pid, room, rect, local, fields, spec, floor, ceiling, rise) -> None:
    """A thing on a chain, its feet `rise` bodies over the floor; the chain may run up into the ceiling."""
    from bloodmap.placement import drawn_extent
    from bloodmap.shade_table import _art
    from resolution import PROFILE
    art = _art()[fields["picnum"]]
    _top, bottom = drawn_extent(art.height, int(art.animation["yofs"]),
                                int(fields["y_repeat"]), int(fields["cstat"]), 0)
    wx0, wy0, wx1, wy1 = (v * PU for v in rect)
    layout.add_sprite(pid, room.region_id,
                      x=int(wx0 + local[0] * (wx1 - wx0)), y=int(wy0 + local[1] * (wy1 - wy0)),
                      z=int(max(ceiling, floor - rise * PROFILE.standing_height - bottom)),
                      **fields, behavior=dict(spec["behavior"]))


#: What is in the secret rooms: (room, a campaign map, its type, its tile,
#: where in the room, how). Bones are E1M2's (its crypts); the finds are
#: what a secret in Blood gives, a doctor's bag and a life seed.
SECRET_DRESS = [
    ("molly_nest", "E1M2", 417, 515, (0.25, 0.3), "floor"),
    ("molly_nest", "E1M2", 417, 515, (0.75, 0.75), "floor"),
    ("molly_nest", "E1M2", 417, 515, (0.4, 0.85), "floor"),
    ("plague_pit", "E1M2", 417, 515, (0.2, 0.4), "floor"),
    ("plague_pit", "E1M2", 417, 515, (0.35, 0.8), "floor"),
    ("plague_pit", "E1M2", 417, 515, (0.7, 0.85), "floor"),
    ("plague_pit", "E1M2", 417, 515, (0.85, 0.45), "floor"),
    ("plague_pit", "E1M2", 416, 689, (0.25, 0.65), "hang"),
    ("plague_pit", "E1M2", 416, 689, (0.75, 0.6), "hang"),
]
#: (room, type, where): Molly herself, and what each room gives
SECRET_FINDS = [
    ("molly_nest", 217, (0.6, 0.55)),       # gill beast
    ("molly_nest", 107, (0.2, 0.75)),       # doctor's bag
    ("plague_pit", 110, (0.5, 0.7)),        # life seed
]
#: The crack on the brook's side of the seal, and the charges behind it
#: (`l3_church.CRACK`: a wall crack, which only a blast breaks).
SEAL_CRACK = {"type": 408, "picnum": 1127, "cstat": 16 | 64 | 128, "x_repeat": 64,
              "y_repeat": 64, "status": 4}
SEAL_CHARGES = (((0.4, 0.06), 1), ((0.5, 0.1), 3), ((0.6, 0.06), 2))


def dress_secrets(layout, rooms, attested) -> list[str]:
    """Bones, Molly and the finds in the secret rooms; the crack and charges at the seal."""
    import wires
    from bloodmap import wiring
    from l3_foundry import _attested

    placed = []
    rects = {r[0]: r[1:5] for r in SECRET_ROOMS}
    sunk = {r[0]: r[5] for r in SECRET_ROOMS}
    clear = {r[0]: r[6] for r in SECRET_ROOMS}
    for index, (name, source, type_id, tile, local, how) in enumerate(SECRET_DRESS):
        if name not in rooms:
            continue
        try:
            spec = _attested(source, type_id, picnum=tile)
        except LookupError:
            continue
        pid = f"sewer:secret_{name}_{index}"
        fields = dict(spec["fields"])
        if how == "hang":
            floor = SEWER_FLOOR + sunk[name]
            _hang(layout, pid, rooms[name], rects[name], local, fields, spec,
                  floor, floor - clear[name], 0.15)
        else:
            layout.place_on_floor(pid, rooms[name].region_id, local=local, **fields,
                                  behavior=dict(spec["behavior"]))
        placed.append(pid)
    for name, type_id, local in SECRET_FINDS:
        spec = attested(type_id)
        if spec is None or name not in rooms:
            continue
        pid = f"sewer:secret_{name}_{type_id}"
        layout.place_on_floor(pid, rooms[name].region_id, local=local, **spec["fields"])
        placed.append(pid)
    if "plague_pit" in rooms:
        channel = wires.channel("sewer:plague-pit")
        x0, y0, x1, y1 = (v * PU for v in rects["plague_seal"])
        walk = edge(rooms, "graves_brook", "south", (rects["plague_seal"][0] + rects["plague_seal"][2]) / 2)
        # the walk's south wall runs east to west
        layout.place_on_wall(
            "sewer:plague_crack", walk.region_id, a1=(int(x1) + 1024, int(y0)), a2=(int(x0) - 1024, int(y0)),
            t=0.5, height_player_heights=0.6, offset_player_widths=0.04, spans_opening=True,
            **SEAL_CRACK, behavior={"tx_id": channel, "command": 1, "trigger_on": 1,
                                    "trigger_off": 1, "trigger_once": 1})
        wires.wire("sewer:plague-pit").when(
            wiring.placement("sewer:plague_crack"), "destroyed", command=1,
            on=True, off=True, once=True)
        placed.append("sewer:plague_crack")
        for index, (local, wait) in enumerate(SEAL_CHARGES):
            pid = f"sewer:plague_charge_{index}"
            layout.place_on_floor(
                pid, rooms["plague_pit"].region_id, local=local,
                type=459, picnum=908, cstat=128, x_repeat=4, y_repeat=64,
                status=11, behavior={"rx_id": channel, "wait_time": wait})
            wires.wire("sewer:plague-pit").then(wiring.placement(pid))
            placed.append(pid)
    return placed


#: The lair's things, every one E2M8's own record (`l3_foundry._attested`):
#: (what, type, tile). E2M8's victims are wired to its ending; these are not.
LAIR_THINGS = {
    "web": (410, 1069), "cocoon": (0, 1061), "torn": (0, 1058), "victim": (416, 1059),
    "mother": (216, 1930), "spider": (213, 1920), "fringe": (0, 1068),
}
#: where in the hall (a share of its bounding box): the spiders on the
#: ceiling, the victims hanging, the mother at the back
LAIR_SPIDERS = [(0.25, 0.35), (0.45, 0.2), (0.7, 0.3), (0.8, 0.6), (0.35, 0.65), (0.6, 0.75)]
LAIR_MOTHER = (0.35, 0.3)
#: (where, what): three rounds of readers read E2M8's wrapped victim (1059)
#: as a post, a column, a palm tree or a light fitting at every length; so
#: one stays, short, and two are E1M2's chained skeletons (416 on 689), their
#: chains run up into the ceiling (the owner: "it doesn't matter")
#: (round 5: the silk sack "floats in mid-air" with no cord; and the
#: skeleton by the way in crowded the first view, so it stands aside)
LAIR_VICTIMS = [((0.3, 0.45), "chained"), ((0.68, 0.5), "chained"), ((0.2, 0.8), "chained")]
#: a victim hangs about half the room: round 1's three readers saw E2M8's
#: repeat (56, made for a room 2.4 bodies high) as columns to the floor
LAIR_VICTIM_REPEAT = (44, 34)
#: the torches (E2M1's 570, type 30): pools of light with dark between, on
#: two opposite corners (round 1: "the whole place is one even murk")
LAIR_TORCHES = [("northwest", 0.5), ("southeast", 0.5)]
#: the cobwebs over the nest's mouth, as the crypt's are (E1M1's: 417 on 1067)
LAIR_MOUTH_WEB = {"type": 417, "picnum": 1067, "cstat": 146, "x_repeat": 48, "y_repeat": 48,
                  "status": 4, "shade": -28, "behavior": {"data_1": 6}}
#: the cocoons' shade: pale against the silk, or they read as carvings in it
LAIR_COCOON_SHADE = -12
#: eggs laid against the pillar's faces, at its foot: round 2-4's comparison
#: readers, "eggs set into the faces of a central pillar" (CHORROR's pillar
#: of egg niches). (the pillar's edge, its repeat)
LAIR_PILLAR_EGGS = [(0, 34), (2, 28), (4, 38), (6, 26)]
#: torn silk at the mouths and on the pillar: E2M8's sheet runs its room's
#: whole height (32,768 at repeat 64); here it is a ragged sheet two thirds
#: of the wall, so it reads as silk and not as a grey slab
LAIR_TORN_REPEAT = (48, 40)
#: web hanging along the hall's walls at the ceiling: (face, share along it)
#: (the walls either side of an alcove's mouth wear its torn silk instead)
LAIR_FRINGES = [("northwest", 0.3), ("northeast", 0.5), ("southwest", 0.5), ("southeast", 0.25),
                ("south", 0.15), ("south", 0.85)]
#: on the floor: E1M2's bones, and the find (a bundle of TNT, for the
#: plague pit's crack)
LAIR_BONES = [(0.2, 0.7), (0.75, 0.4), (0.4, 0.62), (0.62, 0.2), (0.85, 0.75), (0.3, 0.15)]
#: E1M2's bones (515) lie flat (cstat 32) and vanish into dark earth: round
#: 2's readers found none. The skulls stand: E2M1 sprite 164, a pile of them
LAIR_SKULLS = [(0.18, 0.62), (0.78, 0.3), (0.62, 0.82)]
#: in front of the eggs, by the nest's mouth, where a player steps in
#: a box of TNT (63, the bigger pickup) on the hall's floor at the east
#: nest's mouth: round 3's readers could not find the bundle inside it
LAIR_FIND = ("lair_hall", 63, (0.93, 0.5))
#: what each nest gives, deep among its eggs (round 5's use reader:
#: "something worth taking in the nests ... so they are worth entering"):
#: a life essence in the north nest, shells and a gasoline can at the sides
#: (E2M8's lair gives gasoline). (nest, type, (share across, share deep))
LAIR_NEST_FINDS = [("brood_nest", 109, (0.5, 0.85)), ("brood_west", 67, (0.5, 0.85)),
                   ("brood_east", 79, (0.35, 0.85))]
#: webs flat on the two corner walls that hold no torch, high, as the corpus
#: hangs 91 of its webs on solid walls (`work/spider/webs.py`; cstat 465)
LAIR_CORNER_WEBS = ["northeast", "southwest"]
#: strands cascading inside each nest from its ceiling, at the back
LAIR_NEST_STRANDS = (0.2, 0.8)


def _lair_sprite(layout, pid, room, x, y, fields, spec, *, top=None, bottom=None, z=None, **more):
    """One of the lair's things at (x, y), its drawn top or bottom at a height, or its origin at `z`."""
    from bloodmap.placement import drawn_extent
    from bloodmap.shade_table import _art

    fields = {k: v for k, v in {**fields, **more}.items() if k != "behavior"}
    if z is None:
        art = _art()[int(fields["picnum"])]
        up, down = drawn_extent(art.height, int(art.animation["yofs"]), int(fields["y_repeat"]),
                                int(fields["cstat"]), 0)
        z = top - up if top is not None else bottom - down
    # the layout keeps an origin inside its room: the art may hang above it
    z = max(z, SEWER_FLOOR - LAIR_CLEAR + 16)
    layout.add_sprite(pid, room.region_id, x=int(x), y=int(y), z=int(z), **fields,
                      behavior=dict(spec["behavior"]))
    return pid


def dress_stockyard(layout, rooms) -> list[str]:
    """Dress the intake and altar, and tint the running water all the way to the Main."""
    from bloodmap.placement import drawn_extent
    from bloodmap.shade_table import _art
    from l3_foundry import _attested

    # SPIDER1.PLU (7) draws tile 1120's greens in red-brown. The race is the
    # ring's own water as far as the carcass rack, and blood from there down.
    race = rooms["stockyard_drain"].region_id
    xs, ys = zip(*layout.regions[race].outer)
    top = round(RACE_BLOOD_FROM * PU)
    layout.add_overlay("blood:stockyard_drain", race,
                       [(min(xs), top), (max(xs), top), (max(xs), max(ys)), (min(xs), max(ys))],
                       floor_pal=7)

    placed = []

    def seat(room_name, name, source, point, *, from_ceiling=None, **overrides):
        if name == "stockyard_outlet":
            room_name, point = "trolley_tail", (54.125, 61.0 - 8 / PU)
            from_ceiling = 768
            overrides.update(x_repeat=66, y_repeat=58)
        region = layout.regions[rooms[room_name].region_id]
        source_map, type_id, tile = source
        spec = _attested(source_map, type_id, picnum=tile)
        fields = dict(spec["fields"], **overrides)
        art = _art()[tile]
        top, bottom = drawn_extent(art.height, art.animation["yofs"],
                                   fields["y_repeat"], fields["cstat"])
        z = (region.floor_z - 8 - bottom if from_ceiling is None
             else region.ceiling_z + from_ceiling - top)
        x, y = (round(v * PU) for v in point)
        placed.append(layout.add_sprite(f"sewer:{name}", region.region_id, x=x, y=y, z=z,
                                        behavior=dict(spec["behavior"]), **fields))

    # A stained outlet sits high on the south wall. The rack is off the
    # walk so the hooks and bodies stay clear of the manhole's landing.
    seat("stockyard_drain", "stockyard_outlet", ("E1M8", 0, 977), (49.75, 55.75 - 8 / PU),
         from_ceiling=5120, angle=1536, x_repeat=84, y_repeat=70, shade=-8)
    seat("stockyard_rack", "stockyard_hook", ("E1M8", 417, 692), (47.875, 52.25),
         from_ceiling=128, x_repeat=42, y_repeat=42)
    # the rack bleeds across the walk into the race
    seat("stockyard_drain_walk_a", "stockyard_bleed", ("E2M4", 0, 713), (49.0, 52.75),
         x_repeat=40, y_repeat=40, cstat=32, shade=8)
    for i, point in enumerate(((48.125, 53.0), (47.875, 53.75))):
        seat("stockyard_rack", f"stockyard_carcass_{i}", ("E3M2", 416, 1351), point,
             from_ceiling=256, x_repeat=48, y_repeat=42)

    candle = ("E1M5", 32, 938)
    seat("rat_king_pipe", "rat_king_clue", candle, (51.375, 46.4375),
         x_repeat=32, y_repeat=36, cstat=384, shade=-16)
    for i, point in enumerate(((55.875, 45.875), (55.875, 47.875), (56.5, 45.875), (56.5, 47.875))):
        seat("rat_king_altar", f"rat_king_candle_{i}", candle, point,
             x_repeat=42, y_repeat=48, cstat=384, shade=-16)
    seat("rat_king_altar", "rat_king_plaque", ("E1M5", 0, 187), (56.75 - 8 / PU, 46.875),
         from_ceiling=6656, cstat=144, angle=1024, x_repeat=102, y_repeat=102, shade=-12)
    seat("rat_king_altar", "rat_king_blood", ("E2M4", 0, 713), (56.25, 46.875),
         x_repeat=50, y_repeat=50, cstat=32, shade=-16)
    for i, (point, tile, cstat) in enumerate((
            ((56.34, 46.55), 1743, 384), ((56.13, 47.06), 1744, 388),
            ((56.54, 46.88), 1743, 388))):
        seat("rat_king_altar", f"rat_king_rat_{i}", ("E1M4", 0, tile), point,
             x_repeat=23, y_repeat=30, cstat=cstat, shade=-10)
    seat("rat_king_altar", "rat_king_offering", ("E1M4", 109, 2169), (55.93, 47.56),
         shade=-6)
    return placed


def dress_lair(layout, rooms, attested) -> list[str]:
    """The lair's web, cocoons, victims, spiders and their mother, as E2M8 dresses its own."""
    import math

    import wallplane
    from l3_foundry import _attested

    if "lair_hall" not in rooms:
        return []
    spec = {k: _attested("E2M8", t, picnum=p) for k, (t, p) in LAIR_THINGS.items()}
    fields = {k: dict(v["fields"]) for k, v in spec.items()}
    placed = []
    hall_room = rooms["lair_hall"]
    hx0, hy0, hx1, hy1 = (v * PU for v in lair_rects()["lair_hall"])
    ceiling = SEWER_FLOOR - LAIR_CLEAR

    def at(local):
        return hx0 + local[0] * (hx1 - hx0), hy0 + local[1] * (hy1 - hy0)

    # the web across the passage's mouth, the plane across it, to its height
    px0, py0, px1, py1 = (v * PU for v in LAIR_PASSAGE)
    tile_w = 128
    # As the corpus hangs its webs (`work/spider/webs.py`, 693 of them on
    # 1069 in 207 maps; the owner, 2026-11-22: "Check web in other levels
    # what are we doing wrong"): OPAQUE, cstat 401, the commonest (212; only
    # 181 of 693 are translucent, E2M8's 915 among them); and ON THE
    # OPENING'S LINE at the opening's full width, its foot on the floor (117
    # hang on an opening's line, the commonest way across). E2M8's
    # translucent web, hung inside the passage, let the floor show through
    # it, and four blind readers read it as a decal lying on the floor.
    web = dict(fields["web"], angle=512, cstat=401, x_repeat=int((px1 - px0) * 4 / tile_w),
               y_repeat=int(LAIR_PASSAGE_CLEAR * 0.9 / 4 / 128))
    placed.append(_lair_sprite(layout, "sewer:lair_web", rooms["lair_passage"], (px0 + px1) / 2,
                               py1 - 8, web, spec["web"], bottom=SEWER_FLOOR - 256))
    outline = [(x * PU, y * PU) for x, y in LAIR_HALL]

    def on_face(face, point, off):
        """A point on the hall's `face`, nearest `point`, `off` in from it; and the angle facing in."""
        index = LAIR_HALL_FACES[face]
        (ax, ay), (bx, by) = outline[index], outline[(index + 1) % len(outline)]
        length = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / length, (by - ay) / length
        t = max(0.0, min(length, (point[0] - ax) * ux + (point[1] - ay) * uy))
        nx, ny = -uy, ux                                   # inward: left of the wound edge
        angle = int(round(math.atan2(ny, nx) / (2 * math.pi) * 2048)) % 2048
        return ax + ux * t + nx * off, ay + uy * t + ny * off, angle

    # the brood alcoves: their cocoons, pale, of their sizes; silk torn
    # across the hall's wall either side of each mouth
    for name, x0, y0, x1, y1, face, rise, clear, eggs in LAIR_ALCOVES:
        room = rooms[name]
        wx0, wy0, wx1, wy1 = (v * PU for v in (x0, y0, x1, y1))
        floor = SEWER_FLOOR - rise
        for k, (u, v, repeat) in enumerate(eggs):
            # `v` is how deep: from the mouth toward the back wall
            ex, ey = {"north": (wx0 + u * (wx1 - wx0), wy1 - v * (wy1 - wy0)),
                      "west": (wx1 - v * (wx1 - wx0), wy0 + u * (wy1 - wy0)),
                      "east": (wx0 + v * (wx1 - wx0), wy0 + u * (wy1 - wy0))}[face]
            placed.append(_lair_sprite(layout, f"sewer:lair_{name}_cocoon_{k}", room, ex, ey,
                                       dict(fields["cocoon"], x_repeat=repeat, y_repeat=repeat,
                                            shade=LAIR_COCOON_SHADE),
                                       spec["cocoon"], bottom=floor - 256))
        # (no torn silk on the jambs: three rounds read it as flat panels)
        # every nest's mouth: cobwebs hung across its lintel
        mouth_top = floor - clear
        mouth = ([(wx0 + share * (wx1 - wx0), wy1) for share in (0.2, 0.5, 0.8)] if face == "north"
                 else [(wx1 if face == "west" else wx0, wy0 + share * (wy1 - wy0)) for share in (0.25, 0.75)])
        for k, point in enumerate(mouth):
            x, y, angle = on_face(face, point, 40)
            placed.append(_lair_sprite(layout, f"sewer:lair_{name}_mouthweb_{k}", hall_room, x, y,
                                       dict(LAIR_MOUTH_WEB, angle=angle), LAIR_MOUTH_WEB,
                                       top=mouth_top - 256))
        # and strands cascading inside, hung from the nest's ceiling at its
        # back, long (E2M8's fringe 1068 at 56; round 5: "cascading webs")
        for k, share in enumerate(LAIR_NEST_STRANDS):
            sx, sy = {"north": (wx0 + share * (wx1 - wx0), wy0 + 128),
                      "west": (wx0 + 128, wy0 + share * (wy1 - wy0)),
                      "east": (wx1 - 128, wy0 + share * (wy1 - wy0))}[face]
            back = {"north": 512, "west": 0, "east": 1024}[face]      # facing out of the nest
            placed.append(_lair_sprite(layout, f"sewer:lair_{name}_strand_{k}", room, sx, sy,
                                       dict(fields["fringe"], angle=back, y_repeat=48), spec["fringe"],
                                       top=mouth_top + 64))
        if face == "north":
            # and over the north one, the carved spider (E1M5 sprite 421's
            # record, smaller)
            panel = _attested("E1M5", 417, picnum=314)
            x, y, angle = on_face(face, ((wx0 + wx1) / 2, wy1), 16)
            band = mouth_top - ceiling
            placed.append(_lair_sprite(layout, f"sewer:lair_{name}_panel", hall_room, x, y,
                                       dict(panel["fields"], angle=angle, x_repeat=34, y_repeat=34),
                                       panel, bottom=mouth_top - band // 2 + 34 * 64 * 2))
    # eggs at the pillar's foot, against its faces, pale in the dark
    pillar = [(x * PU, y * PU) for x, y in LAIR_PILLAR]
    pcx = sum(p[0] for p in pillar) / len(pillar)
    pcy = sum(p[1] for p in pillar) / len(pillar)
    for k, (edge_index, repeat) in enumerate(LAIR_PILLAR_EGGS):
        (ax, ay), (bx, by) = pillar[edge_index], pillar[(edge_index + 1) % len(pillar)]
        mx, my = (ax + bx) / 2, (ay + by) / 2
        norm = math.hypot(mx - pcx, my - pcy)
        half = 72 * repeat / 8                     # the egg's half width (72 wide)
        ex, ey = mx + (mx - pcx) / norm * (half * 0.6), my + (my - pcy) / norm * (half * 0.6)
        placed.append(_lair_sprite(layout, f"sewer:lair_pillar_egg_{k}", hall_room, ex, ey,
                                   dict(fields["cocoon"], x_repeat=repeat, y_repeat=repeat,
                                        shade=LAIR_COCOON_SHADE),
                                   spec["cocoon"], bottom=SEWER_FLOOR - 128))
    # (no silk on the pillar: round 2's comparison reader saw it "smeared")
    for k, side in enumerate(()):
        (ax, ay), (bx, by) = pillar[side], pillar[(side + 1) % len(pillar)]
        length = math.hypot(bx - ax, by - ay)
        cx, cy = sum(p[0] for p in pillar) / len(pillar), sum(p[1] for p in pillar) / len(pillar)
        mx, my = (ax + bx) / 2, (ay + by) / 2
        nx, ny = (mx - cx), (my - cy)
        norm = math.hypot(nx, ny)
        nx, ny = nx / norm, ny / norm
        angle = int(round(math.atan2(ny, nx) / (2 * math.pi) * 2048)) % 2048
        placed.append(_lair_sprite(layout, f"sewer:lair_pillar_silk_{k}", hall_room, mx + nx * 24,
                                   my + ny * 24, dict(fields["torn"], angle=angle, x_repeat=36,
                                                      y_repeat=LAIR_TORN_REPEAT[1]), spec["torn"],
                                   bottom=SEWER_FLOOR - 512))
    # the torches: E2M1's, on two opposite corners
    torch = _attested("E2M1", 30, picnum=570)
    for k, (face, share) in enumerate(LAIR_TORCHES):
        index = LAIR_HALL_FACES[face]
        (ax, ay), (bx, by) = outline[index], outline[(index + 1) % len(outline)]
        x, y, _angle = on_face(face, (ax + (bx - ax) * share, ay + (by - ay) * share), 96)
        placed.append(_lair_sprite(layout, f"sewer:lair_torch_{k}", hall_room, x, y,
                                   dict(torch["fields"]), torch, bottom=SEWER_FLOOR - 15360))
    # spiders and their mother on the ceiling, upside down (E2M8's records),
    # each with its drawn top against it (round 1: the mother "hangs in the
    # air under the ceiling")
    for k, local in enumerate(LAIR_SPIDERS):
        x, y = at(local)
        placed.append(_lair_sprite(layout, f"sewer:lair_spider_{k}", hall_room, x, y, fields["spider"],
                                   spec["spider"], top=ceiling + 32))
    x, y = at(LAIR_MOTHER)
    placed.append(_lair_sprite(layout, "sewer:lair_mother", hall_room, x, y, fields["mother"],
                               spec["mother"], top=ceiling + 32))
    from caleb import spider_mother
    spider_mother(layout, hall_room.region_id, placed[-1], int(x), int(y))
    # the dead: one wrapped, two on chains
    chained = _attested("E1M2", 416, picnum=689)
    for k, (local, kind) in enumerate(LAIR_VICTIMS):
        x, y = at(local)
        if kind == "chained":
            _hang(layout, f"sewer:lair_victim_{k}", hall_room, lair_rects()["lair_hall"], local,
                  dict(chained["fields"], x_repeat=60, y_repeat=60), chained, SEWER_FLOOR, ceiling, 0.2)
            placed.append(f"sewer:lair_victim_{k}")
            continue
        # four rounds of readers never read E2M8's wrapped victim (1059) as
        # a body; a cocoon hung from the ceiling, a sack of silk, instead
        placed.append(_lair_sprite(layout, f"sewer:lair_victim_{k}", hall_room, x, y,
                                   dict(fields["cocoon"], x_repeat=30, y_repeat=30,
                                        shade=LAIR_COCOON_SHADE),
                                   spec["cocoon"], top=ceiling + 64))
    # web along the walls at the ceiling, a little in from each wall, facing in
    for k, (face, t) in enumerate(LAIR_FRINGES):
        index = LAIR_HALL_FACES[face]
        (ax, ay), (bx, by) = outline[index], outline[(index + 1) % len(outline)]
        length = math.hypot(bx - ax, by - ay)
        nx, ny = -(by - ay) / length, (bx - ax) / length     # inward: left of the wound edge
        x, y = ax + (bx - ax) * t + nx * 48, ay + (by - ay) * t + ny * 48
        angle = int(round(math.atan2(ny, nx) / (2 * math.pi) * 2048)) % 2048
        placed.append(_lair_sprite(layout, f"sewer:lair_fringe_{k}", hall_room, x, y,
                                   dict(fields["fringe"], angle=angle), spec["fringe"], top=ceiling + 32))
    # bones on the floor, and the find
    skulls = _attested("E2M1", 417, picnum=684)
    for k, local in enumerate(LAIR_SKULLS):
        layout.place_on_floor(f"sewer:lair_skulls_{k}", hall_room.region_id,
                              local=local, **skulls["fields"], behavior=dict(skulls["behavior"]))
        placed.append(f"sewer:lair_skulls_{k}")
    bones = _attested("E1M2", 417, picnum=515)
    for k, local in enumerate(LAIR_BONES):
        layout.place_on_floor(f"sewer:lair_bones_{k}", hall_room.region_id,
                              local=local, **bones["fields"], behavior=dict(bones["behavior"]))
        placed.append(f"sewer:lair_bones_{k}")
    for name, type_id, (u, v) in LAIR_NEST_FINDS:
        found = attested(type_id)
        nest = next((r for r in LAIR_ALCOVES if r[0] == name), None)
        if found is None or nest is None or name not in rooms:
            continue
        _n, x0, y0, x1, y1, face, rise, *_rest = nest
        # `v` is how deep, from the mouth: as a share of the room's own box
        lx, ly = {"north": (u, 1.0 - v), "west": (1.0 - v, u), "east": (v, u)}[face]
        wx0, wy0, wx1, wy1 = (c * PU for c in (x0, y0, x1, y1))
        # seated by its drawn foot: centred art (cstat 128) sinks by half
        # through `place_on_floor` (the gasoline can did)
        placed.append(_lair_sprite(layout, f"sewer:lair_{name}_find_{type_id}", rooms[name],
                                   wx0 + lx * (wx1 - wx0), wy0 + ly * (wy1 - wy0), dict(found["fields"]),
                                   {"behavior": {}}, bottom=SEWER_FLOOR - rise))
    # webs flat on the corner walls without a torch, their tops at the ceiling
    for k, face in enumerate(LAIR_CORNER_WEBS):
        index = LAIR_HALL_FACES[face]
        (ax, ay), (bx, by) = outline[index], outline[(index + 1) % len(outline)]
        length = math.hypot(bx - ax, by - ay)
        x, y, angle = on_face(face, ((ax + bx) / 2, (ay + by) / 2), 16)
        repeat = int(length * 0.85 * 4 / 128)
        placed.append(_lair_sprite(layout, f"sewer:lair_corner_web_{k}", hall_room, x, y,
                                   dict(fields["web"], angle=angle, cstat=465, x_repeat=repeat,
                                        y_repeat=min(repeat, 40)),
                                   spec["web"], top=ceiling + 64))
    name, type_id, local = LAIR_FIND
    found = attested(type_id)
    if found is not None and name in rooms:
        layout.place_on_floor(f"sewer:lair_find_{type_id}", rooms[name].region_id, local=local,
                              **found["fields"])
        placed.append(f"sewer:lair_find_{type_id}")
    return placed


#: The Cabal's circle on the settling hall's south quay: the owner's standing
#: candelabra (580, three candles, lit -- `light_kinds` counts them as light)
#: in a ring round a pool of blood, and two of its men (E3M3's own cultists).
#: The design: "the summoning is done where all the city's water meets".
CIRCLE = {"centre": (27.5, 49.0), "radius": 768, "stands": 6,
          "stand": 580, "men": [("E3M3", 201, (25.5, 49.3)), ("E3M3", 202, (29.5, 48.7))]}


def dress_circle(layout, rooms) -> list[str]:
    """The circle on the south quay."""
    import math

    import props
    from l3_foundry import _attested

    room = rooms.get("circle_quay")
    if room is None:
        return []
    x0, y0, x1, y1 = next((a, b, c, d) for n, a, b, c, d, _k in HALL if n == "circle_quay")

    def local(x, y):
        return ((x - x0) / (x1 - x0), (y - y0) / (y1 - y0))

    placed = []
    cx, cy = CIRCLE["centre"]
    for k in range(CIRCLE["stands"]):
        a = 2 * math.pi * k / CIRCLE["stands"]
        x = cx + math.cos(a) * CIRCLE["radius"] / PU
        y = cy + math.sin(a) * CIRCLE["radius"] / PU
        pid = f"sewer:circle_stand_{k}"
        layout.place_on_floor(pid, room.region_id, local=local(x, y), **props.fields(CIRCLE["stand"]))
        placed.append(pid)
    layout.place_on_floor("sewer:circle_blood", room.region_id, local=local(cx, cy), **props.fields(956))
    placed.append("sewer:circle_blood")
    for index, (source, type_id, (x, y)) in enumerate(CIRCLE["men"]):
        man = _attested(source, type_id)
        pid = f"sewer:circle_man_{index}"
        layout.place_on_floor(pid, room.region_id, local=local(x, y), **man["fields"],
                              behavior=dict(man["behavior"]))
        placed.append(pid)
    return placed


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

    # The owner's flat round light, 795, lies flush in E3M3's ceilings
    # (sprites 77 and 278). The crown between the slopes seats the lamp.
    for name, positions in (("graves_brook", (0.13, 0.48, 0.83)),
                            ("gallery", (0.18, 0.52, 0.87)),
                            ("e_leg", (0.23, 0.60, 0.85))):
        if name not in rooms:
            continue
        room = rooms[name]
        region = layout.regions[room.region_id]
        x0, y0, x1, y1 = props.room_rect(room)
        for index, t in enumerate(positions):
            u, v = (t, 0.5) if x1 - x0 > y1 - y0 else (0.5, t)
            layout.add_sprite(f"sewer:{name}_vault_lamp_{index}", room.region_id,
                              x=round(x0 + u * (x1 - x0)), y=round(y0 + v * (y1 - y0)),
                              z=region.ceiling_z + 64, picnum=795, cstat=160,
                              x_repeat=48, y_repeat=48, shade=-128)

    attached = {}
    names = {id(room): name for name, room in rooms.items()}
    rects = _rects()
    for (cname, _own), (target, face) in RESOLVED.items():
        if cname not in rects:
            continue
        cx0, cy0, cx1, cy1 = rects[cname]
        attached.setdefault(names.get(id(target)), []).append((face, cx0, cy0, cx1, cy1))

    out = []
    for name, spec in RUN_FACES.items():
        face, extra = spec[0], spec[1]
        kind = spec[2] if len(spec) > 2 else "tunnel"
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
        local = rects.get(name)
        offset = 0 if local is None else (
            (x0 - local[0]) if horizontal else (y0 - local[1]))
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
            elements=sewerkit.elements_for(kind)))
    return out
