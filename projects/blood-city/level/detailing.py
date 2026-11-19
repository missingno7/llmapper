"""Detail moves: what a room's shape WEARS, declared where the room is.

The owner, 2026-11-18: "Some things you created are simplistic and have
certain shapes, but they don't look sophisticated, there is no combination
of decals and textures making it look like something."

The level could say what a room IS (its outline, its tile, its lamps) and
nothing finer: one region had one wall tile, so a machine hall was a box
of pressed metal with shapes standing in it. Blood's rooms are composed
at the scale below the room -- a control face let into a wall, a band of
pipes, a gauge over a hatch -- and each of those is a WALL RECORD of its
own with its own tile, cut out of the run by two vertices.

``panel``   a stretch of one solid wall that wears another tile: declared
            by its two ends in world coordinates. `split` cuts the vertices
            before compile, `paint` dresses the record after it.
``decal``   a wall-aligned sprite on a panel or wall (through `wallplane`,
            so two things never share a place).

A panel stands on its floor and begins at its own left end, showing whole
repeats of its tile (`fit`), because most of Blood's technical tiles are
pictures of a thing -- a machine front, a pipe rack -- and half a picture
is the fault the owner named in the shops ("shelves aren't aligned with
textures").

`tools.place_character` is the measure this serves: it counts the layers a
place carries against the campaign's rooms of its size.
"""

from __future__ import annotations

from typing import Any

#: every panel declared this build: dicts of region_id, a, b, tile, fields
PANELS: list[dict] = []


def reset() -> None:
    PANELS.clear()


def panel(region_id: str, a, b, tile: int, *, fit: bool = True,
          shade: int | None = None, pal: int | None = None,
          storeys: float | None = None, peg: str = "floor",
          note: str = "") -> dict:
    """Declare that the solid wall from `a` to `b` wears `tile`.

    `storeys` is how many times the tile is stacked up the wall's own
    height; left unset the tile keeps the scale the campaign draws it at
    (y_repeat 8: 256 z a texel).
    """
    spec = {"region_id": region_id, "a": (int(a[0]), int(a[1])),
            "b": (int(b[0]), int(b[1])), "tile": int(tile), "fit": fit,
            "shade": shade, "pal": pal, "storeys": storeys, "note": note,
            "peg": peg,
            "painted": 0, "records": []}
    PANELS.append(spec)
    return spec


def _on(point, a, b) -> bool:
    (px, py), (ax, ay), (bx, by) = point, a, b
    if (bx - ax) * (py - ay) != (by - ay) * (px - ax):
        return False
    return (min(ax, bx) <= px <= max(ax, bx)
            and min(ay, by) <= py <= max(ay, by))


def _cut(loop, points) -> tuple[tuple, int]:
    loop = [(int(x), int(y)) for x, y in loop]
    added = 0
    for point in points:
        if point in loop:
            continue
        for i in range(len(loop)):
            if _on(point, loop[i], loop[(i + 1) % len(loop)]):
                loop.insert(i + 1, point)
                added += 1
                break
    return tuple(loop), added


def split(layout) -> dict:
    """Give every panel its two vertices, before compile."""
    added = 0
    for spec in PANELS:
        region = layout.regions.get(spec["region_id"])
        if region is None:
            continue
        ends = (spec["a"], spec["b"])
        region.outer, n = _cut(region.outer, ends)
        added += n
        holes = []
        for hole in region.holes:
            hole, n = _cut(hole, ends)
            added += n
            holes.append(hole)
        region.holes = tuple(holes)
    return {"panels": len(PANELS), "vertices": added}


def _f(item: Any) -> dict:
    return item.get("fields", item) if isinstance(item, dict) else item.fields


def paint(level, compiled, art_sizes) -> dict:
    """Dress every record lying on a declared panel, after compile."""
    owner: dict[int, int] = {}
    for index, sector in enumerate(level.sectors):
        s = _f(sector)
        for w in range(int(s["wall_ptr"]),
                       int(s["wall_ptr"]) + int(s["wall_count"])):
            owner[w] = index
    report = {"panels": len(PANELS), "records": 0, "unpainted": []}
    for spec in PANELS:
        allocation = compiled.allocations.get(spec["region_id"])
        sector_id = getattr(allocation, "sector_id", None)
        for index, wall in enumerate(level.walls):
            f = _f(wall)
            if int(f["next_sector"]) >= 0:
                continue
            if sector_id is not None and owner.get(index) != sector_id:
                continue
            n = _f(level.walls[int(f["point2"])])
            p0 = (int(f["x"]), int(f["y"]))
            p1 = (int(n["x"]), int(n["y"]))
            if p0 == p1 or not (_on(p0, spec["a"], spec["b"])
                                and _on(p1, spec["a"], spec["b"])):
                continue
            f["picnum"] = spec["tile"]
            if spec["shade"] is not None:
                f["shade"] = spec["shade"]
            if spec["pal"] is not None:
                f["pal"] = spec["pal"]
            size = art_sizes.get(spec["tile"])
            if spec["fit"] and size:
                width, height = size
                length = abs(p1[0] - p0[0]) + abs(p1[1] - p0[1])
                f["x_panning"] = 0
                f["y_panning"] = 0
                if spec["peg"] == "floor":
                    f["cstat"] = int(f["cstat"]) | 4      # stands on its floor
                else:
                    f["cstat"] = int(f["cstat"]) & ~4     # hangs from the roof
                sector = _f(level.sectors[owner[index]])
                clear = abs(int(sector["floor_z"]) - int(sector["ceiling_z"]))
                y_repeat = 8
                if spec["storeys"]:
                    y_repeat = max(1, min(255, round(
                        2048 * height * spec["storeys"] / clear)))
                    f["y_repeat"] = y_repeat
                #: whole pictures across, each as near its drawn proportion
                #: as a whole count allows
                repeats = max(1, round(length * (y_repeat / 8.0)
                                       / (width * 16)))
                f["x_repeat"] = min(255, max(1, repeats * width // 8))
            spec["painted"] += 1
            spec.setdefault("records", []).append(index)
            report["records"] += 1
        if not spec["painted"]:
            report["unpainted"].append(spec["note"] or spec["tile"])
    return report
