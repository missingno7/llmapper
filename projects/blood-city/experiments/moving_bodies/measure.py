"""Measure the broad candidate scan and the rigid slide subset."""

from collections import Counter
import json
from math import hypot
from pathlib import Path
from statistics import median
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bloodmap.corpus import list_corpus_maps
from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields
from bloodmap.motion_sim import (_body_boundary, _body_outline, _body_sprite_payload,
                                 rigid_bodies)
from bloodmap.sector_geom import sector_walls, wall_segment


def main():
    examples = {"MACHINERY-1WAYVEHICLE": 2, "DWE1M2": 225, "DWE1M9": 475,
                "E1M2": 7, "E2M1": 87, "DWE2M1": 105, "DWE3M4": 57,
                "CULTBASE": 615, "PHANTOWN": 88, "HOS-E1M5": 275}
    broad = json.loads(Path(__file__).with_name("groups.json").read_text())
    print("Candidates", len(broad), "members", sum(row["n"] for row in broad),
          "all Drag", sum(row["drag"] == row["n"] for row in broad),
          "all relative ceilings", sum(row["rel"][0] == row["n"] for row in broad),
          "any relative ceiling", sum(bool(row["rel"][0]) for row in broad))
    from shapely.geometry import Polygon

    from bloodmap.sector_geom import outline_and_holes
    from bloodmap.slope import signed_distance

    totals, payloads, time_bins = Counter(), Counter(), []
    mask_depths, solid_widths = [], []
    for entry in list_corpus_maps(attach_tiers=False):
        totals["maps"] += 1
        try:
            level = read_map(entry.path)
        except Exception:
            totals["unreadable"] += 1
            continue
        name = entry.path.stem.upper()
        for body in rigid_bodies(level):
            members = set(body.members)
            totals["bodies"] += 1
            totals["members"] += len(members)
            totals["population:" + entry.population] += 1
            detail = examples.get(name) in members
            fields = {s: record_fields(level.sectors[s]) for s in members}
            live = [f for f in fields.values() if f["floor_z"] != f["ceiling_z"]]
            solids = len(members) - len(live)
            ceilings = [f for f in live if not f["ceiling_stat"] & 1]
            floors = [f for f in live if not f["floor_stat"] & 1]
            totals["all Drag"] += all(record_extra(level.sectors[s]).get("drag") for s in members)
            totals["zero-height groups"] += solids > 0
            totals["zero-height sectors"] += solids
            totals["relative ceiling eligible"] += len(ceilings)
            totals["relative ceiling set"] += sum(bool(f["ceiling_stat"] & 64) for f in ceilings)
            totals["all eligible ceilings relative"] += bool(ceilings) and all(
                f["ceiling_stat"] & 64 for f in ceilings)
            totals["groups with eligible ceilings"] += bool(ceilings)
            totals["relative floor eligible"] += len(floors)
            totals["relative floor set"] += sum(bool(f["floor_stat"] & 64) for f in floors)
            outline = _body_outline(level, body)
            boundary = _body_boundary(level, body)
            one_sided = 0
            if outline.geom_type == "Polygon" and outline.interiors:
                from shapely.geometry import LineString
                one_sided = sum(any(ring.intersection(LineString(wall_segment(level, w))).length
                                    > 0 for ring in outline.interiors)
                                for w in boundary if level.walls[w].fields["next_wall"] < 0)
            totals["groups with interior one-sided walls"] += bool(one_sided)
            totals["interior one-sided walls"] += one_sided
            speed = hypot(*body.displacement) * 10 / body.timing[0] if body.timing[0] else None
            if speed is not None:
                time_bins.append(speed)
            masks = set()
            z_pairs = set()
            for s in members:
                outer, _ = outline_and_holes(level, s)
                if len(outer) >= 3 and fields[s]["floor_z"] == fields[s]["ceiling_z"]:
                    bounds = Polygon(outer).minimum_rotated_rectangle
                    if bounds.geom_type == "Polygon":
                        points = list(bounds.exterior.coords)
                        solid_widths.append(min(hypot(b[0]-a[0], b[1]-a[1])
                                                for a, b in zip(points, points[1:])))
                for w in sector_walls(level, s):
                    f = record_fields(level.walls[w])
                    neighbour = f["next_sector"]
                    if f["cstat"] & 48 and neighbour >= 0:
                        masks.add((s, neighbour, f["over_picnum"], f["cstat"]))
                        hinge = wall_segment(level, w)
                        if len(outer) >= 3 and neighbour in members and hinge[0] != hinge[1]:
                            depths = [signed_distance(p, hinge) for p in outer]
                            if min(depths) >= 0 or max(depths) <= 0:
                                mask_depths.append(max(abs(d) for d in depths))
                    if neighbour >= 0 and neighbour not in members:
                        host = level.sectors[neighbour].fields
                        z_pairs.add((s, neighbour, host["floor_z"] - fields[s]["floor_z"]))
            totals["groups with internal masks"] += any(b in members for _, b, *_ in masks)
            totals["groups with raised external floor"] += any(z > 0 for _, _, z in z_pairs)
            payload = Counter()
            objects = []
            lamp_count = 0
            for i, record in enumerate(level.sprites):
                f = record_fields(record)
                if f["sector"] in members:
                    mode = _body_sprite_payload(level, body, f)
                    payload[mode] += 1
                    if mode != "exempt":
                        objects.append((i, f["sector"], f["picnum"], f["z"], f["cstat"], mode))
                        lamp_count += f["picnum"] == 641
            totals["groups with hanging chain lamp tile 641"] += bool(lamp_count)
            totals["hanging chain lamps tile 641"] += lamp_count
            payloads.update(payload)
            if detail:
                print("\n", name, body.members, body.displacement, body.timing,
                      "speed", speed, "payload", dict(payload), "interior void walls", one_sided)
                print("masks", sorted(masks), "s/host/raised", sorted(z_pairs))
                print("sprites", objects)
                for s, f in sorted(fields.items()):
                    walls = [level.walls[w].fields for w in sector_walls(level, s)]
                    xs, ys = [w["x"] for w in walls], [w["y"] for w in walls]
                    print(s, "width/depth", max(xs)-min(xs), max(ys)-min(ys),
                          "floor/ceil", f["floor_z"], f["ceiling_z"],
                          "stat", f["floor_stat"], f["ceiling_stat"],
                          "tex", f["floor_picnum"], f["ceiling_picnum"],
                          "adj", sorted({w["next_sector"] for w in walls}),
                          "tiles", sorted({w["picnum"] for w in walls}))
    print("\nTOTALS", dict(totals), dict(payloads))
    print("nominal ON speeds min/median/max", *(round(v) for v in
          (min(time_bins), median(time_bins), max(time_bins))))
    for label, values in (("solid sector width", solid_widths),
                          ("interior masked wall side depth", mask_depths)):
        print(label, len(values), *(round(v) for v in (min(values), median(values), max(values))))


if __name__ == "__main__":
    main()
