"""Run the Blood material-discovery experiments. Catalog/maps stay in work/."""

from __future__ import annotations

import json
from pathlib import Path

from bloodmap.analysis import render_svg, validate_map
from bloodmap.art import art_feature, feature_distance, read_art_directory, read_palette
from bloodmap.construction import LevelBuilder, portal_profiles
from bloodmap.designs import DesignedLevel
from bloodmap.format import read_map, write_map
from bloodmap.materials import (
    dump_json, families_from_evidence, import_annotations, load_json,
    ontology_aware_match, palette_vocabulary, query_materials, retrieve_palette,
    select_authoring_kit, similar_palettes, summarize_catalog,
)


ROOT = Path("work")
KNOWLEDGE = Path("knowledge/blood")
AUTHORING = ROOT / "material-authoring"
ROLES = {
    "structural_wall": {
        "surface_applicability": "vertical",
        "rendering_behavior": "opaque",
        "architectural_role": "structural_fill",
        "scale_behavior": "repeating_fill",
    },
    "floor": {
        "surface_applicability": "horizontal_floor",
        "rendering_behavior": "opaque",
        "architectural_role": "structural_fill",
    },
    "ceiling": {
        "surface_applicability": "horizontal_ceiling",
        "architectural_role": "structural_fill",
        "interaction_role": "static",
    },
    "masked_separator": {
        "architectural_role": "masked_separator",
        "rendering_behavior": "masked",
    },
    "interactive_control": {"interaction_role": "interactive_control"},
    "narrow_trim": {
        "architectural_role": "narrow_strip",
        "surface_applicability": "vertical",
        "interaction_role": "static",
    },
}


def _native(catalog: dict, ident: str | None, fallback: int) -> int:
    if not ident:
        return fallback
    return int(str(catalog["assets"][ident]["native_id"]))


def _nearest_appearance(seed: int, tiles: dict, palette, *, exclude: set[int], limit: int = 8) -> list[int]:
    feature = art_feature(tiles[seed], palette)
    ranked = []
    for tile_id, tile in tiles.items():
        if tile_id in exclude or tile_id == seed:
            continue
        ranked.append((feature_distance(feature, art_feature(tile, palette)), tile_id))
    ranked.sort()
    return [tile_id for _distance, tile_id in ranked[:limit]]


def build_probe(pics: dict[str, int], *, name: str) -> DesignedLevel:
    builder = LevelBuilder()
    main = builder.add_sector(
        [
            (0, 0), (6144, 0), (10240, 0), (16384, 0),
            (16384, 4608), (16384, 7680), (16384, 12288), (0, 12288),
        ],
        wall_picnum=pics["wall"], floor_picnum=pics["floor"], ceiling_picnum=pics["ceiling"],
        wall_shade=12, floor_shade=20,
    )
    first_door = builder.add_sector(
        [(16384, 4608), (18432, 4608), (18432, 7680), (16384, 7680)],
        ceiling_z=8192, floor_z=8192, type=600,
        wall_picnum=pics["door"], floor_picnum=pics["floor"], ceiling_picnum=pics["floor"],
        wall_shade=-8, floor_shade=-8, ceiling_shade=-8,
    )
    switch_alcove = builder.add_sector(
        [
            (18432, 2048), (26624, 2048), (26624, 10240),
            (18432, 10240), (18432, 7680), (18432, 4608),
        ],
        wall_picnum=pics["wall"], floor_picnum=pics["floor"], ceiling_picnum=pics["ceiling"],
        wall_shade=20, floor_shade=28,
    )
    builder.connect(main.wall_ids[4], first_door.wall_ids[3])
    builder.connect(first_door.wall_ids[1], switch_alcove.wall_ids[4])
    for wall_id in (main.wall_ids[4], first_door.wall_ids[3], first_door.wall_ids[1], switch_alcove.wall_ids[4]):
        wall = builder.level.walls[wall_id]["fields"]
        wall["over_picnum"] = pics["separator"]
        wall["cstat"] = int(wall.get("cstat") or 0) | 16
    if pics.get("trim"):
        builder.level.walls[main.wall_ids[0]]["fields"]["picnum"] = pics["trim"]
        builder.level.walls[main.wall_ids[7]]["fields"]["picnum"] = pics["trim"]
    builder.set_behavior(
        "sector", first_door.sector_id,
        state=0, busy=0, rx_id=100,
        busy_wave_a=0, busy_wave_b=0, busy_time_a=5, busy_time_b=5,
        rest_state=0, interruptable=0,
        off_ceiling_z=8192, on_ceiling_z=-24576,
        off_floor_z=8192, on_floor_z=8192,
    )
    switch = builder.add_sprite(
        sector=main.sector_id, x=16384, y=3072, z=-4096,
        type=21, picnum=pics["control"], status=0, angle=1024,
        cstat=464, x_repeat=40, y_repeat=40, shade=-8,
    )
    builder.set_behavior(
        "sprite", switch,
        state=0, rest_state=0, tx_id=100, command=1,
        trigger_on=1, trigger_off=0, trigger_push=1, data_1=203,
    )
    builder.set_player_start(sector=main.sector_id, x=15488, y=3072, z=0, angle=0)
    level = builder.build()
    profiles = portal_profiles(level, min_width=2048, min_opening=8192)
    report = {
        "$schema": "bloodmap.material-authoring-probe",
        "name": name,
        "picnums": pics,
        "spaces": {
            "main": main.sector_id,
            "door": first_door.sector_id,
            "alcove": switch_alcove.sector_id,
        },
        "control_sprite": switch,
        "portal_profiles": profiles,
        "counts": {
            "sectors": len(level.sectors),
            "walls": len(level.walls),
            "sprites": len(level.sprites),
        },
    }
    return DesignedLevel(level, report)


def write_level(result: DesignedLevel, stem: str) -> dict:
    AUTHORING.mkdir(parents=True, exist_ok=True)
    map_path = AUTHORING / f"{stem}.MAP"
    svg_path = AUTHORING / f"{stem}.svg"
    disk = result.level.to_disk_map()
    write_map(disk, map_path)
    reparsed = read_map(map_path)
    errors = [item.message for item in validate_map(reparsed) if item.severity == "error"]
    svg_path.write_text(render_svg(reparsed), encoding="utf-8", newline="\n")
    (AUTHORING / f"{stem}.report.json").write_text(
        json.dumps(result.report, indent=2) + "\n", encoding="utf-8",
    )
    return {
        "map": str(map_path),
        "svg": str(svg_path),
        "errors": errors,
        "picnums": result.report["picnums"],
        "counts": result.report["counts"],
    }


def conversion_case(catalog: dict, tiles: dict, palette) -> dict:
    """Separable conversion probe: role-aware ceiling pool vs ontology indoor fill."""
    from bloodmap.materials import rank_candidates

    brick_wall = catalog["assets"]["blood:tile:385"]
    indoor = catalog["assets"]["blood:tile:416"]
    ceiling_pool = [
        asset for asset in catalog["assets"].values()
        if asset["usage"]["ceiling"] > 0 and asset["usage"]["total"] > 0
    ]
    old_from_wall = rank_candidates(brick_wall, ceiling_pool, limit=5)
    old_from_indoor = rank_candidates(indoor, ceiling_pool, limit=5)
    new_from_wall = ontology_aware_match(
        catalog,
        source=brick_wall,
        require={
            "surface_applicability": "horizontal_ceiling",
            "architectural_role": "structural_fill",
            "interaction_role": "static",
        },
        limit=5,
    )
    new_from_indoor = ontology_aware_match(
        catalog,
        source=indoor,
        require={
            "surface_applicability": "horizontal_ceiling",
            "architectural_role": "structural_fill",
            "interaction_role": "static",
        },
        limit=5,
    )
    sky = query_materials(catalog, require={"architectural_role": "sky_sheet"}, limit=3)
    return {
        "source_a": {
            "asset": "blood:tile:385",
            "evidence": "93% wall brick; used as the scratch-room ceiling default",
            "old_top": old_from_wall,
            "new_top": new_from_wall,
        },
        "source_b": {
            "asset": "blood:tile:416",
            "evidence": "97% ceiling indoor fill; role-aware pool still contains mixed and sky tiles",
            "old_top": old_from_indoor,
            "new_top": new_from_indoor,
        },
        "sky_family": sky,
        "old_method": "rank among any corpus tile with ceiling>0 (the role-aware ART ceiling pool, including mixed-use and parallax sheets)",
        "new_method": "ontology require horizontal_ceiling + structural_fill + static",
        "why_better": (
            "Role-aware matching still treats 'used as a ceiling at least once' as one family. "
            "That pool includes sky sheets 2500/3491/3678 and mixed wall/ceiling tiles. "
            "Ontology keeps indoor fill, sky sheets, and animated liquid ceilings in different query slots. "
            "Assigning brick wall 385 as a ceiling is the construction-default failure mode."
        ),
        "kept_separable": True,
        "converter_unchanged": "bloodmap.e3l11._apply_materials still uses role-aware ART nearest-neighbour",
    }


def main() -> None:
    catalog = load_json(ROOT / "blood.materials.json")
    v1 = json.loads((KNOWLEDGE / "ontology-v1.json").read_text(encoding="utf-8"))
    v2 = json.loads((KNOWLEDGE / "ontology-v2.json").read_text(encoding="utf-8"))
    import_annotations(catalog, v1)
    v1_contradictions = [
        item for item in catalog.get("contradictions") or []
        if item.get("asset") in {note["asset"] for note in v1["annotations"]}
        and item.get("facet")
    ]
    (KNOWLEDGE / "contradictions-v1.json").write_text(
        json.dumps({"count": len(v1_contradictions), "items": v1_contradictions}, indent=2) + "\n",
        encoding="utf-8",
    )
    dump_json(ROOT / "blood.material-knowledge-v1.json", catalog)
    import_annotations(catalog, v2)
    catalog["families"] = families_from_evidence(catalog)
    dump_json(ROOT / "blood.material-knowledge-v2.json", catalog)

    queries = {
        "vertical_opaque_fill": query_materials(catalog, require={
            "surface_applicability": "vertical", "rendering_behavior": "opaque",
            "architectural_role": "structural_fill",
        }, limit=5),
        "floor_fill": query_materials(catalog, require={"surface_applicability": "horizontal_floor"}, limit=5),
        "indoor_ceiling": query_materials(catalog, require={
            "surface_applicability": "horizontal_ceiling",
            "architectural_role": "structural_fill",
            "interaction_role": "static",
        }, limit=5),
        "sky_sheet": query_materials(catalog, require={"architectural_role": "sky_sheet"}, limit=5),
        "masked_separator": query_materials(catalog, require={"architectural_role": "masked_separator"}, limit=5),
        "like_110_floor": query_materials(catalog, like="blood:tile:110", require={
            "surface_applicability": "horizontal_floor",
        }, limit=5),
        "control": query_materials(catalog, require={"interaction_role": "interactive_control"}, limit=5),
        "alternatives_to_110": query_materials(catalog, like="blood:tile:110", require={
            "surface_applicability": "vertical", "architectural_role": "structural_fill",
        }, limit=5),
    }
    kit = select_authoring_kit(catalog, ROLES, limit=3)
    palettes = {
        "stone_and_fence": {
            "seed": ["blood:tile:110", "blood:tile:270", "blood:tile:330"],
            "vocabulary": palette_vocabulary(catalog, ["blood:tile:110", "blood:tile:270", "blood:tile:330", "blood:tile:109"]),
            "similar": similar_palettes(catalog, ["blood:tile:110", "blood:tile:270", "blood:tile:330"], limit=6),
            "e1m1": retrieve_palette(catalog, like="blood:tile:110", map_name="E1M1.MAP")[:5],
        },
        "sky_exposed": {
            "seed": ["blood:tile:2500", "blood:tile:3678"],
            "vocabulary": palette_vocabulary(catalog, ["blood:tile:2500", "blood:tile:3678", "blood:tile:2448", "blood:tile:319"]),
            "similar": similar_palettes(catalog, ["blood:tile:2500", "blood:tile:3678"], limit=6),
        },
        "liquid": {
            "seed": ["blood:tile:1030", "blood:tile:1120"],
            "vocabulary": palette_vocabulary(catalog, ["blood:tile:1030", "blood:tile:1120", "blood:tile:1029"]),
            "similar": similar_palettes(catalog, ["blood:tile:1030", "blood:tile:1120"], limit=6),
        },
    }

    art_dir = Path("reference/blood")
    tiles = read_art_directory(art_dir)
    palette = read_palette(art_dir / "xmapedit" / "palettes" / "import" / "BLOOD.PAL")
    nearest = _nearest_appearance(110, tiles, palette, exclude={0, 255}, limit=8)
    naive_pics = {
        "wall": 110,
        "floor": nearest[0],
        "ceiling": nearest[1],
        "door": nearest[2],
        "separator": nearest[3],
        "control": nearest[4],
        "trim": nearest[5],
    }
    knowledge_pics = {
        "wall": kit["roles"]["structural_wall"]["chosen_tile"] or 110,
        "floor": kit["roles"]["floor"]["chosen_tile"] or 270,
        "ceiling": kit["roles"]["ceiling"]["chosen_tile"] or 416,
        "door": kit["roles"]["structural_wall"]["chosen_tile"] or 110,
        "separator": kit["roles"]["masked_separator"]["chosen_tile"] or 330,
        "control": kit["roles"]["interactive_control"]["chosen_tile"] or 1070,
        "trim": kit["roles"]["narrow_trim"]["chosen_tile"] or 93,
    }
    naive_level = write_level(build_probe(naive_pics, name="naive-appearance"), "naive-appearance")
    knowledge_level = write_level(build_probe(knowledge_pics, name="ontology-aware"), "ontology-aware")
    defaults_level = write_level(build_probe({
        "wall": 180, "floor": 292, "ceiling": 385, "door": 104,
        "separator": 104, "control": 1070, "trim": 180,
    }, name="construction-defaults"), "construction-defaults")

    conversion = conversion_case(catalog, tiles, palette)
    report = {
        "summary": summarize_catalog(catalog),
        "ontology": {
            "version": catalog["ontology"]["version"],
            "history": [item.get("version") for item in catalog.get("ontology_history") or []],
            "surviving_facets": [
                {"id": facet["id"], "values": facet["values"], "useful_for": facet["useful_for"]}
                for facet in catalog["ontology"]["facets"]
            ],
            "rejected": catalog["ontology"]["rejected_distinctions"],
            "revision_notes": catalog["ontology"].get("revision_notes"),
        },
        "v1_annotation_contradictions": len(v1_contradictions),
        "v2_annotation_contradictions": len([
            item for item in catalog.get("contradictions") or []
            if item.get("facet") and item.get("asset") in {note["asset"] for note in v2["annotations"]}
        ]),
        "queries": queries,
        "authoring_kit": kit,
        "palettes": palettes,
        "naive_vs_knowledge": {
            "intent": "dark old interior: structural wall, coherent floor/ceiling, door, masked separator, interactive control, limited trim",
            "naive_appearance_neighbors_of_110": nearest,
            "naive": naive_level,
            "knowledge": knowledge_level,
            "construction_defaults": defaults_level,
            "evaluation": {
                "functional_appropriateness": (
                    f"Naive puts appearance-neighbors of wall 110 on floor ({naive_pics['floor']}), "
                    f"ceiling ({naive_pics['ceiling']}), separator ({naive_pics['separator']}), and control "
                    f"({naive_pics['control']}). Knowledge uses wall {knowledge_pics['wall']}, floor "
                    f"{knowledge_pics['floor']}, indoor ceiling {knowledge_pics['ceiling']}, masked fence "
                    f"{knowledge_pics['separator']}, switch {knowledge_pics['control']}, trim {knowledge_pics['trim']}."
                ),
                "surface_role_correctness": "Knowledge respects vertical/floor/ceiling/masked/sprite splits; naive does not.",
                "scale": "Knowledge trim 93 and separator 330 are narrow_repeat; naive separator is another repeating fill.",
                "palette_coherence": "110+270+330 co-occur in original maps; nearest-to-110 floors/ceilings need not.",
                "construction_defaults_note": "Default ceiling 385 is 93% wall; default door 104 has 2 corpus uses.",
            },
        },
        "conversion": conversion,
        "families": [
            {"id": family["id"], "kind": family["kind"], "members": family.get("members"), "basis": family.get("basis")}
            for family in catalog["families"]
            if family.get("kind") in {"functional", "stateful", "native_animation"}
        ][:20],
    }
    (KNOWLEDGE / "experiments.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "v1_contradictions": report["v1_annotation_contradictions"],
        "v2_contradictions": report["v2_annotation_contradictions"],
        "kit": {role: payload["chosen_tile"] for role, payload in kit["roles"].items()},
        "naive": naive_pics,
        "knowledge": knowledge_pics,
        "conversion_old_wall": [item["asset"] for item in conversion["source_a"]["old_top"][:3]],
        "conversion_new_wall": [item["asset"] for item in conversion["source_a"]["new_top"][:3]],
        "conversion_old_ceil": [item["asset"] for item in conversion["source_b"]["old_top"][:3]],
        "conversion_new_ceil": [item["asset"] for item in conversion["source_b"]["new_top"][:3]],
        "maps": [naive_level["map"], knowledge_level["map"]],
        "errors": naive_level["errors"] + knowledge_level["errors"] + defaults_level["errors"],
    }, indent=2))


if __name__ == "__main__":
    main()
