from __future__ import annotations

from collections import Counter, defaultdict
from math import isqrt
from typing import TYPE_CHECKING, Any, Iterable

from .fragment import SYSTEM_CHANNELS, extract_fragment

if TYPE_CHECKING:
    from .model import LevelIR


class ObservationError(ValueError):
    pass


def _safe_design_fingerprint(level: "LevelIR", sector_ids: Iterable[int] | None = None) -> dict[str, Any]:
    """Keep the observation sensor non-authoritative for accepted oddities."""
    from .design import DesignUnderstandingError

    try:
        return level.design_fingerprint(sector_ids)
    except DesignUnderstandingError as exc:
        return {
            "status": "unavailable",
            "error": str(exc),
            "provenance": {
                "verified_facts": ["the source LevelIR observation remains available"],
                "not_inferred": ["design metrics require valid sector wall ownership"],
            },
        }


_BEHAVIOR_FIELDS = (
    "rx_id", "tx_id", "command", "state", "rest_state", "busy",
    "busy_time", "busy_time_a", "busy_time_b", "wait_time", "wait_time_a",
    "wait_time_b", "key", "locked", "decoupled", "trigger_once",
    "is_triggered", "data", "marker_0", "marker_1", "target", "burn_source",
    "off_ceiling_z", "on_ceiling_z", "off_floor_z", "on_floor_z",
)


def _ref(kind: str, identifier: int) -> str:
    return f"{kind}:{identifier}"


def _blood_summary(item: dict[str, Any]) -> dict[str, Any] | None:
    blood = item.get("blood")
    if blood is None:
        return None
    fields = blood["fields"]
    result: dict[str, Any] = {"kind": blood["kind"]}
    for name in _BEHAVIOR_FIELDS:
        if name not in fields:
            continue
        value = int(fields[name])
        if value or name in {"rx_id", "tx_id", "command", "state", "rest_state"}:
            result[name] = value
    triggers = sorted(
        name.removeprefix("trigger_")
        for name, value in fields.items()
        if name.startswith("trigger_") and value
    )
    if triggers:
        result["triggers"] = triggers
    return result


def _wall_owners(level: LevelIR) -> list[int]:
    owners = [-1] * len(level.walls)
    for sector_id, sector in enumerate(level.sectors):
        fields = sector["fields"]
        first, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        if first < 0 or count <= 0 or first + count > len(level.walls):
            raise ObservationError(f"sector:{sector_id} has an invalid wall range")
        for wall_id in range(first, first + count):
            if owners[wall_id] != -1:
                raise ObservationError(f"wall:{wall_id} belongs to multiple sectors")
            owners[wall_id] = sector_id
    return owners


def _sector_geometry(level: LevelIR, sector_id: int) -> dict[str, Any]:
    sector = level.sectors[sector_id]
    fields = sector["fields"]
    wall_ids = list(range(int(fields["wall_ptr"]), int(fields["wall_ptr"]) + int(fields["wall_count"])))
    points = [
        (int(level.walls[wall_id]["fields"]["x"]), int(level.walls[wall_id]["fields"]["y"]))
        for wall_id in wall_ids
    ]
    xs, ys = zip(*points)
    twice_area = 0
    centroid_x, centroid_y = 0, 0
    neighbors: dict[int, list[int]] = defaultdict(list)
    for wall_id in wall_ids:
        wall = level.walls[wall_id]["fields"]
        point2 = int(wall["point2"])
        if not 0 <= point2 < len(level.walls):
            raise ObservationError(f"wall:{wall_id} has invalid point2 {point2}")
        end = level.walls[point2]["fields"]
        cross = int(wall["x"]) * int(end["y"]) - int(end["x"]) * int(wall["y"])
        twice_area += cross
        centroid_x += (int(wall["x"]) + int(end["x"])) * cross
        centroid_y += (int(wall["y"]) + int(end["y"])) * cross
        if int(wall["next_sector"]) >= 0:
            neighbors[int(wall["next_sector"])].append(wall_id)
    centroid = {
        "x": centroid_x / (3 * twice_area),
        "y": centroid_y / (3 * twice_area),
    } if twice_area else {"x": sum(xs) / len(xs), "y": sum(ys) / len(ys)}
    return {
        "wall_ids": wall_ids,
        "bounds": {"min_x": min(xs), "min_y": min(ys), "max_x": max(xs), "max_y": max(ys)},
        "centroid": centroid,
        "neighbors": [
            {"sector": _ref("sector", neighbor), "portal_walls": [_ref("wall", wall) for wall in walls]}
            for neighbor, walls in sorted(neighbors.items())
        ],
    }


def _type_inventory(level: LevelIR) -> dict[str, list[dict[str, int]]]:
    result: dict[str, list[dict[str, int]]] = {}
    for kind, objects in (
        ("sector", level.sectors), ("wall", level.walls), ("sprite", level.sprites),
    ):
        counts = Counter(int(item["fields"]["type"]) for item in objects)
        result[kind] = [{"type": type_id, "count": count} for type_id, count in sorted(counts.items())]
    return result


def _tile_inventory(level: LevelIR) -> list[dict[str, int]]:
    counts: Counter[int] = Counter()
    for sector in level.sectors:
        fields = sector["fields"]
        counts.update((int(fields["ceiling_picnum"]), int(fields["floor_picnum"])))
    for wall in level.walls:
        fields = wall["fields"]
        counts[int(fields["picnum"])] += 1
        if int(fields["over_picnum"]) >= 0:
            counts[int(fields["over_picnum"])] += 1
    counts.update(int(sprite["fields"]["picnum"]) for sprite in level.sprites)
    return [{"tile": tile, "count": count} for tile, count in sorted(counts.items())]


def _channel_graph(level: LevelIR) -> list[dict[str, Any]]:
    transmitters: dict[int, list[dict[str, Any]]] = defaultdict(list)
    receivers: dict[int, list[str]] = defaultdict(list)
    for kind, objects in (
        ("sector", level.sectors), ("wall", level.walls), ("sprite", level.sprites),
    ):
        for identifier, item in enumerate(objects):
            blood = item.get("blood")
            if blood is None:
                continue
            fields = blood["fields"]
            object_ref = _ref(kind, identifier)
            tx_id, rx_id = int(fields["tx_id"]), int(fields["rx_id"])
            if tx_id:
                triggers = sorted(
                    name.removeprefix("trigger_")
                    for name, value in fields.items()
                    if name.startswith("trigger_") and value
                )
                transmitter: dict[str, Any] = {
                    "ref": object_ref,
                    "command": int(fields["command"]),
                }
                if triggers:
                    transmitter["triggers"] = triggers
                transmitters[tx_id].append(transmitter)
            if rx_id:
                receivers[rx_id].append(object_ref)
    channels = []
    for channel in sorted(set(transmitters) | set(receivers)):
        item: dict[str, Any] = {
            "channel": channel,
            "transmitters": transmitters.get(channel, []),
            "receivers": receivers.get(channel, []),
        }
        if channel in SYSTEM_CHANNELS:
            item["system_name"] = SYSTEM_CHANNELS[channel]
        channels.append(item)
    return channels


def _object_channels(item: dict[str, Any]) -> list[int]:
    blood = item.get("blood")
    if blood is None:
        return []
    fields = blood["fields"]
    return sorted({int(value) for value in (fields["tx_id"], fields["rx_id"]) if value})


def _sector_index(level: LevelIR, sprite_ids: dict[int, list[int]]) -> list[dict[str, Any]]:
    result = []
    for sector_id, sector in enumerate(level.sectors):
        geometry = _sector_geometry(level, sector_id)
        blood = _blood_summary(sector)
        item: dict[str, Any] = {
            "ref": _ref("sector", sector_id),
            "type": int(sector["fields"]["type"]),
            "bounds": geometry["bounds"],
            "centroid": geometry["centroid"],
            "wall_count": len(geometry["wall_ids"]),
            "sprite_count": len(sprite_ids.get(sector_id, [])),
            "neighbors": [entry["sector"] for entry in geometry["neighbors"]],
        }
        channels = _object_channels(sector)
        if channels:
            item["channels"] = channels
        if blood is not None:
            item["blood_kind"] = blood["kind"]
        result.append(item)
    return result


def _connector(
    level: LevelIR, wall_id: int, owner: int, selected: set[int],
) -> dict[str, Any] | None:
    wall = level.walls[wall_id]["fields"]
    next_sector = int(wall["next_sector"])
    if next_sector in selected:
        return None
    end = level.walls[int(wall["point2"])]["fields"]
    dx, dy = int(end["x"]) - int(wall["x"]), int(end["y"]) - int(wall["y"])
    return {
        "ref": _ref("wall", wall_id),
        "sector": _ref("sector", owner),
        "kind": "one_sided" if next_sector == -1 else "external_portal",
        "next_sector": None if next_sector == -1 else _ref("sector", next_sector),
        "next_wall": None if int(wall["next_wall"]) == -1 else _ref("wall", int(wall["next_wall"])),
        "start": {"x": int(wall["x"]), "y": int(wall["y"])},
        "end": {"x": int(end["x"]), "y": int(end["y"])},
        "length": isqrt(dx * dx + dy * dy),
        "blocking": bool(int(wall["cstat"]) & 1),
        "tile": int(wall["picnum"]),
        "over_tile": int(wall["over_picnum"]),
    }


def observe_level(level: LevelIR, sector_ids: Iterable[int] | None = None) -> dict[str, Any]:
    """Build a deterministic, compact semantic view directly from LevelIR."""
    owners = _wall_owners(level)
    sprite_ids: dict[int, list[int]] = defaultdict(list)
    for sprite_id, sprite in enumerate(level.sprites):
        sprite_ids[int(sprite["fields"]["sector"])].append(sprite_id)
    xs = [int(wall["fields"]["x"]) for wall in level.walls]
    ys = [int(wall["fields"]["y"]) for wall in level.walls]
    observation: dict[str, Any] = {
        "$schema": "bloodmap.level-observation",
        "schema_version": 1,
        "level": {
            "observation_scope": "level" if sector_ids is None else "selection",
            "format": level.metadata.get("format"),
            "map_version": level.metadata.get("map_version"),
            "counts": {
                "sectors": len(level.sectors),
                "walls": len(level.walls),
                "sprites": len(level.sprites),
            },
            "bounds": {
                "min_x": min(xs), "min_y": min(ys), "max_x": max(xs), "max_y": max(ys),
            } if xs else None,
            "player_start": {
                **{name: int(value) for name, value in level.player_start.items()},
                "sector_ref": _ref("sector", int(level.player_start["sector"])),
            },
            "type_inventory": _type_inventory(level),
            "tile_inventory": _tile_inventory(level),
        },
        "sector_index": _sector_index(level, sprite_ids),
        "channels": _channel_graph(level),
        "selection": None,
    }
    if sector_ids is None:
        observation["design_fingerprint"] = _safe_design_fingerprint(level)
        return observation

    selected_ids = sorted(set(int(value) for value in sector_ids))
    if not selected_ids:
        raise ObservationError("sector selection is empty")
    invalid = [value for value in selected_ids if not 0 <= value < len(level.sectors)]
    if invalid:
        raise ObservationError(f"sector IDs are out of range: {invalid}")
    selected = set(selected_ids)
    fragment = extract_fragment(level, selected_ids)
    sector_details = []
    selected_walls: list[int] = []
    for sector_id in selected_ids:
        sector = level.sectors[sector_id]
        fields = sector["fields"]
        geometry = _sector_geometry(level, sector_id)
        selected_walls.extend(geometry["wall_ids"])
        sector_details.append({
            "ref": _ref("sector", sector_id),
            "type": int(fields["type"]),
            "geometry": geometry,
            "surfaces": {
                "ceiling": {
                    "z": int(fields["ceiling_z"]), "tile": int(fields["ceiling_picnum"]),
                    "stat": int(fields["ceiling_stat"]), "heinum": int(fields["ceiling_heinum"]),
                },
                "floor": {
                    "z": int(fields["floor_z"]), "tile": int(fields["floor_picnum"]),
                    "stat": int(fields["floor_stat"]), "heinum": int(fields["floor_heinum"]),
                },
            },
            "sprites": [_ref("sprite", value) for value in sprite_ids.get(sector_id, [])],
            "blood": _blood_summary(sector),
        })
    connectors = [
        connector
        for wall_id in selected_walls
        if (connector := _connector(level, wall_id, owners[wall_id], selected)) is not None
    ]
    sprites = []
    for sprite_id in sorted(value for sector in selected_ids for value in sprite_ids.get(sector, [])):
        sprite = level.sprites[sprite_id]
        fields = sprite["fields"]
        owner = int(fields["owner"])
        owner_observation: str | dict[str, Any] | None
        if owner == -1:
            owner_observation = None
        elif 0 <= owner < len(level.sprites):
            owner_observation = _ref("sprite", owner)
        else:
            owner_observation = {"raw": owner, "classification": "opaque_non_sprite"}
        sprites.append({
            "ref": _ref("sprite", sprite_id),
            "type": int(fields["type"]),
            "tile": int(fields["picnum"]),
            "position": {
                "x": int(fields["x"]), "y": int(fields["y"]), "z": int(fields["z"]),
                "sector": _ref("sector", int(fields["sector"])), "angle": int(fields["angle"]),
            },
            "status": int(fields["status"]),
            "owner": owner_observation,
            "blood": _blood_summary(sprite),
        })
    interactive_objects = []
    for kind, identifiers, objects in (
        ("sector", selected_ids, level.sectors),
        ("wall", selected_walls, level.walls),
        ("sprite", [int(item["ref"].split(":", 1)[1]) for item in sprites], level.sprites),
    ):
        for identifier in identifiers:
            blood = _blood_summary(objects[identifier])
            if blood is not None:
                interactive_objects.append({
                    "ref": _ref(kind, identifier),
                    "type": int(objects[identifier]["fields"]["type"]),
                    "blood": blood,
                })
    observation["selection"] = {
        "sector_ids": selected_ids,
        "dependency_summary": fragment.dependency_summary(),
        "unresolved_relationships": [
            relationship.to_dict()
            for relationship in fragment.relationships
            if relationship.classification.startswith("external_")
        ],
        "sectors": sector_details,
        "connectors": connectors,
        "sprites": sprites,
        "interactive_objects": interactive_objects,
        "design_fingerprint": _safe_design_fingerprint(level, selected_ids),
    }
    selected_refs = {
        *(_ref("sector", value) for value in selected_ids),
        *(_ref("wall", value) for value in selected_walls),
        *(item["ref"] for item in sprites),
    }
    observation["sector_index"] = [
        item for item in observation["sector_index"] if item["ref"] in selected_refs
    ]
    observation["channels"] = [
        channel for channel in observation["channels"]
        if any(item["ref"] in selected_refs for item in channel["transmitters"])
        or any(item in selected_refs for item in channel["receivers"])
    ]
    observation["level"].pop("type_inventory")
    observation["level"].pop("tile_inventory")
    return observation
