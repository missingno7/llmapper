"""One map, every view, and the places they disagree.

The handbook's first premise is that a level does not have one correct
representation: the same space is a geometric corridor, a topological edge, a
service passage, a chokepoint, a required route and a dark visual transition
at once, and the system should *preserve* the overlapping views rather than
average them.

So this module does not merge. It collects what each phase's reading says
about one map, records the relations between views explicitly, and then --
the part that matters -- lists where they **contradict each other**. The
contradictions are the deliverable's proof that the views are independent. A
bundle whose views all agree has either been reconciled by hand or is only
running one view twice.

No view here is canonical. Every section names the module that produced it
and what that module assumes.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

SCHEMA = "llmapper.multi-view-bundle"
SCHEMA_VERSION = 1

#: Views the bundle knows how to gather. A bundle records which ones it got
#: and which the map does not exercise, rather than quietly omitting them.
VIEWS = (
    "geometry", "assemblies", "functional_regions", "facades",
    "effects", "conditional_topology", "progression", "visual",
)


class BundleError(ValueError):
    pass


def _sector_kind_counts(disk: Any) -> dict[str, int]:
    from .reachability import sector_kinds

    return dict(Counter(sector_kinds(disk).values()))


def geometry_view(disk: Any, spatial: dict[str, Any]) -> dict[str, Any]:
    """What is built, and how much of it a player is meant to enter."""
    view = spatial["views"]["geometry"]
    return {
        "produced_by": "bloodmap.spatial.analyze_spatial, views.geometry",
        "assumes": "wall ownership and sector loops as the MAP records them",
        "sectors": len(disk.sectors),
        "walls": len(disk.walls),
        "sprites": len(disk.sprites),
        "sector_kinds": _sector_kind_counts(disk),
        "bounds": view.get("bounds"),
        "portals": len(spatial["views"]["traversability"]["walkable_at_rest"])
                   + len(spatial["views"]["traversability"]["blocked_or_state_dependent"]),
    }


def assemblies_view(disk: Any, sectors: list[int], *,
                    map_name: str = "") -> dict[str, Any]:
    """Phase 5: what is bound to each mechanism, and in what numbers."""
    from .assembly import assembly_around

    shapes: Counter = Counter()
    records = []
    for sector_id in sectors:
        assembly = assembly_around(disk, sector_id, map_name=map_name)
        shape = assembly.shape()
        shapes[shape] += 1
        records.append({
            "sector": sector_id,
            "root_type": assembly.root_type,
            "shape": [list(item) for item in shape],
            "members": len(assembly.members),
            "roles": dict(Counter(member.role for member in assembly.members)),
        })
    return {
        "produced_by": "bloodmap.assembly.assembly_around",
        "assumes": "an assembly is what a sector contains, references by "
                   "marker, and is wired to by channel",
        "assemblies": len(records),
        "distinct_shapes": len(shapes),
        "commonest_shapes": [{"shape": [list(i) for i in shape], "count": n}
                             for shape, n in shapes.most_common(6)],
        "records": records,
    }


def functional_regions_view(disk: Any, spatial: dict[str, Any]) -> dict[str, Any]:
    """Phase 6: the shapes a space makes, independent of what drives it."""
    from .structures import detect_structures

    document = detect_structures(disk.to_level_ir(), spatial=spatial)
    candidates = document["structures"]
    return {
        "produced_by": "bloodmap.structures.detect_structures",
        "assumes": "structure is recovered from floor heights and portal "
                   "adjacency; nothing about triggers or channels",
        "candidates": len(candidates),
        "by_kind": dict(Counter(item.get("kind") for item in candidates)),
        "coverage": document["coverage"],
        "limitations": document["limitations"],
        "records": candidates,
    }


def facades_view(disk: Any) -> dict[str, Any]:
    """Phase 7: street frontage, where the map has any."""
    from .anchors import find_facades

    facades = find_facades(disk.to_build_ir())
    rhythms: Counter = Counter(item.rhythm for item in facades)
    return {
        "produced_by": "bloodmap.anchors.find_facades",
        "assumes": "a facade is a maximal collinear run of one sky-lit "
                   "sector's wall loop, at least two 1024 bays long",
        "facades": len(facades),
        "by_rhythm": dict(rhythms),
        "hosts": sorted({item.host for item in facades}),
        "records": [
            {"host": item.host, "walls": list(item.walls),
             "solid": list(item.solid), "rhythm": item.rhythm,
             "openings": len(item.openings), "bays": item.bays,
             "run_length_units": item.measures.get("run_length_units"),
             "dominant_tile": item.measures.get("dominant_tile")}
            for item in facades],
    }


def effects_view(disk: Any, *, map_name: str = "") -> dict[str, Any]:
    """Phase 8: what each mechanism physically does, named from its space."""
    from .effects import read_map_mechanisms

    report = read_map_mechanisms(disk, map_name=map_name)
    return {
        "produced_by": "bloodmap.effects.read_map_mechanisms",
        "assumes": "the name comes from the embedding, never the fields; "
                   "rotate and slide are returned undecided",
        "mechanisms": report["count"],
        "by_design_object": dict(Counter(
            item["design_object"] for item in report["mechanisms"])),
        "records": report["mechanisms"],
    }


def conditional_view(disk: Any, base: str) -> dict[str, Any]:
    """Part A: which ways are gated, and the chain that opens them."""
    from .conditional import BASES, build_graph, route_edges

    graph = build_graph(disk, base=base)
    routes = route_edges(graph.edges)
    return {
        "produced_by": f"bloodmap.conditional.build_graph(base={base!r})",
        "assumes": BASES[base],
        "summary": dict(graph.summary),
        "routes": len(routes),
        "by_trigger": dict(Counter(
            cause["trigger"] for route in routes for cause in route["causes"])),
        "keyed": [route for route in routes if route["requires_key"]],
        "irreversible": [route for route in routes if route["irreversible"]],
        "records": routes,
        "_graph": graph,
    }


def progression_view(disk: Any, graph: Any) -> dict[str, Any]:
    """What opens what, in order, and what the other reading says."""
    from .conditional import frontier
    from .progression import analyze_progression, compact_progression_report

    walk = frontier(disk, graph=graph)
    other = compact_progression_report(analyze_progression(disk))
    return {
        "produced_by": "bloodmap.conditional.frontier",
        "assumes": "rounds are ordered; the actions inside a round are not, "
                   "so this is not a play order",
        "start_sector": walk["start_sector"],
        "at_rest_reachable": walk["at_rest_reachable"],
        "finally_reachable": walk["finally_reachable"],
        "gated_by_action": walk["gated_by_action"],
        "rounds": walk["rounds"],
        "sp_understand": {
            "produced_by": "bloodmap.progression.analyze_progression",
            "assumes": "spatial.walkable_at_rest plus channel-opened extras; "
                       "known_non_portal_transitions are not read",
            "at_rest_reachable": other["physical_reachable_at_rest"],
            "final_reachable": other["final_reachable"],
            "exit_reachable": other["exit_reachable"],
            "steps": len(other["steps"]),
        },
    }


def disagreements(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    """Where the views contradict each other.

    Not a defect list. Two readings of the same map built on different
    evidence *should* disagree, and a bundle that hides it is claiming a
    consensus it has not got. Each entry names both sides and what each was
    looking at, and none of them is resolved here.
    """
    found: list[dict[str, Any]] = []
    views = bundle["views"]

    progression = views.get("progression")
    if progression:
        mine = progression["finally_reachable"]
        theirs = progression["sp_understand"]["final_reachable"]
        if mine != theirs:
            found.append({
                "between": ["conditional_topology", "sp_understand"],
                "about": "how much of the map a body can end up reaching",
                "conditional_topology": mine,
                "sp_understand": theirs,
                "difference": abs(mine - theirs),
                "why_they_can_differ":
                    "different base graphs. The conditional view gates on the "
                    "wall blocking cstat and reopens what a mechanism drives; "
                    "analyze_progression floods spatial.walkable_at_rest, "
                    "which also refuses portals under 512 wide or 4096 of "
                    "opening, and never reads known_non_portal_transitions, "
                    "so stack links and teleports are invisible to it.",
            })

    effects, conditional = views.get("effects"), views.get("conditional_topology")
    if effects and conditional:
        undecided = effects["by_design_object"].get("not decidable from z alone", 0)
        scoped = conditional["summary"].get("scoped_out_rotate_slide", 0)
        if undecided or scoped:
            found.append({
                "between": ["effects", "conditional_topology"],
                "about": "mechanisms neither view will name",
                "effects_undecided": undecided,
                "conditional_scoped_out": scoped,
                "why_they_can_differ":
                    "both refuse the rotate and slide families for the same "
                    "reason -- their spatial questions are about a vertical "
                    "opening -- but they count different things: effects "
                    "counts mechanisms it declines to name, the conditional "
                    "view counts mechanisms whose crossings it leaves in the "
                    "base ungated. Neither number is a claim that those "
                    "mechanisms do nothing.",
            })

    facades, functional = views.get("facades"), views.get("functional_regions")
    if facades and functional:
        hosts = set(facades["hosts"])
        structural = set()
        for item in functional["records"]:
            for value in item.get("sectors", []):
                if isinstance(value, int):
                    structural.add(value)
                elif isinstance(value, str) and value.startswith("sector:"):
                    structural.add(int(value.split(":")[1]))
        overlap = sorted(hosts & structural)
        if overlap:
            found.append({
                "between": ["facades", "functional_regions"],
                "about": "sectors both a street frontage and a structural shape",
                "sectors": overlap[:24],
                "count": len(overlap),
                "why_they_can_differ":
                    "a facade is read from a sky-lit sector's wall loop and a "
                    "structure from floor heights and adjacency. One sector "
                    "being both is the two views cutting the same space "
                    "differently, which is the point of keeping both.",
            })

    geometry = views.get("geometry")
    if geometry and progression:
        design = geometry["sector_kinds"].get("reachable", 0)
        reached = progression["finally_reachable"]
        if reached < design:
            found.append({
                "between": ["geometry", "conditional_topology"],
                "about": "sectors the geometry calls player space that the "
                         "traversal never reaches",
                "sectors_of_kind_reachable": design,
                "finally_reachable": reached,
                "difference": design - reached,
                "why_they_can_differ":
                    "sector_kinds asks whether a sector looks like player "
                    "space; the conditional frontier asks whether a body can "
                    "get there through gates it can open. A sector reachable "
                    "only by riding a rotor, or over a blocked wall no "
                    "mechanism drives, is player space this traversal cannot "
                    "enter.",
            })

    visual = views.get("visual")
    if visual and visual.get("refused"):
        found.append({
            "between": ["visual", "conditional_topology"],
            "about": "places the renderer will not stand where another view "
                     "makes a claim",
            "refused": visual["refused"],
            "why_they_can_differ":
                "the observer places a viewpoint only where a body has "
                "standing clearance at rest. A sector the conditional view "
                "calls a way through, shut until something opens it, has "
                "nowhere to stand until then -- so a refusal here agrees "
                "with the gate rather than contradicting it.",
        })
    return found


def build_bundle(disk: Any, *, map_name: str, base: str = "blocking_aware",
                 visual: dict[str, Any] | None = None,
                 abridge: int = 400) -> dict[str, Any]:
    """Gather every view of one map, and say where they disagree."""
    from .spatial import analyze_spatial

    spatial = analyze_spatial(disk.to_build_ir())
    effects = effects_view(disk, map_name=map_name)
    mechanism_sectors = [item["sector_id"] for item in effects["records"]]
    conditional = conditional_view(disk, base)
    graph = conditional.pop("_graph")

    views: dict[str, Any] = {
        "geometry": geometry_view(disk, spatial),
        "assemblies": assemblies_view(disk, mechanism_sectors, map_name=map_name),
        "functional_regions": functional_regions_view(disk, spatial),
        "facades": facades_view(disk),
        "effects": effects,
        "conditional_topology": conditional,
        "progression": progression_view(disk, graph),
    }
    if visual is not None:
        views["visual"] = visual

    bundle = {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "map": map_name,
        "contract": [
            "No view is canonical. Each names the module that produced it "
            "and what that module assumes.",
            "Cross-view relations are explicit rather than merged.",
            "Disagreements between views are listed and left standing. They "
            "are the evidence that the views are independent readings.",
        ],
        "views_gathered": sorted(views),
        "views_missing": sorted(set(VIEWS) - set(views)),
        "views": views,
    }
    bundle["disagreements"] = disagreements(bundle)
    bundle["abridged"] = _abridge(bundle, abridge)
    return bundle


def _abridge(bundle: dict[str, Any], limit: int) -> dict[str, Any]:
    """Trim the long record lists, and say exactly what was trimmed."""
    trimmed: dict[str, Any] = {}
    for name, view in bundle["views"].items():
        records = view.get("records")
        if isinstance(records, list) and len(records) > limit:
            trimmed[name] = {"kept": limit, "of": len(records)}
            view["records"] = records[:limit]
            view["records_note"] = (
                f"abridged: first {limit} of {trimmed[name]['of']}; the "
                f"counts above are over all of them")
    return {"limit": limit, "trimmed": trimmed} if trimmed else {"limit": limit}
