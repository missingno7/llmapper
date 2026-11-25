"""Who can see the player before he has done anything: every foe with a clear line to where he starts, and to a few steps on.

    python projects/blood-city/level/first_sight.py [MAP]

The owner, 2026-11-25: "right now you just get attacked by a lot of enemies around you
immediatelly". A dude that has a line to the player, within what its kind sees, and the
player in front of it, is awake at once (`ai.cpp: aiScanForTarget`; a cultist's range is
the whole city). So the question is of lines. `cansee` is the engine's (`engine.cpp`):
from sector to sector through the portals, refused where the line is under the floor or
over the ceiling of either side. A sprite stops no line; a wall or a step does.
"""

from __future__ import annotations

import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
LEVEL = Path(__file__).resolve().parent

EYE = 13000                                                        # over the floor, either of them
#: from the start, how far on and which way (north, and a little either side) still counts as the beginning: units
STEPS = ((0, 0), (0, -2), (-2, -1), (2, -1))
PU = 1024


class Lines:
    """The map's walls, for asking who sees what."""

    def __init__(self, disk):
        from bloodmap.model import record_fields
        self.walls = [record_fields(w) for w in disk.walls]
        self.sectors = [record_fields(s) for s in disk.sectors]

    def inside(self, sector: int, x: float, y: float) -> bool:
        s, odd = self.sectors[sector], False
        for w in range(s["wall_ptr"], s["wall_ptr"] + s["wall_count"]):
            p, q = self.walls[w], self.walls[self.walls[w]["point2"]]
            if (p["y"] > y) != (q["y"] > y) and x < (q["x"] - p["x"]) * (y - p["y"]) / (q["y"] - p["y"]) + p["x"]:
                odd = not odd
        return odd

    def at(self, x: float, y: float, z: float) -> int | None:
        """The sector of a point: of those over one another, the one it is in."""
        found = [i for i in range(len(self.sectors)) if self.inside(i, x, y)]
        return min(found, key=lambda i: abs(self.sectors[i]["floor_z"] - z), default=None)

    def cansee(self, a, b) -> bool:
        """Whether (x, y, z, sector) sees another."""
        ax, ay, az, sa = a
        bx, by, bz, sb = b
        todo, seen = [sa], {sa}
        while todo:
            here = todo.pop()
            s = self.sectors[here]
            for w in range(s["wall_ptr"], s["wall_ptr"] + s["wall_count"]):
                p, q = self.walls[w], self.walls[self.walls[w]["point2"]]
                dx, dy, ex, ey = bx - ax, by - ay, q["x"] - p["x"], q["y"] - p["y"]
                d = dx * ey - dy * ex
                if not d:
                    continue
                t = ((p["x"] - ax) * ey - (p["y"] - ay) * ex) / d
                u = ((p["x"] - ax) * dy - (p["y"] - ay) * dx) / d
                if not (0 <= t <= 1 and 0 <= u < 1):
                    continue
                n = p["next_sector"]
                if n < 0:
                    return False
                z = az + (bz - az) * t
                for side in (s, self.sectors[n]):
                    if z > side["floor_z"] or z < side["ceiling_z"] and not side["ceiling_stat"] & 1:
                        return False
                if n not in seen:
                    seen.add(n)
                    todo.append(n)
        return sb in seen


def foes(disk, skill: int = 2):
    """(sprite, type, x, y, eye, sector) of everybody placed on a difficulty."""
    from bloodmap.model import record_extra, record_fields
    from bloodmap.supplies import launched
    for i, sprite in enumerate(disk.sprites):
        f = record_fields(sprite)
        if 201 <= f["type"] <= 250 and launched(sprite, skill):
            yield i, f["type"], f["x"], f["y"], f["z"] - 4096, f["sector"]


def report(disk, skill: int = 2, reach: float = 100) -> list[dict]:
    """Every foe that sees one of the first steps: which of them, and how far off it is."""
    lines = Lines(disk)
    sx, sy, sz = (int(disk.header[k]) for k in ("start_x", "start_y", "start_z"))
    points = []
    for dx, dy in STEPS:
        x, y = sx + dx * PU, sy + dy * PU
        sector = lines.at(x, y, sz)
        if sector is not None:
            points.append((x, y, lines.sectors[sector]["floor_z"] - EYE, sector))
    out = []
    for i, kind, x, y, z, sector in foes(disk, skill):
        saw = [k for k, point in enumerate(points) if lines.cansee(point, (x, y, z, sector))]
        far = math.hypot(x - sx, y - sy) / PU
        if saw and far < reach:
            out.append({"sprite": i, "type": kind, "x": round(x / PU, 1), "y": round(y / PU, 1), "far": round(far, 1), "from": saw})
    return sorted(out, key=lambda row: row["far"])


if __name__ == "__main__":
    from bloodmap.format import read_map
    disk = read_map(sys.argv[1] if len(sys.argv) > 1 else LEVEL / "blood-city-current.MAP")
    for skill in (2, 4):
        rows = report(disk, skill)
        print(f"difficulty {skill}: {len(rows)} see the beginning, {sum(0 in r['from'] for r in rows)} the start itself")
        for r in rows:
            print("  ", r)
