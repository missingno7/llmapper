"""Find the community maps that are conversions of a Duke Nukem 3D level.

A sector's signature is its box, its wall count and its height, unmoved by a
conversion that keeps the geometry. The owner, 2026-11-23: "AFTSHOCK is
actually conversion of E1L1 map from Duke3D". Such a map is evidence of
Duke's design and not of Blood's. Writes knowledge/blood/duke-conversions.json.

Only distinctive sectors count: a signature that twenty or more of the other
Blood maps also have (a 1,024 square closet) says nothing.

    python -m tools.find_duke_conversions      # about five minutes over 1,589 Blood maps

The Blood maps are the corpus's campaign, curated and community populations
(`bloodmap.corpus`); the Duke levels are the files of `maps/duke3d`.
"""
import glob
import json
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, '.')
OUT = 'knowledge/blood/duke-conversions.json'
COMMON = 20          # a signature in this many Blood maps is nobody's
LEAST, SHARE = 25, 0.08


def signature(sectors, walls):
    out = Counter()
    for s in sectors:
        ws = range(s['wall_ptr'], s['wall_ptr'] + s['wall_count'])
        xs = [walls[w]['x'] for w in ws]
        ys = [walls[w]['y'] for w in ws]
        box = tuple(sorted((max(xs) - min(xs), max(ys) - min(ys))))
        out[box, s['wall_count'], s['floor_z'] - s['ceiling_z']] += 1
    return out


def blood(path):
    from bloodmap import format as fmt, model
    try:
        d = fmt.read_map(path, verify_crc=False)
        return path, signature([model.record_fields(s) for s in d.sectors],
                               [model.record_fields(w) for w in d.walls])
    except Exception:
        return path, None


def main():
    from bloodmap.duke import read_duke_map
    duke = {}
    for path in sorted(glob.glob('maps/duke3d/*')):
        if not path.lower().endswith('.map'):
            continue
        try:
            d = read_duke_map(path)
        except Exception:
            continue
        duke[path.replace('\\', '/').split('/')[-1]] = signature(
            [s.fields for s in d.sectors], [w.fields for w in d.walls])
    from bloodmap.corpus import list_corpus_maps

    paths = sorted(str(item.path) for population in ("community", "community-curated", "blood-campaign")
                   for item in list_corpus_maps(population=population))
    with ProcessPoolExecutor(14) as ex:
        maps = [(p, s) for p, s in ex.map(blood, paths, chunksize=16) if s]
    seen = Counter()
    for _p, s in maps:
        seen.update(set(s))
    found = []
    for path, s in maps:
        own = Counter({k: v for k, v in s.items() if seen[k] < COMMON})
        best = max(((sum((own & d).values()), name) for name, d in duke.items()), default=(0, ''))
        share = best[0] / sum(duke[best[1]].values()) if best[1] else 0
        if best[0] >= LEAST and share >= SHARE:
            found.append({'map': path.replace('\\', '/').split('blood/', 1)[1], 'duke': best[1],
                          'sectors': best[0], 'share_of_duke_level': round(share, 2)})
    found.sort(key=lambda r: (-r['share_of_duke_level'], r['map']))
    json.dump({'rule': __doc__.split('\n\n')[1].replace('\n', ' '), 'duke_levels': len(duke),
               'blood_maps': len(maps), 'conversions': found},
              open(OUT, 'w', newline='\n'), indent=1)
    print(len(maps), 'maps,', len(duke), 'Duke levels,', len(found), 'conversions')
    for r in found[:60]:
        print(r)


if __name__ == '__main__':
    main()
