"""Walls with pan_always and a y panning velocity over the 43 campaign maps, by tile, with their velocities; and the three walls the waterfall finding cites."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from collections import Counter, defaultdict
from bloodmap.format import read_map
from bloodmap.corpus import campaign_maps, corpus_map_path
from bloodmap.model import record_fields, record_extra

tiles = Counter()
vel = defaultdict(Counter)
for p in campaign_maps():
    d = read_map(p)
    for w in d.walls:
        x = record_extra(w) or {}
        if x.get("pan_always") and x.get("pan_y_velocity"):
            t = record_fields(w)["picnum"]
            tiles[t] += 1
            vel[t][x["pan_y_velocity"]] += 1
print(tiles.most_common(8))
for t in (1005, 1120):
    print(t, sorted(vel[t].items()), "most common", vel[t].most_common(4))

for name, wi in (("E2M7", 482), ("E4M3", 59), ("E1M8", 1309)):
    d = read_map(corpus_map_path(name))
    f = record_fields(d.walls[wi])
    x = record_extra(d.walls[wi]) or {}
    own = next(i for i, s in enumerate(d.sectors)
               if record_fields(s)["wall_ptr"] <= wi < record_fields(s)["wall_ptr"] + record_fields(s)["wall_count"])
    o, n = record_fields(d.sectors[own]), f["next_sector"]
    nf = record_fields(d.sectors[n]) if n >= 0 else {}
    print(name, wi, "picnum", f["picnum"], "pan_always", x.get("pan_always"), "vy", x.get("pan_y_velocity"),
          "in s", own, "floor", o["floor_z"], "ceil", o["ceiling_z"], "next s", n, "floor", nf.get("floor_z"), "ceil", nf.get("ceiling_z"))
