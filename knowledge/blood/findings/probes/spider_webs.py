"""Every breakable web (type 410) and every sprite on tile 1069 in the corpus: its flags, size, height, and where it stands against the walls."""
import sys, math, json
sys.path.insert(0, ".")
from collections import Counter
from bloodmap.corpus import list_corpus_maps
from bloodmap.format import read_map
from bloodmap.model import record_fields as F
from bloodmap.shade_table import _art
from bloodmap.placement import drawn_extent

art = _art()
rows = []
for m in list_corpus_maps():
    if m.mode == "multiplayer" or m.population not in ("blood-campaign", "community-curated", "community"):
        continue
    try:
        d = read_map(m.path)
    except Exception:
        continue
    for i, s in enumerate(d.sprites):
        f = F(s)
        if int(f["type"]) != 410 and int(f["picnum"]) != 1069:
            continue
        sec = int(f["sector"])
        if not 0 <= sec < len(d.sectors):
            continue
        sf = F(d.sectors[sec])
        t = art.get(int(f["picnum"]))
        top = bottom = None
        if t is not None:
            top, bottom = drawn_extent(t.height, int(t.animation["yofs"]), int(f["y_repeat"]), int(f["cstat"]), int(f["z"]))
        # nearest wall line to the sprite, and whether it is two-sided (an opening)
        best = None
        for w in range(int(sf["wall_ptr"]), int(sf["wall_ptr"]) + int(sf["wall_count"])):
            a = F(d.walls[w]); b = F(d.walls[int(a["point2"])])
            ax, ay, bx, by = a["x"], a["y"], b["x"], b["y"]
            L2 = (bx - ax) ** 2 + (by - ay) ** 2 or 1
            u = max(0, min(1, ((f["x"] - ax) * (bx - ax) + (f["y"] - ay) * (by - ay)) / L2))
            px, py = ax + u * (bx - ax), ay + u * (by - ay)
            dist = math.hypot(f["x"] - px, f["y"] - py)
            wall_ang = math.degrees(math.atan2(by - ay, bx - ax)) % 180
            if best is None or dist < best[0]:
                best = (dist, int(a["next_sector"]) >= 0, wall_ang, math.sqrt(L2))
        spr_plane = (int(f["angle"]) * 360 / 2048 + 90) % 180     # a wall sprite's plane
        rows.append({"map": m.name, "pop": m.population, "i": i, "type": int(f["type"]), "picnum": int(f["picnum"]),
                     "cstat": int(f["cstat"]), "align": (int(f["cstat"]) >> 4) & 3, "xr": int(f["x_repeat"]), "yr": int(f["y_repeat"]),
                     "angle": int(f["angle"]), "floor_gap": (int(sf["floor_z"]) - bottom) if bottom is not None else None,
                     "ceil_gap": (top - int(sf["ceiling_z"])) if top is not None else None,
                     "room_h": int(sf["floor_z"]) - int(sf["ceiling_z"]),
                     "wall_dist": round(best[0]) if best else None, "wall_open": best[1] if best else None,
                     "plane_vs_wall": round(abs(((spr_plane - best[2]) + 90) % 180 - 90)) if best else None,
                     "wall_len": round(best[3]) if best else None})
json.dump(rows, open("work/spider/webs.json", "w"), indent=0)
c = [r for r in rows if r["picnum"] == 1069]
print(len(rows), "webs;", len(c), "on 1069 in", len({r['map'] for r in c}), "maps")
for key in ("cstat", "align", "type"):
    print(key, Counter(r[key] for r in c).most_common(8))
print("bits", {b: sum(1 for r in c if r["cstat"] & b) for b in (1, 2, 4, 8, 16, 32, 64, 128, 256, 512)})
print("plane vs nearest wall (deg)", Counter(r["plane_vs_wall"] // 10 * 10 for r in c if r["plane_vs_wall"] is not None).most_common())
print("wall distance", sorted(r["wall_dist"] for r in c)[:: max(1, len(c) // 12)])
print("floor gap (drawn bottom above floor)", sorted(r["floor_gap"] for r in c if r["floor_gap"] is not None)[:: max(1, len(c) // 12)])
print("ceiling gap", sorted(r["ceil_gap"] for r in c if r["ceil_gap"] is not None)[:: max(1, len(c) // 12)])
