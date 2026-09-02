"""Stage 4 -- overlays: the islands, the sun, its field, and the lamps.

Two readers. `bloodmap.read_islands` recovers `overlay.HeightIsland` from the
map's own steps and then runs the WRITER's `overlay.kerb_records` over what it
recovered. `bloodmap.read_light` recovers the sun's bearing from the shade
boundaries -- the axis from the oblique ones, the sign from the perpendicular
ones -- then the field's levels, then which corner threw each shadow.

    PYTHONPATH=. python projects/e3m1-decompiled/source/stage4_overlays.py
"""

from __future__ import annotations

from collections import Counter

from _common import level, write
from _review import Tree, answers, write_pack

from bloodmap.light_field import MAX_LEVELS, STEP, STEP_ENVELOPE
from bloodmap.read_islands import read_islands, summary as island_summary
from bloodmap.read_joins import surface_kinds
from bloodmap.read_light import read_light, summary as light_summary
from bloodmap.texture_frame import sector_index


def _review(world, islands, light, network) -> dict:
    step = light["step"]
    outside, inside = step["outside_it"], step["inside_the_campaign_envelope"]
    voids = sum(row["what_the_other_side_is"].get("void", 0)
                for row in islands["islands_the_writer_over_claims"])
    cast = light["casters"]
    tree = Tree(len(world.sectors), "E3M1 -- islands and the light field")
    tree.add("scope", "out_of_scope",
             "not this layer's population (indoors, off the street network)",
             tree.root.id,
             [index for index in range(len(world.sectors)) if index not in network])
    tree.add("islands", "overlay",
             f"height islands, rise {islands['rise']}", tree.root.id,
             islands["island_sectors"])
    for island in islands["islands"]:
        tree.add(island["island_id"], "island",
                 f"{island['island_id']} x{len(island['sectors'])} "
                 f"kerb {island['kerb_tile']}", "islands", island["sectors"])
    field = light["field"]
    fitted = field["shades_that_fit_base_plus_k_step"]
    if fitted:
        tree.add("field", "overlay",
                 f"light field, base {field['lit_base']} + k*{STEP}",
                 tree.root.id,
                 [index for shade in fitted
                  for index in field["levels"][shade]["sectors"]])
        for shade, depth in sorted(fitted.items(), key=lambda row: row[1]):
            tree.add(f"depth:{depth}", "light_level",
                     f"depth {depth} = shade {shade}", "field",
                     field["levels"][shade]["sectors"])
    questions = [
        {"node": "field",
         "question": (f"E3M1's own shadow deltas are {step['deltas']}, median "
                      f"{step['median']}, not {STEP}. {outside} of "
                      f"{outside + inside} boundary "
                      f"records fall OUTSIDE the "
                      f"gate's envelope {list(STEP_ENVELOPE)}, so the map the "
                      f"street language was read from fails the gate the "
                      f"writer enforces. Is the envelope wrong, or is E3M1 "
                      f"outside it on purpose?"),
         "recommended_default": ("keep the envelope as a campaign envelope and "
                                 "state that E3M1 is outside it: my own "
                                 "re-measurement over 38 campaign maps gives "
                                 "median 12 and 53% inside [8, 16] on all "
                                 "parallax sectors, median 15 and 43% on the "
                                 "largest outdoor component only. The gate "
                                 "should say which network it means"),
         "evidence": "references/overlays.json: light.step, campaign_step"},
        {"node": "islands",
         "question": (f"`overlay.kerb_records` claims "
                      f"{islands['kerb_records_the_writer_claims']} kerb "
                      f"records over E3M1's {len(islands['islands'])} islands "
                      f"and the map makes "
                      f"{islands['kerb_records_the_map_makes']}. It emits one "
                      f"entry per outline edge and never reads its "
                      f"`ground_outline` argument, so it asks for a kerb on "
                      f"the {voids} edges facing the void too. Should it take "
                      f"the ground's edges, or should the caller filter?"),
         "recommended_default": ("`kerb_records` should use `ground_outline` -- "
                                 "it already takes it -- and emit a record "
                                 "only where the island edge is also a ground "
                                 "edge. This is a writer change and is "
                                 "reported, not made"),
         "evidence": "references/overlays.json: islands.islands_the_writer_over_claims"},
        {"node": "depth:0",
         "question": (f"The reader recovers a throw bearing of "
                      f"{light['sign']['throw_bearing_units']} build units "
                      f"against the project's cited 478, and the sign is "
                      f"unanimous ({light['sign']['far_end_boundaries']} "
                      f"far-end boundaries, {light['sign']['votes']}). But the "
                      f"corner test is a tie: "
                      f"{cast['up_sun_end_is_a_mass_corner']} of "
                      f"{cast['edges']} oblique edges have a mass corner up-sun "
                      f"and {cast['down_sun_end_is_a_mass_corner']} have one "
                      f"down-sun. Is that enough to call the casters "
                      f"recovered?"),
         "recommended_default": ("no. The bearing is recovered and the casters "
                                 "are not; the ledger says so rather than "
                                 "naming a caster the geometry does not "
                                 "choose"),
         "evidence": "references/overlays.json: light.casters"},
    ]
    return write_pack(4, tree, "E3M1 layer 4: islands and the light field",
                      questions)


def main() -> int:
    world = level()
    owners = sector_index(world)
    kinds = surface_kinds(world, owners=owners)
    islands = read_islands(world, kinds["kinds"], owners=owners)
    light = read_light(world, kinds["kinds"], owners=owners)
    network = set(light["network"])

    steps = islands["steps_that_are_not_islands_count"]
    rise_steps = kinds["steps_in_the_network"].get(islands["rise"], 0)
    off_bearing = len(light["axis"]["residue_edges_off_the_bearing"])
    on_bearing = light["axis"]["cluster_records"]
    fits = len(light["field"]["sectors_that_fit"])
    misfits = len(light["field"]["sectors_that_fit_no_level"])

    population = len(network) + rise_steps + steps + on_bearing + off_bearing
    explained = fits + rise_steps + on_bearing
    residue = misfits + steps + off_bearing

    payload = {
        "reader": "bloodmap.read_islands and bloodmap.read_light (both new; "
                  "the islands are replayed through overlay.kerb_records, the "
                  "writer)",
        "islands": islands,
        "island_summary": island_summary(islands),
        "light": {key: value for key, value in light.items()
                  if key not in ("shade_edges",)},
        "shade_edges": light["shade_edges"],
        "light_summary": light_summary(light),
        "campaign_step": _campaign_step(),
        "disagreements_with_the_measured_facts": _disagreements(islands, light),
        "ledger": {
            "reader": "bloodmap.read_islands, bloodmap.read_light (new)",
            "gate": ("the recovered islands replayed through "
                     "overlay.kerb_records and diffed against the records the "
                     "map actually kerbs; the recovered bearing against the "
                     "oblique boundaries; every sector's shade against "
                     f"base + k*{STEP}"),
            "population": (f"the street network: {len(network)} sectors, "
                           f"{rise_steps + steps} floor steps, "
                           f"{on_bearing + off_bearing} oblique shade edges "
                           f"= {population} items"),
            "explained": explained,
            "residue": residue,
            "residue_percent": round(100.0 * residue / population, 2),
            "residue_is": (f"{misfits} sectors whose shade is not "
                           f"base + k*{STEP}, {steps} floor steps that are not "
                           f"the island rise, {off_bearing} oblique shade "
                           f"edges not at the sun's bearing"),
            "disagreements": _disagreements(islands, light),
        },
    }
    payload["review"] = _review(world, islands, light, network)
    payload["owner_marks_read_back"] = answers(4)
    write("overlays.json", payload)

    print(f"E3M1 overlays, on {len(network)} street sectors")
    print(f"  islands            : {len(islands['islands'])} at rise "
          f"{islands['rise']}, kerb tiles {islands['kerb_tiles_seen']}")
    print(f"  kerb records       : the map makes "
          f"{islands['kerb_records_the_map_makes']}, "
          f"overlay.kerb_records claims "
          f"{islands['kerb_records_the_writer_claims']}")
    print(f"  sun axis           : {light['axis']['axis_degrees']} deg over "
          f"{light['axis']['cluster_records']} records "
          f"(spread {light['axis']['cluster_spread_degrees']})")
    print(f"  throw bearing      : {light['sign']['throw_bearing_units']} build "
          f"units, votes {light['sign']['votes']}")
    print(f"  field              : base {light['field']['lit_base']}, "
          f"{light['field']['significant_count']} significant levels, "
          f"deltas {light['step']['deltas']}")
    print(f"  fits base + k*{STEP}  : {fits} sectors; {misfits} fit no level "
          f"({light['field']['shades_that_fit_no_level']})")
    print(f"  casters            : up-sun "
          f"{light['casters']['up_sun_end_is_a_mass_corner']}, down-sun "
          f"{light['casters']['down_sun_end_is_a_mass_corner']}, neither "
          f"{light['casters']['neither_end_is']} of "
          f"{light['casters']['edges']} -- a tie, so not recovered")
    print(f"  lamps              : {light['lamps']['fullbright_sprites']} "
          f"fullbright sprites, tiles {light['lamps']['tiles']}")
    print(f"  RESIDUE            : {residue} of {population} items "
          f"({round(100.0 * residue / population, 2)}%)")
    return 0


def _claims(world, islands, light) -> list[dict]:
    """What the overlays reproduce, field by field.

    `floor_shade` is the ADDITIVE channel, so the field's claim on it is a
    contribution and not an ownership: a lamp claiming the same field later
    adds to it rather than conflicting with it, which is the whole reason
    `channels.py` made shade additive.
    """
    rows = []
    for island in islands["islands"]:
        for index in island["sectors"]:
            rows.append({
                "kind": "sector", "index": index, "field": "floor_z",
                "owner": island["island_id"],
                "value": int(world.sectors[index]["fields"]["floor_z"]),
                "why": (f"a HeightIsland of rise {island['rise']} on the base "
                        f"plane at z {islands['base_plane_z']}")})
    field = light["field"]
    for shade, depth in field["shades_that_fit_base_plus_k_step"].items():
        for index in field["levels"][shade]["sectors"]:
            rows.append({
                "kind": "sector", "index": index, "field": "floor_shade",
                "owner": f"sun:depth{depth}", "value": int(shade),
                "why": (f"the light field at depth {depth}: "
                        f"{field['lit_base']} + {depth}*{STEP} = {shade}, with "
                        f"the sun's throw at "
                        f"{light['sign']['throw_bearing_units']} build units")})
    return rows


def _campaign_step() -> dict:
    """The step re-measured over the campaign, by BOTH network definitions.

    The definition moves the answer, which is the finding: on all parallax
    sectors the median is 12 and half the boundaries lie in [8, 16], which is
    what decisions section 21 reports; on the largest outdoor component only
    it is 15 and 43%.
    """
    from bloodmap.format import read_map
    from bloodmap.patterns import list_corpus_maps
    from bloodmap.read_joins import adjacency, street_network
    from bloodmap.read_light import shade_edges

    out = {}
    for name, whole in (("all parallax sectors", True),
                        ("the largest outdoor component", False)):
        deltas: Counter = Counter()
        maps = 0
        for item in sorted(list_corpus_maps(population="blood-campaign"),
                           key=lambda row: row.path.stem):
            world = read_map(item.path).to_level_ir()
            owners = sector_index(world)
            if whole:
                network = {index for index, sector in enumerate(world.sectors)
                           if int(sector["fields"]["ceiling_stat"]) & 1}
            else:
                network, _ = street_network(world, adjacency(world, owners))
            if not network:
                continue
            maps += 1
            deltas.update(abs(row["shade_here"] - row["shade_there"])
                          for row in shade_edges(world, network, owners))
        values = sorted(deltas.elements())
        low, high = STEP_ENVELOPE
        inside = sum(count for delta, count in deltas.items()
                     if low <= delta <= high)
        out[name] = {
            "maps": maps, "boundary_records": len(values),
            "median": values[len(values) // 2] if values else None,
            "mean": round(sum(values) / len(values), 1) if values else None,
            "inside_the_envelope": inside,
            "inside_percent": round(100.0 * inside / len(values), 1) if values else None,
            "deltas": {int(k): int(v) for k, v in sorted(deltas.items())},
        }
    return out


def _disagreements(islands, light) -> list[dict]:
    out = []
    low, high = STEP_ENVELOPE
    outside = light["step"]["outside_it"]
    if outside:
        out.append({
            "claim": f"the light field quantises to base + k*{STEP}, and every "
                     f"shadow edge's delta lies in [{low}, {high}]",
            "the_reader_finds": (
                f"E3M1's own deltas are {light['step']['deltas']}: "
                f"{outside} of {outside + light['step']['inside_the_campaign_envelope']} "
                f"boundary records are outside the envelope, and only shades "
                f"{sorted(light['field']['shades_that_fit_base_plus_k_step'])} "
                f"of {sorted(light['field']['levels'])} fit base + k*{STEP}"),
            "reconciled": ("the base is right (8) and the level count is right "
                           f"({light['field']['significant_count']}, inside "
                           f"2-{MAX_LEVELS}); the STEP is not. E3M1's is 24-26, "
                           "twice the campaign median"),
        })
    axis = light["axis"]
    out.append({
        "claim": "20 oblique shade edges at ~84 degrees (SUN_BEARING 478)",
        "the_reader_finds": (
            f"{axis['oblique_edges']} oblique shade-boundary RECORDS in the "
            f"street network, {axis['cluster_records']} of them within "
            f"{axis['cluster_spread_degrees']} degrees of "
            f"{axis['axis_degrees']}; the throw bearing comes back as "
            f"{light['sign']['throw_bearing_units']} build units against the "
            f"cited 478, a difference of 0.18 degrees"),
        "reconciled": ("the bearing is confirmed to within one build unit. "
                       "The COUNT is not: 22 shade-boundary records over 24 "
                       "street sectors here against the cited 44 over 68. No "
                       "definition of the network reproduces 44/68 -- all "
                       "parallax sectors gives 22 over 45, parallax plus one "
                       "ring of neighbours 22 over 76"),
    })
    claimed = islands["kerb_records_the_writer_claims"]
    made = islands["kerb_records_the_map_makes"]
    if claimed != made:
        out.append({
            "claim": "overlay.kerb_records says which records carry the kerb",
            "the_reader_finds": (
                f"replayed over the three recovered islands it claims "
                f"{claimed} records; E3M1 makes {made}. It iterates the "
                f"island's outline and never reads its `ground_outline` "
                f"argument, so it asks for a kerb on every edge facing a "
                f"building, an interior or the void"),
            "reconciled": "the 11 it gets right are exactly the map's 11, all "
                          "wearing tile 6; the other 70 are edges that face "
                          "something that is not the road",
        })
    return out


if __name__ == "__main__":
    raise SystemExit(main())
