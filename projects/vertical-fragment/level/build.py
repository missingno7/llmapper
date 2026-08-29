"""Build the fragment, judge it, and write down what it is.

.. code-block:: bash

    python projects/vertical-fragment/level/build.py

Nothing here is optional. `bloodmap.rules.evaluate` runs in this path and its
errors fail the build, which is the whole point of a graded registry: the
severity of every rule comes from how often Blood itself breaks it, so a rule
that fires here is one the campaign essentially never breaks.
"""

from __future__ import annotations

import collections
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from bloodmap import aperture, layers, rules, rules_blood  # noqa: F401
from bloodmap.format import encode_map
from bloodmap.reachability import analyze_reachability, portal_graph

import fragment

REPORTS = HERE.parent / "reports"
MAP_PATH = HERE / "MALTX.MAP"


def circulation(disk) -> dict:
    """Is every sector reachable from every other, through portals alone?

    The gantry is not a portal, so what this measures is the level *minus* its
    sprite deck. A fragment whose only route to somewhere is the deck would show
    up here as a second component, which is worth knowing rather than hiding.
    """
    graph = portal_graph(disk)
    seen, stack = {0}, [0]
    while stack:
        current = stack.pop()
        for other in graph.get(current, ()):
            if other not in seen:
                seen.add(other)
                stack.append(other)
    return {"sectors": len(disk.sectors), "one_component": len(seen),
            "unreached": sorted(set(range(len(disk.sectors))) - seen)}


def main() -> int:
    program = fragment.build()
    layout = program.compile()

    layer_report = layers.report(layout)
    fatal = [f for f in layer_report["findings"] if f["severity"] == "error"]
    if fatal:
        for finding in fatal:
            print("LAYER ERROR", finding["code"], finding["location"])
        return 1

    compiled = layout.compile()
    disk = compiled.level.to_disk_map()
    data = encode_map(disk)

    # Determinism, checked rather than assumed: the same source twice must give
    # the same bytes, or nothing downstream can be compared against anything.
    again = encode_map(fragment.build().compile().compile().level.to_disk_map())
    if again != data:
        print("BUILD IS NOT DETERMINISTIC")
        return 1

    graded = rules.load_grades()
    diagnostics = rules.evaluate(disk, grades=graded)
    by_severity: dict[str, list] = {}
    for item in diagnostics:
        by_severity.setdefault(item.severity, []).append(item)

    openings = aperture.audit(disk)

    REPORTS.mkdir(parents=True, exist_ok=True)
    MAP_PATH.write_bytes(data)

    (REPORTS / "layers.json").write_text(
        json.dumps(layer_report, indent=1) + "\n", encoding="utf-8")
    (REPORTS / "tree.json").write_text(
        json.dumps(program.outline_document(), indent=1) + "\n", encoding="utf-8")

    reach = analyze_reachability(disk)
    manifest = {
        "$schema": "llmapper.vertical-fragment-build",
        "map": MAP_PATH.name,
        "bytes": len(data),
        "sectors": len(disk.sectors),
        "walls": len(disk.walls),
        "sprites": len(disk.sprites),
        "tree": {
            "nodes": 1 + len(list(_walk(program))),
            "max_depth": max(len(node.ancestors()) for node in _walk(program)),
            "rooms": len(program.rooms()),
        },
        "layers": layer_report["layers"],
        "overlaps": len(layer_report["overlaps"]),
        "layer_findings": layer_report["findings"],
        "techniques": _techniques(disk, layer_report),
        "circulation": circulation(disk),
        "offmap_fraction": round(reach.offmap_fraction, 4),
        "rules": {
            "graded": len(graded),
            "registered": len(rules.RULES),
            "errors": [_say(item) for item in by_severity.get("error", ())],
            "warnings": [_say(item) for item in by_severity.get("warning", ())],
            "notes": len(by_severity.get("note", ())),
        },
        "apertures": {
            "checked": len(openings),
            "violations": [item for item in openings if item.get("severity") == "error"],
        },
    }
    (REPORTS / "build-manifest.json").write_text(
        json.dumps(manifest, indent=1) + "\n", encoding="utf-8")

    print("wrote {} -- {} sectors, {} walls, {} sprites, {} bytes".format(
        MAP_PATH.name, len(disk.sectors), len(disk.walls), len(disk.sprites), len(data)))
    print("tree: {} nodes, depth {}, {} rooms".format(
        manifest["tree"]["nodes"], manifest["tree"]["max_depth"],
        manifest["tree"]["rooms"]))
    print("layers: {} bands, {} overlaps, {} findings".format(
        len(layer_report["layers"]), len(layer_report["overlaps"]),
        len(layer_report["findings"])))
    print("techniques: " + ", ".join(
        "{}={}".format(k, v) for k, v in manifest["techniques"].items()))
    print("circulation: {} of {} sectors in one portal component".format(
        manifest["circulation"]["one_component"], manifest["circulation"]["sectors"]))
    print("rules: {} of {} graded; {} error(s), {} warning(s), {} note(s)".format(
        manifest["rules"]["graded"], manifest["rules"]["registered"],
        len(manifest["rules"]["errors"]), len(manifest["rules"]["warnings"]),
        manifest["rules"]["notes"]))
    for line in manifest["rules"]["errors"]:
        print("   ERROR", line)
    for line in manifest["rules"]["warnings"][:10]:
        print("   warn ", line)

    if manifest["rules"]["errors"]:
        print("\nrefusing the build: a rule the campaign essentially never breaks")
        return 1
    if manifest["circulation"]["unreached"]:
        print("\nrefusing the build: sectors nothing can walk to")
        return 1
    return 0


def _walk(node):
    for child in getattr(node, "children", ()):
        yield child
        yield from _walk(child)


def _say(item) -> str:
    return "{}: {} [{}]".format(item.code, item.message[:110], item.location)


def _techniques(disk, layer_report: dict) -> dict[str, int]:
    """One count per way of getting space over space, so none can quietly vanish."""
    kinds = collections.Counter(o["declared"] for o in layer_report["overlaps"])
    stacks = kinds.get("stack", 0) + kinds.get("water", 0) + kinds.get("link", 0)
    helix = kinds.get("helix", 0) + kinds.get("tower_door", 0)
    plan = kinds.get(None, 0)
    deck = sum(1 for sprite in disk.sprites
               if (int(sprite.fields["cstat"]) & 48) == 32
               and int(sprite.fields["cstat"]) & 1)
    return {"plan_overlap": plan, "room_over_room": stacks,
            "spiral_turns": helix, "blocking_floor_sprite": deck}


if __name__ == "__main__":
    raise SystemExit(main())
