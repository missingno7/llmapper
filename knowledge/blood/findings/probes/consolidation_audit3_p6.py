"""Player-start markers per campaign map (types 1 and 2), a few wall and switch records (E1M2 s34, the DOOR-CURTAINS lesson), and the wall lengths of E3M1's ceiling-lifting doors that are shut at rest."""
import math
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from bloodmap.corpus import campaign_maps, corpus_map_path
from bloodmap.format import read_map
from bloodmap.model import record_extra as X, record_fields as F


@lru_cache(None)
def M(name):
    return read_map(corpus_map_path(name))


def sec(name, i):
    m = M(name); return F(m.sectors[i]), X(m.sectors[i])


def walls(name, i):
    m = M(name); f = F(m.sectors[i])
    return [(j, F(m.walls[j]), X(m.walls[j])) for j in range(f["wall_ptr"], f["wall_ptr"] + f["wall_count"])]


# start markers per campaign map
c1 = Counter(); c2 = Counter()
for p in campaign_maps():
    m = read_map(p); nm = p.stem.upper()
    for s in m.sprites:
        f = F(s)
        if f["type"] == 1: c1[nm] += 1
        if f["type"] == 2: c2[nm] += 1
print("type1 per map", Counter(c1.values()), "type2 per map", Counter(c2.values()))
# E1M2 s34 walls
print("E1M2 s34 wall cstats", [(j, w["cstat"]) for j, w, _ in walls("E1M2", 34)])
# DOOR-CURTAINS
try:
    print("DC s3", sec("DOOR-CURTAINS", 3)[1] and {k: v for k, v in sec("DOOR-CURTAINS", 3)[1].items() if k in ("rx_id","tx_id","trigger_wall_push")})
    m = M("DOOR-CURTAINS")
    for j in (38, 39, 40):
        x = X(m.walls[j]); print("DC wall", j, x and {k: v for k, v in x.items() if v and k in ("tx_id","rx_id","trigger_push","command")})
except Exception as e: print("DC err", e)
# E3M1 z doors widths
m = M("E3M1")
for i, s in enumerate(m.sectors):
    f = F(s); x = X(s)
    if f["type"] != 600 or not x: continue
    if x["on_ceiling_z"] != x["off_ceiling_z"] and x["on_floor_z"] == x["off_floor_z"] and min(x["on_floor_z"]-x["on_ceiling_z"], x["off_floor_z"]-x["off_ceiling_z"]) == 0:
        ws = walls("E3M1", i); L = []
        for j, w, _ in ws:
            p2 = F(m.walls[w["point2"]]); L.append(int(math.hypot(p2["x"]-w["x"], p2["y"]-w["y"])))
        print("E3M1 door", i, sorted(L))
