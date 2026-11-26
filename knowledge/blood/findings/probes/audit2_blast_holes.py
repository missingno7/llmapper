"""Recount blast holes in the 43 campaign maps: type 600 sectors shut at rest that open within a tenth (busy_time_a <= 1), their width along the wall and opening in bodies."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import os
import statistics
import sys

from bloodmap.corpus import campaign_maps
from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields

BODY = 16960


def quartiles(values):
    values = sorted(values)
    q = statistics.quantiles(values, n=4, method="inclusive")
    return {"n": len(values), "q1": q[0], "median": q[1], "q3": q[2]}


widths, openings, rows = [], [], []
for path in campaign_maps():
    disk = read_map(path)
    for index, sector in enumerate(disk.sectors):
        f = record_fields(sector)
        if int(f["type"]) != 600:
            continue
        x = record_extra(sector) or {}
        if int(f["ceiling_z"]) != int(f["floor_z"]):
            continue
        if int(x.get("busy_time_a", 0) or 0) > 1:
            continue
        start, count = int(f["wall_ptr"]), int(f["wall_count"])
        xs = [int(record_fields(disk.walls[w])["x"]) for w in range(start, start + count)]
        ys = [int(record_fields(disk.walls[w])["y"]) for w in range(start, start + count)]
        width = max(max(xs) - min(xs), max(ys) - min(ys))
        opening = (int(x.get("on_floor_z", 0)) - int(x.get("on_ceiling_z", 0))) / BODY
        widths.append(width)
        openings.append(opening)
        rows.append((path.stem.upper(), index, width, round(opening, 2)))
print("pieces", len(rows), "in", len({r[0] for r in rows}), "maps")
print("width (longer bounding-box side)", quartiles(widths))
print("opening in bodies", {k: round(v, 2) if isinstance(v, float) else v for k, v in quartiles(openings).items()})
e3m4 = [r for r in rows if r[0] == "E3M4"]
print("E3M4", e3m4)

# The population of knowledge/blood/findings/probes/sewer-study_breach_shapes.json (185 pieces, 96 holes by channel):
import json
import pathlib
from collections import defaultdict

kept = json.loads(pathlib.Path("knowledge/blood/findings/probes/sewer-study_breach_shapes.json").read_text())
holes = defaultdict(list)
by_map = defaultdict(list)
for row in kept:
    by_map[row["map"]].append(row)
for path in campaign_maps():
    name = path.stem.upper()
    if name not in by_map:
        continue
    disk = read_map(path)
    for row in by_map[name]:
        f = record_fields(disk.sectors[row["sector"]])
        start, count = int(f["wall_ptr"]), int(f["wall_count"])
        pts = [(int(record_fields(disk.walls[w])["x"]), int(record_fields(disk.walls[w])["y"])) for w in range(start, start + count)]
        holes[(name, row["ch"])].append((pts, (row["on_floor"] - row["on_ceil"]) / BODY))
hole_widths, hole_openings, piece_widths = [], [], []
for key, pieces in holes.items():
    xs = [p[0] for pts, _o in pieces for p in pts]
    ys = [p[1] for pts, _o in pieces for p in pts]
    hole_widths.append(max(max(xs) - min(xs), max(ys) - min(ys)))
    hole_openings.append(max(o for _p, o in pieces))
    for pts, _o in pieces:
        piece_widths.append(max(max(p[0] for p in pts) - min(p[0] for p in pts), max(p[1] for p in pts) - min(p[1] for p in pts)))
print("kept population: holes", len(holes), "pieces", len(piece_widths))
print("hole width (longer side of the pieces' joint box)", quartiles(hole_widths))
print("piece width", quartiles(piece_widths))
print("hole opening, bodies (largest piece)", {k: round(v, 2) if isinstance(v, float) else v for k, v in quartiles(hole_openings).items()})
