"""How fine a map is cut for light: sectors that differ from a neighbour they open onto only in shade."""
import sys, statistics
sys.path.insert(0, ".")
from bloodmap.format import read_map
from bloodmap.model import record_fields as F
from bloodmap.sector_geom import outline_and_holes
from shapely.geometry import Polygon

SAME = ("floor_z", "ceiling_z", "floor_picnum", "ceiling_picnum", "floor_heinum", "ceiling_heinum", "floor_pal")


def measure(disk):
    S = [F(s) for s in disk.sectors]
    area = {}
    for i in range(len(S)):
        try:
            area[i] = Polygon(*outline_and_holes(disk, i)).area
        except Exception:
            area[i] = 0.0
    light, equal_pairs, step = set(), 0, []
    for i, f in enumerate(S):
        for w in range(int(f["wall_ptr"]), int(f["wall_ptr"]) + int(f["wall_count"])):
            o = int(F(disk.walls[w])["next_sector"])
            if o <= i:
                continue
            g = S[o]
            if all(int(f.get(k, 0)) == int(g.get(k, 0)) for k in SAME) and int(f["extra"]) <= 0 and int(g["extra"]) <= 0:
                light |= {i, o}
                d = abs(int(f["floor_shade"]) - int(g["floor_shade"]))
                step.append(d)
                if d <= 1:
                    equal_pairs += 1
    total = sum(area.values())
    la = [area[i] for i in light]
    tiny = sum(1 for a in la if a < 512 * 512)
    return {"sectors": len(S), "walls": len(disk.walls), "area_M": round(total / 1e6),
            "sectors_per_M": round(len(S) / (total / 1e6), 2),
            "light_sectors": len(light), "light_median_area_k": round(statistics.median(la) / 1e3) if la else 0,
            "light_tiny_<512sq": tiny, "seam_steps_median": statistics.median(step) if step else 0,
            "seams_<=1_shade": equal_pairs, "seams": len(step)}


if __name__ == "__main__":
    for path in sys.argv[1:]:
        if path.startswith("E"):
            from bloodmap.corpus import corpus_map_path
            name, disk = path, read_map(corpus_map_path(path))
        else:
            name, disk = path.split("/")[-1], read_map(path)
        print(name, measure(disk), flush=True)
