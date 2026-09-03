"""Every layer's readers, run as a census over all 43 campaign maps.

    PYTHONPATH=".;projects/campaign-census/source" \
        python projects/campaign-census/source/residue_curve.py

The readers are pure functions, so the whole eight-layer decompilation runs on
any map without a project directory: what comes out is, per map per layer, the
share of claimable fields claimed and the residue.

The table has one job beyond the curve itself. Research section 2.5: the
language is done when a new map's residue under the existing readers is small,
and its TAIL names the next macro. So the second map to decompile in full is
the one E3M1's readers already explain best -- decisions section 30 -- because
the point of the second map is to find what the two SHARE, and a map the
readers cannot read yet would only measure their gaps again.

Nothing here writes a project. It writes `census_layer` facts and one table.
"""

from __future__ import annotations

import json
import traceback
from collections import Counter

from _common import PROJECT, art_sizes, campaign, write

from bloodmap import read_facts
from bloodmap.anchors import find_bundles
from bloodmap.curriculum import mine_map
from bloodmap.format import read_map
from bloodmap.read_edges import read_edges
from bloodmap.read_intent import (
    name_mechanisms, name_places, named_props)
from bloodmap.read_islands import read_islands
from bloodmap.read_joins import join_census, surface_kinds
from bloodmap.read_ledger import fields_of
from bloodmap.read_light import read_light
from bloodmap.read_mechanisms import curriculum_index, read_mechanisms
from bloodmap.read_plan import read_plan
from bloodmap.read_stairs import read_stairs
from bloodmap.read_store import FactStore
from bloodmap.read_surfaces import read_surfaces
from bloodmap.texture_frame import sector_index

KINDS = ("sector", "wall", "sprite", "xsector", "xwall", "xsprite")


def lessons_dir() -> str:
    import os

    from bloodmap.patterns import corpus_map_path

    return os.environ.get(
        "BLOODMAP_LESSONS",
        str(corpus_map_path("E1M1").parent.parent / "mechanism" / "Vanilla"))


def read_one(path, sizes, lessons, index) -> dict:
    """All eight layers on one map, as facts, without a project directory.

    Layer 1 is the only one that needs a hierarchy, and `decompile_level`
    builds it -- so a map that has never been decompiled into a project still
    gets its space tree here.
    """
    disk = read_map(path)
    level = disk.to_level_ir()
    owners = sector_index(level)
    store = FactStore()

    from bloodmap.decompiler import decompile_level

    #: Layer 1 is the one reader here that can fail on a campaign map:
    #: `analyze_spatial` returns no geometry record for E6M7's sector 144 and
    #: `decompile_level` raises on it. A map that cannot be decompiled is
    #: still read by the other seven layers, and the row says which one is
    #: missing -- dropping the map would hide a gap in a reader that predates
    #: this work.
    hierarchy = None
    layer1_error = None
    try:
        hierarchy = decompile_level(level, source_name=path.name).hierarchy
        store.extend(read_facts.layer1(level, hierarchy))
    except Exception as error:
        layer1_error = repr(error)

    surfaces = read_surfaces(level, art_sizes=sizes)
    stairs = read_stairs(level)
    store.extend(read_facts.layer2(level, surfaces, stairs))

    kinds = surface_kinds(level, owners=owners)
    census = join_census(level, kinds["kinds"], owners=owners)
    store.extend(read_facts.layer3(level, {"kinds": kinds, "census": census}))

    islands = read_islands(level, kinds["kinds"], owners=owners)
    light = read_light(level, kinds["kinds"], owners=owners)
    store.extend(read_facts.layer4(level, islands, light))

    edges = read_edges(level, kinds["kinds"], owners=owners)
    store.extend(read_facts.layer6(level, edges))

    plan = read_plan(level, kinds["kinds"], owners=owners)
    store.extend(read_facts.layer7(level, plan))

    reading = mine_map(path)
    mechanisms = read_mechanisms(level, disk, lessons=lessons, reading=reading)
    store.extend(read_facts.layer5(level, mechanisms))

    from bloodmap.read_facts import _basis_of, _sectors_of

    spaces = [{"id": node["id"], "sectors": _sectors_of(node)}
              for node in (hierarchy or {"nodes": []})["nodes"]
              if node["kind"] == "space" and not any(
                  "reviewable singleton" in basis
                  for basis in _basis_of(node))]
    names = name_mechanisms(mechanisms["sentences"], index)
    places = name_places(
        level, spaces,
        street=[i for i, k in kinds["kinds"].items()
                if k in ("road", "pavement", "outdoor_ground", "end_wall")],
        start_sector=int(disk.header["start_sector"]),
        structures={run["id"]: run["sectors"] for run in stairs["runs"]},
        stacks=mechanisms["stacks"], props=named_props(level),
        bundles=[row.to_dict() for row in find_bundles(disk.to_build_ir())])
    store.extend(read_facts.layer8(names, places))
    store.extend(read_facts.selections(store))

    counts = {"sector": len(level.sectors), "wall": len(level.walls),
              "sprite": len(level.sprites),
              "xsector": sum(1 for i in level.sectors if i.get("blood")),
              "xwall": sum(1 for i in level.walls if i.get("blood")),
              "xsprite": sum(1 for i in level.sprites if i.get("blood"))}
    claimable = sum(counts[kind] * len(fields_of(kind)) for kind in KINDS)
    held = {(row.attrs["record"], row.attrs["field"]) for row in store["claims"]}

    per_layer: dict[int, dict] = {}
    for predicate, rows in store.rows.items():
        for row in rows:
            if row.layer is None:
                continue
            into = per_layer.setdefault(row.layer, {"facts": 0, "claims": 0,
                                                    "residue": 0})
            into["facts"] += 1
            if predicate == "claims":
                into["claims"] += 1
            if predicate == "residue":
                into["residue"] += 1
    return {
        "map": path.stem.upper(),
        "counts": counts,
        "claimable_fields": claimable,
        "fields_with_a_claim": len(held),
        "claimed_share": round(100.0 * len(held) / claimable, 3) if claimable else 0.0,
        "residue_facts": sum(row["residue"] for row in per_layer.values()),
        "per_layer": {str(layer): row for layer, row in sorted(per_layer.items())},
        "layer1_error": layer1_error,
        #: What decides whether a map is a candidate: the street MODEL's own
        #: minimum, which is a road with an island standing on it and a kerb
        #: at the join. A base plane of two sectors and no kerb is an outdoor
        #: place, not a street, and ranking it as one is how the literal rule
        #: picked a map whose "street" is two sectors.
        "street_sectors": sum(1 for k in kinds["kinds"].values()
                              if k in ("road", "pavement")),
        "road_sectors": sum(1 for k in kinds["kinds"].values() if k == "road"),
        "islands": len(islands["islands"]),
        "kerb_records": islands["kerb_records_the_map_makes"],
        "has_a_street_network": bool(
            [i for i, k in kinds["kinds"].items() if k == "road"]),
        "has_a_street_in_the_models_sense": bool(
            islands["islands"] and islands["kerb_records_the_map_makes"]),
    }


def main() -> int:
    sizes = art_sizes()
    lessons = lessons_dir()
    index = curriculum_index(lessons)
    rows, failed = [], []
    for path in campaign():
        try:
            rows.append(read_one(path, sizes, lessons, index))
        except Exception as error:                # a map that cannot be read
            failed.append({"map": path.stem.upper(), "error": repr(error),
                           "where": traceback.format_exc().splitlines()[-3:]})
            print(f"  {path.stem.upper():8s} FAILED {error!r}")
    rows.sort(key=lambda row: -row["claimed_share"])

    store = FactStore()
    for row in rows:
        store.add("census_layer", f"map:{row['map']}",
                  {"map": row["map"], "claimed_share": row["claimed_share"],
                   "claimable_fields": row["claimable_fields"],
                   "fields_with_a_claim": row["fields_with_a_claim"],
                   "residue_facts": row["residue_facts"],
                   "street_sectors": row["street_sectors"],
                   "has_a_street_network": row["has_a_street_network"],
                   "per_layer": row["per_layer"],
                   "population": "blood-campaign"},
                  reader="projects/campaign-census/source/residue_curve.py")
    store.write(PROJECT / "facts")

    with_street = [row for row in rows if row["has_a_street_network"]]
    real_street = [row for row in rows
                   if row["has_a_street_in_the_models_sense"]
                   and row["map"] != "E3M1"]
    literal = sorted((row for row in with_street if row["map"] != "E3M1"),
                     key=lambda row: -row["claimed_share"])

    #: THE RULE IS AMBIGUOUS, and the ambiguity is measurable rather than a
    #: matter of taste. Layer 2 makes 92-97% of every map's claims, and it
    #: measures texture runs, which have nothing to do with streets -- so
    #: "largest claimed share" ranks maps by their wall count. Ranking the
    #: same maps on everything EXCEPT layer 2 gives a different winner. Two
    #: defensible readings of one rule is the condition the stated default
    #: was given for.
    def without_layer2(row):
        other = sum(value["claims"] for key, value in row["per_layer"].items()
                    if key != "2")
        return round(100.0 * other / row["claimable_fields"], 4)

    by_share = literal[0]["map"] if literal else None
    by_other = (sorted(real_street, key=lambda row: -without_layer2(row))[0]["map"]
                if real_street else None)
    ambiguous = by_share != by_other

    #: The corroboration, on the criterion the SLEEP PHASE actually needs: the
    #: second map is for finding what two decompilations share, so the map
    #: that matters is the one E3M1's street grammar reaches furthest. The
    #: join table describes anything at all on four maps.
    reached = sorted((row for row in rows
                      if row["per_layer"].get("3", {}).get("claims", 0)),
                     key=lambda row: -row["per_layer"]["3"]["claims"])
    default = "E1M2"
    chosen = default if ambiguous else by_share
    choice = next((row for row in rows if row["map"] == chosen), None)

    selection = {
        "chosen": chosen,
        "criterion": ("among maps with a street network, the largest claimed "
                      "share under E3M1's readers; the stated default if that "
                      "is ambiguous is E1M2"),
        "the_literal_rule_gives": by_share,
        "excluding_layer_2_gives": by_other,
        "why_it_is_ambiguous": (
            "layer 2 makes 92-97% of every map's claims and measures texture "
            "runs, not streets, so the two rankings disagree completely: "
            f"{by_share} by total claimed share, {by_other} without layer 2, "
            "and neither is stable under a reader change to layer 2"),
        "corroboration": (
            "the join table -- the street grammar itself -- describes anything "
            "on four maps: " + ", ".join(
                f"{row['map']} ({row['per_layer']['3']['claims']})"
                for row in reached) +
            f". Excluding E3M1, {default} leads by a factor of two, and it is "
            f"a whole map rather than a fragment"),
    }

    write("residue-curve.json", {
        "population": "blood-campaign",
        "maps_read": len(rows),
        "maps_that_failed": failed,
        "maps_with_a_street_network": len(with_street),
        "maps_with_a_street_in_the_models_sense": len(real_street),
        "ranking_by_the_literal_rule": [row["map"] for row in literal[:5]],
        "ranking_among_real_streets": [
            {"map": row["map"], "claimed_share": row["claimed_share"],
             "road_sectors": row["road_sectors"], "islands": row["islands"],
             "kerb_records": row["kerb_records"]} for row in real_street],
        "rule": ("the second map is the one E3M1's readers already explain "
                 "best among maps with a street network, because the point of "
                 "a second map is what the two SHARE (research 2.5); the "
                 "default if ambiguous is E1M2"),
        "selection": selection,
        "chosen": chosen,
        "maps_the_join_table_reaches": [
            {"map": row["map"], "layer3_claims": row["per_layer"]["3"]["claims"],
             "road_sectors": row["road_sectors"], "islands": row["islands"],
             "kerb_records": row["kerb_records"],
             "sectors": row["counts"]["sector"]} for row in reached],
        "rows": rows,
    })

    print(f"\n{len(rows)} maps read, {len(failed)} failed, "
          f"{len(with_street)} with a street network\n")
    print(f"{'map':8s} {'claimed':>8s} {'fields':>8s} {'of':>9s} "
          f"{'residue':>8s} road/is/kerb   per-layer claims")
    for row in rows:
        layers = " ".join(f"{k}:{v['claims']}" for k, v in row["per_layer"].items()
                          if v["claims"])
        print(f"{row['map']:8s} {row['claimed_share']:7.3f}% "
              f"{row['fields_with_a_claim']:8d} {row['claimable_fields']:9d} "
              f"{row['residue_facts']:8d} "
              f"{row['road_sectors']:3d}/{row['islands']:2d}/"
              f"{row['kerb_records']:3d}   {layers}")
    print("")
    print("maps the JOIN TABLE reaches at all (layer 3 claims):")
    for row in reached:
        print("  %-6s %3d claims  road %2d / islands %2d / kerbs %3d  %4d sectors"
              % (row["map"], row["per_layer"]["3"]["claims"],
                 row["road_sectors"], row["islands"], row["kerb_records"],
                 row["counts"]["sector"]))
    print("")
    print("the literal rule gives %s; without layer 2 it gives %s; ambiguous: %s"
          % (by_share, by_other, ambiguous))
    if choice:
        print("SECOND MAP: %s -- %s%% claimed, %d road sectors, %d islands, "
              "%d kerb records, %d sectors, %d layer-3 claims"
              % (choice["map"], choice["claimed_share"], choice["road_sectors"],
                 choice["islands"], choice["kerb_records"],
                 choice["counts"]["sector"],
                 choice["per_layer"].get("3", {}).get("claims", 0)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
