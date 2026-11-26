"""Count the campaign's sprites of tiles 536, 754, 672 and 2553 with and without cstat 128, and their y-repeats."""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from bloodmap.corpus import campaign_maps  # noqa: E402
from bloodmap.format import read_map  # noqa: E402
from bloodmap.model import record_fields  # noqa: E402

TILES = (536, 754, 672, 2553)
count = collections.Counter()
rep = collections.defaultdict(collections.Counter)
for path in campaign_maps():
    for s in read_map(path).sprites:
        f = record_fields(s)
        if f["picnum"] in TILES:
            count[f["picnum"], bool(f["cstat"] & 128)] += 1
            rep[f["picnum"]][f["y_repeat"]] += 1
for t in TILES:
    print(t, "with 128:", count[t, True], "without:", count[t, False], "y_repeat:", dict(rep[t].most_common(4)))
