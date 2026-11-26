import sys; sys.path.insert(0, "work/consolidation/audit3")
from lib import *
m = M("E1M4")
def who(ch):
    out = []
    for kind, recs in (("sprite", m.sprites), ("sector", m.sectors), ("wall", m.walls)):
        for k, r in enumerate(recs):
            x = X(r)
            if not x: continue
            if x.get("tx_id") == ch or x.get("rx_id") == ch:
                f = F(r)
                out.append((kind, k, f.get("type"), f.get("picnum"), "tx" if x.get("tx_id") == ch else "rx", x.get("command"), f.get("sector")))
    return out
for ch in (124, 106, 110, 200, 250, 108):
    print(ch, who(ch))
for k, s in enumerate(m.sprites):
    if F(s)["picnum"] == 967: print("bullseye", k, F(s)["sector"], X(s) and X(s).get("tx_id"))
