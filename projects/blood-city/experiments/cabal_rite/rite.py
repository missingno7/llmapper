"""Break the Cabal's rite headless at level start, the player standing in the well, and read where the engine takes them.

Everything the stone beast's death answers is put on the level-start channel in a
copy of the city; nothing else is changed. The well's floor carrying the player
down, and the map running on through the quake, the spawns and the bursting
glass, are the engine's own. `python experiments/cabal_rite/rite.py`.
"""
import sys
from pathlib import Path
sys.path[:0] = ['.', 'projects/blood-city/level']
import cabal_rite as R
import wires
from bloodmap import oracle as O
from bloodmap.format import read_map, write_map
from bloodmap.model import record_extra, record_fields
from bloodmap.sector_geom import sector_at

m = read_map('projects/blood-city/level/blood-city-current.MAP')
broken, moved = wires.channel('cabal:broken'), 0
for record in (*m.sectors, *m.walls, *m.sprites):
    x = record_extra(record)
    if x and x['rx_id'] == broken:
        record.extra.fields['rx_id'] = 7
        moved += 1
# nobody shoots: the cultists of the copy are furniture
for sprite in m.sprites:
    if record_fields(sprite)['type'] in (201, 202, 244, 208, 207, 18) and abs(record_fields(sprite)['y'] - R.CENTRE[1]) < 9000:
        sprite.fields['type'], sprite.fields['status'] = 0, 0
where = sys.argv[1] if len(sys.argv) > 1 else 'well'
x, y, floor = {'well': (R.CENTRE[0] + 120, R.CENTRE[1] + 60, R.BRIM), 'gullet': (R.CENTRE[0], R.GULLET + 1800, R.SILL), 'dais': (R.CENTRE[0] - 1000, 64700, R.DAIS),
                  'rim': (R.CENTRE[0] + 1500, R.CENTRE[1] + 200, R.FLOOR), 'floor': (R.CENTRE[0] - 2600, R.CENTRE[1] - 600, R.FLOOR)}[where]
sector = sector_at(m, x, y, floor_near=floor)
m.header.update(start_x=x, start_y=y, start_z=floor - 8000, start_sector=sector, start_angle=512)
out = Path('work/cabal/rite.MAP')
write_map(m, out)
print('listeners moved to the level start:', moved, 'sector', sector)
r = O._probe_passage_trajectory(out, nblood=Path('NBlood/nblood.exe').resolve(), game_dir=Path('reference/blood').resolve(),
                                work_dir=Path('work/cabal/rite').resolve(), game_seconds=12, wall_clock_timeout=90)
print({k: v for k, v in r.items() if k != 'trajectory'} | {'telemetry_events': r['telemetry_events'][:5]})
t = r['trajectory']
print('health from', t[0]['health'], 'to a least of', min(q['health'] for q in t), '; furthest from where it stood',
      round(max(((q['x'] - x) ** 2 + (q['y'] - y) ** 2) ** 0.5 for q in t)))
for k in range(0, len(t), max(1, len(t) // 30)):
    print({q: t[k].get(q) for q in ('tick', 'x', 'y', 'z', 'sector', 'health')})
