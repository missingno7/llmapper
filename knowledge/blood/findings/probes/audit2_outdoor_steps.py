"""Outdoor steps over the 43 campaign maps: sky-ceilinged neighbours whose floors differ by a step (256 to 4096); riser (the lower sector's wall facing up) against the upper tread's floor shade, and tread against tread."""
import collections
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from bloodmap.corpus import campaign_maps  # noqa: E402
from bloodmap.format import read_map  # noqa: E402
from bloodmap.model import record_fields  # noqa: E402

LOW, HIGH = 256, 4096
riser_minus_tread, tread_steps, pairs = [], [], 0
for path in campaign_maps():
    m = read_map(path)
    S = [record_fields(s) for s in m.sectors]
    W = [record_fields(w) for w in m.walls]
    seen = set()
    for lo, s in enumerate(S):
        if not s["ceiling_stat"] & 1 or s["floor_heinum"]:
            continue
        for w in range(s["wall_ptr"], s["wall_ptr"] + s["wall_count"]):
            hi = W[w]["next_sector"]
            if hi < 0 or (lo, hi) in seen:
                continue
            t = S[hi]
            if not t["ceiling_stat"] & 1 or t["floor_heinum"]:
                continue
            rise = s["floor_z"] - t["floor_z"]
            if not LOW <= rise <= HIGH:
                continue
            seen.add((lo, hi))
            pairs += 1
            riser_minus_tread.append(W[w]["shade"] - t["floor_shade"])
            tread_steps.append(abs(t["floor_shade"] - s["floor_shade"]))
print("outdoor step pairs", pairs)
print("riser minus upper tread: median", statistics.median(riser_minus_tread), "commonest", collections.Counter(riser_minus_tread).most_common(6))
print("tread to tread: equal", sum(1 for d in tread_steps if d == 0), "of", len(tread_steps), "median", statistics.median(tread_steps))
