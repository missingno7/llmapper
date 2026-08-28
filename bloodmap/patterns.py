"""Corpus-grounded design-pattern observation, clustering, and retrieval.

This layer sits between sensors and interpretation. It does not name rooms.
It records measurable spawn, route, morphology, and vertical relationships,
clusters them by independent discrete signatures, and retrieves precedents.

Populations are never mixed: original campaign, original BloodBath, conversions,
and generated maps stay separate.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from math import atan2, degrees, hypot
from pathlib import Path
from typing import Any, Iterable

from .build_ir import BuildIR
from .design import _polygon_loops, _signed_area
from .exposure import (
    ExposureError,
    route_exposure_report,
    spawn_neighborhood_report,
)
from .format import read_map
from .model import DiskMap
from .morphology import _loop_metrics
from .player_space import PLAYER_PROFILES
from .sight import spawn_sight_report
from .spatial import analyze_spatial


SCHEMA = "llmapper.design-patterns"
SCHEMA_VERSION = 1
PLAYER_WIDTH = 384
#: One standing human, from the player profile. Never hardcode this: it was
#: 0x1600 in a dozen modules, which is `POSTURE.eyeAboveZ` -- an offset from
#: the sprite's centre, not a body -- and every height in the project was
#: denominated in a unit 3x too small.
PLAYER_HEIGHT = PLAYER_PROFILES["blood"].standing_height

POPULATIONS = {
    "blood-campaign": "original Blood single-player episode maps (E*M*)",
    "blood-bloodbath": "original BloodBath deathmatch maps (BB*)",
    "conversion": "Duke/Doom conversions and derived Blood maps",
    "generated": "scratch-authored or reconstructed maps",
    "other": "unclassified Blood MAPs",
}


class PatternError(ValueError):
    pass


def classify_map_population(path: str | Path) -> str:
    """Fail-closed population label from filename provenance, not contents."""
    stem = Path(path).stem.upper()
    name = Path(path).name.upper()
    if "RECONSTRUCTION" in name:
        return "generated"
    if name.endswith("-BLOOD.MAP"):
        return "conversion"
    if stem.startswith(("DWE", "DNE", "TEDE", "DW")):
        return "conversion"
    if stem.startswith("BB") and stem[2:].isdigit():
        return "blood-bloodbath"
    if len(stem) >= 4 and stem[0] == "E" and stem[1].isdigit() and "M" in stem:
        return "blood-campaign"
    return "other"


def list_original_maps(directory: str | Path, *, population: str) -> list[Path]:
    root = Path(directory)
    if population not in POPULATIONS:
        raise PatternError(f"unknown population {population!r}")
    files = sorted(
        path for path in root.iterdir()
        if path.is_file() and path.suffix.lower() == ".map"
    )
    return [path for path in files if classify_map_population(path) == population]


def _id(ref: str) -> int:
    return int(str(ref).split(":", 1)[1])


def _sky(build: BuildIR, sector_id: int) -> bool:
    return bool(int(build.sectors[sector_id]["fields"]["ceiling_stat"]) & 1)


def _area(build: BuildIR, sector_id: int) -> float:
    return abs(sum(_signed_area(loop) for loop in _polygon_loops(build, sector_id)))


def _shade(build: BuildIR, sector_id: int) -> dict[str, int]:
    fields = build.sectors[sector_id]["fields"]
    first = int(fields["wall_ptr"])
    count = int(fields["wall_count"])
    walls = [int(build.walls[wid]["fields"].get("shade") or 0) for wid in range(first, first + count)]
    return {
        "floor": int(fields.get("floor_shade") or 0),
        "ceiling": int(fields.get("ceiling_shade") or 0),
        "wall_mean": int(round(sum(walls) / max(1, len(walls)))),
    }


def _materials(build: BuildIR, sector_id: int) -> dict[str, int]:
    fields = build.sectors[sector_id]["fields"]
    first = int(fields["wall_ptr"])
    wall_pic = int(build.walls[first]["fields"]["picnum"]) if 0 <= first < len(build.walls) else 0
    return {
        "floor_picnum": int(fields["floor_picnum"]),
        "ceiling_picnum": int(fields["ceiling_picnum"]),
        "wall_picnum": wall_pic,
    }


def _bin_relative(value: float | None, median: float, *, low: float = 0.5, high: float = 2.0) -> str:
    if value is None or median <= 0:
        return "unknown"
    if value < low * median:
        return "small"
    if value > high * median:
        return "large"
    return "medium"


def _bin_hops(value: int | None) -> str:
    if value is None:
        return "none"
    if value <= 0:
        return "0"
    if value == 1:
        return "1"
    return "2+"


def _bin_exits(value: int) -> str:
    if value <= 1:
        return "1"
    if value == 2:
        return "2"
    return "3+"


def _bin_frac(value: float | None, *, low: float = 0.25, high: float = 0.75) -> str:
    if value is None:
        return "unknown"
    if value < low:
        return "low"
    if value > high:
        return "high"
    return "mid"


def _bin_sight(widths: float | None) -> str:
    if widths is None:
        return "unknown"
    if widths < 8:
        return "low"
    if widths < 24:
        return "mid"
    return "high"


def _bin_step(player_heights: float) -> str:
    mag = abs(player_heights)
    if mag < 0.25:
        return "flat"
    if mag < 1.5:
        return "step"
    return "storey"


def observe_spawn_neighborhoods(
    disk: DiskMap, *, map_id: str, population: str, force: bool = False,
) -> list[dict[str, Any]]:
    """One observation sample per multiplayer start.

    Mining keeps this BloodBath-only so campaign maps are not silently mixed.
    Pattern-aware reading may pass force=True to score a generated candidate.
    """
    if population != "blood-bloodbath" and not force:
        return []
    build = disk.to_build_ir()
    try:
        neighborhoods = spawn_neighborhood_report(build, include_sp_start=False)
        sight = spawn_sight_report(build, include_sp_start=False)
    except ExposureError:
        return []
    clear_by_origin: dict[str, list[bool]] = defaultdict(list)
    for pair in sight.get("pairs") or []:
        clear_by_origin[str(pair["a"])].append(bool(pair["clear"]))
        clear_by_origin[str(pair["b"])].append(bool(pair["clear"]))
    samples = []
    for item in neighborhoods["neighborhoods"]:
        sector_id = _id(item["sector"])
        origin = str(item["origin"])
        clears = clear_by_origin.get(origin) or []
        samples.append({
            "subject": "spawn-neighborhood",
            "population": population,
            "map": map_id,
            "focus": {"sprite": int(item["sprite_id"]), "sector": sector_id, "origin": origin},
            "geometry": {
                "sky_ceiling": item["sky_ceiling"],
                "vertices": _loop_metrics(max(_polygon_loops(build, sector_id), key=lambda loop: abs(_signed_area(loop))))["vertices"],
            },
            "scale": {
                "spawn_sector_area_player_areas": item["spawn_sector_area_player_areas"],
                "local_reachable_area_player_areas": item["local_reachable_area_player_areas"],
            },
            "visibility": {
                "max_2d_sight_player_widths": item["max_2d_sight_player_widths"],
                "sky_region_ray_fraction": item["sky_region_ray_fraction"],
                "spawn_pair_clear_fraction": None if not clears else round(sum(clears) / len(clears), 4),
            },
            "routes": {
                "immediate_portal_choices": item["immediate_portal_choices"],
                "hops_to_largest_sky_region": item["hops_to_largest_sky_region"],
            },
            "materials": _materials(build, sector_id),
            "lighting": _shade(build, sector_id),
            "evidence": ["spawn_neighborhood_report", "spawn_sight_report"],
        })
    return samples


def observe_routes(disk: DiskMap, *, map_id: str, population: str, include_sp_start: bool) -> list[dict[str, Any]]:
    build = disk.to_build_ir()
    try:
        report = route_exposure_report(build, include_sp_start=include_sp_start)
    except ExposureError:
        return []
    samples = []
    for route in report["routes"]:
        if not route.get("reachable"):
            continue
        seq = []
        heights = []
        shades = []
        for sample in route.get("samples") or []:
            sector_id = _id(sample["sector"])
            seq.append("S" if sample["sky_ceiling"] else "C")
            fields = build.sectors[sector_id]["fields"]
            heights.append(int(fields["floor_z"]))
            shades.append(_shade(build, sector_id)["wall_mean"])
        compressed = []
        for token in seq:
            if not compressed or compressed[-1] != token:
                compressed.append(token)
        first_h, last_h = (heights[0], heights[-1]) if heights else (0, 0)
        first_s, last_s = (shades[0], shades[-1]) if shades else (0, 0)
        samples.append({
            "subject": "route-exposure",
            "population": population,
            "map": map_id,
            "focus": {"origin": route["origin"], "hops": route["hops"]},
            "geometry": {"cover_sequence": "".join(compressed), "hops": route["hops"]},
            "scale": {
                "sky_sample_fraction": route["sky_sample_fraction"],
                "mean_max_sight_player_widths": route["mean_max_sight_player_widths"],
                "min_max_sight_player_widths": route["min_max_sight_player_widths"],
            },
            "visibility": {
                "cover_sky_transitions": route["cover_sky_transitions"],
            },
            "routes": {
                "floor_delta_player_heights": round((last_h - first_h) / PLAYER_HEIGHT, 4),
                "shade_delta": last_s - first_s,
            },
            "lighting": {"origin_wall_shade": first_s, "destination_wall_shade": last_s},
            "evidence": ["route_exposure_report"],
        })
    return samples


def observe_morphology(disk: DiskMap, *, map_id: str, population: str) -> list[dict[str, Any]]:
    build = disk.to_build_ir()
    samples = []
    for sector_id in range(len(build.sectors)):
        area = _area(build, sector_id) / (PLAYER_WIDTH ** 2)
        if area < 1.0:
            continue
        loops = _polygon_loops(build, sector_id)
        outer = max(loops, key=lambda loop: abs(_signed_area(loop)))
        metrics = _loop_metrics(outer)
        if metrics["vertices"] < 3:
            continue
        turns = []
        lengths = []
        n = len(outer)
        for index in range(n):
            ax, ay = outer[index]
            bx, by = outer[(index + 1) % n]
            lengths.append(hypot(bx - ax, by - ay))
            cx, cy = outer[(index + 2) % n]
            ux, uy = bx - ax, by - ay
            vx, vy = cx - bx, cy - by
            lu, lv = hypot(ux, uy), hypot(vx, vy)
            if lu < 1 or lv < 1:
                continue
            turns.append(round(degrees(atan2(ux * vy - uy * vx, ux * vx + uy * vy)) / 15.0) * 15)
        perimeter = sum(lengths) or 1.0
        rel = [round(value / perimeter, 3) for value in lengths]
        samples.append({
            "subject": "local-morphology",
            "population": population,
            "map": map_id,
            "focus": {"sector": sector_id},
            "geometry": {
                "vertices": metrics["vertices"],
                "rectangular": metrics["rectangular"],
                "convex": metrics["convex"],
                "chamfer_corners": metrics["chamfer_corners"],
                "curved_chains": metrics["curved_chains"],
                "aabb_fill": metrics["aabb_fill"],
                "turn_sequence_deg": turns,
                "relative_lengths": rel,
            },
            "scale": {"area_player_areas": round(area, 4)},
            "materials": _materials(build, sector_id),
            "lighting": _shade(build, sector_id),
            "context": {"sky_ceiling": _sky(build, sector_id), "hole_count": max(0, len(loops) - 1)},
            "evidence": ["analyze_morphology loop metrics"],
        })
    return samples


def observe_vertical(disk: DiskMap, *, map_id: str, population: str) -> list[dict[str, Any]]:
    build = disk.to_build_ir()
    spatial = analyze_spatial(build)
    samples = []
    for edge in spatial["views"]["traversability"]["walkable_at_rest"]:
        left, right = _id(edge["sectors"][0]), _id(edge["sectors"][1])
        lf = int(build.sectors[left]["fields"]["floor_z"])
        rf = int(build.sectors[right]["fields"]["floor_z"])
        delta = (rf - lf) / PLAYER_HEIGHT
        if abs(delta) < 0.2:
            continue
        ls, rs = _sky(build, left), _sky(build, right)
        if ls == rs:
            sky_rel = "same"
        elif (not ls) and rs:
            sky_rel = "cover_to_open"
        else:
            sky_rel = "open_to_cover"
        shade_delta = _shade(build, right)["wall_mean"] - _shade(build, left)["wall_mean"]
        samples.append({
            "subject": "vertical-transition",
            "population": population,
            "map": map_id,
            "focus": {"sectors": [left, right], "wall": edge.get("wall")},
            "geometry": {
                "floor_delta_player_heights": round(delta, 4),
                "sky_relationship": sky_rel,
            },
            "scale": {
                "left_area_player_areas": round(_area(build, left) / (PLAYER_WIDTH ** 2), 4),
                "right_area_player_areas": round(_area(build, right) / (PLAYER_WIDTH ** 2), 4),
            },
            "visibility": {"sky_relationship": sky_rel},
            "lighting": {
                "shade_delta": shade_delta,
                "left": _shade(build, left),
                "right": _shade(build, right),
            },
            "materials": {"left": _materials(build, left), "right": _materials(build, right)},
            "evidence": ["spatial.traversability.walkable_at_rest"],
        })
    return samples


def observe_map(path: str | Path, *, population: str | None = None) -> list[dict[str, Any]]:
    path = Path(path)
    pop = population or classify_map_population(path)
    disk = read_map(path)
    map_id = path.name
    samples: list[dict[str, Any]] = []
    samples.extend(observe_spawn_neighborhoods(disk, map_id=map_id, population=pop))
    samples.extend(observe_routes(
        disk, map_id=map_id, population=pop,
        include_sp_start=pop == "blood-campaign",
    ))
    samples.extend(observe_morphology(disk, map_id=map_id, population=pop))
    samples.extend(observe_vertical(disk, map_id=map_id, population=pop))
    return samples


def _spawn_signature(sample: dict[str, Any], medians: dict[str, float]) -> str:
    vis = sample["visibility"]
    routes = sample["routes"]
    scale = sample["scale"]
    return "|".join((
        f"sky:{int(sample['geometry']['sky_ceiling'])}",
        f"hops:{_bin_hops(routes['hops_to_largest_sky_region'])}",
        f"exits:{_bin_exits(int(routes['immediate_portal_choices']))}",
        f"area:{_bin_relative(scale['spawn_sector_area_player_areas'], medians.get('spawn_area', 1))}",
        f"local:{_bin_relative(scale['local_reachable_area_player_areas'], medians.get('local_area', 1))}",
        f"field:{_bin_frac(vis['sky_region_ray_fraction'])}",
        f"sight:{_bin_sight(vis['max_2d_sight_player_widths'])}",
        f"peek:{_bin_frac(vis['spawn_pair_clear_fraction'], low=0.1, high=0.4)}",
    ))


def _route_signature(sample: dict[str, Any]) -> str:
    geo = sample["geometry"]
    routes = sample["routes"]
    return "|".join((
        f"seq:{geo['cover_sequence'] or '?'}",
        f"hops:{_bin_hops(geo['hops'])}",
        f"skyfrac:{_bin_frac(sample['scale']['sky_sample_fraction'])}",
        f"z:{_bin_step(float(routes['floor_delta_player_heights']))}",
        f"shade:{'darker' if routes['shade_delta'] > 4 else 'brighter' if routes['shade_delta'] < -4 else 'flat'}",
    ))


def _morph_signature(sample: dict[str, Any]) -> str:
    geo = sample["geometry"]
    verts = int(geo["vertices"])
    if verts <= 4:
        vbin = "4"
    elif verts <= 8:
        vbin = "5-8"
    else:
        vbin = "9+"
    fill = geo.get("aabb_fill") or 0
    return "|".join((
        f"rect:{int(bool(geo['rectangular']))}",
        f"convex:{int(bool(geo['convex']))}",
        f"verts:{vbin}",
        f"chamfer:{'1+' if geo['chamfer_corners'] else '0'}",
        f"curve:{'1+' if geo['curved_chains'] else '0'}",
        f"fill:{'boxy' if fill >= 0.75 else 'loose'}",
        f"sky:{int(bool(sample['context']['sky_ceiling']))}",
        f"holes:{'1+' if sample['context']['hole_count'] else '0'}",
    ))


def _vertical_signature(sample: dict[str, Any]) -> str:
    geo = sample["geometry"]
    shade = sample["lighting"]["shade_delta"]
    return "|".join((
        f"step:{_bin_step(float(geo['floor_delta_player_heights']))}",
        f"sky:{geo['sky_relationship']}",
        f"shade:{'darker' if shade > 4 else 'brighter' if shade < -4 else 'flat'}",
        f"into:{_bin_relative(sample['scale']['right_area_player_areas'], sample['scale']['left_area_player_areas'] or 1)}",
    ))


_SIGNATURES = {
    "spawn-neighborhood": _spawn_signature,
    "route-exposure": _route_signature,
    "local-morphology": _morph_signature,
    "vertical-transition": _vertical_signature,
}


def _median(values: list[float]) -> float:
    if not values:
        return 1.0
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def cluster_samples(samples: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Group samples by independent discrete signatures. No room names."""
    by_subject: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in samples:
        by_subject[str(sample["subject"])].append(sample)
    medians = {
        "spawn_area": _median([
            item["scale"]["spawn_sector_area_player_areas"]
            for item in by_subject.get("spawn-neighborhood", [])
        ]),
        "local_area": _median([
            item["scale"]["local_reachable_area_player_areas"]
            for item in by_subject.get("spawn-neighborhood", [])
        ]),
    }
    candidates = []
    for subject, items in sorted(by_subject.items()):
        signer = _SIGNATURES[subject]
        buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in items:
            if subject == "spawn-neighborhood":
                key = signer(item, medians)
            else:
                key = signer(item)
            item = dict(item)
            item["signature"] = key
            buckets[key].append(item)
        for signature, members in sorted(buckets.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            maps = sorted({item["map"] for item in members})
            candidates.append({
                "candidate_id": f"candidate:{subject}:{signature}",
                "subject": subject,
                "signature": signature,
                "occurrence_count": len(members),
                "map_count": len(maps),
                "maps": maps,
                "occurrences": [
                    {"map": item["map"], "focus": item["focus"], "population": item["population"]}
                    for item in members
                ],
                "common_properties": _common_properties(subject, signature, members),
                "status": "unsigned",
            })
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "kind": "derived",
        "model": "discrete independent-view signatures; names are not assigned here",
        "sample_count": sum(len(items) for items in by_subject.values()),
        "candidates": candidates,
        "medians": medians,
        "limitations": [
            "signatures are quantized; nearby geometry may split across bins",
            "2D sight ignores height and sprites",
            "campaign and bloodbath populations must be mined separately",
        ],
    }


def _common_properties(subject: str, signature: str, members: list[dict[str, Any]]) -> dict[str, Any]:
    parts = dict(item.split(":", 1) for item in signature.split("|") if ":" in item)
    return {
        "signature_parts": parts,
        "count": len(members),
        "maps": sorted({item["map"] for item in members}),
    }


def mine_directory(directory: str | Path, *, population: str) -> dict[str, Any]:
    import sys

    paths = list_original_maps(directory, population=population)
    if not paths:
        raise PatternError(f"no maps for population {population} in {directory}")
    samples: list[dict[str, Any]] = []
    errors = []
    for index, path in enumerate(paths, start=1):
        print(f"[{index}/{len(paths)}] {path.name}", file=sys.stderr, flush=True)
        try:
            samples.extend(observe_map(path, population=population))
        except Exception as exc:
            errors.append({"map": path.name, "error": str(exc)})
    clustered = cluster_samples(samples)
    clustered["population"] = population
    clustered["maps_mined"] = [path.name for path in paths]
    clustered["observe_errors"] = errors
    return clustered


def signature_parts(signature: str | dict[str, Any] | None) -> dict[str, str]:
    if signature is None:
        return {}
    if isinstance(signature, dict):
        return {str(key): str(value) for key, value in signature.items()}
    return dict(item.split(":", 1) for item in str(signature).split("|") if ":" in item)


def parts_satisfy(parts: dict[str, str], require: dict[str, Any] | None) -> bool:
    """True when every required key equals the quantized signature part."""
    if not require:
        return True
    for key, value in require.items():
        if key in {"tag", "status", "scale", "id", "population"}:
            continue
        if str(parts.get(key)) != str(value):
            return False
    return True


def sample_signature(sample: dict[str, Any], medians: dict[str, float] | None = None) -> str:
    subject = sample["subject"]
    medians = medians or {"spawn_area": 1.0, "local_area": 1.0}
    if subject == "spawn-neighborhood":
        return _spawn_signature(sample, medians)
    if subject == "route-exposure":
        return _route_signature(sample)
    if subject == "local-morphology":
        return _morph_signature(sample)
    if subject == "vertical-transition":
        return _vertical_signature(sample)
    raise PatternError(f"unknown subject {subject!r}")


def pattern_matches_signature(pattern: dict[str, Any], signature: str) -> bool:
    """A sample may match several patterns; exact string equality is not required."""
    parts = signature_parts(signature)
    match = pattern.get("match") or {}
    if match:
        return parts_satisfy(parts, match)
    listed = pattern.get("signatures") or []
    if listed:
        return signature in listed or any(parts_satisfy(parts, signature_parts(item)) for item in listed)
    stored = pattern.get("signature")
    if isinstance(stored, dict) and stored:
        return parts_satisfy(parts, stored)
    if isinstance(stored, str) and "|" in stored:
        return signature == stored or parts_satisfy(parts, signature_parts(stored))
    return False


def load_catalog(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def query_catalog(
    catalog: dict[str, Any],
    *,
    view: str | None = None,
    require: dict[str, Any] | None = None,
    map_name: str | None = None,
    population: str | None = None,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Return multiple matching pattern occurrences, never a single best match."""
    require = require or {}
    buckets: list[list[dict[str, Any]]] = []
    for pattern in catalog.get("patterns") or []:
        if view and view not in {
            pattern.get("view"), pattern.get("scale"), pattern.get("subject"),
        }:
            continue
        if population and pattern.get("population") != population:
            continue
        tags = [str(item) for item in (pattern.get("tags") or [])]
        parts = signature_parts(pattern.get("match") or pattern.get("signature"))
        ok = True
        for key, value in require.items():
            expected = str(value)
            if key == "tag":
                ok = expected in tags
            elif key in parts:
                ok = str(parts.get(key)) == expected
            elif key in {"status", "scale", "subject", "population"}:
                ok = str(pattern.get(key)) == expected
            elif expected in tags:
                ok = True
            else:
                ok = False
            if not ok:
                break
        if not ok:
            continue
        bucket = []
        for occurrence in pattern.get("occurrences") or []:
            if map_name and occurrence.get("map") != map_name:
                continue
            bucket.append({
                "pattern_id": pattern["id"],
                "status": pattern.get("status"),
                "subject": pattern.get("subject"),
                "signature": pattern.get("signature") or pattern.get("match"),
                "occurrence": occurrence,
                "interpretation": (pattern.get("interpretation") or {}).get("label"),
            })
        if bucket:
            buckets.append(bucket)
    hits = []
    while buckets and len(hits) < limit:
        remaining = []
        for bucket in buckets:
            hits.append(bucket.pop(0))
            if bucket:
                remaining.append(bucket)
            if len(hits) >= limit:
                break
        buckets = remaining
    return hits


def inspect_pattern(catalog: dict[str, Any], pattern_id: str) -> dict[str, Any]:
    for pattern in catalog.get("patterns") or []:
        if pattern.get("id") == pattern_id:
            return pattern
    raise PatternError(f"unknown pattern {pattern_id!r}")


def match_samples_to_catalog(samples: list[dict[str, Any]], catalog: dict[str, Any]) -> list[dict[str, Any]]:
    """Attach every matching catalog hypothesis to a sample. Overlap is allowed."""
    medians = catalog.get("medians") or {"spawn_area": 40.0, "local_area": 200.0}
    matches = []
    for sample in samples:
        subject = sample["subject"]
        if subject not in _SIGNATURES:
            continue
        signature = sample_signature(sample, medians)
        for pattern in catalog.get("patterns") or []:
            if pattern.get("subject") != subject:
                continue
            if not pattern_matches_signature(pattern, signature):
                continue
            matches.append({
                "pattern_id": pattern["id"],
                "status": pattern.get("status"),
                "subject": subject,
                "signature": signature,
                "focus": sample["focus"],
                "interpretation": (pattern.get("interpretation") or {}).get("label"),
                "confidence": pattern.get("confidence"),
            })
    return matches


def attach_corpus_occurrences(
    catalog: dict[str, Any],
    unsigned: dict[str, Any],
    *,
    max_occurrences: int = 32,
) -> dict[str, Any]:
    """Fill pattern occurrence lists from an unsigned mine of one population."""
    if catalog.get("medians") is None and unsigned.get("medians"):
        catalog["medians"] = unsigned["medians"]
    rows: list[dict[str, Any]] = []
    for candidate in unsigned.get("candidates") or []:
        for occurrence in candidate.get("occurrences") or []:
            rows.append({
                "subject": candidate["subject"],
                "signature": candidate["signature"],
                "map": occurrence["map"],
                "focus": occurrence.get("focus"),
                "population": occurrence.get("population") or unsigned.get("population"),
            })
    for pattern in catalog.get("patterns") or []:
        if pattern.get("population") and unsigned.get("population"):
            if pattern["population"] != unsigned["population"]:
                continue
        hits = [
            item for item in rows
            if item["subject"] == pattern.get("subject")
            and pattern_matches_signature(pattern, item["signature"])
        ]
        maps = sorted({item["map"] for item in hits})
        pattern["occurrence_count"] = len(hits)
        pattern["map_count"] = len(maps)
        pattern["maps"] = maps
        pattern["occurrences"] = [
            {
                "map": item["map"],
                "focus": item["focus"],
                "population": item["population"],
                "signature": item["signature"],
            }
            for item in hits[:max_occurrences]
        ]
        pattern["occurrences_truncated"] = len(hits) > max_occurrences
    return catalog


def pattern_aware_understanding(
    disk: DiskMap, catalog: dict[str, Any], *, map_id: str, population: str,
    include_sp_start: bool | None = None,
) -> dict[str, Any]:
    from .understanding import understand_map
    if include_sp_start is None:
        include_sp_start = population == "blood-campaign"
    packet = understand_map(disk, include_sp_start=include_sp_start)
    samples = []
    samples.extend(observe_spawn_neighborhoods(
        disk, map_id=map_id, population=population, force=True,
    ))
    samples.extend(observe_routes(
        disk, map_id=map_id, population=population,
        include_sp_start=population == "blood-campaign",
    ))
    samples.extend(observe_morphology(disk, map_id=map_id, population=population))
    samples.extend(observe_vertical(disk, map_id=map_id, population=population))
    matches = match_samples_to_catalog(samples, catalog)
    sky = packet.get("space") or {}
    sky_space = (sky.get("sky") or {}).get("footprint_player_areas") or 0
    cov_space = (sky.get("covered") or {}).get("footprint_player_areas") or 0
    sky_sectors = (sky.get("sky") or {}).get("sector_count") or 0
    cov_sectors = (sky.get("covered") or {}).get("sector_count") or 0
    total_area = sky_space + cov_space
    total_sectors = sky_sectors + cov_sectors
    packet["patterns"] = {
        "catalog": catalog.get("id"),
        "match_count": len(matches),
        "by_pattern": dict(Counter(item["pattern_id"] for item in matches)),
        "matches": matches,
        "area_vs_sector": {
            "sky_area_fraction": None if not total_area else round(sky_space / total_area, 4),
            "sky_sector_fraction": None if not total_sectors else round(sky_sectors / total_sectors, 4),
            "note": "sector count and footprint can disagree; both are evidence",
        },
        "limitations": [
            "matches are hypotheses over quantized signatures",
            "absence of a match is not evidence the relation is absent",
            "2D spawn sight ignores height",
        ],
    }
    return packet
