"""Share of each campaign map's sectors not reachable from the player start, by two-sided walls alone and with link markers and teleports too (bloodmap.reachability)."""
import statistics
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from bloodmap.corpus import campaign_maps
from bloodmap.format import read_map
from bloodmap.reachability import analyze_reachability, player_start, portal_graph


def unreached(graph, origin, count):
    seen, pending = {origin}, deque([origin])
    while pending:
        for n in graph.get(pending.popleft(), ()):
            if n not in seen:
                seen.add(n)
                pending.append(n)
    return 1 - len(seen) / count


walls, full = {}, {}
for path in campaign_maps():
    disk = read_map(path)
    name = Path(path).stem.upper()
    walls[name] = unreached(portal_graph(disk), player_start(disk)["sector"], len(disk.sectors))
    full[name] = analyze_reachability(disk).offmap_fraction
for label, d in (("walls only", walls), ("walls, links, teleports", full)):
    worst = max(d, key=d.get)
    print(f"{label}: median {statistics.median(d.values()):.3f}, worst {worst} {d[worst]:.3f}")
print("E6M5 walls only", round(walls.get("E6M5", -1), 3))
