"""E3M1's roofed-sector areas (q3, share over 10M) and the campaign medians of level_profile's dead-end fraction, mean degree and loops per 100 sectors."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import os
import statistics
import sys

from bloodmap.corpus import campaign_maps, corpus_map_path
from bloodmap.format import read_map
from bloodmap.level_profile import _sector_area, flatten, level_profile


def roofed(disk):
    """q3 and share over 10,000,000 of the areas of sectors whose ceiling is not parallax."""
    areas = sorted(_sector_area(disk, i) for i, s in enumerate(disk.sectors) if not int(s.fields["ceiling_stat"]) & 1)
    return len(areas), statistics.quantiles(areas, n=4)[2], sum(1 for a in areas if a > 10e6) / len(areas)


print("E3M1 roofed sectors, q3, share over 10M:", roofed(read_map(corpus_map_path("E3M1"))))
keys = ("dead_end_fraction", "mean_degree", "loops_per_100_sectors")
values = {k: [] for k in keys}
for path in campaign_maps():
    flat = flatten(level_profile(read_map(path)))
    for k in keys:
        values[k].append(flat[next(x for x in flat if x.endswith(k))])
print("campaign medians over", len(campaign_maps()), "maps:", {k: statistics.median(v) for k, v in values.items()})
