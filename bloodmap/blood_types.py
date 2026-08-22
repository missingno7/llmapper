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
#: Something the corpus contains that the engine has no case for.  Named
#: here so it stops reading as an unknown, not because it does anything.
_MEASURED = "measured in the campaign; no case in NBlood"


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

    # Dudes, traps and the rest of the thing range.  These were missing
    # entirely, which mattered: 4,400 of the campaign's typed sprites are
    # enemies and kTrapExploder alone appears 1,085 times in 31 maps.
    201: _entry('kDudeCultistTommy', 'dude', _COMMON),
    202: _entry('kDudeCultistShotgun', 'dude', _COMMON),
    203: _entry('kDudeZombieAxeNormal', 'dude', _COMMON),
    204: _entry('kDudeZombieButcher', 'dude', _COMMON),
    205: _entry('kDudeZombieAxeBuried', 'dude', _COMMON),
    206: _entry('kDudeGargoyleFlesh', 'dude', _COMMON),
    207: _entry('kDudeGargoyleStone', 'dude', _COMMON),
    208: _entry('kDudeGargoyleStatueFlesh', 'dude', _COMMON),
    209: _entry('kDudeGargoyleStatueStone', 'dude', _COMMON),
    210: _entry('kDudePhantasm', 'dude', _COMMON),
    211: _entry('kDudeHellHound', 'dude', _COMMON),
    212: _entry('kDudeHand', 'dude', _COMMON),
    213: _entry('kDudeSpiderBrown', 'dude', _COMMON),
    214: _entry('kDudeSpiderRed', 'dude', _COMMON),
    215: _entry('kDudeSpiderBlack', 'dude', _COMMON),
    216: _entry('kDudeSpiderMother', 'dude', _COMMON),
    217: _entry('kDudeGillBeast', 'dude', _COMMON),
    218: _entry('kDudeBoneEel', 'dude', _COMMON),
    219: _entry('kDudeBat', 'dude', _COMMON),
    220: _entry('kDudeRat', 'dude', _COMMON),
    221: _entry('kDudePodGreen', 'dude', _COMMON),
    222: _entry('kDudeTentacleGreen', 'dude', _COMMON),
    223: _entry('kDudePodFire', 'dude', _COMMON),
    224: _entry('kDudeTentacleFire', 'dude', _COMMON),
    225: _entry('kDudePodMother', 'dude', _COMMON),
    226: _entry('kDudeTentacleMother', 'dude', _COMMON),
    227: _entry('kDudeCerberusTwoHead', 'dude', _COMMON),
    228: _entry('kDudeCerberusOneHead', 'dude', _COMMON),
    229: _entry('kDudeTchernobog', 'dude', _COMMON),
    230: _entry('kDudeCultistTommyProne', 'dude', _COMMON),
    231: _entry('kDudePlayer1', 'dude', _COMMON),
    232: _entry('kDudePlayer2', 'dude', _COMMON),
    233: _entry('kDudePlayer3', 'dude', _COMMON),
    234: _entry('kDudePlayer4', 'dude', _COMMON),
    235: _entry('kDudePlayer5', 'dude', _COMMON),
    236: _entry('kDudePlayer6', 'dude', _COMMON),
    237: _entry('kDudePlayer7', 'dude', _COMMON),
    238: _entry('kDudePlayer8', 'dude', _COMMON),
    239: _entry('kDudeBurningInnocent', 'dude', _COMMON),
    240: _entry('kDudeBurningCultist', 'dude', _COMMON),
    241: _entry('kDudeBurningZombieAxe', 'dude', _COMMON),
    242: _entry('kDudeBurningZombieButcher', 'dude', _COMMON),
    244: _entry('kDudeZombieAxeLaying', 'dude', _COMMON),
    245: _entry('kDudeInnocent', 'dude', _COMMON),
    246: _entry('kDudeCultistShotgunProne', 'dude', _COMMON),
    247: _entry('kDudeCultistTesla', 'dude', _COMMON),
    248: _entry('kDudeCultistTNT', 'dude', _COMMON),
    249: _entry('kDudeCultistBeast', 'dude', _COMMON),
    250: _entry('kDudeTinyCaleb', 'dude', _COMMON),
    251: _entry('kDudeBeast', 'dude', _COMMON),
    252: _entry('kDudeBurningTinyCaleb', 'dude', _COMMON),
    253: _entry('kDudeBurningBeast', 'dude', _COMMON),
    413: _entry('kTrapMachinegun', 'trap', _COMMON),
    418: _entry('kThingArmedTNTStick', 'thing', _COMMON),
    419: _entry('kThingArmedTNTBundle', 'thing', _COMMON),
    420: _entry('kThingArmedSpray', 'thing', _COMMON),
    421: _entry('kThingBone', 'thing', _COMMON),
    425: _entry('kThingBloodBits', 'thing', _COMMON),
    426: _entry('kThingBloodChunks', 'thing', _COMMON),
    427: _entry('kThingZombieHead', 'thing', _COMMON),
    428: _entry('kThingNapalmBall', 'thing', _COMMON),
    429: _entry('kThingPodFireBall', 'thing', _COMMON),
    430: _entry('kThingPodGreenBall', 'thing', _COMMON),
    431: _entry('kThingDroppedLifeLeech', 'thing', _COMMON),
    432: _entry('kThingVoodooHead', 'thing', _COMMON),
    452: _entry('kTrapFlame', 'trap', _COMMON),
    454: _entry('kTrapSawCircular', 'trap', _COMMON),
    456: _entry('kTrapZapSwitchable', 'trap', _COMMON),
    459: _entry('kTrapExploder', 'trap', _COMMON),
    # Present in the campaign, named nowhere in NBlood and switched on nowhere
    # either: no case in triggers.cpp, actor.cpp or the editor type lists.  They
    # are recorded because they are in the data, and marked inert because the
    # engine does nothing with them.  Fourteen sprites in the whole campaign.
    136: _entry("unhandled", "anomaly", _MEASURED,
                notes="5 sprites; a gap in the item range, no engine case"),
    455: _entry("unhandled", "anomaly", _MEASURED,
                notes="6 sprites; a gap in the trap range, no engine case"),
    457: _entry("unhandled", "anomaly", _MEASURED,
                notes="2 sprites; a gap in the trap range, no engine case"),
    458: _entry("unhandled", "anomaly", _MEASURED,
                notes="1 sprite; a gap in the trap range, no engine case"),
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
    607: _entry(
        "unhandled",
        "anomaly",
        "measured in the campaign; absent from common_game.h and from "
        "mapedit.cpp tSectType",
        notes=(
            "Three sectors in the campaign carry type 607. The engine has no case "
            "for it in trMessageSector, so it behaves as a plain sector that "
            "happens to own an XSECTOR. Recorded because it is in the data, not "
            "because it does anything."
        ),
    ),
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
    12: _entry("kCmdCounterSector", "command", _EVENTQ),
    20: _entry("kCmdCallback", "command", _EVENTQ),
    21: _entry("kCmdRepeat", "command", _EVENTQ),
    # 30..52 are the *cause* of an event rather than an instruction: the engine
    # sends them when a player pushes, shoots, walks into or looks at something.
    30: _entry("kCmdSpritePush", "cause", _EVENTQ),
    31: _entry("kCmdSpriteImpact", "cause", _EVENTQ),
    32: _entry("kCmdSpritePickup", "cause", _EVENTQ),
    33: _entry("kCmdSpriteTouch", "cause", _EVENTQ),
    34: _entry("kCmdSpriteSight", "cause", _EVENTQ),
    35: _entry("kCmdSpriteProximity", "cause", _EVENTQ),
    36: _entry("kCmdSpriteExplode", "cause", _EVENTQ),
    40: _entry("kCmdSectorPush", "cause", _EVENTQ),
    41: _entry("kCmdSectorImpact", "cause", _EVENTQ),
    42: _entry("kCmdSectorEnter", "cause", _EVENTQ),
    43: _entry("kCmdSectorExit", "cause", _EVENTQ),
    50: _entry("kCmdWallPush", "cause", _EVENTQ),
    51: _entry("kCmdWallImpact", "cause", _EVENTQ),
    52: _entry("kCmdWallTouch", "cause", _EVENTQ),
}

#: ``kCmdNumberic``.  Every command from 64 upward carries the number
#: ``command - 64`` rather than an instruction, and what the number means is
#: decided by the channel it is sent on.  843 objects in the campaign use this
#: and all 43 maps contain at least one.
NUMERIC_COMMAND_BASE = 64
NUMERIC_COMMAND_MAX = 255

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
    6: _entry("kChannelModernEndLevelCustom", "reserved", _EVENTQ,
              notes="gModernMap only; the numeric command is the level to end to"),
    15: _entry("kChannelPlayerDeathTeamA", "reserved", _EVENTQ),
    16: _entry("kChannelPlayerDeathTeamB", "reserved", _EVENTQ),
    17: _entry("kChannelLevelStartNBLOOD", "reserved", _EVENTQ, notes="NBlood only, gModernMap"),
    18: _entry("kChannelLevelStartRAZE", "reserved", _EVENTQ, notes="Raze only, gModernMap"),
    29: _entry("kChannelAllPlayers", "reserved", _EVENTQ),
    30: _entry("kChannelPlayer0", "reserved", _EVENTQ, notes="30..37 are the eight player slots"),
    50: _entry("kChannelEventCauser", "reserved", _EVENTQ),
    60: _entry("kChannelMapModernRev1", "reserved", _EVENTQ),
    61: _entry("kChannelMapModernRev2", "reserved", _EVENTQ),
    90: _entry("kChannelRemoteBomb0", "reserved", _EVENTQ, notes="90..97 are the remote bomb slots"),
    100: _entry("kChannelUser", "reserved", _EVENTQ,
                notes="100..1023 is the range a level may use for its own wiring"),
}

#: What ``command - 64`` means, per channel.  The number is meaningless without
#: the channel, which is why a command table alone cannot read a Blood map.
NUMERIC_COMMAND_MEANING: dict[int, dict[str, str]] = {
    1: {"call": "levelSetupSecret(n)",
        "means": "the level has n secrets in total",
        "provenance": "NBlood source/blood/src/eventq.cpp:394, levels.cpp:160"},
    2: {"call": "levelTriggerSecret(n)",
        "means": "secret number n has just been found",
        "provenance": "NBlood source/blood/src/eventq.cpp:398, levels.cpp:165"},
    3: {"call": "trTextOver(n)",
        "means": "show level message n",
        "provenance": "NBlood source/blood/src/eventq.cpp:377, triggers.cpp:2344"},
    6: {"call": "levelEndLevelCustom(n)",
        "means": "end the level to level n; gModernMap only",
        "provenance": "NBlood source/blood/src/eventq.cpp:389"},
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
    if kind == "command" and identifier >= NUMERIC_COMMAND_BASE:
        # Not an instruction: the number itself is the payload, and the channel
        # it travels on decides what the number means.
        value = identifier - NUMERIC_COMMAND_BASE
        return {
            "kind": kind,
            "type_id": identifier,
            "name": f"kCmdNumberic + {value}",
            "category": "number",
            "known": identifier <= NUMERIC_COMMAND_MAX,
            "provenance": _EVENTQ,
            "value": value,
            "notes": ("carries the number %d; see NUMERIC_COMMAND_MEANING for what "
                      "that means on each reserved channel" % value),
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
