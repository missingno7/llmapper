"""Count each campaign map's live wiring chains: how many, how many relay on, how deep, how many wait, how wide; and a built map's beside them."""
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from bloodmap.corpus import campaign_maps  # noqa: E402
from bloodmap.format import read_map  # noqa: E402
from bloodmap.wiring import chains  # noqa: E402


def profile(disk):
    found = [c for c in chains(disk) if not c["silent"]]
    depths = Counter(c["depth"] for c in found)
    relayed = sum(1 for c in found if c["depth"] >= 2)
    timed = sum(1 for c in found if any(int(s.get("wait") or 0) > 0 for s in c["steps"]))
    widest = max((len(c["steps"]) for c in found), default=0)
    return {"chains": len(found), "relayed": relayed, "deepest": max(depths, default=0), "timed": timed, "widest": widest}


if len(sys.argv) > 1:                                  # a built map to set beside the campaign
    print(Path(sys.argv[1]).stem, profile(read_map(sys.argv[1])))
rows = {p.stem.upper(): profile(read_map(p)) for p in campaign_maps()}
for key in ("chains", "relayed", "deepest", "timed", "widest"):
    values = [r[key] for r in rows.values()]
    print(f"campaign {key}: median {statistics.median(values)}, max {max(values)} "
          f"({max(rows, key=lambda m: rows[m][key])})")
print("most relayed maps:", sorted(rows.items(), key=lambda kv: -kv[1]["relayed"])[:4])
