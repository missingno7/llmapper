"""What a control looks like, and how high it hangs.

Blood says what a control *is* with its art and its height together, and the two
have to agree. A switch you press sits at eye level and wears a lever or a
button; a switch you shoot sits well above that and wears a different tile
entirely. Swap them and the player either cannot reach a switch they are
supposed to press, or shoots at a lever that only responds to a hand.

What the campaign does
----------------------

``knowledge/blood/design/switches-v1.json``, all 43 maps, every sprite of type
20-23 (``kSwitchToggle``, ``kSwitchOneWay``, ``kSwitchCombo``,
``kSwitchPadlock`` -- NBlood ``common_game.h:231``):

===============  =====  ====================================  ===================
worked by            n  height above floor (q1/median/q3)     commonest tiles
===============  =====  ====================================  ===================
pressed            453  0.60 / **0.79** / 0.79                1070, 1046, 1078
shot                63  1.00 / **1.93** / 3.26                2290, 710, 1165
either              14  0.79 / 0.81 / 0.84                    1046
===============  =====  ====================================  ===================

The player's eye is at **0.83** standing humans, so a pressed switch sits at eye
level or a little under -- Blood's use is a hitscan from the eye, so "in reach"
means "in the line you are already looking along". A shot switch is at 1.93,
more than twice as high, and the tile families barely overlap.

The exit
--------

``kChannelLevelExitNormal = 4`` (NBlood ``eventq.h:30``) ends the level, and 5
is the secret exit. Of the campaign's 50 exit switches, **41 wear tile 318** --
a downward blade emblem, 78x44 -- and that tile appears only 5 times anywhere
else in the whole campaign. It is as close to a reserved word as Blood's art
gets, and 5 of the 6 secret exits use it too. An exit wearing the ordinary lever
tile 1070 (274 uses elsewhere) tells the player nothing.
"""

from __future__ import annotations

from typing import Any

from .doors import MOTION_TYPES, Z_MOTION_TYPES
from .player_space import PLAYER_PROFILES

PLAYER_HEIGHT = PLAYER_PROFILES["blood"].standing_height
EYE_HEIGHT = PLAYER_PROFILES["blood"].eye_height

#: NBlood common_game.h:231-236
SWITCH_TYPES = {20: "toggle", 21: "one_way", 22: "combo", 23: "padlock"}

#: NBlood eventq.h:30-32
CHANNEL_EXIT = 4
CHANNEL_SECRET_EXIT = 5

#: The exit's own tile: 41 of 50 campaign exits, 5 uses anywhere else.
EXIT_TILE = 318

#: Levers and buttons, in campaign order of use. All are pressed.
PRESSED_TILES = (1070, 1046, 1078, 1074, 1076, 1048, 1072)

#: Panels and targets. All are shot.
SHOT_TILES = (2290, 710, 1165, 784, 1727, 483)

#: Where a pressed switch goes: the campaign median, just under the eye.
PRESSED_HEIGHT = 0.79

#: The ceiling on reach. The campaign's pressed switches reach p95 0.84 and the
#: eye is at 0.83; past this a hand cannot get to it.
PRESSED_LIMIT = 0.95

#: Where a shot switch goes, and the floor under it -- below this it is not
#: obviously a target and the player will try to press it.
SHOT_HEIGHT = 1.93
SHOT_FLOOR = 1.00


class SwitchError(ValueError):
    """A control the player could not work as built."""


def is_switch(sprite: Any) -> bool:
    return int(sprite.fields["type"]) in SWITCH_TYPES


def _extra(item: Any) -> dict:
    extra = getattr(item, "extra", None)
    if extra is None or not hasattr(extra, "fields"):
        return {}
    return extra.fields


def pressed_switch(*, tile: int = PRESSED_TILES[0], tx_id: int,
                   command: int = 3, toggle: bool = True) -> dict[str, Any]:
    """A switch worked by hand, at the campaign's own height and tile."""
    if tile in SHOT_TILES:
        raise SwitchError(
            "tile %d is a target the campaign shoots, not a lever it presses; "
            "use one of %s" % (tile, ", ".join(str(t) for t in PRESSED_TILES)))
    return {
        "type": 20 if toggle else 21,
        "picnum": int(tile), "cstat": 464,
        "x_repeat": 40, "y_repeat": 40, "shade": -8,
        "height_player_heights": PRESSED_HEIGHT,
        "behavior": {"tx_id": int(tx_id), "command": int(command),
                     "trigger_on": 1, "trigger_push": 1},
    }


def exit_switch(*, secret: bool = False) -> dict[str, Any]:
    """The switch that ends the level, wearing the tile that says so."""
    return {
        "type": 20, "picnum": EXIT_TILE, "cstat": 464,
        "x_repeat": 40, "y_repeat": 40, "shade": -8,
        "height_player_heights": PRESSED_HEIGHT,
        "behavior": {"tx_id": CHANNEL_SECRET_EXIT if secret else CHANNEL_EXIT,
                     "command": 1, "trigger_on": 1, "trigger_push": 1},
    }


def check(disk: Any) -> list[str]:
    """Controls this map builds that a player could not work.

    Three complaints, all measured against the campaign rather than asserted:
    a pressed switch out of reach, a shot switch wearing a pressed tile, and an
    exit that does not wear the exit's own tile.
    """
    complaints: list[str] = []
    for index, sprite in enumerate(disk.sprites):
        if not is_switch(sprite):
            continue
        fields = sprite.fields
        extra = _extra(sprite)
        sector = int(fields["sector"])
        if not 0 <= sector < len(disk.sectors):
            continue
        floor = int(disk.sectors[sector].fields["floor_z"])
        height = (floor - int(fields["z"])) / PLAYER_HEIGHT
        picnum = int(fields["picnum"])
        tx = int(extra.get("tx_id", 0) or 0)
        shot = bool(int(extra.get("trigger_impact", 0) or 0)
                    or int(extra.get("trigger_vector", 0) or 0))
        pushed = bool(int(extra.get("trigger_push", 0) or 0)
                      or int(extra.get("trigger_wall_push", 0) or 0))

        if pushed and not shot and height > PRESSED_LIMIT:
            complaints.append(
                "switch %d is %.2f humans up and is worked by hand; the eye is "
                "at %.2f and the campaign presses at %.2f"
                % (index, height, EYE_HEIGHT / PLAYER_HEIGHT, PRESSED_HEIGHT))
        if shot and not pushed and picnum in PRESSED_TILES:
            complaints.append(
                "switch %d is shot but wears lever tile %d; the campaign shoots "
                "%s" % (index, picnum, ", ".join(str(t) for t in SHOT_TILES[:3])))
        if tx in (CHANNEL_EXIT, CHANNEL_SECRET_EXIT) and picnum != EXIT_TILE:
            complaints.append(
                "the switch on channel %d ends the level but wears tile %d; "
                "41 of the campaign's 50 exits wear %d, which it uses almost "
                "nowhere else" % (tx, picnum, EXIT_TILE))
    return complaints


#: Build's "invisible" cstat bit. A sprite carrying it is in the map, is
#: pressable, and is not drawn.
INVISIBLE = 0x8000


def _commanded_sectors(disk: Any, tx_id: int) -> list[int]:
    """Which sectors listen on this channel."""
    if not tx_id:
        return []
    out = []
    for index, sector in enumerate(disk.sectors):
        extra = _extra(sector)
        if extra and int(extra.get("rx_id") or 0) == tx_id:
            out.append(index)
    return out


def switch_role(disk: Any, sprite_index: int) -> dict[str, Any] | None:
    """What one switch *does*, with nothing about where it is or how it looks.

    The feature set is deliberately narrow, and the narrowness is the
    experiment: the question is whether a concealed trigger commands a
    different **kind** of thing than an exposed one, so a feature that reads
    geometry, height, or tile identity would answer a different question and
    look like an answer to this one.
    """
    sprite = disk.sprites[sprite_index]
    if not is_switch(sprite):
        return None
    fields = sprite.fields
    extra = _extra(sprite) or {}
    tx_id = int(extra.get("tx_id") or 0)
    rx_id = int(extra.get("rx_id") or 0)
    commanded = _commanded_sectors(disk, tx_id)
    types = sorted({int(disk.sectors[index].fields["type"]) for index in commanded})
    return {
        "sprite": sprite_index,
        "hidden": bool(int(fields["cstat"]) & INVISIBLE),
        "switch_kind": SWITCH_TYPES.get(int(fields["type"]), "other"),
        # channel role
        "transmits": bool(tx_id),
        "listens": bool(rx_id),
        "relays": bool(tx_id and rx_id),
        "ends_the_level": tx_id in (CHANNEL_EXIT, CHANNEL_SECRET_EXIT),
        "reserved_channel": 0 < tx_id < 8,
        # what it commands
        "sectors_commanded": len(commanded),
        "commands_nothing_in_this_map": bool(tx_id) and not commanded,
        "commands_motion": any(t in MOTION_TYPES for t in types),
        "commands_z_motion": any(t in Z_MOTION_TYPES for t in types),
        "commands_more_than_one_kind": len(types) > 1,
        "commanded_types": types,
        # how it may be worked
        "one_way": int(fields["type"]) == 21,
        "keyed": bool(int(extra.get("key") or 0)),
        "once_only": bool(extra.get("trigger_once")),
    }


#: The features the contrast is scored on. Channel role and what the switch
#: commands -- never geometry, never the tile.
CONTRAST_FEATURES = (
    "transmits", "listens", "relays", "ends_the_level", "reserved_channel",
    "sectors_commanded", "commands_nothing_in_this_map", "commands_motion",
    "commands_z_motion", "commands_more_than_one_kind", "one_way", "keyed",
    "once_only",
)


def contrast_hidden_switches(
    *, directory: Any = None, population: str = "blood-campaign",
    view: str | None = None, examples: int = 8,
) -> dict[str, Any]:
    """Do concealed switches command a different kind of thing than open ones?

    Same discipline as `anchors.contrast_anchor_sets`: balanced accuracy
    rather than accuracy, a per-map transfer check so a mapper's habit cannot
    pass as a concept, and counterexamples preserved rather than pruned.
    """
    from .anchors import (
        DISCRIMINATOR_FLOOR, _counterexamples, _map_transfer, _separation,
    )
    from .format import read_map
    from .patterns import list_corpus_maps

    selected = list_corpus_maps(directory, population=population, view=view)
    if not selected:
        raise SwitchError(f"no maps for population={population!r}")

    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for item in selected:
        try:
            disk = read_map(item.path)
        except Exception as exc:
            skipped.append({"map": item.path.stem,
                            "reason": f"{type(exc).__name__}: {exc}"})
            continue
        for index in range(len(disk.sprites)):
            role = switch_role(disk, index)
            if role is None:
                continue
            rows.append({"map": item.path.stem,
                         "label": "hidden" if role["hidden"] else "visible",
                         **role})

    hidden = [row for row in rows if row["label"] == "hidden"]
    visible = [row for row in rows if row["label"] == "visible"]
    if not hidden or not visible:
        raise SwitchError(
            f"contrast needs both sides: {len(hidden)} hidden, "
            f"{len(visible)} visible")
    measured = [_separation(name, [row[name] for row in hidden],
                            [row[name] for row in visible])
                for name in CONTRAST_FEATURES]
    measured.sort(key=lambda item: -item.get("balanced_accuracy", 0))
    discriminating = [m for m in measured
                      if m.get("balanced_accuracy", 0) >= DISCRIMINATOR_FLOOR]
    best = discriminating[0] if discriminating else None
    return {
        "$schema": "llmapper.blood-hidden-switch-contrast",
        "schema_version": 1,
        "question": "does a concealed trigger command a different kind of "
                    "thing than an exposed one",
        "selection": {"population": population, "view": view,
                      "maps_searched": len(selected)},
        "counts": {
            "hidden": {"switches": len(hidden),
                       "maps": len({row["map"] for row in hidden})},
            "visible": {"switches": len(visible),
                        "maps": len({row["map"] for row in visible})},
        },
        "features_scored": list(CONTRAST_FEATURES),
        "discriminator_floor": DISCRIMINATOR_FLOOR,
        "discriminating": discriminating,
        "rejected": [m for m in measured
                     if m.get("balanced_accuracy", 0) < DISCRIMINATOR_FLOOR],
        "counterexamples": _counterexamples(best, hidden, visible, examples),
        "map_transfer": _map_transfer(best, hidden),
        "skipped": skipped,
        "rows": rows,
        "limitations": [
            "Every feature is channel role or what the switch commands. "
            "Nothing geometric is scored, so a separator that is really "
            "position or tile identity cannot hide as one of them -- and by "
            "the same token this cannot say whether hidden switches sit "
            "somewhere different.",
            "Balanced accuracy, not accuracy: the split is heavily imbalanced "
            "and a rule that never fires scores well on the raw rate.",
            "Thresholds are fitted on the rows they are scored on. These are "
            "separations observed, not a validated classifier.",
            "`commands_nothing_in_this_map` is a fact about the map, not "
            "about the switch: a channel with no listening sector may be "
            "commanding sprites, which this does not look at.",
        ],
    }
