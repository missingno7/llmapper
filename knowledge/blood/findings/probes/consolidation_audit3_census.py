"""Third audit share: recount cheap campaign tallies quoted by findings."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import sys, math, statistics as st
from collections import Counter, defaultdict
from bloodmap.format import read_map
from bloodmap.corpus import campaign_maps
from bloodmap.model import record_fields as F, record_extra as X
maps = list(campaign_maps()); print("maps", len(maps))
no_ror = []; sec_total = {}; chan2 = Counter(); secmaps = set(); credit_maps=set()
gib_block = 0; block2 = 0; gibw = 0
start_dis = 0; start_n = 0
garg = set(); tesla = set()
barrels = defaultdict(list); cracks = defaultdict(list)
uw_f, uw_c = [], []
webs = Counter()
z456 = 0
sky_regions = 0; sky_multi = 0
for p in maps:
    name = p.stem.upper(); m = read_map(p)
    secs = [F(s) for s in m.sectors]; sx = [X(s) for s in m.sectors]
    ws = [F(w) for w in m.walls]; wx = [X(w) for w in m.walls]
    sps = [F(s) for s in m.sprites]; spx = [X(s) for s in m.sprites]
    # ror
    if not any(s["type"] in (6,7,9,10,11,12,13,14) and s["status"] == 0 for s in sps): no_ror.append(name)
    # secrets: who sends on channel 1 (total) and channel 2 (credit)
    for kind, recs, xs in (("sprite", sps, spx), ("sector", secs, sx), ("wall", ws, wx)):
        for r, x in zip(recs, xs):
            if not x: continue
            if x.get("tx_id") == 1: secmaps.add(name); sec_total.setdefault(name, []).append(x.get("command"))
            if x.get("tx_id") == 2: chan2[kind] += 1; credit_maps.add(name)
    # walls
    for w, x in zip(ws, wx):
        if w["next_sector"] >= 0 and (w["cstat"] & 1):
            block2 += 1
            if w["type"] == 511: gib_block += 1
        if w["type"] == 511: gibw += 1
    # starts
    for s, x in zip(sps, spx):
        if s["type"] == 1 and x and x.get("data_1") == 0:
            start_n += 1
            if (s["x"], s["y"]) != (m.header.get("x") if isinstance(getattr(m,"header",None), dict) else None, None): pass
        if s["type"] == 252 or s["type"] == 253: pass
        if s["type"] in (204, 205): garg.add(name)  # stone gargoyle? checked below
        if s["type"] == 456: z456 += 1
        if s["type"] == 400: barrels[name].append((s["x"], s["y"], s["z"], s["cstat"], s["sector"]))
        if s["type"] == 408: cracks[name].append((s["x"], s["y"]))
        if s["picnum"] in (1069, 1070) and False: pass
    for f, x in zip(secs, sx):
        if x and x.get("underwater"):
            uw_f.append(f["floor_shade"]); uw_c.append(f["ceiling_shade"])
print("no ror markers on statnum 0:", len(no_ror), no_ror)
print("maps sending tx 1:", len(secmaps), "credit tx2 maps:", len(credit_maps), dict(chan2))
print("blocking two-sided wall records:", block2, "of them kWallGib:", gib_block, "gib walls total", gibw)
print("underwater sectors", len(uw_f), "floor median", st.median(uw_f), "ceil median", st.median(uw_c), "quartiles f", st.quantiles(uw_f, n=4), "c", st.quantiles(uw_c, n=4))
print("type 456 in campaign", z456)
# barrels: cluster within 1024
for name, bs in barrels.items():
    print("barrels", name, len(bs), [(b[0], b[1], b[3]) for b in bs][:12], "cracks", cracks.get(name, [])[:6])
