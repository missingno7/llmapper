"""Declared viewpoint poses and the temporary MAP variants that realize them.

A viewpoint is a request to look at one authored place from one stated pose.
Preparing a variant is deliberately pure and dependency-free so viewpoint
declaration, validation, and manifest generation stay testable without a game
executable.  Only :mod:`bloodmap.oracle` runs the engine.

The single mutation a variant is allowed to make is the player-start pose: the
header start fields and every native ``kMarkerPlayerStart`` sprite.  Everything
else -- sectors, walls, wall references, sprite inventory, extended records --
is preserved, so a captured view is evidence about the candidate MAP and not
about a differently-built map.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from .model import LevelIR
from .planar_geom import Point, point_in_loop

SCHEMA = "llmapper.viewpoint-manifest"
SCHEMA_VERSION = 1

# Native Blood player-start marker. Blood spawns from this sprite, not from the
# header, so a viewpoint that moved only the header would not move the camera.
PLAYER_START_TYPE = 1

PURPOSES = {
    "player_start",
    "transition_approach",
    "assembly_center",
    "reverse_view",
    "vertical_relationship",
    "landmark",
}


class ViewpointError(ValueError):
    """A declared viewpoint cannot be realized against this level."""


@dataclass(frozen=True)
class ViewpointSpec:
    """One declared camera pose inside a named authored region."""

    viewpoint_id: str
    purpose: str
    region_id: str
    x: int
    y: int
    z: int
    angle: int
    note: str = ""
    #: Engine ``Aim_Up`` taps applied before the frame is taken; negative aims
    #: down.  A camera locked to level pitch cannot review a ceiling or a sky,
    #: which is how this pilot shipped four iterations without once looking at
    #: the upper half of any of its spaces.  Pitch is not part of the MAP: it is
    #: a capture control, so it never changes the variant and never appears in
    #: the variant diff.
    pitch: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "viewpoint_id": self.viewpoint_id,
            "purpose": self.purpose,
            "region_id": self.region_id,
            "pose": {"x": int(self.x), "y": int(self.y), "z": int(self.z), "angle": int(self.angle)},
            "pitch": int(self.pitch),
            "note": self.note,
        }


def _sector_loops(level: LevelIR, sector_id: int) -> list[list[Point]]:
    """Rebuild a sector's wall loops from point2 links; wall order is not assumed."""
    fields = level.sectors[sector_id]["fields"]
    first, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    members = set(range(first, first + count))
    loops: list[list[Point]] = []
    unseen = set(members)
    while unseen:
        start = min(unseen)
        loop: list[Point] = []
        current = start
        while True:
            if current not in unseen:
                break
            unseen.discard(current)
            wall = level.walls[current]["fields"]
            loop.append((int(wall["x"]), int(wall["y"])))
            current = int(wall["point2"])
            if current == start:
                break
            if current not in members:
                raise ViewpointError(f"sector:{sector_id} wall loop leaves the sector at wall:{current}")
        if len(loop) >= 3:
            loops.append(loop)
    if not loops:
        raise ViewpointError(f"sector:{sector_id} has no usable wall loop")
    # Largest first, so loops[0] is the outline and the rest are holes.
    # Tracing order is wall order, and Build does not guarantee the outer
    # loop owns the lowest wall index: BB4 sector 41 traces a hole of
    # 1048576 before an outline of 22077276, and E1M1 has seven such
    # sectors.  Callers that read loops[0] as the outline -- _contains,
    # interior_point, the look.py harnesses -- then accepted points that
    # sit in the hole, which is outside the sector, and the observer was
    # handed cameras standing in solid space.
    loops.sort(key=lambda loop: abs(_loop_area2(loop)), reverse=True)
    return loops


def _loop_area2(loop: list[Point]) -> int:
    """Twice the signed area; sign is winding, magnitude orders the loops."""
    total = 0
    for index, point in enumerate(loop):
        nxt = loop[(index + 1) % len(loop)]
        total += point[0] * nxt[1] - nxt[0] * point[1]
    return total


def _contains(level: LevelIR, sector_id: int, x: int, y: int) -> bool:
    """Point-in-sector with holes: inside the outer loop and outside every hole."""
    loops = _sector_loops(level, sector_id)
    outer, holes = loops[0], loops[1:]
    if point_in_loop((x, y), tuple(outer)) == 0:
        return False
    return all(point_in_loop((x, y), tuple(hole)) != 1 for hole in holes)


def resolve_viewpoint(
    level: LevelIR, spec: ViewpointSpec, *, allocations: dict[str, int],
) -> dict[str, Any]:
    """Validate one declared pose and bind it to an exact sector reference."""
    if spec.purpose not in PURPOSES:
        raise ViewpointError(f"unknown viewpoint purpose {spec.purpose!r}")
    if spec.region_id not in allocations:
        raise ViewpointError(f"viewpoint {spec.viewpoint_id} names unknown region {spec.region_id!r}")
    sector_id = int(allocations[spec.region_id])
    if not 0 <= sector_id < len(level.sectors):
        raise ViewpointError(f"viewpoint {spec.viewpoint_id} resolved to invalid sector {sector_id}")
    if not _contains(level, sector_id, int(spec.x), int(spec.y)):
        raise ViewpointError(
            f"viewpoint {spec.viewpoint_id} pose ({spec.x}, {spec.y}) is not inside sector:{sector_id}"
        )
    fields = level.sectors[sector_id]["fields"]
    floor_z, ceiling_z = int(fields["floor_z"]), int(fields["ceiling_z"])
    if not ceiling_z <= int(spec.z) <= floor_z:
        raise ViewpointError(
            f"viewpoint {spec.viewpoint_id} z={spec.z} is outside sector:{sector_id} "
            f"[{ceiling_z}, {floor_z}]"
        )
    return {
        **spec.to_dict(),
        "sector": f"sector:{sector_id}",
        "sector_id": sector_id,
        "sector_floor_z": floor_z,
        "sector_ceiling_z": ceiling_z,
    }


def start_marker_sprites(level: LevelIR) -> list[int]:
    return [
        index for index, sprite in enumerate(level.sprites)
        if int(sprite["fields"]["type"]) == PLAYER_START_TYPE
    ]


def apply_viewpoint(level: LevelIR, resolved: dict[str, Any]) -> LevelIR:
    """Return a copy whose only difference is the player-start pose."""
    variant = LevelIR.from_dict(deepcopy(level.to_dict()))
    pose = resolved["pose"]
    sector_id = int(resolved["sector_id"])
    variant.player_start = {
        "x": int(pose["x"]), "y": int(pose["y"]), "z": int(pose["z"]),
        "angle": int(pose["angle"]) & 2047, "sector": sector_id,
    }
    for index in start_marker_sprites(variant):
        fields = variant.sprites[index]["fields"]
        fields["x"] = int(pose["x"])
        fields["y"] = int(pose["y"])
        fields["z"] = int(pose["z"])
        fields["angle"] = int(pose["angle"]) & 2047
        fields["sector"] = sector_id
    return variant


POSE_SPRITE_FIELDS = ("x", "y", "z", "angle", "sector")


def viewpoint_variant_diff(base: LevelIR, variant: LevelIR) -> dict[str, Any]:
    """Enumerate every difference between a candidate and one of its variants.

    Used as a gate, not as a description: anything outside the player-start pose
    is reported so a caller can refuse to treat the capture as evidence.
    """
    base_document, variant_document = base.to_dict(), variant.to_dict()
    unexpected: list[str] = []
    for key in ("metadata", "sky", "sectors", "walls"):
        if base_document[key] != variant_document[key]:
            unexpected.append(key)
    markers = set(start_marker_sprites(base))
    if markers != set(start_marker_sprites(variant)):
        unexpected.append("player_start_marker_inventory")
    if len(base.sprites) != len(variant.sprites):
        unexpected.append("sprite_count")
    else:
        for index, (left, right) in enumerate(zip(base.sprites, variant.sprites)):
            if left == right:
                continue
            if index not in markers:
                unexpected.append(f"sprite:{index}")
                continue
            changed = {
                key for key in left["fields"]
                if left["fields"][key] != right["fields"][key]
            }
            if not changed <= set(POSE_SPRITE_FIELDS) or left.get("extra") != right.get("extra"):
                unexpected.append(f"sprite:{index}")
    return {
        "player_start_changed": base_document["player_start"] != variant_document["player_start"],
        "player_start_markers_moved": sorted(
            index for index in markers if base.sprites[index] != variant.sprites[index]
        ),
        "unexpected_changes": sorted(set(unexpected)),
        "variant_is_pose_only": not unexpected,
    }


def prepare_viewpoints(
    level: LevelIR,
    specs: Sequence[ViewpointSpec],
    *,
    allocations: dict[str, int],
) -> list[dict[str, Any]]:
    """Resolve, realize, and self-check every declared viewpoint."""
    seen: set[str] = set()
    prepared: list[dict[str, Any]] = []
    for spec in specs:
        if spec.viewpoint_id in seen:
            raise ViewpointError(f"duplicate viewpoint id {spec.viewpoint_id!r}")
        seen.add(spec.viewpoint_id)
        resolved = resolve_viewpoint(level, spec, allocations=allocations)
        variant = apply_viewpoint(level, resolved)
        diff = viewpoint_variant_diff(level, variant)
        if not diff["variant_is_pose_only"]:
            raise ViewpointError(
                f"viewpoint {spec.viewpoint_id} changed more than the start pose: "
                f"{diff['unexpected_changes']}"
            )
        prepared.append({"resolved": resolved, "level": variant, "diff": diff})
    return prepared


def viewpoint_manifest(
    level: LevelIR,
    specs: Sequence[ViewpointSpec],
    *,
    allocations: dict[str, int],
    map_sha256: str,
) -> dict[str, Any]:
    """Deterministic declaration of what will be captured, before any engine runs."""
    prepared = prepare_viewpoints(level, specs, allocations=allocations)
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "candidate_map_sha256": map_sha256,
        "player_start_marker_sprites": [f"sprite:{index}" for index in start_marker_sprites(level)],
        "viewpoints": [
            {**item["resolved"], "variant_is_pose_only": item["diff"]["variant_is_pose_only"]}
            for item in prepared
        ],
        "limitations": [
            "a viewpoint states where the camera was placed, not what a player would do",
            "image evidence requires the external engine; this manifest alone proves nothing visual",
        ],
    }


def viewpoints_from_records(records: Iterable[dict[str, Any]]) -> list[ViewpointSpec]:
    """Rebuild specs from serialized declarations (round-trip for stored packets)."""
    result: list[ViewpointSpec] = []
    for record in records:
        pose = record["pose"]
        result.append(ViewpointSpec(
            viewpoint_id=str(record["viewpoint_id"]),
            purpose=str(record["purpose"]),
            region_id=str(record["region_id"]),
            x=int(pose["x"]), y=int(pose["y"]), z=int(pose["z"]), angle=int(pose["angle"]),
            pitch=int(record.get("pitch", 0)),
            note=str(record.get("note", "")),
        ))
    return result
