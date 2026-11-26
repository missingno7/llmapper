"""Five sectors read whole (E1M2 s213, E3M2 s82 and s87, DWE1M4 s229 and s230: heights, tiles, neighbours, walls, sprites) and the centres of E3M4's pews s280-285."""
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


def centroid(name, i):
    ws = walls(name, i); xs = [w[1]["x"] for w in ws]; ys = [w[1]["y"] for w in ws]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def sprites_in(name, i):
    m = M(name)
    return [(k, F(s), X(s)) for k, s in enumerate(m.sprites) if F(s)["sector"] == i]


def show(mp, i):
    f, x = sec(mp, i)
    nb = sorted({w[1]["next_sector"] for w in walls(mp, i) if w[1]["next_sector"] >= 0})
    print(mp, i, "type", f["type"], "floor", f["floor_z"], "ceil", f["ceiling_z"], "fpic", f["floor_picnum"], "cpic", f["ceiling_picnum"], "fstat", f["floor_stat"], "cstat", f["ceiling_stat"])
    print("   nb", [(n, sec(mp, n)[0]["floor_z"], sec(mp, n)[0]["ceiling_z"]) for n in nb])
    ws = walls(mp, i); xs=[w[1]["x"] for w in ws]; ys=[w[1]["y"] for w in ws]
    print("   bbox", min(xs), max(xs), min(ys), max(ys), "walls", [(w[0], w[1]["picnum"], w[1]["cstat"], w[1]["next_sector"]) for w in ws][:8])
    print("   sprites", [(k, s["picnum"], s["type"], s["cstat"], s["z"]) for k, s, _ in sprites_in(mp, i)][:12])


for mp, i in [("E1M2",213),("E3M2",82),("E3M2",87),("DWE1M4",229),("DWE1M4",230)]:
    show(mp, i)
for i in range(280,286): print(i, centroid("E3M4", i))
