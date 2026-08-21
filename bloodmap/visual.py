"""Structured visual observation through the XMapEdit fork.

This module is the llmapper half of a bridge:

.. code-block:: text

    LevelProgram node
        -> compiler allocations   (which sectors and walls a source node owns)
        -> MAP
        -> xmapedit-observe       (what the renderer actually painted)
        -> visible native ids
        -> visible source nodes

The division of labour is deliberate and narrow.  The renderer is asked only
for what *it* alone knows -- which native objects survived the portal flood and
the front-to-back clipping, and how much of the frame each one ended up
covering.  Everything else -- distances, player-relative sizes, names, what a
node is for -- llmapper already computes better and is not asked for again.

Nothing here injects a key or focuses a window.  A pose is a number in a JSON
file.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .model import LevelIR
from .player_space import player_profile

SCHEMA = "llmapper.xmapedit-visual-observation"
SCHEMA_VERSION = 1

REQUEST_SCHEMA = "llmapper.xmapedit-observation-request"
REQUEST_SCHEMA_VERSION = 1

#: Surface kinds the observer reports, in the order it defines them.
SURFACE_KINDS = ("wall", "upper", "lower", "masked", "floor", "ceiling", "sky", "sprite")

#: Kinds that are architecture rather than decoration.  A room that is visible
#: only through one of its sprites is not really visible.
STRUCTURAL_KINDS = ("wall", "upper", "lower", "masked", "floor", "ceiling", "sky")


class ObservationError(RuntimeError):
    """The observer could not be run, or answered with something unusable."""


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Viewpoint:
    """One camera pose, and what it is a view *of*.

    ``node`` and ``purpose`` never reach the renderer.  They are llmapper's
    own bookkeeping, carried through so a manifest can be read without the
    plan that produced it.
    """

    view_id: str
    x: int
    y: int
    z: int
    angle: int = 0
    horiz: int = 100
    sector: int | None = None
    node: str = ""
    purpose: str = ""
    screenshot: bool = False
    note: str = ""

    def to_request(self) -> dict[str, Any]:
        """Only the fields the observer reads, in a fixed order."""
        record: dict[str, Any] = {
            "id": self.view_id,
            "x": int(self.x),
            "y": int(self.y),
            "z": int(self.z),
            "angle": int(self.angle) & 2047,
            "horiz": int(self.horiz),
        }
        if self.sector is not None:
            record["sector"] = int(self.sector)
        record["screenshot"] = bool(self.screenshot)
        return record

    def to_dict(self) -> dict[str, Any]:
        record = self.to_request()
        record.update({"node": self.node, "purpose": self.purpose, "note": self.note})
        return record


@dataclass(frozen=True)
class ObservationRequest:
    """A batch: one map, loaded once, and every pose worth looking from."""

    map_path: str
    output_dir: str
    resource_dir: str = "reference/blood"
    viewpoints: tuple[Viewpoint, ...] = ()
    width: int = 320
    height: int = 200
    screenshots: bool = False
    brightness: int = 0
    rff: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """The wire form.  Deterministic: same request, same bytes."""
        record: dict[str, Any] = {
            "$schema": REQUEST_SCHEMA,
            "schema_version": REQUEST_SCHEMA_VERSION,
            "map": _posix(self.map_path),
            "resource_dir": _posix(self.resource_dir),
            "output": _posix(self.output_dir),
            "width": int(self.width),
            "height": int(self.height),
            "screenshots": bool(self.screenshots),
            "brightness": int(self.brightness),
        }
        if self.rff:
            record["rff"] = _posix(self.rff)
        record["views"] = [view.to_request() for view in self.viewpoints]
        return record

    def plan(self) -> dict[str, Any]:
        """The request plus the llmapper-side bookkeeping the renderer ignores."""
        record = self.to_dict()
        record["views"] = [view.to_dict() for view in self.viewpoints]
        return record

    def write(self, path: str | os.PathLike[str]) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=1) + "\n", encoding="utf-8")
        return target

    def with_screenshots(self, view_ids: Iterable[str]) -> "ObservationRequest":
        """Turn on frames for a named few, which is the intended way to use them."""
        wanted = set(view_ids)
        return replace(
            self,
            screenshots=bool(wanted),
            viewpoints=tuple(
                replace(view, screenshot=view.view_id in wanted) for view in self.viewpoints
            ),
        )


def _posix(path: str | os.PathLike[str]) -> str:
    return str(path).replace("\\", "/")


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------

def default_binary(root: str | os.PathLike[str] | None = None) -> Path:
    """Where the fork puts the observer when it is built in place."""
    base = Path(root) if root is not None else Path(__file__).resolve().parent.parent
    name = "xmapedit-observe.exe" if os.name == "nt" else "xmapedit-observe"
    return base / "xmapedit" / "bin" / name


def run_observation(
    request: ObservationRequest,
    *,
    binary: str | os.PathLike[str] | None = None,
    request_path: str | os.PathLike[str] | None = None,
    timeout: float = 600.0,
) -> "ObservationManifest":
    """Run one batch and read the manifest back.

    One process, one map load, every view.  Raises rather than returning a
    half-answer, because a missing view is not the same as an empty one.
    """
    exe = Path(binary) if binary is not None else default_binary()
    if not exe.exists():
        raise ObservationError(
            f"{exe} is not built; run: mingw32-make -C xmapedit/src_blood/observe"
        )
    path = Path(request_path) if request_path is not None else Path(request.output_dir) / "request.json"
    request.write(path)
    try:
        completed = subprocess.run(
            [str(exe), str(path)],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise ObservationError(f"{exe.name} did not finish within {timeout:g}s") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip().splitlines()
        raise ObservationError(
            f"{exe.name} exited {completed.returncode}: {detail[-1] if detail else 'no output'}"
        )
    manifest_path = Path(request.output_dir) / "observation.json"
    if not manifest_path.exists():
        raise ObservationError(f"{exe.name} wrote no manifest at {manifest_path}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return ObservationManifest(data=data, request=request, path=manifest_path)


@dataclass
class ObservationManifest:
    """The observer's answer, indexed by view id."""

    data: dict[str, Any]
    request: ObservationRequest | None = None
    path: Path | None = None

    def __post_init__(self) -> None:
        if self.data.get("$schema") != SCHEMA:
            raise ObservationError(f"not an observation manifest: {self.data.get('$schema')!r}")
        seen: dict[str, dict[str, Any]] = {}
        for view in self.data.get("views", []):
            view_id = view.get("id")
            if view_id in seen:
                raise ObservationError(f"view {view_id!r} appears more than once")
            seen[view_id] = view
        self._views = seen

    @property
    def views(self) -> list[dict[str, Any]]:
        return list(self.data.get("views", []))

    @property
    def view_ids(self) -> list[str]:
        return list(self._views)

    def view(self, view_id: str) -> dict[str, Any]:
        try:
            return self._views[view_id]
        except KeyError:
            raise ObservationError(f"no view {view_id!r} in this manifest") from None

    @property
    def limitations(self) -> list[str]:
        return list(self.data.get("limitations", []))

    @property
    def timing(self) -> dict[str, Any]:
        return dict(self.data.get("timing_ms", {}))

    def invalid(self) -> list[dict[str, Any]]:
        """Poses the observer refused, with its reason.  It never moves a camera."""
        return [view for view in self.views if view.get("status") != "ok"]


# ---------------------------------------------------------------------------
# Source / native mapping
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NodeAllocation:
    """Which native objects one source node owns."""

    node: str
    path: tuple[str, ...]
    kind: str = "space"
    sectors: frozenset[int] = frozenset()
    walls: frozenset[int] = frozenset()
    sprites: frozenset[int] = frozenset()

    def to_dict(self) -> dict[str, Any]:
        return {
            "node": self.node,
            "path": list(self.path),
            "kind": self.kind,
            "sectors": sorted(self.sectors),
            "walls": sorted(self.walls),
            "sprites": sorted(self.sprites),
        }


class SourceMap:
    """The join between a source hierarchy and the native ids a renderer reports.

    Only leaves own native objects.  An ancestor is visible when one of its
    leaves is, which is what makes a parent overview readable: the observer
    reports 40 sectors and this reports "the manor, through its lobby".
    """

    def __init__(self, allocations: Sequence[NodeAllocation], *,
                 owner_kinds: Sequence[str] | None = None) -> None:
        self.allocations: dict[str, NodeAllocation] = {a.node: a for a in allocations}
        self.owner_kinds = tuple(owner_kinds) if owner_kinds is not None else None
        self.sector_owner: dict[int, str] = {}
        self.wall_owner: dict[int, str] = {}
        self.sprite_owner: dict[int, str] = {}
        for alloc in allocations:
            # Some kinds are overlays rather than places.  A recovered staircase
            # runs through sectors that a space already owns, and answering
            # "which node is this sector" with the stair would lose the room.
            if self.owner_kinds is not None and alloc.kind not in self.owner_kinds:
                continue
            for sector_id in alloc.sectors:
                self.sector_owner.setdefault(sector_id, alloc.node)
            for wall_id in alloc.walls:
                self.wall_owner.setdefault(wall_id, alloc.node)
            for sprite_id in alloc.sprites:
                self.sprite_owner.setdefault(sprite_id, alloc.node)

    # -- construction ------------------------------------------------------
    @classmethod
    def from_level_program(cls, program: Any, compiled: Any) -> "SourceMap":
        """From a generated level: the compiler knows exactly what it allocated."""
        allocations = compiled.allocations
        placements = getattr(compiled, "placement_sprites", {}) or {}
        walls_of_sector = _walls_by_sector(compiled.level)
        records: list[NodeAllocation] = []

        for room in program.rooms():
            node = room.path()
            path = tuple(node.split("/"))
            alloc = allocations.get(room.region_id)
            sectors = {alloc.sector_id} if alloc else set()
            walls = set(alloc.wall_ids) if alloc else set()
            records.append(NodeAllocation(node, path, "room", frozenset(sectors), frozenset(walls)))

            for declaration in room.structures:
                prefix = f"region:{declaration.structure_id}"
                own_sectors: set[int] = set()
                own_walls: set[int] = set()
                for region_id, item in allocations.items():
                    if region_id == prefix or region_id.startswith(prefix + ":"):
                        own_sectors.add(item.sector_id)
                        own_walls.update(item.wall_ids)
                if not own_sectors:
                    continue
                child = f"{node}/{declaration.structure_id}"
                records.append(NodeAllocation(
                    child, tuple(child.split("/")), declaration.kind,
                    frozenset(own_sectors), frozenset(own_walls),
                ))

        # Details sit under whichever node placed them, which is what the
        # placement id records.
        by_node: dict[str, set[int]] = {}
        known = {record.node for record in records}
        for placement_id, sprite_index in placements.items():
            owner = _owner_of_placement(placement_id, known)
            if owner is None:
                continue
            by_node.setdefault(owner, set()).add(int(sprite_index))
        records = [
            replace(record, sprites=frozenset(by_node.get(record.node, ())))
            for record in records
        ]
        # Sectors a structure created but no room claimed still need walls.
        records = [
            replace(record, walls=record.walls or frozenset(
                wall for sector_id in record.sectors for wall in walls_of_sector.get(sector_id, ())
            ))
            for record in records
        ]
        return cls(records)

    @classmethod
    def from_hierarchy(cls, hierarchy: Mapping[str, Any], level: LevelIR) -> "SourceMap":
        """From a decompiled original: the recovered tree is the source we have."""
        nodes = {node["id"]: node for node in hierarchy.get("nodes", [])}
        walls_of_sector = _walls_by_sector(level)

        def owned(node: Mapping[str, Any], key: str) -> list[int]:
            """Two shapes exist: the live hierarchy nests ids under ``sources``,
            the committed reading view lists them at the top level."""
            if key in node:
                return [int(v) for v in node[key]]
            return [int(v) for v in (node.get("sources") or {}).get(key, [])]
        sprites_of_sector: dict[int, set[int]] = {}
        for index, sprite in enumerate(level.sprites):
            sector_id = int(sprite["fields"].get("sector", -1))
            sprites_of_sector.setdefault(sector_id, set()).add(index)

        def path_of(node_id: str) -> tuple[str, ...]:
            parts: list[str] = []
            current: str | None = node_id
            seen: set[str] = set()
            while current and current not in seen:
                seen.add(current)
                parts.append(current)
                current = nodes.get(current, {}).get("parent")
            return tuple(reversed(parts))

        # A node owns the sectors none of its descendants claim.  Requiring a
        # node to be childless instead loses every space that has a detail
        # group hanging off it, which on E2M3 is half of them.
        claimed_by_children: dict[str, set[int]] = {}
        for node_id, node in nodes.items():
            for child in node.get("children", []):
                child_node = nodes.get(child)
                if child_node is None:
                    continue
                claimed_by_children.setdefault(node_id, set()).update(
                    owned(child_node, "sectors")
                )

        records: list[NodeAllocation] = []
        for node_id, node in nodes.items():
            sectors = set(owned(node, "sectors"))
            sectors -= claimed_by_children.get(node_id, set())
            if not sectors:
                continue
            walls = {w for s in sectors for w in walls_of_sector.get(s, ())}
            sprites = {p for s in sectors for p in sprites_of_sector.get(s, ())}
            records.append(NodeAllocation(
                node_id, path_of(node_id), str(node.get("kind", "space")),
                frozenset(sectors), frozenset(walls), frozenset(sprites),
            ))
        kinds = {record.kind for record in records}
        return cls(records, owner_kinds=("space",) if "space" in kinds else None)

    # -- reading -----------------------------------------------------------
    def owner(self, *, sector: int | None = None, wall: int | None = None,
              sprite: int | None = None) -> str | None:
        if wall is not None and wall in self.wall_owner:
            return self.wall_owner[wall]
        if sprite is not None and sprite in self.sprite_owner:
            return self.sprite_owner[sprite]
        if sector is not None:
            return self.sector_owner.get(sector)
        return None

    def path_of(self, node: str) -> tuple[str, ...]:
        record = self.allocations.get(node)
        return record.path if record else (node,)

    def to_dict(self) -> dict[str, Any]:
        return {
            "$schema": "llmapper.source-native-allocation",
            "schema_version": 1,
            "owner_kinds": list(self.owner_kinds) if self.owner_kinds else None,
            "nodes": [record.to_dict() for record in
                      sorted(self.allocations.values(), key=lambda r: r.node)],
        }


def _owner_of_placement(placement_id: str, known: set[str]) -> str | None:
    """``placement:<owner path>:<detail>`` and ``placement:<structure>:<deco>:NNN``."""
    if not placement_id.startswith("placement:"):
        return None
    body = placement_id[len("placement:"):]
    parts = body.split(":")
    for cut in range(len(parts), 0, -1):
        candidate = ":".join(parts[:cut])
        if candidate in known:
            return candidate
        matches = [node for node in known if node.endswith("/" + candidate)]
        if len(matches) == 1:
            return matches[0]
    return None


def _walls_by_sector(level: LevelIR) -> dict[int, tuple[int, ...]]:
    result: dict[int, tuple[int, ...]] = {}
    for sector in level.sectors:
        fields = sector["fields"]
        start = int(fields["wall_ptr"])
        count = int(fields["wall_count"])
        result[int(sector["id"])] = tuple(range(start, start + count))
    return result


# ---------------------------------------------------------------------------
# The join
# ---------------------------------------------------------------------------

def join_view(view: Mapping[str, Any], source_map: SourceMap, *,
              level: LevelIR | None = None, profile: str = "blood") -> dict[str, Any]:
    """Turn one view's native ids into source nodes, with prominence and depth.

    Prominence is the renderer's: painted pixels after occlusion, as a fraction
    of the frame.  Depth is llmapper's: measured from the camera to the
    geometry, in player widths, because the renderer has no better answer and
    a derived one is easier to check.
    """
    if view.get("status") != "ok":
        return {
            "status": view.get("status", "unknown"),
            "reason": view.get("reason", ""),
            "visible": [],
            "occluded": [],
        }

    frame = view.get("frame", {})
    frame_pixels = max(1, int(frame.get("pixels", 1)))
    camera = view.get("camera", {})
    unit = player_profile(profile).body_width

    buckets: dict[str, dict[str, Any]] = {}
    for surface in view.get("surfaces", []):
        node = source_map.owner(
            sector=surface.get("sector"), wall=surface.get("wall"),
            sprite=surface.get("sprite"),
        )
        if node is None:
            node = f"unmapped:sector:{surface.get('sector')}"
        bucket = buckets.setdefault(node, {
            "node": node,
            "path": list(source_map.path_of(node)),
            "pixels": 0,
            "structural_pixels": 0,
            "surfaces": 0,
            "sectors": set(),
            "kinds": {},
            "tiles": {},
        })
        pixels = int(surface.get("pixels", 0))
        kind = str(surface.get("kind", "wall"))
        bucket["pixels"] += pixels
        if kind in STRUCTURAL_KINDS:
            bucket["structural_pixels"] += pixels
        bucket["surfaces"] += 1
        bucket["sectors"].add(int(surface.get("sector", -1)))
        bucket["kinds"][kind] = bucket["kinds"].get(kind, 0) + pixels
        picnum = int(surface.get("picnum", -1))
        bucket["tiles"][picnum] = bucket["tiles"].get(picnum, 0) + pixels

    depths = _sector_depths(camera, level, unit) if level is not None else {}

    visible: list[dict[str, Any]] = []
    for bucket in buckets.values():
        sectors = sorted(s for s in bucket["sectors"] if s >= 0)
        near = [depths[s][0] for s in sectors if s in depths]
        far = [depths[s][1] for s in sectors if s in depths]
        record = {
            "node": bucket["node"],
            "path": bucket["path"],
            "pixels": bucket["pixels"],
            "frame_fraction": round(bucket["pixels"] / frame_pixels, 4),
            "structural_fraction": round(bucket["structural_pixels"] / frame_pixels, 4),
            "surfaces": bucket["surfaces"],
            "sectors": sectors,
            "pixels_by_kind": dict(sorted(bucket["kinds"].items(), key=lambda kv: -kv[1])),
            "dominant_tiles": [
                {"picnum": tile, "pixels": pixels}
                for tile, pixels in sorted(bucket["tiles"].items(), key=lambda kv: -kv[1])[:4]
            ],
        }
        if near:
            record["near_player_widths"] = round(min(near), 2)
            record["far_player_widths"] = round(max(far), 2)
        visible.append(record)
    visible.sort(key=lambda item: (-item["pixels"], item["node"]))

    occluded_nodes: dict[str, int] = {}
    for surface in view.get("occluded", []):
        node = source_map.owner(
            sector=surface.get("sector"), wall=surface.get("wall"),
            sprite=surface.get("sprite"),
        )
        if node is None or node in buckets:
            continue
        occluded_nodes[node] = occluded_nodes.get(node, 0) + 1

    return {
        "status": "ok",
        "visible": visible,
        "occluded": [
            {"node": node, "path": list(source_map.path_of(node)), "surfaces": count}
            for node, count in sorted(occluded_nodes.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        "frame_painted_fraction": round(int(frame.get("painted", 0)) / frame_pixels, 4),
        "sky_fraction": round(int(frame.get("sky_pixels", 0)) / frame_pixels, 4),
    }


def _sector_depths(camera: Mapping[str, Any], level: LevelIR,
                   unit: int) -> dict[int, tuple[float, float]]:
    """Nearest and farthest wall vertex of each sector, in player widths."""
    cx = float(camera.get("x", 0))
    cy = float(camera.get("y", 0))
    result: dict[int, tuple[float, float]] = {}
    walls = level.walls
    for sector in level.sectors:
        fields = sector["fields"]
        start = int(fields["wall_ptr"])
        count = int(fields["wall_count"])
        near = math.inf
        far = 0.0
        for index in range(start, min(start + count, len(walls))):
            wall = walls[index]["fields"]
            dx = float(wall["x"]) - cx
            dy = float(wall["y"]) - cy
            distance = math.hypot(dx, dy) / unit
            near = min(near, distance)
            far = max(far, distance)
        if near is not math.inf:
            result[int(sector["id"])] = (near, far)
    return result


# ---------------------------------------------------------------------------
# Compact summary
# ---------------------------------------------------------------------------

def compact_summary(view: Mapping[str, Any], join: Mapping[str, Any], *,
                    viewpoint: Viewpoint | None = None,
                    max_nodes: int = 6, tile_names: Mapping[int, str] | None = None) -> str:
    """A bounded, decomposed reading of one view.

    Deliberately no score.  "dominant", "prominent", "a trace" are read off the
    frame fraction and say what was measured; whether that is good is the
    reader's question, in the context of a brief this module has never seen.
    """
    lines: list[str] = []
    head = view.get("id", "view")
    if viewpoint is not None and viewpoint.purpose:
        head = f"{head} -- {viewpoint.purpose}"
    lines.append(f"View: {head}")

    if join.get("status") != "ok":
        lines.append(f"  refused: {join.get('reason') or join.get('status')}")
        return "\n".join(lines)

    camera = view.get("camera", {})
    lines.append(
        "  camera: sector {sector}, angle {angle}, horiz {horiz}{derived}".format(
            sector=camera.get("sector"), angle=camera.get("angle"),
            horiz=camera.get("horiz"),
            derived=" (eye height derived)" if camera.get("eye_height_derived") else "",
        )
    )
    if viewpoint is not None and viewpoint.node:
        lines.append(f"  of: {viewpoint.node}")

    visible = list(join.get("visible", []))
    lines.append("  visible:")
    if not visible:
        lines.append("    nothing")
    for record in visible[:max_nodes]:
        depth = ""
        if "near_player_widths" in record:
            depth = " at {near}-{far} PW".format(
                near=record["near_player_widths"], far=record["far_player_widths"],
            )
        lines.append(
            "    {node}: {word}, {pct:.1f}% of frame{depth}".format(
                node=record["node"], word=_prominence(record["frame_fraction"]),
                pct=100 * record["frame_fraction"], depth=depth,
            )
        )
    if len(visible) > max_nodes:
        lines.append(f"    ... and {len(visible) - max_nodes} more, none above "
                     f"{100 * visible[max_nodes]['frame_fraction']:.1f}%")

    occluded = list(join.get("occluded", []))
    if occluded:
        names = ", ".join(item["node"] for item in occluded[:4])
        more = "" if len(occluded) <= 4 else f", and {len(occluded) - 4} more"
        lines.append(f"  reached the renderer but nothing survived: {names}{more}")

    sky = join.get("sky_fraction", 0.0)
    if sky:
        lines.append(f"  sky: {100 * sky:.1f}% of frame")

    tiles: dict[int, int] = {}
    for record in visible:
        for tile in record.get("dominant_tiles", []):
            tiles[tile["picnum"]] = tiles.get(tile["picnum"], 0) + tile["pixels"]
    if tiles:
        top = sorted(tiles.items(), key=lambda kv: -kv[1])[:3]
        rendered = ", ".join(
            f"{(tile_names or {}).get(picnum, 'tile ' + str(picnum))} ({100 * pixels / max(1, int(view.get('frame', {}).get('pixels', 1))):.0f}%)"
            for picnum, pixels in top
        )
        lines.append(f"  dominant surfaces: {rendered}")

    if view.get("diagnostics"):
        for item in view["diagnostics"]:
            lines.append(f"  diagnostic: {item}")
    return "\n".join(lines)


def _prominence(fraction: float) -> str:
    if fraction >= 0.30:
        return "dominant"
    if fraction >= 0.10:
        return "prominent"
    if fraction >= 0.02:
        return "present"
    return "a trace"


# ---------------------------------------------------------------------------
# Aggregation across views
# ---------------------------------------------------------------------------

def covisibility(manifest: ObservationManifest, source_map: SourceMap, *,
                 min_fraction: float = 0.01) -> dict[str, Any]:
    """How often each node is seen from a view taken of another node.

    Evidence toward grouping, and nothing more.  Two rooms that see each other
    from every representative pose are probably one place; that is a hypothesis
    for a reader to accept or reject, not a taxonomy.
    """
    from_node: dict[str, dict[str, int]] = {}
    views_of: dict[str, int] = {}
    plan = {view.view_id: view for view in (manifest.request.viewpoints if manifest.request else ())}

    for view in manifest.views:
        if view.get("status") != "ok":
            continue
        viewpoint = plan.get(view.get("id", ""))
        origin = viewpoint.node if viewpoint and viewpoint.node else None
        if origin is None:
            origin = source_map.sector_owner.get(int(view.get("camera", {}).get("sector", -1)))
        if origin is None:
            continue
        views_of[origin] = views_of.get(origin, 0) + 1
        join = join_view(view, source_map)
        for record in join["visible"]:
            if record["node"] == origin or record["frame_fraction"] < min_fraction:
                continue
            from_node.setdefault(origin, {})
            from_node[origin][record["node"]] = from_node[origin].get(record["node"], 0) + 1

    pairs: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for left, targets in from_node.items():
        for right, count in targets.items():
            key = tuple(sorted((left, right)))
            if key in seen:
                continue
            seen.add(key)
            back = from_node.get(right, {}).get(left, 0)
            pairs.append({
                "nodes": list(key),
                "forward": count,
                "back": back,
                "mutual": bool(count and back),
                "views_of_each": [views_of.get(key[0], 0), views_of.get(key[1], 0)],
            })
    pairs.sort(key=lambda item: (-(item["forward"] + item["back"]), item["nodes"]))
    return {
        "$schema": "llmapper.visual-covisibility",
        "schema_version": 1,
        "min_frame_fraction": min_fraction,
        "views_per_node": dict(sorted(views_of.items())),
        "pairs": pairs,
        "limitations": [
            "co-visibility from a handful of planned poses, not from every point in a room",
            "a pose looks one way; a room seen only from behind the camera is absent here",
            "evidence toward grouping, never a grouping on its own",
        ],
    }


__all__ = [
    "SCHEMA", "SCHEMA_VERSION", "SURFACE_KINDS", "STRUCTURAL_KINDS",
    "ObservationError", "Viewpoint", "ObservationRequest", "ObservationManifest",
    "NodeAllocation", "SourceMap",
    "default_binary", "run_observation", "join_view", "compact_summary", "covisibility",
]
