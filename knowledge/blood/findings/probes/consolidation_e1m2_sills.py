"""E1M2's wall-crack pieces: each sloped floor against each neighbour's floor at the two ends of the wall they share."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import json, sys
from bloodmap.corpus import corpus_map_path
from bloodmap.format import read_map
from bloodmap.model import record_fields as F
from bloodmap.slope import signed_distance, rise_at
m = read_map(corpus_map_path("E1M2"))
pieces = [r for r in json.load(open("knowledge/blood/findings/probes/sewer-study_breach_shapes.json")) if r["map"] == "E1M2"]
ours = {r["sector"] for r in pieces}
def floor_at(si, pt):
    s = F(m.sectors[si]); z = s["floor_z"]
    if s["floor_stat"] & 2 and s["floor_heinum"]:
        a = F(m.walls[s["wall_ptr"]]); b = F(m.walls[a["point2"]])
        z += rise_at(s["floor_heinum"], signed_distance(pt, ((a["x"], a["y"]), (b["x"], b["y"]))))
    return z
for r in pieces:
    s = F(m.sectors[r["sector"]])
    for w in range(s["wall_ptr"], s["wall_ptr"] + s["wall_count"]):
        W = F(m.walls[w]); n = W["next_sector"]
        if n < 0 or n in ours:
            continue
        ends = ((W["x"], W["y"]), (F(m.walls[W["point2"]])["x"], F(m.walls[W["point2"]])["y"]))
        print("channel", r["ch"], "piece s%d" % r["sector"], "against s%d" % n,
              "sill (neighbour floor minus piece floor):", [round(floor_at(n, p) - floor_at(r["sector"], p)) for p in ends])
