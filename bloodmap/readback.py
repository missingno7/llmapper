"""Read a built map back and diff it against the sentence that built it.

The authoring-loop law, made one callable. Roadmap Phase 11 item 3: *every
constructor's test builds, reads back through effects/conditional, and asserts
the parse equals the grammar sentence the constructor claims*. That was true
of the pattern zoo only, because the gates lived in `projects/pattern-zoo`;
blood-city built a curtain that failed conformance and nothing in its build
said so until a gate was added there by hand, one at a time.

This module owns the comparison instead, so a project wires ONE call.

## The sentence

The declared side is a plain dict with a documented shape. It is deliberately
*not* a typed `MechanismDecl` yet (roadmap Phase 13): the schema is what the
comparison needs, and the typed layer should be shaped by that need rather
than guessed at. Every key is optional except `construct`; an absent key is
a claim not made, and a claim not made is never a difference.

```text
construct     str   what kind of thing this is: "curtain", "planar_door",
                    "turnstile", "sliding_gate", "lift", "z_motion_door",
                    "glass", "aperture", "street", "stack" ... The name
                    routes the conformance template and nothing else.
name          str   what to call it in the diff. Defaults to the construct.

--- placement ------------------------------------------------------------
sector        int   the sector the mechanism lives in
sectors       [int] every sector the construct built, the motor included
sector_type   int   the type that sector must carry (614, 615, 600 ...)

--- payload --------------------------------------------------------------
members       [int] the motion set the construct DECLARES it may deform.
                    `motion.check_motion_set` law: an undeclared member is
                    an integration defect even when the geometry is valid at
                    every step of the travel.
payload_shape str   what `effects.payload` must call it
reads_as      str   what `effects.design_object` must read it as

--- wiring ---------------------------------------------------------------
wiring  {route, channel, command, rx_id, tx_id, requires_key, irreversible}
                    `route` is checked through `conditional.route_edges`;
                    the numeric fields are checked against the XSECTOR.

--- drag -----------------------------------------------------------------
drag  {closure: bool, steps: int}
                    when `closure` is true, `motion_sim.closure_health` must
                    report no problems over the whole travel, for every loop
                    the DragPoint closure touches -- neighbours included.

--- visibility -----------------------------------------------------------
visibility  {tiles: [int], walkable_band: bool, per_leaf: bool}
                    every listed tile authored inside the construct's own
                    sectors must be drawn somewhere (`render_slots`), and
                    with `walkable_band` at least one of its walls must draw
                    in a band a body walks through.

--- state ----------------------------------------------------------------
state  {changes: bool, travel: int|None}
                    the state-pair measurement: the mechanism must measure
                    DIFFERENT at OFF and at ON. Same four measures as
                    `reports/zoo-state-check.json` (its generator is
                    `work/_state_check.py`, which snapped two whole maps;
                    this does it in memory from the poses).
```

## What it returns

`ReadBack`, whose `differences` are typed `Difference` records naming the
facet, what the sentence wanted, what the reader found, and WHICH READER
found it. `agrees` is structural equality.

A reader that cannot measure a facet says so in `unmeasured` rather than
passing it silently -- the standing warning in this repository is that a
critic which measures nothing reports 100% conformance forever.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

__all__ = [
    "Difference", "ReadBack", "SENTENCE_KEYS", "sentence",
    "read_back", "state_pair", "readback_report",
]

SCHEMA = "llmapper.readback"
SCHEMA_VERSION = 1

#: Every key a sentence may carry. An unknown key is refused rather than
#: ignored: a misspelled claim that is silently dropped is a gate that
#: measures nothing, which is the failure mode this whole module exists for.
SENTENCE_KEYS = frozenset({
    "construct", "name", "sector", "sectors", "sector_type", "members",
    "payload_shape", "reads_as", "wiring", "drag", "visibility", "state",
    "note",
})

#: Which conformance measurement a construct name calls for. A construct with
#: no entry is not un-checked -- it still goes through existence, members,
#: wiring, closure, visibility and the state pair; it simply has no mined
#: template of its own.
_TEMPLATES: dict[str, str] = {
    "curtain": "measure_curtain",
    "turnstile": "measure_turnstile",
    "rotor": "measure_turnstile",
    "planar_door": "measure_planar_door",
    "sliding_gate": "measure_sprite_payload",
    "sprite_gate": "measure_sprite_payload",
}


@dataclass(frozen=True)
class Difference:
    """One facet on which the built map and the sentence disagree."""

    #: The sentence's `name`, so a diff over a manifest names the mechanism.
    mechanism: str
    #: A dotted facet path: "sector_type", "wiring.channel", "members" ...
    facet: str
    wanted: Any
    found: Any
    #: The module:function that measured it, so the reading can be re-run.
    reader: str
    detail: str = ""

    def __str__(self) -> str:
        return (f"{self.mechanism}: {self.facet}: wanted {self.wanted!r}, "
                f"found {self.found!r} [{self.reader}]"
                + (f" -- {self.detail}" if self.detail else ""))


@dataclass
class ReadBack:
    """What reading the built map back found, against what was declared."""

    map: str = ""
    sentences: int = 0
    differences: list[Difference] = field(default_factory=list)
    #: Per mechanism, everything the readers measured -- kept whether or not
    #: it disagreed, because the numbers are the evidence.
    measured: list[dict[str, Any]] = field(default_factory=list)
    #: Facets a sentence claimed that no reader could measure here. Never
    #: silent: an unmeasurable claim is a hole in the gate.
    unmeasured: list[str] = field(default_factory=list)

    @property
    def agrees(self) -> bool:
        """Structural equality: the parse equals the declared sentence."""
        return not self.differences

    def to_dict(self) -> dict[str, Any]:
        return {
            "$schema": SCHEMA, "schema_version": SCHEMA_VERSION,
            "map": self.map,
            "sentences": self.sentences,
            "agrees": self.agrees,
            "differences": [
                {"mechanism": d.mechanism, "facet": d.facet,
                 "wanted": _plain(d.wanted), "found": _plain(d.found),
                 "reader": d.reader, "detail": d.detail}
                for d in self.differences],
            "unmeasured": list(self.unmeasured),
            "measured": [_plain(row) for row in self.measured],
        }

    def report(self) -> str:
        if self.agrees:
            head = f"read-back: {self.sentences} sentence(s), all agree"
        else:
            head = (f"read-back: {self.sentences} sentence(s), "
                    f"{len(self.differences)} difference(s)")
        lines = [head]
        lines += [f"  DIFF {d}" for d in self.differences]
        lines += [f"  (unmeasured) {u}" for u in self.unmeasured]
        return "\n".join(lines)


def _plain(value: Any) -> Any:
    """JSON-able, without pretending a set or a tuple is a list elsewhere."""
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_plain(v) for v in value]
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    return str(value)


class SentenceError(ValueError):
    """A declared sentence that cannot mean anything."""


def sentence(construct: str, **claims: Any) -> dict[str, Any]:
    """Build a sentence dict, refusing a key the readers do not know.

    The shape is documented in this module's docstring. This exists so that
    a typo in a claim fails at the call site rather than quietly removing a
    gate, and so the eventual `MechanismDecl` has one place to grow from.
    """
    if not construct or not isinstance(construct, str):
        raise SentenceError("a sentence names its construct")
    unknown = sorted(set(claims) - SENTENCE_KEYS)
    if unknown:
        raise SentenceError(
            f"{construct}: unknown claim(s) {unknown}; the sentence keys are "
            f"{sorted(SENTENCE_KEYS)}")
    out: dict[str, Any] = {"construct": construct}
    out.update(claims)
    out.setdefault("name", construct)
    return out


# ---------------------------------------------------------------------------
# the state pair, in memory
# ---------------------------------------------------------------------------

def _sector_polygon(disk: Any, sector_id: int) -> list[tuple[float, float]]:
    from .motion_sim import blood_sector_walls

    return list(blood_sector_walls(disk, sector_id))


def _area(points: Sequence[tuple[float, float]]) -> float:
    total = 0.0
    for index, (x, y) in enumerate(points):
        nx, ny = points[(index + 1) % len(points)]
        total += x * ny - nx * y
    return abs(total) / 2.0


def state_pair(disk: Any, sector_id: int) -> dict[str, Any]:
    """Measure one mechanism at OFF and at ON, and say what changed.

    The same four measures as `reports/zoo-state-check.json`, whose generator
    (`work/_state_check.py`, commit 929cdc1) wrote two whole snapped maps and
    read them both. Nothing here needs a file: `motion_sim.blood_poses`
    already transcribes `TranslateSector` and knows which of the two frames
    is OFF for a sector that rests open, and the z pair lives in the XSECTOR.

    * **plan area** -- a slide re-partitions area between two halves,
    * **headroom** -- `on_floor_z - off_floor_z` less the ceiling's move, the
      whole payload of a z-motion door,
    * **turn** -- how far a rotator swings,
    * **sprite travel** -- the marker separation, which the drag-flagged
      payload sprites ride.

    `changes` is False when every one of them is zero, which is the finding
    the generator called "NOTHING MEASURABLE CHANGED". A whole-circle rotator
    is exempt and says so, because ending where it began IS the mechanism.
    """
    from .motion import MOVING_TYPES, marker_pair, rotate_marker
    from .motion_sim import blood_poses

    fields = disk.sectors[sector_id].fields
    extra = disk.sectors[sector_id].extra
    xfields = extra.fields if extra is not None else {}
    out: dict[str, Any] = {"sector": sector_id,
                           "type": int(fields["type"]),
                           "measured": []}

    #: z motion: the pair the XSECTOR declares, which is what actually moves.
    headroom = ((int(xfields.get("on_floor_z", 0))
                 - int(xfields.get("off_floor_z", 0)))
                - (int(xfields.get("on_ceiling_z", 0))
                   - int(xfields.get("off_ceiling_z", 0))))
    out["headroom_change"] = int(headroom)
    if headroom:
        out["measured"].append("headroom")

    area_change = 0.0
    if int(fields["type"]) in tuple(MOVING_TYPES):
        try:
            off, on = blood_poses(disk, sector_id)
        except Exception as exc:                       # unmeasurable, not ok
            out["area_error"] = str(exc)
            off = on = None
        if off is not None and on is not None:
            area_change = round(_area(on) - _area(off), 1)
            out["area_off"] = round(_area(off), 1)
            out["area_on"] = round(_area(on), 1)
    out["area_change"] = area_change
    if area_change:
        out["measured"].append("area")

    pair = marker_pair(disk, sector_id)
    travel = round(math.hypot(*pair["travel"]), 1) if pair else 0.0
    out["declared_travel"] = travel
    if travel:
        out["measured"].append("travel")

    spin = rotate_marker(disk, sector_id)
    out["turn"] = spin["turn"] if spin else None
    out["whole_circles"] = bool(spin and spin.get("turns_full_circles"))
    if spin and spin["turn"]:
        out["measured"].append("turn")

    out["changes"] = bool(out["measured"])
    if not out["changes"] and out["whole_circles"]:
        out["changes"] = True
        out["note"] = ("identical by design: turns whole circles, so both "
                       "states are the same pose")
    return out


# ---------------------------------------------------------------------------
# the readers
# ---------------------------------------------------------------------------

def _sector_walls(disk: Any, sector_id: int) -> range:
    fields = disk.sectors[sector_id].fields
    start = int(fields["wall_ptr"])
    return range(start, start + int(fields["wall_count"]))


def _read_existence(disk: Any, claim: Mapping[str, Any], name: str,
                    sector: int, owners: Sequence[int],
                    row: dict[str, Any]) -> list[Difference]:
    """The sector is the type it claims, and the stack finds a mechanism."""
    from .effects import payload, read_mechanism

    out: list[Difference] = []
    found_type = int(disk.sectors[sector].fields["type"])
    row["sector_type"] = found_type
    wanted_type = claim.get("sector_type")
    if wanted_type is not None and int(wanted_type) != found_type:
        out.append(Difference(name, "sector_type", int(wanted_type),
                              found_type, "format.DiskMap.sectors[].type"))
        #: The rest of the reading is about a different thing; stop here.
        return out

    if claim.get("reads_as") or claim.get("payload_shape"):
        reading = read_mechanism(disk, sector, owners=list(owners))
        if reading is None:
            out.append(Difference(
                name, "exists", "a mechanism", None,
                "effects.read_mechanism",
                "the reading stack finds no moving mechanism in this sector"))
            return out
        row["reads_as"] = reading["design_object"]
        if claim.get("reads_as") and reading["design_object"] != claim["reads_as"]:
            out.append(Difference(name, "reads_as", claim["reads_as"],
                                  reading["design_object"],
                                  "effects.design_object"))
    if claim.get("payload_shape"):
        shape = payload(disk, sector)["shape"]["shape"]
        row["payload_shape"] = shape
        if shape != claim["payload_shape"]:
            out.append(Difference(name, "payload_shape",
                                  claim["payload_shape"], shape,
                                  "effects.payload"))
    return out


def _read_members(disk: Any, claim: Mapping[str, Any], name: str,
                  sector: int, row: dict[str, Any]) -> list[Difference]:
    """The motion set equals what the construct declared, and nothing more.

    The engine's own reading: `motion_sim.drag_closure` walks `nextwall` the
    way `DragPoint` does (triggers.cpp:817-854, and the `lastwall` restart at
    engine.cpp:13227), so a neighbour that merely touches by coordinate is
    not counted and one linked through a one-sided wall is.
    """
    from .motion import check_motion_set, drag_closure

    declared = claim.get("members")
    if declared is None:
        return []
    closure = drag_closure(disk, sector)
    actual = sorted(set(closure["sectors"]) | {sector})
    row["motion_set"] = actual
    row["closure_basis"] = closure["basis"]
    allowed = sorted(set(int(s) for s in declared) | {sector})
    row["declared_members"] = allowed
    if actual == allowed:
        return []
    finding = check_motion_set(disk, sector, allowed)
    detail = "; ".join(item["why"] for item in finding.undeclared[:3])
    return [Difference(name, "members", allowed, actual,
                       "motion_sim.drag_closure", detail)]


def _read_wiring(disk: Any, claim: Mapping[str, Any], name: str,
                 sector: int, sectors: Sequence[int], graph: Any,
                 row: dict[str, Any]) -> list[Difference]:
    """The channel, the verb, and the ROUTE a player actually works it by."""
    want = claim.get("wiring")
    if not want:
        return []
    out: list[Difference] = []
    extra = disk.sectors[sector].extra
    fields = extra.fields if extra is not None else {}
    row["wiring"] = {k: int(fields.get(k, 0))
                     for k in ("rx_id", "tx_id", "command", "state")}
    for key in ("rx_id", "tx_id", "command"):
        if key in want and want[key] is not None:
            found = int(fields.get(key, 0))
            if int(want[key]) != found:
                out.append(Difference(name, f"wiring.{key}", int(want[key]),
                                      found, "format XSECTOR"))
    if "channel" in want and want["channel"] is not None:
        channel = int(want["channel"])
        found = {int(fields.get("rx_id", 0)), int(fields.get("tx_id", 0))}
        if channel not in found:
            out.append(Difference(name, "wiring.channel", channel,
                                  sorted(found), "format XSECTOR",
                                  "neither rx nor tx carries the channel"))

    route_claim = want.get("route")
    if route_claim:
        if graph is None:
            return out + []
        from .conditional import route_edges

        group = set(int(s) for s in sectors)
        routes = [r for r in route_edges(graph.edges)
                  if r["mechanism"] in group and r["mechanism_kind"] == "sector"]
        triggers = sorted({cause["trigger"] for r in routes
                           for cause in r["causes"]})
        row["routes"] = triggers
        if route_claim not in triggers:
            out.append(Difference(name, "wiring.route", route_claim, triggers,
                                  "conditional.route_edges"))
        if want.get("requires_key"):
            keys = sorted({r["requires_key"] for r in routes})
            if int(want["requires_key"]) not in keys:
                out.append(Difference(name, "wiring.requires_key",
                                      int(want["requires_key"]), keys,
                                      "conditional.route_edges"))
        if want.get("irreversible") and not any(r["irreversible"] for r in routes):
            out.append(Difference(name, "wiring.irreversible", True, False,
                                  "conditional.route_edges"))
    return out


def _read_closure(disk: Any, claim: Mapping[str, Any], name: str,
                  sector: int, row: dict[str, Any]) -> list[Difference]:
    """Everything the motion drags, swept through the whole travel."""
    want = claim.get("drag")
    if not want or not want.get("closure"):
        return []
    from .motion_sim import closure_health

    health = closure_health(disk, sector, steps=int(want.get("steps", 16)))
    row["closure"] = {
        "loops": len(health["loops"]),
        "problems": list(health["problems"]),
        "notes": list(health["notes"]),
        "graze_tolerance": health.get("graze_tolerance"),
        "grazing_loops": health.get("grazing_loops"),
    }
    if health["problems"]:
        return [Difference(name, "drag.closure", "no problems",
                           list(health["problems"]),
                           "motion_sim.closure_health")]
    return []


def _read_visibility(disk: Any, claim: Mapping[str, Any], name: str,
                     sectors: Sequence[int], draws: Any,
                     row: dict[str, Any]) -> list[Difference]:
    """Every declared tile is drawn somewhere, and where it has to be.

    `render_slots` owns the rendering law (engine.cpp:4938-4940 and the
    band table transcribed there). A tile authored on a wall and drawn on no
    band is a material that was chosen and then lost -- the defect that made
    the city's stage curtain invisible while every other gate passed it.
    """
    want = claim.get("visibility")
    if not want:
        return []
    from .render_slots import WALKABLE_BANDS, bands_of_pair, render_slots

    found = draws if draws is not None else render_slots(disk)
    tiles = [int(t) for t in want.get("tiles", ())]
    if not tiles:
        return []
    group = set(int(s) for s in sectors)
    walls = [w for s in sorted(group) for w in _sector_walls(disk, s)]
    out: list[Difference] = []
    per_tile: dict[int, dict[str, Any]] = {}
    for tile in tiles:
        #: BOTH fields. A masked or one-way middle band is drawn from
        #: `over_picnum` (engine.cpp:4940 and the deferred masked pass at
        #: :7217-7218), which is the only way a tile reaches the middle of a
        #: two-sided wall -- glass and a maskwall panel are exactly that, and
        #: a reader that looked at `picnum` alone said they were on no wall.
        wearing = [w for w in walls
                   if tile in (int(disk.walls[w].fields["picnum"]),
                               int(disk.walls[w].fields.get("over_picnum", -1)))]
        #: Drawn, by the tile the band actually shows -- not by which field
        #: it came from, which is the engine's business and not the claim's.
        drawn, walkable = [], []
        for wall in wearing:
            bands = [b for b in bands_of_pair(found, wall) if b.tile == tile]
            if bands:
                drawn.append(wall)
            if any(b.band in WALKABLE_BANDS for b in bands):
                walkable.append(wall)
        per_tile[tile] = {"authored": len(wearing), "drawn": len(drawn),
                          "walkable": len(walkable)}
        if not wearing:
            out.append(Difference(name, f"visibility.{tile}.authored",
                                  ">= 1 wall", 0, "format walls",
                                  f"tile {tile} is on no wall of sectors "
                                  f"{sorted(group)}"))
            continue
        if len(drawn) != len(wearing):
            out.append(Difference(
                name, f"visibility.{tile}.drawn", len(wearing), len(drawn),
                "render_slots.bands_of_pair",
                f"{len(wearing) - len(drawn)} wall(s) wear tile {tile} and "
                f"draw it on no band"))
        if want.get("walkable_band"):
            #: At least one PER LEAF, not every wall: DOOR-CURTAINSD s4 has
            #: six fabric walls and two visible ones, and a rule demanding
            #: all six rejects the tutorial (roadmap, the curtain family).
            need = int(want.get("per_leaf", 1)) or 1
            if len(walkable) < need:
                out.append(Difference(
                    name, f"visibility.{tile}.walkable_band", need,
                    len(walkable), "render_slots.bands_of_pair (walkable bands)",
                    "a two-sided unmasked wall draws its picnum only on the "
                    "step bands (engine.cpp:4938-4940)"))
    row["visibility"] = per_tile
    return out


def _read_conformance(disk: Any, claim: Mapping[str, Any], name: str,
                      sector: int, row: dict[str, Any]) -> list[Difference]:
    """The construct still looks like the original it was mined from."""
    from . import conformance as conformance_module

    which = _TEMPLATES.get(str(claim.get("construct", "")))
    if which is None:
        return []
    measure = getattr(conformance_module, which)
    try:
        found = measure(disk, sector)
    except conformance_module.ConformanceError as exc:
        return [Difference(name, "conformance", claim["construct"],
                           "unmeasurable", f"conformance.{which}", str(exc))]
    row["conformance"] = {"construct": found.construct,
                          "measured": found.measured,
                          "deviations": [str(d) for d in found.deviations]}
    if found.conforms:
        return []
    return [Difference(name, "conformance", "conforms",
                       [str(d) for d in found.deviations],
                       f"conformance.{which}")]


def _read_state(disk: Any, claim: Mapping[str, Any], name: str, sector: int,
                row: dict[str, Any]) -> list[Difference]:
    """Both states of the mechanism, measured, not looked at."""
    want = claim.get("state")
    if not want:
        return []
    found = state_pair(disk, sector)
    row["state_pair"] = found
    out: list[Difference] = []
    if want.get("changes") and not found["changes"]:
        out.append(Difference(
            name, "state.changes", True, False, "readback.state_pair",
            "nothing measurable changes between OFF and ON: not area, not "
            "headroom, not the marker travel, not a turn"))
    travel = want.get("travel")
    if travel is not None and abs(found["declared_travel"] - float(travel)) > 2:
        out.append(Difference(name, "state.travel", float(travel),
                              found["declared_travel"], "motion.marker_pair"))
    return out


# ---------------------------------------------------------------------------
# the one function
# ---------------------------------------------------------------------------

def read_back(disk: Any, sentences: Iterable[Mapping[str, Any]], *,
              map_name: str = "", owners: Sequence[int] | None = None,
              graph: Any = None) -> ReadBack:
    """Read a built map back and diff it against its declared sentences.

    `disk` is a `DiskMap` -- from `format.read_map` for a map on disk, or
    `compiled.level.to_disk_map()` straight out of a `PlanarLayout.compile`.
    `sentences` are the dicts documented at the top of this module.

    Returns a `ReadBack` whose `agrees` is structural equality. Nothing here
    raises on a difference: a difference is a finding, and the caller decides
    whether it fails a build.
    """
    from .doors import _wall_owners

    out = ReadBack(map=str(map_name), sentences=0)
    wall_owner_list = list(owners) if owners is not None else _wall_owners(disk)

    #: Shared across every sentence: the render pass is a whole-map read and
    #: the conditional graph is expensive.
    draws = None
    wants_visibility = False
    wants_route = False
    for claim in sentences:
        if claim.get("visibility", {}).get("tiles"):
            wants_visibility = True
        if (claim.get("wiring") or {}).get("route"):
            wants_route = True
    if wants_visibility:
        from .render_slots import render_slots

        draws = render_slots(disk)
    if wants_route and graph is None:
        try:
            from .conditional import build_graph

            graph = build_graph(disk)
        except Exception as exc:                      # never silent
            out.unmeasured.append(
                f"conditional.build_graph failed ({exc}); no route claim "
                f"could be checked")
            graph = None

    for raw in sentences:
        claim = dict(raw)
        unknown = sorted(set(claim) - SENTENCE_KEYS)
        if unknown:
            raise SentenceError(
                f"{claim.get('name', claim.get('construct'))}: unknown "
                f"claim(s) {unknown}")
        name = str(claim.get("name") or claim.get("construct") or "?")
        out.sentences += 1
        sector = claim.get("sector")
        sectors = [int(s) for s in claim.get("sectors", ())]
        if sector is None and sectors:
            sector = sectors[0]
        if sector is None:
            out.unmeasured.append(
                f"{name}: the sentence names no sector, so nothing in the "
                f"built map could be found to compare it with")
            continue
        sector = int(sector)
        if not sectors:
            sectors = [sector]
        if sector >= len(disk.sectors):
            out.differences.append(Difference(
                name, "sector", sector, f"{len(disk.sectors)} sectors",
                "format.DiskMap", "the declared sector is not in the map"))
            continue

        row: dict[str, Any] = {"name": name,
                               "construct": claim.get("construct"),
                               "sector": sector, "sectors": sectors}
        out.measured.append(row)
        found = _read_existence(disk, claim, name, sector, wall_owner_list, row)
        out.differences.extend(found)
        if any(d.facet == "sector_type" for d in found):
            #: A sector of the wrong type is a different thing; measuring its
            #: payload would report about that other thing.
            continue
        out.differences.extend(_read_members(disk, claim, name, sector, row))
        out.differences.extend(
            _read_wiring(disk, claim, name, sector, sectors, graph, row))
        out.differences.extend(_read_closure(disk, claim, name, sector, row))
        out.differences.extend(
            _read_visibility(disk, claim, name, sectors, draws, row))
        out.differences.extend(_read_conformance(disk, claim, name, sector, row))
        out.differences.extend(_read_state(disk, claim, name, sector, row))
        if (claim.get("wiring") or {}).get("route") and graph is None:
            out.unmeasured.append(
                f"{name}: wiring.route -- no conditional graph was available")
    return out


def readback_report(result: ReadBack) -> str:
    """The diff as a build log prints it, one line per difference."""
    return result.report()


# ---------------------------------------------------------------------------
# deriving the declared side from what a build actually declared
# ---------------------------------------------------------------------------

#: The sector types whose motion is worth sweeping and whose payload has a
#: declarable membership. 600/602 move in z and have neither.
_SWEPT_TYPES = (613, 614, 615, 616, 617)
#: Types whose whole point is that something differs between the two states.
_STATEFUL_TYPES = _SWEPT_TYPES + (600, 602, 606, 612, 618, 619, 620, 621)


def sentences_from_layout(compiled: Any, *, layout: Any = None,
                          fabric_tile: int = 146) -> list[dict[str, Any]]:
    """The sentences a build DECLARED, read off the layout that built it.

    This is the honest declared side for a whole-level gate: it is not a
    second hand-written manifest that can drift from the source, it is what
    the regions actually say about themselves -- their sector type, the
    XSECTOR the constructor asked for, and the payload the constructor
    declared through `PlanarLayout.declare_motion`.

    Why it is worth running on the FINAL disk even though `compile` already
    preflights the motion set: the city's facade passes SPLIT WALLS after
    `compile` returns, and the swept gate that ran inside `compile` was
    looking at the geometry before that. Anything those passes break is
    invisible until the finished map is read back.

    A claim is made only where the layout made one. A region that declared
    no motion set gets no `members` claim; a region with no XSECTOR gets no
    wiring claim. Never invent a claim the source did not state.
    """
    source = layout if layout is not None else getattr(compiled, "layout", None)
    if source is None:
        raise SentenceError(
            "sentences_from_layout needs the PlanarLayout that compiled; "
            "pass layout= when the CompiledLayout does not carry it")
    allocations = compiled.allocations
    declared_motion = dict(getattr(source, "declared_motion", {}) or {})
    out: list[dict[str, Any]] = []
    for region_id, region in source.regions.items():
        allocation = allocations.get(region_id)
        if allocation is None:
            continue
        type_id = int(getattr(region, "type", 0) or 0)
        behavior = dict(getattr(region, "sector_behavior", {}) or {})
        if not type_id and not behavior:
            continue
        claims: dict[str, Any] = {"name": region_id,
                                  "sector": int(allocation.sector_id),
                                  "sectors": [int(allocation.sector_id)]}
        if type_id:
            claims["sector_type"] = type_id
        if region_id in declared_motion:
            claims["members"] = sorted(
                int(allocations[name].sector_id)
                for name in declared_motion[region_id] if name in allocations)
        wiring = {key: int(behavior[key])
                  for key in ("rx_id", "tx_id", "command")
                  if key in behavior}
        if wiring:
            claims["wiring"] = wiring
        if type_id in _SWEPT_TYPES:
            claims["drag"] = {"closure": True}
        if type_id in _STATEFUL_TYPES:
            claims["state"] = {"changes": True}
        #: What kind of thing this is, for the conformance template. Read
        #: from the built region rather than from a label, the way the zoo's
        #: sweep identifies a curtain by what it WEARS -- a name can be
        #: changed and the tile cannot.
        construct = _construct_of(source, region, type_id, fabric_tile)
        if construct == "curtain":
            claims["visibility"] = {"tiles": [int(fabric_tile)],
                                    "walkable_band": True, "per_leaf": 1}
        out.append(sentence(construct, **claims))
    return out


def _construct_of(layout: Any, region: Any, type_id: int,
                  fabric_tile: int) -> str:
    """Name the construct from what the region is and what it wears."""
    if type_id in (613, 615):
        return "turnstile"
    if type_id == 614:
        painted = {int(entry.get("picnum", -1))
                   for entry in _painted_walls(layout, region)}
        if fabric_tile in painted or int(
                getattr(region, "wall_picnum", 0)) == fabric_tile:
            return "curtain"
        return "marked_slide"
    if type_id in (600, 602):
        return "z_motion_door"
    if type_id in (616, 617):
        return "unmarked_mover"
    return "sector"


def _painted_walls(layout: Any, region: Any) -> list[dict[str, Any]]:
    """Every explicit wall paint the layout recorded for this region.

    `PlanarLayout.painted` is keyed `(region_id, edge) -> fields`.
    """
    painted = getattr(layout, "painted", None) or {}
    return [fields for (region_id, _edge), fields in painted.items()
            if region_id == region.region_id]


def lost_tiles_as_differences(lost: Any, *,
                              mechanism: str = "(whole map)") -> list[Difference]:
    """The rendering rule's violations, restated as read-back differences.

    `rules_blood`'s `wall-tile-is-drawn-somewhere` finds a tile a map
    authors on walls and shows on no band anywhere. That is not a style
    warning: it is a READ-BACK DIFF -- the map claims a material and the
    engine draws something else -- and printing it in the rule registry's
    voice let it read as one diagnostic among hundreds. Restated here so a
    build can print it in the same vocabulary as every other difference.
    """
    out = []
    for violation in getattr(lost, "violations", ()) or ():
        out.append(Difference(
            mechanism, "visibility.drawn", "drawn on some band", "drawn nowhere",
            "rules_blood.wall-tile-is-drawn-somewhere",
            f"{violation.location}: {violation.detail}"))
    return out
