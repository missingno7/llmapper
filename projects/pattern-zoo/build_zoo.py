"""Generate the Pattern Zoo from its registry.

    python projects/pattern-zoo/build_zoo.py

The gallery is corridors **between correctly-sized rooms**, not a grid of
equal boxes. Each exhibit states its own clear height and footprint; the
default is the campaign median (33280 units, 1.96 player heights, from
`norms-v1.json` `shape.median_height`), and a lift or a facade asks for more.
v1 gave everything 1.5 heights and the facades had no room to be facades.

Nothing is placed by hand: the stalls come from `registry.exhibits()` and
their contents from `stalls.py`, through the constructors that own each
concept.

**The ROR budget is respected.** Two room-over-room volumes must not be in
view at once, so exhibits that declare `room_over_room` are kept apart along
the spine.
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
#: The project directory has a hyphen in its name, so it is not a package;
#: the two modules beside this one are imported by path.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from bloodmap.format import write_map                       # noqa: E402
from bloodmap.lettering import write_on_wall                # noqa: E402
from bloodmap.planar_layout import PlanarLayout             # noqa: E402
from bloodmap.texture_align import sprite_tile_extents      # noqa: E402

import registry as registry_module                          # noqa: E402

U = 1024
#: The spine's own shell, deliberately plain: the rooms wear the materials.
SPINE_SKIN = (400, 294, 285)
CORRIDOR_WIDTH = 3 * U
#: The neck between spine and room, exactly as wide as the mouth. Without it
#: a room's whole near wall lies on the corridor's and only part of it pairs.
NECK = 768
MOUTH = 2 * U
ENTRANCE = 4 * U
#: How deep the room behind a stall runs -- where the mechanism itself lives.
BACK_DEPTH = 5 * U
#: Clear air between one room and the next along the spine.
GAP = 2 * U

FLOOR_Z = 0
#: Two ROR volumes in view at once make the renderer draw both.
ROR_SEPARATION = 5 * (5 * U)


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def plan(exhibits):
    """Lay the rooms out along the spine, each at its own size.

    Rooms alternate sides and advance by their own depth, so a big room takes
    the space it needs instead of everything shrinking to the smallest.
    """
    placed = []
    cursor = {-1: ENTRANCE, 1: ENTRANCE}
    ror_at = []
    side = -1
    for exhibit in exhibits:
        across, deep = exhibit.size
        while True:
            centre = cursor[side] + across // 2
            if not exhibit.room_over_room:
                break
            clash = any(abs(centre - other) < ROR_SEPARATION
                        for other, other_side in ror_at if other_side == side)
            if not clash:
                ror_at.append((centre, side))
                break
            cursor[side] += across + GAP
        placed.append((exhibit, side, centre))
        cursor[side] = centre + across // 2 + GAP
        side = -side
    return placed


def build_level() -> PlanarLayout:
    exhibits = registry_module.exhibits()
    placed = plan(exhibits)
    length = max(centre + exhibit.size[0] // 2
                 for exhibit, _side, centre in placed) + ENTRANCE

    #: Seated sprites need their tiles' drawn extents, or an object placed at
    #: floor level is buried to the waist -- or, as the owner found in v1,
    #: hangs in the air.
    try:
        extents = sprite_tile_extents()
    except Exception:
        extents = {}
    layout = PlanarLayout(name="pattern-zoo", visibility=800,
                          tile_extents=extents)
    wall, floor, ceiling = SPINE_SKIN
    half = CORRIDOR_WIDTH // 2
    spine_clear = registry_module.MEDIAN_CLEAR
    layout.add_region(
        "region:spine", _rect(-half, 0, half, length),
        floor_z=FLOOR_Z, ceiling_z=FLOOR_Z - spine_clear,
        wall_picnum=wall, floor_picnum=floor, ceiling_picnum=ceiling,
        intent={"purpose": "the gallery corridor; every room opens off it"})

    for exhibit, side, centre in placed:
        name = exhibit.label.lower().replace(" ", "_")
        across, deep = exhibit.size
        ceiling_z = FLOOR_Z - exhibit.clear
        skin = exhibit.skin
        edge = half if side > 0 else -half
        neck_far = edge + side * NECK
        near, far = neck_far, neck_far + side * deep
        x0, x1 = (near, far) if side > 0 else (far, near)
        y0, y1 = centre - across // 2, centre + across // 2

        neck_box = ((edge, centre - MOUTH // 2, neck_far, centre + MOUTH // 2)
                    if side > 0 else
                    (neck_far, centre - MOUTH // 2, edge, centre + MOUTH // 2))
        layout.add_region(
            f"neck:{name}", _rect(*neck_box),
            floor_z=FLOOR_Z, ceiling_z=FLOOR_Z - spine_clear,
            wall_picnum=wall, floor_picnum=floor, ceiling_picnum=ceiling,
            intent={"purpose": f"the way in to {exhibit.label}"})
        stall_id = f"stall:{name}"
        layout.add_region(
            stall_id, _rect(x0, y0, x1, y1),
            floor_z=FLOOR_Z, ceiling_z=ceiling_z,
            wall_picnum=skin[0], floor_picnum=skin[1], ceiling_picnum=skin[2],
            intent={"purpose": f"{exhibit.label}: {exhibit.about}",
                    "try": exhibit.try_this, "provenance": exhibit.provenance})
        layout.add_connection(
            f"c:{name}:spine", "region:spine", f"neck:{name}",
            a1=(edge, centre - MOUTH // 2), a2=(edge, centre + MOUTH // 2),
            min_width=U)
        layout.add_connection(
            f"c:{name}:stall", f"neck:{name}", stall_id,
            a1=(neck_far, centre - MOUTH // 2),
            a2=(neck_far, centre + MOUTH // 2), min_width=U)

        #: The label goes on the corridor wall beside the mouth. The span's
        #: direction decides which way `place_on_wall` offsets, so the two
        #: sides run opposite ways.
        #: The label runs from the mouth's edge into the free corridor wall
        #: between this room and the next. Half a room's frontage is not
        #: enough: SWITCHED DOOR needs 1766 units at size 48 and half of a
        #: 5120 room is 1536.
        low = (edge, centre + MOUTH // 2)
        high = (edge, centre + across // 2 + GAP - 256)
        sign_a, sign_b = (high, low) if side < 0 else (low, high)
        write_on_wall(layout, f"sign:{name}", "region:spine",
                      a1=sign_a, a2=sign_b, text=exhibit.label,
                      height_player_heights=1.15, size=48)

        back_near, back_far = far, far + side * BACK_DEPTH
        back = ((back_near, y0, back_far, y1) if side > 0
                else (back_far, y0, back_near, y1))
        if exhibit.is_empty():
            #: An honest gap, lettered on the room's own back wall.
            a1, a2 = ((x1, y0), (x1, y1)) if side > 0 else ((x0, y1), (x0, y0))
            write_on_wall(layout, f"blocker:{name}", stall_id,
                          a1=a1, a2=a2, text=exhibit.blocker,
                          height_player_heights=0.85, size=48)
            continue
        exhibit.build(layout, stall_id, (x0, y0, x1, y1), back,
                      floor_z=FLOOR_Z, ceiling_z=ceiling_z, skin=skin)

    layout.set_player_start("region:spine", x=0, y=ENTRANCE // 2, z=FLOOR_Z,
                            angle=512)
    return layout


def main() -> int:
    layout = build_level()
    compiled = layout.compile()
    disk = compiled.level.to_disk_map()
    here = pathlib.Path(__file__).resolve().parent
    out = here / "level" / "pattern-zoo.MAP"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_map(disk, out)

    sectors = {name: allocation.sector_id
               for name, allocation in compiled.allocations.items()}
    #: Which sprites were *seated on a floor*. Only the builder knows this --
    #: in the finished MAP a face sprite hung deliberately up a wall and one
    #: that failed to find its floor look identical. The self-read needs the
    #: distinction to tell a floating mannequin from a mounted crack.
    floor_seated = sorted(
        compiled.placement_sprites[placement.placement_id]
        for placement in layout.placements
        if placement.seat == "floor"
        and placement.placement_id in compiled.placement_sprites)
    manifest = {
        "$schema": "llmapper.pattern-zoo-build", "schema_version": 2,
        "map": str(out.relative_to(ROOT)).replace("\\", "/"),
        "sectors": len(disk.sectors), "walls": len(disk.walls),
        "sprites": len(disk.sprites),
        "region_sectors": sectors,
        "floor_seated_sprites": floor_seated,
        "exhibits": [
            {"label": e.label, "about": e.about, "try": e.try_this,
             "provenance": e.provenance, "empty": e.is_empty(),
             "blocker": e.blocker or None,
             "room_over_room": e.room_over_room,
             "covers": list(e.covers),
             "hand_composed": list(e.hand_composed),
             "expect_summary": e.expect.summary(),
             "clear": e.clear, "size": list(e.size), "skin": list(e.skin),
             "sector": sectors.get(
                 "stall:" + e.label.lower().replace(" ", "_"))}
            for e in registry_module.exhibits()],
    }
    (here / "reports").mkdir(parents=True, exist_ok=True)
    (here / "reports" / "build-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {out}: {len(disk.sectors)} sectors, {len(disk.walls)} walls, "
          f"{len(disk.sprites)} sprites, {len(manifest['exhibits'])} exhibits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
