"""Re-run tools/mine_run_rhythm.py's measure per population, and say what the 'items' on runs are."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import sys, collections, statistics
from bloodmap.format import read_map
from bloodmap.corpus import list_corpus_maps
PLAN = 1024
for view in ("reference", "original"):
    per_run, gaps, tiles, maps, pops = [], [], collections.Counter(), 0, collections.Counter()
    for item in sorted(list_corpus_maps(view=view), key=lambda i: str(i.path)):
        try:
            m = read_map(str(item.path))
        except Exception:
            continue
        maps += 1
        by = collections.defaultdict(list)
        for sp in m.sprites:
            if sp.status == 0 and sp.type == 0 and sp.picnum > 0:
                by[sp.sector].append(sp)
        for i, s in enumerate(m.sectors):
            if s.wall_count < 4:
                continue
            pts = [(m.walls[w].x, m.walls[w].y) for w in range(s.wall_ptr, s.wall_ptr + s.wall_count)]
            w = max(p[0] for p in pts) - min(p[0] for p in pts); d = max(p[1] for p in pts) - min(p[1] for p in pts)
            length, across = max(w, d), max(1, min(w, d))
            if length < 4 * PLAN or length / across < 2.5:
                continue
            items = sorted((sp.x if w >= d else sp.y) for sp in by.get(i, []))
            for sp in by.get(i, []):
                tiles[sp.picnum] += 1
            if len(items) >= 2:
                gaps += [(b - a) / PLAN for a, b in zip(items, items[1:]) if b > a]
                per_run.append(len(items) / (length / PLAN)); pops[item.population] += 1
    total = sum(tiles.values())
    print(view, "maps", maps, "runs", len(per_run), "by population", dict(pops), "gaps", len(gaps),
          "median gap", round(statistics.median(gaps), 2), "median items/plan", round(statistics.median(per_run), 3))
    print("  items on runs", total, "of which 624+625 (light glows)", tiles[624] + tiles[625],
          f"({(tiles[624] + tiles[625]) / total:.0%})", "top", tiles.most_common(6))
