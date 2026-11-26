"""From a level's layout to its map on disk: compile, align, hold to the gates, light, tidy, write, and say what was measured.

The owner, 2026-11-26: "Imagine that tomorrow I ask a fresh agent to build an
entirely different Blood level from scratch ... It should not need to read the
entire history of Gravesend or copy its directory as a starting point."

Everything a level's map goes through after its rooms are declared was, until
that day, statements in the last seven hundred lines of Gravesend's build. Each
pass is a library function; what was missing was their ORDER, which a second
level could only learn by reading the first. This is the order, for a level
that has no passes of its own to put between them:

    wire      the circuit's channels are numbered and written (`wiring.Circuit.apply`)
    compile   the layout becomes sectors, walls and sprites
    level     `on_level(compiled)`: the level's own work on the compiled level
    align     a wall in two bands hangs both from one place; one texture frame a
              run of walls, standing on its floor; a raised solid's top starts at
              its own corner
    disk      `on_disk(disk, compiled)`: the level's own work on the finished records
    gates     the rule registry; every sliding and turning mechanism swept
              through its travel; the map read back against what the layout
              declared; every sprite as the engine draws it; tile uses nobody has
              shown; the wiring read back. Four things REFUSE the map, and then
              nothing is written: a rule of severity error, a mechanism that
              breaks what it drags, a read-back difference, and wiring that
              differs from what the circuit declared. Everything else is
              measured and reported (a warning, a sunk sprite, a tile nobody has
              shown): the level's status lists it, and it is the author's to answer.
    overlays  shadows and patches declared on the layout are cut into the map,
              and may add no warning and break no sweep
    light     `bloodmap.light_stage`, when the level gives a `light` rule: lamps
              laid, shadows and floor bands cut, every shade written; pieces that
              came out alike are made one again; the same two conditions. The
              stage lays lights in ROOFED rooms only: a rule on a place under the
              sky lays nothing, and is named. What the stage lays is not linted
              by the sprite gate before it (a chain lamp's chain runs into the
              ceiling on purpose)
    tidy      walls the passes split and nothing needs are joined
    write     the map, `<name>.tags.json` (which sectors are which kind of
              place), and the manifest: what every pass counted

A level with passes of its own between these (Gravesend has dozens) calls the
same functions itself, in this order: `projects/blood-city/level/build_skeleton.py`.

The result is `Finished`. Its `refused` says why no map was written; a build
script returns `1` on it. Nothing here chooses a tile or a shape: a gate says
what it measured, and the thresholds are the rule registry's and the campaign's.
"""

from __future__ import annotations

import collections
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

ART_DIR = "reference/blood"


@dataclass
class Finished:
    """What a build made: the map's records, the compiled layout they came from, and everything measured on the way."""

    disk: Any
    compiled: Any
    manifest: dict[str, Any]
    refused: list[str] = field(default_factory=list)
    stages: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.refused


def _open(diags) -> collections.Counter:
    return collections.Counter((d.severity, d.code) for d in diags if d.severity in ("error", "warning"))


def gates(disk: Any, compiled: Any, layout: Any = None, *, circuit: Any = None, map_name: str = "") -> dict[str, Any]:
    """Hold a finished map to everything that can be read off it. `refused` lists what forbids writing it.

    `rules` is the registry's diagnostics by severity and code, with where each
    error and warning is; `swept` every mechanism through its travel; `readback`
    the map against the layout's own declarations; `sprite_fit` each sprite as
    the renderer draws it; `tile_contexts` what the campaign and the owner's
    maps never show (a discovery to record, or a mistake); `wires` the circuit
    read off the map.
    """
    import bloodmap.rules_blood  # noqa: F401  (the registry is filled by this import)
    from . import sprite_fit, tile_contexts
    from .readback import read_back, sentences_from_layout
    from .rules import evaluate
    from .swept_state import run as sweep

    report: dict[str, Any] = {"refused": []}
    diags = evaluate(disk)
    report["rules"] = {
        "total": len(diags), "by_severity": dict(collections.Counter(d.severity for d in diags)),
        "by_code": {f"{a}:{b}": c for (a, b), c in collections.Counter((d.severity, d.code) for d in diags).items()},
        "open": [{"severity": d.severity, "code": d.code, "at": d.location, "says": d.message}
                 for d in diags if d.severity in ("error", "warning")]}
    report["refused"] += [f"rule {d.code} at {d.location}: {d.message}" for d in diags if d.severity == "error"]
    swept = sweep(disk)
    report["swept"] = {k: swept[k] for k in ("mechanisms", "sound", "deforming_neighbours", "problems", "notes")}
    report["refused"] += [f"a mechanism breaks geometry it drags: {line}" for line in swept["problems"]]
    checked = read_back(disk, sentences_from_layout(compiled, layout=layout or compiled.layout), map_name=map_name)
    report["readback"] = checked.to_dict()
    if not checked.agrees:
        report["refused"] += [f"read-back: {difference}" for difference in checked.differences]
    lint = sprite_fit.lint(disk)
    report["sprite_fit"] = {
        "rates": lint["rates"],
        **{kind: [{k: row[k] for k in ("sprite", "tile", "sector") if k in row} for row in lint[kind]]
           for kind in ("sunk", "through", "squeezed", "lifted")},
        "overlaps": [{"sprites": [o["a"], o["b"]], "tiles": list(o["tiles"]), "sector": o["sector"]} for o in lint["overlaps"]],
        "flat_overlaps": [{"sprites": [o["a"], o["b"]], "tiles": list(o["tiles"]), "sector": o["sector"]}
                          for o in lint["flat_overlaps"]],
        "unbacked": lint["unbacked"], "sunk_actors": lint["sunk_actors"], "on_travelling_floor": lint["on_travelling_floor"]}
    novel = tile_contexts.novel(disk)
    report["tile_contexts"] = {
        "new": [{k: r[k] for k in ("tile", "slot", "place", "count", "first")} for r in novel if r["evidence"] is None],
        "outside": [{"tile": r["tile"], "slot": r["slot"], "place": r["place"], "count": r["count"],
                     "source": r["evidence"]["source"]} for r in novel if r["evidence"] is not None],
        "misfit": [{"tile": r["tile"], "slot": r["slot"], "place": r["place"], "count": r["count"], "said": r["misfit"]}
                   for r in novel if r.get("misfit")]}
    if circuit is not None:
        report["wires"] = circuit.read_back(compiled, disk)
        if not report["wires"].get("agrees", True):
            report["refused"] += [f"wire {row['name']}: {fault}" for row in report["wires"].get("wires", [])
                                  for fault in row.get("faults", [])] or ["the map's wiring differs from what the circuit declared"]
    report["_diags"] = diags
    return report


def _regate(disk: Any, before, what: str) -> list[str]:
    """A pass that cuts the finished map may add no warning or error and break no mechanism's sweep."""
    from .rules import evaluate
    from .swept_state import run as sweep

    added = _open(evaluate(disk)) - before
    broke = sweep(disk)["problems"]
    return ([f"{what} added {dict(added)}"] if added else []) + [f"{what} broke {line}" for line in broke]


def finish(layout: Any, out: str | Path | None = None, *, circuit: Any = None,
           on_level: Callable[[Any], Any] | None = None, on_disk: Callable[[Any, Any], Any] | None = None,
           light: Callable[[str], Any] | None = None, light_options: dict[str, Any] | None = None,
           world_phase: Callable[[str], bool] | None = None, manifest: dict[str, Any] | None = None,
           art_dir: str = ART_DIR, say: Callable[[str], None] = print) -> Finished:
    """Take a declared layout to a map on disk, in the order the module's docstring gives.

    `out` is the MAP to write (nothing is written without it, or when a gate
    refuses). `circuit` is the level's `wiring.Circuit`. `light` is the rule for
    a region's kind of light (`light_stage.Rule`); without it the map keeps the
    shades its layout gave it. `world_phase` names the regions whose walls take
    their texture origin from the world, so that a street's fronts share one
    grid. `manifest` is the level's own counts, kept beside the passes'.
    """
    from . import overlays, tidy
    from .format import write_map
    from .rules import evaluate
    from .surface import RecordOwner
    from .texture_align import wall_art_sizes
    from .texture_frame import frame_map, frame_raised_solids, peg_split_bands

    manifest = dict(manifest or {})
    stages: list[dict[str, Any]] = []
    since = [time.perf_counter()]

    def stage(name: str, says: str) -> None:
        now = time.perf_counter()
        if stages:
            stages[-1]["seconds"] = round(now - since[0], 2)
        stages.append({"name": name, "says": says})
        since[0] = now

    def done(disk, compiled, refused=()) -> Finished:
        stage("end", "")
        stages.pop()
        manifest["stages"] = [{"name": row["name"], "says": row["says"]} for row in stages]
        for line in refused:
            say(f"REFUSED: {line}")
        return Finished(disk, compiled, manifest, list(refused), stages)

    stage("compile", "the layout becomes sectors, walls and sprites")
    layout.lit_when_finished = light is not None
    if circuit is not None:
        if circuit.layout is None:
            circuit.bind(layout)
        # a table of planned wires may name more than is built yet; a wire declared by hand with no end is a mistake,
        # and `apply` says so
        idle = circuit.drop_idle() if getattr(circuit, "planned", False) else []
        manifest["wires"] = {"declared": circuit.apply(), "idle": idle}
    compiled = layout.compile()
    manifest["lighting"] = dict(compiled.lighting_report)
    if on_level is not None:
        stage("level", "the level's own passes on the compiled level")
        manifest["level"] = on_level(compiled)

    stage("alignment", "one texture frame per run of walls, standing on its floor")
    art_sizes = wall_art_sizes(art_dir)
    records = RecordOwner()
    fronts = {int(w) for region, allocation in compiled.allocations.items() if world_phase and world_phase(region)
              for w in allocation.wall_ids}
    bands = peg_split_bands(compiled.level, records=records, owner="surface")
    manifest["split_bands"] = {k: v for k, v in bands.items() if k != "walls"}
    manifest["texture_frames"] = frame_map(compiled.level, art_sizes=art_sizes, world_phase=fronts, records=records,
                                           owner="surface", v_anchor="floor")
    manifest["raised_solids"] = frame_raised_solids(compiled.level, art_sizes=art_sizes)

    disk = compiled.level.to_disk_map()
    if on_disk is not None:
        stage("disk", "the level's own passes on the finished records")
        manifest["disk"] = on_disk(disk, compiled)

    stage("gates", "nothing is built: rules, swept closure, read-back, sprite fit, tile contexts, wiring")
    held = gates(disk, compiled, layout, circuit=circuit, map_name=Path(out).name if out else "")
    diags = held.pop("_diags")
    refused = held.pop("refused")
    if "wires" in held:
        manifest.setdefault("wires", {}).update(held.pop("wires"))
    manifest.update(held)
    say(f"rules: {manifest['rules']['total']} diagnostics {manifest['rules']['by_severity']}; "
        f"swept: {manifest['swept']['mechanisms']} mechanisms; read-back "
        f"{'agrees' if not any(r.startswith('read-back') for r in refused) else 'DIFFERS'}; "
        f"sprite fit {manifest['sprite_fit']['rates']}; tile uses nobody has shown: {len(manifest['tile_contexts']['new'])}")
    if refused:
        return done(disk, compiled, refused)

    parent: dict[int, int] = {}
    if layout.overlays:
        stage("overlays", "shadows and patches declared on the layout, cut into the finished map")
        laid = overlays.lay(disk, compiled)
        parent = {int(k): int(v) for k, v in laid.get("parent", {}).items()}
        manifest["overlays"] = {k: v for k, v in laid.items() if k != "parent"}
        refused = _regate(disk, _open(diags), "the overlays")
        if refused:
            return done(disk, compiled, refused)

    region_of = {allocation.sector_id: region for region, allocation in sorted(compiled.allocations.items())}
    for piece, source in sorted(parent.items()):
        region_of[piece] = region_of.get(source, "")
    if light is not None:
        stage("light", "lamps laid, shadows and floor bands cut, every shade written")
        from . import light_stage

        before = _open(evaluate(disk))
        lit = light_stage.run(disk, region_of, light, **(light_options or {}))
        # a rule that names lights and laid none: under the sky the stage lays nothing (a lamp post is set by hand)
        asked = {region for region in set(region_of.values()) if region and light(region).form != "none"}
        unlit = sorted(asked - set(lit.get("rooms", {})))
        if unlit:
            say("light rules that laid no light (a sector open to the sky, or too low or small to be a room): " + ", ".join(unlit))
        lit_parent = {int(k): parent.get(int(v), int(v)) for k, v in lit["parent"].items()}
        merged = tidy.merge_alike(disk, int(lit["sectors_before"]))
        into = merged.pop("into")
        lit_parent = {into[k]: v for k, v in lit_parent.items() if into[k] >= int(lit["sectors_before"])}
        parent.update(lit_parent)
        manifest["light_stage"] = {**{k: v for k, v in lit.items() if k != "parent"}, "sectors": len(disk.sectors),
                                   "walls": len(disk.walls), "pieces": len(lit_parent), "rules_that_laid_nothing": unlit}
        manifest["merged"] = merged
        refused = _regate(disk, before, "the light stage")
        if refused:
            return done(disk, compiled, refused)

    stage("write", "the map, its sector tags and the manifest")
    manifest["tidy"] = tidy.unsplit(disk, art_sizes)
    tags: dict[str, list[int]] = {}
    for region_id, region in layout.regions.items():
        kind = (getattr(region, "intent", None) or {}).get("kind")
        allocation = compiled.allocations.get(region_id)
        if kind and allocation is not None:
            tags.setdefault(str(kind), []).append(allocation.sector_id)
    for piece, source in sorted(parent.items()):
        for sectors in tags.values():
            if source in sectors:
                sectors.append(piece)
    manifest["size"] = {"sectors": len(disk.sectors), "walls": len(disk.walls), "sprites": len(disk.sprites)}
    if out is not None:
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        write_map(disk, out)
        out.with_suffix(".tags.json").write_text(json.dumps({k: sorted(v) for k, v in sorted(tags.items())}, indent=1),
                                                 encoding="utf-8")
    say(f"sectors {len(disk.sectors)} walls {len(disk.walls)} sprites {len(disk.sprites)}" + (f" -> {out}" if out else ""))
    return done(disk, compiled)


def write_manifest(finished: Finished, path: str | Path) -> None:
    """Keep what the build measured beside the map: the same build writes the same file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(finished.manifest, indent=2, default=str) + "\n", encoding="utf-8", newline="\n")
