"""Find what a theatre is made of in every map: rows of seats, seat grids, wide curtains, signs."""
import glob
import json
import math
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, '.')
CURT = {145, 146, 147, 159}
WORDS = ('THEAT', 'CINEM', 'OPERA', 'STAGE', 'MOVIE', 'PLAYH', 'TICKET', 'BALCON', 'DRESSING',
         'BACKST', 'AUDIT', 'ORCHES', 'SHOWTIME', 'TEATR', 'KINO')


def words(sprites):
    """Runs of letter sprites (3808 = A) on one line, read both ways."""
    rows = defaultdict(list)
    for s in sprites:
        p = s['picnum']
        if 3808 <= p < 3834:
            rows[(s['sector'], s['angle'] & 1023, round(s['z'] / 2048))].append((s['x'], s['y'], chr(65 + p - 3808)))
    out = []
    for r in rows.values():
        if len(r) < 4:
            continue
        for key in (lambda t: (t[0], t[1]), lambda t: (t[1], t[0])):
            w = ''.join(t[2] for t in sorted(r, key=key))
            out += [w, w[::-1]]
    return [w for w in out if any(k in w for k in WORDS)]


def seat_rows(S, W):
    strips = defaultdict(list)
    for i, s in enumerate(S):
        if not 4 <= s['wall_count'] <= 8:
            continue
        ws = range(s['wall_ptr'], s['wall_ptr'] + s['wall_count'])
        xs = [W[w]['x'] for w in ws]
        ys = [W[w]['y'] for w in ws]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        a, b = min(w, h), max(w, h)
        if not (96 <= a <= 800 and b >= 1200 and b >= 2.2 * a):
            continue
        nb = Counter(W[k]['next_sector'] for k in ws if W[k]['next_sector'] >= 0)
        if not nb:
            continue
        host = nb.most_common(1)[0][0]
        if S[host]['floor_z'] - S[host]['ceiling_z'] < 24576:
            continue
        axis = 'x' if w > h else 'y'
        strips[(axis, round(b / 256), round(a / 64))].append(
            (i, host, (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, S[host]['floor_z'] - s['floor_z'], s['floor_z']))
    out = []
    for (axis, lb, sb), items in strips.items():
        cols = defaultdict(list)
        for it in items:
            cols[round((it[2] if axis == 'x' else it[3]) / 256)].append(it)
        for col in cols.values():
            if len(col) < 4:
                continue
            at = (lambda t: t[3]) if axis == 'x' else (lambda t: t[2])
            col.sort(key=at)
            run, best, last = [col[0]], [], 0
            for k in range(1, len(col)):
                gap = at(col[k]) - at(col[k - 1])
                if 500 <= gap <= 3200 and (len(run) < 2 or abs(gap - last) <= 0.15 * last + 32):
                    run.append(col[k])
                else:
                    best = max(best, run, key=len)
                    run = [col[k]]
                last = gap
            best = max(best, run, key=len)
            floors = {t[5] for t in best}
            if len(best) < 4 or not (any(1500 <= abs(t[4]) <= 16000 for t in best) or len(floors) >= 3):
                continue
            out.append({'n': len(best), 'len': lb * 256, 'deep': sb * 64, 'sector': best[len(best) // 2][0],
                        'host': best[0][1], 'raked': len(floors) >= 3})
    return out


def grids(P):
    pic = defaultdict(list)
    for s in P:
        plain = s['type'] < 18 or s['type'] in (416, 417)
        if plain and s['picnum'] > 0 and not 3800 <= s['picnum'] <= 3850 and not s['cstat'] & 0x8030:
            pic[s['picnum'], s['x'] // 12000, s['y'] // 12000].append(s)
    out = []
    for (p, _a, _b), m in pic.items():
        if len(m) < 12:
            continue
        ux = Counter(round(s['x'] / 96) for s in m)
        uy = Counter(round(s['y'] / 96) for s in m)
        gx = sum(v >= 3 for v in ux.values())
        gy = sum(v >= 3 for v in uy.values())
        if gx >= 3 and gy >= 3:
            out.append({'n': len(m), 'tile': p, 'x': gx, 'y': gy, 'sector': m[len(m) // 2]['sector']})
    return out


def scan(path):
    from bloodmap import format as fmt, model
    try:
        d = fmt.read_map(path, verify_crc=False)
        S = [model.record_fields(s) for s in d.sectors]
        W = [model.record_fields(w) for w in d.walls]
        P = [model.record_fields(s) for s in d.sprites]
        out = {'path': path, 'sectors': len(S), 'rows': seat_rows(S, W), 'grids': grids(P), 'curtains': [],
               'words': sorted(set(words(P)))}
        for i, s in enumerate(S):
            for w in range(s['wall_ptr'], s['wall_ptr'] + s['wall_count']):
                f = W[w]
                if f['picnum'] in CURT or f['over_picnum'] in CURT:
                    e = W[f['point2']]
                    length = math.hypot(e['x'] - f['x'], e['y'] - f['y'])
                    if length >= 2000:
                        out['curtains'].append({'len': round(length), 'sector': i, 'h': s['floor_z'] - s['ceiling_z']})
        out['posters'] = {p: sum(s['picnum'] == p for s in P) + sum(f['picnum'] == p for f in W)
                          for p in (2047, 225, 943, 905, 77)}
        return out
    except Exception as e:
        return {'path': path, 'error': str(e)[:100]}


def score(r):
    rows = sum(x['n'] for x in r['rows'])
    cur = max([c['len'] for c in r['curtains'] if c['h'] >= 30000] or [0])
    g = max([x['n'] for x in r['grids']] or [0])
    p = r['posters']
    return (min(rows, 40) / 4 + 3 * any(x['raked'] for x in r['rows']) + min(cur, 8000) / 1000 + min(g, 60) / 8
            + 6 * len(r['words']) + 2 * min(p[2047], 2) + min(p[225] + p[943], 3))


if __name__ == '__main__':
    paths = []
    for pattern in ('maps/blood/community/*', 'maps/blood/campaign/*', 'maps/blood/curated/*',
                    'maps/blood/mechanism/**/*', 'D:/Games/DOS/BLOOD/Maps/RABID/*'):
        paths += glob.glob(pattern, recursive=True)
    paths = sorted({p for p in paths if p.lower().endswith('.map')})
    with ProcessPoolExecutor(14) as ex:
        res = list(ex.map(scan, paths, chunksize=8))
    json.dump(res, open('work/aldermack/scan.json', 'w'))
    print(len(res), 'maps,', sum('error' in r for r in res), 'unreadable')
    ok = sorted((r for r in res if 'error' not in r), key=score, reverse=True)
    for r in ok[:60]:
        print(round(score(r), 1), r['path'].replace('\\', '/').split('/', 2)[-1],
              'rows', [(x['n'], x['len'], x['deep'], x['sector'], 'R' if x['raked'] else '') for x in r['rows']][:3],
              'grid', [(x['n'], x['tile'], x['sector']) for x in r['grids']][:2],
              'curt', sorted([(c['len'], c['sector'], c['h']) for c in r['curtains']], reverse=True)[:2],
              r['words'][:3], {k: v for k, v in r['posters'].items() if v})
