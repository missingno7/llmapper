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

`finish` runs them for a level whose own work fits the two hooks it offers
(`on_level`, `on_disk`). A level with passes of its own between the stages
drives the same session itself: `Finish` holds the layout, the compiled level,
the records each pass has claimed (`records`), the map, the manifest and what
was cut from what (`parent`), and each stage is one of its methods, called in
the order above with the level's passes between them. That is the whole of the
contract, and the reason a level never copies a stage: what a stage does, and
what refuses the map, lives here once. What a level puts between them (its
facades, its glass, its sounds, its own measurements and reports) is its own.
Gravesend is built that way (`projects/blood-city/level/build_skeleton.py`).

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
    the renderer draws it; `floors_across` a floor whose tile runs one way laid
    across a long sector; `tile_contexts` what the campaign and the owner's
    maps never show (a discovery to record, or a mistake); `wires` the circuit
    read off the map.
    """
    import bloodmap.rules_blood  # noqa: F401  (the registry is filled by this import)
    from . import sprite_fit, tile_contexts
    from .tile_looks import directional_floor_faults
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
    # a floor whose tile has a direction, laid across a long sector (the owner: rails "90 degrees from train")
    report["floors_across"] = directional_floor_faults(disk)
    novel = tile_contexts.novel(disk)
    report["tile_contexts"] = {
        "new": [{k: r[k] for k in ("tile", "slot", "place", "count", "first")} for r in novel if r["evidence"] is None],
        "outside": [{"tile": r["tile"], "slot": r["slot"], "place": r["place"], "count": r["count"],
                     "source": r["evidence"]["source"], "maps": r["evidence"].get("maps")}
                    for r in novel if r["evidence"] is not None],
        "misfit": [{"tile": r["tile"], "slot": r["slot"], "place": r["place"], "count": r["count"], "first": r["first"],
                    "said": r["misfit"]} for r in novel if r.get("misfit")]}
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


class Finish:
    """One level's map on its way to disk: each shared stage a method, called in the module's order.

    A method that can refuse the map returns whether it may go on; once one has
    refused, `refused` says why and `finished()` is the result. A stage called
    out of that order, or after a refusal, raises `FinishError`: `align` before
    `to_disk`, and nothing is cut, lit, tidied or written before `hold`. The level calls
    `stage(name, says)` to mark its own stages if it keeps no timer of its own.
    """

    def __init__(self, layout: Any, *, circuit: Any = None, manifest: dict[str, Any] | None = None,
                 art_dir: str = ART_DIR, say: Callable[[str], None] = print):
        from .surface import RecordOwner

        self.layout, self.circuit, self.art_dir, self.say = layout, circuit, art_dir, say
        self.manifest: dict[str, Any] = dict(manifest or {})
        #: who has claimed each wall record's texture fields: a level's own passes (shop glass, an insert) claim here
        #: before `align`, so the frames do not re-derive what they own
        self.records = RecordOwner()
        self.compiled: Any = None
        self.disk: Any = None
        self.refused: list[str] = []
        #: a sector the overlays or the light cut out of another -> the sector it was cut from (before the cuts)
        self.parent: dict[int, int] = {}
        self.stages: list[dict[str, Any]] = []
        self._since = time.perf_counter()
        self._wired = False
        self._held = False
        self._art_sizes: dict[int, tuple[int, int]] | None = None
        self._diags: Any = None

    @property
    def ok(self) -> bool:
        return not self.refused

    @property
    def art_sizes(self) -> dict[int, tuple[int, int]]:
        if self._art_sizes is None:
            from .texture_align import wall_art_sizes

            self._art_sizes = wall_art_sizes(self.art_dir)
        return self._art_sizes

    @property
    def diags(self) -> Any:
        """The rule registry's diagnostics of the map as `hold` saw it."""
        return self._diags

    def stage(self, name: str, says: str) -> None:
        now = time.perf_counter()
        if self.stages:
            self.stages[-1]["seconds"] = round(now - self._since, 2)
        self.stages.append({"name": name, "says": says})
        self._since = now

    def _refuse(self, lines: list[str]) -> bool:
        for line in lines:
            self.say(f"REFUSED: {line}")
        self.refused += lines
        return not self.refused

    def _need(self, stage: str, *, compiled: bool = False, disk: bool = False, no_disk: bool = False,
              held: bool = False) -> None:
        """A stage called out of the module's order, or after the map was refused, is a mistake and says so."""
        if self.refused:
            raise FinishError(f"{stage}: the map was refused ({self.refused[0]}); nothing more is done to it")
        if compiled and self.compiled is None:
            raise FinishError(f"{stage} comes after compile")
        if disk and self.disk is None:
            raise FinishError(f"{stage} comes after to_disk")
        if no_disk and self.disk is not None:
            raise FinishError(f"{stage} works on the compiled level, so it comes before to_disk; after it, nothing it "
                              "did would reach the map")
        if held and not self._held:
            raise FinishError(f"{stage} comes after hold: a map that has not been held to the gates is not cut, lit or "
                              "written")

    def wire(self) -> None:
        """Number the circuit's channels and write them onto the layout (once; `compile` does it if the level has not)."""
        if self.circuit is None or self._wired:
            return
        self._wired = True
        if self.circuit.layout is None:
            self.circuit.bind(self.layout)
        # a table of planned wires may name more than is built yet; a wire declared by hand with no end is a mistake,
        # and `apply` says so
        idle = self.circuit.drop_idle() if getattr(self.circuit, "planned", False) else []
        self.manifest["wires"] = {"declared": self.circuit.apply(), "idle": idle}

    def compile(self, *, lit: bool) -> Any:
        """The layout becomes sectors, walls and sprites. `lit`: the light stage will write the shades at the end."""
        self.layout.lit_when_finished = lit
        self.wire()
        self.compiled = self.layout.compile()
        self.manifest["lighting"] = dict(self.compiled.lighting_report)
        return self.compiled

    def align(self, *, world_phase: Callable[[str], bool] | None = None) -> None:
        """A wall in two bands hangs both from one place; one texture frame a run of walls, standing on its floor;
        a raised solid's top starts at its own corner. `world_phase` names the regions whose walls take their texture
        origin from the world, so that a street's fronts share one grid."""
        from .texture_frame import frame_map, frame_raised_solids, peg_split_bands

        self._need("align", compiled=True, no_disk=True)
        level = self.compiled.level
        fronts = {int(w) for region, allocation in self.compiled.allocations.items() if world_phase and world_phase(region)
                  for w in allocation.wall_ids}
        bands = peg_split_bands(level, records=self.records, owner="surface")
        self.manifest["split_bands"] = {k: v for k, v in bands.items() if k != "walls"}
        self.manifest["texture_frames"] = frame_map(level, art_sizes=self.art_sizes, world_phase=fronts,
                                                    records=self.records, owner="surface", v_anchor="floor")
        self.manifest["raised_solids"] = frame_raised_solids(level, art_sizes=self.art_sizes)

    def to_disk(self) -> Any:
        """The compiled level's records as a map; the passes after this work on `disk`."""
        self._need("to_disk", compiled=True, no_disk=True)
        self.disk = self.compiled.level.to_disk_map()
        return self.disk

    def hold(self, *, map_name: str = "") -> bool:
        """The gates (`gates`). Four things refuse the map: see the module's docstring."""
        self._need("hold", disk=True)
        self._held = True
        held = gates(self.disk, self.compiled, self.layout, circuit=self.circuit, map_name=map_name)
        self._diags = held.pop("_diags")
        refused = held.pop("refused")
        if "wires" in held:
            self.manifest.setdefault("wires", {}).update(held.pop("wires"))
        self.manifest.update(held)
        self.say(f"rules: {held['rules']['total']} diagnostics {held['rules']['by_severity']}; "
                 f"swept: {held['swept']['mechanisms']} mechanisms; read-back "
                 f"{'agrees' if not any(r.startswith('read-back') for r in refused) else 'DIFFERS'}; "
                 f"sprite fit {held['sprite_fit']['rates']}; tile uses nobody has shown: {len(held['tile_contexts']['new'])}")
        return self._refuse(refused)

    def cut_overlays(self) -> bool:
        """Shadows and patches declared on the layout, cut into the finished map: they may add no warning and break no
        sweep. Nothing to do for a layout that declares none."""
        self._need("cut_overlays", held=True)
        if not self.layout.overlays:
            return True
        from . import overlays

        laid = overlays.lay(self.disk, self.compiled)
        self.parent.update({int(k): int(v) for k, v in laid.get("parent", {}).items()})
        self.manifest["overlays"] = {k: v for k, v in laid.items() if k != "parent"}
        return self._refuse(_regate(self.disk, _open(self._diags), "the overlays"))

    def region_of(self) -> dict[int, str]:
        """Which region each sector of the map belongs to, a piece cut from a sector with it."""
        out = {allocation.sector_id: region for region, allocation in sorted(self.compiled.allocations.items())}
        for piece, source in sorted(self.parent.items()):
            out[piece] = out.get(source, "")
        return out

    def light(self, rule: Callable[[str], Any], *, before_merge: Callable[[Any, Any], Any] | None = None,
              **options: Any) -> bool:
        """`bloodmap.light_stage` with the region's `rule`; then pieces that came out alike are made one again, and the
        map is held to the same two conditions as the overlays. `options` go to `light_stage.run` (`keep`,
        `lamp_scale`, `room_key`, `groups`). `before_merge(disk, compiled)` is the level's own work on the lit map
        while its pieces are still apart (a floor evened under what hangs over it)."""
        from . import light_stage, tidy
        from .rules import evaluate

        self._need("light", held=True)
        disk = self.disk
        before = _open(evaluate(disk))
        region_of = self.region_of()
        lit = light_stage.run(disk, region_of, rule, **options)
        # a rule that names lights and laid none: under the sky the stage lays nothing (a lamp post is set by hand)
        asked = {region for region in set(region_of.values()) if region and rule(region).form != "none"}
        unlit = sorted(asked - set(lit.get("rooms", {})))
        if unlit:
            self.say("light rules that laid no light (a sector open to the sky, or too low or small to be a room): "
                     + ", ".join(unlit))
        evened = before_merge(disk, self.compiled) if before_merge is not None else None
        lit_parent = {int(k): self.parent.get(int(v), int(v)) for k, v in lit["parent"].items()}
        merged = tidy.merge_alike(disk, int(lit["sectors_before"]))
        into = merged.pop("into")
        lit_parent = {into[k]: v for k, v in lit_parent.items() if into[k] >= int(lit["sectors_before"])}
        self.parent.update(lit_parent)
        self.manifest["light_stage"] = {**{k: v for k, v in lit.items() if k != "parent"}, "sectors": len(disk.sectors),
                                        "walls": len(disk.walls), "pieces": len(lit_parent), "rules_that_laid_nothing": unlit,
                                        **({"before_merge": evened} if before_merge is not None else {})}
        self.manifest["merged"] = merged
        return self._refuse(_regate(disk, before, "the light stage"))

    def tidy(self, art: Any = None) -> dict[str, int]:
        """Walls the passes split and nothing needs are joined again (`tidy.unsplit`)."""
        from . import tidy

        self._need("tidy", held=True)
        self.manifest["tidy"] = tidy.unsplit(self.disk, self.art_sizes if art is None else art)
        return self.manifest["tidy"]

    def tags(self, extra: dict[str, list[int]] | None = None) -> dict[str, list[int]]:
        """Which sectors are which kind of place: each region's declared `kind`, and `extra` (the level's own names),
        with every piece cut from a sector under its source's names."""
        tags: dict[str, list[int]] = {}
        for region_id, region in self.layout.regions.items():
            kind = (getattr(region, "intent", None) or {}).get("kind")
            allocation = self.compiled.allocations.get(region_id)
            if kind and allocation is not None:
                tags.setdefault(str(kind), []).append(allocation.sector_id)
        for name, sectors in (extra or {}).items():
            tags.setdefault(name, []).extend(int(s) for s in sectors)
        for piece, source in sorted(self.parent.items()):
            for sectors in tags.values():
                if source in sectors:
                    sectors.append(piece)
        return {name: sorted(set(sectors)) for name, sectors in sorted(tags.items())}

    def write(self, out: str | Path | None, *, tags: dict[str, list[int]] | None = None) -> None:
        """The map, `<name>.tags.json` beside it, and its size in the manifest. Nothing is written when a gate refused."""
        from .format import write_map

        self._need("write", held=True)
        disk = self.disk
        self.manifest["size"] = {"sectors": len(disk.sectors), "walls": len(disk.walls), "sprites": len(disk.sprites)}
        if out is not None:
            out = Path(out)
            out.parent.mkdir(parents=True, exist_ok=True)
            write_map(disk, out)
            out.with_suffix(".tags.json").write_text(json.dumps(self.tags() if tags is None else tags, indent=1),
                                                     encoding="utf-8")
        self.say(f"sectors {len(disk.sectors)} walls {len(disk.walls)} sprites {len(disk.sprites)}"
                 + (f" -> {out}" if out else ""))

    def finished(self) -> Finished:
        """What was made, whether or not it was written; the stages that ran go into the manifest."""
        self.stage("end", "")
        self.stages.pop()
        self.manifest["stages"] = [{"name": row["name"], "says": row["says"]} for row in self.stages]
        return Finished(self.disk, self.compiled, self.manifest, list(self.refused), self.stages)


class FinishError(RuntimeError):
    pass


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
    made = Finish(layout, circuit=circuit, manifest=manifest, art_dir=art_dir, say=say)
    made.stage("compile", "the layout becomes sectors, walls and sprites")
    made.compile(lit=light is not None)
    if on_level is not None:
        made.stage("level", "the level's own passes on the compiled level")
        made.manifest["level"] = on_level(made.compiled)
    made.stage("alignment", "one texture frame per run of walls, standing on its floor")
    made.align(world_phase=world_phase)
    made.to_disk()
    if on_disk is not None:
        made.stage("disk", "the level's own passes on the finished records")
        made.manifest["disk"] = on_disk(made.disk, made.compiled)
    made.stage("gates", "nothing is built: rules, swept closure, read-back, sprite fit, tile contexts, wiring")
    if not made.hold(map_name=Path(out).name if out else ""):
        return made.finished()
    if layout.overlays:
        made.stage("overlays", "shadows and patches declared on the layout, cut into the finished map")
        if not made.cut_overlays():
            return made.finished()
    if light is not None:
        made.stage("light", "lamps laid, shadows and floor bands cut, every shade written")
        if not made.light(light, **(light_options or {})):
            return made.finished()
    made.stage("write", "the map, its sector tags and the manifest")
    made.tidy()
    made.write(out)
    return made.finished()


def write_manifest(finished: Finished, path: str | Path) -> None:
    """Keep what the build measured beside the map: the same build writes the same file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(finished.manifest, indent=2, default=str) + "\n", encoding="utf-8", newline="\n")
