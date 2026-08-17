"""Single-player understanding packet: progression + mechanisms + materials + vertical.

This is a reading layer over original campaign maps. It does not copy polygons
into reconstructions. Physical walkability and allowed progress stay separate.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .blood_types import classify
from .format import read_map
from .model import DiskMap
from .patterns import classify_map_population, list_original_maps, observe_vertical
from .placement import observe_sprite_attachment, SWITCH_TYPES
from .player_space import PLAYER_PROFILES
from .progression import (
    EXIT_CHANNELS,
    analyze_progression,
    classify_mechanisms,
    compact_progression_report,
    completion_witness,
)
from .understanding import understand_map


SCHEMA = "llmapper.sp-understanding"
SCHEMA_VERSION = 1
PLAYER = PLAYER_PROFILES["blood"]
PLAYER_HEIGHT = PLAYER.standing_height


def _ontology_lookup() -> dict[int, dict[str, str]]:
    path = Path(__file__).resolve().parents[1] / "knowledge" / "blood" / "ontology-v2.json"
    if not path.is_file():
        return {}
    import json
    payload = json.loads(path.read_text(encoding="utf-8"))
    found: dict[int, dict[str, str]] = {}
    for item in payload.get("annotations") or []:
        asset = str(item.get("asset") or "")
        if not asset.startswith("blood:tile:"):
            continue
        try:
            tile = int(asset.rsplit(":", 1)[1])
        except ValueError:
            continue
        values = item.get("values") or {}
        found[tile] = {
            "visual_material": str(values.get("visual_material") or "unknown"),
            "architectural_role": str(values.get("architectural_role") or "unknown"),
            "surface_applicability": str(values.get("surface_applicability") or "unknown"),
        }
    return found


_ONTOLOGY = _ontology_lookup()


def describe_picnum(picnum: int) -> dict[str, Any]:
    facets = _ONTOLOGY.get(int(picnum))
    if facets is None:
        return {"picnum": int(picnum), "known_facets": False}
    return {"picnum": int(picnum), "known_facets": True, **facets}


def _modal(counter: Counter[int], *, n: int = 3) -> list[dict[str, Any]]:
    return [{"count": count, **describe_picnum(picnum)} for picnum, count in counter.most_common(n)]


def palette_summary(disk: DiskMap, sector_ids: set[int] | None = None) -> dict[str, Any]:
    selected = set(range(len(disk.sectors))) if sector_ids is None else set(sector_ids)
    floors: Counter[int] = Counter()
    ceils: Counter[int] = Counter()
    walls: Counter[int] = Counter()
    shades = []
    for sector_id in selected:
        sector = disk.sectors[sector_id]
        fields = sector.fields
        floors[int(fields["floor_picnum"])] += 1
        ceils[int(fields["ceiling_picnum"])] += 1
        shades.append((int(fields["floor_shade"]) + int(fields["ceiling_shade"])) / 2)
        first = int(fields["wall_ptr"])
        for wall_id in range(first, first + int(fields["wall_count"])):
            walls[int(disk.walls[wall_id].fields["picnum"])] += 1
    shades.sort()
    return {
        "sector_count": len(selected),
        "floor": _modal(floors),
        "ceiling": _modal(ceils),
        "wall": _modal(walls),
        "median_shade": None if not shades else round(shades[len(shades) // 2], 2),
        "shade_range": None if not shades else [round(shades[0], 2), round(shades[-1], 2)],
    }


def mechanism_chain_signature(chain: dict[str, Any]) -> str:
    from .progression import _chain_signature
    return _chain_signature(chain)


def mine_mechanism_compositions(directory: str | Path, *, population: str = "blood-campaign") -> dict[str, Any]:
    """Unsigned chain signatures across a population. Not a room ontology."""
    from .analysis import channel_graph
    from .progression import _motion_receivers

    paths = list_original_maps(directory, population=population)
    signatures: Counter[str] = Counter()
    by_sig: dict[str, list[str]] = defaultdict(list)
    errors = []
    for path in paths:
        try:
            disk = read_map(path)
            graph = channel_graph(disk)
            receivers = _motion_receivers(disk)
        except Exception as exc:
            errors.append({"map": path.name, "error": str(exc)})
            continue
        seen = set()
        for channel in graph["channels"]:
            if not channel["transmitters"] or not channel["receivers"]:
                continue
            chain = {
                "transmitters": channel["transmitters"],
                "receivers": channel["receivers"],
                "exit": channel["channel"] in EXIT_CHANNELS,
                "motion_receivers": receivers.get(channel["channel"], []),
            }
            sig = mechanism_chain_signature(chain)
            if sig in seen:
                continue
            seen.add(sig)
            signatures[sig] += 1
            if len(by_sig[sig]) < 8:
                by_sig[sig].append(path.name)
    recurring = [
        {"signature": sig, "maps": signatures[sig], "examples": by_sig[sig]}
        for sig, _count in signatures.most_common(40)
        if signatures[sig] >= 3
    ]
    return {
        "$schema": "llmapper.mechanism-compositions",
        "schema_version": 1,
        "kind": "derived",
        "population": population,
        "maps_mined": len(paths),
        "unique_signatures": len(signatures),
        "recurring": recurring,
        "observe_errors": errors[:20],
        "limitations": [
            "signature is TX/RX cardinality plus motion/exit flags, not a named puzzle type",
            "maps without a grounded channel graph are skipped",
        ],
    }


def e2m2_mechanism_patterns(report: dict[str, Any], compositions: dict[str, Any] | None = None) -> dict[str, Any]:
    candidates = []
    campaign = {
        item["signature"]: item for item in (compositions or {}).get("recurring") or []
    }
    for chain in report.get("chains") or []:
        n_rx = chain.get("receiver_count", len(chain.get("receivers") or []))
        n_tx = chain.get("transmitter_count", len(chain.get("transmitters") or []))
        sig = mechanism_chain_signature({
            "transmitters": chain.get("transmitters") or [f"{kind}:x" for kind in (chain.get("transmitter_kinds") or ["sprite"])] * n_tx,
            "receivers": ["x"] * n_rx,
            "exit": chain.get("exit"),
            "motion_receivers": chain.get("motion_receivers") or [],
        })
        status = "supported" if sig in campaign else "hypothesis"
        if n_rx < 2 and not chain.get("exit") and not chain.get("motion_receivers"):
            continue
        interpretation = None
        if chain.get("exit"):
            interpretation = "exit_channel"
        elif n_rx >= 2 and chain.get("motion_receivers"):
            interpretation = "fanout_motion"
        elif n_rx >= 2:
            interpretation = "fanout_receivers"
        elif chain.get("motion_receivers"):
            interpretation = "single_motion_gate"
        candidates.append({
            "channel": chain.get("channel"),
            "signature": sig,
            "status": status,
            "interpretation": interpretation,
            "campaign_maps": (campaign.get(sig) or {}).get("maps"),
            "examples": (campaign.get(sig) or {}).get("examples"),
        })
    return {
        "$schema": "llmapper.e2m2-mechanism-patterns",
        "schema_version": 1,
        "kind": "derived",
        "candidates": candidates,
        "pipeline": "E2M2 observation → signature → campaign search → supported/hypothesis",
    }


def enemy_placement_character(disk: DiskMap) -> dict[str, Any]:
    samples = []
    for index, sprite in enumerate(disk.sprites):
        typed = classify("sprite", int(sprite.fields["type"]))
        if typed.get("category") != "dude":
            continue
        try:
            sample = observe_sprite_attachment(disk, index)
        except Exception:
            continue
        samples.append(sample)
    if not samples:
        return {"count": 0}
    heights = sorted(item["height_from_floor_player_heights"] for item in samples)
    dists = sorted(item["wall_distance_player_widths"] for item in samples)
    return {
        "count": len(samples),
        "sit": dict(Counter(item["sit"] for item in samples)),
        "median_height_player_heights": round(heights[len(heights) // 2], 4),
        "median_wall_distance_player_widths": round(dists[len(dists) // 2], 4),
        "types": dict(Counter(item["type_id"] for item in samples)),
    }


def switch_attachment_character(disk: DiskMap) -> dict[str, Any]:
    samples = []
    for index, sprite in enumerate(disk.sprites):
        if int(sprite.fields["type"]) not in SWITCH_TYPES:
            continue
        try:
            samples.append(observe_sprite_attachment(disk, index))
        except Exception:
            continue
    if not samples:
        return {"count": 0}
    wall = [item for item in samples if item["wall_aligned"] or item["sit"] in {"wall_flush", "wall_offset"}]
    heights = sorted(item["height_from_floor_player_heights"] for item in wall) if wall else []
    return {
        "count": len(samples),
        "wall_mounted": len(wall),
        "sit": dict(Counter(item["sit"] for item in samples)),
        "median_wall_height_player_heights": None if not heights else round(heights[len(heights) // 2], 4),
    }


def build_sp_packet(disk: DiskMap, *, map_name: str = "") -> dict[str, Any]:
    """Independent SP understanding packet. No original vertex lists."""
    sensors = understand_map(disk, include_sp_start=True)
    progression = analyze_progression(disk)
    roles = classify_mechanisms(progression, disk)
    progression["roles"] = roles
    compact = compact_progression_report(progression)
    compact["witness_summary"] = completion_witness(progression)
    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "kind": "derived",
        "map": map_name,
        "model": "understand sensors + state-dependent progression; not a room detector",
        "sensors": {
            "parse": sensors["parse"],
            "aabb_player_widths": sensors["aabb_player_widths"],
            "starts": sensors["starts"],
            "pickup_categories": sensors["pickup_categories"],
            "space": sensors["space"],
            "spatial": sensors["spatial"],
            "morphology": {
                "orthogonal_length_fraction": (sensors.get("morphology") or {}).get("walls", {}).get("orthogonal_length_fraction"),
                "diagonal_length_fraction": (sensors.get("morphology") or {}).get("walls", {}).get("diagonal_length_fraction"),
                "orientation_diversity": (sensors.get("morphology") or {}).get("walls", {}).get("orientation_diversity"),
                "rectangular_sector_fraction": (sensors.get("morphology") or {}).get("sectors", {}).get("rectangular_fraction"),
            },
            "underwater_sectors": sensors["underwater_sectors"],
        },
        "progression": compact,
        "palette": palette_summary(disk),
        "switches": switch_attachment_character(disk),
        "enemies": enemy_placement_character(disk),
        "physical_vs_progress": {
            "physical_reachable_at_rest": compact["physical_reachable_at_rest"],
            "final_reachable": compact["final_reachable"],
            "blocked_or_state_dependent_portals": sensors["spatial"]["blocked_or_state_dependent"],
            "exit_reachable": compact["exit_reachable"],
        },
        "limitations": compact.get("limitations") or [],
    }


def analyze_floor_bands(disk: DiskMap) -> dict[str, Any]:
    """Compact vertical morphology: distinct floor bands and connections between them."""
    from .spatial import analyze_spatial

    build = disk.to_build_ir()
    spatial = analyze_spatial(build)
    floors = sorted({int(sector.fields["floor_z"]) for sector in disk.sectors})
    bands: list[dict[str, Any]] = []
    used: set[int] = set()
    for floor_z in floors:
        if floor_z in used:
            continue
        members = [
            index for index, sector in enumerate(disk.sectors)
            if abs(int(sector.fields["floor_z"]) - floor_z) <= PLAYER_HEIGHT * 0.15
        ]
        for index in members:
            used.add(int(disk.sectors[index].fields["floor_z"]))
        zs = [int(disk.sectors[index].fields["floor_z"]) for index in members]
        median_z = sorted(zs)[len(zs) // 2]
        bands.append({
            "median_floor_z": median_z,
            "sector_count": len(members),
            "delta_from_lowest_player_heights": round((max(floors) - median_z) / PLAYER_HEIGHT, 4),
        })
    bands.sort(key=lambda item: -item["median_floor_z"])
    connections = []
    for edge in spatial["views"]["traversability"]["walkable_at_rest"]:
        delta = abs(int(edge["floor_delta"])) / PLAYER_HEIGHT
        if delta < 0.2:
            continue
        connections.append({
            "floor_delta_player_heights": round(delta, 4),
            "width": edge.get("width"),
            "step_or_jump_may_be_required": edge.get("step_or_jump_may_be_required"),
        })
    vertical = spatial["views"]["vertical"]["relationships"]
    overlooking = [
        {
            "relation": item["relation"],
            "floor_delta_player_heights": round(item["floor_delta"] / PLAYER_HEIGHT, 4),
        }
        for item in vertical
        if item["relation"] in {"above", "below"} and item["floor_delta"] >= PLAYER_HEIGHT * 0.5
    ]
    starts = []
    for index, sprite in enumerate(disk.sprites):
        type_id = int(sprite.fields["type"])
        if type_id not in {1, 2}:
            continue
        sector_id = int(sprite.fields["sector"])
        floor_z = int(disk.sectors[sector_id].fields["floor_z"])
        starts.append({
            "sprite": index,
            "type_id": type_id,
            "delta_from_lowest_player_heights": round((max(floors) - floor_z) / PLAYER_HEIGHT, 4) if floors else 0,
        })
    pickups = []
    for index, sprite in enumerate(disk.sprites):
        typed = classify("sprite", int(sprite.fields["type"]))
        if typed.get("category") not in {"weapon", "ammo", "health", "armor", "powerup", "key", "flag"}:
            continue
        sector_id = int(sprite.fields["sector"])
        floor_z = int(disk.sectors[sector_id].fields["floor_z"])
        pickups.append(round((max(floors) - floor_z) / PLAYER_HEIGHT, 4) if floors else 0)
    return {
        "$schema": "llmapper.vertical-bands",
        "schema_version": 1,
        "kind": "derived",
        "band_count": len(bands),
        "bands": bands,
        "walkable_height_changes": len(connections),
        "median_walkable_delta_player_heights": (
            None if not connections else round(
                sorted(item["floor_delta_player_heights"] for item in connections)[len(connections) // 2], 4
            )
        ),
        "overlooking_xy_overlaps": overlooking[:24],
        "start_elevations": starts,
        "pickup_elevation_median": None if not pickups else round(sorted(pickups)[len(pickups) // 2], 4),
        "vertical_samples": observe_vertical(disk, map_id="local", population="local")[:40],
    }


def retrieve_vertical_in_campaign(
    directory: str | Path,
    *,
    query_delta_min: float = 0.4,
    query_delta_max: float = 3.0,
    population: str = "blood-campaign",
    limit_maps: int = 8,
) -> dict[str, Any]:
    """BB3-style small/medium walkable floor deltas: occurrences in campaign maps."""
    paths = list_original_maps(directory, population=population)
    hits = []
    counterexamples = []
    for path in paths:
        try:
            disk = read_map(path)
            bands = analyze_floor_bands(disk)
        except Exception as exc:
            counterexamples.append({"map": path.name, "error": str(exc)})
            continue
        deltas = [
            item["geometry"]["floor_delta_player_heights"]
            for item in bands.get("vertical_samples") or []
        ]
        in_range = [abs(delta) for delta in deltas if query_delta_min <= abs(delta) <= query_delta_max]
        if len(in_range) >= 2 and bands["band_count"] >= 2:
            if len(hits) < limit_maps:
                hits.append({
                    "map": path.name,
                    "band_count": bands["band_count"],
                    "matching_transitions": len(in_range),
                    "median_matching_delta": round(sorted(in_range)[len(in_range) // 2], 4),
                })
        elif bands["band_count"] <= 1:
            if len(counterexamples) < 12:
                counterexamples.append({"map": path.name, "reason": "single_floor_band"})
    return {
        "$schema": "llmapper.vertical-retrieval",
        "schema_version": 1,
        "kind": "derived",
        "population": population,
        "query": {"delta_min": query_delta_min, "delta_max": query_delta_max},
        "occurrences": hits,
        "counterexamples": counterexamples[:12],
        "status": "supported" if len(hits) >= 3 else "hypothesis",
    }
