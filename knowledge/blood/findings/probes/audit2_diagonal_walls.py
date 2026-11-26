"""Share of walls that are neither horizontal nor vertical, and of sectors that are four-walled axis-aligned rectangles, in E3M1, TEDE1M2 and any map path given (a path under maps/duke3d is read as Duke)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import os
import sys

from bloodmap.corpus import corpus_map_path
from bloodmap.format import read_map
from bloodmap.model import record_fields


def shares(disk):
    walls = [record_fields(w) for w in disk.walls]
    diagonal = sum(1 for w in walls if (w["x"] != walls[w["point2"]]["x"]) and (w["y"] != walls[w["point2"]]["y"]))
    rect = 0
    for s in map(record_fields, disk.sectors):
        loop = walls[s["wall_ptr"]:s["wall_ptr"] + s["wall_count"]]
        if len(loop) == 4 and len({w["x"] for w in loop}) == 2 and len({w["y"] for w in loop}) == 2:
            rect += 1
    return round(100 * diagonal / len(walls), 1), round(100 * rect / len(disk.sectors), 1)


if __name__ == "__main__":
    from bloodmap.duke import read_duke_map
    for name in ["E3M1", "TEDE1M2"] + sys.argv[1:]:
        if os.path.exists(name):
            disk = read_duke_map(name) if "duke3d" in name else read_map(name)
        else:
            disk = read_map(corpus_map_path(name))
        print(name, "diagonal walls %, rectangle sectors %:", shares(disk))
