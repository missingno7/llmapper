import sys; sys.path.insert(0, "work/consolidation/audit3")
from lib import *
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
