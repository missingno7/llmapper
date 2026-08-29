"""What the campaign's plan actually does about unorderable bunches.

Two hypotheses, measured rather than assumed:

1. **Turned entrances.** Stacked rooms open on facades at roughly 90 degrees, so
   no vertical slice looks into both (the owner's hypothesis).
2. **Plan lines.** Maps with fewer conflicts use more distinct wall lines --
   jogs, offsets, non-orthogonal walls -- so `wallfront` is not handed collinear
   same-height neighbours.

Neither is about z. `wallfront` (engine.cpp:2227) never reads it.

.. code-block:: bash

    python -m tools.measure_draw_order maps/blood/BB4.MAP
    python -m tools.measure_draw_order projects/vertical-fragment/level/MALTX.MAP \\
        --conflicts projects/vertical-fragment/reports/render-conflicts.json
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
from collections import Counter
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from bloodmap.format import read_map
from bloodmap.layers import OVERLAPPING_KINDS, STANDING_HEIGHT as STANDING
from bloodmap.planar_geom import polygon_relation, same_ground
from tools.mine_layers import sector_loops as _sector_loops

def sector_box(disk, sid: int) -> tuple[int, int, int, int]:
    loops = _sector_loops(disk, sid)
    pts = [p for loop in loops for p in loop]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def overlapping_sector_pairs(disk) -> list[tuple[int, int, str]]:
    """Sector pairs that share ground, the same predicate `layers.find_overlaps` uses."""
    n = len(disk.sectors)
    boxes = [sector_box(disk, i) for i in range(n)]
    out: list[tuple[int, int, str]] = []
    for i in range(n):
        ai = boxes[i]
        loops_i = _sector_loops(disk, i)
        outer_i = loops_i[0]
        for j in range(i + 1, n):
            aj = boxes[j]
            if ai[2] <= aj[0] or aj[2] <= ai[0] or ai[3] <= aj[1] or aj[3] <= ai[1]:
                continue
            loops_j = _sector_loops(disk, j)
            outer_j = loops_j[0]
            if same_ground(outer_i, outer_j):
                kind = "identical_footprint"
            else:
                kind = str(polygon_relation(loops_i, loops_j)["kind"])
                if kind not in OVERLAPPING_KINDS:
                    continue
            out.append((i, j, kind))
    return out


def plan_lines(disk) -> dict[str, Any]:
    """How many distinct supporting lines the walls occupy.

    An axis-aligned wall on x=k shares a vertical line with every other wall on
    x=k; `wallfront` returns -1 for any two of those whose segments overlap in y
    (engine.cpp:2227). Diagonals get their own (a, b, c) line.
    """
    vertical: set[int] = set()
    horizontal: set[int] = set()
    diagonal: set[tuple[int, int, int]] = set()
    walls = 0
    non_ortho = 0
    for wall in disk.walls:
        a = wall.fields
        b = disk.walls[int(a["point2"])].fields
        x1, y1, x2, y2 = int(a["x"]), int(a["y"]), int(b["x"]), int(b["y"])
        if (x1, y1) == (x2, y2):
            continue
        walls += 1
        if x1 == x2:
            vertical.add(x1)
        elif y1 == y2:
            horizontal.add(y1)
        else:
            non_ortho += 1
            dx, dy = x2 - x1, y2 - y1
            # ax + by = c, reduced.
            a_c, b_c, c_c = dy, -dx, dy * x1 - dx * y1
            g = math.gcd(math.gcd(a_c, b_c), c_c) or 1
            a_c, b_c, c_c = a_c // g, b_c // g, c_c // g
            if a_c < 0 or (a_c == 0 and b_c < 0):
                a_c, b_c, c_c = -a_c, -b_c, -c_c
            diagonal.add((a_c, b_c, c_c))
    lines = len(vertical) + len(horizontal) + len(diagonal)
    return {
        "walls": walls,
        "vertical_lines": len(vertical),
        "horizontal_lines": len(horizontal),
        "diagonal_lines": len(diagonal),
        "distinct_lines": lines,
        "walls_per_line": round(walls / lines, 3) if lines else None,
        "non_orthogonal_walls": non_ortho,
        "non_orthogonal_share": round(non_ortho / walls, 4) if walls else None,
    }


def _edge(disk, wid: int) -> tuple[tuple[int, int], tuple[int, int]]:
    a = disk.walls[wid].fields
    b = disk.walls[int(a["point2"])].fields
    return (int(a["x"]), int(a["y"])), (int(b["x"]), int(b["y"]))


def entrance_vector(disk, sid: int, *, exclude: set[int] | None = None) -> tuple[float, float] | None:
    """Length-weighted mean outward normal of this sector's walkable portals.

    Build loops wind clockwise, so the outward normal of (dx, dy) is (-dy, dx).
    Portals to `exclude` (the stacked partner) are skipped: those are the floor
    above or below, not an entrance.
    """
    skip = exclude or set()
    s = disk.sectors[sid].fields
    start, count = int(s["wall_ptr"]), int(s["wall_count"])
    nx = ny = 0.0
    for wid in range(start, start + count):
        w = disk.walls[wid].fields
        nxt = int(w["next_sector"])
        if nxt < 0 or nxt in skip:
            continue
        if int(w["cstat"]) & 1:
            continue  # blocking: not an entrance you walk through
        (x1, y1), (x2, y2) = _edge(disk, wid)
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length == 0:
            continue
        # outward
        nx += (-dy / length) * length
        ny += (dx / length) * length
    mag = math.hypot(nx, ny)
    if mag == 0:
        return None
    return (nx / mag, ny / mag)


def angle_between(a: tuple[float, float], b: tuple[float, float]) -> float:
    dot = max(-1.0, min(1.0, a[0] * b[0] + a[1] * b[1]))
    return math.degrees(math.acos(dot))


def stacked_entrance_angles(disk) -> dict[str, Any]:
    """For every overlapping pair, the angle between the two rooms' entrances.

    Derived: the vectors are the portal normals. Interpreted: 90 degrees means
    the two openings face perpendicular facades, which is the owner's hypothesis
    for why BB4 can stack three floors on one space.
    """
    pairs = overlapping_sector_pairs(disk)
    angles: list[float] = []
    missing = 0
    rows = []
    for left, right, kind in pairs:
        fl = int(disk.sectors[left].fields["floor_z"])
        fr = int(disk.sectors[right].fields["floor_z"])
        if abs(fl - fr) <= STANDING:
            continue  # a step, not a storey
        va = entrance_vector(disk, left, exclude={right})
        vb = entrance_vector(disk, right, exclude={left})
        if va is None or vb is None:
            missing += 1
            continue
        deg = angle_between(va, vb)
        angles.append(deg)
        rows.append({"sectors": [left, right], "kind": kind, "angle_deg": round(deg, 1),
                     "floor_z": [fl, fr]})
    if not angles:
        return {"stacked_pairs": 0, "missing_entrance": missing, "angles": []}
    ordered = sorted(angles)
    n = len(ordered)
    buckets = Counter(int(round(a / 15) * 15) for a in ordered)
    return {
        "stacked_pairs": n,
        "missing_entrance": missing,
        "mean_deg": round(sum(ordered) / n, 1),
        "median_deg": round(ordered[n // 2], 1),
        "share_within_30_of_90": round(sum(1 for a in ordered if abs(a - 90) <= 30) / n, 3),
        "share_within_30_of_0_or_180": round(
            sum(1 for a in ordered if a <= 30 or a >= 150) / n, 3),
        "buckets_15deg": {str(k): buckets[k] for k in sorted(buckets)},
        "pairs": rows,
    }


def _unique_pair_rows(rows: list[dict]) -> list[dict]:
    """One row per sector pair; `asked` is the total bunchfront questions."""
    by: dict[tuple[int, ...], dict] = {}
    for row in rows:
        key = tuple(row["sectors"])
        if key not in by:
            by[key] = dict(row)
            by[key]["asked"] = 0
        by[key]["asked"] += int(row.get("asked", 1))
    return sorted(by.values(), key=lambda r: (-r["asked"], r["sectors"]))


def classify_conflicts(disk, report: dict) -> dict[str, Any]:
    """Split renderer faults: overlapping pairs, coplanar neighbours, same-sector.

    Same-sector hits are a sector whose own walls lie on one line (a jog, a
    C-shape). Two-sector hits are the rooms-in-a-row fault. Overlapping hits
    are stacked storeys. Report all three; collapsing them hid the difference
    once already.
    """
    overlap = {(a, b) for a, b, _k in overlapping_sector_pairs(disk)}
    overlapping, coplanar, same = [], [], []
    two_views, same_views, overlap_views = set(), set(), set()
    for row in report.get("conflicts") or report.get("pairs") or ():
        raw = row["sectors"]
        if len(raw) != 2:
            continue
        left, right = int(raw[0]), int(raw[1])
        asked = row.get("asked", 1)
        view = row.get("view")
        if left == right:
            same.append({"sectors": [left, right], "asked": asked})
            if view:
                same_views.add(view)
            continue
        pair = (min(left, right), max(left, right))
        sl = disk.sectors[pair[0]].fields
        sr = disk.sectors[pair[1]].fields
        entry = {
            "sectors": list(pair),
            "asked": asked,
            "floor_z": [int(sl["floor_z"]), int(sr["floor_z"])],
            "ceiling_z": [int(sl["ceiling_z"]), int(sr["ceiling_z"])],
            "box": [sector_box(disk, pair[0]), sector_box(disk, pair[1])],
            "overlapping": pair in overlap,
        }
        if pair in overlap:
            overlapping.append(entry)
            if view:
                overlap_views.add(view)
        else:
            coplanar.append(entry)
            if view:
                two_views.add(view)
    views = int(report.get("views_rendered") or 0)
    bad = report.get("views_with_a_conflict") or []
    def rate(n):
        return round(1000 * n / views, 2) if views else None
    return {
        "views_rendered": views,
        "views_with_a_conflict": len(bad),
        "per_thousand": rate(len(bad)),
        "per_thousand_two_sector": rate(len(two_views | overlap_views)),
        "per_thousand_overlapping": rate(len(overlap_views)),
        "per_thousand_coplanar": rate(len(two_views)),
        "per_thousand_same_sector": rate(len(same_views)),
        "pairs_overlapping": _unique_pair_rows(overlapping),
        "pairs_coplanar": _unique_pair_rows(coplanar),
        "pairs_same_sector": _unique_pair_rows(same),
        "n_overlapping": len({tuple(p["sectors"]) for p in overlapping}),
        "n_coplanar": len({tuple(p["sectors"]) for p in coplanar}),
        "n_same_sector": len({tuple(p["sectors"]) for p in same}),
    }


def one_way_walls(disk) -> list[dict[str, Any]]:
    out = []
    for index, wall in enumerate(disk.walls):
        cstat = int(wall.fields["cstat"])
        if cstat & 32:
            out.append({
                "wall": index,
                "cstat": cstat,
                "blocking": bool(cstat & 1),
                "masked": bool(cstat & 16),
                "next_sector": int(wall.fields["next_sector"]),
                "over_picnum": int(wall.fields["over_picnum"]),
                "at": (int(wall.fields["x"]), int(wall.fields["y"])),
            })
    return out


def measure(disk) -> dict[str, Any]:
    overlaps = overlapping_sector_pairs(disk)
    return {
        "sectors": len(disk.sectors),
        "walls": len(disk.walls),
        "overlapping_pairs": len(overlaps),
        "plan": plan_lines(disk),
        "entrances": stacked_entrance_angles(disk),
        "one_way_walls": one_way_walls(disk),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map")
    parser.add_argument("--conflicts", default=None)
    parser.add_argument("-o", "--out", default=None)
    args = parser.parse_args(argv)
    disk = read_map(args.map)
    data = measure(disk)
    data["map"] = args.map
    if args.conflicts:
        report = json.loads(pathlib.Path(args.conflicts).read_text(encoding="utf-8"))
        data["conflicts"] = classify_conflicts(disk, report)
    text = json.dumps(data, indent=2)
    if args.out:
        pathlib.Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
