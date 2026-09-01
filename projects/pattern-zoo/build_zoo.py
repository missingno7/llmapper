"""Generate the Pattern Zoo from its registry.

    python projects/pattern-zoo/build_zoo.py

v3. The owner rejected v2 for its shape: a corridor of one-exhibit cells is
not a gallery, and a mechanism shown in a generic box says nothing about how
it is used. So the zoo is now a spine that branches into **sections**, and a
section is ONE environment -- a shop, a street, a sewer -- holding the
exhibits that belong together in it.

Inside a section the exhibits stand in **bays** along its back wall, each as
wide as that exhibit needs, and each preceded by a **pier** of solid wall
that carries its label. The label cannot go on the bay's own wall: an
exhibit is entitled to open all of it -- a doorway, a park, a frontage --
and letters hung across an opening are refused, correctly. So the pier is
sized to whichever word it has to carry, and is solid by construction.

Nothing is placed by hand: sections and exhibits come from `registry.py` and
their contents from `stalls.py`, through the constructors that own each
concept.
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
from bloodmap.lettering import (                            # noqa: E402
    drawn_width, text_width, write_on_wall,
)
from bloodmap.planar_layout import PlanarLayout             # noqa: E402
from bloodmap.texture_align import sprite_tile_extents      # noqa: E402

import registry as registry_module                          # noqa: E402

U = 1024
PLAYER_HEIGHT = 16960
#: The spine's own shell, deliberately plain: the sections wear the materials.
SPINE_SKIN = (400, 294, 285)
CORRIDOR_WIDTH = 3 * U
#: The neck between spine and section, exactly as wide as the mouth. Without
#: it a section's whole near wall lies on the corridor's and only part of it
#: pairs, which the planar compiler refuses.
NECK = 768
MOUTH = 2 * U
ENTRANCE = 4 * U
#: Clear air between one section and the next along the spine.
GAP = 3 * U

FLOOR_Z = 0
#: How high an exhibit's label sits: above a doorway header at 1.5 player
#: heights, and inside the campaign-median clear of 1.96.
LABEL_HEIGHT_PH = 1.72
LABEL_SIZE = registry_module.LABEL_SIZE
PIER = registry_module.PIER


def _toward(text, span, size, *, forward):
    """Where the middle of a word sits so it hugs one end of its wall.

    `write_on_wall` checks that a word fits the wall but not that a given `t`
    keeps it there, so pushing a label toward the bay it names by eye ran the
    last letters past the pier and across the neighbouring opening. This
    clamps the offset to what the wall actually has room for.
    """
    needed = text_width(text, size) + drawn_width(size)
    if span <= 0:
        return 0.5
    margin = (needed / 2.0) / span
    edge = max(0.5, min(1.0 - margin, 0.85))
    return edge if forward else 1.0 - edge


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def plan(sections):
    """Lay the sections along the spine, each at its own frontage.

    Sections alternate sides and advance by their own frontage, so a long
    gallery takes the room it needs instead of everything shrinking to the
    smallest.
    """
    placed = []
    cursor = {-1: ENTRANCE, 1: ENTRANCE}
    side = -1
    for section in sections:
        across = section.frontage()
        centre = cursor[side] + across // 2
        placed.append((section, side, centre))
        cursor[side] = centre + across // 2 + GAP
        side = -side
    return placed


def _bays(section, centre):
    """Each exhibit's pier and bay along the section's back wall.

    The pier comes first and carries the label; the bay follows and is the
    exhibit's to open however it likes.
    """
    across = section.frontage()
    at = centre - across // 2
    out = []
    for item in section.exhibits:
        pier = item.pier()
        out.append((item, at, at + pier, at + pier, at + pier + item.bay))
        at += pier + item.bay
    return out


def build_level() -> PlanarLayout:
    sections = registry_module.sections()
    placed = plan(sections)
    length = max(centre + section.frontage() // 2
                 for section, _side, centre in placed) + ENTRANCE

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
        intent={"purpose": "the spine; every section opens off it"})

    for section, side, centre in placed:
        name = section.region_prefix()
        across = section.frontage()
        deep = section.standing
        ceiling_z = FLOOR_Z - section.clear
        skin = section.skin
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
            intent={"purpose": f"the way in to {section.label}"})
        section_id = f"section:{name}"
        layout.add_region(
            section_id, _rect(x0, y0, x1, y1),
            floor_z=FLOOR_Z, ceiling_z=ceiling_z,
            wall_picnum=skin[0], floor_picnum=skin[1], ceiling_picnum=skin[2],
            parallax_ceiling=section.outdoor,
            intent={"purpose": f"{section.label}: {section.about}"})
        layout.add_connection(
            f"c:{name}:spine", "region:spine", f"neck:{name}",
            a1=(edge, centre - MOUTH // 2), a2=(edge, centre + MOUTH // 2),
            min_width=U)
        layout.add_connection(
            f"c:{name}:section", f"neck:{name}", section_id,
            a1=(neck_far, centre - MOUTH // 2),
            a2=(neck_far, centre + MOUTH // 2), min_width=U)

        #: The section's name on the corridor wall beside its mouth.
        low = (edge, centre + MOUTH // 2)
        high = (edge, centre + across // 2 - 256)
        sign_a, sign_b = (high, low) if side < 0 else (low, high)
        write_on_wall(layout, f"sign:{name}", "region:spine",
                      a1=sign_a, a2=sign_b, text=section.label,
                      height_player_heights=1.15, size=64)

        back_wall = far
        for item, pier_low, pier_high, bay_low, bay_high in _bays(section,
                                                                   centre):
            bx0, bx1 = (near, far) if side > 0 else (far, near)
            bay = (bx0, bay_low, bx1, bay_high)
            back_near, back_far = back_wall, back_wall + side * item.depth
            back = ((back_near, bay_low, back_far, bay_high) if side > 0
                    else (back_far, bay_low, back_near, bay_high))

            #: The label goes on the PIER beside the bay, not on the bay's
            #: own wall: an exhibit is entitled to open all of its wall, and
            #: letters hung across an opening are refused. Ordered the way an
            #: inward-facing wall is ordered, so they face into the room.
            a1 = (back_wall, pier_low) if side > 0 else (back_wall, pier_high)
            a2 = (back_wall, pier_high) if side > 0 else (back_wall, pier_low)
            #: Justified hard against the bay it names. The pier runs
            #: low-to-high before the bay, so on the +x side the bay is at
            #: the far end of the pier wall and on the -x side at the near.
            span = pier_high - pier_low
            toward = _toward(item.label, span, LABEL_SIZE, forward=side > 0)
            write_on_wall(layout, f"label:{item.region_prefix()}", section_id,
                          a1=a1, a2=a2, text=item.label, t=toward,
                          height_player_heights=LABEL_HEIGHT_PH,
                          size=LABEL_SIZE)
            if item.is_empty():
                #: An honest gap, lettered under its own name.
                write_on_wall(layout, f"blocker:{item.region_prefix()}",
                              section_id, a1=a1, a2=a2, text=item.blocker,
                              t=_toward(item.blocker, span, LABEL_SIZE,
                                        forward=side > 0),
                              height_player_heights=0.85, size=LABEL_SIZE)
                continue
            item.build(layout, section_id, bay, back,
                       floor_z=FLOOR_Z, ceiling_z=ceiling_z, skin=skin,
                       section_box=(x0, y0, x1, y1))

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
    #: Which sprites were *seated on a floor*, and which are letters. Only
    #: the builder knows either: in the finished MAP a face sprite hung
    #: deliberately up a wall and one that failed to find its floor look
    #: identical, and a letter is just another wall sprite.
    floor_seated = sorted({
        compiled.placement_sprites[placement.placement_id]
        for placement in layout.placements
        if placement.seat == "floor"
        and placement.placement_id in compiled.placement_sprites})
    letters = sorted({
        compiled.placement_sprites[placement.placement_id]
        for placement in layout.placements
        if (placement.placement_id.startswith(("label:", "sign:", "blocker:"))
            and placement.placement_id in compiled.placement_sprites)})
    manifest = {
        "$schema": "llmapper.pattern-zoo-build", "schema_version": 3,
        "map": str(out.relative_to(ROOT)).replace("\\", "/"),
        "sectors": len(disk.sectors), "walls": len(disk.walls),
        "sprites": len(disk.sprites),
        "region_sectors": sectors,
        "floor_seated_sprites": floor_seated,
        "letter_sprites": letters,
        "sections": [
            {"label": s.label, "about": s.about, "clear": s.clear,
             "outdoor": s.outdoor, "skin": list(s.skin),
             "hand_composed": list(s.hand_composed),
             "sector": sectors.get("section:" + s.region_prefix()),
             "exhibits": [e.label for e in s.exhibits]}
            for s in registry_module.sections()],
        "exhibits": [
            {"label": e.label, "about": e.about, "try": e.try_this,
             "provenance": e.provenance, "empty": e.is_empty(),
             "blocker": e.blocker or None,
             "section": registry_module.section_of(e.label).label,
             "room_over_room": e.room_over_room,
             "covers": list(e.covers),
             "hand_composed": list(e.hand_composed),
             "expect_summary": e.expect.summary(),
             "bay": e.bay, "depth": e.depth,
             "prefix": e.region_prefix()}
            for e in registry_module.exhibits()],
    }
    (here / "reports").mkdir(parents=True, exist_ok=True)
    (here / "reports" / "build-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {out}: {len(disk.sectors)} sectors, {len(disk.walls)} walls, "
          f"{len(disk.sprites)} sprites, {len(manifest['sections'])} sections, "
          f"{len(manifest['exhibits'])} exhibits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
