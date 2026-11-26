"""E3M1 street walls at 16 units a pixel: how many have x panning phased to world position, how many pan 0 from the wall's start, and how many both."""
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from bloodmap.corpus import corpus_map_path
from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields
from bloodmap.texture_align import wall_art_sizes


def load(name):
    m = read_map(corpus_map_path(name))
    S = [dict(record_fields(s), **(record_extra(s) or {})) for s in m.sectors]
    W = [dict(record_fields(w), **(record_extra(w) or {})) for w in m.walls]
    return S, W


def walls_of(S, si):
    s = S[si]
    return list(range(s["wall_ptr"], s["wall_ptr"] + s["wall_count"]))


sizes = wall_art_sizes()
name = sys.argv[1] if len(sys.argv) > 1 else 'E3M1'
S,W = load(name)
owner = {}
for i,s in enumerate(S):
    for w in walls_of(S,i): owner[w]=i
c = Counter()
for w,x in enumerate(W):
    s = S[owner[w]]
    if not s['ceiling_stat'] & 1: continue           # street: the wall's own sector is open to the sky
    if x['next_sector'] >= 0 and S[x['next_sector']]['ceiling_stat'] & 1: continue  # open-to-open seam
    b = W[x['point2']]; L = math.hypot(b['x']-x['x'], b['y']-x['y'])
    tw = sizes.get(x['picnum'], (0,0))[0]
    if not tw or not x['x_repeat']: continue
    upp = L / (x['x_repeat'] * 8)
    if abs(upp - 16) > 0.5: continue
    if x['x'] != b['x'] and x['y'] != b['y']: c['diagonal']+=1; continue
    along = (b['x']-x['x']) if x['y']==b['y'] else (b['y']-x['y'])
    start = x['x'] if x['y']==b['y'] else x['y']
    sign = 1 if along > 0 else -1
    world = (sign*start//16) % tw
    pan = x['x_panning'] % tw
    c['n']+=1
    if pan == world: c["world"]+=1
    if pan == (-sign*start//16) % tw: c["world_other_sign"]+=1
    if start % 1024 == 0: c["starts_on_1024"]+=1
    if pan == 0: c['zero']+=1
    if pan == world and pan == 0: c['both']+=1
print(name, dict(c))
