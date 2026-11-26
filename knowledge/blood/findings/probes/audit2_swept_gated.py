"""Count, over the 43 campaign maps, the swept mechanisms bloodmap.conditional considers and those for which it can measure which state is shut (a gated swept edge)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from bloodmap.conditional import conditional_edges
from bloodmap.corpus import campaign_maps
from bloodmap.format import read_map

swept, gated = 0, set()
for path in campaign_maps():
    edges, summary = conditional_edges(read_map(path))
    swept += summary["swept_mechanisms"]
    gated |= {(Path(path).stem, e.mechanism) for e in edges if isinstance(e.delta, dict) and e.delta.get("kind") == "swept"}
print("swept mechanisms:", swept, "with the shut state measured:", len(gated), sorted(gated))
