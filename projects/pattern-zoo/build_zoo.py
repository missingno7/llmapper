"""Generate the Pattern Zoo from its registry.

    python projects/pattern-zoo/build_zoo.py

A spine corridor with stalls down both sides, one exhibit per stall, its label
written on the corridor wall beside its mouth. Nothing is placed by hand: the
stalls come from `registry.exhibits()` and their contents from `stalls.py`,
through `PlanarLayout` and the existing constructors.

**The ROR budget is respected.** Two room-over-room volumes must not be in
view at once or the renderer draws both -- the lesson E1M1 encodes by reusing
one volume for two jobs. Exhibits that declare `room_over_room` are placed on
opposite sides of the corridor and at least `ROR_SEPARATION` apart along it.
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from bloodmap.format import write_map
from bloodmap.lettering import write_on_wall
from bloodmap.planar_layout import PlanarLayout
from bloodmap.texture_align import sprite_tile_extents

#: The project directory has a hyphen in its name, so it is not a package;
#: the two modules beside this one are imported by path.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import registry as registry_module  # noqa: E402
import stalls as stalls_module  # noqa: E402

U = 1024
WALL, FLOOR, CEILING = stalls_module.WALL, stalls_module.FLOOR, stalls_module.CEILING

#: The gallery's shape. Generous on purpose: a visitor has to be able to walk
#: past an exhibit that is mid-motion without being caught by it.
CORRIDOR_WIDTH = 3 * U
STALL_DEPTH = 5 * U
STALL_WIDTH = 5 * U
STALL_PITCH = 6 * U
MOUTH = 2 * U
ENTRANCE = 4 * U
#: How deep the room behind a stall runs.
BACK_DEPTH = 5 * U
#: The short neck between corridor and stall.
NECK = 768

FLOOR_Z = 0
CEILING_Z = -3 * 16960 // 2

#: How far apart two room-over-room volumes have to sit along the corridor.
#: One stall pitch is not enough -- a visitor standing between two adjacent
#: stalls sees into both.
ROR_SEPARATION = 3 * STALL_PITCH


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _place_exhibits(exhibits):
    """Left/right along the corridor, keeping ROR volumes out of each other's view."""
    placed, ror_at = [], []
    row = 0
    for exhibit in exhibits:
        side = -1 if row % 2 == 0 else 1
        while exhibit.room_over_room:
            y = ENTRANCE + row * STALL_PITCH
            clash = any(abs(y - other_y) < ROR_SEPARATION and side == other_side
                        for other_y, other_side in ror_at)
            if not clash:
                ror_at.append((y, side))
                break
            row += 1
            side = -1 if row % 2 == 0 else 1
        placed.append((exhibit, row, side))
        row += 1
    return placed


def build_level() -> PlanarLayout:
    exhibits = registry_module.exhibits()
    placed = _place_exhibits(exhibits)
    rows = max(row for _e, row, _s in placed) + 1
    length = ENTRANCE + rows * STALL_PITCH + ENTRANCE

    #: Seated sprites need their tiles' drawn extents, or a standing object
    #: placed at floor level is buried to the waist.
    try:
        extents = sprite_tile_extents()
    except Exception:
        extents = {}
    layout = PlanarLayout(name="pattern-zoo", visibility=800,
                          tile_extents=extents)
    half = CORRIDOR_WIDTH // 2
    layout.add_region(
        "region:spine", _rect(-half, 0, half, length),
        floor_z=FLOOR_Z, ceiling_z=CEILING_Z,
        wall_picnum=WALL, floor_picnum=FLOOR, ceiling_picnum=CEILING,
        intent={"purpose": "the gallery corridor; every stall opens off it"})

    for exhibit, row, side in placed:
        name = exhibit.label.lower().replace(" ", "_")
        centre = ENTRANCE + row * STALL_PITCH + STALL_WIDTH // 2
        #: A neck between corridor and stall, exactly as wide as the mouth.
        #: Without it the stall's whole near wall lies on the corridor's, and
        #: only the mouth part of it pairs -- which the planar layout reports
        #: as unexplained unpaired portals, and rightly.
        wall = half if side > 0 else -half
        neck_far = wall + side * NECK
        near = neck_far
        far = near + side * STALL_DEPTH
        x0, x1 = (near, far) if side > 0 else (far, near)
        y0, y1 = centre - STALL_WIDTH // 2, centre + STALL_WIDTH // 2
        stall_id = f"stall:{name}"
        neck_box = ((wall, centre - MOUTH // 2, neck_far, centre + MOUTH // 2)
                    if side > 0 else
                    (neck_far, centre - MOUTH // 2, wall, centre + MOUTH // 2))
        layout.add_region(
            f"neck:{name}", _rect(*neck_box),
            floor_z=FLOOR_Z, ceiling_z=CEILING_Z,
            wall_picnum=WALL, floor_picnum=FLOOR, ceiling_picnum=CEILING,
            intent={"purpose": f"the way in to {exhibit.label}"})
        layout.add_region(
            stall_id, _rect(x0, y0, x1, y1),
            floor_z=FLOOR_Z, ceiling_z=CEILING_Z,
            wall_picnum=WALL, floor_picnum=FLOOR, ceiling_picnum=CEILING,
            intent={"purpose": f"{exhibit.label}: {exhibit.about}",
                    "try": exhibit.try_this, "provenance": exhibit.provenance})
        layout.add_connection(
            f"c:{name}:spine", "region:spine", f"neck:{name}",
            a1=(wall, centre - MOUTH // 2), a2=(wall, centre + MOUTH // 2),
            min_width=U)
        layout.add_connection(
            f"c:{name}:stall", f"neck:{name}", stall_id,
            a1=(neck_far, centre - MOUTH // 2),
            a2=(neck_far, centre + MOUTH // 2), min_width=U)
        #: Sub-rooms go *beyond* the stall's far wall, never inside it: a
        #: region wholly contained in another is a containment the planar
        #: layout refuses, and rightly.
        back_near = far
        back_far = far + side * BACK_DEPTH
        back = ((back_near, y0, back_far, y1) if side > 0
                else (back_far, y0, back_near, y1))

        #: The label goes on the corridor wall beside the mouth, so a visitor
        #: walking the spine reads it before turning in.
        #: `place_on_wall` offsets the sprite *into* the region, and which
        #: way that is comes from the wall's direction. On the corridor's
        #: left wall the span has to run the other way or the letters land
        #: outside the corridor.
        low = (wall, centre + MOUTH // 2)
        high = (wall, centre + STALL_PITCH // 2)
        sign_a, sign_b = (high, low) if side < 0 else (low, high)
        text = exhibit.label if not exhibit.is_empty() else f"{exhibit.label} EMPTY"
        try:
            write_on_wall(layout, f"sign:{name}", "region:spine",
                          a1=sign_a, a2=sign_b, text=text,
                          height_player_heights=1.15, size=48)
        except Exception:
            #: A label too long for its wall is a registry bug, but it must
            #: not stop the map building -- the stall is still walkable and
            #: the tour sheet still names it.
            pass
        if exhibit.is_empty():
            try:
                write_on_wall(layout, f"blocker:{name}", stall_id,
                              a1=(x0, y1), a2=(x1, y1), text=exhibit.blocker,
                              height_player_heights=0.8, size=48)
            except Exception:
                pass
            continue
        exhibit.build(layout, stall_id, (x0, y0, x1, y1), back,
                      floor_z=FLOOR_Z, ceiling_z=CEILING_Z)

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
    #: Which sector each stall became, so the tour can render them in
    #: registry order without guessing.
    sectors = {name: allocation.sector_id
               for name, allocation in compiled.allocations.items()
               if name.startswith("stall:")}
    manifest = {
        "$schema": "llmapper.pattern-zoo-build", "schema_version": 1,
        "stall_sectors": sectors,
        "map": str(out.relative_to(ROOT)).replace("\\", "/"),
        "sectors": len(disk.sectors), "walls": len(disk.walls),
        "sprites": len(disk.sprites),
        "exhibits": [
            {"label": e.label, "about": e.about, "try": e.try_this,
             "provenance": e.provenance, "empty": e.is_empty(),
             "blocker": e.blocker or None,
             "room_over_room": e.room_over_room,
             "covers": list(e.covers),
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
