"""Lamp tiles by how many sprites the player can shoot out (a thing of types 400-433, or a switch 20-22 triggered by vector or impact), over the campaign and the corpus views."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from collections import Counter
from bloodmap.format import read_map
from bloodmap.corpus import campaign_maps, list_corpus_maps
from bloodmap.model import record_fields, record_extra

TILES = (2290, 2288, 693, 676, 692, 944, 945, 641, 640, 506)


def shot(f, x):
    if 400 <= f["type"] < 434:
        return True
    return f["type"] in (20, 21, 22) and bool(x.get("trigger_vector") or x.get("trigger_impact"))


views = {"campaign": [str(p) for p in campaign_maps()]}
for v in ("original", "reference"):
    views[v] = [str(m.path) for m in list_corpus_maps(view=v)]
for name, paths in views.items():
    n, b = Counter(), Counter()
    read = 0
    for p in paths:
        try:
            d = read_map(p)
        except Exception:
            continue
        read += 1
        for s in d.sprites:
            f = record_fields(s)
            if f["picnum"] in TILES:
                n[f["picnum"]] += 1
                b[f["picnum"]] += shot(f, record_extra(s) or {})
    print(name, len(paths), "listed,", read, "read:", ", ".join(f"{t}: {b[t]} of {n[t]}" for t in TILES))
