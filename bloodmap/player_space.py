"""Player-relative and corpus-relative spatial presentation.

Exact native geometry stays available. This layer does not invent rooms, meters
as a primary unit, or a taxonomy of corridors and halls. It normalizes space
against a source-backed player body and, when present, original-map distributions.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from math import hypot
from typing import Any, Iterable

from .build_ir import BuildIR
from .doom import ML_TWOSIDED, NO_SIDE, DoomDiskMap, texture_label
from .spatial import SpatialAnalysisError, analyze_spatial, _ref


class PlayerSpaceError(ValueError):
    pass


SCHEMA = "llmapper.player-space"
SCHEMA_VERSION = 1
SKY_FLATS = frozenset({"F_SKY1", "F_SKY2", "F_SKY3", "F_SKY4"})


@dataclass(frozen=True)
class PlayerSpatialProfile:
    game: str
    native_unit: str
    body_radius: int
    body_width: int
    standing_height: int
    eye_height: int
    crouch_height: int | None
    max_step: int
    jump: bool
    crouch: bool
    min_passage_width: int
    min_passage_height_standing: int
    min_passage_height_crouch: int | None
    evidence: dict[str, str]
    optional_meters_per_native: float | None = None
    #: `POSTURE.eyeAboveZ` as the engine stores it: the camera's offset from the
    #: player *sprite's own z*, which `GetSpriteExtents` puts at the body's
    #: centre, not at the feet. It is not a height above the floor and it is not
    #: a body height. Kept because `zView = pSprite->z - eyeAboveZ` is the line
    #: that uses it, and anything reproducing that line needs this number.
    eye_above_centre: int | None = None

    @property
    def id(self) -> str:
        return f"player-profile:{self.game}"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["id"] = self.id
        payload["optional_meters"] = {
            "per_native": self.optional_meters_per_native,
            "role": "optional intuition only; not the primary abstraction",
        }
        return payload


PLAYER_PROFILES = {
    "blood": PlayerSpatialProfile(
        game="blood",
        native_unit="build",
        body_radius=192,
        body_width=384,
        # The body is the drawn figure, not the posture offset. See the note on
        # `eye_above_centre` and the correction recorded below.
        standing_height=16960,
        eye_height=14112,
        crouch_height=13376,
        max_step=4096,
        jump=True,
        crouch=True,
        min_passage_width=384,
        min_passage_height_standing=16960,
        min_passage_height_crouch=13376,
        eye_above_centre=0x1600,
        evidence={
            "body_radius": (
                "NBlood source/blood/src/dude.cpp gPlayerTemplate normal human clipdist=0x30; "
                "player.cpp playerProcess dw = pSprite->clipdist<<2 → 192"
            ),
            "standing_height": (
                "NBlood source/blood/src/db.h:325 GetSpriteExtents -- a dude's body is "
                "bottom-top = yrepeat*tilesizy*4, and the bot's own model agrees "
                "(llmapper/bot/blood/blood_physics.cpp liveBody: shape.height = bottom - top). "
                "Blood ships no Caleb sprite in any map, so the figure is taken from the "
                "human dudes the campaign does place: tiles 2820/2825 (cultist) are 106px "
                "at the yrepeat 40 used 1422 times => 16960. INTERPRETED as Caleb's scale; "
                "liveBody() measures the real body exactly at runtime."
            ),
            "eye_height": (
                "footOffset + eyeAboveZ. GetSpriteExtents puts a face sprite's z at its "
                "centre, and player.cpp playerStart does `pSprite->z -= bottom - pSprite->z` "
                "to drop the feet onto the start z -- so the centre sits (16960/2)=8480 above "
                "the floor and the camera 0x1600 above that. Cross-checked by render: at this "
                "height 17% of a cultist stands above the horizon, which is what "
                "(16960-14112)/16960 predicts; at 0x1600 it would be 67%."
            ),
            "crouch_height": (
                "the bot's derivation, llmapper/bot/blood/caleb_physics.cpp:255 -- "
                "body.height - (standing.eyeAboveZ - crouching.eyeAboveZ) "
                "= 16960 - (0x1600 - 0x800)"
            ),
            "min_passage_height_standing": (
                "clipping tests the sprite extent, so a standing body needs its whole "
                "height. llmapper/bot/blood/blood_terrain.cpp:204 clearanceFor returns "
                "Standing only when freeHeight >= body.height. Campaign agrees: static "
                "openings between playable sectors are uniformly sparse from 4k to 16k "
                "(170-600 per 2k band) and jump 4x at 16384."
            ),
            "jump": "NBlood POSTURE.normalJumpZ is nonzero for standing human",
            "max_step": (
                "llmapper spatial at-rest floor_delta threshold of 4096; Blood clipmove "
                "flordist is sprite-extent derived, not a named autostep"
            ),
            "correction": (
                "Until 2026-08-27 every field here was 0x1600, on the evidence line "
                "'gPostureDefaults[kModeHuman][kPostureStand].eyeAboveZ=0x1600'. That "
                "read the engine correctly and then called the answer the wrong thing: "
                "eyeAboveZ is measured from the sprite's centre, so it is neither a body "
                "height nor a height above the floor. The consequence was a camera at 25% "
                "of room height instead of 67% -- every observation in this project was "
                "framed from chest level -- and a walkable-clearance test that passed "
                "passages a third of the height the player needs."
            ),
        },
        optional_meters_per_native=1.76 / 16960,
    ),
    "duke3d": PlayerSpatialProfile(
        game="duke3d",
        native_unit="build",
        body_radius=164,
        body_width=328,
        standing_height=38 << 8,
        eye_height=38 << 8,
        crouch_height=None,
        max_step=20 << 8,
        jump=True,
        crouch=True,
        min_passage_width=328,
        min_passage_height_standing=38 << 8,
        min_passage_height_crouch=None,
        evidence={
            "body_radius": (
                "EDuke32 source/duke3d/src/premap.cpp P_ResetExtents clipdist=164 passed to clipmove as walldist"
            ),
            "standing_height": "EDuke32 source/duke3d/src/player.h PHEIGHT (38<<8)",
            "max_step": "EDuke32 source/duke3d/src/premap.cpp P_ResetExtents autostep=20<<8",
            "jump": "Duke player jump is a runtime movement affordance; JumpZ is not a map field",
            "crouch": "Duke crouch exists; no separate named crouch clip height in P_ResetExtents",
        },
        optional_meters_per_native=1.76 / (38 << 8),
    ),
    "doom": PlayerSpatialProfile(
        game="doom",
        native_unit="doom",
        body_radius=16,
        body_width=32,
        standing_height=56,
        eye_height=41,
        crouch_height=None,
        max_step=24,
        jump=False,
        crouch=False,
        min_passage_width=32,
        min_passage_height_standing=56,
        min_passage_height_crouch=None,
        evidence={
            "body_radius": "GZDoom wadsrc/static/zscript/actors/player/player.zs PlayerPawn Radius 16",
            "standing_height": "GZDoom player.zs PlayerPawn Height 56",
            "eye_height": "GZDoom player.zs Player.ViewHeight 41",
            "max_step": "GZDoom wadsrc/static/zscript/actors/actor.zs Actor MaxStepHeight 24",
            "jump": "classic Doom has no jump; GZDoom Player.JumpZ is not vanilla MAPINFO behavior",
            "crouch": "classic Doom has no crouch",
        },
        optional_meters_per_native=1.76 / 56.0,
    ),
}


def player_profile(game: str) -> PlayerSpatialProfile:
    if game == "duke":
        game = "duke3d"
    try:
        return PLAYER_PROFILES[game]
    except KeyError as exc:
        raise PlayerSpaceError(f"no player spatial profile for {game}") from exc


def _ratio(value: float | int | None, unit: int) -> float | None:
    if value is None or unit <= 0:
        return None
    return round(float(value) / unit, 4)


def corpus_samples(corpus: dict[str, Any] | None, key: str) -> list[float] | None:
    if not corpus:
        return None
    value = corpus.get(key)
    if isinstance(value, list) and value and not isinstance(value[0], dict):
        return [float(item) for item in value]
    return None


def _percentile(value: float | int | None, samples: list[float] | None) -> float | None:
    if value is None or not samples:
        return None
    ordered = sorted(float(item) for item in samples)
    count = sum(1 for item in ordered if item <= float(value))
    return round(100.0 * count / len(ordered), 1)


def _summary(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    return {
        "min": round(ordered[0], 4),
        "median": round(ordered[n // 2], 4),
        "max": round(ordered[-1], 4),
        "samples": n,
    }


def _heuristic_tail(percentile: float | None, *, low: str, high: str) -> dict[str, str] | None:
    if percentile is None:
        return None
    if percentile <= 15:
        return {"value": low, "confidence": "heuristic", "basis": "lower tail of this game's corpus distribution"}
    if percentile >= 85:
        return {"value": high, "confidence": "heuristic", "basis": "upper tail of this game's corpus distribution"}
    return {
        "value": "typical for this game's original maps",
        "confidence": "heuristic",
        "basis": "inside the central corpus mass",
    }


def layered(
    *,
    raw: float | int | None,
    unit: int,
    unit_name: str,
    samples: list[float] | None = None,
    relative: float | None = None,
    low: str = "unusually small relative to this corpus",
    high: str = "unusually large relative to this corpus",
    profile: PlayerSpatialProfile,
) -> dict[str, Any]:
    player_units = _ratio(raw, unit)
    percentile = _percentile(player_units, samples)
    return {
        "raw": None if raw is None else round(float(raw), 4),
        "native_unit": profile.native_unit,
        player_units_key(unit_name): player_units,
        "corpus_percentile": percentile,
        "relative_to_neighbor": None if relative is None else round(float(relative), 4),
        "profile": profile.id,
        "interpretation": _heuristic_tail(percentile, low=low, high=high),
    }


def player_units_key(unit_name: str) -> str:
    return {
        "width": "player_widths",
        "height": "player_heights",
        "area": "player_areas",
    }.get(unit_name, unit_name)


def traversal_affordances(
    *,
    width: float,
    opening: float,
    floor_delta: float,
    blocking: bool,
    profile: PlayerSpatialProfile,
) -> dict[str, Any]:
    can_fit = (not blocking) and width >= profile.min_passage_width
    stand = opening >= profile.min_passage_height_standing
    crouch_ok = (
        profile.crouch
        and profile.min_passage_height_crouch is not None
        and opening >= profile.min_passage_height_crouch
    )
    can_step = floor_delta <= profile.max_step
    requires_crouch = bool(can_fit and (not stand) and crouch_ok)
    requires_jump = bool(can_fit and stand and (not can_step) and profile.jump)
    can_walk = bool(can_fit and stand and can_step)
    cannot = blocking or (not can_fit) or (not stand and not crouch_ok) or (not can_step and not profile.jump)
    return {
        "can_fit": can_fit,
        "can_walk_through": can_walk,
        "can_step_up": can_step,
        "requires_jump": requires_jump,
        "requires_crouch": requires_crouch,
        "cannot_traverse": cannot,
        "physical": {
            "width_player_widths": _ratio(width, profile.body_width),
            "clear_height_player_heights": _ratio(opening, profile.standing_height),
            "step_player_heights": _ratio(floor_delta, profile.standing_height),
        },
        "basis": "player collision width/height and named step/jump/crouch affordances; not comfort",
        "profile": profile.id,
    }


def _portal_records(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    return list(analysis["views"]["geometry"]["portals"])


def _sector_record(analysis: dict[str, Any], sector_id: int) -> dict[str, Any]:
    ref = _ref("sector", sector_id)
    for item in analysis["views"]["geometry"]["sectors"]:
        if item["ref"] == ref:
            return item
    raise PlayerSpaceError(f"sector {sector_id} is outside the spatial analysis")


def _aabb(bounds: dict[str, int]) -> tuple[float, float]:
    return float(bounds["max_x"] - bounds["min_x"]), float(bounds["max_y"] - bounds["min_y"])


def _dominant(counts: dict[int, int]) -> dict[str, int] | None:
    if not counts:
        return None
    picnum, uses = max(counts.items(), key=lambda item: (item[1], -item[0]))
    return {"picnum": int(picnum), "uses": int(uses)}


def _combine_bounds(items: list[dict[str, int]]) -> dict[str, int]:
    return {
        "min_x": min(item["min_x"] for item in items),
        "max_x": max(item["max_x"] for item in items),
        "min_y": min(item["min_y"] for item in items),
        "max_y": max(item["max_y"] for item in items),
    }


def _enclosure(
    *,
    sky_fraction: float,
    perimeter: float,
    open_width: float,
    median_height: float | None,
    profile: PlayerSpatialProfile,
) -> dict[str, Any]:
    lateral = 1.0 if perimeter <= 0 else max(0.0, min(1.0, 1.0 - open_width / perimeter))
    vertical = 1.0 - sky_fraction
    if median_height is not None and profile.standing_height:
        # Very tall indoor volumes feel less vertically enclosed even without sky.
        vertical *= min(1.0, (3.0 * profile.standing_height) / max(median_height, 1.0))
    vertical = max(0.0, min(1.0, vertical))
    return {
        "sky_exposure": round(sky_fraction, 4),
        "lateral_enclosure": round(lateral, 4),
        "vertical_enclosure": round(vertical, 4),
        "openness": round(1.0 - 0.5 * (lateral + vertical), 4),
        "basis": "parallax/sky fraction, boundary portal width over perimeter, height vs standing stature",
        "interpretation": None,
    }


def inspect_connection(
    build: BuildIR,
    *,
    wall_id: int | None = None,
    left: int | None = None,
    right: int | None = None,
    corpus: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile = player_profile(build.source_game)
    analysis = analyze_spatial(build)
    edge = None
    for item in _portal_records(analysis):
        sectors = [int(ref.split(":", 1)[1]) for ref in item["sectors"]]
        walls = [int(ref.split(":", 1)[1]) for ref in item["walls"]]
        if wall_id is not None and wall_id in walls:
            edge = item
            break
        if left is not None and right is not None and set(sectors) == {int(left), int(right)}:
            edge = item
            break
    if edge is None:
        raise PlayerSpaceError("no portal matches the requested connection")
    samples = (
        corpus_samples(corpus, "traversable_opening_width_player_widths")
        or corpus_samples(corpus, "opening_width_player_widths")
    )
    affordance = traversal_affordances(
        width=edge["width"], opening=edge["at_rest_opening"],
        floor_delta=edge["floor_delta"], blocking=edge["blocking_flag"], profile=profile,
    )
    return {
        "$schema": SCHEMA, "schema_version": SCHEMA_VERSION, "kind": "connection",
        "portal": edge["id"], "sectors": edge["sectors"], "walls": edge["walls"],
        "profile": profile.to_dict(),
        "width": layered(
            raw=edge["width"], unit=profile.body_width, unit_name="width",
            samples=samples, low="unusually narrow opening", high="unusually wide opening",
            profile=profile,
        ),
        "clear_height": layered(
            raw=edge["at_rest_opening"], unit=profile.standing_height, unit_name="height",
            samples=corpus_samples(corpus, "clear_height_player_heights"),
            low="unusually low clearance", high="unusually tall clearance", profile=profile,
        ),
        "step": layered(
            raw=edge["floor_delta"], unit=profile.standing_height, unit_name="height",
            samples=corpus_samples(corpus, "step_player_heights"),
            low="trivial step", high="large vertical transition", profile=profile,
        ),
        "movement": affordance,
    }


def inspect_space(
    build: BuildIR,
    sector_ids: Iterable[int] | None = None,
    *,
    corpus: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile = player_profile(build.source_game)
    analysis = analyze_spatial(build)
    selected = sorted(set(range(len(build.sectors))) if sector_ids is None else {int(value) for value in sector_ids})
    invalid = [value for value in selected if not 0 <= value < len(build.sectors)]
    if invalid:
        raise PlayerSpaceError(f"sector IDs are out of range: {invalid}")
    sectors = [_sector_record(analysis, value) for value in selected]
    bounds = _combine_bounds([item["bounds"] for item in sectors])
    width, depth = _aabb(bounds)
    footprint = sum(float(item["area"]) for item in sectors)
    heights = [float(item["clear_height"]) for item in sectors]
    elongation = max(width, depth) / max(1.0, min(width, depth))
    sky = 0
    floors: dict[int, int] = defaultdict(int)
    ceilings: dict[int, int] = defaultdict(int)
    walls: dict[int, int] = defaultdict(int)
    for sector_id in selected:
        fields = build.sectors[sector_id]["fields"]
        if int(fields["ceiling_stat"]) & 1:
            sky += 1
        floors[int(fields["floor_picnum"])] += 1
        ceilings[int(fields["ceiling_picnum"])] += 1
        first = int(fields["wall_ptr"])
        count = int(fields["wall_count"])
        for wall_id in range(first, first + count):
            walls[int(build.walls[wall_id]["fields"]["picnum"])] += 1
    internal: list[dict[str, Any]] = []
    boundary: list[dict[str, Any]] = []
    seen_internal: set[str] = set()
    seen_boundary: set[str] = set()
    perimeter = 0.0
    for sector_id in selected:
        fields = build.sectors[sector_id]["fields"]
        first = int(fields["wall_ptr"])
        count = int(fields["wall_count"])
        for wall_id in range(first, first + count):
            wall_fields = build.walls[wall_id]["fields"]
            point2 = int(wall_fields["point2"])
            end = build.walls[point2]["fields"]
            length = hypot(int(end["x"]) - int(wall_fields["x"]), int(end["y"]) - int(wall_fields["y"]))
            next_sector = int(wall_fields["next_sector"])
            if next_sector in selected:
                record = next(
                    (
                        item for item in _portal_records(analysis)
                        if _ref("sector", sector_id) in item["sectors"] and _ref("sector", next_sector) in item["sectors"]
                    ),
                    None,
                )
                if record is not None and record["id"] not in seen_internal:
                    seen_internal.add(record["id"])
                    internal.append(record)
                continue
            perimeter += length
            if next_sector < 0:
                continue
            record = next(
                (
                    item for item in _portal_records(analysis)
                    if _ref("sector", sector_id) in item["sectors"] and _ref("sector", next_sector) in item["sectors"]
                ),
                None,
            )
            if record is None or record["id"] in seen_boundary:
                continue
            seen_boundary.add(record["id"])
            boundary.append(record)
    openings = [item["width"] for item in internal + boundary if not item["blocking_flag"]]
    open_width = sum(item["width"] for item in boundary if not item["blocking_flag"])
    height_summary = _summary(heights)
    width_summary = _summary(openings)
    enclosure = _enclosure(
        sky_fraction=sky / max(1, len(selected)),
        perimeter=perimeter,
        open_width=open_width,
        median_height=None if height_summary is None else height_summary["median"],
        profile=profile,
    )
    bottleneck = None if not openings else min(openings)
    movement = None
    if bottleneck is not None:
        sample = next(item for item in internal + boundary if item["width"] == bottleneck)
        movement = traversal_affordances(
            width=sample["width"], opening=sample["at_rest_opening"],
            floor_delta=sample["floor_delta"], blocking=sample["blocking_flag"], profile=profile,
        )
    corpus = corpus or {}
    return {
        "$schema": SCHEMA, "schema_version": SCHEMA_VERSION, "kind": "space",
        "source_game": build.source_game,
        "sectors": [_ref("sector", value) for value in selected],
        "profile": profile.to_dict(),
        "movement": {
            "narrowest_connection": None if bottleneck is None else layered(
                raw=bottleneck, unit=profile.body_width, unit_name="width",
                samples=corpus_samples(corpus, "traversable_opening_width_player_widths")
                or corpus_samples(corpus, "opening_width_player_widths"),
                low="unusually tight passage", high="unusually wide passage", profile=profile,
            ),
            "affordances": movement,
            "connector_count": len(boundary),
            "internal_portal_count": len(internal),
        },
        "scale": {
            "footprint": layered(
                raw=footprint, unit=profile.body_width ** 2, unit_name="area",
                samples=corpus_samples(corpus, "footprint_player_areas"),
                low="unusually small footprint", high="unusually large footprint", profile=profile,
            ),
            "aabb_width": layered(
                raw=width, unit=profile.body_width, unit_name="width",
                samples=corpus_samples(corpus, "aabb_width_player_widths"),
                low="unusually narrow space", high="unusually wide space", profile=profile,
            ),
            "aabb_depth": layered(
                raw=depth, unit=profile.body_width, unit_name="width", profile=profile,
            ),
            "clear_height": layered(
                raw=None if height_summary is None else height_summary["median"],
                unit=profile.standing_height, unit_name="height",
                samples=corpus_samples(corpus, "clear_height_player_heights"),
                low="unusually low", high="unusually tall", profile=profile,
            ),
            "clear_height_range": height_summary,
            "opening_width_range": width_summary,
        },
        "shape": {
            "elongation": round(elongation, 4),
            "sector_count": len(selected),
            "wall_loop_count_sum": sum(int(item["wall_loop_count"]) for item in sectors),
            "basis": "AABB of selected sectors; irregular selections keep min/median/max instead of one width",
        },
        "enclosure": enclosure,
        "surfaces": {
            "dominant_floor_picnum": _dominant(floors),
            "dominant_ceiling_picnum": _dominant(ceilings),
            "dominant_wall_picnum": _dominant(walls),
            "basis": "raw native picnum counts; not material-family names",
        },
        "visibility": {
            "model": "direct-portal candidates only",
            "boundary_openings": len(boundary),
            "basis": analysis["views"]["visibility"]["model"],
        },
    }


def compare_transition(
    build: BuildIR,
    source_sectors: Iterable[int],
    dest_sectors: Iterable[int],
    *,
    corpus: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source = inspect_space(build, source_sectors, corpus=corpus)
    dest = inspect_space(build, dest_sectors, corpus=corpus)

    def ratio(left: dict[str, Any] | None, right: dict[str, Any] | None, key: str) -> float | None:
        if not left or not right:
            return None
        a, b = left.get(key), right.get(key)
        if a in (None, 0) or b is None:
            return None
        return round(float(b) / float(a), 4)

    width_ratio = ratio(source["scale"]["aabb_width"], dest["scale"]["aabb_width"], "player_widths")
    height_ratio = ratio(source["scale"]["clear_height"], dest["scale"]["clear_height"], "player_heights")
    area_ratio = ratio(source["scale"]["footprint"], dest["scale"]["footprint"], "player_areas")
    expansion = None
    if (width_ratio and width_ratio >= 2.0) or (area_ratio and area_ratio >= 3.0) or (height_ratio and height_ratio >= 2.0):
        expansion = {
            "value": "strong spatial expansion",
            "confidence": "heuristic",
            "basis": "destination is several times wider, taller, or larger than the approach",
        }
    elif width_ratio and width_ratio <= 0.5:
        expansion = {
            "value": "strong spatial compression",
            "confidence": "heuristic",
            "basis": "destination is much narrower than the approach",
        }
    return {
        "$schema": SCHEMA, "schema_version": SCHEMA_VERSION, "kind": "transition",
        "from": source["sectors"], "to": dest["sectors"],
        "width_ratio": width_ratio,
        "clear_height_ratio": height_ratio,
        "navigable_area_ratio": area_ratio,
        "sky_exposure": [source["enclosure"]["sky_exposure"], dest["enclosure"]["sky_exposure"]],
        "enclosure": [source["enclosure"], dest["enclosure"]],
        "branch_count": [source["movement"]["connector_count"], dest["movement"]["connector_count"]],
        "source": source,
        "destination": dest,
        "interpretation": expansion,
    }


def present_space(payload: dict[str, Any]) -> dict[str, Any]:
    """Compact LLM-facing view. Full layered evidence remains on the payload."""
    if payload.get("kind") == "transition":
        return {
            "kind": "transition",
            "from": payload["from"],
            "to": payload["to"],
            "width_ratio": payload["width_ratio"],
            "clear_height_ratio": payload["clear_height_ratio"],
            "navigable_area_ratio": payload["navigable_area_ratio"],
            "sky_exposure": payload["sky_exposure"],
            "branch_count": payload["branch_count"],
            "interpretation": payload.get("interpretation"),
        }
    if payload.get("kind") == "connection":
        return {
            "kind": "connection",
            "portal": payload.get("portal"),
            "sectors": payload.get("sectors"),
            "width_player_widths": (payload.get("width") or {}).get("player_widths"),
            "width_percentile": (payload.get("width") or {}).get("corpus_percentile"),
            "width_raw": (payload.get("width") or {}).get("raw"),
            "clear_height_player_heights": (payload.get("clear_height") or {}).get("player_heights"),
            "movement": payload.get("movement"),
            "interpretation": (payload.get("width") or {}).get("interpretation"),
        }
    movement = payload.get("movement") or {}
    scale = payload.get("scale") or {}
    opening = movement.get("narrowest_connection") or {}
    afford = movement.get("affordances") or {}
    surfaces = payload.get("surfaces") or {}
    return {
        "kind": "space",
        "sectors": payload.get("sectors"),
        "movement": {
            "can_walk_through": afford.get("can_walk_through"),
            "requires_jump": afford.get("requires_jump"),
            "requires_crouch": afford.get("requires_crouch"),
            "cannot_traverse": afford.get("cannot_traverse"),
            "narrowest_connection_player_widths": opening.get("player_widths"),
            "narrowest_connection_percentile": opening.get("corpus_percentile"),
            "connector_count": movement.get("connector_count"),
        },
        "scale": {
            "footprint_percentile": (scale.get("footprint") or {}).get("corpus_percentile"),
            "footprint_player_areas": (scale.get("footprint") or {}).get("player_areas"),
            "clear_height_player_heights": (scale.get("clear_height") or {}).get("player_heights"),
            "clear_height_percentile": (scale.get("clear_height") or {}).get("corpus_percentile"),
            "aabb_width_player_widths": (scale.get("aabb_width") or {}).get("player_widths"),
        },
        "shape": payload.get("shape"),
        "enclosure": {
            key: payload["enclosure"][key]
            for key in ("sky_exposure", "lateral_enclosure", "vertical_enclosure", "openness")
        } if payload.get("enclosure") else None,
        "surfaces": {
            "dominant_wall_picnum": surfaces.get("dominant_wall_picnum"),
            "dominant_floor_picnum": surfaces.get("dominant_floor_picnum"),
        } if surfaces else None,
    }


def focus_observation(payload: dict[str, Any], question: str) -> dict[str, Any]:
    """Question-oriented subset. Full layered evidence remains on the payload."""
    compact = present_space(payload)
    mapping = {
        "traverse": {"kind": payload.get("kind"), "movement": compact.get("movement") or payload.get("movement")},
        "scale": {"kind": payload.get("kind"), "scale": compact.get("scale") or payload.get("scale")},
        "enclosure": {"kind": payload.get("kind"), "enclosure": compact.get("enclosure") or payload.get("enclosure")},
        "shape": {"kind": payload.get("kind"), "shape": compact.get("shape")},
        "opening": compact if payload.get("kind") == "connection" else {
            "kind": payload.get("kind"),
            "narrowest_connection": (payload.get("movement") or {}).get("narrowest_connection"),
            "movement": compact.get("movement"),
        },
        "transition": compact if payload.get("kind") == "transition" else compact,
    }
    if question not in mapping:
        raise PlayerSpaceError(
            f"unknown spatial question {question!r}; expected one of {sorted(mapping)}"
        )
    return mapping[question]


def mine_build_spatial_corpus(maps: list[tuple[str, BuildIR]]) -> dict[str, Any]:
    if not maps:
        raise PlayerSpaceError("spatial corpus is empty")
    game = maps[0][1].source_game
    profile = player_profile(game)
    widths, heights, areas, steps, elongations, aabb_widths, trav_widths = [], [], [], [], [], [], []
    # Sky-lit sectors are a separate population.  A courtyard compared against
    # every sector of its footprint is being compared mostly against interiors,
    # and the two are not built to the same heights.
    sky_heights: list[float] = []
    features: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    used = 0
    for name, build in maps:
        if build.source_game != game:
            raise PlayerSpaceError("spatial corpus mixes games")
        try:
            analysis = analyze_spatial(build)
        except SpatialAnalysisError as exc:
            skipped.append({"map": name, "error": str(exc)})
            continue
        used += 1
        for edge in analysis["views"]["geometry"]["portals"]:
            if edge["blocking_flag"]:
                continue
            widths.append(edge["width"] / profile.body_width)
            steps.append(edge["floor_delta"] / profile.standing_height)
            min_height = profile.min_passage_height_crouch or profile.min_passage_height_standing
            if edge["width"] >= profile.min_passage_width and edge["at_rest_opening"] >= min_height:
                trav_widths.append(edge["width"] / profile.body_width)
        for sector in analysis["views"]["geometry"]["sectors"]:
            heights.append(sector["clear_height"] / profile.standing_height)
            sector_id = int(str(sector["ref"]).split(":", 1)[1])
            parallax = bool(int(build.sectors[sector_id]["fields"]["ceiling_stat"]) & 1)
            if parallax:
                sky_heights.append(sector["clear_height"] / profile.standing_height)
            w, d = _aabb(sector["bounds"])
            aabb_widths.append(w / profile.body_width)
            areas.append(sector["area"] / (profile.body_width ** 2))
            elongations.append(max(w, d) / max(1.0, min(w, d)))
            features.append({
                "map": name, "sector": sector["ref"], "sky": parallax,
                "elongation": round(max(w, d) / max(1.0, min(w, d)), 4),
                "area_player": round(sector["area"] / (profile.body_width ** 2), 4),
                "height_player": round(sector["clear_height"] / profile.standing_height, 4),
            })
    if used == 0:
        raise PlayerSpaceError("spatial corpus has no maps the spatial sensor can analyze")
    clusters = _unlabeled_clusters(features)
    return {
        "$schema": "llmapper.spatial-corpus",
        "schema_version": SCHEMA_VERSION,
        "game": game,
        "profile": profile.id,
        "maps": used,
        "skipped": skipped,
        "opening_width_player_widths": widths,
        "traversable_opening_width_player_widths": trav_widths,
        "clear_height_player_heights": heights,
        "sky_clear_height_player_heights": sky_heights,
        "footprint_player_areas": areas,
        "step_player_heights": steps,
        "aabb_width_player_widths": aabb_widths,
        "summaries": {
            "sky_clear_height_player_heights": _summary(sky_heights),
            "opening_width_player_widths": _summary(widths),
            "traversable_opening_width_player_widths": _summary(trav_widths),
            "clear_height_player_heights": _summary(heights),
            "footprint_player_areas": _summary(areas),
            "step_player_heights": _summary(steps),
            "aabb_width_player_widths": _summary(aabb_widths),
            "elongation": _summary(elongations),
        },
        "clusters": clusters,
        "notes": [
            "Distributions are player-normalized. Labels such as corridor are not assigned.",
            "Percentiles are computed against these samples, not universal constants.",
            "All non-blocking portals are kept; traversable_opening_width_player_widths excludes sub-body slivers.",
        ],
    }


def _unlabeled_clusters(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(features) < 4:
        return []
    elong = _summary([item["elongation"] for item in features])
    area = _summary([item["area_player"] for item in features])
    if elong is None or area is None:
        return []

    def bin_of(value: float, summary: dict[str, float]) -> str:
        if value <= summary["median"]:
            return "lo"
        if value >= (summary["median"] + summary["max"]) / 2:
            return "hi"
        return "mid"

    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in features:
        groups[(bin_of(item["elongation"], elong), bin_of(item["area_player"], area))].append(item)
    clusters = []
    for number, (key, members) in enumerate(sorted(groups.items())):
        if len(members) < 2:
            continue
        med_el = _summary([item["elongation"] for item in members])["median"]
        interpretation = None
        if key[0] == "hi" and key[1] == "lo":
            interpretation = {
                "value": "elongated small space",
                "confidence": "heuristic",
                "basis": "high elongation and low player-relative area relative to this corpus",
            }
        elif key[0] == "lo" and key[1] == "hi":
            interpretation = {
                "value": "compact large space",
                "confidence": "heuristic",
                "basis": "low elongation and high player-relative area relative to this corpus",
            }
        clusters.append({
            "id": f"cluster:space:{number:04d}",
            "kind": "unlabeled_spatial",
            "members": len(members),
            "sample": [item["sector"] for item in members[:8]],
            "elongation_bin": key[0],
            "area_bin": key[1],
            "median_elongation": med_el,
            "provenance": "DERIVED",
            "interpretation": interpretation,
        })
    return clusters


def mine_doom_spatial_corpus(levels: list[DoomDiskMap]) -> dict[str, Any]:
    profile = player_profile("doom")
    widths, heights, areas, trav_widths = [], [], [], []
    for level in levels:
        if not level.supported:
            continue
        for line in level.linedefs:
            if not (line.flags & ML_TWOSIDED) or line.side_back == NO_SIDE:
                continue
            v1, v2 = level.vertices[line.v1], level.vertices[line.v2]
            player_w = hypot(v1.x - v2.x, v1.y - v2.y) / profile.body_width
            widths.append(player_w)
            if player_w * profile.body_width >= profile.min_passage_width:
                trav_widths.append(player_w)
        for sector in level.sectors:
            heights.append((sector.ceiling_height - sector.floor_height) / profile.standing_height)
        # Per-sector AABB from sidedef vertices.
        by_sector: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for line in level.linedefs:
            for side_index in (line.side_front, line.side_back):
                if side_index == NO_SIDE or not 0 <= side_index < len(level.sidedefs):
                    continue
                sector_id = level.sidedefs[side_index].sector
                by_sector[sector_id].append((level.vertices[line.v1].x, level.vertices[line.v1].y))
                by_sector[sector_id].append((level.vertices[line.v2].x, level.vertices[line.v2].y))
        for points in by_sector.values():
            xs, ys = [p[0] for p in points], [p[1] for p in points]
            w, d = max(xs) - min(xs), max(ys) - min(ys)
            areas.append((w * d) / (profile.body_width ** 2))
    return {
        "$schema": "llmapper.spatial-corpus",
        "schema_version": SCHEMA_VERSION,
        "game": "doom",
        "profile": profile.id,
        "maps": sum(1 for level in levels if level.supported),
        "opening_width_player_widths": widths,
        "traversable_opening_width_player_widths": trav_widths,
        "clear_height_player_heights": heights,
        "footprint_player_areas": areas,
        "summaries": {
            "opening_width_player_widths": _summary(widths),
            "traversable_opening_width_player_widths": _summary(trav_widths),
            "clear_height_player_heights": _summary(heights),
            "footprint_player_areas": _summary(areas),
        },
        "clusters": [],
    }


def inspect_doom_space(level: DoomDiskMap, sector_ids: Iterable[int] | None = None, *, corpus: dict[str, Any] | None = None) -> dict[str, Any]:
    if not level.supported:
        raise PlayerSpaceError(f"cannot inspect unsupported Doom map {level.name}")
    profile = player_profile("doom")
    selected = sorted(set(range(len(level.sectors))) if sector_ids is None else {int(value) for value in sector_ids})
    heights = [
        float(level.sectors[sector_id].ceiling_height - level.sectors[sector_id].floor_height)
        for sector_id in selected
    ]
    sky = sum(
        1 for sector_id in selected
        if texture_label(level.sectors[sector_id].ceiling_texture) in SKY_FLATS
    )
    openings = []
    perimeter = 0.0
    open_width = 0.0
    points: list[tuple[int, int]] = []
    for line in level.linedefs:
        v1, v2 = level.vertices[line.v1], level.vertices[line.v2]
        length = hypot(v1.x - v2.x, v1.y - v2.y)
        sides = [line.side_front]
        if line.side_back != NO_SIDE:
            sides.append(line.side_back)
        owners = [
            level.sidedefs[side].sector
            for side in sides if 0 <= side < len(level.sidedefs)
        ]
        if not set(owners) & set(selected):
            continue
        points.extend(((v1.x, v1.y), (v2.x, v2.y)))
        perimeter += length
        two_sided = bool(line.flags & ML_TWOSIDED) and line.side_back != NO_SIDE
        if two_sided:
            openings.append(length)
            if not set(owners) <= set(selected):
                open_width += length
    if not points:
        raise PlayerSpaceError("selection has no linedefs")
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    width, depth = float(max(xs) - min(xs)), float(max(ys) - min(ys))
    footprint = width * depth
    height_summary = _summary(heights)
    bottleneck = None if not openings else min(openings)
    movement = None
    if bottleneck is not None:
        opening = height_summary["min"] if height_summary else 0
        movement = traversal_affordances(
            width=bottleneck, opening=opening, floor_delta=0, blocking=False, profile=profile,
        )
    enclosure = _enclosure(
        sky_fraction=sky / max(1, len(selected)),
        perimeter=perimeter,
        open_width=open_width,
        median_height=None if height_summary is None else height_summary["median"],
        profile=profile,
    )
    corpus = corpus or {}
    payload = {
        "$schema": SCHEMA, "schema_version": SCHEMA_VERSION, "kind": "space",
        "source_game": "doom", "map": level.name,
        "sectors": [_ref("sector", value) for value in selected],
        "profile": profile.to_dict(),
        "movement": {
            "narrowest_connection": None if bottleneck is None else layered(
                raw=bottleneck, unit=profile.body_width, unit_name="width",
                samples=corpus_samples(corpus, "traversable_opening_width_player_widths")
                or corpus_samples(corpus, "opening_width_player_widths"),
                low="unusually tight passage", high="unusually wide passage", profile=profile,
            ),
            "affordances": movement,
            "connector_count": None,
        },
        "scale": {
            "footprint": layered(
                raw=footprint, unit=profile.body_width ** 2, unit_name="area",
                samples=corpus_samples(corpus, "footprint_player_areas"), profile=profile,
            ),
            "aabb_width": layered(raw=width, unit=profile.body_width, unit_name="width", profile=profile),
            "clear_height": layered(
                raw=None if height_summary is None else height_summary["median"],
                unit=profile.standing_height, unit_name="height",
                samples=corpus_samples(corpus, "clear_height_player_heights"), profile=profile,
            ),
            "clear_height_range": height_summary,
        },
        "shape": {
            "elongation": round(max(width, depth) / max(1.0, min(width, depth)), 4),
            "sector_count": len(selected),
            "basis": "AABB of linedefs touching the selected Doom sectors",
        },
        "enclosure": enclosure,
    }
    return payload


def conversion_player_scale_report() -> dict[str, Any]:
    """Compare existing conversion scales against player-body ratios. Does not replace them."""
    blood, duke, doom = player_profile("blood"), player_profile("duke3d"), player_profile("doom")
    duke_in_blood = duke.body_width * 3 / 2
    doom_in_blood = doom.body_width * 16
    return {
        "$schema": "llmapper.player-scale-conversion",
        "schema_version": SCHEMA_VERSION,
        "existing_scales": {
            "duke_to_blood_xy": "3:2 from E3L1/DNE3L1 wall-vector overlap",
            "doom_to_blood_xy": "16 from wad2map.cpp and TEDE1M9",
        },
        "player_body_width": {
            "blood": blood.body_width,
            "duke3d": duke.body_width,
            "doom": doom.body_width,
        },
        "after_existing_xy_scale": {
            "duke_body_width_in_blood_units": duke_in_blood,
            "doom_body_width_in_blood_units": doom_in_blood,
            "duke_over_blood": round(duke_in_blood / blood.body_width, 4),
            "doom_over_blood": round(doom_in_blood / blood.body_width, 4),
        },
        "standing_height_after_z_scale": {
            "duke_pheight_in_blood_units": duke.standing_height * 3 / 2,
            "doom_height_in_blood_units": doom.standing_height * 256,
            "blood_eye": blood.standing_height,
        },
        "conclusion": (
            "Existing map-geometry scales remain the conversion default. Player-body "
            "ratios differ: 3:2 Duke→Blood makes Duke's clip cylinder ~28% wider than "
            "Blood's player, and Doom×16 makes a 32-unit Doom body 512 Blood units vs "
            "Blood's 384. Preserve relative player scale as a report, not a replacement."
        ),
        "evidence": [blood.evidence["body_radius"], duke.evidence["body_radius"], doom.evidence["body_radius"]],
    }


def comparable_openings(*items: tuple[str, float | int]) -> dict[str, Any]:
    """Player-relative comparison of native openings across games."""
    rows = []
    for game, width in items:
        profile = player_profile(game)
        rows.append({
            "game": profile.game,
            "raw": int(width),
            "native_unit": profile.native_unit,
            "player_widths": _ratio(width, profile.body_width),
            "profile": profile.id,
        })
    widths = [item["player_widths"] for item in rows if item["player_widths"] is not None]
    spread = None if len(widths) < 2 else round(max(widths) - min(widths), 4)
    return {
        "openings": rows,
        "player_width_spread": spread,
        "approximately_comparable": bool(spread is not None and spread <= 0.35),
        "basis": "native widths divided by each game's collision body width; conversion XY scales are not applied",
    }


def _expand_measured(values: Any) -> list[float]:
    if values is None:
        return []
    if isinstance(values, dict):
        counts = values.get("counts") or {}
        expanded: list[float] = []
        for key, count in counts.items():
            expanded.extend([float(key)] * int(count))
        if expanded:
            return expanded
        return [float(values[key]) for key in ("min", "p25", "median", "p75", "max") if key in values]
    return [float(value) for value in values]


def material_player_scale(asset: dict[str, Any], *, game: str | None = None) -> dict[str, Any]:
    """Player-relative world coverage from a materials catalog asset."""
    profile = player_profile(game or str(asset.get("game") or "blood"))
    appearance = asset.get("appearance") or {}
    dist = asset.get("distributions") or {}
    return material_world_scale(
        world_widths=_expand_measured(dist.get("world_width")),
        x_repeats=_expand_measured(dist.get("x_repeat")),
        tile_width=appearance.get("width"),
        profile=profile,
        sector_heights=_expand_measured(dist.get("sector_height")),
        y_repeats=_expand_measured(dist.get("y_repeat")),
        tile_height=appearance.get("height"),
    )


def material_world_scale(
    *,
    world_widths: Iterable[int],
    x_repeats: Iterable[int],
    tile_width: int | None,
    profile: PlayerSpatialProfile,
    sector_heights: Iterable[int] | None = None,
    y_repeats: Iterable[int] | None = None,
    tile_height: int | None = None,
) -> dict[str, Any]:
    """World coverage of a texture relative to the player, from measured placements."""
    widths = _expand_measured(world_widths)
    repeats = [int(value) for value in _expand_measured(x_repeats) if int(value) > 0]
    per_repeat = []
    if tile_width:
        # Build x-repeat 8 is 1:1 texel-to-world; coverage per tile ≈ tile_width * xrepeat / 8.
        per_repeat = [tile_width * value / 8.0 for value in repeats]
    elif widths and repeats and len(widths) == len(repeats):
        per_repeat = [width * 8.0 / repeat for width, repeat in zip(widths, repeats)]
    height_repeat = []
    y_values = _expand_measured(y_repeats)
    if tile_height and y_values:
        height_repeat = [tile_height * int(value) / 8.0 for value in y_values if int(value) > 0]
    elif sector_heights:
        height_repeat = _expand_measured(sector_heights)
    typical_repeat = None if not repeats else sorted(repeats)[len(repeats) // 2]
    world = _summary([float(value) for value in widths])
    coverage = _summary(per_repeat)
    return {
        "world_width": world,
        "x_repeat": _summary([float(value) for value in repeats]),
        "world_per_horizontal_repeat": coverage,
        "player_widths_per_repeat": None if not per_repeat else _summary(
            [value / profile.body_width for value in per_repeat]
        ),
        "player_heights_per_repeat": None if not height_repeat else _summary(
            [value / profile.standing_height for value in height_repeat]
        ),
        "typical_x_repeat": typical_repeat,
        "rarely_tiled_horizontally": bool(
            world is not None and coverage is not None and world["median"] <= 2.5 * coverage["median"]
        ),
        "profile": profile.id,
        "basis": "Build x-repeat 8 is 1:1; player-relative coverage uses the game player profile",
    }


def sprite_height_above_floor(
    build: BuildIR, sprite_id: int, *, profile: PlayerSpatialProfile | None = None,
) -> dict[str, Any]:
    sprite = build.sprites[int(sprite_id)]["fields"]
    sector = build.sectors[int(sprite["sector"])]["fields"]
    profile = profile or player_profile(build.source_game)
    # Build sprite z is typically at the sprite origin; floor_z is the sector floor.
    above = abs(int(sector["floor_z"]) - int(sprite["z"]))
    return layered(
        raw=above, unit=profile.standing_height, unit_name="height", profile=profile,
        low="near the floor", high="high on the wall or in the volume",
    )


# ---------------------------------------------------------------------------
# Negative space: the clearance an assembly claims
# ---------------------------------------------------------------------------
#
# `04_...md`: many design constraints are about intentionally empty space, and
# the concept matters more than the geometry. Nothing here builds a sector; a
# clearance is a claim about floor an assembly needs kept free, carried by the
# assembly and checkable against a map.
#
# The numbers below are measured, and they overturned the obvious model. Of the
# 146 counter-like bundles in the campaign, only 23% keep half a player width
# on *every* side and 73% are flush against their host on at least one -- a
# counter backs onto something. What every one of them keeps is one open side.
# So the claim is an access front, not a prism around the object.

#: Every campaign bundle measured keeps at least this much free floor on its
#: widest side; the median is 9.33. Below this nothing was observed, which is
#: what makes it a floor rather than a preference.
ACCESS_FRONT_MIN_PLAYER_WIDTHS = 1.333

CLEARANCE_ROLES = {
    "access_front": "the open side an assembly is used from",
    "workspace_behind": "the side an operator stands on, when there is one",
}


@dataclass(frozen=True)
class Clearance:
    """Floor an assembly claims. `hard` is false: this is a design claim.

    `sides_player_widths` is sorted, so the value carries no world bearing --
    the same assembly rotated a quarter turn produces the same clearance.
    """

    id: str
    owner: str
    role: str
    hard: bool
    sides_player_widths: tuple[float, ...]
    required_free_from: tuple[str, ...] = ("static_solids",)
    preferred_free_from: tuple[str, ...] = ("decoration",)
    basis: str = ""

    @property
    def access_front(self) -> float:
        """The widest free side. What the assembly is actually used from."""
        return max(self.sides_player_widths) if self.sides_player_widths else 0.0

    @property
    def narrowest(self) -> float:
        return min(self.sides_player_widths) if self.sides_player_widths else 0.0

    @property
    def backs_onto_something(self) -> bool:
        """Flush on at least one side. True of 73% of campaign counters."""
        return self.narrowest <= 0.05

    @property
    def asymmetric(self) -> bool:
        widest = self.access_front
        return widest > 0 and self.narrowest / widest < 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "owner": self.owner,
            "role": self.role,
            "hard": self.hard,
            "sides_player_widths": list(self.sides_player_widths),
            "access_front_player_widths": round(self.access_front, 3),
            "narrowest_player_widths": round(self.narrowest, 3),
            "backs_onto_something": self.backs_onto_something,
            "asymmetric": self.asymmetric,
            "required_free_from": list(self.required_free_from),
            "preferred_free_from": list(self.preferred_free_from),
            "basis": self.basis,
        }


def bundle_clearance(
    build, core: int, host: int, *, game: str = "blood", owner: str | None = None,
) -> Clearance:
    """The free floor a raised island keeps inside its host, per side.

    Bounding boxes, not polygons: the gap is between the core's plan box and
    the host's, which is exact under the quarter-turn rotations Build geometry
    admits and is named `bounding-box` in the basis so no consumer mistakes it
    for a swept volume. A negative side means the core's box reaches past the
    host's, which happens when the host is L-shaped; it is reported, not
    clamped.
    """
    from .anchors import _sector_bounds

    profile = player_profile(game)
    core_box = _sector_bounds(build, core)
    host_box = _sector_bounds(build, host)
    if core_box is None or host_box is None:
        raise PlayerSpaceError(f"sector:{core} or sector:{host} has no outline")
    gaps = sorted([
        core_box[0] - host_box[0], core_box[1] - host_box[1],
        host_box[2] - core_box[2], host_box[3] - core_box[3],
    ])
    return Clearance(
        id=f"sector:{core}:access",
        owner=owner or f"sector:{core}",
        role="access_front",
        hard=False,
        sides_player_widths=tuple(round(g / profile.body_width, 3) for g in gaps),
        basis="bounding-box gap between the core and its host, per side, sorted",
    )


def check_clearance(
    clearance: Clearance, *, minimum: float = ACCESS_FRONT_MIN_PLAYER_WIDTHS,
) -> dict[str, Any]:
    """Does this assembly keep the access front the corpus always keeps?

    Deliberately **not** a clearance-all-round check. Asserting free floor on
    every side would reject 77% of the campaign's own counters, which is how a
    plausible rule becomes a critic that fails the source material.
    """
    front = clearance.access_front
    violations = []
    if front < minimum:
        violations.append({
            "code": "access-front-too-narrow",
            "measured_player_widths": round(front, 3),
            "minimum_player_widths": minimum,
            "message": f"widest free side is {front:.2f} player widths; every "
                       f"campaign bundle measured keeps at least {minimum}",
        })
    return {
        "owner": clearance.owner,
        "role": clearance.role,
        "hard": clearance.hard,
        "access_front_player_widths": round(front, 3),
        "passes": not violations,
        "violations": violations,
        "notes": [
            "backs onto something on at least one side" if clearance.backs_onto_something
            else "free on every side, which 77% of campaign counters are not",
        ],
    }
