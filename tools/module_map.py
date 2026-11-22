"""Write `docs/module-map.md`: every library module and tool, one line each, by layer.

The page exists so that the question "is there already something for this?"
has an answer that takes one read and cannot go stale. Each line is the first
sentence of the module's own docstring; the only thing kept here is which
layer a module belongs to. A module nobody has placed fails the check, which
is the point: adding one means deciding where it sits.

.. code-block:: bash

    python -m tools.module_map            # rewrite docs/module-map.md
    python -m tools.module_map --check    # exit 1 if it is out of date
"""

from __future__ import annotations

import argparse
import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "module-map.md"

#: Library layers, lowest first. A module may import from its own layer and
#: the ones above it in this list; the exceptions are function-local imports
#: and are listed in `docs/architecture.md`.
LIBRARY: list[tuple[str, str, list[str]]] = [
    ("Native formats",
     "Bytes to exact models and back. Nothing here interprets; every writer "
     "reconstructs the file from decoded fields.",
     ["format", "model", "duke", "doom", "art"]),
    ("Corpus",
     "Where a map came from and how to list one population. Never glob a "
     "directory.",
     ["corpus", "tiering"]),
    ("Shared IR and geometry",
     "One contract for Build sectors, walls and sprites, and the geometry "
     "every other layer measures with.",
     ["build_ir", "analysis", "sector_geom", "planar_geom", "sector_map"]),
    ("Engine facts",
     "What the engine does, transcribed and citable: type names, the "
     "player's body, the renderer's wall pass, motion.",
     ["blood_types", "player_space", "render_slots", "drawsort", "flatsprite",
      "overlap_visibility", "motion", "motion_sim", "swept_state",
      "duke_motion"]),
    ("Sensors",
     "Derived readings of a map. Never authoritative, never written back.",
     ["design", "spatial", "sight", "exposure", "morphology", "contents",
      "reachability", "relations", "patterns", "anchors", "structures",
      "materials", "level_profile", "effects", "wiring", "posed", "completion", "assembly", "conditional",
      "progression", "understanding", "sp_understand", "bundle", "style"]),
    ("Probes",
     "Replayable questions about a level, with explicit world state.",
     ["experience", "probes", "probe_schema", "state_model", "counterfactual",
      "design_contract"]),
    ("Semantics",
     "Mechanisms named above their native encodings, per game and across "
     "games.",
     ["semantics", "mechanisms", "duke_semantics", "doom_semantics", "doors"]),
    ("Authoring: structure",
     "Writing a level as source. `LevelProgram` is the editable form; it "
     "lowers through `PlanarLayout` into `LevelIR`.",
     ["levelprog", "planar_layout", "layout", "layers", "vocabulary",
      "prefab", "aperture", "breach", "slope", "spiral", "roomoverroom", "skyline",
      "overlay", "construction", "composition", "fragment", "recipe",
      "designs"]),
    ("Authoring: surfaces and light",
     "What a surface is made of, where its texture sits, and how it is lit.",
     ["surface", "surfaces", "joins", "texture_frame", "texture_align",
      "glass", "lettering", "lighting", "lightbomb", "light_field", "sunlight",
      "overlays", "shade_table", "daylight", "light_kinds", "light_stage"]),
    ("Authoring: things and mechanisms",
     "Sprites, fixtures, controls and moving parts, built from mined "
     "templates.",
     ["placement", "furniture", "decoration", "item_display", "keys",
      "switches", "mechanism", "channels", "arbiter", "construct"]),
    ("Authoring: the city",
     "Street and block vocabulary, and the compiler pipeline that runs the "
     "passes in order.",
     ["street", "street_model", "city", "pipeline"]),
    ("Reading a map back",
     "The inverse of the writers: a built or original map read into facts, "
     "claims and a hierarchy, and diffed against what was declared.",
     ["decompiler", "readback", "conformance", "geometry_audit", "facts",
      "read_store", "read_facts", "read_ledger", "read_census",
      "read_surfaces", "read_joins", "read_islands", "read_light",
      "read_stairs", "read_mechanisms", "read_edges", "read_plan",
      "read_intent", "contradictions"]),
    ("Rules and knowledge",
     "Graded claims about Blood, the owner's tile readings, and the indexes "
     "over `knowledge/blood/`.",
     ["rules", "rules_blood", "owner_anchors", "usage_kinds", "tile_contexts", "curriculum",
      "curriculum_laws", "examples", "assets", "knowledge_index"]),
    ("Evidence loop and observation",
     "Compile a candidate, read it back independently, look at it through "
     "the observer, and keep the packet.",
     ["authoring_loop", "visual", "viewplan", "viewpoints", "view_score",
      "oracle", "workspace"]),
    ("Cross-game conversion",
     "A converted map is a new authored map with a fidelity report, never a "
     "roundtrip.",
     ["conversion", "differential", "doom_geometry", "doom_convert",
      "doom_fixtures", "e3l11"]),
    ("Entry points",
     "The `python -m bloodmap` command line and the package's re-exports.",
     ["cli", "__init__", "__main__"]),
]

#: Tools by what they are for. A tool is a sensor's run over a corpus, a
#: check of one map, or a way of looking; the logic it runs lives in the
#: library.
TOOLS: list[tuple[str, str, list[str]]] = [
    ("Measuring the campaign",
     "Each runs a library sensor over `corpus.campaign_maps()` and writes a "
     "versioned file under `knowledge/blood/design/`.",
     ["mine_apertures", "mine_assemblies", "mine_decoration", "mine_keys",
      "mine_layers", "mine_mechanisms", "mine_monuments", "mine_overlooks",
      "mine_patterns", "mine_prefabs", "mine_prop_catalogue",
      "mine_run_rhythm", "mine_sector_motion_sounds", "mine_set_pieces", "mine_skylines",
      "mine_sprite_heights", "mine_stacks", "mine_storeys",
      "mine_structures", "mine_style_combinations", "mine_surface_items",
      "mine_surface_palettes", "mine_switches", "mine_texture_fit",
      "mine_usage_kinds", "mine_visual_norms", "mine_wall_sprites",
      "mine_wall_thickness", "design_norms", "grade_rules", "link_census",
      "sweep_drag_closure", "measure_draw_order", "texture_continuity"]),
    ("Measuring towns and other games",
     "Precedent for the city: Blood's town maps, and Duke's, in units that "
     "cross between them.",
     ["city_profile", "mine_city_assets", "mine_city_norms", "plot_city_norms",
      "mine_e6m1_shop", "mine_fixtures", "mine_room_grammar",
      "mine_sewer_kit", "mine_sewers", "mine_stands", "mine_urban_semantics",
      "mine_venues", "mine_duke_mechanisms", "extract_duke_semantics",
      "read_duke_signs", "duke_view"]),
    ("Checking a built map",
     "Lints and comparisons of one map against the engine or the campaign.",
     ["sprite_fit", "light_profile", "light_sources", "reading_check", "unattested_values", "map_discriminator", "symmetry_diff",
      "inspect_mechanisms", "verify_motion", "render_conflicts",
      "vector_solver", "vector_report", "bunch_order", "build2d_core",
      "whatif", "judge_experiment"]),
    ("Looking",
     "Render what the game shows, through the XMapEdit observer.",
     ["observe", "render_precedent", "sweep_views", "look_at", "mechanism_look", "tile_usage",
      "showcase", "plan_view"]),
    ("The library of Blood",
     "Tiles, places, studies and ideas (`knowledge/blood/LIBRARY.md`), and "
     "the readers that criticise a place.",
     ["catalog", "study", "ideas", "place_character", "tile_naming_sheet",
      "critique", "critic_bench", "critic_lab", "tile_contexts", "wiki_levels",
      "sound_catalog", "sound_readback"]),
    ("Decompiling an original map",
     "From one MAP to a project: hierarchy, fact store, review packs, and "
     "the round trip that rebuilds it.",
     ["decompile_project", "decompile_stages", "emit_level_program",
      "propose_areas", "review_pack", "round_trip", "fragment_map"]),
    ("The frozen authoring pilot",
     "Records of `projects/reasoned-authoring-v1`; kept so its evidence "
     "still checks.",
     ["build_precedent_packet", "mine_precedents", "precedent_detail",
      "check_authoring_archive"]),
    ("Bot run analysis",
     "Reading the NBlood playtest bot's telemetry.",
     ["bot_invariants", "bot_map_render", "bot_narrative", "bot_scorecard",
      "map_topology"]),
    ("This repository",
     "Keeping the map of the code current.",
     ["module_map"]),
]

HEADER = """# The module map

Every module in `bloodmap/` and every tool in `tools/`, one line each. Look
here before writing a helper: if it is about a map, somebody has probably
already written it.

Generated by `python -m tools.module_map` from each module's own docstring;
`tests/test_module_map.py` fails when this page is out of date or a module
has not been placed in a layer. Which module owns which *kind of fact* is
[architecture](architecture.md); what to reach for when building is
[the toolkit index](toolkit-index.md).
"""


def first_sentence(path: pathlib.Path) -> str:
    """The opening sentence of a module's docstring, on one line."""
    source = path.read_text(encoding="utf-8")
    doc = ast.get_docstring(ast.parse(source)) or ""
    paragraph = " ".join(doc.strip().split("\n\n")[0].split())
    match = re.match(r"(.+?[.!?])(?:\s|$)", paragraph)
    sentence = match.group(1) if match else paragraph
    # A sentence that ends in a colon was introducing a list; keep the clause.
    return sentence.rstrip(":").strip()


def module_path(folder: str, name: str) -> pathlib.Path:
    direct = ROOT / folder / f"{name}.py"
    return direct if direct.exists() else ROOT / folder / name / "__init__.py"


def present(folder: str) -> set[str]:
    base = ROOT / folder
    names = {path.stem for path in base.glob("*.py")}
    names |= {path.name for path in base.iterdir()
              if path.is_dir() and (path / "__init__.py").exists()}
    return names


def problems() -> list[str]:
    """Everything that stops the page being a true map of the code."""
    found: list[str] = []
    for folder, groups, skip in (("bloodmap", LIBRARY, set()),
                                 ("tools", TOOLS, {"__init__"})):
        placed = [name for _title, _why, names in groups for name in names]
        twice = sorted({name for name in placed if placed.count(name) > 1})
        there = present(folder) - skip
        for name in sorted(there - set(placed)):
            found.append(f"{folder}/{name} is not placed in any layer")
        for name in sorted(set(placed) - there):
            found.append(f"{folder}/{name} is listed and does not exist")
        for name in twice:
            found.append(f"{folder}/{name} is listed twice")
        for name in sorted(there & set(placed)):
            if name in ("__main__",):
                continue
            if not first_sentence(module_path(folder, name)):
                found.append(f"{folder}/{name} has no docstring to quote")
    return found


def render() -> str:
    out = [HEADER]
    for heading, folder, groups in (("The library: `bloodmap/`", "bloodmap", LIBRARY),
                                    ("The tools: `tools/`", "tools", TOOLS)):
        out.append(f"## {heading}\n")
        for title, why, names in groups:
            out.append(f"### {title}\n")
            out.append(f"{why}\n")
            out.append("| Module | What it is |")
            out.append("| --- | --- |")
            for name in names:
                path = module_path(folder, name)
                said = first_sentence(path) if path.exists() else ""
                if name == "__main__":
                    said = "Runs `cli.main`."
                out.append(f"| `{name}` | {said.replace('|', '/')} |")
            out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true",
                        help="report instead of writing; exit 1 if stale")
    args = parser.parse_args(argv)

    found = problems()
    for line in found:
        print(line, file=sys.stderr)
    text = render()
    if args.check:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != text:
            print(f"{OUTPUT.relative_to(ROOT).as_posix()} is out of date; "
                  f"run python -m tools.module_map", file=sys.stderr)
            return 1
        return 1 if found else 0
    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT.relative_to(ROOT).as_posix()}")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
