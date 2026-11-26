"""Count visible light-tile sprites standing in parallax-ceiling sectors, per campaign map (+DWE3M1, DWE3M10)."""
import sys, collections
from bloodmap.format import read_map
from bloodmap.corpus import campaign_maps, corpus_map_path
from bloodmap.model import record_fields, record_extra

LIGHT = {506, 2101, 641, 3566, 580, 1701, 501, 2493, 2290, 2288, 795, 796, 693, 640, 676, 677, 570, 554, 550, 560, 938}
paths = list(campaign_maps()) + [corpus_map_path(n) for n in ("DWE3M1", "DWE3M10")]
total = 0
for p in paths:
    m = read_map(p)
    hits = collections.Counter(); bright = []
    for i, s in enumerate(m.sprites):
        f = record_fields(s)
        sec = f["sector"]
        if sec < 0 or sec >= len(m.sectors):
            continue
        sf = record_fields(m.sectors[sec])
        if not sf["ceiling_stat"] & 1:
            continue
        invisible = bool(f["cstat"] & 32768)
        if f["picnum"] in LIGHT and not invisible and f["status"] != 10:
            hits[f["picnum"]] += 1
            if p.stem.upper() in ("E3M1", "E2M3", "E2M2", "DWE3M1"):
                bright.append((i, f["picnum"], f["type"], f["x_repeat"], f["y_repeat"], f["status"], f["cstat"]))
        if f["shade"] <= -20 and p.stem.upper() == "E3M1":
            bright_any = (i, f["picnum"], f["cstat"], f["status"], f["type"])
    n = sum(hits.values()); total += n if p.stem.upper().startswith("E") else 0
    if n:
        print(p.stem.upper(), n, dict(hits), bright[:12])
print("campaign total", total)
