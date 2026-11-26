"""Share of rooms (tools/mine_style_combinations.py's definition) holding any prop, and a light-giving prop (prop-catalogue shade <= -20), over the campaign and over the reference view."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import json
import pathlib
from bloodmap.format import read_map
from bloodmap.corpus import campaign_maps, list_corpus_maps
from bloodmap.player_space import PLAYER_PROFILES

PLAYER = PLAYER_PROFILES["blood"].standing_height
CAT = json.loads(pathlib.Path("knowledge/blood/references/prop-catalogue.json").read_text(encoding="utf-8"))
LIGHTS = {int(k) for k, v in CAT.items() if v["shade"] <= -20}


def area(m, s):
    pts = [(m.walls[w].x, m.walls[w].y) for w in range(s.wall_ptr, s.wall_ptr + s.wall_count)]
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))) / 2


def count(paths):
    rooms = bare = lit = 0
    for path in paths:
        try:
            m = read_map(path)
        except Exception:
            continue
        props = {}
        for sp in m.sprites:
            if sp.status == 0 and sp.type == 0 and sp.picnum > 0:
                props.setdefault(sp.sector, set()).add(sp.picnum)
        for i, s in enumerate(m.sectors):
            if s.wall_count < 3 or s.type in (600, 602, 604, 614, 616, 618):
                continue
            if s.floor_z - s.ceiling_z < 1.2 * PLAYER or area(m, s) < 1_000_000:
                continue
            rooms += 1
            p = props.get(i, set())
            bare += not p
            lit += bool(p & LIGHTS)
    return rooms, bare, lit


for name, paths in (("campaign", campaign_maps()), ("reference", [str(x.path) for x in list_corpus_maps(view="reference")])):
    r, b, l = count(list(paths))
    print(f"{name}: rooms {r}, bare {b} ({b / r:.1%}), with a light prop {l} ({l / r:.1%})")
