"""Per campaign map, the share of floor and ceiling surfaces that are sloped; over all sloped surfaces, how far each rises across its sector, in player heights (floors and ceilings apart)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import os
import statistics
import sys

from bloodmap.corpus import campaign_maps
from bloodmap.format import read_map
from bloodmap.model import record_fields
from bloodmap.sector_geom import outline_and_holes
from bloodmap.slope import depth, rise_at

BODY = 16960
shares, rises = [], {"floor": [], "ceiling": []}
for path in campaign_maps():
    disk = read_map(path)
    walls = [record_fields(w) for w in disk.walls]
    sloped = 0
    for index, s in enumerate(map(record_fields, disk.sectors)):
        first = walls[s["wall_ptr"]]
        hinge = ((first["x"], first["y"]), (walls[first["point2"]]["x"], walls[first["point2"]]["y"]))
        for part in ("floor", "ceiling"):
            if int(s[f"{part}_stat"]) & 2 and int(s[f"{part}_heinum"]):
                sloped += 1
                outline, _holes = outline_and_holes(disk, index)
                rises[part].append(abs(rise_at(int(s[f"{part}_heinum"]), depth(outline, hinge))) / BODY)
    shares.append(sloped / (2 * len(disk.sectors)))
q = lambda v: [round(x, 2) for x in statistics.quantiles(v, n=4)]
print("median share of sloped surfaces per map", round(100 * statistics.median(shares), 1), "%")
print("sloped floors", len(rises["floor"]), "ceilings", len(rises["ceiling"]))
print("rise, player heights: floors q1/median/q3", q(rises["floor"]), "ceilings", q(rises["ceiling"]), "both", q(rises["floor"] + rises["ceiling"]))
