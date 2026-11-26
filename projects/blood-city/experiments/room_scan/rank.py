import json, sys
sys.path.insert(0, 'work/aldermack')
from bloodmap import format as fmt, model
res = [r for r in json.load(open('work/aldermack/scan.json')) if 'error' not in r]
out = []
for r in res:
    if not r['rows'] and not any(c['len'] >= 3500 and c['h'] >= 40000 for c in r['curtains']) and not r['words'] and not r['posters']['2047']:
        continue
    d = fmt.read_map(r['path'], verify_crc=False)
    S = [model.record_fields(s) for s in d.sectors]; W = [model.record_fields(w) for w in d.walls]
    seats = []
    for x in r['rows']:
        i = x['sector']; s = S[i]
        ws = range(s['wall_ptr'], s['wall_ptr'] + s['wall_count'])
        nb = {W[w]['next_sector'] for w in ws if W[w]['next_sector'] >= 0}
        # a stair step borders steps above and below it; a seat borders open floor on a long side
        fl = sorted({S[n]['floor_z'] for n in nb})
        up = any(S[n]['floor_z'] < s['floor_z'] - 512 for n in nb); dn = any(S[n]['floor_z'] > s['floor_z'] + 512 for n in nb)
        if up and dn and len(nb) <= 3 and x['raked']:
            # could be a raked house: needs rows of wide pitch or tall host
            host_h = s['floor_z'] - s['ceiling_z']
            if x['len'] < 4000 or host_h < 60000:
                continue
        seats.append(x)
    n = sum(x['n'] for x in seats)
    cur = max([c['len'] for c in r['curtains'] if c['h'] >= 40000] or [0])
    sc = min(n, 24) / 3 + cur / 1200 + 6 * len(r['words']) + 3 * min(r['posters']['2047'], 2)
    out.append((sc, r['path'].replace(chr(92), '/'), [(x['n'], x['len'], x['deep'], x['sector']) for x in seats][:4], cur,
                sorted({(c['sector'], c['len'], c['h']) for c in r['curtains'] if c['h'] >= 30000}, key=lambda t: -t[1])[:3], r['words'][:2], r['posters']['2047']))
out.sort(reverse=True)
for o in out[:75]: print(round(o[0], 1), o[1].split('/', 2)[-1], o[2], o[4], o[5], o[6] or '')
