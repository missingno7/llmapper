"""E3M3's sewer corridors across their width: each sector's floor, ceiling, slopes and tiles along a line."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import sys, math
from bloodmap.corpus import corpus_map_path
from bloodmap.format import read_map
from bloodmap.model import record_fields as F, record_extra as X
from bloodmap.sector_geom import outline_and_holes
from shapely.geometry import Polygon, LineString

d = read_map(corpus_map_path("E3M3"))
polys = {}
for i in range(len(d.sectors)):
    try:
        polys[i] = Polygon(*outline_and_holes(d, i))
    except Exception:
        pass


def section(label, a, b):
    line = LineString([a, b])
    print(f"== {label}: {a} -> {b}")
    rows = []
    for i, p in polys.items():
        if not p.intersects(line):
            continue
        seg = p.intersection(line)
        if seg.length < 8:
            continue
        c = seg.centroid
        t = line.project(c)
        f = F(d.sectors[i]); x = X(d.sectors[i]) if d.sectors[i].extra is not None else {}
        rows.append((t, i, round(seg.length), int(f["floor_z"]), int(f["ceiling_z"]),
                     int(f["floor_heinum"]) if int(f["floor_stat"]) & 2 else 0,
                     int(f["ceiling_heinum"]) if int(f["ceiling_stat"]) & 2 else 0,
                     int(f["floor_picnum"]), int(f["ceiling_picnum"]),
                     {k: x.get(k) for k in ("pan_velocity", "pan_angle", "depth", "drag") if x and x.get(k)}))
    for t, i, w, fz, cz, fh, ch, fp, cp, xx in sorted(rows):
        print(f"  t={t:7.0f} sector {i:4d} width {w:5d} floor {fz:6d} ceil {cz:6d} "
              f"fheinum {fh:6d} cheinum {ch:6d} fpic {fp:5d} cpic {cp:5d} {xx}")


def centre(i):
    c = polys[i].centroid
    return (c.x, c.y)


# across channel 120 at its middle, both ways from it
cx, cy = centre(120)
mnx, mny, mxx, mxy = polys[120].bounds
horizontal = (mxx - mnx) > (mxy - mny)
if horizontal:
    section("across channel 120", (cx, cy - 3000), (cx, cy + 3000))
else:
    section("across channel 120", (cx - 3000, cy), (cx + 3000, cy))
for s in (162, 129, 134):
    if s in polys:
        cx, cy = centre(s); mnx, mny, mxx, mxy = polys[s].bounds
        if (mxx - mnx) > (mxy - mny):
            section(f"across {s}", (cx, cy - 3000), (cx, cy + 3000))
        else:
            section(f"across {s}", (cx - 3000, cy), (cx + 3000, cy))
