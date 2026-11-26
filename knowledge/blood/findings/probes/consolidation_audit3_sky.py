"""Third audit share: does each connected outdoor region of a campaign map wear one sky picnum?"""
import sys; sys.path.insert(0, ".")
from collections import Counter
from bloodmap.format import read_map
from bloodmap.corpus import campaign_maps
from bloodmap.model import record_fields as F
tot = multi = 0; sizes = Counter(); bad = []
for p in campaign_maps():
    m = read_map(p); secs = [F(s) for s in m.sectors]; ws = [F(w) for w in m.walls]
    sky = [i for i, s in enumerate(secs) if s["ceiling_stat"] & 1]
    S = set(sky); seen = set()
    for i in sky:
        if i in seen: continue
        comp = [i]; seen.add(i)
        for a in comp:
            f = secs[a]
            for j in range(f["wall_ptr"], f["wall_ptr"] + f["wall_count"]):
                n = ws[j]["next_sector"]
                if n in S and n not in seen: seen.add(n); comp.append(n)
        pics = {secs[a]["ceiling_picnum"] for a in comp}
        tot += 1
        if len(pics) > 1: multi += 1; bad.append((p.stem, len(comp), sorted(pics)))
print("regions", tot, "with more than one sky picnum", multi)
print(bad[:15])
