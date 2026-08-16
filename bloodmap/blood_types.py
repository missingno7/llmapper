"""Source-backed Blood object-type names.

Numeric sector/wall/sprite types are not semantics by themselves. This catalog
maps those integers to NBlood names so an LLM can read `kMarkerMPStart` instead
of `type 2`, while unknown IDs stay unknown.

Evidence is the NBlood headers and the Blood map editor type list. Runtime
behavior of a named type is not simulated here.
"""

from __future__ import annotations

from typing import Any


SCHEMA = "llmapper.blood-types"
SCHEMA_VERSION = 1

_COMMON = "NBlood source/blood/src/common_game.h"
_MAPEDIT = "NBlood source/blood/src/mapedit.cpp TextList tSpriteType/tSectType/tWallType"
_EVENTQ = "NBlood source/blood/src/eventq.h"
_ASOUND = "NBlood source/blood/src/asound.cpp kStatAmbience / ambInit"


def _entry(name: str, category: str, provenance: str, *, notes: str | None = None) -> dict[str, Any]:
    payload = {"name": name, "category": category, "provenance": provenance, "known": True}
    if notes:
        payload["notes"] = notes
    return payload


SPRITE_TYPES: dict[int, dict[str, Any]] = {
    0: _entry("Decoration", "decoration", _MAPEDIT),
    1: _entry("kMarkerSPStart", "start", _COMMON),
    2: _entry("kMarkerMPStart", "start", _COMMON),
    3: _entry("kMarkerOff", "marker", _COMMON),
    4: _entry("kMarkerOn", "marker", _COMMON),
    5: _entry("kMarkerAxis", "marker", _COMMON),
    6: _entry("kMarkerLowLink", "marker", _COMMON),
    7: _entry("kMarkerUpLink", "marker", _COMMON),
    8: _entry("kMarkerWarpDest", "marker", _COMMON),
    9: _entry("kMarkerUpWater", "marker", _COMMON),
    10: _entry("kMarkerLowWater", "marker", _COMMON),
    11: _entry("kMarkerUpStack", "marker", _COMMON),
    12: _entry("kMarkerLowStack", "marker", _COMMON),
    13: _entry("kMarkerUpGoo", "marker", _COMMON),
    14: _entry("kMarkerLowGoo", "marker", _COMMON),
    15: _entry("kMarkerPath", "marker", _COMMON),
    18: _entry("kMarkerDudeSpawn", "marker", _COMMON),
    19: _entry("kMarkerEarthQuake", "marker", _COMMON),
    20: _entry("kSwitchToggle", "switch", _COMMON),
    21: _entry("kSwitchOneWay", "switch", _COMMON),
    22: _entry("kSwitchCombo", "switch", _COMMON),
    23: _entry("kSwitchPadlock", "switch", _COMMON),
    30: _entry("kDecorationTorch", "decoration", _COMMON),
    32: _entry("kDecorationCandle", "decoration", _COMMON),
    40: _entry("kItemWeaponRandom", "weapon", _COMMON),
    41: _entry("kItemWeaponSawedoff", "weapon", _COMMON),
    42: _entry("kItemWeaponTommygun", "weapon", _COMMON),
    43: _entry("kItemWeaponFlarePistol", "weapon", _COMMON),
    44: _entry("kItemWeaponVoodooDoll", "weapon", _COMMON),
    45: _entry("kItemWeaponTeslaCannon", "weapon", _COMMON),
    46: _entry("kItemWeaponNapalmLauncher", "weapon", _COMMON),
    47: _entry("kItemWeaponPitchfork", "weapon", _COMMON),
    48: _entry("kItemWeaponSprayCan", "weapon", _COMMON),
    49: _entry("kItemWeaponTNT", "weapon", _COMMON),
    50: _entry("kItemWeaponLifeLeech", "weapon", _COMMON),
    60: _entry("kItemAmmoSprayCan", "ammo", _COMMON),
    62: _entry("kItemAmmoTNTBundle", "ammo", _COMMON),
    63: _entry("kItemAmmoTNTBox", "ammo", _COMMON),
    64: _entry("kItemAmmoProxBombBundle", "ammo", _COMMON),
    65: _entry("kItemAmmoRemoteBombBundle", "ammo", _COMMON),
    66: _entry("kItemAmmoTrappedSoul", "ammo", _COMMON),
    67: _entry("kItemAmmoSawedoffFew", "ammo", _COMMON),
    68: _entry("kItemAmmoSawedoffBox", "ammo", _COMMON),
    69: _entry("kItemAmmoTommygunFew", "ammo", _COMMON),
    70: _entry("kItemAmmoVoodooDoll", "ammo", _COMMON),
    72: _entry("kItemAmmoTommygunDrum", "ammo", _COMMON),
    73: _entry("kItemAmmoTeslaCharge", "ammo", _COMMON),
    76: _entry("kItemAmmoFlares", "ammo", _COMMON),
    79: _entry("kItemAmmoGasolineCan", "ammo", _COMMON),
    100: _entry("kItemKeySkull", "key", _COMMON),
    101: _entry("kItemKeyEye", "key", _COMMON),
    102: _entry("kItemKeyFire", "key", _COMMON),
    103: _entry("kItemKeyDagger", "key", _COMMON),
    104: _entry("kItemKeySpider", "key", _COMMON),
    105: _entry("kItemKeyMoon", "key", _COMMON),
    106: _entry("kItemKeyKey7", "key", _COMMON),
    107: _entry("kItemHealthDoctorBag", "health", _COMMON),
    108: _entry("kItemHealthMedPouch", "health", _COMMON),
    109: _entry("kItemHealthLifeEssense", "health", _COMMON),
    110: _entry("kItemHealthLifeSeed", "health", _COMMON),
    111: _entry("kItemHealthRedPotion", "health", _COMMON),
    112: _entry("kItemFeatherFall", "powerup", _COMMON),
    113: _entry("kItemShadowCloak", "powerup", _COMMON),
    114: _entry("kItemDeathMask", "powerup", _COMMON),
    115: _entry("kItemJumpBoots", "powerup", _COMMON),
    117: _entry("kItemTwoGuns", "powerup", _COMMON),
    118: _entry("kItemDivingSuit", "powerup", _COMMON),
    119: _entry("kItemGasMask", "powerup", _COMMON),
    121: _entry("kItemCrystalBall", "powerup", _COMMON),
    124: _entry("kItemReflectShots", "powerup", _COMMON),
    125: _entry("kItemBeastVision", "powerup", _COMMON),
    128: _entry("kItemShroomDelirium", "powerup", _COMMON),
    139: _entry("kItemArmorAsbest", "armor", _COMMON),
    140: _entry("kItemArmorBasic", "armor", _COMMON),
    141: _entry("kItemArmorBody", "armor", _COMMON),
    142: _entry("kItemArmorFire", "armor", _COMMON),
    143: _entry("kItemArmorSpirit", "armor", _COMMON),
    144: _entry("kItemArmorSuper", "armor", _COMMON),
    145: _entry("kItemFlagABase", "flag", _COMMON),
    146: _entry("kItemFlagBBase", "flag", _COMMON),
    147: _entry("kItemFlagA", "flag", _COMMON),
    148: _entry("kItemFlagB", "flag", _COMMON),
    400: _entry("kThingTNTBarrel", "thing", _COMMON),
    401: _entry("kThingArmedProxBomb", "thing", _COMMON),
    402: _entry("kThingArmedRemoteBomb", "thing", _COMMON),
    405: _entry("kThingCrateFace", "thing", _COMMON),
    406: _entry("kThingGlassWindow", "thing", _COMMON),
    407: _entry("kThingFluorescent", "thing", _COMMON),
    408: _entry("kThingWallCrack", "thing", _COMMON),
    409: _entry("Wood Beam", "thing", _MAPEDIT),
    410: _entry("kThingSpiderWeb", "thing", _COMMON),
    411: _entry("kThingMetalGrate", "thing", _COMMON),
    412: _entry("kThingFlammableTree", "thing", _COMMON),
    414: _entry("kThingFallingRock", "thing", _COMMON),
    415: _entry("kThingKickablePail", "thing", _COMMON),
    416: _entry("kThingObjectGib", "thing", _COMMON),
    417: _entry("kThingObjectExplode", "thing", _COMMON),
    423: _entry("kThingDripWater", "thing", _COMMON),
    424: _entry("kThingDripBlood", "thing", _COMMON),
    700: _entry("kGenTrigger", "generator", _COMMON),
    701: _entry("kGenDripWater", "generator", _COMMON),
    702: _entry("kGenDripBlood", "generator", _COMMON),
    703: _entry("kGenMissileFireball", "generator", _COMMON),
    704: _entry("kGenMissileEctoSkull", "generator", _COMMON),
    705: _entry("kGenDart", "generator", _COMMON),
    706: _entry("kGenBubble", "generator", _COMMON),
    707: _entry("kGenBubbleMulti", "generator", _COMMON),
    708: _entry("kGenSound", "sound", _COMMON),
    709: _entry("kSoundSector", "sound", _COMMON),
    710: _entry(
        "Ambient SFX",
        "sound",
        f"{_MAPEDIT}; {_ASOUND}",
        notes=(
            "Not a named constant in common_game.h (gap between kSoundSector=709 and "
            "kSoundPlayer=711). Map editor places type 710 on kStatAmbience=12. "
            "asound.cpp ambInit uses XSPRITE data1/data2 as distance range, data3 as SFX id."
        ),
    ),
    711: _entry("kSoundPlayer", "sound", _COMMON),
}

SECTOR_TYPES: dict[int, dict[str, Any]] = {
    0: _entry("Normal", "plain", _MAPEDIT),
    600: _entry("kSectorZMotion", "motion", _COMMON),
    602: _entry("kSectorZMotionSprite", "motion", _COMMON),
    603: _entry("Warp", "teleport", _MAPEDIT),
    604: _entry("kSectorTeleport", "teleport", _COMMON),
    612: _entry("kSectorPath", "motion", _COMMON),
    613: _entry("kSectorRotateStep", "motion", _COMMON),
    614: _entry("kSectorSlideMarked", "motion", _COMMON),
    615: _entry("kSectorRotateMarked", "motion", _COMMON),
    616: _entry("kSectorSlide", "motion", _COMMON),
    617: _entry("kSectorRotate", "motion", _COMMON),
    618: _entry("kSectorDamage", "hazard", _COMMON),
    619: _entry("kSectorCounter", "counter", _COMMON),
}

WALL_TYPES: dict[int, dict[str, Any]] = {
    0: _entry("Normal", "plain", _MAPEDIT),
    20: _entry("kSwitchToggle", "switch", _MAPEDIT),
    21: _entry("kSwitchOneWay", "switch", _MAPEDIT),
    500: _entry("Wall Link", "link", _MAPEDIT),
    501: _entry("kWallStack", "stack", _COMMON),
    511: _entry("kWallGib", "destructible", _COMMON),
}

COMMANDS: dict[int, dict[str, Any]] = {
    0: _entry("kCmdOff", "command", _EVENTQ),
    1: _entry("kCmdOn", "command", _EVENTQ),
    2: _entry("kCmdState", "command", _EVENTQ),
    3: _entry("kCmdToggle", "command", _EVENTQ),
    4: _entry("kCmdNotState", "command", _EVENTQ),
    5: _entry("kCmdLink", "command", _EVENTQ),
    6: _entry("kCmdLock", "command", _EVENTQ),
    7: _entry("kCmdUnlock", "command", _EVENTQ),
    8: _entry("kCmdToggleLock", "command", _EVENTQ),
    9: _entry("kCmdStopOff", "command", _EVENTQ),
    10: _entry("kCmdStopOn", "command", _EVENTQ),
    11: _entry("kCmdStopNext", "command", _EVENTQ),
}

RESERVED_CHANNELS: dict[int, dict[str, Any]] = {
    0: _entry("kChannelZero", "reserved", _EVENTQ),
    1: _entry("kChannelSetTotalSecrets", "reserved", _EVENTQ),
    2: _entry("kChannelSecretFound", "reserved", _EVENTQ),
    3: _entry("kChannelTextOver", "reserved", _EVENTQ),
    4: _entry("kChannelLevelExitNormal", "reserved", _EVENTQ),
    5: _entry("kChannelLevelExitSecret", "reserved", _EVENTQ),
    7: _entry("kChannelLevelStart", "reserved", _EVENTQ),
    8: _entry("kChannelLevelStartMatch", "reserved", _EVENTQ, notes="DM and teams"),
    9: _entry("kChannelLevelStartCoop", "reserved", _EVENTQ),
    10: _entry("kChannelLevelStartTeamsOnly", "reserved", _EVENTQ),
    80: _entry("kChannelTeamAFlagCaptured", "reserved", _EVENTQ),
    81: _entry("kChannelTeamBFlagCaptured", "reserved", _EVENTQ),
}

_CATALOGS = {
    "sprite": SPRITE_TYPES,
    "sector": SECTOR_TYPES,
    "wall": WALL_TYPES,
    "command": COMMANDS,
    "channel": RESERVED_CHANNELS,
}


def classify(kind: str, type_id: int) -> dict[str, Any]:
    """Return a named catalog entry, or an explicit unknown record."""
    catalog = _CATALOGS.get(kind)
    if catalog is None:
        raise ValueError(f"unsupported Blood type kind {kind!r}")
    identifier = int(type_id)
    if kind == "channel" and identifier >= 100:
        return {
            "kind": kind,
            "type_id": identifier,
            "name": "kChannelUser",
            "category": "user",
            "known": True,
            "provenance": _EVENTQ,
            "notes": "User TX/RX channel; kChannelUser=100 .. kChannelUserMax=1024",
        }
    found = catalog.get(identifier)
    if found is None and kind == "sprite" and 201 <= identifier <= 253:
        found = _entry(f"kDude ({identifier})", "dude", _COMMON)
    if found is None:
        return {
            "kind": kind,
            "type_id": identifier,
            "name": None,
            "category": "unknown",
            "known": False,
            "provenance": None,
            "notes": "Not present in the NBlood type catalog used by llmapper",
        }
    return {"kind": kind, "type_id": identifier, **found}


def command_name(command: int) -> str:
    record = classify("command", command)
    return record["name"] or f"command:{command}"
