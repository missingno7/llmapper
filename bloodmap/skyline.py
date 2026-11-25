"""How tall a building looks, when the building is a hole.

A mass carved out of a street has no height of its own.  Its street face is a
one-sided wall *of the street sector*, and Build draws a one-sided wall from
that sector's floor to that sector's ceiling.  So every mass in one open region
is exactly as tall as the region's sky, and a city built that way has no
skyline however its plan is varied.  Blood City measured this on itself: 34 sky
sectors, one ceiling, every block 11.6 bodies.

The campaign gets height two ways, and both are in the corpus
(`tools/mine_skylines.py`: of the 38 campaign maps with open sky, none draws
its street walls to a single height and 32 draw them to three or more):

* **Raised roof floors.**  The building's footprint is a sky sector whose floor
  is the roof; the face is the lower step of a two-sided wall.  E1M5 leans on
  this -- seven wall heights from 3 to 10 bodies and no sky step of a body or
  more.  It needs the footprint to be a sector, so it cannot stand over an
  interior without stacking space (`bloodmap.layers`).

* **A stepped sky.**  Open sectors side by side hold their ceilings at different
  heights.  `engine.cpp:4688` skips the upper wall section when *both* sides
  are parallax, so the step is never drawn, while every one-sided wall in each
  sector is still drawn to that sector's own ceiling.  17 campaign maps do it,
  across 141 portals: E1M3 has 29, E3M1 13 and E1M1 12 -- and E3M1's step is
  15.4 bodies.

**Raise the floor; do not lower the sky.**  A low parallax ceiling is still a
ceiling.  The renderer paints it from the top of the far wall upward across
every column the sector covers, so it occludes exactly like a lid: lower a
yard's sky to shorten its wall and the tower behind the wall, and every block
beyond it, is replaced by sky.  Blood City did this on 2026-11-17 and its owner
caught it in the first minute of play.  So:

* :func:`roof` is the default.  The low thing -- a boundary wall, a building's
  top, a buttress -- is a sector whose floor is its top, under the common sky.
  Its face is the lower step of a two-sided wall and the view passes over it.
  Over an interior it is a second layer (`bloodmap.layers`), with its band
  clear above the rooms beneath.
* :func:`apron` -- a strip of open ground with its own sky -- is for making
  something **taller** than the common sky (a tower).  A raised sky hides
  nothing.  Lowering one is the lid again, however small the strip.

**A roof you can see over forbids a door beneath it.**  Build keeps one open
span per screen column.  The columns above a low roof stay open -- that is what
seeing over it means -- and any sector the renderer reaches meanwhile paints
into them: a porch under the roof drew its ceiling up the sky beside the door
as a "pole", and with the door open the room behind smeared 18,000 to 23,000
pixels across it (`projects/blood-city/experiments/church-roofs`).  This is
the engine's old sector-over-sector rule and `bloodmap.layers` already states
it: the space you enter the ground floor from must not also open into the
storey above through the same facade.  So the way into a roofed building is
through something nothing is seen over -- a tower, whose one-sided walls close
every column they cover -- and :func:`leaks_under_roofs` finds the doors that
break this before a frame has to.

The one thing a low sky also does is clip (`rules_blood`
``open-neighbours-share-a-sky``): the player and every sprite are bounded by a
ceiling whether or not it is drawn.  :data:`REACH` is the height below which an
apron would be an invisible ceiling to jump into, and :func:`apron` refuses it.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Sequence

from .levelprog import Frame, LevelProgramError, Room
from .player_space import PLAYER_PROFILES

#: One standing Blood human, in Build z units.
STANDING_HEIGHT = PLAYER_PROFILES["blood"].standing_height

#: The lowest sky an apron may hold, above its floor.  A player's eye is 0.83 of
#: a body and a jump adds well under one; three bodies is out of reach with
#: room to spare, and is also about the lowest street wall the campaign draws
#: under open sky (E1M5 and E1M3 both bottom out at 3).
REACH = 3 * STANDING_HEIGHT


def apron(parent: Any, node_id: str, outline: Iterable[Sequence[int]], *,
          wall_height: int, floor_z: int, sky_picnum: int, wall_picnum: int,
          floor_picnum: int, floor_shade: int | None = None,
          faces: dict[str, int] | None = None, frame: Frame | None = None,
          ceiling_slope: Any = None, layer: str | None = None,
          note: str = "") -> Room:
    """Open ground against a face, whose sky sets how tall that face is drawn.

    `outline` is the strip itself; the faces it shares with the mass are simply
    left unconnected and become the mass's walls, in `wall_picnum`.  Faces are
    named ``e0``, ``e1``... by outline edge unless `faces` says otherwise, so a
    caller connects the open ones to the street and to neighbouring aprons.

    A `ceiling_slope` (loodmap.slope.SlopeSpec) tilts the sky, and with it
    the top edge of every wall drawn against it: two aprons hinged on a face's
    centre line and falling away from it draw that face as a gable.  The
    height is then the height at the hinge.
    """
    points = [(int(x), int(y)) for x, y in outline]
    if int(wall_height) < REACH:
        raise LevelProgramError(
            f"{node_id}: an apron sky {wall_height} above its floor is within a "
            f"player's reach ({REACH}); it would be an invisible ceiling")
    room = parent.room(
        node_id, points, role="exterior",
        faces=faces or {f"e{index}": index for index in range(len(points))},
        frame=frame or Frame(0, 0),
        region_kwargs={"portal_wall_picnum": int(wall_picnum),
                       **({"ceiling_slope": ceiling_slope}
                          if ceiling_slope is not None else {})},
        intent={"kind": "sky_apron", "wall_height": int(wall_height)},
        note=note or f"sky apron: the face behind it is drawn {wall_height} tall",
    )
    surfaces = dict(wall_picnum=int(wall_picnum), floor_picnum=int(floor_picnum),
                    ceiling_picnum=int(sky_picnum), parallax_ceiling=True,
                    floor_z=int(floor_z), clear_height=int(wall_height))
    if floor_shade is not None:
        surfaces["floor_shade"] = int(floor_shade)
    if layer is not None:
        surfaces["layer"] = layer
    room.surfaces(**surfaces)
    return room


def roof(parent: Any, node_id: str, outline: Iterable[Sequence[int]], *,
         top_height: int, sky_height: int, grade_z: int, sky_picnum: int,
         wall_picnum: int, top_picnum: int, top_shade: int | None = None,
         layer: str | None = None, floor_slope: Any = None,
         ceiling_slope: Any = None, frame: Frame | None = None,
         note: str = "") -> Room:
    """The top of something solid: a sector whose floor is `top_height` up.

    Seen from the ground it is a wall `top_height` tall with the world visible
    over it, because its face is the lower step of a two-sided wall and its
    sky is the common one (`sky_height` above grade).  Nobody walks on it; it
    exists to be looked over.

    The face takes its tile from the *viewer's* side of the wall, so call
    :func:`dress_steps` on the compiled level to paint it.  A ``floor_slope``
    pitches the top: two roofs hinged on their eaves and rising to a shared
    ridge draw a gable at each end.
    """
    points = [(int(x), int(y)) for x, y in outline]
    if int(top_height) <= 0 or int(sky_height) <= int(top_height):
        raise LevelProgramError(
            f"{node_id}: a roof {top_height} up needs a sky above it, "
            f"not one at {sky_height}")
    kwargs = {"portal_wall_picnum": int(wall_picnum)}
    if floor_slope is not None:
        kwargs["floor_slope"] = floor_slope
    if ceiling_slope is not None:
        kwargs["ceiling_slope"] = ceiling_slope
    room = parent.room(
        node_id, points, role="exterior",
        faces={f"e{index}": index for index in range(len(points))},
        frame=frame or Frame(0, 0), region_kwargs=kwargs,
        intent={"kind": "roof", "top_height": int(top_height),
                "face_picnum": int(wall_picnum)},
        note=note or f"a roof {top_height} above grade, to be looked over",
    )
    surfaces = dict(wall_picnum=int(wall_picnum), floor_picnum=int(top_picnum),
                    ceiling_picnum=int(sky_picnum), parallax_ceiling=True,
                    floor_z=int(grade_z) - int(top_height),
                    clear_height=int(sky_height) - int(top_height))
    if top_shade is not None:
        surfaces["floor_shade"] = int(top_shade)
    if layer is not None:
        surfaces["layer"] = layer
    room.surfaces(**surfaces)
    return room


def dress_steps(level: Any, faces: dict[int, int], *,
                only_from: Any = None) -> dict[str, int]:
    """Paint the face of every raised sector, from whichever side sees it.

    `faces` maps a raised sector to the tile its sides wear.  The lower step
    of a two-sided wall is drawn from the record on the LOWER side, so the
    tile has to be written on the neighbour's wall, not on the roof's own --
    which is why a roof built without this wears the street's facade.

    `only_from` limits the painting to records in those sectors: the ones
    that look UP at the raised thing from a street, say, and not the ones
    between two raised things.
    """
    painted = 0
    for sector_id, sector in enumerate(level.sectors):
        if only_from is not None and sector_id not in only_from:
            continue
        fields = _fields(sector)
        floor = int(fields["floor_z"])
        start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        for wall_id in range(start, start + count):
            wall = _fields(level.walls[wall_id])
            other = int(wall["next_sector"])
            if other not in faces:
                continue
            if int(_fields(level.sectors[other])["floor_z"]) >= floor:
                continue                    # not looking up at it from here
            wall["picnum"] = int(faces[other])
            painted += 1
    return {"step_walls_painted": painted, "raised_sectors": len(faces)}


def _fields(item: Any) -> dict:
    if isinstance(item, dict):
        return item.get("fields", item)
    return item.fields


def street_wall_heights(level: Any) -> list[dict[str, int]]:
    """Every one-sided wall under open sky, with the height it is drawn to.

    This is the measurement the module exists for: what a player on the ground
    sees as "how tall is that building".  Flat ceilings only -- a sloped sky is
    reported at its sector's nominal ceiling.
    """
    out = []
    for sector_id, sector in enumerate(level.sectors):
        fields = _fields(sector)
        if not int(fields["ceiling_stat"]) & 1:
            continue
        height = int(fields["floor_z"]) - int(fields["ceiling_z"])
        start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        for wall_id in range(start, start + count):
            if int(_fields(level.walls[wall_id])["next_sector"]) < 0:
                out.append({"sector": sector_id, "wall": wall_id,
                            "height": height})
    return out


def lowered_skies(level: Any) -> list[dict[str, int]]:
    """Open sectors holding their sky under the map's commonest one.

    Each is a lid: whatever stands beyond its walls and above them is not
    drawn from inside it, or through it.  A door bay is a legitimate one; a
    yard is not.  The commonest sky is taken by wall length it is drawn
    over, so one big street outvotes many small aprons.
    """
    weight: Counter = Counter()
    open_sectors = []
    for sector_id, sector in enumerate(level.sectors):
        fields = _fields(sector)
        if not int(fields["ceiling_stat"]) & 1:
            continue
        open_sectors.append((sector_id, int(fields["ceiling_z"]),
                             int(fields["floor_z"])))
        weight[int(fields["ceiling_z"])] += int(fields["wall_count"])
    if not weight:
        return []
    common = weight.most_common(1)[0][0]
    return [{"sector": sector_id, "below_common_sky": ceiling - common,
             "clear": floor - ceiling}
            for sector_id, ceiling, floor in open_sectors
            if ceiling > common and floor != ceiling]


#: a lower sky no deeper than this before a wall is that wall's own top (an apron, a lip), not open ground
STRIP_DEPTH = 1024


def thin_fronts(level: Any, *, least: int = 16384) -> list[dict[str, int]]:
    """Where a building is a front with no side: a wall that stops at open ground under a lower sky.

    A wall is drawn to its own sector's sky. Where a street's wall ends at an
    opening into ground whose sky stands lower, what turns the corner there is
    drawn to the lower one, and above it the building is a blade against the
    sky. The owner, 2026-11-25, of a forecourt built so between two buildings of
    11.6 bodies under a sky of 6.8: "makes buildings next to it to look like
    paper thin because of the sky". The ground beside a building takes the
    building's sky; what is meant to be low takes a strip of its own before it
    (`apron`), which is what `STRIP_DEPTH` leaves out, on either side (a tower's
    apron has the higher sky). So does the top of a mass, and a sky backing:
    nobody stands on either.
    """
    sectors = [_fields(s) for s in level.sectors]
    walls = [_fields(w) for w in level.walls]
    owner, before = {}, {}
    for index, sector in enumerate(sectors):
        for w in range(int(sector["wall_ptr"]), int(sector["wall_ptr"]) + int(sector["wall_count"])):
            owner[w], before[int(walls[w]["point2"])] = index, w
    found = []
    for w, wall in enumerate(walls):
        far = int(wall["next_sector"])
        if far < 0 or w not in owner:
            continue
        here, there = sectors[owner[w]], sectors[far]
        if not (int(here["ceiling_stat"]) & 1 and int(there["ceiling_stat"]) & 1):
            continue
        drop = int(there["ceiling_z"]) - int(here["ceiling_z"])
        if drop < least or is_sky_backing(level, far) or int(there["floor_z"]) < int(here["floor_z"]) - 3 * STANDING_HEIGHT:
            continue
        a, b = wall, walls[int(wall["point2"])]
        length = max(1.0, ((int(a["x"]) - int(b["x"])) ** 2 + (int(a["y"]) - int(b["y"])) ** 2) ** 0.5)

        def depth(sector: dict) -> float:
            ring = range(int(sector["wall_ptr"]), int(sector["wall_ptr"]) + int(sector["wall_count"]))
            return max(abs((int(walls[v]["x"]) - int(a["x"])) * (int(b["y"]) - int(a["y"]))
                           - (int(walls[v]["y"]) - int(a["y"])) * (int(b["x"]) - int(a["x"]))) / length for v in ring)

        if min(depth(here), depth(there)) <= STRIP_DEPTH:
            continue
        for end in (before[w], int(wall["point2"])):
            if int(walls[end]["next_sector"]) < 0:
                found.append({"sector": owner[w], "low": far, "wall": end, "x": int((a if end == before[w] else b)["x"]),
                              "y": int((a if end == before[w] else b)["y"]), "bare": drop})
    return found


def is_sky_backing(level: Any, sector_id: int) -> bool:
    """A parallax sector with no height: the sky behind something.

    E3M1 stands one behind each of its street-end walls (s340, s338: floor
    and ceiling both at grade, ceiling parallax).  A sector with no height
    draws no wall; the mass in front of it is two-sided to it and both skies
    are parallax, so no upper step is drawn either, and the eye goes over
    the mass into sky.  It is the opposite of a lowered sky: it hides
    nothing, because it is put where there is nothing.
    """
    fields = _fields(level.sectors[sector_id])
    return (bool(int(fields["ceiling_stat"]) & 1)
            and int(fields["floor_z"]) == int(fields["ceiling_z"]))


def sky_backings(level: Any) -> list[int]:
    return [index for index in range(len(level.sectors))
            if is_sky_backing(level, index)]


def leaks_under_roofs(layout: Any, *, overlaps: Iterable[Any] | None = None
                      ) -> list[dict[str, str]]:
    """Rooms under a see-over roof that open onto the air that sees the roof.

    Each is a render fault waiting for its door to open: the renderer reaches
    the room through the opening while the screen columns above the roof are
    still open, and the room's ceiling is painted into the sky.  The check is
    on the source layout, so it runs before anything is compiled:

    * a **roof** is a region made by :func:`roof`;
    * the **air** that sees it is every open-sky region joined to it through
      open-sky regions;
    * a **room beneath** is a roofed region whose plan the roof overlaps;
    * the fault is a join between such a room and that air -- a door, a porch,
      a window sector.  A door counts shut or open: it will be opened.

    A room reached only through other roofed rooms is not reported, and that
    is the cure: put the way in under something that is not seen over.
    """
    from collections import defaultdict, deque

    from . import layers

    regions = layout.regions
    graph = layers.portal_graph(layout)
    found = layers.find_overlaps(layout) if overlaps is None else overlaps
    open_air = {rid for rid, region in regions.items()
                if getattr(region, "parallax_ceiling", False)}
    roofs = {rid for rid in open_air
             if dict(getattr(regions[rid], "intent", {}) or {}).get("kind") == "roof"}
    beneath: dict[str, set[str]] = defaultdict(set)
    for overlap in found:
        for upper, lower in ((overlap.left, overlap.right),
                             (overlap.right, overlap.left)):
            if upper in roofs and lower in regions and lower not in open_air:
                beneath[upper].add(lower)
    out = []
    for roof_id in sorted(beneath):
        air, queue = {roof_id}, deque([roof_id])
        while queue:
            for other in graph.get(queue.popleft(), ()):
                if other in open_air and other not in air:
                    air.add(other)
                    queue.append(other)
        for room in sorted(beneath[roof_id]):
            for outside in sorted(graph.get(room, set()) & air):
                out.append({"roof": roof_id, "room": room, "opens_onto": outside})
    return out


def profile(level: Any) -> dict[str, Any]:
    """The skyline as numbers: which heights street walls take, and how many.

    A description, not a target.  One distinct height says every building is
    the same building; more says only that they differ, not that they differ
    well -- that is what a rendered frame is for.
    """
    rows = street_wall_heights(level)
    heights = Counter(row["height"] for row in rows)
    return {
        "walls": len(rows),
        "distinct_heights": len(heights),
        "by_bodies": {f"{height / STANDING_HEIGHT:.1f}": count
                      for height, count in sorted(heights.items())},
        "lowered_skies": len(lowered_skies(level)),
        "tallest": max(heights) if heights else 0,
        "tallest_sectors": sorted({row["sector"] for row in rows
                                   if heights and row["height"] == max(heights)}),
    }
