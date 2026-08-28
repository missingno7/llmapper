"""Order-independent fingerprint of a compiled MAP.

Restructuring the level tree renames regions and reorders the DFS, so the
compiled sector list comes out in a different order carrying the same city.
A byte diff cannot tell that apart from a design change; a canonical
multiset can.  Each sector is reduced to its geometry and surfaces with its
wall loop rotated to a canonical start, sprites to their world placement.
"""
from __future__ import annotations
import hashlib, json, pathlib, sys, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from bloodmap.format import read_map


def canon(path):
    m = read_map(path)
    sectors = []
    for s in m.sectors:
        loop = [(m.walls[w].x, m.walls[w].y)
                for w in range(s.wall_ptr, s.wall_ptr + s.wall_count)]
        if loop:
            k = loop.index(min(loop))
            loop = loop[k:] + loop[:k]
        sectors.append((s.floor_z, s.ceiling_z, s.floor_picnum, s.ceiling_picnum,
                        s.floor_shade, s.ceiling_shade, s.floor_stat, s.ceiling_stat,
                        s.floor_heinum, s.ceiling_heinum, tuple(loop)))
    walls = []
    for i, w in enumerate(m.walls):
        nxt = m.walls[w.point2]
        walls.append((w.x, w.y, nxt.x, nxt.y, w.picnum, w.over_picnum, w.cstat,
                      w.shade, w.x_repeat, w.y_repeat, w.next_sector >= 0))
    sprites = [(sp.x, sp.y, sp.z, sp.picnum, sp.type, sp.cstat, sp.status,
                sp.shade, sp.x_repeat, sp.y_repeat, sp.angle) for sp in m.sprites]
    return {
        "sectors": len(m.sectors), "walls": len(m.walls), "sprites": len(m.sprites),
        "sector_set": collections.Counter(sectors),
        "wall_set": collections.Counter(walls),
        "sprite_set": collections.Counter(sprites),
    }


def digest(c):
    def h(counter):
        blob = json.dumps(sorted((repr(k), v) for k, v in counter.items()))
        return hashlib.sha256(blob.encode()).hexdigest()[:16]
    return {"sectors": c["sectors"], "walls": c["walls"], "sprites": c["sprites"],
            "sector_hash": h(c["sector_set"]), "wall_hash": h(c["wall_set"]),
            "sprite_hash": h(c["sprite_set"])}


def compare(a, b):
    ca, cb = canon(a), canon(b)
    out = {"before": digest(ca), "after": digest(cb)}
    for key in ("sector_set", "wall_set", "sprite_set"):
        only_a = ca[key] - cb[key]
        only_b = cb[key] - ca[key]
        out[key] = {"only_before": sum(only_a.values()),
                    "only_after": sum(only_b.values()),
                    "sample_before": [str(k) for k in list(only_a)[:3]],
                    "sample_after": [str(k) for k in list(only_b)[:3]]}
    return out


if __name__ == "__main__":
    if len(sys.argv) == 3:
        print(json.dumps(compare(sys.argv[1], sys.argv[2]), indent=1))
    else:
        print(json.dumps(digest(canon(sys.argv[1])), indent=1))
