"""Recount sky-below-a-roofed-neighbour pairs over the 43 campaign maps, as rules_blood's rule pairs them: equal, higher, lower, median gap."""
import collections
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from bloodmap.corpus import campaign_maps  # noqa: E402
from bloodmap.format import read_map  # noqa: E402
from bloodmap.reachability import portal_graph  # noqa: E402

gaps, below = [], collections.Counter()
for path in campaign_maps():
    disk = read_map(path)
    graph = portal_graph(disk)
    open_ = {i for i, s in enumerate(disk.sectors) if int(s.fields["ceiling_stat"]) & 1}
    for i in sorted(open_):
        here = int(disk.sectors[i].fields["ceiling_z"])
        for o in graph.get(i, ()):
            if not 0 <= o < len(disk.sectors) or o in open_:
                continue
            gap = int(disk.sectors[o].fields["ceiling_z"]) - here   # >0: the sky stands higher
            gaps.append(gap)
            if gap < 0:
                below[path.stem.upper()] += 1
n = len(gaps)
eq = sum(1 for g in gaps if g == 0)
print(f"maps {len(campaign_maps())} pairs {n} equal {eq} ({100 * eq / n:.1f}%) sky higher {sum(1 for g in gaps if g > 0)} "
      f"sky lower {sum(below.values())} median gap {statistics.median(gaps)}")
print("sky lower by map:", dict(below))
