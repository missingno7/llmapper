"""Emit a hierarchical, navigable Python program for one original MAP.

``bloodmap.decompiler.emit_python_source`` already produces "readable Python"
for a level.  For E2M3 that file is 138,008 lines, 99% of them the one exact
``LevelIR`` literal, with 278 functions that look things up in it.  Editing those functions changes
nothing, and reading one of them tells you nothing about one room.

This emitter produces the other thing.  Every part owns its own geometry in its
own coordinates, its own surfaces, and its own details, and the file is a tree
of functions shaped like the level:

    build_level()
      build_area_003()
        build_space_037()
          sector rooms, their surfaces, their sprites

What it is not: byte-exact.  ``E2M3.MAP`` stays the authority and is what the
provenance points at.  The program is a *re-expression* whose fidelity is
measured rather than assumed, and the measurement is written into the file.

    python -m tools.emit_level_program maps/blood/E2M3.MAP \\
        -o projects/e2m3-decompiled/source/E2M3.py
"""

from __future__ import annotations

import argparse
import json
import pathlib
from collections import Counter, defaultdict
from typing import Any

from bloodmap.decompiler import decompile_level
from bloodmap.format import read_map
from bloodmap.planar_geom import area2, polygon_relation, validate_loop
from bloodmap.structures import detect_structures
from bloodmap.viewpoints import _sector_loops

PLAYER_WIDTH = 384
PLAYER_HEIGHT = 0x1600

#: Spaces at or above this footprint get their own named builder; the rest are
#: emitted inside their area as parts, so the file has a readable top level.
NAMED_SPACE_PLAYER_AREAS = 20.0


def _identifier(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_").lower()


def _bounds(points: list[tuple[int, int]]) -> tuple[int, int, int, int]:
    return (
        min(p[0] for p in points), min(p[1] for p in points),
        max(p[0] for p in points), max(p[1] for p in points),
    )


def _sector_loops_split(level, sector_id: int) -> tuple[list[tuple[int, int]], list[list[tuple[int, int]]]]:
    """The sector's outer loop and its holes, wound the way the compiler wants."""
    loops = _sector_loops(level, sector_id)
    outer_loop = max(loops, key=lambda loop: abs(area2(tuple(loop))))
    outer = [(int(x), int(y)) for x, y in outer_loop]
    if area2(tuple(outer)) < 0:
        outer.reverse()
    holes: list[list[tuple[int, int]]] = []
    for loop in loops:
        if loop is outer_loop:
            continue
        hole = [(int(x), int(y)) for x, y in loop]
        if area2(tuple(hole)) > 0:
            hole.reverse()
        holes.append(hole)
    return outer, holes


def _sector_outline(level, sector_id: int) -> list[tuple[int, int]]:
    return _sector_loops_split(level, sector_id)[0]


def _face_names(points: list[tuple[int, int]]) -> dict[str, int]:
    """Name an axis-aligned edge by compass direction, only when it is the extreme one.

    A compass name has to mean something to be useful: "north" is only emitted
    for an edge that actually lies on the outline's minimum y.  On a twelve-sided
    sector most edges get no name, which is the honest answer -- the author
    addresses those by index, or gives them names by hand.
    """
    names: dict[str, int] = {}
    count = len(points)
    min_x, min_y, max_x, max_y = _bounds(points)
    for index in range(count):
        ax, ay = points[index]
        bx, by = points[(index + 1) % count]
        if ay == by and ay in (min_y, max_y):
            name = "north" if bx > ax else "south"
            if (name == "north") != (ay == min_y):
                continue
        elif ax == bx and ax in (min_x, max_x):
            name = "east" if by > ay else "west"
            if (name == "east") != (ax == max_x):
                continue
        else:
            continue
        length = abs(bx - ax) + abs(by - ay)
        current = names.get(name)
        if current is None:
            names[name] = index
        else:
            cx, cy = points[current]
            dx, dy = points[(current + 1) % count]
            if length > abs(dx - cx) + abs(dy - cy):
                names[name] = index
    return names


def _sectors_named_in(message: str) -> list[int]:
    """Every ``sector_NNN`` the compiler mentioned, in the order it mentioned them."""
    result: list[int] = []
    for token in message.replace(":", " ").replace("/", " ").split():
        if token.startswith("sector_") and token[7:10].isdigit():
            value = int(token[7:10])
            if value not in result:
                result.append(value)
    return result


def _modal(values: list[int]) -> int | None:
    if not values:
        return None
    return Counter(values).most_common(1)[0][0]


class ProgramEmitter:
    def __init__(self, path: pathlib.Path, *, art_dir: str | None = None,
                 names: dict[str, dict[str, str]] | None = None,
                 areas_document: dict[str, Any] | None = None) -> None:
        self.path = path
        self.names = dict(names or {})
        # assembly id -> the proposed zones inside it.  Without this the middle
        # of the tree is a flat list of every space in the assembly, which on
        # E2M3 is 123 calls in one function.
        self.zones: dict[str, list[dict[str, Any]]] = {}
        for item in (areas_document or {}).get("assemblies", []):
            if item.get("grouped") and item.get("primary"):
                self.zones[item["assembly"]] = item["primary"]["areas"]
        self.art_sizes: dict[int, tuple[int, int]] = {}
        if art_dir:
            from bloodmap.vocabulary import art_sizes_from_directory

            self.art_sizes = art_sizes_from_directory(art_dir)
        self.level = read_map(path).to_level_ir()
        self.source = decompile_level(self.level, source_name=path.name)
        self.structures = detect_structures(self.level)
        self.nodes = {item["id"]: item for item in self.source.hierarchy["nodes"]}
        self.outlines: dict[int, list[tuple[int, int]]] = {}
        self.hole_loops: dict[int, list[list[tuple[int, int]]]] = {}
        for sector_id in range(len(self.level.sectors)):
            outer, holes = _sector_loops_split(self.level, sector_id)
            self.outlines[sector_id] = outer
            self.hole_loops[sector_id] = holes
        self.structure_of: dict[int, dict[str, Any]] = {}
        for item in self.structures["structures"]:
            if item["kind"] in {"stepped_run", "recess", "landing"}:
                for sector_id in item["sectors"]:
                    self.structure_of.setdefault(sector_id, item)
        self.sprites_by_sector: dict[int, list[int]] = defaultdict(list)
        for index, sprite in enumerate(self.level.sprites):
            self.sprites_by_sector[int(sprite["fields"]["sector"])].append(index)
        # Roughly one original sector in a hundred is a loop the authoring
        # compiler will not accept -- a zero-area sliver, a repeated vertex, a
        # self-touching outline.  Those are recorded rather than repaired: the
        # exact MAP still has them, and silently "fixing" geometry would be
        # inventing evidence about what the designer drew.
        self._overlaps: list[tuple[int, int, str]] | None = None
        self.escapes: dict[int, str] = {}
        for sector_id, outline in self.outlines.items():
            errors = validate_loop(outline, role="outer")
            if errors:
                self.escapes[sector_id] = errors[0]

    # -- grouping ---------------------------------------------------------
    def areas(self) -> list[dict[str, Any]]:
        """Assemblies with their spaces, largest first, so the file reads top-down."""
        result = []
        for node in self.source.hierarchy["nodes"]:
            if node["kind"] != "assembly":
                continue
            spaces = [
                self.nodes[child] for child in node["children"]
                if self.nodes[child]["kind"] == "space"
            ]
            spaces.sort(
                key=lambda item: -item["geometry"]["player_relative"]["footprint_player_areas"]
            )
            result.append({"node": node, "spaces": spaces})
        result.sort(
            key=lambda item: -item["node"]["geometry"]["player_relative"]["footprint_player_areas"]
        )
        return result

    def _style_for(self, sector_ids: list[int]) -> dict[str, int]:
        floors, ceilings, walls, floor_shades, ceiling_shades, wall_shades = ([] for _ in range(6))
        parallax = 0
        for sector_id in sector_ids:
            fields = self.level.sectors[sector_id]["fields"]
            floors.append(int(fields["floor_picnum"]))
            ceilings.append(int(fields["ceiling_picnum"]))
            floor_shades.append(int(fields["floor_shade"]))
            ceiling_shades.append(int(fields["ceiling_shade"]))
            parallax += 1 if int(fields["ceiling_stat"]) & 1 else 0
            first, count = int(fields["wall_ptr"]), int(fields["wall_count"])
            for wall_id in range(first, first + count):
                walls.append(int(self.level.walls[wall_id]["fields"]["picnum"]))
                wall_shades.append(int(self.level.walls[wall_id]["fields"]["shade"]))
        style = {
            "wall_picnum": _modal(walls), "floor_picnum": _modal(floors),
            "ceiling_picnum": _modal(ceilings), "wall_shade": _modal(wall_shades),
            "floor_shade": _modal(floor_shades), "ceiling_shade": _modal(ceiling_shades),
        }
        if parallax and parallax * 2 >= len(sector_ids):
            style["parallax_ceiling"] = True
        return {key: value for key, value in style.items() if value is not None}

    def overlapping_pairs(self) -> list[tuple[int, int, str]]:
        if self._overlaps is None:
            self._overlaps = self._compute_overlapping_pairs()
        return [
            item for item in self._overlaps
            if item[0] not in self.escapes and item[1] not in self.escapes
        ]

    def _compute_overlapping_pairs(self) -> list[tuple[int, int, str]]:
        """Sector pairs that share XY footprint on purpose.

        Build has no rule against this; ``PlanarLayout`` does, because in
        authored work an undeclared overlap is a bug.  A decompiled original has
        to declare the ones the designer actually drew.
        """
        boxes = {sector_id: _bounds(points) for sector_id, points in self.outlines.items()}
        result: list[tuple[int, int, str]] = []
        ids = sorted(self.outlines)
        for index, left in enumerate(ids):
            lx0, ly0, lx1, ly1 = boxes[left]
            for right in ids[index + 1:]:
                rx0, ry0, rx1, ry1 = boxes[right]
                if lx1 < rx0 or rx1 < lx0 or ly1 < ry0 or ry1 < ly0:
                    continue
                relation = polygon_relation(
                    [self.outlines[left], *self.hole_loops[left]],
                    [self.outlines[right], *self.hole_loops[right]],
                )
                kind = str(relation["kind"])
                if kind in {"partial_area_overlap", "full_containment_a_in_b",
                            "full_containment_b_in_a"}:
                    result.append((left, right, kind))
        return result

    def escape_until_it_compiles(self, limit: int = 40) -> list[dict[str, Any]]:
        """Compile, and each time the authoring compiler refuses a sector, escape it.

        This is a measurement, not a repair.  Each refusal names a class of
        geometry original designers drew and the authoring model cannot express;
        the sector goes into ``NATIVE_ESCAPES`` with the compiler's own words,
        and the count is the honest coverage figure for the language.
        """
        from bloodmap.levelprog import LevelProgramError

        history: list[dict[str, Any]] = []
        for _ in range(limit):
            try:
                self.build_program().compile().compile()
                return history
            except Exception as exc:  # PlanarLayoutError and its subclasses
                message = str(exc)
                sector_ids = _sectors_named_in(message)
                fresh = [value for value in sector_ids if value not in self.escapes]
                if not fresh:
                    history.append({"sector": None, "reason": message, "resolved": False})
                    return history
                chosen = fresh[-1]
                self.escapes[chosen] = message
                history.append({"sector": chosen, "reason": message, "resolved": True})
        return history

    def build_program(self):
        """Build the program in memory, without going through the emitted text."""
        namespace: dict[str, Any] = {}
        exec(compile(self.emit(), "<emitted>", "exec"), namespace)  # noqa: S102
        return namespace["build_level"]()

    def _start_room(self) -> tuple[str, tuple[float, float], int] | None:
        """Where the level starts, named by its room rather than by a coordinate."""
        for sprite in self.level.sprites:
            fields = sprite["fields"]
            if int(fields["type"]) != 1:
                continue
            sector_id = int(fields["sector"])
            outline = self.outlines[sector_id]
            min_x, min_y, max_x, max_y = _bounds(outline)
            width = max(1, max_x - min_x)
            depth = max(1, max_y - min_y)
            local = (
                (int(fields["x"]) - min_x) / width,
                (int(fields["y"]) - min_y) / depth,
            )
            return ("sector_%03d" % sector_id, local, int(fields["angle"]) & 2047)
        return None

    # -- emission ---------------------------------------------------------
    def emit(self) -> str:
        lines: list[str] = []
        areas = self.areas()
        counts = {
            "sectors": len(self.level.sectors), "walls": len(self.level.walls),
            "sprites": len(self.level.sprites),
        }
        lines.append('"""%s as a hierarchical level program.' % self.path.stem)
        lines.append("")
        lines.append("Generated by tools.emit_level_program.  Read this file the way you would")
        lines.append("read any unfamiliar codebase: start at build_level, pick the area you care")
        lines.append("about, and open only that builder.  Each room states its own outline in its")
        lines.append("own coordinates, its own surface overrides, and its own sprites.")
        lines.append("")
        lines.append("AUTHORITY.  %s is the exact source of truth and this file is not." % self.path.name)
        lines.append("It is a re-expression of the decompiled hierarchy: the grouping is derived,")
        lines.append("the names are interpreted, and the geometry is reproduced sector for sector")
        lines.append("but recompiled, so wall ordering and portal indices are the compiler's own.")
        lines.append("")
        lines.append("    exact: %s" % json.dumps(counts))
        lines.append("    regenerate: python -m tools.emit_level_program %s" % self.path.as_posix())
        lines.append('"""')
        lines.append("")
        lines.append("from __future__ import annotations")
        lines.append("")
        lines.append("from bloodmap.levelprog import (")
        lines.append("    Frame, LevelProgram, Style, native_detail,")
        lines.append(")")
        lines.append("")
        if self.escapes:
            lines.append("#: Sectors the authoring model cannot express, and why.  They exist in")
            lines.append("#: %s and are deliberately absent here rather than repaired." % self.path.name)
            lines.append("NATIVE_ESCAPES = {")
            for sector_id, reason in sorted(self.escapes.items()):
                lines.append("    %d: %r," % (sector_id, reason))
            lines.append("}")
            lines.append("")
        else:
            lines.append("NATIVE_ESCAPES: dict[int, str] = {}")
            lines.append("")
        lines.append("U = 384          # one player body width")
        lines.append("PH = 0x1600      # one player standing height")
        lines.append("")

        builders: list[str] = []
        for area in areas:
            builders.append(self._emit_area(lines, area))

        lines.append("")
        lines.append("def build_level() -> LevelProgram:")
        lines.append('    """The whole level: %d areas, %d spaces, %d of %d sectors.'
                     % (len(areas), sum(len(a["spaces"]) for a in areas),
                        counts["sectors"] - len(self.escapes), counts["sectors"]))
        lines.append("")
        lines.append("    %d sector(s) are in NATIVE_ESCAPES and are not built here."
                     % len(self.escapes))
        lines.append('    """')
        style = self._style_for(list(range(len(self.level.sectors))))
        lines.append("    level = LevelProgram(")
        lines.append("        %r, name=%r," % (self.path.stem.lower(), self.path.stem))
        lines.append("        style=Style(")
        for key, value in sorted(style.items()):
            lines.append("            %s=%r," % (key, value))
        lines.append("            floor_z=0, clear_height=8 * PH,")
        lines.append("        ),")
        lines.append("    )")
        for name in builders:
            lines.append("    %s(level)" % name)
        pairs = self.overlapping_pairs()
        if pairs:
            lines.append("    # Sectors the original overlaps in XY on purpose.  Build allows it;")
            lines.append("    # the authoring compiler requires it to be said out loud.")
            lines.append("    rooms = {room.node_id: room for room in level.rooms()}")
            for left, right, kind in pairs:
                lines.append("    level.declare_stack(rooms[%r], rooms[%r], kind=%r)"
                             % ("sector_%03d" % left, "sector_%03d" % right, kind))
        start = self._start_room()
        if start is not None:
            room_path, local, angle = start
            lines.append("    # The native kMarkerPlayerStart sprite's sector.")
            lines.append("    level.set_start(")
            lines.append("        next(room for room in level.rooms() if room.path().endswith(%r)),"
                         % room_path)
            lines.append("        local=(%.3f, %.3f), angle=%d," % (local[0], local[1], angle))
            lines.append("    )")
        lines.append("    return level")
        lines.append("")
        lines.append("")
        lines.append("if __name__ == '__main__':")
        lines.append("    program = build_level()")
        lines.append("    print(program.tree())")
        lines.append("")
        return "\n".join(lines)

    def _emit_area(self, lines: list[str], area: dict[str, Any]) -> str:
        node = area["node"]
        number = node["id"].split(":")[1]
        naming = self.names.get(node["id"]) or {}
        label = _identifier(naming.get("name") or ("area_%s" % number))
        name = "build_%s" % label
        sectors = node["sources"]["sectors"]
        origin = _bounds([point for s in sectors for point in self.outlines[s]])[:2]
        geometry = node["geometry"]["player_relative"]
        lines.append("")
        lines.append("def %s(parent) -> object:" % name)
        lines.append('    """%s (%s): %d sectors, %.0f player areas, %d spaces.'
                     % (label, node["id"], len(sectors),
                        geometry["footprint_player_areas"], len(area["spaces"])))
        if naming.get("basis"):
            lines.append("")
            lines.append("    Named from measurement: %s" % naming["basis"])
        lines.append("")
        lines.append("    Origin is this area's own corner, so every outline below is local to it.")
        lines.append('    """')
        style = self._style_for(sectors)
        lines.append("    area = parent.assembly(")
        lines.append("        %r," % label)
        lines.append("        frame=Frame(%d, %d)," % origin)
        lines.append("        style=Style(%s),"
                     % ", ".join("%s=%r" % item for item in sorted(style.items())))
        lines.append("    )")
        zones = self._zones_for(area)
        if zones:
            # The middle of the tree.  Without it this function is one call per
            # space -- 123 of them on E2M3 -- and a reader who wants one wing of
            # the level has to read all of it.
            lines.append("    for build in (")
            for zone in zones:
                lines.append("        %s," % zone["builder"])
            lines.append("    ):")
            lines.append("        build(area)")
            lines.append("    return area")
            for zone in zones:
                self._emit_zone(lines, zone, origin, style)
        else:
            for space in area["spaces"]:
                lines.append("    %s(area)" % self._space_builder_name(space))
            lines.append("    return area")
            # Each space is its own function, appended after the area that calls
            # it, so "modify the staircase room" is one function to open rather
            # than a four-thousand-line area to scroll.
            for space in area["spaces"]:
                self._emit_space(lines, space, origin, style)
        return name

    def _zones_for(self, area: dict[str, Any]) -> list[dict[str, Any]]:
        """Group an assembly spaces into the proposed zones, in a stable order."""
        proposal = self.zones.get(area["node"]["id"])
        if not proposal or len(proposal) >= len(area["spaces"]):
            return []
        by_id = {space["id"]: space for space in area["spaces"]}
        assigned: set[str] = set()
        zones: list[dict[str, Any]] = []
        label_base = _identifier(self._area_label(area))
        for index, group in enumerate(proposal, start=1):
            members = [by_id[space_id] for space_id in group["spaces"] if space_id in by_id]
            if not members:
                continue
            assigned.update(space["id"] for space in members)
            members.sort(
                key=lambda item: -item["geometry"]["player_relative"]["footprint_player_areas"]
            )
            label = "zone_%02d" % index
            zones.append({
                "label": label,
                "builder": "build_%s_%s" % (label_base, label),
                "spaces": members,
                "facts": group,
            })
        leftovers = [space for space in area["spaces"] if space["id"] not in assigned]
        if leftovers:
            zones.append({
                "label": "zone_unsorted",
                "builder": "build_%s_zone_unsorted" % label_base,
                "spaces": leftovers,
                "facts": None,
            })
        return zones

    def _area_label(self, area: dict[str, Any]) -> str:
        node = area["node"]
        naming = self.names.get(node["id"]) or {}
        return naming.get("name") or ("area_%s" % node["id"].split(":")[1])

    def _emit_zone(self, lines: list[str], zone: dict[str, Any],
                   area_origin: tuple[int, int], area_style: dict[str, int]) -> None:
        sectors = [s for space in zone["spaces"] for s in space["sources"]["sectors"]]
        origin = _bounds([point for s in sectors for point in self.outlines[s]])[:2]
        local_origin = (origin[0] - area_origin[0], origin[1] - area_origin[1])
        facts = zone["facts"]
        lines.append("")
        lines.append("")
        lines.append("def %s(area) -> object:" % zone["builder"])
        lines.append('    """%s: %d spaces, %d sectors.'
                     % (zone["label"], len(zone["spaces"]), len(sectors)))
        lines.append("")
        if facts:
            lines.append("    Grouped from measurement rather than from a name: median floor z")
            lines.append("    %d, %.0f%% of its sectors open to the sky, dominant surfaces %s,"
                         % (facts["median_floor_z"], 100 * facts["sky_fraction"],
                            facts["dominant_tiles"][:3]))
            lines.append("    centred at %s player widths. Seeded on %s."
                         % (facts["centroid_player_widths"], facts["seed"]))
        else:
            lines.append("    The spaces no proposed group claimed. They are here so the level")
            lines.append("    is complete, not because they belong together.")
        lines.append("")
        lines.append("    Origin is the corner of this zone, so outlines below are local to it.")
        lines.append('    """')
        style = self._style_for(sectors)
        overrides = {k: v for k, v in style.items() if area_style.get(k) != v}
        lines.append("    zone = area.assembly(")
        lines.append("        %r, frame=Frame(%d, %d)," % (zone["label"], *local_origin))
        if overrides:
            lines.append("        style=Style(%s),"
                         % ", ".join("%s=%r" % item for item in sorted(overrides.items())))
        lines.append("    )")
        for space in zone["spaces"]:
            lines.append("    %s(zone)" % self._space_builder_name(space))
        lines.append("    return zone")
        for space in zone["spaces"]:
            self._emit_space(lines, space, origin, style)

    def _space_builder_name(self, space: dict[str, Any]) -> str:
        """A unique function name per space.

        Space ids restart at 001 inside every assembly, so the local part alone
        collides across areas and silently drops whole spaces from the program.
        The interpreted name wins when there is one, because that is what a
        reader will search for.
        """
        naming = self.names.get(space["id"]) or {}
        if naming.get("name"):
            return "build_" + _identifier(naming["name"])
        assembly, _, local = space["id"].partition("/")
        return "build_" + _identifier(f"{assembly}_{local}")

    def _emit_space(self, lines: list[str], space: dict[str, Any],
                    area_origin: tuple[int, int], area_style: dict[str, int]) -> None:
        sectors = space["sources"]["sectors"]
        footprint = space["geometry"]["player_relative"]["footprint_player_areas"]
        naming = self.names.get(space["id"]) or {}
        identifier = self._space_builder_name(space)[len("build_"):]
        origin = _bounds([point for s in sectors for point in self.outlines[s]])[:2]
        local_origin = (origin[0] - area_origin[0], origin[1] - area_origin[1])
        structures = sorted({
            self.structure_of[s]["kind"] for s in sectors if s in self.structure_of
        })
        note = "%.0f player areas, %d sector%s%s" % (
            footprint, len(sectors), "" if len(sectors) == 1 else "s",
            (", contains " + ", ".join(structures)) if structures else "",
        )
        style = self._style_for(sectors)
        overrides = {k: v for k, v in style.items() if area_style.get(k) != v}
        space_var = "space"
        lines.append("")
        lines.append("")
        lines.append("def %s(area) -> object:" % self._space_builder_name(space))
        lines.append('    """%s: %s.' % (identifier, note))
        if naming.get("basis"):
            lines.append("")
            lines.append("    Named from measurement: %s" % naming["basis"])
        lines.append("")
        lines.append("    Origin is this space's own corner; every outline below is local to it.")
        lines.append('    """')
        lines.append("    %s = area.assembly(" % space_var)
        lines.append("        %r, frame=Frame(%d, %d)," % (identifier, *local_origin))
        if overrides:
            lines.append("        style=Style(%s),"
                         % ", ".join("%s=%r" % item for item in sorted(overrides.items())))
        lines.append("        note=%r," % note)
        lines.append("    )")
        for sector_id in sectors:
            if sector_id in self.escapes:
                lines.append("    # sector %d is in NATIVE_ESCAPES: %s"
                             % (sector_id, self.escapes[sector_id]))
                continue
            self._emit_sector(lines, space_var, sector_id, origin, style)
        lines.append("    return space")

    def _emit_sector(self, lines: list[str], space_var: str, sector_id: int,
                     space_origin: tuple[int, int], space_style: dict[str, int]) -> None:
        outline = self.outlines[sector_id]
        local = [(x - space_origin[0], y - space_origin[1]) for x, y in outline]
        fields = self.level.sectors[sector_id]["fields"]
        floor_z, ceiling_z = int(fields["floor_z"]), int(fields["ceiling_z"])
        own = self._style_for([sector_id])
        overrides = {k: v for k, v in own.items() if space_style.get(k) != v}
        overrides["floor_z"] = floor_z
        overrides["clear_height"] = floor_z - ceiling_z
        structure = self.structure_of.get(sector_id)
        role = {"stepped_run": "stair", "recess": "detail", "landing": "gameplay"}.get(
            (structure or {}).get("kind"), "gameplay",
        )
        var = "s%03d" % sector_id
        faces = _face_names(local)
        lines.append("    %s = %s.room(" % (var, space_var))
        lines.append("        %r," % ("sector_%03d" % sector_id))
        lines.append("        [%s]," % ", ".join("(%d, %d)" % point for point in local))
        if faces:
            lines.append("        faces={%s}," % ", ".join(
                "%r: %d" % item for item in sorted(faces.items(), key=lambda kv: kv[1])
            ))
        lines.append("        role=%r," % role)
        lines.append("        style=Style(%s),"
                     % ", ".join("%s=%r" % item for item in sorted(overrides.items())))
        lines.append("        note=%r," % (
            "part of %s" % structure["id"] if structure else "native sector %d" % sector_id
        ))
        lines.append("    )")
        for hole in self.hole_loops.get(sector_id) or []:
            local_hole = [(x - space_origin[0], y - space_origin[1]) for x, y in hole]
            lines.append("    %s.carve([%s])  # a native inner loop of this sector"
                         % (var, ", ".join("(%d, %d)" % point for point in local_hole)))
        sprites = self.sprites_by_sector.get(sector_id) or []
        if sprites:
            lines.append("    %s.decorate(" % var)
            for sprite_id in sprites[:24]:
                sprite = self.level.sprites[sprite_id]["fields"]
                picnum = int(sprite["picnum"])
                pixels = self.art_sizes.get(picnum)
                height = (
                    pixels[1] * int(sprite["y_repeat"]) * 4 / PLAYER_HEIGHT
                    if pixels else None
                )
                # A decompilation states the repeats the original used.  Changing
                # them to a target height would be inventing evidence; the height
                # in the comment is there to make the number mean something.
                lines.append(
                    "        native_detail(%r, %d, x_repeat=%d, y_repeat=%d, "
                    "type=%d, cstat=%d, shade=%d),  # native sprite %d%s"
                    % ("sprite_%03d" % sprite_id, picnum,
                       int(sprite["x_repeat"]), int(sprite["y_repeat"]),
                       int(sprite["type"]), int(sprite["cstat"]), int(sprite["shade"]),
                       sprite_id,
                       ("  ~%.1f player heights" % height) if height else "  (tile not in ART)")
                )
            if len(sprites) > 24:
                lines.append("        # %d more native sprites in this sector"
                             % (len(sprites) - 24))
            lines.append("    )")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--art-dir", help="Blood ART directory, for real sprite sizes")
    parser.add_argument("--names", help="JSON of node id -> {name, basis} interpretations")
    parser.add_argument("--areas", help="an llmapper.area-proposals document, for the middle layer")
    parser.add_argument("--escape-until-compiles", action="store_true",
                        help="escape sectors the authoring compiler refuses, and report them")
    args = parser.parse_args(argv)
    names = json.loads(pathlib.Path(args.names).read_text(encoding="utf-8")) if args.names else None
    areas_document = (
        json.loads(pathlib.Path(args.areas).read_text(encoding="utf-8")) if args.areas else None
    )
    emitter = ProgramEmitter(pathlib.Path(args.map), art_dir=args.art_dir, names=names,
                             areas_document=areas_document)
    history: list[dict[str, Any]] = []
    if args.escape_until_compiles:
        history = emitter.escape_until_it_compiles()
    text = emitter.emit()
    out = pathlib.Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(json.dumps({
        "output": str(out),
        "lines": text.count("\n") + 1,
        "bytes": len(text),
        "areas": len(emitter.areas()),
        "sectors": len(emitter.level.sectors),
        "declared_stacks": len(emitter.overlapping_pairs()),
        "native_escapes": emitter.escapes,
        "escape_history": history,
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
