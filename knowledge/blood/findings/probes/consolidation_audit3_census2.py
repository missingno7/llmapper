"""Third audit share: gargoyles and Teslas, barrel groups and cracks, type 456."""
import sys, math; sys.path.insert(0, ".")
from bloodmap.format import read_map
from bloodmap.corpus import campaign_maps
from bloodmap.model import record_fields as F, record_extra as X
garg, gt = [], []
groups_all = []
for p in campaign_maps():
    name = p.stem.upper(); m = read_map(p)
    sps = [(k, F(s), X(s)) for k, s in enumerate(m.sprites)]
    ts = {s["type"] for _, s, _ in sps}
    # dudes can also be spawned via data fields; count placed only
    if ts & {207, 209}:
        garg.append(name)
        if ts & {45}: gt.append(name)
    for k, s, x in sps:
        if s["type"] == 456: print("456", name, k, s["picnum"])
    bs = [(s["x"], s["y"]) for _, s, _ in sps if s["type"] == 400]
    cr = [(s["x"], s["y"]) for _, s, _ in sps if s["type"] == 408]
    # single-link clusters at 1024
    left = list(range(len(bs))); seen = set()
    for i in range(len(bs)):
        if i in seen: continue
        comp = [i]; seen.add(i)
        for a in comp:
            for j in range(len(bs)):
                if j not in seen and math.dist(bs[a], bs[j]) <= 1024: seen.add(j); comp.append(j)
        near = min((math.dist(bs[a], c) for a in comp for c in cr), default=None)
        groups_all.append((name, len(comp), None if near is None else int(near)))
print("maps with a stone gargoyle (207/209):", len(garg), garg, "of them with a Tesla (item 45):", len(gt))
from collections import Counter
print("barrel groups by size:", sorted(Counter(g[1] for g in groups_all).items()))
for size in (1, 2, 3):
    gs = [g for g in groups_all if g[1] == size]
    print(size, len(gs), "within 1200 of a crack:", sum(1 for g in gs if g[2] is not None and g[2] <= 1200))
print([g for g in groups_all if g[1] >= 3])
