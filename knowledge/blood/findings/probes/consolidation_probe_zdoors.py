"""Z-motion sector openings over the campaign: all type 600, and those whose ceiling moves while the floor stays."""
import statistics as st
from bloodmap.format import read_map
from bloodmap.corpus import campaign_maps
from bloodmap.model import record_fields, record_extra

allopen, ceil_only, shut_rest, floor_move = [], [], [], []
for p in campaign_maps():
    m = read_map(p)
    for s in m.sectors:
        f = record_fields(s)
        if f["type"] != 600:
            continue
        x = record_extra(s)
        if not x or "on_ceiling_z" not in x:
            continue
        on_c, off_c, on_f, off_f = x["on_ceiling_z"], x["off_ceiling_z"], x["on_floor_z"], x["off_floor_z"]
        opening = max(on_f - on_c, off_f - off_c)
        allopen.append(opening)
        if on_c != off_c and on_f == off_f:
            ceil_only.append(opening)
            if min(on_f - on_c, off_f - off_c) == 0:
                shut_rest.append(opening)
        if on_f != off_f:
            floor_move.append(opening)
def q(v):
    v = sorted(v); n = len(v)
    return n, st.median(v), v[n // 10] if n else None
print("all type 600", q(allopen))
print("ceiling moves, floor fixed", q(ceil_only))
print("  of those, shut in one pose (a door)", q(shut_rest))
print("floor moves", q(floor_move))
print("door share > 16384:", sum(v > 16384 for v in shut_rest) / len(shut_rest), "> 16960:", sum(v > 16960 for v in shut_rest) / len(shut_rest))
print("q1,q3", sorted(shut_rest)[len(shut_rest)//4], sorted(shut_rest)[3*len(shut_rest)//4])
