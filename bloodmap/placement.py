"""Corpus-grounded object attachment: how sprites sit relative to architecture.

This does not invent a furniture ontology. It measures wall/floor/ceiling
relationships for original Blood sprites, then lets construction resolve
wall/floor/ceiling anchors instead of free XYZ.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from math import atan2, cos, hypot, pi, sin
from pathlib import Path
from typing import Any

from .blood_types import classify
from .format import read_map
from .model import DiskMap
from .patterns import classify_map_population, list_original_maps
from .planar_geom import point_in_loop
from .player_space import PLAYER_PROFILES


SCHEMA = "llmapper.object-placement"
SCHEMA_VERSION = 1
PLAYER = PLAYER_PROFILES["blood"]
PLAYER_HEIGHT = PLAYER.standing_height
PLAYER_WIDTH = PLAYER.body_width

SWITCH_TYPES = {20, 21, 22, 23}
TORCH_TYPES = {30, 32}
WALL_ALIGN_CSTAT = 16  # Blood kSprWall
FLOOR_ALIGN_CSTAT = 32  # Blood kSprFloor


class PlacementError(ValueError):
    pass


#: Blood draws a sprite centred on its own ``z``.
#:
#: ``GetSpriteExtents`` (db.h) is the whole rule, and it is shorter than the
#: assumptions usually made about it::
#:
#:     *top = *bottom = pSprite->z;
#:     if ((cstat & 0x30) != 0x20) {            // anything but floor-aligned
#:         int center = tilesiz[picnum].y / 2 + picanm[picnum].yofs;
#:         *top    -= (yrepeat << 2) * center;
#:         *bottom += (yrepeat << 2) * (height - center);
#:     }
#:
#: There is no ``cstat & 128`` test in it. Bit 128 is Duke's y-centring flag and
#: Blood sets it on most sprites, but Blood's extents ignore it: face sprites and
#: wall-aligned sprites alike hang half above and half below their z. Only a
#: floor-aligned sprite (cstat & 0x30 == 0x20) is a flat plane at z.
#:
#: So placing a standing object at ``z = floor_z`` buries exactly half of it,
#: which is not a rounding error but the default outcome of the obvious guess.
#: The campaign puts the *bottom* on the floor: of its 65 fence sprites, 43 sit
#: at ``bottom - floor_z == 0`` exactly.
SPRITE_ALIGNMENT_MASK = 0x30
SPRITE_ALIGNMENT_FLOOR = 0x20


def sprite_extent(tile_height: int, y_repeat: int, cstat: int, *,
                  y_offset: int = 0) -> tuple[int, int]:
    """How far a sprite reaches above and below its own z, in z units.

    Returns ``(above, below)``, both non-negative. A floor-aligned sprite is a
    plane and returns ``(0, 0)``.
    """
    if int(cstat) & SPRITE_ALIGNMENT_MASK == SPRITE_ALIGNMENT_FLOOR:
        return (0, 0)
    height = int(tile_height)
    centre = height // 2 + int(y_offset)
    scale = int(y_repeat) << 2
    return (scale * centre, scale * (height - centre))


def drawn_height(tile_height: int, y_repeat: int) -> int:
    """The z units a sprite covers top to bottom."""
    return (int(y_repeat) << 2) * int(tile_height)


def seated_z(*, seat: str, floor_z: int, ceiling_z: int, tile_height: int,
             y_repeat: int, cstat: int, y_offset: int = 0,
             clearance: int = 0) -> int:
    """The z that puts a sprite where the author meant it.

    ``seat`` is ``"floor"`` (bottom on the floor -- what a standing object
    wants), ``"ceiling"`` (top against the ceiling -- what a hanging one wants),
    or ``"centre"`` (z midway between, for something mounted on a wall). Build's
    z axis points down, so the floor is the larger number.
    """
    above, below = sprite_extent(tile_height, y_repeat, cstat, y_offset=y_offset)
    if seat == "floor":
        return int(floor_z) - below - int(clearance)
    if seat == "ceiling":
        return int(ceiling_z) + above + int(clearance)
    if seat == "centre":
        return (int(floor_z) + int(ceiling_z)) // 2
    raise PlacementError(f"unknown seat {seat!r}; use floor, ceiling or centre")


def fits_between(floor_z: int, ceiling_z: int, tile_height: int, y_repeat: int,
                 cstat: int, *, y_offset: int = 0) -> bool:
    """Whether the sprite is short enough to stand in the space at all."""
    above, below = sprite_extent(tile_height, y_repeat, cstat, y_offset=y_offset)
    return (above + below) <= abs(int(floor_z) - int(ceiling_z))


def repeat_to_fit(floor_z: int, ceiling_z: int, tile_height: int, *,
                  fraction: float = 1.0, step: int = 8) -> int:
    """The largest y_repeat whose drawn height is at most ``fraction`` of the space.

    Snapped down to a multiple of ``step``: the campaign draws 73% of its
    decorations at a power of two and uses only 53 distinct repeats in the whole
    game, so an exact-fit repeat computed to the unit would be a value Blood
    never uses.
    """
    span = abs(int(floor_z) - int(ceiling_z)) * float(fraction)
    exact = int(span // (4 * int(tile_height)))
    return max(step, (exact // step) * step)


def _id(ref: str) -> int:
    return int(str(ref).split(":", 1)[1])


def _wall_segment(disk: DiskMap, wall_id: int) -> tuple[tuple[int, int], tuple[int, int]]:
    wall = disk.walls[wall_id]
    nxt = disk.walls[int(wall.fields["point2"])]
    return (
        (int(wall.fields["x"]), int(wall.fields["y"])),
        (int(nxt.fields["x"]), int(nxt.fields["y"])),
    )


def point_segment_distance(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> tuple[float, float]:
    """Return (distance, t in [0,1]) from point to segment AB."""
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    if length2 <= 0:
        return hypot(px - ax, py - ay), 0.0
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
    qx, qy = ax + t * dx, ay + t * dy
    return hypot(px - qx, py - qy), t


def inward_normal(ax: int, ay: int, bx: int, by: int) -> tuple[float, float]:
    """Inward unit normal for a clockwise Build screen-space edge."""
    dx, dy = bx - ax, by - ay
    length = hypot(dx, dy) or 1.0
    return (-dy / length, dx / length)


def build_angle(dx: float, dy: float) -> int:
    return int(round(atan2(dy, dx) * 1024 / pi)) & 2047


def _owner_walls(disk: DiskMap, sector_id: int) -> list[int]:
    fields = disk.sectors[sector_id].fields
    first = int(fields["wall_ptr"])
    return list(range(first, first + int(fields["wall_count"])))


def nearest_wall(disk: DiskMap, sector_id: int, x: int, y: int, *, prefer_solid: bool = True) -> dict[str, Any]:
    best: dict[str, Any] | None = None
    for wall_id in _owner_walls(disk, sector_id):
        wall = disk.walls[wall_id]
        portal = int(wall.fields["next_sector"]) >= 0
        if prefer_solid and portal:
            continue
        (ax, ay), (bx, by) = _wall_segment(disk, wall_id)
        dist, t = point_segment_distance(x, y, ax, ay, bx, by)
        record = {
            "wall_id": wall_id,
            "distance": dist,
            "t": t,
            "portal": portal,
            "a": (ax, ay),
            "b": (bx, by),
        }
        if best is None or dist < best["distance"]:
            best = record
    if best is None and prefer_solid:
        return nearest_wall(disk, sector_id, x, y, prefer_solid=False)
    if best is None:
        raise PlacementError(f"sector {sector_id} has no walls")
    return best


def observe_sprite_attachment(disk: DiskMap, sprite_id: int) -> dict[str, Any]:
    sprite = disk.sprites[sprite_id]
    fields = sprite.fields
    sector_id = int(fields["sector"])
    x, y, z = int(fields["x"]), int(fields["y"]), int(fields["z"])
    sector = disk.sectors[sector_id].fields
    floor_z = int(sector["floor_z"])
    ceil_z = int(sector["ceiling_z"])
    typed = classify("sprite", int(fields["type"]))
    wall = nearest_wall(disk, sector_id, x, y)
    nx, ny = inward_normal(*wall["a"], *wall["b"])
    facing = build_angle(nx, ny)
    angle = int(fields["angle"]) & 2047
    delta = (angle - facing) & 2047
    if delta > 1024:
        delta -= 2048
    height_from_floor = floor_z - z
    height_to_ceil = z - ceil_z
    dist_pw = wall["distance"] / PLAYER_WIDTH
    if dist_pw < 0.2:
        sit = "wall_flush"
    elif dist_pw < 0.75:
        sit = "wall_offset"
    elif height_from_floor <= PLAYER_HEIGHT * 0.15:
        sit = "floor_supported"
    elif height_to_ceil <= PLAYER_HEIGHT * 0.2:
        sit = "ceiling_supported"
    else:
        sit = "free_space"
    cstat = int(fields["cstat"])
    return {
        "sprite": sprite_id,
        "type_id": int(fields["type"]),
        "type_name": typed.get("name"),
        "category": typed.get("category"),
        "sector": sector_id,
        "cstat": cstat,
        "wall_aligned": bool(cstat & WALL_ALIGN_CSTAT),
        "floor_aligned": bool(cstat & FLOOR_ALIGN_CSTAT),
        "nearest_wall": wall["wall_id"],
        "wall_distance_player_widths": round(dist_pw, 4),
        "wall_t": round(wall["t"], 4),
        "height_from_floor_player_heights": round(height_from_floor / PLAYER_HEIGHT, 4),
        "height_to_ceiling_player_heights": round(height_to_ceil / PLAYER_HEIGHT, 4),
        "angle": angle,
        "inward_angle": facing,
        "angle_vs_inward": delta,
        "faces_inward": abs(delta) <= 256,
        "sit": sit,
        "portal_wall": wall["portal"],
    }


def _bin_height(value: float) -> str:
    if value < 0.25:
        return "floor"
    if value < 0.55:
        return "low"
    if value < 0.9:
        return "use"
    if value < 1.4:
        return "high"
    return "near_ceil"


def _bin_dist(value: float) -> str:
    if value < 0.2:
        return "flush"
    if value < 0.75:
        return "offset"
    if value < 2.0:
        return "near"
    return "far"


def _summarize_kind(samples: list[dict[str, Any]]) -> dict[str, Any]:
    heights = [item["height_from_floor_player_heights"] for item in samples]
    dists = [item["wall_distance_player_widths"] for item in samples]
    return {
        "count": len(samples),
        "maps": sorted({item["map"] for item in samples}),
        "sit": dict(Counter(item["sit"] for item in samples)),
        "height_bin": dict(Counter(_bin_height(item["height_from_floor_player_heights"]) for item in samples)),
        "wall_dist_bin": dict(Counter(_bin_dist(item["wall_distance_player_widths"]) for item in samples)),
        "faces_inward_fraction": round(
            sum(1 for item in samples if item["faces_inward"]) / max(1, len(samples)), 4
        ),
        "wall_aligned_fraction": round(
            sum(1 for item in samples if item["wall_aligned"]) / max(1, len(samples)), 4
        ),
        "median_height_player_heights": round(sorted(heights)[len(heights) // 2], 4) if heights else None,
        "median_wall_distance_player_widths": round(sorted(dists)[len(dists) // 2], 4) if dists else None,
    }


def mine_attachments(directory: str | Path, *, population: str = "blood-campaign") -> dict[str, Any]:
    paths = list_original_maps(directory, population=population)
    if not paths:
        raise PlacementError(f"no maps for {population} in {directory}")
    by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
    errors = []
    for path in paths:
        try:
            disk = read_map(path)
        except Exception as exc:
            errors.append({"map": path.name, "error": str(exc)})
            continue
        for index, sprite in enumerate(disk.sprites):
            type_id = int(sprite.fields["type"])
            typed = classify("sprite", type_id)
            category = typed.get("category")
            if type_id in SWITCH_TYPES:
                kind = "switch"
            elif type_id in TORCH_TYPES:
                kind = "torch"
            elif category in {"weapon", "ammo", "health", "armor", "powerup", "key"}:
                kind = "pickup"
            elif category == "dude":
                kind = "enemy"
            elif category == "decoration":
                kind = "decoration"
            else:
                continue
            try:
                sample = observe_sprite_attachment(disk, index)
            except Exception as exc:
                errors.append({"map": path.name, "sprite": index, "error": str(exc)})
                continue
            sample["map"] = path.name
            sample["population"] = population
            by_kind[kind].append(sample)
    summaries = {kind: _summarize_kind(samples) for kind, samples in sorted(by_kind.items())}
    wall_switches = [
        item for item in by_kind.get("switch", [])
        if item["wall_aligned"] or item["sit"] in {"wall_flush", "wall_offset"}
    ]
    floor_switches = [
        item for item in by_kind.get("switch", [])
        if item["floor_aligned"] or (item["sit"] == "floor_supported" and not item["wall_aligned"])
    ]
    if wall_switches:
        summaries["switch_wall_mounted"] = _summarize_kind(wall_switches)
    if floor_switches:
        summaries["switch_floor_pad"] = _summarize_kind(floor_switches)
    wall_use = [
        item for item in wall_switches
        if 0.35 <= item["height_from_floor_player_heights"] <= 2.6
    ]
    height_source = wall_use or wall_switches
    rec_height = 0.65
    if height_source:
        rec_height = round(
            sorted(item["height_from_floor_player_heights"] for item in height_source)[len(height_source) // 2],
            4,
        )
    rec_offset = 0.08
    if wall_switches:
        dists = sorted(item["wall_distance_player_widths"] for item in wall_switches)
        wall_offset = dists[len(dists) // 2]
        rec_offset = min(0.12, max(0.06, wall_offset if wall_offset < 0.5 else 0.12))
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "kind": "derived",
        "population": population,
        "maps_mined": [path.name for path in paths],
        "summaries": summaries,
        "observe_errors": errors[:40],
        "recommended": {
            "switch": {
                "anchor": "wall",
                "height_player_heights": rec_height,
                "offset_player_widths": rec_offset,
                "cstat": 464,
                "facing": "into_region",
                "basis": "wall-aligned / wall-sit switches only; floor pads are a separate population",
            },
            "pickup": {
                "anchor": "floor",
                "height_player_heights": 0.0,
                "clearance_player_widths": 0.5,
            },
            "torch": {
                "anchor": "wall",
                "height_player_heights": (summaries.get("torch") or {}).get("median_height_player_heights") or 0.9,
                "offset_player_widths": 0.08,
            },
            "enemy": {
                "anchor": "floor",
                "height_player_heights": 0.0,
                "clearance_player_widths": 0.75,
            },
        },
        "limitations": [
            "nearest-wall metric is 2D; slopes and stacked sectors are not modeled",
            "use-range is inferred from corpus offset plus first-puzzle 896-unit evidence, not a full ActionScan",
        ],
    }


def resolve_anchor(
    *,
    kind: str,
    a1: tuple[int, int],
    a2: tuple[int, int],
    floor_z: int,
    ceiling_z: int,
    t: float = 0.5,
    height_player_heights: float = 0.65,
    offset_player_widths: float = 0.08,
    facing: str = "into_region",
    local: tuple[float, float] | None = None,
    outer: list[tuple[int, int]] | None = None,
) -> dict[str, int]:
    """Derive x/y/z/angle from a wall, floor, or ceiling anchor."""
    if kind == "wall":
        ax, ay = a1
        bx, by = a2
        mx = int(round(ax + (bx - ax) * t))
        my = int(round(ay + (by - ay) * t))
        nx, ny = inward_normal(ax, ay, bx, by)
        offset = offset_player_widths * PLAYER_WIDTH
        x = int(round(mx + nx * offset))
        y = int(round(my + ny * offset))
        z = int(round(floor_z - height_player_heights * PLAYER_HEIGHT))
        z = max(ceiling_z + 256, min(floor_z - 256, z))
        angle = build_angle(nx, ny)
        if facing == "outward":
            angle = (angle + 1024) & 2047
        return {"x": x, "y": y, "z": z, "angle": angle}
    if kind in {"floor", "ceiling"}:
        if outer is None or local is None:
            raise PlacementError("floor/ceiling anchors need outer loop and local 0-1 position")
        xs = [p[0] for p in outer]
        ys = [p[1] for p in outer]
        x = int(round(min(xs) + local[0] * (max(xs) - min(xs))))
        y = int(round(min(ys) + local[1] * (max(ys) - min(ys))))
        if kind == "floor":
            z = int(round(floor_z - height_player_heights * PLAYER_HEIGHT))
        else:
            z = int(round(ceiling_z + max(256, height_player_heights * PLAYER_HEIGHT)))
        z = max(ceiling_z, min(floor_z, z))
        return {"x": x, "y": y, "z": z, "angle": 0}
    raise PlacementError(f"unknown anchor kind {kind!r}")


def use_pose(resolved: dict[str, int], *, standoff_player_widths: float = 2.3) -> dict[str, int]:
    """A standing pose in front of a wall-mounted control (first-puzzle ~896 units)."""
    angle = int(resolved["angle"])
    rad = angle * pi / 1024
    dist = standoff_player_widths * PLAYER_WIDTH
    return {
        "x": int(round(resolved["x"] + cos(rad) * dist)),
        "y": int(round(resolved["y"] + sin(rad) * dist)),
        "z": resolved["z"],
        "angle": (angle + 1024) & 2047,
    }


def validate_attachments(disk: DiskMap, *, intended: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Fail unexplained free-space switches. Intended floating must be declared."""
    intended = intended or []
    allowed = {item.get("sprite") for item in intended if item.get("allow_free")}
    violations = []
    switches = []
    for index, sprite in enumerate(disk.sprites):
        if int(sprite.fields["type"]) not in SWITCH_TYPES:
            continue
        sample = observe_sprite_attachment(disk, index)
        switches.append(sample)
        if sample["sit"] == "free_space" and index not in allowed:
            violations.append({
                "sprite": index,
                "code": "floating_switch",
                "sit": sample["sit"],
                "wall_distance_player_widths": sample["wall_distance_player_widths"],
                "message": "push switch is not near a wall and was not declared free",
            })
        elif sample["sit"] in {"wall_flush", "wall_offset"} and not sample["faces_inward"]:
            violations.append({
                "sprite": index,
                "code": "switch_faces_away",
                "angle_vs_inward": sample["angle_vs_inward"],
                "message": "wall switch does not face into its sector",
            })
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "kind": "derived",
        "switch_count": len(switches),
        "violations": violations,
        "ok": not violations,
    }


def _sector_loop(disk: DiskMap, sector_id: int) -> list[tuple[int, int]]:
    fields = disk.sectors[sector_id].fields
    first = int(fields["wall_ptr"])
    count = int(fields["wall_count"])
    points = []
    wall_id = first
    for _ in range(count):
        wall = disk.walls[wall_id]
        points.append((int(wall.fields["x"]), int(wall.fields["y"])))
        wall_id = int(wall.fields["point2"])
        if wall_id == first:
            break
    return points


def probe_use_feasibility(disk: DiskMap, sprite_id: int, *, standoff_player_widths: float = 2.3) -> dict[str, Any]:
    """Deterministic Use pose: standing in front of a wall control, in its sector."""
    sample = observe_sprite_attachment(disk, sprite_id)
    sprite = disk.sprites[sprite_id].fields
    resolved = {
        "x": int(sprite["x"]),
        "y": int(sprite["y"]),
        "z": int(sprite["z"]),
        "angle": int(sprite["angle"]) & 2047,
    }
    pose = use_pose(resolved, standoff_player_widths=standoff_player_widths)
    loop = _sector_loop(disk, int(sprite["sector"]))
    inside = point_in_loop((pose["x"], pose["y"]), loop) != 0
    height = sample["height_from_floor_player_heights"]
    usable_height = 0.35 <= height <= 2.6
    return {
        "sprite": sprite_id,
        "pose": pose,
        "pose_in_owner_sector": inside,
        "usable_height": usable_height,
        "height_from_floor_player_heights": height,
        "sit": sample["sit"],
        "ok": bool(inside and usable_height and sample["sit"] in {"wall_flush", "wall_offset"}),
    }


def validate_use_poses(disk: DiskMap) -> dict[str, Any]:
    """Hard gate: wall switches must be usable from a standing pose in their sector."""
    violations = []
    probes = []
    for index, sprite in enumerate(disk.sprites):
        if int(sprite.fields["type"]) not in SWITCH_TYPES:
            continue
        sample = observe_sprite_attachment(disk, index)
        if sample["sit"] not in {"wall_flush", "wall_offset"}:
            continue
        probe = probe_use_feasibility(disk, index)
        probes.append(probe)
        if not probe["ok"]:
            violations.append({
                "sprite": index,
                "code": "unusable_switch_pose",
                "pose_in_owner_sector": probe["pose_in_owner_sector"],
                "usable_height": probe["usable_height"],
                "message": "wall switch has no standing use pose inside its sector at corpus height",
            })
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "kind": "derived",
        "probes": probes,
        "violations": violations,
        "ok": not violations,
    }


def misseated_sprites(disk: Any, tile_extents: dict[int, tuple[int, int]],
                      *, tolerance: int = 256) -> list[dict[str, Any]]:
    """Sprites whose drawn extent leaves the sector they are in.

    The fault this catches is invisible to every structural check: the map is
    valid, the engine loads it, and the player sees a fence sunk to its waist in
    the floor. It comes from placing a sprite at ``z = floor_z`` and expecting it
    to stand there, which is the natural reading of the field and the wrong one.

    `tolerance` allows the quarter-player-width slop the campaign itself carries;
    212 of its 3,251 decorations sit further below their floor than that, so this
    is a warning about a level's own intent rather than a law.
    """
    out: list[dict[str, Any]] = []
    for index, sprite in enumerate(disk.sprites):
        fields = sprite.fields
        if int(fields["type"]) != 0 or int(fields["cstat"]) & 32768:
            continue
        extent = tile_extents.get(int(fields["picnum"]))
        if extent is None:
            continue
        sector_id = int(fields["sector"])
        if not 0 <= sector_id < len(disk.sectors):
            continue
        above, below = sprite_extent(
            extent[0], int(fields["y_repeat"]), int(fields["cstat"]), y_offset=extent[1])
        z = int(fields["z"])
        sector = disk.sectors[sector_id].fields
        floor_z, ceiling_z = int(sector["floor_z"]), int(sector["ceiling_z"])

        # A floor-aligned sprite is a flat plane at its own z, so it has no
        # extent to sink or poke -- and the test below therefore never saw one
        # hanging in the air. Eleven of them were, because tile 795's canonical
        # cstat is 224, which is floor alignment, and it had been copied into a
        # *wall* placement. The mounting is part of the tile: laying a floor
        # grate against a wall leaves a disc floating edge-on.
        #
        # It is measured against the *nearer* of the two horizontal planes,
        # because a flat sprite is a plate and a plate lies on either. The
        # campaign's ceiling lights are floor-aligned sprites hung at the
        # ceiling, and a check that only knew about floors would have called
        # every one of them a fault.
        if int(fields["cstat"]) & SPRITE_ALIGNMENT_MASK == SPRITE_ALIGNMENT_FLOOR:
            drift = min(abs(z - floor_z), abs(z - ceiling_z))
            if drift > tolerance:
                out.append({
                    "sprite": index,
                    "picnum": int(fields["picnum"]),
                    "sector": sector_id,
                    "floor_aligned_adrift": drift,
                })
            continue

        sunk = (z + below) - floor_z
        poking = ceiling_z - (z - above)
        if sunk > tolerance or poking > tolerance:
            out.append({
                "sprite": index,
                "picnum": int(fields["picnum"]),
                "sector": sector_id,
                "below_floor": max(0, sunk),
                "above_ceiling": max(0, poking),
            })
    return out


def sprite_width(tile_width: int, x_repeat: int) -> int:
    """A sprite's drawn width in map units.

    Build scales a sprite by four in both axes, and the z axis is a sixteenth of
    the xy one -- so a height of ``(y_repeat << 2) * tile_height`` z units is a
    width of ``x_repeat * tile_width / 4`` xy units for the same repeat.
    """
    return int(x_repeat) * int(tile_width) // 4


def leaf_repeat(travel: int, tile_width: int) -> int:
    """The widest x_repeat for a sliding leaf that fully clears its opening.

    A leaf carried by a slide sector moves by the marker separation and no
    further, so anything wider than that distance is still standing in the
    doorway when the gate has finished opening. The campaign builds to just
    inside the limit -- E1M1's leaf is 1536 wide and travels 1448, E1M5's is
    1792 and travels 1600 -- so the rule is width <= travel, not width < travel.
    """
    return max(1, min(255, (int(travel) * 4) // int(tile_width)))


def blocked_when_open(travel: int, tile_width: int, x_repeat: int) -> int:
    """How much of the opening a leaf still covers once the gate has opened."""
    return max(0, sprite_width(tile_width, x_repeat) - int(travel))


def _wall_direction(ax: int, ay: int, bx: int, by: int) -> int:
    from math import atan2, pi

    return int(round(atan2(by - ay, bx - ax) / (2 * pi) * 2048)) & 2047


def wall_mount_angles(disk: Any, *, max_distance: int = 460) -> list[dict[str, Any]]:
    """Every wall-aligned sprite, with its angle relative to the wall it sits on.

    A wall-aligned sprite's `angle` is the normal of its face, not the line it
    lies along, so it presents itself to the room only when the angle is a
    quarter turn from the wall's direction. The campaign is emphatic: of 2,839
    wall-aligned sprites mounted within a player width or so of a wall, **92%
    are perpendicular** and 83% are at exactly +512 -- which makes it a facing
    rule rather than a symmetry, since +1536 (the other perpendicular) is only
    8%.

    Getting this wrong is invisible in every structural sense and unmissable on
    screen: the sprite stands edge-on, a bright line instead of a fence.
    """
    out: list[dict[str, Any]] = []
    for index, sprite in enumerate(disk.sprites):
        fields = sprite.fields
        cstat = int(fields["cstat"])
        if cstat & SPRITE_ALIGNMENT_MASK != WALL_ALIGN_CSTAT or cstat & 32768:
            continue
        sector_id = int(fields["sector"])
        if not 0 <= sector_id < len(disk.sectors):
            continue
        sector = disk.sectors[sector_id].fields
        start, count = int(sector["wall_ptr"]), int(sector["wall_count"])
        sx, sy = int(fields["x"]), int(fields["y"])
        best = None
        for wall in range(start, start + count):
            ax, ay = int(disk.walls[wall].fields["x"]), int(disk.walls[wall].fields["y"])
            nxt = int(disk.walls[wall].fields["point2"])
            bx, by = int(disk.walls[nxt].fields["x"]), int(disk.walls[nxt].fields["y"])
            dx, dy = bx - ax, by - ay
            length = dx * dx + dy * dy
            t = 0.0 if not length else max(0.0, min(1.0, ((sx - ax) * dx + (sy - ay) * dy) / length))
            distance = hypot(sx - (ax + t * dx), sy - (ay + t * dy))
            if best is None or distance < best[0]:
                best = (distance, ax, ay, bx, by)
        if best is None or best[0] > max_distance:
            continue
        relative = (int(fields["angle"]) - _wall_direction(*best[1:])) & 2047
        out.append({
            "sprite": index,
            "picnum": int(fields["picnum"]),
            "relative_angle": relative,
            "perpendicular": relative in (512, 1536),
            "distance": round(best[0]),
        })
    return out


def edge_on_sprites(disk: Any, **kwargs: Any) -> list[dict[str, Any]]:
    """Wall-mounted sprites presenting their edge to the room instead of a face."""
    return [row for row in wall_mount_angles(disk, **kwargs) if not row["perpendicular"]]
