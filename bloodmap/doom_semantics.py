"""Doom runtime mechanism inventory.

Linedef specials and sector types are taken from GZDoom
``wadsrc/static/xlat/base.txt`` and ``xlat/doom.txt``, which is what
``FLevelLocals::TranslateLineDef`` uses for classic Doom-format maps.

Only vanilla Doom / Doom II specials 1-141 (excluding Boom 78/85) are
promoted. Recognition returns semantic mechanisms with native linedef/sector
references; it does not emit Blood records.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

from .doom import (
    ML_TWOSIDED, NO_SIDE, DoomDiskMap, DoomLinedef, texture_label,
)
from .mechanisms import (
    Representability, SemanticConnection, SemanticLevel, SemanticMechanism,
    SemanticRegion,
)


# GZDoom xlat/defines.i
D_SLOW, D_FAST = 16, 64
F_SLOW, F_FAST = 8, 32
P_FAST, P_TURBO = 32, 64
VDOORWAIT, PLATWAIT = 150, 105
ST_SLOW, ST_TURBO = 2, 32

# Activation flags from xlat/defines.i: WALK=0, USE=2, SHOOT=6, MONWALK=4, REP=1, MONST=16
ACT_WALK, ACT_USE, ACT_SHOOT, ACT_MONWALK = "walk", "use", "shoot", "monster_walk"


@dataclass(frozen=True)
class LinedefSpecial:
    number: int
    activation: str
    repeatable: bool
    monsters: bool
    action: str
    kind: str
    fidelity: str
    speed: int | None = None
    wait: int | None = None
    key: str | None = None
    local_backsector: bool = False
    notes: str = ""


def _spec(
    number: int, flags: str, action: str, kind: str, *,
    fidelity: str = Representability.SEMANTIC.value,
    speed: int | None = None, wait: int | None = None, key: str | None = None,
    local: bool = False, notes: str = "",
) -> LinedefSpecial:
    parts = {item.strip() for item in flags.split("|") if item.strip() and item.strip() != "0"}
    if "USE" in parts:
        activation = ACT_USE
    elif "SHOOT" in parts:
        activation = ACT_SHOOT
    elif "MONWALK" in parts:
        activation = ACT_MONWALK
    else:
        activation = ACT_WALK
    return LinedefSpecial(
        number=number, activation=activation, repeatable="REP" in parts,
        monsters="MONST" in parts or "MONWALK" in parts, action=action, kind=kind,
        fidelity=fidelity, speed=speed, wait=wait, key=key, local_backsector=local, notes=notes,
    )


# Vanilla 1-141 from GZDoom xlat/base.txt. Boom 78/85 stay unclassified.
LINEDEF_SPECIALS: dict[int, LinedefSpecial] = {
    1: _spec(1, "USE|MONST|REP", "Door_Raise", "door", speed=D_SLOW, wait=VDOORWAIT, local=True),
    2: _spec(2, "WALK", "Door_Open", "door", speed=D_SLOW),
    3: _spec(3, "WALK", "Door_Close", "door", speed=D_SLOW),
    4: _spec(4, "WALK|MONST", "Door_Raise", "door", speed=D_SLOW, wait=VDOORWAIT),
    5: _spec(5, "WALK", "Floor_RaiseToLowestCeiling", "floor_move", speed=F_SLOW, fidelity=Representability.APPROXIMATE.value),
    6: _spec(6, "WALK", "Ceiling_CrushAndRaiseDist", "ceiling_move", fidelity=Representability.UNSUPPORTED.value, notes="crusher"),
    7: _spec(7, "USE", "Stairs_BuildUpDoom", "stair", speed=ST_SLOW, fidelity=Representability.APPROXIMATE.value),
    8: _spec(8, "WALK", "Stairs_BuildUpDoom", "stair", speed=ST_SLOW, fidelity=Representability.APPROXIMATE.value),
    9: _spec(9, "USE", "Floor_Donut", "floor_move", fidelity=Representability.UNSUPPORTED.value),
    10: _spec(10, "WALK|MONST", "Plat_DownWaitUpStayLip", "lift", speed=P_FAST, wait=PLATWAIT),
    11: _spec(11, "USE", "Exit_Normal", "exit", local=True),
    12: _spec(12, "WALK", "Light_MaxNeighbor", "light", fidelity=Representability.APPROXIMATE.value),
    13: _spec(13, "WALK", "Light_ChangeToValue", "light", fidelity=Representability.APPROXIMATE.value),
    16: _spec(16, "WALK", "Door_CloseWaitOpen", "door", speed=D_SLOW, wait=240, fidelity=Representability.APPROXIMATE.value),
    18: _spec(18, "USE", "Floor_RaiseToNearest", "floor_move", speed=F_SLOW, fidelity=Representability.APPROXIMATE.value),
    19: _spec(19, "WALK", "Floor_LowerToHighest", "floor_move", speed=F_SLOW, fidelity=Representability.APPROXIMATE.value),
    21: _spec(21, "USE", "Plat_DownWaitUpStayLip", "lift", speed=P_FAST, wait=PLATWAIT),
    23: _spec(23, "USE", "Floor_LowerToLowest", "floor_move", speed=F_SLOW, fidelity=Representability.APPROXIMATE.value),
    26: _spec(26, "USE|REP", "Door_LockedRaise", "key_gate", speed=D_SLOW, wait=VDOORWAIT, key="blue", local=True),
    27: _spec(27, "USE|REP", "Door_LockedRaise", "key_gate", speed=D_SLOW, wait=VDOORWAIT, key="yellow", local=True),
    28: _spec(28, "USE|REP", "Door_LockedRaise", "key_gate", speed=D_SLOW, wait=VDOORWAIT, key="red", local=True),
    29: _spec(29, "USE", "Door_Raise", "door", speed=D_SLOW, wait=VDOORWAIT),
    31: _spec(31, "USE", "Door_Open", "door", speed=D_SLOW, local=True, notes="open stay"),
    32: _spec(32, "USE|MONST", "Door_LockedRaise", "key_gate", speed=D_SLOW, wait=0, key="blue", local=True, notes="open stay"),
    33: _spec(33, "USE|MONST", "Door_LockedRaise", "key_gate", speed=D_SLOW, wait=0, key="red", local=True, notes="open stay"),
    34: _spec(34, "USE|MONST", "Door_LockedRaise", "key_gate", speed=D_SLOW, wait=0, key="yellow", local=True, notes="open stay"),
    35: _spec(35, "WALK", "Light_ChangeToValue", "light", fidelity=Representability.APPROXIMATE.value),
    36: _spec(36, "WALK", "Floor_LowerToHighest", "floor_move", speed=F_FAST, fidelity=Representability.APPROXIMATE.value),
    38: _spec(38, "WALK", "Floor_LowerToLowest", "floor_move", speed=F_SLOW, fidelity=Representability.APPROXIMATE.value),
    39: _spec(39, "WALK|MONST", "Teleport", "teleport"),
    42: _spec(42, "USE|REP", "Door_Close", "door", speed=D_SLOW),
    46: _spec(46, "SHOOT|REP|MONST", "Door_Open", "door", speed=D_SLOW, fidelity=Representability.APPROXIMATE.value),
    48: _spec(48, "0", "Scroll_Texture_Left", "light", fidelity=Representability.UNSUPPORTED.value, notes="texture scroll"),
    50: _spec(50, "USE", "Door_Close", "door", speed=D_SLOW),
    51: _spec(51, "USE", "Exit_Secret", "exit", local=True),
    52: _spec(52, "WALK", "Exit_Normal", "exit", local=True),
    61: _spec(61, "USE|REP", "Door_Open", "door", speed=D_SLOW),
    62: _spec(62, "USE|REP", "Plat_DownWaitUpStayLip", "lift", speed=P_FAST, wait=PLATWAIT),
    63: _spec(63, "USE|REP", "Door_Raise", "door", speed=D_SLOW, wait=VDOORWAIT),
    75: _spec(75, "WALK|REP", "Door_Close", "door", speed=D_SLOW),
    86: _spec(86, "WALK|REP", "Door_Open", "door", speed=D_SLOW),
    88: _spec(88, "WALK|REP|MONST", "Plat_DownWaitUpStayLip", "lift", speed=P_FAST, wait=PLATWAIT),
    90: _spec(90, "WALK|REP", "Door_Raise", "door", speed=D_SLOW, wait=VDOORWAIT),
    97: _spec(97, "WALK|REP|MONST", "Teleport", "teleport"),
    99: _spec(99, "USE|REP", "Door_LockedRaise", "key_gate", speed=D_FAST, wait=0, key="blue"),
    103: _spec(103, "USE", "Door_Open", "door", speed=D_SLOW),
    105: _spec(105, "WALK|REP", "Door_Raise", "door", speed=D_FAST, wait=VDOORWAIT),
    106: _spec(106, "WALK|REP", "Door_Open", "door", speed=D_FAST),
    108: _spec(108, "WALK", "Door_Raise", "door", speed=D_FAST, wait=VDOORWAIT),
    109: _spec(109, "WALK", "Door_Open", "door", speed=D_FAST),
    111: _spec(111, "USE", "Door_Raise", "door", speed=D_FAST, wait=VDOORWAIT),
    112: _spec(112, "USE", "Door_Open", "door", speed=D_FAST),
    114: _spec(114, "USE|REP", "Door_Raise", "door", speed=D_FAST, wait=VDOORWAIT),
    115: _spec(115, "USE|REP", "Door_Open", "door", speed=D_FAST),
    117: _spec(117, "USE|REP", "Door_Raise", "door", speed=D_FAST, wait=VDOORWAIT, local=True),
    118: _spec(118, "USE", "Door_Open", "door", speed=D_FAST, local=True),
    120: _spec(120, "WALK|REP", "Plat_DownWaitUpStayLip", "lift", speed=P_TURBO, wait=PLATWAIT),
    121: _spec(121, "WALK", "Plat_DownWaitUpStayLip", "lift", speed=P_TURBO, wait=PLATWAIT),
    122: _spec(122, "USE", "Plat_DownWaitUpStayLip", "lift", speed=P_TURBO, wait=PLATWAIT),
    123: _spec(123, "USE|REP", "Plat_DownWaitUpStayLip", "lift", speed=P_TURBO, wait=PLATWAIT),
    124: _spec(124, "WALK", "Exit_Secret", "exit", local=True),
    125: _spec(125, "MONWALK", "Teleport", "teleport", fidelity=Representability.UNSUPPORTED.value, notes="monsters only"),
    126: _spec(126, "MONWALK|REP", "Teleport", "teleport", fidelity=Representability.UNSUPPORTED.value, notes="monsters only"),
    133: _spec(133, "USE", "Door_LockedRaise", "key_gate", speed=D_FAST, wait=0, key="blue"),
    134: _spec(134, "USE|REP", "Door_LockedRaise", "key_gate", speed=D_FAST, wait=0, key="red"),
    135: _spec(135, "USE", "Door_LockedRaise", "key_gate", speed=D_FAST, wait=0, key="red"),
    136: _spec(136, "USE|REP", "Door_LockedRaise", "key_gate", speed=D_FAST, wait=0, key="yellow"),
    137: _spec(137, "USE", "Door_LockedRaise", "key_gate", speed=D_FAST, wait=0, key="yellow"),
}

# GZDoom xlat/doom.txt sector specials (vanilla 1-21). Boom bitmasks are out of scope.
SECTOR_SPECIALS: dict[int, tuple[str, str, str]] = {
    1: ("light", "dLight_Flicker", Representability.APPROXIMATE.value),
    2: ("light", "dLight_StrobeFast", Representability.APPROXIMATE.value),
    3: ("light", "dLight_StrobeSlow", Representability.APPROXIMATE.value),
    4: ("damage_area", "dLight_Strobe_Hurt", Representability.APPROXIMATE.value),
    5: ("damage_area", "dDamage_Hellslime", Representability.SEMANTIC.value),
    7: ("damage_area", "dDamage_Nukage", Representability.SEMANTIC.value),
    8: ("light", "dLight_Glow", Representability.APPROXIMATE.value),
    9: ("secret", "SECRET_MASK", Representability.APPROXIMATE.value),
    11: ("damage_area", "dDamage_End", Representability.APPROXIMATE.value),
    16: ("damage_area", "dDamage_SuperHellslime", Representability.SEMANTIC.value),
}

# GZDoom wadsrc/static/mapinfo/doomitems.txt — gameplay roles only.
THING_ROLES: dict[int, tuple[str, str]] = {
    1: ("player_start", "Player1Start"),
    2: ("player_start", "Player2Start"),
    3: ("player_start", "Player3Start"),
    4: ("player_start", "Player4Start"),
    5: ("key", "BlueCard"),
    6: ("key", "YellowCard"),
    8: ("ammo", "Backpack"),
    9: ("enemy", "ShotgunGuy"),
    13: ("key", "RedCard"),
    14: ("teleport_dest", "TeleportDest"),
    16: ("enemy", "Cyberdemon"),
    17: ("ammo", "CellPack"),
    38: ("key", "RedSkull"),
    39: ("key", "YellowSkull"),
    40: ("key", "BlueSkull"),
    58: ("enemy", "Spectre"),
    64: ("enemy", "Archvile"),
    65: ("enemy", "ChaingunGuy"),
    66: ("enemy", "Revenant"),
    67: ("enemy", "Fatso"),
    68: ("enemy", "Arachnotron"),
    69: ("enemy", "HellKnight"),
    71: ("enemy", "PainElemental"),
    82: ("weapon", "SuperShotgun"),
    83: ("health", "Megasphere"),
    2001: ("weapon", "Shotgun"),
    2002: ("weapon", "Chaingun"),
    2003: ("weapon", "RocketLauncher"),
    2004: ("weapon", "PlasmaRifle"),
    2005: ("weapon", "Chainsaw"),
    2006: ("weapon", "BFG9000"),
    2007: ("ammo", "Clip"),
    2008: ("ammo", "Shell"),
    2010: ("ammo", "RocketAmmo"),
    2011: ("health", "Stimpack"),
    2012: ("health", "Medikit"),
    2013: ("health", "Soulsphere"),
    2014: ("health", "HealthBonus"),
    2015: ("armor", "ArmorBonus"),
    2018: ("armor", "GreenArmor"),
    2019: ("armor", "BlueArmor"),
    2046: ("ammo", "RocketBox"),
    2047: ("ammo", "Cell"),
    2048: ("ammo", "ClipBox"),
    2049: ("ammo", "ShellBox"),
    3001: ("enemy", "DoomImp"),
    3002: ("enemy", "Demon"),
    3003: ("enemy", "BaronOfHell"),
    3004: ("enemy", "Zombieman"),
    3005: ("enemy", "Cacodemon"),
    3006: ("enemy", "LostSoul"),
}

KEY_COLORS = {
    5: "blue", 40: "blue",
    6: "yellow", 39: "yellow",
    13: "red", 38: "red",
}

VANILLA_SPECIAL_MAX = 141
BOOM_SPECIALS_IN_VANILLA_RANGE = {78, 85}


def _back_sector(level: DoomDiskMap, line: DoomLinedef) -> int | None:
    if line.side_back == NO_SIDE or not 0 <= line.side_back < len(level.sidedefs):
        return None
    return int(level.sidedefs[line.side_back].sector)


def _front_sector(level: DoomDiskMap, line: DoomLinedef) -> int | None:
    if not 0 <= line.side_front < len(level.sidedefs):
        return None
    return int(level.sidedefs[line.side_front].sector)


def tagged_sectors(level: DoomDiskMap, tag: int) -> list[int]:
    return [index for index, sector in enumerate(level.sectors) if int(sector.tag) == int(tag)]


def special_targets(level: DoomDiskMap, line: DoomLinedef, spec: LinedefSpecial) -> list[int]:
    if spec.kind == "exit":
        return []
    if spec.kind == "teleport":
        return tagged_sectors(level, line.tag)
    if spec.local_backsector and int(line.tag) == 0:
        back = _back_sector(level, line)
        return [] if back is None else [back]
    if int(line.tag) == 0:
        back = _back_sector(level, line)
        return [] if back is None else [back]
    return tagged_sectors(level, line.tag)


def analyze_doom_mechanisms(level: DoomDiskMap) -> dict[str, Any]:
    """Inventory runtime meaning. Does not lower to Blood."""
    if not level.supported:
        return {"map": level.name, "format": level.format, "status": "unsupported", "reason": level.unsupported_reason}
    mechanisms: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []
    counts: dict[str, int] = defaultdict(int)
    for index, line in enumerate(level.linedefs):
        special = int(line.special)
        if special == 0:
            continue
        spec = LINEDEF_SPECIALS.get(special)
        if spec is None:
            kind = "boom-or-unknown"
            if special in BOOM_SPECIALS_IN_VANILLA_RANGE or special > VANILLA_SPECIAL_MAX:
                kind = "boom-or-extension"
            unsupported.append({"linedef": index, "special": special, "kind": kind})
            counts[kind] += 1
            continue
        targets = special_targets(level, line, spec)
        record = {
            "id": f"linedef:{index}",
            "kind": spec.kind,
            "special": special,
            "action": spec.action,
            "activation": spec.activation,
            "repeatable": spec.repeatable,
            "tag": int(line.tag),
            "targets": [f"sector:{item}" for item in targets],
            "key": spec.key,
            "speed": spec.speed,
            "wait": spec.wait,
            "fidelity": spec.fidelity,
            "local_backsector": spec.local_backsector and int(line.tag) == 0,
        }
        if spec.notes:
            record["notes"] = spec.notes
        mechanisms.append(record)
        counts[spec.kind] += 1
    for index, sector in enumerate(level.sectors):
        special = int(sector.special)
        if special == 0:
            continue
        info = SECTOR_SPECIALS.get(special)
        if info is None:
            unsupported.append({"sector": index, "special": special, "kind": "sector-special-unknown"})
            counts["sector-special-unknown"] += 1
            continue
        kind, action, fidelity = info
        mechanisms.append({
            "id": f"sector:{index}",
            "kind": kind,
            "special": special,
            "action": action,
            "activation": "enter",
            "repeatable": True,
            "tag": int(sector.tag),
            "targets": [f"sector:{index}"],
            "fidelity": fidelity,
        })
        counts[kind] += 1
    things: dict[str, int] = defaultdict(int)
    unknown_things: dict[int, int] = defaultdict(int)
    for thing in level.things:
        role = THING_ROLES.get(int(thing.type))
        if role is None:
            unknown_things[int(thing.type)] += 1
        else:
            things[role[0]] += 1
    return {
        "map": level.name,
        "format": level.format,
        "counts": dict(sorted(counts.items())),
        "thing_roles": dict(sorted(things.items())),
        "unknown_things": dict(sorted(unknown_things.items())),
        "mechanisms": mechanisms,
        "unsupported": unsupported,
    }


def _region_id(sector_id: int) -> str:
    return f"region:{sector_id}"


def _adjacent_pairs(level: DoomDiskMap) -> list[tuple[int, int, int, bool]]:
    """(linedef, front_sector, back_sector, blocking)."""
    pairs = []
    for index, line in enumerate(level.linedefs):
        if line.side_back == NO_SIDE:
            continue
        front, back = _front_sector(level, line), _back_sector(level, line)
        if front is None or back is None or front == back:
            continue
        pairs.append((index, front, back, bool(line.flags & 0x1) and not (line.flags & ML_TWOSIDED)))
    return pairs


def _opening(level: DoomDiskMap, left: int, right: int) -> int:
    a, b = level.sectors[left], level.sectors[right]
    return min(a.ceiling_height, b.ceiling_height) - max(a.floor_height, b.floor_height)


def doom_to_semantic_level(level: DoomDiskMap) -> SemanticLevel:
    """Compile a classic Doom map into the engine-neutral progression graph."""
    inventory = analyze_doom_mechanisms(level)
    regions = [
        SemanticRegion(id=_region_id(index), native_refs=[f"sector:{index}"], tags=[f"tag:{sector.tag}"] if sector.tag else [])
        for index, sector in enumerate(level.sectors)
    ]
    items_by_sector: dict[int, list[str]] = defaultdict(list)
    start_sector = 0
    teleport_destinations: dict[int, list[int]] = defaultdict(list)
    for thing in level.things:
        sector_id = containing_sector(level, thing.x, thing.y)
        if sector_id is None:
            continue
        if thing.type == 1:
            start_sector = sector_id
        color = KEY_COLORS.get(thing.type)
        if color:
            items_by_sector[sector_id].append(f"key:{color}")
        if thing.type == 14:
            teleport_destinations[int(level.sectors[sector_id].tag)].append(sector_id)
    for sector_id, items in items_by_sector.items():
        regions[sector_id].items.extend(items)

    door_sectors: dict[int, dict[str, Any]] = {}
    semantic_mechanisms: list[SemanticMechanism] = []
    for record in inventory["mechanisms"]:
        if record["kind"] not in {"door", "key_gate", "lift", "teleport", "exit", "secret", "damage_area"}:
            continue
        mechanism = SemanticMechanism(
            id=str(record["id"]),
            kind=str(record["kind"]),
            source_game="doom",
            native_refs=[str(record["id"]), *record.get("targets", [])],
            activation=str(record.get("activation", "use")),
            repeatable=bool(record.get("repeatable", False)),
            state="closed" if record["kind"] in {"door", "key_gate", "lift"} else "idle",
            parameters={key: record[key] for key in ("special", "action", "speed", "wait", "tag") if key in record},
            required_keys=[record["key"]] if record.get("key") else [],
            targets=list(record.get("targets", [])),
            fidelity=str(record.get("fidelity", Representability.SEMANTIC.value)),
            notes=str(record.get("notes", "")),
        )
        semantic_mechanisms.append(mechanism)
        if record["kind"] in {"door", "key_gate", "lift"}:
            for target in record.get("targets", []):
                door_sectors[int(target.split(":")[1])] = record

    connections: list[SemanticConnection] = []
    seen_open: set[tuple[int, int]] = set()
    for line_id, front, back, _blocking in _adjacent_pairs(level):
        pair = tuple(sorted((front, back)))
        door_record = door_sectors.get(front) or door_sectors.get(back)
        if door_record:
            door_sector = front if front in door_sectors else back
            neighbor = back if door_sector == front else front
            for source, target in ((neighbor, door_sector), (door_sector, neighbor)):
                connections.append(SemanticConnection(
                    id=f"conn:linedef:{line_id}:{source}:{target}",
                    kind="key_gate" if door_record["kind"] == "key_gate" else door_record["kind"],
                    source=_region_id(source),
                    target=_region_id(target),
                    mechanism_id=str(door_record["id"]),
                    required_keys=[door_record["key"]] if door_record.get("key") else [],
                    initial="closed",
                ))
            continue
        if pair in seen_open:
            continue
        if _opening(level, front, back) <= 0:
            continue
        seen_open.add(pair)
        connections.append(SemanticConnection(
            id=f"conn:{front}:{back}",
            kind="open",
            source=_region_id(front),
            target=_region_id(back),
            initial="open",
        ))
        connections.append(SemanticConnection(
            id=f"conn:{back}:{front}",
            kind="open",
            source=_region_id(back),
            target=_region_id(front),
            initial="open",
        ))

    for record in inventory["mechanisms"]:
        if record["kind"] != "teleport":
            continue
        line_id = int(str(record["id"]).split(":")[1])
        line = level.linedefs[line_id]
        source = _front_sector(level, line)
        destinations = teleport_destinations.get(int(line.tag), [])
        if source is None:
            continue
        for dest in destinations:
            connections.append(SemanticConnection(
                id=f"conn:teleport:{line_id}:{dest}",
                kind="teleport",
                source=_region_id(source),
                target=_region_id(dest),
                mechanism_id=str(record["id"]),
                initial="open",
            ))

    exit_regions = []
    for record in inventory["mechanisms"]:
        if record["kind"] != "exit":
            continue
        line_id = int(str(record["id"]).split(":")[1])
        sector_id = _front_sector(level, level.linedefs[line_id])
        if sector_id is not None:
            exit_regions.append(_region_id(sector_id))

    return SemanticLevel(
        source_game="doom",
        regions=regions,
        connections=connections,
        mechanisms=semantic_mechanisms,
        start_region=_region_id(start_sector),
        exit_regions=sorted(set(exit_regions)),
        notes="compiled from classic Doom linedef specials, sector specials, and adjacency",
    )


def containing_sector(level: DoomDiskMap, x: int, y: int) -> int | None:
    """Even-odd test over each sector's directed sidedef edges. Boundary counts as inside."""
    hits: list[int] = []
    for sector_id in range(len(level.sectors)):
        if _point_in_doom_sector(level, sector_id, x, y):
            hits.append(sector_id)
    if not hits:
        return None
    return hits[0]


def _point_in_doom_sector(level: DoomDiskMap, sector_id: int, x: int, y: int) -> bool:
    edges: list[tuple[int, int, int, int]] = []
    for line in level.linedefs:
        for side_index, reverse in ((line.side_front, False), (line.side_back, True)):
            if side_index == NO_SIDE or not 0 <= side_index < len(level.sidedefs):
                continue
            if int(level.sidedefs[side_index].sector) != sector_id:
                continue
            a, b = level.vertices[line.v1], level.vertices[line.v2]
            if reverse:
                edges.append((b.x, b.y, a.x, a.y))
            else:
                edges.append((a.x, a.y, b.x, b.y))
    inside = False
    for x1, y1, x2, y2 in edges:
        if (min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2)
                and (x2 - x1) * (y - y1) == (y2 - y1) * (x - x1)):
            return True
        if (y1 > y) != (y2 > y) and x < x1 + (x2 - x1) * (y - y1) / (y2 - y1):
            inside = not inside
    return inside
