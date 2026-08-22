"""Propose major areas for a decompiled level, and say why for each merge.

The gap this fills is named in the architecture audit: ``decompile_level``
defines an assembly as a connected component of the portal graph, and a normal
level is one component.  E2M3's main complex is 123 spaces in a flat list, so a
reader who wants "the east wing" has to read all 123.

Areas are a *spatial* grouping, and connectivity alone does not find them.  This
combines what llmapper already measures -- position, elevation, material
vocabulary, sky exposure, bottlenecks -- with one thing only the renderer knows,
which is whether two spaces are actually seen together.

The output is a proposal, not a taxonomy.  Every merge carries the reasons that
justified it, the strongest rejected merges are kept, and a second grouping at a
different threshold is kept beside the first so a reader can disagree with
evidence rather than with an assertion.

.. code-block:: bash

    python -m tools.propose_areas maps/blood/E2M3.MAP \\
        --hierarchy projects/e2m3-decompiled/hierarchy.json \\
        --packet work/obs-e2m3/packet.json \\
        -o projects/e2m3-decompiled/references/area-proposals.json
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from bloodmap.format import read_map
from bloodmap.model import LevelIR
from bloodmap.player_space import player_profile
from bloodmap.reachability import analyze_reachability, classify_offmap

SCHEMA = "llmapper.area-proposals"
SCHEMA_VERSION = 1

#: How much each signal is worth in a pairwise affinity.  Flat and visible on
#: purpose: a tuned weight vector nobody can read would make the proposals
#: harder to argue with, not better.
WEIGHTS = {
    "mutual_covisibility": 2.0,
    "one_way_covisibility": 1.0,
    "same_sky_class": 1.5,
    "same_elevation_band": 1.5,
    "shared_materials": 1.5,
    "proximity": 1.0,
    "wide_opening": 1.0,
}
MAX_SCORE = sum(WEIGHTS.values()) - WEIGHTS["one_way_covisibility"]


def _sector_facts(level: LevelIR, profile: str) -> dict[int, dict[str, Any]]:
    unit = player_profile(profile).body_width
    facts: dict[int, dict[str, Any]] = {}
    for sector in level.sectors:
        fields = sector["fields"]
        start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        xs: list[int] = []
        ys: list[int] = []
        for index in range(start, min(start + count, len(level.walls))):
            wall = level.walls[index]["fields"]
            xs.append(int(wall["x"]))
            ys.append(int(wall["y"]))
        if not xs:
            continue
        facts[int(sector["id"])] = {
            "centroid": (sum(xs) / len(xs) / unit, sum(ys) / len(ys) / unit),
            "floor_z": int(fields["floor_z"]),
            "sky": bool(int(fields["ceiling_stat"]) & 1),
            "wall_tiles": [],
            "floor_tile": int(fields["floor_picnum"]),
            "ceiling_tile": int(fields["ceiling_picnum"]),
        }
        for index in range(start, min(start + count, len(level.walls))):
            facts[int(sector["id"])]["wall_tiles"].append(
                int(level.walls[index]["fields"]["picnum"])
            )
    return facts


def _portal_graph(level: LevelIR) -> dict[int, dict[int, float]]:
    """Sector adjacency, valued by the total width of shared openings."""
    graph: dict[int, dict[int, float]] = defaultdict(dict)
    for sector in level.sectors:
        fields = sector["fields"]
        sector_id = int(sector["id"])
        start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        for index in range(start, min(start + count, len(level.walls))):
            wall = level.walls[index]["fields"]
            neighbour = int(wall["next_sector"])
            if neighbour < 0:
                continue
            point2 = int(wall["point2"])
            if not 0 <= point2 < len(level.walls):
                continue
            other = level.walls[point2]["fields"]
            width = math.hypot(int(other["x"]) - int(wall["x"]),
                               int(other["y"]) - int(wall["y"]))
            graph[sector_id][neighbour] = graph[sector_id].get(neighbour, 0.0) + width
    return graph


def _jaccard(left: Iterable[int], right: Iterable[int]) -> float:
    a, b = set(left), set(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class AreaProposer:
    def __init__(self, level: LevelIR, hierarchy: Mapping[str, Any],
                 packet: Mapping[str, Any] | None, *, profile: str = "blood",
                 playable: Iterable[int] | None = None) -> None:
        self.level = level
        self.profile = profile
        self.unit = player_profile(profile).body_width
        self.stand = player_profile(profile).standing_height
        self.facts = _sector_facts(level, profile)
        self.graph = _portal_graph(level)
        self.nodes = {node["id"]: node for node in hierarchy.get("nodes", [])}
        # An area is a place a player goes.  A switch closet and an author's
        # signature are neither, and grouping them with the rooms they sit
        # beside is how a proposal ends up with a "zone" made of letters.
        self.playable = None if playable is None else set(playable)
        self.excluded: dict[str, list[int]] = {}
        self.spaces = {}
        for node_id, node in self.nodes.items():
            if node.get("kind") != "space" or not node.get("sectors"):
                continue
            sectors = [int(s) for s in node["sectors"]]
            if self.playable is not None:
                kept = [s for s in sectors if s in self.playable]
                if not kept:
                    self.excluded[node_id] = sectors
                    continue
                if len(kept) != len(sectors):
                    node = dict(node)
                    node["sectors"] = kept
            self.spaces[node_id] = node
        self.covisible = self._covisibility(packet)

    def _covisibility(self, packet: Mapping[str, Any] | None) -> dict[tuple[str, str], dict[str, int]]:
        result: dict[tuple[str, str], dict[str, int]] = {}
        if not packet:
            return result
        for pair in packet.get("covisibility", {}).get("pairs", []):
            left, right = pair["nodes"]
            result[(left, right)] = {"forward": pair["forward"], "back": pair["back"],
                                     "mutual": bool(pair["mutual"])}
            result[(right, left)] = result[(left, right)]
        return result

    # -- per-space summaries ------------------------------------------------
    def space_facts(self, space_id: str) -> dict[str, Any]:
        sectors = [s for s in self.spaces[space_id]["sectors"] if s in self.facts]
        if not sectors:
            return {}
        centroids = [self.facts[s]["centroid"] for s in sectors]
        floors = sorted(self.facts[s]["floor_z"] for s in sectors)
        wall_tiles: list[int] = []
        for s in sectors:
            wall_tiles.extend(self.facts[s]["wall_tiles"])
        counts: dict[int, int] = defaultdict(int)
        for tile in wall_tiles:
            counts[tile] += 1
        for s in sectors:
            counts[self.facts[s]["floor_tile"]] += 2
        dominant = [tile for tile, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:5]]
        return {
            "sectors": sectors,
            "centroid": (sum(c[0] for c in centroids) / len(centroids),
                         sum(c[1] for c in centroids) / len(centroids)),
            "median_floor_z": floors[len(floors) // 2],
            "sky_fraction": sum(1 for s in sectors if self.facts[s]["sky"]) / len(sectors),
            "dominant_tiles": dominant,
        }

    # -- affinity -----------------------------------------------------------
    def affinity(self, left: Mapping[str, Any], right: Mapping[str, Any],
                 left_ids: Sequence[str], right_ids: Sequence[str]) -> tuple[float, list[str]]:
        reasons: list[str] = []
        score = 0.0

        best = None
        for a in left_ids:
            for b in right_ids:
                record = self.covisible.get((a, b))
                if record and (best is None or record["forward"] + record["back"] >
                               best["forward"] + best["back"]):
                    best = record
        if best and best["mutual"]:
            score += WEIGHTS["mutual_covisibility"]
            reasons.append("each is visible from a representative view of the other")
        elif best:
            score += WEIGHTS["one_way_covisibility"]
            reasons.append("one is visible from a representative view of the other")

        if abs(left["sky_fraction"] - right["sky_fraction"]) < 0.5:
            score += WEIGHTS["same_sky_class"]
            reasons.append("both are %s" % ("open to the sky" if left["sky_fraction"] >= 0.5
                                            else "enclosed"))

        drop = abs(left["median_floor_z"] - right["median_floor_z"]) / self.stand
        if drop <= 2.0:
            score += WEIGHTS["same_elevation_band"]
            reasons.append("median floors within %.1f player heights" % drop)

        overlap = _jaccard(left["dominant_tiles"], right["dominant_tiles"])
        if overlap > 0:
            score += WEIGHTS["shared_materials"] * overlap
            reasons.append("dominant surfaces overlap %.0f%%" % (100 * overlap))

        distance = math.hypot(left["centroid"][0] - right["centroid"][0],
                              left["centroid"][1] - right["centroid"][1])
        if distance <= 16.0:
            score += WEIGHTS["proximity"] * (1.0 - distance / 16.0)
            reasons.append("centres %.1f player widths apart" % distance)

        width = self.opening_width(left["sectors"], right["sectors"])
        if width > 0:
            wide = min(1.0, width / (4 * self.unit))
            score += WEIGHTS["wide_opening"] * wide
            reasons.append("openings between them total %.1f player widths"
                           % (width / self.unit))
        return score / MAX_SCORE, reasons

    def opening_width(self, left: Sequence[int], right: Sequence[int]) -> float:
        total = 0.0
        right_set = set(right)
        for sector_id in left:
            for other, width in self.graph.get(sector_id, {}).items():
                if other in right_set:
                    total += width
        return total

    # -- clustering ---------------------------------------------------------
    def cluster(self, space_ids: Sequence[str], *, target: int, floor_score: float,
                size_cap: float) -> dict[str, Any]:
        """Greedy agglomeration over the portal graph, recording every merge."""
        members = {space_id: [space_id] for space_id in space_ids}
        facts = {space_id: self.space_facts(space_id) for space_id in space_ids}
        summaries = {space_id: dict(facts[space_id]) for space_id in space_ids}
        total_sectors = sum(len(facts[s]["sectors"]) for s in space_ids)
        cap = max(2, int(total_sectors * size_cap))
        merges: list[dict[str, Any]] = []

        def adjacent(a: str, b: str) -> bool:
            return self.opening_width(summaries[a]["sectors"], summaries[b]["sectors"]) > 0

        while len(members) > target:
            best: tuple[float, str, str, list[str]] | None = None
            keys = sorted(members)
            for i, a in enumerate(keys):
                for b in keys[i + 1:]:
                    if not adjacent(a, b):
                        continue
                    if len(summaries[a]["sectors"]) + len(summaries[b]["sectors"]) > cap:
                        continue
                    score, reasons = self.affinity(summaries[a], summaries[b],
                                                   members[a], members[b])
                    if best is None or score > best[0]:
                        best = (score, a, b, reasons)
            if best is None or best[0] < floor_score:
                break
            score, a, b, reasons = best
            merges.append({
                "into": a, "absorbed": b, "score": round(score, 3), "reasons": reasons,
                "sectors_after": len(summaries[a]["sectors"]) + len(summaries[b]["sectors"]),
            })
            members[a] = members[a] + members[b]
            summaries[a] = self._merge_summary(summaries[a], summaries[b])
            del members[b]
            del summaries[b]

        rejected: list[dict[str, Any]] = []
        keys = sorted(members)
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                if not adjacent(a, b):
                    continue
                score, reasons = self.affinity(summaries[a], summaries[b],
                                               members[a], members[b])
                rejected.append({"left": a, "right": b, "score": round(score, 3),
                                 "reasons": reasons})
        rejected.sort(key=lambda item: -item["score"])

        areas = []
        for key in sorted(members, key=lambda k: -len(summaries[k]["sectors"])):
            summary = summaries[key]
            areas.append({
                "seed": key,
                "spaces": sorted(members[key]),
                "sectors": sorted(summary["sectors"]),
                "sector_count": len(summary["sectors"]),
                "median_floor_z": summary["median_floor_z"],
                "sky_fraction": round(summary["sky_fraction"], 3),
                "dominant_tiles": summary["dominant_tiles"],
                "centroid_player_widths": [round(v, 1) for v in summary["centroid"]],
            })
        return {
            "target": target, "floor_score": floor_score, "size_cap": size_cap,
            "areas": areas,
            "merges": merges,
            "strongest_rejected": rejected[:8],
        }

    def _merge_summary(self, left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
        sectors = list(left["sectors"]) + list(right["sectors"])
        weight_l = len(left["sectors"])
        weight_r = len(right["sectors"])
        total = weight_l + weight_r
        floors = sorted(self.facts[s]["floor_z"] for s in sectors if s in self.facts)
        counts: dict[int, int] = defaultdict(int)
        for tile in list(left["dominant_tiles"]) + list(right["dominant_tiles"]):
            counts[tile] += 1
        return {
            "sectors": sectors,
            "centroid": (
                (left["centroid"][0] * weight_l + right["centroid"][0] * weight_r) / total,
                (left["centroid"][1] * weight_l + right["centroid"][1] * weight_r) / total,
            ),
            "median_floor_z": floors[len(floors) // 2] if floors else left["median_floor_z"],
            "sky_fraction": (left["sky_fraction"] * weight_l
                             + right["sky_fraction"] * weight_r) / total,
            "dominant_tiles": [t for t, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:5]],
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map")
    parser.add_argument("--hierarchy", required=True)
    parser.add_argument("--packet", default=None,
                        help="a visual observation packet; without it co-visibility "
                             "contributes nothing and the proposal says so")
    parser.add_argument("-o", "--out", required=True)
    parser.add_argument("--target", type=int, default=10,
                        help="how many areas to aim for inside the largest assembly")
    parser.add_argument("--floor-score", type=float, default=0.35)
    parser.add_argument("--size-cap", type=float, default=0.30)
    parser.add_argument("--include-offmap", action="store_true",
                        help="group the switch closets and signatures too, which is "
                             "almost never what you want")
    args = parser.parse_args(argv)

    disk = read_map(args.map)
    level = disk.to_level_ir()
    hierarchy = json.loads(Path(args.hierarchy).read_text(encoding="utf-8"))
    packet = None
    if args.packet:
        packet = json.loads(Path(args.packet).read_text(encoding="utf-8"))

    offmap = None if args.include_offmap else classify_offmap(disk)
    playable = None
    if offmap is not None:
        playable = set(analyze_reachability(disk).reached)
    proposer = AreaProposer(level, hierarchy, packet, playable=playable)
    by_assembly: dict[str, list[str]] = defaultdict(list)
    for space_id, node in proposer.spaces.items():
        by_assembly[str(node.get("parent"))].append(space_id)

    assemblies: list[dict[str, Any]] = []
    for assembly_id in sorted(by_assembly, key=lambda k: -len(by_assembly[k])):
        space_ids = sorted(by_assembly[assembly_id])
        if len(space_ids) <= max(2, args.target // 2):
            assemblies.append({
                "assembly": assembly_id,
                "spaces": len(space_ids),
                "grouped": False,
                "reason": "already small enough to read as a list",
            })
            continue
        target = args.target if len(space_ids) > args.target * 2 else max(2, len(space_ids) // 3)
        primary = proposer.cluster(space_ids, target=target,
                                   floor_score=args.floor_score, size_cap=args.size_cap)
        alternative = proposer.cluster(space_ids, target=max(3, target // 2),
                                       floor_score=args.floor_score * 0.8,
                                       size_cap=min(0.5, args.size_cap * 1.6))
        assemblies.append({
            "assembly": assembly_id,
            "spaces": len(space_ids),
            "grouped": True,
            "primary": primary,
            "alternative": alternative,
        })

    document = {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "of": Path(args.map).name,
        "hierarchy": str(args.hierarchy).replace("\\", "/"),
        "packet": str(args.packet).replace("\\", "/") if args.packet else None,
        "weights": WEIGHTS,
        "offmap": None if offmap is None else {
            "counts": offmap["counts"],
            "sectors_by_kind": offmap["sectors_by_kind"],
            "excluded_spaces": {k: v for k, v in sorted(proposer.excluded.items())},
        },
        "assemblies": assemblies,
        "limitations": [
            "a proposal, not a taxonomy: the merges are evidence for a reader to accept or reject",
            "greedy agglomeration, so an early merge is never revisited",
            "co-visibility comes from a handful of planned poses per space"
            if packet else "no visual packet was supplied, so co-visibility contributed nothing",
            "no name is invented here; areas are identified by their seed space",
            "geometry the player cannot reach is excluded by default: switch "
            "closets and author signatures are not places",
        ],
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({
        "assemblies": [
            {"assembly": item["assembly"], "spaces": item["spaces"],
             "areas": len(item["primary"]["areas"]) if item.get("grouped") else item["spaces"]}
            for item in assemblies
        ],
        "out": str(out),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
