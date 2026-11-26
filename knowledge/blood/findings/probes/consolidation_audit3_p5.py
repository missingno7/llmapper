"""Five flights of steps (E3M1, E3M7, E6M5, E3M8, E4M5): each step's heights and its solid walls' tile, panning, repeat and length, to see whether a wall course runs on down the flight."""
import math
import sys
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from bloodmap.corpus import corpus_map_path
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


def flight(mp, secs):
    m = M(mp)
    for i in secs:
        f,_ = sec(mp,i)
        ws = walls(mp,i)
        row=[]
        for j,w,_x in ws:
            if w["next_sector"]>=0: continue
            p2 = F(m.walls[w["point2"]])
            L = math.hypot(p2["x"]-w["x"], p2["y"]-w["y"])
            row.append((j,w["picnum"],w["x_panning"],w["y_panning"],w["x_repeat"],w["y_repeat"],int(L),w["cstat"]))
        print(mp,i,"fz",f["floor_z"],"cz",f["ceiling_z"],"cst",f["ceiling_stat"],"hei",f.get("ceiling_heinum"),row)


flight("E3M1",[78,79,39]); flight("E3M7",[89,88,80]); flight("E6M5",[304,305,314]); flight("E3M8",[113,114,115]); flight("E4M5",[5,114,113])
