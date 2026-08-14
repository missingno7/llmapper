from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable

from .model import LevelIR


# Verified against NBlood source/blood/src/eventq.h. Undefined values below 100
# are deliberately not guessed to be system channels.
SYSTEM_CHANNELS: dict[int, str] = {
    1: "set_total_secrets",
    2: "secret_found",
    3: "text_over",
    4: "level_exit_normal",
    5: "level_exit_secret",
    6: "modern_end_level_custom",
    7: "level_start",
    8: "level_start_match",
    9: "level_start_coop",
    10: "level_start_teams_only",
    15: "player_death_team_a",
    16: "player_death_team_b",
    17: "level_start_nblood",
    18: "level_start_raze",
    29: "all_players",
    30: "player_0",
    31: "player_1",
    32: "player_2",
    33: "player_3",
    34: "player_4",
    35: "player_5",
    36: "player_6",
    37: "player_7",
    50: "event_causer",
    60: "map_modern_revision_1",
    61: "map_modern_revision_2",
    80: "team_a_flag_captured",
    81: "team_b_flag_captured",
    90: "remote_bomb_0",
    91: "remote_bomb_1",
    92: "remote_bomb_2",
    93: "remote_bomb_3",
    94: "remote_bomb_4",
    95: "remote_bomb_5",
    96: "remote_bomb_6",
    97: "remote_bomb_7",
}


class FragmentError(ValueError):
    pass


@dataclass(frozen=True)
class IndexMap:
    kind: str
    source_to_fragment: dict[int, int]

    @property
    def fragment_to_source(self) -> dict[int, int]:
        return {fragment: source for source, fragment in self.source_to_fragment.items()}

    def localize(self, source_id: int) -> int:
        try:
            return self.source_to_fragment[source_id]
        except KeyError as exc:
            raise FragmentError(f"{self.kind} source id {source_id} is outside the fragment") from exc

    def restore(self, fragment_id: int) -> int:
        try:
            return self.fragment_to_source[fragment_id]
        except KeyError as exc:
            raise FragmentError(f"{self.kind} fragment id {fragment_id} has no source mapping") from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "source_to_fragment": {str(k): v for k, v in sorted(self.source_to_fragment.items())},
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "IndexMap":
        return cls(
            kind=str(value["kind"]),
            source_to_fragment={int(k): int(v) for k, v in value["source_to_fragment"].items()},
        )


@dataclass(frozen=True)
class FragmentRelationship:
    classification: str
    relation: str
    source: dict[str, Any]
    field: str
    target: dict[str, Any]
    direction: str | None = None
    channel: int | None = None
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = {
            "classification": self.classification,
            "relation": self.relation,
            "source": self.source,
            "field": self.field,
            "target": self.target,
        }
        if self.direction is not None:
            value["direction"] = self.direction
        if self.channel is not None:
            value["channel"] = self.channel
        if self.note is not None:
            value["note"] = self.note
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "FragmentRelationship":
        return cls(
            classification=str(value["classification"]), relation=str(value["relation"]),
            source=dict(value["source"]), field=str(value["field"]), target=dict(value["target"]),
            direction=value.get("direction"), channel=value.get("channel"), note=value.get("note"),
        )


@dataclass(frozen=True)
class PreservedReference:
    object_kind: str
    fragment_id: int
    path: str
    source_value: int
    localized_value: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_kind": self.object_kind, "fragment_id": self.fragment_id,
            "path": self.path, "source_value": self.source_value,
            "localized_value": self.localized_value, "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "PreservedReference":
        return cls(
            object_kind=str(value["object_kind"]), fragment_id=int(value["fragment_id"]),
            path=str(value["path"]), source_value=int(value["source_value"]),
            localized_value=int(value["localized_value"]), reason=str(value["reason"]),
        )


@dataclass
class LevelFragment:
    source: dict[str, Any]
    index_maps: dict[str, IndexMap]
    sectors: list[dict[str, Any]]
    walls: list[dict[str, Any]]
    sprites: list[dict[str, Any]]
    relationships: list[FragmentRelationship]
    preserved_references: list[PreservedReference]
    schema: str = "bloodmap.level-fragment"
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "$schema": self.schema,
            "schema_version": self.schema_version,
            "source": self.source,
            "index_maps": {name: value.to_dict() for name, value in sorted(self.index_maps.items())},
            "sectors": self.sectors,
            "walls": self.walls,
            "sprites": self.sprites,
            "relationships": [value.to_dict() for value in self.relationships],
            "preserved_references": [value.to_dict() for value in self.preserved_references],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "LevelFragment":
        if value.get("$schema") != "bloodmap.level-fragment" or int(value.get("schema_version", -1)) != 1:
            raise FragmentError("unsupported LevelFragment schema")
        return cls(
            source=dict(value["source"]),
            index_maps={name: IndexMap.from_dict(item) for name, item in value["index_maps"].items()},
            sectors=list(value["sectors"]), walls=list(value["walls"]), sprites=list(value["sprites"]),
            relationships=[FragmentRelationship.from_dict(item) for item in value["relationships"]],
            preserved_references=[PreservedReference.from_dict(item) for item in value["preserved_references"]],
        )

    def dependency_summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for relationship in self.relationships:
            counts[relationship.classification] = counts.get(relationship.classification, 0) + 1
        return dict(sorted(counts.items()))

    def apply_to_source(self, level: LevelIR) -> LevelIR:
        return apply_fragment_in_place(level, self)


@dataclass
class BehaviorClosureResult:
    """A fragment plus the source sectors required by its gameplay references."""

    fragment: LevelFragment
    requested_sector_ids: list[int]
    selected_sector_ids: list[int]
    additions: list[dict[str, Any]]
    unresolved_relationships: list[FragmentRelationship]

    def report(self) -> dict[str, Any]:
        return {
            "operation": "extract_behavior_closed_fragment",
            "requested_sector_ids": self.requested_sector_ids,
            "selected_sector_ids": self.selected_sector_ids,
            "added_sector_ids": sorted(
                set(self.selected_sector_ids) - set(self.requested_sector_ids)
            ),
            "additions": self.additions,
            "unresolved_relationships": [
                relationship.to_dict() for relationship in self.unresolved_relationships
            ],
            "dependency_summary": self.fragment.dependency_summary(),
            "fragment_counts": {
                "sectors": len(self.fragment.sectors),
                "walls": len(self.fragment.walls),
                "sprites": len(self.fragment.sprites),
            },
        }


def _fragment_ref(kind: str, identifier: int) -> dict[str, Any]:
    return {"space": "fragment", "kind": kind, "id": identifier}


def _source_ref(kind: str, identifier: int) -> dict[str, Any]:
    return {"space": "source", "kind": kind, "id": identifier}


def _system_ref(channel: int) -> dict[str, Any]:
    return {"space": "system", "kind": "channel", "id": channel, "name": SYSTEM_CHANNELS[channel]}


def _blood(item: dict[str, Any]) -> dict[str, int] | None:
    extra = item.get("blood")
    return None if extra is None else extra["fields"]


def _channel_endpoints(level: LevelIR) -> tuple[dict[int, list[tuple[str, int]]], dict[int, list[tuple[str, int]]]]:
    transmitters: dict[int, list[tuple[str, int]]] = {}
    receivers: dict[int, list[tuple[str, int]]] = {}
    for kind, objects in (("sector", level.sectors), ("wall", level.walls), ("sprite", level.sprites)):
        for index, item in enumerate(objects):
            fields = _blood(item)
            if fields is None:
                continue
            if fields["tx_id"]:
                transmitters.setdefault(fields["tx_id"], []).append((kind, index))
            if fields["rx_id"]:
                receivers.setdefault(fields["rx_id"], []).append((kind, index))
    return transmitters, receivers


def extract_fragment(level: LevelIR, sector_ids: Iterable[int]) -> LevelFragment:
    selected = sorted(set(int(value) for value in sector_ids))
    if not selected:
        raise FragmentError("at least one sector must be selected")
    for sector_id in selected:
        if not 0 <= sector_id < len(level.sectors):
            raise FragmentError(f"sector {sector_id} is outside 0..{len(level.sectors)-1}")

    wall_ids: list[int] = []
    for sector_id in selected:
        fields = level.sectors[sector_id]["fields"]
        first, count = fields["wall_ptr"], fields["wall_count"]
        ids = list(range(first, first + count))
        if any(not 0 <= wall_id < len(level.walls) for wall_id in ids):
            raise FragmentError(f"sector {sector_id} has an invalid wall range")
        wall_ids.extend(ids)
    if len(wall_ids) != len(set(wall_ids)):
        raise FragmentError("selected sectors have overlapping wall ownership")
    sprite_ids = [i for i, item in enumerate(level.sprites) if item["fields"]["sector"] in selected]

    sector_map = IndexMap("sector", {source: local for local, source in enumerate(selected)})
    wall_map = IndexMap("wall", {source: local for local, source in enumerate(wall_ids)})
    sprite_map = IndexMap("sprite", {source: local for local, source in enumerate(sprite_ids)})

    def extra_map(kind: str, ids: list[int], objects: list[dict[str, Any]]) -> IndexMap:
        source_ids = [objects[index]["fields"]["extra"] for index in ids if objects[index]["fields"]["extra"] > 0]
        if len(source_ids) != len(set(source_ids)):
            raise FragmentError(f"duplicate {kind} extra ownership in selected objects")
        return IndexMap(kind, {source: local + 1 for local, source in enumerate(source_ids)})

    xsector_map = extra_map("xsector", selected, level.sectors)
    xwall_map = extra_map("xwall", wall_ids, level.walls)
    xsprite_map = extra_map("xsprite", sprite_ids, level.sprites)
    maps = {
        "sector": sector_map, "wall": wall_map, "sprite": sprite_map,
        "xsector": xsector_map, "xwall": xwall_map, "xsprite": xsprite_map,
    }
    relationships: list[FragmentRelationship] = []
    preserved: list[PreservedReference] = []

    def preserve(kind: str, local_id: int, path: str, source_value: int, local_value: int, reason: str) -> None:
        preserved.append(PreservedReference(kind, local_id, path, source_value, local_value, reason))

    def localize_extra(item: dict[str, Any], kind: str, local_id: int) -> None:
        fields = item["fields"]
        if fields["extra"] > 0:
            fields["extra"] = maps["x" + kind].localize(fields["extra"])
            relationships.append(FragmentRelationship(
                "internal_reference", "extra_ownership", _fragment_ref(kind, local_id),
                "fields.extra", _fragment_ref("x" + kind, fields["extra"]),
            ))
        blood = _blood(item)
        if blood is not None:
            source_reference = blood["reference"]
            blood["reference"] = local_id
            preserve(kind, local_id, "blood.fields.reference", source_reference, local_id, "redundant_owner")
            relationships.append(FragmentRelationship(
                "internal_reference", "redundant_owner", _fragment_ref("x" + kind, fields["extra"]),
                "blood.fields.reference", _fragment_ref(kind, local_id),
                note="loaders overwrite this redundant disk value; source value is preserved",
            ))

    sectors: list[dict[str, Any]] = []
    for source_id in selected:
        local_id = sector_map.localize(source_id)
        item = copy.deepcopy(level.sectors[source_id])
        item["source_id"] = source_id
        item["id"] = local_id
        fields = item["fields"]
        fields["wall_ptr"] = wall_map.localize(fields["wall_ptr"])
        relationships.append(FragmentRelationship(
            "internal_reference", "wall_ownership", _fragment_ref("sector", local_id),
            "fields.wall_ptr/wall_count",
            {"space": "fragment", "kind": "wall_range", "first": fields["wall_ptr"], "count": fields["wall_count"]},
        ))
        localize_extra(item, "sector", local_id)
        blood = _blood(item)
        if blood is not None:
            for field in ("marker_0", "marker_1"):
                target = blood[field]
                if target < 0:
                    continue
                if target in sprite_map.source_to_fragment:
                    blood[field] = sprite_map.localize(target)
                    relationships.append(FragmentRelationship(
                        "internal_reference", "marker", _fragment_ref("sector", local_id),
                        f"blood.fields.{field}", _fragment_ref("sprite", blood[field]),
                    ))
                else:
                    blood[field] = -1
                    preserve("sector", local_id, f"blood.fields.{field}", target, -1, "external_marker")
                    relationships.append(FragmentRelationship(
                        "external_marker", "marker", _fragment_ref("sector", local_id),
                        f"blood.fields.{field}", _source_ref("sprite", target),
                    ))
        sectors.append(item)

    walls: list[dict[str, Any]] = []
    for source_id in wall_ids:
        local_id = wall_map.localize(source_id)
        item = copy.deepcopy(level.walls[source_id])
        item["source_id"] = source_id
        item["id"] = local_id
        fields = item["fields"]
        point2 = fields["point2"]
        if point2 not in wall_map.source_to_fragment:
            raise FragmentError(f"wall {source_id}.point2={point2} leaves selected sector ownership")
        fields["point2"] = wall_map.localize(point2)
        relationships.append(FragmentRelationship(
            "internal_reference", "wall_loop", _fragment_ref("wall", local_id),
            "fields.point2", _fragment_ref("wall", fields["point2"]),
        ))
        next_wall, next_sector = fields["next_wall"], fields["next_sector"]
        if next_wall >= 0 or next_sector >= 0:
            if next_wall in wall_map.source_to_fragment and next_sector in sector_map.source_to_fragment:
                fields["next_wall"] = wall_map.localize(next_wall)
                fields["next_sector"] = sector_map.localize(next_sector)
                relationships.append(FragmentRelationship(
                    "internal_reference", "portal", _fragment_ref("wall", local_id),
                    "fields.next_wall/next_sector",
                    {"space": "fragment", "kind": "portal", "wall": fields["next_wall"], "sector": fields["next_sector"]},
                ))
            else:
                fields["next_wall"] = fields["next_sector"] = -1
                preserve("wall", local_id, "fields.next_wall", next_wall, -1, "external_geometry")
                preserve("wall", local_id, "fields.next_sector", next_sector, -1, "external_geometry")
                relationships.append(FragmentRelationship(
                    "external_geometry", "portal", _fragment_ref("wall", local_id),
                    "fields.next_wall/next_sector",
                    {"space": "source", "kind": "portal", "wall": next_wall, "sector": next_sector},
                    note="detached in fragment; preserved for same-source reinsertion",
                ))
        localize_extra(item, "wall", local_id)
        walls.append(item)

    sprites: list[dict[str, Any]] = []
    for source_id in sprite_ids:
        local_id = sprite_map.localize(source_id)
        item = copy.deepcopy(level.sprites[source_id])
        item["source_id"] = source_id
        item["id"] = local_id
        fields = item["fields"]
        fields["sector"] = sector_map.localize(fields["sector"])
        relationships.append(FragmentRelationship(
            "internal_reference", "sector_membership", _fragment_ref("sprite", local_id),
            "fields.sector", _fragment_ref("sector", fields["sector"]),
        ))
        source_index = fields["index"]
        fields["index"] = local_id
        preserve("sprite", local_id, "fields.index", source_index, local_id, "redundant_owner")
        relationships.append(FragmentRelationship(
            "internal_reference", "redundant_owner", _fragment_ref("sprite", local_id),
            "fields.index", _fragment_ref("sprite", local_id),
            note="source index is preserved for exact same-source reinsertion",
        ))
        owner = fields["owner"]
        if 0 <= owner < len(level.sprites):
            if owner in sprite_map.source_to_fragment:
                fields["owner"] = sprite_map.localize(owner)
                relationships.append(FragmentRelationship(
                    "internal_reference", "ownership", _fragment_ref("sprite", local_id),
                    "fields.owner", _fragment_ref("sprite", fields["owner"]),
                ))
            else:
                fields["owner"] = -1
                preserve("sprite", local_id, "fields.owner", owner, -1, "external_ownership")
                relationships.append(FragmentRelationship(
                    "external_ownership", "ownership", _fragment_ref("sprite", local_id),
                    "fields.owner", _source_ref("sprite", owner),
                ))
        elif owner != -1:
            relationships.append(FragmentRelationship(
                "system_global", "opaque_owner", _fragment_ref("sprite", local_id),
                "fields.owner", {"space": "system", "kind": "owner_value", "id": owner},
                note="non-sprite owner value is preserved and not remapped",
            ))
        localize_extra(item, "sprite", local_id)
        blood = _blood(item)
        if blood is not None:
            for field, relation in (("target", "target"), ("burn_source", "burn_source")):
                target = blood[field]
                authored_reference = (
                    field == "target" and bool(blood["dude_flag_4"]) and target > 0
                ) or (
                    field == "burn_source" and blood["burn_time"] > 0 and target >= 0
                )
                if not authored_reference:
                    relationships.append(FragmentRelationship(
                        "system_global", "runtime_state", _fragment_ref("sprite", local_id),
                        f"blood.fields.{field}",
                        {"space": "runtime", "kind": "sprite_index_value", "id": target},
                        note=(
                            "NBlood resets ordinary AI targets during aiInitSprite; "
                            "burn_source is inactive when burn_time is zero"
                        ),
                    ))
                    continue
                if not 0 <= target < len(level.sprites):
                    if target >= 0:
                        relationships.append(FragmentRelationship(
                            "system_global", relation, _fragment_ref("sprite", local_id),
                            f"blood.fields.{field}",
                            {"space": "system", "kind": "sprite_reference_value", "id": target},
                            note="out-of-range value is preserved and not remapped",
                        ))
                    continue
                if target in sprite_map.source_to_fragment:
                    blood[field] = sprite_map.localize(target)
                    relationships.append(FragmentRelationship(
                        "internal_reference", relation, _fragment_ref("sprite", local_id),
                        f"blood.fields.{field}", _fragment_ref("sprite", blood[field]),
                    ))
                else:
                    blood[field] = -1
                    preserve("sprite", local_id, f"blood.fields.{field}", target, -1, "external_ownership")
                    relationships.append(FragmentRelationship(
                        "external_ownership", relation, _fragment_ref("sprite", local_id),
                        f"blood.fields.{field}", _source_ref("sprite", target),
                    ))
        sprites.append(item)

    selected_objects = {
        (kind, source)
        for kind, mapping in (("sector", sector_map), ("wall", wall_map), ("sprite", sprite_map))
        for source in mapping.source_to_fragment
    }
    transmitters, receivers = _channel_endpoints(level)

    def endpoint_ref(endpoint: tuple[str, int]) -> dict[str, Any]:
        kind, source_id = endpoint
        mapping = maps[kind]
        return _fragment_ref(kind, mapping.localize(source_id)) if endpoint in selected_objects else _source_ref(kind, source_id)

    channels = sorted(set(transmitters) | set(receivers))
    for channel in channels:
        selected_tx = [value for value in transmitters.get(channel, []) if value in selected_objects]
        selected_rx = [value for value in receivers.get(channel, []) if value in selected_objects]
        if not selected_tx and not selected_rx:
            continue
        if channel in SYSTEM_CHANNELS:
            for endpoint in selected_tx:
                relationships.append(FragmentRelationship(
                    "system_global", "channel", endpoint_ref(endpoint), "blood.fields.tx_id",
                    _system_ref(channel), direction="outgoing", channel=channel,
                ))
            for endpoint in selected_rx:
                relationships.append(FragmentRelationship(
                    "system_global", "channel", _system_ref(channel), "blood.fields.rx_id",
                    endpoint_ref(endpoint), direction="incoming", channel=channel,
                ))
            continue
        external_tx = [value for value in transmitters.get(channel, []) if value not in selected_objects]
        external_rx = [value for value in receivers.get(channel, []) if value not in selected_objects]
        for tx in selected_tx:
            if selected_rx:
                for rx in selected_rx:
                    relationships.append(FragmentRelationship(
                        "internal_reference", "trigger", endpoint_ref(tx), "blood.fields.tx_id",
                        endpoint_ref(rx), direction="outgoing", channel=channel,
                    ))
            for rx in external_rx:
                relationships.append(FragmentRelationship(
                    "external_trigger", "trigger", endpoint_ref(tx), "blood.fields.tx_id",
                    endpoint_ref(rx), direction="outgoing", channel=channel,
                ))
            if not selected_rx and not external_rx:
                relationships.append(FragmentRelationship(
                    "external_trigger", "trigger", endpoint_ref(tx), "blood.fields.tx_id",
                    {"space": "source", "kind": "channel", "id": channel, "status": "no_receiver"},
                    direction="outgoing", channel=channel,
                    note="TX without RX is game-valid; dependency remains unresolved",
                ))
        for rx in selected_rx:
            for tx in external_tx:
                relationships.append(FragmentRelationship(
                    "external_trigger", "trigger", endpoint_ref(tx), "blood.fields.tx_id",
                    endpoint_ref(rx), direction="incoming", channel=channel,
                ))
            if not selected_tx and not external_tx:
                relationships.append(FragmentRelationship(
                    "external_trigger", "trigger",
                    {"space": "source", "kind": "channel", "id": channel, "status": "no_transmitter"},
                    "blood.fields.rx_id", endpoint_ref(rx), direction="incoming", channel=channel,
                    note="RX without TX is game-valid; dependency remains unresolved",
                ))

    return LevelFragment(
        source={
            "schema": level.schema, "schema_version": level.schema_version,
            "source_crc32": level.metadata.get("source_crc32"),
            "ir_sha256": hashlib.sha256(
                json.dumps(level.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
            "map_version": level.metadata.get("map_version"),
            "counts": {"sectors": len(level.sectors), "walls": len(level.walls), "sprites": len(level.sprites)},
            "selected_sector_ids": selected,
        },
        index_maps=maps, sectors=sectors, walls=walls, sprites=sprites,
        relationships=relationships, preserved_references=preserved,
    )


def extract_behavior_closed_fragment(
    level: LevelIR,
    sector_ids: Iterable[int],
    *,
    max_sectors: int = 256,
) -> BehaviorClosureResult:
    """Extract sectors and recursively include their resolvable gameplay dependencies.

    Geometry portals remain boundaries. Gameplay references are followed to the
    sector owning the referenced sector, wall, or sprite. Game-valid channels
    without an endpoint and malformed/out-of-range references remain explicit.
    """
    requested = sorted(set(int(value) for value in sector_ids))
    if not requested:
        raise FragmentError("at least one sector must be selected")
    if max_sectors < len(requested):
        raise FragmentError(
            f"requested selection has {len(requested)} sectors, exceeding max_sectors={max_sectors}"
        )

    wall_owners: list[int | None] = [None] * len(level.walls)
    for sector_id, sector in enumerate(level.sectors):
        first = int(sector["fields"]["wall_ptr"])
        count = int(sector["fields"]["wall_count"])
        for wall_id in range(first, first + count):
            if not 0 <= wall_id < len(wall_owners):
                raise FragmentError(f"sector {sector_id} has an invalid wall range")
            if wall_owners[wall_id] is not None:
                raise FragmentError(f"wall {wall_id} is owned by multiple sectors")
            wall_owners[wall_id] = sector_id

    def owning_sector(reference: dict[str, Any]) -> int | None:
        if reference.get("space") != "source" or "id" not in reference:
            return None
        identifier = int(reference["id"])
        kind = reference.get("kind")
        if kind == "sector" and 0 <= identifier < len(level.sectors):
            return identifier
        if kind == "wall" and 0 <= identifier < len(wall_owners):
            return wall_owners[identifier]
        if kind == "sprite" and 0 <= identifier < len(level.sprites):
            sector = int(level.sprites[identifier]["fields"]["sector"])
            return sector if 0 <= sector < len(level.sectors) else None
        return None

    selected = set(requested)
    additions: list[dict[str, Any]] = []
    gameplay_classes = {"external_trigger", "external_marker", "external_ownership"}
    while True:
        fragment = extract_fragment(level, selected)
        discovered: dict[int, list[dict[str, Any]]] = {}
        for relationship in fragment.relationships:
            if relationship.classification not in gameplay_classes:
                continue
            for role, reference in (
                ("source", relationship.source), ("target", relationship.target),
            ):
                sector_id = owning_sector(reference)
                if sector_id is None or sector_id in selected:
                    continue
                discovered.setdefault(sector_id, []).append({
                    "classification": relationship.classification,
                    "relation": relationship.relation,
                    "role": role,
                    "reference": dict(reference),
                    "channel": relationship.channel,
                })
        if not discovered:
            break
        if len(selected) + len(discovered) > max_sectors:
            raise FragmentError(
                "behavior closure would exceed "
                f"max_sectors={max_sectors}; selected={len(selected)}, next={sorted(discovered)}"
            )
        for sector_id in sorted(discovered):
            additions.append({"sector_id": sector_id, "reasons": discovered[sector_id]})
            selected.add(sector_id)

    unresolved = [
        relationship for relationship in fragment.relationships
        if relationship.classification in gameplay_classes
    ]
    return BehaviorClosureResult(
        fragment=fragment,
        requested_sector_ids=requested,
        selected_sector_ids=sorted(selected),
        additions=additions,
        unresolved_relationships=unresolved,
    )


def _path_get(item: dict[str, Any], path: str) -> int:
    value: Any = item
    for component in path.split("."):
        value = value[component]
    return int(value)


def _path_set(item: dict[str, Any], path: str, value: int) -> None:
    target: Any = item
    components = path.split(".")
    for component in components[:-1]:
        target = target[component]
    target[components[-1]] = value


def apply_fragment_in_place(level: LevelIR, fragment: LevelFragment) -> LevelIR:
    """Apply a fragment back to its source indices, restoring detached dependencies.

    This is intentionally a same-source operation. Cross-map insertion and channel
    allocation belong to the next composition milestone.
    """
    expected_counts = fragment.source["counts"]
    actual_counts = {"sectors": len(level.sectors), "walls": len(level.walls), "sprites": len(level.sprites)}
    if actual_counts != expected_counts:
        raise FragmentError(f"source counts differ: expected {expected_counts}, got {actual_counts}")
    expected_crc = fragment.source.get("source_crc32")
    if expected_crc and level.metadata.get("source_crc32") != expected_crc:
        raise FragmentError("fragment source CRC does not match target LevelIR")
    expected_hash = fragment.source.get("ir_sha256")
    actual_hash = hashlib.sha256(
        json.dumps(level.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if expected_hash and actual_hash != expected_hash:
        raise FragmentError("fragment source IR fingerprint does not match target LevelIR")

    result = copy.deepcopy(level)
    preserved = {(p.object_kind, p.fragment_id, p.path): p for p in fragment.preserved_references}
    runtime_sprite_fields = {
        (int(relationship.source["id"]), relationship.field.rsplit(".", 1)[-1])
        for relationship in fragment.relationships
        if relationship.classification == "system_global"
        and relationship.relation == "runtime_state"
        and relationship.source.get("space") == "fragment"
        and relationship.source.get("kind") == "sprite"
    }

    def restore_item(kind: str, fragment_item: dict[str, Any]) -> dict[str, Any]:
        item = copy.deepcopy(fragment_item)
        local_id = int(item["id"])
        item.pop("source_id", None)
        item["id"] = fragment.index_maps[kind].restore(local_id)
        fields = item["fields"]
        if fields["extra"] > 0:
            fields["extra"] = fragment.index_maps["x" + kind].restore(fields["extra"])
        blood = _blood(item)
        if blood is not None:
            entry = preserved[(kind, local_id, "blood.fields.reference")]
            if blood["reference"] == entry.localized_value:
                blood["reference"] = entry.source_value
        return item

    for fragment_item in fragment.sectors:
        local_id = int(fragment_item["id"])
        item = restore_item("sector", fragment_item)
        fields = item["fields"]
        fields["wall_ptr"] = fragment.index_maps["wall"].restore(fields["wall_ptr"])
        blood = _blood(item)
        if blood is not None:
            for field in ("marker_0", "marker_1"):
                path = f"blood.fields.{field}"
                entry = preserved.get(("sector", local_id, path))
                if entry is not None and blood[field] == entry.localized_value:
                    blood[field] = entry.source_value
                elif blood[field] >= 0:
                    blood[field] = fragment.index_maps["sprite"].restore(blood[field])
        result.sectors[item["id"]] = item

    for fragment_item in fragment.walls:
        local_id = int(fragment_item["id"])
        item = restore_item("wall", fragment_item)
        fields = item["fields"]
        fields["point2"] = fragment.index_maps["wall"].restore(fields["point2"])
        for field, map_name in (("next_wall", "wall"), ("next_sector", "sector")):
            path = f"fields.{field}"
            entry = preserved.get(("wall", local_id, path))
            if entry is not None and fields[field] == entry.localized_value:
                fields[field] = entry.source_value
            elif fields[field] >= 0:
                fields[field] = fragment.index_maps[map_name].restore(fields[field])
        result.walls[item["id"]] = item

    for fragment_item in fragment.sprites:
        local_id = int(fragment_item["id"])
        item = restore_item("sprite", fragment_item)
        fields = item["fields"]
        fields["sector"] = fragment.index_maps["sector"].restore(fields["sector"])
        index_entry = preserved[("sprite", local_id, "fields.index")]
        if fields["index"] == index_entry.localized_value:
            fields["index"] = index_entry.source_value
        owner_entry = preserved.get(("sprite", local_id, "fields.owner"))
        if owner_entry is not None and fields["owner"] == owner_entry.localized_value:
            fields["owner"] = owner_entry.source_value
        elif fields["owner"] >= 0:
            fields["owner"] = fragment.index_maps["sprite"].restore(fields["owner"])
        blood = _blood(item)
        if blood is not None:
            for field in ("target", "burn_source"):
                path = f"blood.fields.{field}"
                entry = preserved.get(("sprite", local_id, path))
                if entry is not None and blood[field] == entry.localized_value:
                    blood[field] = entry.source_value
                elif blood[field] >= 0 and (local_id, field) not in runtime_sprite_fields:
                    blood[field] = fragment.index_maps["sprite"].restore(blood[field])
        result.sprites[item["id"]] = item

    return result
