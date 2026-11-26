"""Ride the Phantom Terminus headless: the car saved away and called home at level start, the player aboard.

The trajectory is the engine's own: from tick 172 of the run of 2026-11-24 the
rider's x falls about 204 every 12 ticks, the car's 2,048 a second, on three
different sectors of the body. `python experiments/moving_bodies/ride.py`.
"""
import sys
from pathlib import Path
sys.path[:0] = ['.', 'projects/blood-city/level']
import phantom_terminus as T
import wires
from bloodmap import oracle as O
from bloodmap.format import read_map, write_map
from bloodmap.model import record_extra
from bloodmap.sector_geom import sector_at

src = 'projects/blood-city/level/blood-city-current.MAP'
m = read_map(src)
run = wires.channel(T.RUN)
n = 0
for s in m.sectors:
    x = record_extra(s)
    if x and x['rx_id'] == run:
        s.extra.fields.update(rx_id=7, state=0, busy=0)
        n += 1
aisle = sector_at(m, *T.COACH(35, 25), floor_near=T.DECK)
x, y = T.COACH(60, 25)
m.header.update(start_x=x + T.TRAVEL, start_y=y, start_z=T.DECK - 8000, start_sector=aisle, start_angle=1024)
out = Path('work/movers/ride.MAP')
write_map(m, out)
print('members on the wire', n, 'aisle', aisle)
r = O._probe_passage_trajectory(out, nblood=Path('NBlood/nblood.exe').resolve(),
                                game_dir=Path('reference/blood').resolve(),
                                work_dir=Path('work/movers/ride').resolve(), game_seconds=12, wall_clock_timeout=90)
print({k: v for k, v in r.items() if k not in ('trajectory',)} | {'telemetry_events': r['telemetry_events'][:5]})
t = r['trajectory']
print(t[0] if t else None)
for k in range(0, len(t), max(1, len(t) // 30)):
    print({q: t[k].get(q) for q in ('tick', 'x', 'y', 'z', 'sector')})
