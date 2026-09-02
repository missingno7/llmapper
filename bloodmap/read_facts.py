"""Every reader as a function from facts to facts.

`RESEARCH-OVERLAPPING-LAYERS-2026-09-02.md` section 3: the readers live in
`bloodmap` and emit facts; the project only orchestrates and stores. So each
`layerN` function here takes a level and a `FactStore` that already holds the
base facts, and returns the facts that layer derives -- with the base facts it
came from, and the reader that made it, on every row.

Nothing here mutates the level, and nothing deletes a fact. A reading that
could go two ways is emitted as `candidate` rows and left for a `selection`
pass with its criterion stated; a field nothing explains is emitted as
`residue`. Both are predicates like any other.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any, Sequence

from .read_store import Fact, FactStore
from .read_ledger import channel_of, fields_of

SECTOR, WALL, SPRITE = "sector", "wall", "sprite"


def _ids(kind: str, indexes) -> tuple[str, ...]:
    return tuple(f"{kind}:{int(index)}" for index in indexes)


#: `layer -> the module whose reading a claim of that layer came from`. The
#: OWNER of a claim is the thing that explains the field (a surface, a join
#: row, an island, a sentence); the READER is the code that found it. Keeping
#: them apart is what lets the manifest's `readers` count modules instead of
#: listing three hundred surface ids.
CLAIM_READERS = {
    2: "bloodmap.read_surfaces+read_stairs", 3: "bloodmap.read_joins",
    4: "bloodmap.read_islands+read_light", 5: "bloodmap.read_mechanisms",
    6: "bloodmap.read_edges", 7: "bloodmap.read_plan",
}


def _claim(record: str, name: str, value: Any, *, layer: int, owner: str,
           why: str, sources: Sequence[str] = ()) -> Fact:
    kind = record.split(":", 1)[0]
    return Fact("claims", f"{record}:{name}",
                {"record": record, "field": name, "value": value,
                 "channel": channel_of(kind, name), "aspect": owner,
                 "why": why},
                sources=tuple(sources) or (record,),
                reader=CLAIM_READERS.get(layer, "claim"), layer=layer)


# ---------------------------------------------------------------------------
# layer 1: the space tree, as `part_of` facts
# ---------------------------------------------------------------------------

def _sectors_of(node: dict[str, Any]) -> list[int]:
    """A node's sectors, in either shape the project produces.

    `decompiler.decompile_level` nests them under `sources`;
    `tools/decompile_project`'s reading view flattens them to `sectors`. The
    census runs the readers on maps that have no project directory, so it
    hands over the first shape and the stages hand over the second.
    """
    if "sectors" in node:
        return list(node["sectors"])
    return list(node.get("sources", {}).get("sectors", ()))


def _basis_of(node: dict[str, Any]) -> list[str]:
    """Why a node exists, in either shape: flat `basis`, or nested under
    `provenance`."""
    if "basis" in node:
        return list(node["basis"])
    return list((node.get("provenance") or {}).get("basis") or [])


def layer1(level: Any, hierarchy: dict[str, Any]) -> list[Fact]:
    """A hierarchy is a set of `part_of` facts, not a tree object.

    Which is the point of saying it this way: two hierarchies can then coexist
    over one record set without either being "the" tree, and the aspect is an
    attribute rather than a file.
    """
    reader = "bloodmap.decompiler.decompile_level"
    out: list[Fact] = []
    for node in hierarchy["nodes"]:
        if node["parent"] is None:
            continue
        out.append(Fact("part_of", f"space:{node['id']}",
                        {"child": node["id"], "parent": node["parent"],
                         "aspect": "space", "kind": node["kind"],
                         "grouped_by_evidence": not any(
                             "reviewable singleton" in basis
                             for basis in _basis_of(node)),
                         "basis": _basis_of(node)},
                        sources=_ids(SECTOR, _sectors_of(node)),
                        reader=reader, layer=1))
        for sector in _sectors_of(node):
            out.append(Fact("part_of", f"space:{node['id']}:sector:{sector}",
                            {"child": f"sector:{sector}", "parent": node["id"],
                             "aspect": "space", "kind": "member"},
                            sources=(f"sector:{sector}",),
                            reader=reader, layer=1))
    residue = [node for node in hierarchy["nodes"]
               if node["kind"] == "space" and any(
                   "reviewable singleton" in basis
                   for basis in _basis_of(node))]
    for node in residue:
        for sector in _sectors_of(node):
            out.append(Fact("residue", f"space:sector:{sector}",
                            {"about": f"sector:{sector}", "aspect": "space",
                             "why": "no perceptual-space evidence groups this "
                                    "sector; it is in the tree only so the "
                                    "partition closes"},
                            sources=(f"sector:{sector}",),
                            reader=reader, layer=1))
    return out


# ---------------------------------------------------------------------------
# layer 2: surfaces, frames, stairs
# ---------------------------------------------------------------------------

FRAME_FIELDS = ("picnum", "x_repeat", "x_panning", "y_repeat", "y_panning")


def layer2(level: Any, surfaces: dict[str, Any], stairs: dict[str, Any]
           ) -> list[Fact]:
    reader = "bloodmap.read_surfaces"
    out: list[Fact] = []
    for surface in surfaces["surfaces"]:
        if len(surface.records) < 2:
            continue
        sources = _ids(WALL, surface.records)
        out.append(Fact("surface", surface.surface_id,
                        {"tile": surface.tile, "records": list(surface.records),
                         "exact": len(surface.exact),
                         "world_phased": surface.world_phased},
                        sources=sources, reader=reader, layer=2))
        out.append(Fact("frame", f"frame:{surface.surface_id}",
                        {"surface": surface.surface_id,
                         "tile": int(surface.frame.tile),
                         "texels_per_unit": float(surface.frame.texels_per_unit),
                         "u0": int(surface.frame.u0),
                         "v0": None if surface.frame.v0 is None else int(surface.frame.v0),
                         "y_repeat": int(surface.frame.y_repeat),
                         "flip": int(surface.frame.flip)},
                        sources=(surface.surface_id,), reader=reader, layer=2))
        for record in surface.records:
            out.append(Fact("attachment", f"{surface.surface_id}:wall:{record}",
                            {"surface": surface.surface_id,
                             "record": f"wall:{record}",
                             "reproduced": record in surface.exact},
                            sources=(f"wall:{record}", surface.surface_id),
                            reader=reader, layer=2))
        for record in surface.exact:
            face = level.walls[record]["fields"]
            for name in FRAME_FIELDS:
                out.append(_claim(f"wall:{record}", name, int(face[name]),
                                  layer=2, owner=surface.surface_id,
                                  why="one frame over "
                                      f"{len(surface.records)} records replays "
                                      "through texture_frame.resolve_run to "
                                      "this value",
                                  sources=(f"wall:{record}",
                                           f"frame:{surface.surface_id}")))
    for record in surfaces["residue_broken"]:
        out.append(Fact("residue", f"surface:broken:wall:{record}",
                        {"about": f"wall:{record}", "aspect": "surface",
                         "why": "broken off a same-material neighbour: the "
                                "projection does not continue across the "
                                "shared vertex"},
                        sources=(f"wall:{record}",),
                        reader=reader, layer=2))
    for record in surfaces["residue_solitary"]:
        out.append(Fact("residue", f"surface:solitary:wall:{record}",
                        {"about": f"wall:{record}", "aspect": "surface",
                         "why": "no same-material neighbour at all: a frame "
                                "fitted to it would reproduce it for free"},
                        sources=(f"wall:{record}",),
                        reader=reader, layer=2))

    stair_reader = "bloodmap.read_stairs"
    for run in stairs["runs"]:
        fit = run["fit"]
        out.append(Fact("stepped_run", run["id"],
                        {"sectors": run["sectors"], "rise": fit["rise"],
                         "origin": fit["origin"],
                         "constant_rise": fit["constant_rise"],
                         "parameters": run["parameters"],
                         "residual_sectors": fit["residual"]},
                        sources=_ids(SECTOR, run["sectors"]),
                        reader=stair_reader, layer=2))
        for index in fit["reproduces"]:
            out.append(_claim(f"sector:{index}", "floor_z",
                              int(level.sectors[index]["fields"]["floor_z"]),
                              layer=2, owner=run["id"],
                              why=f"a stepped run of rise {fit['rise']} from "
                                  f"{fit['origin']}: this floor lands on the "
                                  f"fitted progression",
                              sources=(f"sector:{index}", run["id"])))
        for index in fit["residual"]:
            out.append(Fact("residue", f"stair:residual:sector:{index}",
                            {"about": f"sector:{index}", "aspect": "structure",
                             "why": f"in {run['id']} but off its fitted "
                                    f"progression of rise {fit['rise']}"},
                            sources=(f"sector:{index}", run["id"]),
                            reader=stair_reader, layer=2))
    return out


# ---------------------------------------------------------------------------
# layer 3: kinds and joins
# ---------------------------------------------------------------------------

def layer3(level: Any, joins_result: dict[str, Any]) -> list[Fact]:
    from . import joins as writer
    from .joins import TILE_CLASSES

    reader = "bloodmap.read_joins"
    kinds = joins_result["kinds"]
    census = joins_result["census"]
    out: list[Fact] = []
    for index, kind in sorted(kinds["kinds"].items()):
        out.append(Fact("surface_kind", f"sector:{index}",
                        {"record": f"sector:{index}", "kind": kind,
                         "why": kinds["why"][index]},
                        sources=(f"sector:{index}",), reader=reader, layer=3))
    for key, records in census["described_records"].items():
        a, b, height = key.split("|")
        rule = writer.rule(a, b, height)
        wanted = next((value for cls, value in TILE_CLASSES.items()
                       if cls in rule.a_shows), None)
        for record in records:
            face = level.walls[record]["fields"]
            out.append(Fact("join", f"wall:{record}",
                            {"record": f"wall:{record}", "a": a, "b": b,
                             "height": height, "row": key,
                             "shows": rule.a_shows, "frame": rule.frame,
                             "wears_tile": int(face["picnum"]),
                             "blocking": bool(int(face["cstat"]) & 1)},
                            sources=(f"wall:{record}",), reader=reader, layer=3))
            if wanted is not None and int(face["picnum"]) == wanted:
                out.append(_claim(f"wall:{record}", "picnum", int(face["picnum"]),
                                  layer=3, owner=f"join:{key}",
                                  why=f"the {key} row shows {rule.a_shows!r} "
                                      f"and the class resolves to tile {wanted}"))
            if rule.cstat and (int(face["cstat"]) & rule.cstat) == rule.cstat:
                out.append(_claim(f"wall:{record}", "cstat", int(face["cstat"]),
                                  layer=3, owner=f"join:{key}",
                                  why=f"the {key} row sets cstat {rule.cstat} "
                                      f"and this record carries it"))
    for key, records in census["undescribed_records"].items():
        for record in records:
            out.append(Fact("unknown_join", f"wall:{record}",
                            {"record": f"wall:{record}", "pair": key},
                            sources=(f"wall:{record}",), reader=reader, layer=3))
            out.append(Fact("residue", f"join:wall:{record}",
                            {"about": f"wall:{record}", "aspect": "join",
                             "why": f"the writer's table has no row for {key}"},
                            sources=(f"wall:{record}",), reader=reader, layer=3))
    return out


# ---------------------------------------------------------------------------
# layer 4: islands, the sun, its field, the lamps
# ---------------------------------------------------------------------------

def layer4(level: Any, islands: dict[str, Any], light: dict[str, Any]
           ) -> list[Fact]:
    from .light_field import STEP

    reader = "bloodmap.read_islands"
    out: list[Fact] = []
    for island in islands["islands"]:
        out.append(Fact("island", island["island_id"],
                        {"sectors": island["sectors"], "rise": island["rise"],
                         "kerb_tile": island["kerb_tile"],
                         "boundary_faces": island["boundary_faces"]},
                        sources=_ids(SECTOR, island["sectors"]),
                        reader=reader, layer=4))
        for index in island["sectors"]:
            out.append(_claim(f"sector:{index}", "floor_z",
                              int(level.sectors[index]["fields"]["floor_z"]),
                              layer=4, owner=island["island_id"],
                              why=f"a HeightIsland of rise {island['rise']} on "
                                  f"the base plane at z {islands['base_plane_z']}",
                              sources=(f"sector:{index}", island["island_id"])))
    for size, count in islands["steps_that_are_not_islands"].items():
        out.append(Fact("residue", f"island:step:{size}",
                        {"about": f"{count} floor steps of {size}",
                         "aspect": "island",
                         "why": f"not the measured island rise "
                                f"({islands['rise']}): a wall top rather than "
                                f"a step"},
                        reader=reader, layer=4))

    light_reader = "bloodmap.read_light"
    sign = light.get("sign") or {}
    out.append(Fact("sun", "sun:0",
                    {"throw_bearing_units": sign.get("throw_bearing_units"),
                     "axis_degrees": light["axis"].get("axis_degrees"),
                     "decided_by": f"{sign.get('far_end_boundaries')} far-end "
                                   f"boundaries, votes {sign.get('votes')}",
                     "lit_base": light["field"]["lit_base"],
                     "observed_deltas": light["step"]["deltas"]},
                    sources=tuple(f"wall:{row['wall']}"
                                  for row in light["shade_edges"]),
                    reader=light_reader, layer=4))
    for row in light["shade_edges"]:
        out.append(Fact("shade_edge", f"wall:{row['wall']}",
                        {"record": f"wall:{row['wall']}",
                         "between": [f"sector:{row['here']}",
                                     f"sector:{row['there']}"],
                         "delta": abs(row["shade_here"] - row["shade_there"]),
                         "axis_degrees": row["axis"]},
                        sources=(f"wall:{row['wall']}",),
                        reader=light_reader, layer=4))
    field = light["field"]
    for shade, depth in field["shades_that_fit_base_plus_k_step"].items():
        for index in field["levels"][shade]["sectors"]:
            out.append(Fact("shade_depth", f"sector:{index}",
                            {"record": f"sector:{index}", "depth": depth,
                             "shade": shade},
                            sources=(f"sector:{index}", "sun:0"),
                            reader=light_reader, layer=4))
            out.append(_claim(f"sector:{index}", "floor_shade", int(shade),
                              layer=4, owner=f"sun:depth{depth}",
                              why=f"the light field at depth {depth}: "
                                  f"{field['lit_base']} + {depth}*{STEP} = {shade}",
                              sources=(f"sector:{index}", "sun:0")))
    for shade, delta in field["shades_that_fit_no_level"].items():
        for index in field["levels"][shade]["sectors"]:
            out.append(Fact("residue", f"light:sector:{index}",
                            {"about": f"sector:{index}", "aspect": "light",
                             "why": f"floor shade {shade} is {delta} from the "
                                    f"base and fits no base + k*{STEP} level"},
                            sources=(f"sector:{index}",),
                            reader=light_reader, layer=4))
    for record in light["axis"].get("residue_edges_off_the_bearing", ()):
        out.append(Fact("residue", f"light:edge:wall:{record}",
                        {"about": f"wall:{record}", "aspect": "light",
                         "why": "an oblique shade boundary not at the sun's "
                                "bearing: one directional source cannot have "
                                "made it"},
                        sources=(f"wall:{record}",),
                        reader=light_reader, layer=4))
    for index, tiles in light["lamps"]["fullbright_by_sector"].items():
        out.append(Fact("light_source", f"sector:{index}",
                        {"record": f"sector:{index}", "kind": "fullbright sprites",
                         "tiles": tiles},
                        sources=(f"sector:{index}",),
                        reader=light_reader, layer=4))
    #: THE CASTERS ARE A CANDIDATE, NOT A FACT. The corner test is a tie, so
    #: the reading is kept both ways rather than decided inside the reader.
    cast = light.get("casters") or {}
    if cast and cast.get("up_sun_end_is_a_mass_corner") == cast.get(
            "down_sun_end_is_a_mass_corner"):
        out.append(Fact("candidate", "light:casters",
                        {"about": "sun:0",
                         "readings": ["the up-sun corner throws each shadow",
                                      "the down-sun corner does"],
                         "why": f"{cast['up_sun_end_is_a_mass_corner']} of "
                                f"{cast['edges']} oblique edges have a mass "
                                f"corner up-sun and "
                                f"{cast['down_sun_end_is_a_mass_corner']} have "
                                f"one down-sun: a tie"},
                        sources=("sun:0",), reader=light_reader, layer=4))
    return out


# ---------------------------------------------------------------------------
# layer 6: the edge chain
# ---------------------------------------------------------------------------

def layer6(level: Any, edges: dict[str, Any]) -> list[Fact]:
    reader = "bloodmap.read_edges"
    out: list[Fact] = []
    for number, segment in enumerate(edges["segments"]):
        out.append(Fact("edge_segment", f"edge:{number:03d}",
                        {"kind": segment["kind"],
                         "records": [f"wall:{r}" for r in segment["records"]],
                         "length": segment["length"]},
                        sources=_ids(WALL, segment["records"]),
                        reader=reader, layer=6))
    backing = sorted({int(level.walls[int(record)]["fields"]["next_sector"])
                      for record, kind in edges["kinds"].items()
                      if kind == "backing"})
    for index in backing:
        out.append(_claim(f"sector:{index}", "ceiling_z",
                          int(level.sectors[index]["fields"]["ceiling_z"]),
                          layer=6, owner="edge:backing",
                          why="a backing mass has no interior, so its ceiling "
                              "is its floor"))
    for record, kind in edges["kinds"].items():
        if kind != "building_back":
            continue
        out.append(_claim(f"wall:{record}", "over_picnum",
                          int(level.walls[int(record)]["fields"]["over_picnum"]),
                          layer=6, owner="edge:building_back",
                          why="a one-sided wall against the void takes no "
                              "facade run and no masked band"))
    for record in edges["residue_records"]:
        out.append(Fact("residue", f"edge:wall:{record}",
                        {"about": f"wall:{record}", "aspect": "edge",
                         "why": "a boundary record in no edge class"},
                        sources=(f"wall:{record}",), reader=reader, layer=6))
    offmap = edges["offmap"]
    for component in offmap.get("components", ()):
        out.append(Fact("offmap", f"offmap:{component['sectors'][0]}",
                        {"sectors": component["sectors"],
                         "kind": component["kind"],
                         "why": component["reasons"]},
                        sources=_ids(SECTOR, component["sectors"]),
                        reader="bloodmap.reachability.classify_offmap", layer=6))
    return out


# ---------------------------------------------------------------------------
# layer 7: the plan
# ---------------------------------------------------------------------------

def layer7(level: Any, plan: dict[str, Any]) -> list[Fact]:
    reader = "bloodmap.read_plan"
    out: list[Fact] = []
    for run in plan["corridors"]:
        out.append(Fact("corridor", run["corridor_id"],
                        {"sectors": run["sectors"], "role": run["role"],
                         "axis": run["axis"], "ratio": run["ratio"],
                         "carriageway_pu": run["carriageway_pu"],
                         "carriageway_class": run["carriageway_class"]["nearest"],
                         "full_width_pu": run["full_width_pu"],
                         "full_width_class": run["full_width_class"]["nearest"],
                         "length_pu": run["length_pu"]},
                        sources=_ids(SECTOR, run["sectors"]),
                        reader=reader, layer=7))
    for number, edge in enumerate(plan["edges"]):
        out.append(Fact("plan_edge", f"plan_edge:{number:02d}",
                        dict(edge), sources=(edge["corridor"],),
                        reader=reader, layer=7))
    for block in plan["blocks"]:
        out.append(Fact("block", block["block_id"],
                        {"sectors": block["sectors"],
                         "envelope_pu": block["envelope_pu"]},
                        sources=_ids(SECTOR, block["sectors"]),
                        reader=reader, layer=7))
    for row in plan["candidates"]:
        out.append(Fact("candidate", f"plan:{row['about']}",
                        {"about": row["about"], "readings": row["readings"],
                         "why": row["why"]},
                        sources=(row["about"],), reader=reader, layer=7))
    for index in plan["residue_sectors"]:
        out.append(Fact("residue", f"plan:sector:{index}",
                        {"about": f"sector:{index}", "aspect": "plan",
                         "why": "ground on no street, island or area"},
                        sources=(f"sector:{index}",), reader=reader, layer=7))
    return out


# ---------------------------------------------------------------------------
# layer 5: mechanisms as sentences
# ---------------------------------------------------------------------------

def layer5(level: Any, mechanisms: dict[str, Any]) -> list[Fact]:
    reader = "bloodmap.read_mechanisms"
    out: list[Fact] = []
    for row in mechanisms["sentences"]:
        members = mechanisms["realises"].get(row["id"], [])
        out.append(Fact("sentence", row["id"],
                        {"kind": row["kind"], "type": row["type"],
                         "sentence": row["sentence"], "shape": row["shape"],
                         "slots": row["slots"],
                         "against_the_course": row["against_the_course"]},
                        sources=tuple(members), reader=reader, layer=5))
        for record in members:
            out.append(Fact("realises", f"{row['id']}:{record}",
                            {"sentence": row["id"], "record": record},
                            sources=(row["id"], record), reader=reader, layer=5))
    for row in mechanisms["links"]:
        out.append(Fact("link", f"channel:{row['channel']}",
                        {"channel": row["channel"], "from": row["from"],
                         "to": row["to"], "triggers": row["triggers"]},
                        sources=tuple(row["from"]) + tuple(row["to"]),
                        reader="bloodmap.conditional.transmitters", layer=5))
    for row in mechanisms["keys"]:
        out.append(Fact("key", f"key:channel:{row['channel']}",
                        {"channel": row["channel"], "sprites": row["sprites"]},
                        sources=tuple(row["sprites"]),
                        reader="bloodmap.conditional.key_sprites", layer=5))
    for row in mechanisms["stacks"]:
        out.append(Fact("stack", f"stack:{row['link_id']}",
                        {"lower": f"sector:{row['lower']}",
                         "upper": f"sector:{row['upper']}",
                         "sprites": [f"sprite:{s}" for s in row["sprites"]],
                         "offset": row["offset"],
                         "faults": row.get("faults", [])},
                        sources=(f"sector:{row['lower']}",
                                 f"sector:{row['upper']}"),
                        reader="bloodmap.curriculum", layer=5))
    for number, row in enumerate(mechanisms["conditions"]):
        out.append(Fact("condition", f"condition:{number:03d}", dict(row),
                        sources=tuple(f"sector:{s}" for s in row["sectors"]),
                        reader="bloodmap.conditional.conditional_edges",
                        layer=5))
    #: What a sentence determines: the record's own type, and for a z-motion
    #: mechanism the state-anchored quartet its XSECTOR carries.
    for row in mechanisms["sentences"]:
        if row["kind"] == "sector mechanism":
            index = int(row["id"].rsplit(":", 1)[1])
            out.append(_claim(f"sector:{index}", "type", int(row["type"]),
                              layer=5, owner=row["id"],
                              why=f"the sentence is: {row['sentence'][:90]}"))
            for name, value in (row.get("z_pair") or {}).items():
                out.append(_claim(f"xsector:{index}", name, int(value),
                                  layer=5, owner=row["id"],
                                  why="the state-anchored z quartet the "
                                      "sentence states"))
        elif row["kind"] == "breakable wall":
            index = int(row["id"].rsplit(":", 1)[1])
            out.append(_claim(f"wall:{index}", "type", int(row["type"]),
                              layer=5, owner=row["id"],
                              why="kWallGib: the wall breaks"))
    for row in mechanisms["residue"]:
        out.append(Fact("residue", f"mechanism:{row['record']}",
                        {"about": row["record"], "aspect": "mechanism",
                         "why": row["why"]},
                        sources=(row["record"],), reader=reader, layer=5))
    return out


# ---------------------------------------------------------------------------
# layer 8: intent
# ---------------------------------------------------------------------------

def layer8(mechanisms: dict[str, Any], places: dict[str, Any]) -> list[Fact]:
    reader = "bloodmap.read_intent"
    out: list[Fact] = []
    for row in mechanisms["named"]:
        out.append(Fact("selection", f"name:{row['sentence']}",
                        {"about": row["sentence"], "chosen": row["name"],
                         "criterion": mechanisms["rule"],
                         "basis": row["basis"]},
                        sources=(row["sentence"],), reader=reader, layer=8))
    for row in mechanisms["candidates"]:
        out.append(Fact("candidate", f"name:{row['sentence']}",
                        {"about": row["sentence"], "readings": row["readings"],
                         "why": row["why"]},
                        sources=(row["sentence"],), reader=reader, layer=8))
    for row in mechanisms["refused"]:
        out.append(Fact("residue", f"intent:{row['sentence']}",
                        {"about": row["sentence"], "aspect": "intent",
                         "why": row["why"]},
                        sources=(row["sentence"],), reader=reader, layer=8))
    for row in places["named"]:
        out.append(Fact("selection", f"name:{row['space']}",
                        {"about": row["space"], "chosen": row["name"],
                         "criterion": places["rule"], "basis": row["basis"]},
                        sources=tuple(f"sector:{s}" for s in row["sectors"]),
                        reader=reader, layer=8))
    for row in places["candidates"]:
        out.append(Fact("candidate", f"name:{row['space']}",
                        {"about": row["space"], "readings": row["readings"],
                         "why": row["why"], "bases": row["bases"]},
                        sources=tuple(f"sector:{s}" for s in row["sectors"]),
                        reader=reader, layer=8))
    for row in places["refused"]:
        out.append(Fact("residue", f"intent:{row['space']}",
                        {"about": row["space"], "aspect": "intent",
                         "why": row["why"]},
                        sources=(row["space"],), reader=reader, layer=8))
    return out


# ---------------------------------------------------------------------------
# the selection passes: named, with their criteria stated
# ---------------------------------------------------------------------------

def selections(store: Any) -> list[Fact]:
    """Resolve the candidates the readers left, each by a stated criterion.

    Manifold's rule the other way round: a reader may not commit, and a
    selection pass may not be anonymous. Each row here says which candidate it
    is about, what it chose, and the criterion -- including where it chooses
    NOTHING, because "the evidence is a tie" is a result and not a gap.
    """
    out: list[Fact] = []
    for row in store["candidate"]:
        if row.id == "light:casters":
            out.append(Fact("selection", "select:light:casters",
                            {"about": row.id, "chosen": None,
                             "criterion": ("a caster is chosen when the "
                                           "shadow's side edge starts at a "
                                           "mass corner up-sun MORE OFTEN "
                                           "than down-sun"),
                             "basis": row.attrs["why"] + " -- so nothing is "
                                      "chosen and the candidate stands"},
                            sources=(row.id,), reader="selection", layer=4))
        elif row.id.startswith("plan:corridor:"):
            ratio = float(row.attrs.get("ratio") or 0.0)
            out.append(Fact("selection", f"select:{row.id}",
                            {"about": row.id,
                             "chosen": "edge" if ratio >= 2.0 else "junction",
                             "criterion": ("a piece of road is an edge when "
                                           "its long/short ratio is at least "
                                           "read_plan.CORRIDOR_RATIO (2.0), a "
                                           "junction below it"),
                             "basis": f"its ratio is {ratio}"},
                            sources=(row.id,), reader="selection", layer=7))
    return out
