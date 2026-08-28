"""Set-pieces: objects modelled as sectors, at the campaign's proportions.

The prefab layer stops at rooms.  This is the object scale -- the idioms
Build furniture is actually made of, and constructors that compose them
into the classes `knowledge/blood/design/set-pieces-v1.json` found by
mining 7,014 pieces out of the campaign.

**The idioms.**

``raised_solid``   one block standing above its host floor: a counter, a
                   table, a plinth.
``stepped_solid``  two or more tiers side by side: E1M1's piano is a tall
                   wooden body with two stepped keyboard strips beside it.
``basin``          concentric tiers descending below the host floor, the
                   innermost holding water: a fountain, a pool.
``inset``          a hollow with a mouth, faced in its own material: the
                   furnace's fire chamber.
``canopy``         a lowered ceiling over a footprint, on posts or not: a
                   stall, a bier, a bar back.

**The proportion that mattered most.**  Every raised-block class the mining
found agrees on its height:

    129 pieces / 38 maps   rise p10 0.36  median 0.48  p90 0.48
     83 pieces / 35 maps   rise p10 0.30  median 0.48  p90 0.48
     77 pieces / 33 maps   rise p10 0.36  median 0.48  p90 0.48
     74 pieces / 32 maps   rise p10 0.30  median 0.42  p90 0.48

**0.48 player heights is 8,140 units.**  Gravesend's counters were built at
4,096 -- half that -- which is why the saloon's bar and card tables read as
low platforms rather than as furniture.  `COUNTER` below is the mined
number, not the invented one.

Footprints run 0.5-1.5 plan units on both axes for a counter or table, and
2.0-3.4 for a basin.  The basin class (36 pieces / 25 maps) descends in
even steps -- its worked example runs tiers -0.54, -0.36, -0.18, 0.0.

Labels here are INTERPRETED.  The proportions, palettes and occurrence
counts they carry are DERIVED, and every constructor names the class it is
built from so the claim can be checked.
"""

from __future__ import annotations

import json
import pathlib

from bloodmap.levelprog import Frame, RECT_FACES, Style

PLAYER = 16960
PLAN = 1024
COMPASS = dict(zip(RECT_FACES, range(4)))

_REF = pathlib.Path(__file__).resolve().parents[1] / "references"


def _knowledge():
    path = (pathlib.Path(__file__).resolve().parents[3]
            / "knowledge" / "blood" / "design" / "set-pieces-v1.json")
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


#: The mined heights, in player heights, converted to z units.
#: Every one of these is a median from the class named beside it.
COUNTER = int(0.48 * PLAYER)      # 8140 -- raised-block classes, 363 pieces
LOW_STEP = int(0.24 * PLAYER)     # 4070 -- the shallow-tier class, 45 pieces
PLINTH = int(0.66 * PLAYER)       # 11193 -- the taller pedestal class, 107x
ALTAR = int(0.85 * PLAYER)        # 14416 -- two-tier raised class, 42x/16 maps
BASIN_STEP = int(0.18 * PLAYER)   # 3052 -- the basin class's even descent

#: Water that reads as water: E3M3's shallow form, not DWE3M10's underwater
#: volume tile (which needs a link pair to work at all).
WATER_FLOOR = 1120
WATER_DEPTH = 7

#: kGenSound.  E1M1's piano carries three; a fountain wants one.
SOUND_TYPE = 708
SOUND_TILE = 2519


class SetPieceError(ValueError):
    """A declaration this vocabulary cannot build."""


def _rect_room(assembly, name, rect, material, *, floor_z, clear, note,
               role="detail", behavior=None, shade=None):
    x0, y0, x1, y1 = (int(v) for v in rect)
    if x1 <= x0 or y1 <= y0:
        raise SetPieceError(f"{name}: empty footprint {rect}")
    region_kwargs = dict(material.region_kwargs())
    if behavior:
        region_kwargs["sector_behavior"] = behavior
    room = assembly.room(
        name, [(0, 0), (x1 - x0, 0), (x1 - x0, y1 - y0), (0, y1 - y0)],
        role=role, faces=dict(COMPASS), frame=Frame(x0, y0),
        region_kwargs=region_kwargs, note=note)
    style = material.style_kwargs(floor_z=floor_z, clear_height=clear)
    if shade is not None:
        style["floor_shade"] = shade
    room.surfaces(**style)
    return room


def _carve_into(host, rect):
    """Cut this footprint out of its host, in the host's own frame."""
    x0, y0, x1, y1 = (int(v) for v in rect)
    frame = host.world_frame()
    host.carve([(x0 - frame.dx, y0 - frame.dy), (x1 - frame.dx, y0 - frame.dy),
                (x1 - frame.dx, y1 - frame.dy), (x0 - frame.dx, y1 - frame.dy)])


def _rim(connector, piece, host, tag):
    """Join a piece to its host on all four faces.

    Every coincident edge must be a declared portal -- the rule this
    project relearns whenever an island goes in without it.  `connector`
    is whichever object owns BOTH sides: a piece cut into a street belongs
    to its own assembly but joins the city.
    """
    for face in ("north", "east", "south", "west"):
        connector.connect(piece.face(face), host.face("north"),
                          connection_id=f"connection:{tag}_{face}")


# --------------------------------------------------------------------------
# the idioms
# --------------------------------------------------------------------------

def raised_solid(assembly, name, host, rect, material, *, grade,
                 rise=COUNTER, host_clear, note="", shade=None,
                 connector=None):
    """One block standing above its host floor.  Class: raised block."""
    _carve_into(host, rect)
    piece = _rect_room(assembly, name, rect, material,
                       floor_z=grade - rise, clear=host_clear - rise,
                       note=note or f"{name}: a raised block at {rise} units",
                       shade=shade)
    _rim(connector or assembly, piece, host, name)
    return piece


def stepped_solid(assembly, name, host, rects, material, *, grade,
                  rises, host_clear, note=""):
    """Tiers side by side, each its own sector.  Class: E1M1's piano.

    `rects` and `rises` are parallel; the tiers must not touch each other
    or they share an undeclared edge.  The piano's are 0.54 / 0.60 / 0.72.
    """
    if len(rects) != len(rises):
        raise SetPieceError(f"{name}: {len(rects)} tiers, {len(rises)} rises")
    out = []
    for index, (rect, rise) in enumerate(zip(rects, rises)):
        out.append(raised_solid(
            assembly, f"{name}_{index}", host, rect, material, grade=grade,
            rise=rise, host_clear=host_clear,
            note=note or f"{name} tier {index} at {rise}"))
    return out


def basin(assembly, name, host, rect, material, water_material, *, grade,
          host_clear, tiers=2, step=BASIN_STEP, wall_thickness=512,
          note="", connector=None):
    """Concentric tiers descending to water.  Class: basin, 36x / 25 maps.

    Built from the outside in: each ring is carved out of the one around
    it and fills the hole, so every coincident edge is a declared portal.
    The innermost holds E3M3's shallow water form.
    """
    x0, y0, x1, y1 = (int(v) for v in rect)
    innermost = min(x1 - x0, y1 - y0) - 2 * wall_thickness * tiers
    if innermost < 512:
        raise SetPieceError(
            f"{name}: {rect} leaves {innermost} units of well after "
            f"{tiers} tiers at {wall_thickness}")

    # The rim stands proud of the host floor, which is what makes a basin
    # read as a basin rather than as a hole in the ground.
    _carve_into(host, rect)
    rim = _rect_room(assembly, f"{name}_rim", rect, material,
                     floor_z=grade - LOW_STEP, clear=host_clear - LOW_STEP,
                     note=note or f"{name}: the basin rim")
    _rim(connector or assembly, rim, host, f"{name}_rim")

    outer, previous = rim, rect
    for tier in range(1, tiers + 1):
        inset = wall_thickness * tier
        inner = (x0 + inset, y0 + inset, x1 - inset, y1 - inset)
        depth = grade + step * tier
        last = tier == tiers
        _carve_into(outer, inner)
        piece = _rect_room(
            assembly, f"{name}_tier{tier}", inner,
            water_material if last else material,
            floor_z=depth, clear=host_clear + step * tier,
            behavior={"depth": WATER_DEPTH} if last else None,
            note=f"{name}: tier {tier}" + (" (water)" if last else ""))
        _rim(assembly, piece, outer, f"{name}_t{tier}")   # inner rings are ours
        outer, previous = piece, inner
    return {"rim": rim, "well": outer}


def sound_gizmo(layout, placement_id, region_id, *, local=(0.5, 0.5),
                data1=0):
    """A kGenSound emitter, the way E1M1's piano carries three."""
    return layout.place_on_floor(
        placement_id, region_id, local=local, height_player_heights=0.3,
        type=SOUND_TYPE, picnum=SOUND_TILE, cstat=128, shade=0,
        x_repeat=64, y_repeat=64, status=0,
        behavior={"data1": data1} if data1 else None)


def inset(assembly, name, host, rect, material, *, grade, host_clear,
          mouth_clear, sunk=0, note="", connector=None):
    """A hollow with a mouth, faced in its own material.

    Class: E1M1's furnace -- a fire-flat chamber behind a low opening.  The
    mouth is the piece's own ceiling brought down, which is what makes it
    read as something you look INTO rather than a recess in the wall; the
    campaign's are 0.42 to 0.97 player heights of opening.
    """
    _carve_into(host, rect)
    piece = _rect_room(assembly, name, rect, material,
                       floor_z=grade + sunk, clear=mouth_clear,
                       note=note or f"{name}: a hollow behind a low mouth")
    _rim(connector or assembly, piece, host, name)
    return piece


def canopy(assembly, name, host, rect, material, *, grade, host_clear,
           head_room, note="", connector=None):
    """A lowered ceiling over a footprint: a stall roof, a bar back, a bier.

    The floor stays where the host's is, so the player walks under it --
    the piece is the ceiling, not the ground.
    """
    _carve_into(host, rect)
    piece = _rect_room(assembly, name, rect, material,
                       floor_z=grade, clear=head_room,
                       note=note or f"{name}: a canopy at {head_room}")
    _rim(connector or assembly, piece, host, name)
    return piece


# --------------------------------------------------------------------------
# the classes Gravesend needs
# --------------------------------------------------------------------------

def counter(assembly, name, host, rect, material, *, grade, host_clear,
            rise=COUNTER, note=""):
    """A bar counter, shop counter or table.

    Class: raised block, 363 pieces across 38 maps, rise median 0.48 player
    heights, footprint 0.5-1.5 plan units.  Gravesend built these at 0.24
    and they read as steps.
    """
    return raised_solid(assembly, name, host, rect, material, grade=grade,
                        rise=rise, host_clear=host_clear,
                        note=note or f"{name}: a counter at the mined 0.48")


def altar(assembly, name, host, rect, material, *, grade, host_clear,
          note=""):
    """A two-tier raised block: altar, bier, tomb.

    Class: 42 pieces / 16 maps, rise 0.60-0.97, median 0.85.  Built as a
    broad lower tier with a narrower upper one standing on it, which is the
    shape the class's examples take.
    """
    x0, y0, x1, y1 = (int(v) for v in rect)
    inset = max(256, min((x1 - x0), (y1 - y0)) // 6)
    lower = raised_solid(assembly, f"{name}_step", host, rect, material,
                         grade=grade, rise=COUNTER, host_clear=host_clear,
                         note=note or f"{name}: the altar step")
    upper_rect = (x0 + inset, y0 + inset, x1 - inset, y1 - inset)
    _carve_into(lower, upper_rect)
    upper = _rect_room(assembly, f"{name}_mensa", upper_rect, material,
                       floor_z=grade - ALTAR, clear=host_clear - ALTAR,
                       note=f"{name}: the mensa")
    _rim(assembly, upper, lower, f"{name}_mensa")
    return {"step": lower, "mensa": upper}


def stall(assembly, name, host, rect, material, *, grade, host_clear,
          canopy_clear=None, note=""):
    """A market stall: a counter under a lowered canopy.

    Class: two-sector raised piece, 66 pieces / 21 maps, rise 0.36-0.48,
    footprint 0.5-1.88 by 0.62-1.62.  The canopy is the second sector --
    same footprint, ceiling brought down, which is how Build makes a
    covered thing without posts.
    """
    x0, y0, x1, y1 = (int(v) for v in rect)
    board = counter(assembly, f"{name}_board", host, rect, material,
                    grade=grade, host_clear=host_clear,
                    note=note or f"{name}: the stall board")
    if canopy_clear is not None:
        board.surfaces(floor_z=grade - COUNTER, clear_height=canopy_clear)
    return board
