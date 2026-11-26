"""E1M2 s34, the host of things riding outside a moving body: its type, its sprites' bit 8192, which of its walls carry bit 16384."""
import sys; sys.path.insert(0, ".")
from bloodmap.corpus import corpus_map_path
from bloodmap.format import read_map
from bloodmap.model import record_fields as F, record_extra as X
from bloodmap.sector_geom import outline_and_holes
m = read_map(corpus_map_path("E1M2"))
S = 34
s = F(m.sectors[S]); x = X(m.sectors[S]) or {}
print("s34 type", s["type"], "markers", x.get("marker_0"), x.get("marker_1"))
for k, sp in enumerate(m.sprites):
    f = F(sp)
    if f["sector"] == S:
        print("  sprite", k, "tile", f["picnum"], "cstat", f["cstat"], "bit 8192" if f["cstat"] & 8192 else "")
first, n = s["wall_ptr"], s["wall_count"]
loops, cur, start = [], [], first
for w in range(first, first + n):                     # walls in loops: a loop closes where point2 returns to its start
    cur.append(w)
    if F(m.walls[w])["point2"] == start:
        loops.append(cur); cur = []; start = w + 1
loops.sort(key=len, reverse=True)
for i, loop in enumerate(loops):
    flagged = [w for w in loop if F(m.walls[w])["cstat"] & 16384]
    print("  loop", i, "walls", loop[0], "-", loop[-1], f"({len(loop)})", "flagged 16384:", flagged)
