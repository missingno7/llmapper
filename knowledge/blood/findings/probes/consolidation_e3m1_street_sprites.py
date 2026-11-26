"""What stands in E3M1's sky-ceilinged sectors: every sprite there by type, and the visible type-0 ones by tile."""
import sys; sys.path.insert(0, ".")
from collections import Counter
from bloodmap.corpus import corpus_map_path
from bloodmap.format import read_map
from bloodmap.model import record_fields as F
m = read_map(corpus_map_path("E3M1"))
open_sky = {i for i, s in enumerate(m.sectors) if F(s)["ceiling_stat"] & 1}
types, plain = Counter(), []
for k, sp in enumerate(m.sprites):
    f = F(sp)
    if f["sector"] not in open_sky:
        continue
    types[f["type"]] += 1
    if f["type"] == 0 and not f["cstat"] & 32768:          # bit 32768: invisible
        plain.append((k, f["picnum"], f["cstat"]))
    if f["type"] == 417:
        print("type 417:", k, "tile", f["picnum"])
print("sprites in sky sectors by type:", dict(sorted(types.items())))
print("visible type-0 sprites (index, tile, cstat):", plain)
