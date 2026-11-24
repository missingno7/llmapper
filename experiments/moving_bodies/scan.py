"""Groups of connected horizontal movers on one receiver, over every corpus map (work/movers/groups.json)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import json
from collections import defaultdict
from bloodmap import corpus
from bloodmap.format import read_map
from bloodmap.model import record_fields, record_extra
from bloodmap.sector_geom import outline_and_holes
out = []
items = corpus.list_corpus_maps()
for it in items:
    path = getattr(it, 'path', it)
    try:
        m = read_map(path)
    except Exception as e:
        continue
    movers = {}
    for i, s in enumerate(m.sectors):
        f = s.fields
        if f['type'] in (613,614, 615,616, 617):
            x = record_extra(s)
            if x: movers[i] = (f['type'], x.get('rx_id', 0))
    if len(movers) < 2: continue
    adj = defaultdict(set)
    for i in movers:
        f = m.sectors[i].fields
        for w in range(f['wall_ptr'], f['wall_ptr'] + f['wall_count']):
            n = m.walls[w].fields['next_sector']
            if n in movers and movers[n][1] == movers[i][1] and movers[i][1]:
                adj[i].add(n)
    seen = set()
    for i in movers:
        if i in seen or not adj[i]: continue
        st, comp = [i], []
        while st:
            k = st.pop()
            if k in seen: continue
            seen.add(k); comp.append(k); st += list(adj[k])
        if len(comp) < 2: continue
        xs = []; ys = []
        for k in comp:
            f = m.sectors[k].fields
            for w in range(f['wall_ptr'], f['wall_ptr'] + f['wall_count']):
                xs.append(m.walls[w].fields['x']); ys.append(m.walls[w].fields['y'])
        mk = []
        for k in comp:
            x = record_extra(m.sectors[k])
            try:
                a, b = m.sprites[x['marker_0']].fields, m.sprites[x['marker_1']].fields
                mk.append((b['x'] - a['x'], b['y'] - a['y'], b['angle'] - a['angle']))
            except Exception: mk.append(None)
        drag = sum(1 for k in comp if record_extra(m.sectors[k]).get('drag'))
        fl = len({m.sectors[k].fields['floor_z'] for k in comp}); cl = len({m.sectors[k].fields['ceiling_z'] for k in comp})
        rel = sum(1 for k in comp if m.sectors[k].fields['ceiling_stat'] & 64), sum(1 for k in comp if m.sectors[k].fields['floor_stat'] & 64)
        out.append(dict(map=path.name if hasattr(path,'name') else str(path), pop=str(getattr(it,'population','')), n=len(comp), types=sorted({movers[k][0] for k in comp}), rx=movers[comp[0]][1],
            size=(max(xs)-min(xs), max(ys)-min(ys)), disp=sorted(set(map(str,mk)))[:4], drag=drag, floors=fl, ceils=cl, rel=rel, sectors=sorted(comp)))
out.sort(key=lambda r: -r['n'])
json.dump(out, open('work/movers/groups.json', 'w'), indent=0)
print(len(items), len(out))
for r in out:
    if r['n'] >= 3 and 614 in r['types'] or 616 in r['types'] and r['n']>=2 and 613 not in r['types']:
        print(r['map'], r['pop'], r['n'], r['types'], r['size'], r['disp'], 'drag', r['drag'], 'fl', r['floors'], 'cl', r['ceils'], 'rel', r['rel'], r['sectors'][:6])
