"""In E1M4, E1M1, E1M2, E3M1 and E3M2: four-walled sectors between a roofed and a sky-ceilinged sector whose floor stands above both and whose ceiling hangs below both (a window through a wall), with width, depth, sill and opening in bodies."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import statistics
import sys
from bloodmap.format import read_map
from bloodmap.corpus import corpus_map_path
from bloodmap.model import record_fields

BODY = 16960
total = 0
for name in sys.argv[1:] or ["E1M4", "E1M1", "E1M2", "E3M1", "E3M2"]:
    m = read_map(corpus_map_path(name))
    secs = [record_fields(s) for s in m.sectors]
    walls = [record_fields(w) for w in m.walls]
    rows = []
    for i, f in enumerate(secs):
        if f["wall_count"] != 4:
            continue
        ws = walls[f["wall_ptr"]:f["wall_ptr"] + 4]
        nbs = [w["next_sector"] for w in ws if w["next_sector"] >= 0]
        if len(nbs) != 2 or nbs[0] == nbs[1]:
            continue
        a, b = secs[nbs[0]], secs[nbs[1]]
        if bool(a["ceiling_stat"] & 1) == bool(b["ceiling_stat"] & 1):
            continue
        if not (f["floor_z"] < min(a["floor_z"], b["floor_z"]) and f["ceiling_z"] > max(a["ceiling_z"], b["ceiling_z"])):
            continue
        lens = []
        for k, w in enumerate(ws):
            n = ws[(k + 1) % 4]
            lens.append(abs(n["x"] - w["x"]) + abs(n["y"] - w["y"]))
        red = [lens[k] for k, w in enumerate(ws) if w["next_sector"] >= 0]
        white = [lens[k] for k, w in enumerate(ws) if w["next_sector"] < 0]
        inside = a if not a["ceiling_stat"] & 1 else b
        rows.append((min(red), max(white), (inside["floor_z"] - f["floor_z"]) / BODY, (f["floor_z"] - f["ceiling_z"]) / BODY))
    total += len(rows)
    if rows:
        print(name, len(rows), "width", sorted(r[0] for r in rows), "depth", sorted(r[1] for r in rows),
              "sill median %.2f" % statistics.median(r[2] for r in rows), "opening median %.2f" % statistics.median(r[3] for r in rows))
    else:
        print(name, 0)
print("total", total)
