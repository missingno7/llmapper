"""Posed: a copy of a map with everything one wiring chain answers put in its other state.

Every frame this project renders shows a map in the pose it was SAVED in,
and the observer is a static editor renderer: no door moves, no event runs
(`xmapedit/src_blood/observe/README.md`, "Differences from NBlood"). So a
critic cannot tell whether a mechanism works the intended way, because it
only ever sees one end of it. This builds the other end -- as a separate
`DiskMap`, never by touching the input -- and says, object by object, what
was done and what could not be shown and why.

A chain (`bloodmap.wiring.chains`) is a cause, a sender and the listeners on
its wire. `posed` follows it the way the engine does: the sender takes the
state its cause gives it, each message carries the sender's `command`, and
each listener lands in the state that command gives it. Only answers whose
picture the engine derives from that state are posed, and each is a
transcription, not an approximation:

* a z-moving sector (600, 602, and the z pair of 614-617) rests at
  `off_*_z` for state 0 and `on_*_z` for state 1 (`ZTranslateSector`,
  NBlood triggers.cpp:1023-1120, with `GetWaveValue` 0 and 65536 at the two
  ends); sprites on it ride as the engine moves them;
* a slide or rotate sector (614-617) drags vertices by `TranslateSector`
  (triggers.cpp:856-1021); `motion_sim.closure_sweep` is that transcription
  and this only reads its two end poses, sprites flagged 8192/16384 moving
  with it;
* a kSwitchToggle/kSwitchOneWay is drawn `picanm.num + 1` tiles further on
  when its state is set and its tile's view type is 0 (view.cpp:2724-2737
  and :2822-2826). The observer reads no XSPRITE (obs_main.c:369 skips the
  bytes), so the copy's `picnum` is moved instead of its `state`;
* a thing destroyed as its own chain's cause is gone (`actPostSprite(...,
  kStatFree)`, triggers.cpp:385-392), so it is hidden with cstat 32768. The
  gib or debris it leaves is not drawn.

Everything else -- generators, sounds, exploders, lighting, a counter, a
path sector, an engine channel such as a secret or the exit -- is reported
"not posed" with the reason. That honest refusal is part of the output.

`rested` is the same objects in the pose the game shows at LOAD. That is not
always the saved map: `trInit` rebases a slide a whole travel backwards
before moving it to its state (triggers.cpp:2222-2247), so a state-0 slide is
found displaced from where it was drawn, and a switch saved at state 1 is
drawn on its second picture. A before/after pair is honest only if "before"
is the rest pose, so `tools/mechanism_look.py` renders `rested` against
`posed`, not the saved file against `posed`.

What is not modelled, and said in every report: whether the sender actually
sends (the trigger_on/trigger_off gate of `SetSpriteState`, triggers.cpp:
100-106), delays and self-return (`wait_time`), and anything that happens
after the travel ends.
"""

from __future__ import annotations

import copy
from typing import Any, Mapping

from .blood_types import SECTOR_TYPES, SPRITE_TYPES
from .model import record_extra, record_fields
from .motion_sim import closure_sweep, blood_travel, rotate_about
from .sector_geom import outline_and_holes

#: Sector types whose floor/ceiling the engine moves on a state change
#: (the `OperateSector` dispatch, triggers.cpp:1680-1696).
Z_TYPES = {600: "kSectorZMotion", 602: "kSectorZMotionSprite"}
#: Sector types that drag vertices; 614-617 also take their z pair
#: (`trInit` falls through to `ZTranslateSector`, triggers.cpp:2246-2250).
SWEPT_TYPES = {614: "kSectorSlideMarked", 615: "kSectorRotateMarked",
               616: "kSectorSlide", 617: "kSectorRotate"}
SWITCH_TYPES = {20: "kSwitchToggle", 21: "kSwitchOneWay"}
#: Markers never ride a moving sector (triggers.cpp:933-941, :1047).
MARKER_STATNUMS = (10, 16)
INVISIBLE = 32768

#: eventq.h:83-89
COMMANDS = {0: "kCmdOff", 1: "kCmdOn", 2: "kCmdState", 3: "kCmdToggle",
            4: "kCmdNotState", 5: "kCmdLink", 6: "kCmdLock", 7: "kCmdUnlock",
            8: "kCmdToggleLock"}

NOT_MODELLED = [
    "whether a sender's state actually changes: SetSpriteState returns before "
    "sending when it does not (triggers.cpp:87-88), and the pose shows what the "
    "listeners do IF the message arrives. (A thing saved at state 0 does "
    "change: `actInit` sets every thing but a few to state 1 at level start, "
    "actor.cpp:2551, so its destruction is a real 1 -> 0.) A silent sender's listeners are not "
    "posed; a trigger_on/trigger_off gate the new state misses is flagged per "
    "listener (triggers.cpp:100-106)",
    "wait_time: a listener that returns on its own is shown at the far end "
    "of its travel, before it returns",
    "busy waves and the moment in between: only the two ends are posed",
]


def _parse(ref: str) -> tuple[str, int]:
    kind, _, index = ref.partition(" ")
    return kind, int(index) if index.strip().lstrip("-").isdigit() else -1


def _frames(tiles: Mapping[int, Any] | None, tile: int) -> tuple[int | None, int | None, int | None]:
    """(picanm num, picanm view type, yofs) of a tile, or Nones without ART."""
    if tiles is None or int(tile) not in tiles:
        return None, None, None
    from .art import decode_picanm

    anim = decode_picanm(tiles[int(tile)].picanm)
    return int(anim["frames"]), int(anim["extra"]) & 7, int(anim["yofs"])


def _event(cause: list[str]) -> int | None:
    """The command the engine's own trigger carries for a chain's cause.

    A level-start channel sends kCmdOn (triggers.cpp:2316-2338); a thing
    destroyed or a dude killed is triggered with kCmdOff (actor.cpp:3513,
    `actKillDude`); every player act (push, shot, touch ...) is one of the
    engine's sprite/sector trigger commands, which no case of a switch or a
    door names, so it takes the `default:` branch -- None here means that.
    """
    first = cause[0] if cause else ""
    if first.startswith("channel "):
        return 1
    if first in ("destroyed", "killed"):
        return 0
    return None


def _next_state(kind: str, type_id: int, extra: Mapping[str, Any], command: int | None,
                *, root: bool) -> tuple[int | None, str]:
    """The state an object lands in when `command` reaches it (None: undecided).

    `command` None is the `default:` branch of `OperateSprite` /
    `OperateDoor`: a toggle, or for a one-way switch its rest state flipped.
    """
    state = int(extra.get("state", 0) or 0)
    if command is not None and command not in (0, 1, 3):
        return None, f"command {command} ({COMMANDS.get(command, '?')}) sets no state"
    if kind == "sprite":
        if type_id == 20:                                     # triggers.cpp:441-457
            return ({0: 0, 1: 1}.get(command, state ^ 1),
                    "triggers.cpp:441-457 (kSwitchToggle)")
        if type_id == 21:                                     # triggers.cpp:458-474
            rest = int(extra.get("rest_state", 0) or 0)
            return ({0: 0, 1: 1}.get(command, rest ^ 1),
                    "triggers.cpp:458-474 (kSwitchOneWay)")
        if SPRITE_TYPES.get(type_id, {}).get("category") == "thing" and root:
            return 0, "actor.cpp:3513 trTriggerSprite(kCmdOff) on destruction"
        return ({0: 0, 1: 1}.get(command, state ^ 1),
                "generic OperateSprite reading; its picture is not derived from state")
    if kind == "sector":
        if type_id in Z_TYPES or type_id in SWEPT_TYPES:
            return ({0: 0, 1: 1}.get(command, state ^ 1),
                    "OperateDoor: off/on, else toggle (triggers.cpp:1680-1696)")
        return None, f"sector type {type_id} is not a door the engine moves on a state"
    return None, f"{kind} state is not read here"


def _plan(disk: Any, chain: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Every object of the chain once, in order, with its state now and after."""
    plan: list[dict[str, Any]] = []
    seen: dict[str, dict[str, Any]] = {}
    after: dict[str, int | None] = {}

    def record(ref: str):
        kind, index = _parse(ref)
        group = {"sector": disk.sectors, "sprite": disk.sprites, "wall": disk.walls}.get(kind)
        if group is None or not 0 <= index < len(group):
            return kind, index, None, {}
        item = group[index]
        return kind, index, item, (record_extra(item) or {})

    root = chain["root"]
    kind, index, item, extra = record(root)
    type_id = int(chain.get("root_type_id", 0))
    decoupled = bool(int(extra.get("decoupled", 0) or 0))
    if decoupled:
        state, why = int(extra.get("state", 0) or 0), \
            "decoupled: trTriggerSprite sends its command and keeps its state (triggers.cpp:1895)"
    else:
        state, why = _next_state(kind, type_id, extra, _event(list(chain.get("cause", []))), root=True)
    row = {"object": root, "kind": kind, "index": index, "type_id": type_id,
           "type": chain.get("root_type"), "role": "sender",
           "cause": "/".join(chain.get("cause", [])),
           "state": [int(extra.get("state", 0) or 0), state], "why_state": why,
           "messages": 0,
           "wait": (int(extra.get("wait_time", extra.get("wait_time_a", 0)) or 0)
                    if int(extra.get("rest_state", 0) or 0) != state else 0)}
    plan.append(row)
    seen[root] = row
    after[root] = state
    gates = {root: _gate(extra, state, decoupled)}
    sends_as = {root: gates[root][2]}

    for step in chain.get("steps", []):
        if chain.get("silent") and step["from"] == root:
            silent = ("the sender reports no change of its state (no trigger_on, "
                      "trigger_off or link: wiring.can_send), so this never arrives")
        else:
            silent = ""
        target = step["to"]
        gate, arrives, _as = gates.get(step["from"], ("", "", None))
        if target == "engine":
            plan.append({"object": f"engine channel {step['channel']}", "kind": "engine",
                         "index": int(step["channel"]), "type_id": int(step["to_type_id"]),
                         "type": step["to_type"], "role": "listener", "from": step["from"],
                         "state": [None, None], "why_state": "the engine's own channel",
                         "messages": 1, "silent": silent, "gate": gate,
                         "arrives": arrives})
            continue
        if target in seen:
            seen[target]["messages"] += 1
            continue
        kind, index, item, extra = record(target)
        command = int(step.get("command", 0))
        sender_after = sends_as.get(step["from"], after.get(step["from"]))
        if command in (2, 4):                     # evSend, eventq.cpp:353-360
            if sender_after is None:
                resolved, why = None, (f"command {COMMANDS[command]} follows the sender's "
                                       "state, which is undecided")
            else:
                on = bool(sender_after) ^ (command == 4)
                resolved, why = (1 if on else 0), f"{COMMANDS[command]} resolved by evSend"
        else:
            resolved, why = command, ""
        if command in (2, 4) and resolved is None:
            state = None
        else:
            state, why2 = _next_state(kind, int(step["to_type_id"]), extra,
                                      None if resolved == 3 else resolved, root=False)
            why = "; ".join(w for w in (why, why2) if w)
        row = {"object": target, "kind": kind, "index": index,
               "type_id": int(step["to_type_id"]), "type": step["to_type"],
               "role": "listener", "from": step["from"], "command": command,
               "state": [int(extra.get("state", 0) or 0), state], "why_state": why,
               "wait": int(step.get("wait", 0) or 0), "messages": 1,
               "silent": silent, "gate": gate, "arrives": arrives}
        plan.append(row)
        seen[target] = row
        after[target] = state
        gates[target] = _gate(extra, state, bool(int(extra.get("decoupled", 0) or 0)))
        sends_as[target] = gates[target][2]
    return plan


def _gate(extra: Mapping[str, Any], state: int | None,
          decoupled: bool) -> tuple[str, str, int | None]:
    """(why it may send nothing, when it sends, the state it sends as).

    `SetSpriteState` (triggers.cpp:100-106, and its sector and wall twins)
    sends on an ON only with trigger_on and on an OFF only with
    trigger_off; a decoupled sprite sends regardless (triggers.cpp:1895).
    A sender that misses the edge it lands on can still send on the way
    BACK: with a wait_time and a rest state it is not in, the engine posts
    the return (triggers.cpp:98-99), and that change crosses the other edge.
    E1M1's opening casket is wired exactly so: its level-start switch has
    trigger_off only and wait_time 6.
    """
    if decoupled or state is None:
        return "", "", state
    edge = "trigger_on" if state else "trigger_off"
    if int(extra.get(edge, 0) or 0) or int(extra.get("command", 0) or 0) == 5:
        return "", "", state
    wait = int(extra.get("wait_time", extra.get("wait_time_a", 0)) or 0)
    rest = int(extra.get("rest_state", 0) or 0)
    if wait and rest != state:
        back = "trigger_on" if rest else "trigger_off"
        if int(extra.get(back, 0) or 0):
            return "", (f"arrives when its sender returns to state {rest} after "
                        f"{wait / 10:g} s (triggers.cpp:98-99, then :100-106)"), rest
    return (f"its sender lands in state {state} and has no {edge}; by "
            "triggers.cpp:100-106 it sends nothing on this change"), "", state


def _centroid(disk: Any, sector_id: int) -> list[int]:
    outline, _holes = outline_and_holes(disk, sector_id)
    if not outline:
        return [0, 0]
    return [int(sum(p[0] for p in outline) / len(outline)),
            int(sum(p[1] for p in outline) / len(outline))]


def _sprites_in(disk: Any, sector_id: int):
    for index, sprite in enumerate(disk.sprites):
        fields = record_fields(sprite)
        if int(fields["sector"]) == sector_id and int(fields.get("status", 0)) not in MARKER_STATNUMS:
            yield index, fields


def _pose_z(disk: Any, out: Any, sector_id: int, target: int,
            tiles: Mapping[int, Any] | None, row: dict[str, Any]) -> None:
    """Floor and ceiling at the `target` end of the z pair, sprites riding."""
    extra = record_extra(disk.sectors[sector_id]) or {}
    fields = record_fields(out.sectors[sector_id])
    for surface, off, on, ride_flag in (("floor", "off_floor_z", "on_floor_z", 8192),
                                         ("ceiling", "off_ceiling_z", "on_ceiling_z", 16384)):
        low, high = int(extra.get(off, 0) or 0), int(extra.get(on, 0) or 0)
        if low == high:
            continue
        old = int(fields[f"{surface}_z"])
        new = high if target else low
        if old == new:
            row["done"].append(f"{surface} already at {new}")
            continue
        fields[f"{surface}_z"] = new
        row["done"].append(f"{surface} z {old} -> {new} ({on if target else off})")
        row["changed"] = True
        moved, undecided = [], []
        for index, sprite in _sprites_in(out, sector_id):
            cstat = int(sprite["cstat"])
            if cstat & ride_flag:
                sprite["z"] = int(sprite["z"]) + new - old
                moved.append(index)
            elif surface == "floor" and not cstat & 48:
                frames, _view, yofs = _frames(tiles, int(sprite["picnum"]))
                if frames is None:
                    undecided.append(index)
                    continue
                # GetSpriteExtents, db.h:325-335
                height = int(tiles[int(sprite["picnum"])].height)
                center = height // 2 + int(yofs)
                bottom = int(sprite["z"]) + (int(sprite["y_repeat"]) << 2) * (height - center)
                if old <= bottom:
                    sprite["z"] = int(sprite["z"]) + new - old
                    moved.append(index)
        if moved:
            row["done"].append(f"sprites {moved} ride the {surface} "
                               "(triggers.cpp:1044-1062 / :1090-1099)")
        if undecided:
            row["undecided"].append(f"sprites {undecided} may ride the floor; no ART "
                                    "to size them (GetSpriteExtents), left where they are")


def _place(travel: Any, point: tuple[float, float], sign: float, busy: float,
           pivot: tuple[float, float]) -> tuple[float, float]:
    """`TranslateSector`'s move of one sprite base point (triggers.cpp:944-963)."""
    vc = travel.a6 + (travel.a9 - travel.a6) * busy
    v8 = travel.a7 + (travel.a10 - travel.a7) * busy
    vbp = travel.a8 + (travel.a11 - travel.a8) * busy
    moved = rotate_about(point, round(sign * vbp), pivot) if vbp else point
    return (moved[0] + sign * (vc - travel.a4), moved[1] + sign * (v8 - travel.a5))


def _pose_sweep(disk: Any, out: Any, sector_id: int, target: int,
                row: dict[str, Any]) -> None:
    """Every vertex `TranslateSector` drags, at the `target` end of the travel."""
    try:
        swept = closure_sweep(disk, sector_id, steps=1)
        travel = blood_travel(disk, sector_id)
    except ValueError as exc:
        row["not_posed"].append(f"the sweep cannot be read: {exc}")
        return
    rest = int(travel.rest)
    step = 0 if target == rest else -1
    moved = []
    for wall_id, (x, y) in swept.positions[step].items():
        fields = record_fields(out.walls[wall_id])
        nx, ny = int(round(x)), int(round(y))
        if (int(fields["x"]), int(fields["y"])) != (nx, ny):
            row.setdefault("where", []).append([int(fields["x"]), int(fields["y"])])
            row["where"].append([nx, ny])
            fields["x"], fields["y"] = nx, ny
            moved.append(wall_id)
    if moved:
        row["changed"] = True
        row["done"].append(f"{len(moved)} wall vertices dragged to busy "
                           f"{swept.busy[step]:g} (motion_sim.closure_sweep)")
    else:
        row["done"].append(f"walls already at busy {swept.busy[step]:g}")
    busy = float(swept.busy[step])
    turned = travel.a11 - travel.a8
    sprites_moved = []
    for index, sprite in _sprites_in(disk, sector_id):
        cstat = int(sprite["cstat"])
        if not cstat & (8192 | 16384):
            continue
        sign = 1.0 if cstat & 8192 else -1.0
        drawn = (float(sprite["x"]), float(sprite["y"]))
        # Vanilla turns a reverse-moving sprite about (a4, a4), not (a4, a5):
        # `sprDy = a4` outside modern maps, triggers.cpp:874-877.
        pivot = (travel.a4, travel.a5) if sign > 0 else (travel.a4, travel.a4)
        if sign < 0 and (travel.a8 or travel.a11):
            row["undecided"].append(f"sprite {index}: reverse-moving and turning; vanilla's "
                                    "(a4, a4) pivot assumed, a modern map uses (a4, a5)")
        base = _place(travel, drawn, sign, -1.0, pivot)       # the trInit rebase
        point = _place(travel, base, sign, busy, pivot)
        target_sprite = record_fields(out.sprites[index])
        target_sprite["x"], target_sprite["y"] = int(round(point[0])), int(round(point[1]))
        # ang changes by sign * (a11 - a8) * (busy - 1) from the drawn one:
        # the rebase turns it back a travel, the move forward to `busy`.
        target_sprite["angle"] = (int(sprite["angle"])
                                  + int(round(sign * turned * (busy - 1)))) & 2047
        sprites_moved.append(index)
    if sprites_moved:
        row["changed"] = True
        row["done"].append(f"sprites {sprites_moved} carried (cstat 8192/16384, "
                           "triggers.cpp:944-963)")
    extra = record_extra(disk.sectors[sector_id]) or {}
    if int(extra.get("drag", 0) or 0):
        row["undecided"].append("Drag is set: sprites standing on the floor are carried in "
                                "game (triggers.cpp:964-979); they are not moved here")


def _pose_switch(disk: Any, out: Any, sprite_id: int, target: int,
                 tiles: Mapping[int, Any] | None, row: dict[str, Any]) -> None:
    fields = record_fields(disk.sprites[sprite_id])
    saved = int(fields["picnum"])
    if int(fields["cstat"]) & INVISIBLE or not int(fields["x_repeat"]) or not int(fields["y_repeat"]):
        row["done"].append("draws nothing in either state (invisible or zero repeat)")
        return
    frames, view, _yofs = _frames(tiles, saved)
    if view is not None and view != 0:
        row["not_posed"].append(f"tile {saved} has picanm view type {view}; only view "
                                "type 0 shows a switch's state (view.cpp:2724)")
        return
    step = (frames if frames is not None else 0) + 1
    shown = saved + (step if target else 0)
    record_fields(out.sprites[sprite_id])["picnum"] = shown
    row["where"] = [[int(fields["x"]), int(fields["y"])]]
    if shown != saved:
        row["changed"] = True
    row["done"].append(
        f"drawn as tile {shown} (state {target}: picnum + picanm.num + 1 = {saved}+{step} "
        f"when set, view.cpp:2737 and :2822-2826); the observer reads no XSPRITE "
        "(obs_main.c:369), so picnum was moved, not state")
    if frames is None:
        row["undecided"].append("no ART: view type and picanm.num not checked, "
                                "assumed 0 and 0")


def _pose(disk: Any, chain: Mapping[str, Any], end: str,
          tiles: Mapping[int, Any] | None) -> tuple[Any, dict[str, Any]]:
    out = copy.deepcopy(disk)
    rows = []
    for item in _plan(disk, chain):
        before, after = item["state"]
        target = after if end == "other" else before
        row = dict(item, done=[], not_posed=[], undecided=[], changed=False)
        kind, index, type_id = item["kind"], item["index"], item["type_id"]
        if item["messages"] > 1:
            row["undecided"].append(f"reached by {item['messages']} messages of this "
                                    "chain; posed after the first only")
        if item.get("silent"):
            row["not_posed"].append(item["silent"])
            rows.append(row)
            continue
        if item.get("arrives"):
            row["done"].append(f"message {item['arrives']}")
        if item.get("gate"):
            row["undecided"].append(
                item["gate"] + "; posed anyway, but the message may never arrive")
        if kind == "engine":
            row["not_posed"].append(f"the engine's channel {item['type']}: what it does "
                                    "(a secret counted, a level ended, a message shown) "
                                    "is not a picture of the map")
        elif kind == "wall":
            row["not_posed"].append("a wall's state change is not posed (a switch wall's "
                                    "picture, a gib wall) -- not transcribed here")
        elif target is None:
            row["not_posed"].append(f"no state to show: {item['why_state']}")
        elif kind == "sector":
            sector_name = SECTOR_TYPES.get(type_id, {}).get("name", str(type_id))
            if type_id in Z_TYPES or type_id in SWEPT_TYPES:
                row["where"] = [_centroid(disk, index)]
                if type_id in SWEPT_TYPES:
                    _pose_sweep(disk, out, index, target, row)
                _pose_z(disk, out, index, target, tiles, row)
                if not row["done"] and not row["not_posed"]:
                    row["done"].append("its z pair does not travel")
            else:
                row["not_posed"].append(f"{sector_name} does not move on a state")
        elif kind == "sprite":
            category = SPRITE_TYPES.get(type_id, {}).get("category")
            fields = record_fields(disk.sprites[index])
            if type_id in SWITCH_TYPES:
                _pose_switch(disk, out, index, target, tiles, row)
            elif (item["role"] == "sender" and category == "thing"
                  and row.get("cause") == "destroyed"):
                row["where"] = [[int(fields["x"]), int(fields["y"])]]
                if end == "other":
                    record_fields(out.sprites[index])["cstat"] = int(fields["cstat"]) | INVISIBLE
                    row["changed"] = True
                    row["done"].append("hidden (cstat 32768): destroyed, it is freed "
                                       "(triggers.cpp:385-392 / actor.cpp:3513)")
                    row["not_posed"].append("the gib, debris or explosion it leaves is "
                                            "not drawn")
                else:
                    row["done"].append("standing, as at load")
            else:
                row["not_posed"].append(
                    f"{item['type']} ({category or 'unknown category'}): what it does is "
                    "an effect over time (a sound, an explosion, a spawn, a light) or a "
                    "state with no picture of its own")
        if item.get("wait") and end == "other" and row["changed"]:
            row["undecided"].append(f"wait_time {item['wait']}: returns on its own "
                                    f"after {item['wait'] / 10:g} s")
        rows.append(row)
    report = {
        "root": chain["root"], "cause": list(chain.get("cause", [])),
        "end": "other state" if end == "other" else "rest (as at load)",
        "objects": rows,
        "posed": [r["object"] for r in rows if r["changed"]],
        "not_posed": [{"object": r["object"], "type": r["type"], "why": r["not_posed"]}
                      for r in rows if r["not_posed"]],
        "observer": "xmapedit-observe draws one static state and reads no XSPRITE "
                    "(obs_main.c:369), so a switch's state picture is posed by picnum",
        "not_modelled": list(NOT_MODELLED),
        "art": tiles is not None,
    }
    return out, report


def posed(disk: Any, chain: Mapping[str, Any], *,
          tiles: Mapping[int, Any] | None = None) -> tuple[Any, dict[str, Any]]:
    """A deep copy with everything `chain` answers in its OTHER state, and the report.

    `tiles` (`bloodmap.art.read_art_directory`) lets a switch's second picture
    and a riding sprite's extent be read from ART; without it both are
    assumed and the report says so. The input is never changed.
    """
    return _pose(disk, chain, "other", tiles)


def rested(disk: Any, chain: Mapping[str, Any], *,
           tiles: Mapping[int, Any] | None = None) -> tuple[Any, dict[str, Any]]:
    """A deep copy with the same objects as the game shows them at load.

    The "before" of a before/after pair. It differs from the saved map where
    the engine moves a thing at load (a slide's `trInit` rebase, a switch
    saved at state 1); the report's `posed` lists those objects.
    """
    return _pose(disk, chain, "rest", tiles)


def chain_of(chains: list[Mapping[str, Any]], root: str) -> Mapping[str, Any]:
    """The chain a sender starts, by its name ("sprite 51")."""
    for chain in chains:
        if chain["root"] == root:
            return chain
    raise KeyError(f"no chain starts at {root!r}")
