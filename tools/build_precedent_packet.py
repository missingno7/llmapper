"""Freeze the bounded precedent packet consulted by the monastery pilot.

Each entry answers one concrete authoring question, keeps exact source
references, and states the abstract lesson separately from the observation.
Generated candidates are never admissible here: this file is evidence about
original Blood maps only.
"""

from __future__ import annotations

import json
from pathlib import Path

from bloodmap.format import read_map
from bloodmap.player_space import player_profile
from bloodmap.spatial import analyze_spatial
from bloodmap.workspace import source_identity

PROFILE = player_profile("blood")
OUT = Path("projects/reasoned-authoring-v1/references/precedent-packet.json")

CONSULTATIONS = [
    {
        "precedent_id": "precedent:open-parent-containing-structure",
        "question": "How does an original map build a large exterior space that contains buildings?",
        "map": "E2M6.MAP",
        "sectors": [208],
        "relationship_consulted": (
            "one exterior sector whose wall loops carve the building masses out of it, "
            "rather than several exterior sectors placed around separate buildings"
        ),
        "lesson": (
            "Model the courtyard as ONE region with holes for each mass. Containment then "
            "exists in the geometry itself instead of only in the author's naming."
        ),
        "implementation": (
            "PlanarLayout.carve_hole for the chapel shell and the garden bed, so the "
            "courtyard region literally surrounds both."
        ),
    },
    {
        "precedent_id": "precedent:release-opening",
        "question": "How wide is the constrained side of an opening that produces strong spatial release?",
        "map": "E2M6.MAP",
        "sectors": [40, 208],
        "relationship_consulted": (
            "a 1.33 player-width opening from a 4.3 player-area pocket into a "
            "6220 player-area exterior"
        ),
        "lesson": (
            "Release comes from the ratio, not from making the opening ornate. A gate barely "
            "wider than the player, opening onto a far larger space, is enough."
        ),
        "implementation": "a 2-unit-wide, 2-player-height gate tunnel opening onto the courtyard",
    },
    {
        "precedent_id": "precedent:stair-run",
        "question": "What step rise, step size, and lighting does an original stair run use?",
        "map": "E2M6.MAP",
        "sectors": [52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63],
        "relationship_consulted": (
            "twelve identical 2.0 player-area steps, each rising exactly 2048 units, with the "
            "floor shade ramping 37 down to 15 along the run"
        ),
        "lesson": (
            "A stair is a shade gradient as much as a geometry ramp: the run gets brighter "
            "toward its destination, which reads as a light source ahead."
        ),
        "implementation": "crypt and gallery stairs use a fixed per-step rise and a monotonic shade ramp",
    },
    {
        "precedent_id": "precedent:dark-low-interior",
        "question": "What scale, shade, and material does a crypt-like interior actually use?",
        "map": "E6M3.MAP",
        "sectors": [68, 75],
        "relationship_consulted": (
            "1.45 to 2.91 player heights clear, 25 to 34 player areas, shade 52 to 56, and the "
            "same tile (1097) on floor, ceiling, and walls"
        ),
        "lesson": (
            "A crypt is defined by being low, small, dark, and MONOMATERIAL. Material variety "
            "would destroy the effect that scale and shade create."
        ),
        "implementation": "crypt hall and niches use tile 1097 on all three surfaces at high shade",
    },
    {
        "precedent_id": "precedent:carved-room-vocabulary",
        "question": "How many wall tiles does a large, heavily carved interior actually use?",
        "map": "E4M4.MAP",
        "sectors": [48],
        "relationship_consulted": (
            "1124 player areas, 13 wall loops, and only three wall tiles in a "
            "114 / 33 / 19 dominant-secondary-trim distribution"
        ),
        "lesson": (
            "A rich room is one dominant fill tile, one secondary, and one rare trim, not a "
            "different tile per surface. Variety comes from geometry and decoration."
        ),
        "implementation": "each pilot assembly gets one fill tile, one secondary, and one accent",
    },
    {
        "precedent_id": "precedent:decorated-large-room",
        "question": "How densely is a large original room actually decorated?",
        "map": "E1M6.MAP",
        "sectors": [391],
        "relationship_consulted": (
            "950 player areas with 39 sprites and six distinct wall tiles, two of which "
            "carry 121 of the 132 walls"
        ),
        "lesson": (
            "Roughly 4 sprites per 100 player areas in an interior focal room; the exterior "
            "precedent (E2M6 sector:208) runs 0.13 per 100. Outdoor space is sparse on purpose."
        ),
        "implementation": "interiors are decorated an order of magnitude more densely than the courtyard",
    },
]

REJECTED = [
    {
        "candidate": "E1M6.MAP sector:439 to sector:391",
        "why_rejected": (
            "the automatic release-opening detector ranked it first, but sector:439 has "
            "0.1 player areas and zero clear height: it is a degenerate closed sector, not a "
            "designed approach pocket"
        ),
        "consequence": "release-opening evidence was taken from E2M6 instead, after inspection",
    },
    {
        "candidate": "E1M6.MAP sector:244",
        "why_rejected": (
            "ranked highly as a decorated room but has tile 0 on every surface, no portals, and "
            "63 stacked type-20 sprites: an authoring scratch sector, not a composed room"
        ),
        "consequence": "decoration density evidence was taken from E1M6 sector:391 instead",
    },
    {
        "candidate": "blood:tile:449 interpreted as stone_masonry",
        "why_rejected": (
            "the mined annotation says stone_masonry, but the rendered tile is gnarled "
            "root or bark; the interpreted facet disagrees with the image"
        ),
        "consequence": "tile 449 is unused by the pilot and the disagreement is an open uncertainty",
    },
]


def _sid(ref):
    return int(str(ref).split(":", 1)[1])


def observe(map_name: str, sector_ids: list[int]) -> list[dict]:
    path = Path("maps/blood") / map_name
    disk = read_map(path)
    level = disk.to_level_ir()
    spatial = analyze_spatial(disk.to_build_ir())
    geo = {_sid(item["ref"]): item for item in spatial["views"]["geometry"]["sectors"]}
    rows = []
    for sid in sector_ids:
        fields = level.sectors[sid]["fields"]
        first, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        wall_tiles: dict[str, int] = {}
        for wall_id in range(first, first + count):
            key = str(int(level.walls[wall_id]["fields"]["picnum"]))
            wall_tiles[key] = wall_tiles.get(key, 0) + 1
        sprites = [
            int(item["fields"]["picnum"]) for item in level.sprites
            if int(item["fields"]["sector"]) == sid
        ]
        rows.append({
            "source_ref": f"{map_name}#sector:{sid}",
            "walls": f"{map_name}#wall:{first}..{first + count - 1}",
            "player_relative": {
                "footprint_player_areas": round(geo[sid]["area"] / PROFILE.body_width ** 2, 2),
                "clear_height_player_heights": round(
                    geo[sid]["clear_height"] / PROFILE.standing_height, 2,
                ),
            },
            "native": {
                "floor_z": geo[sid]["floor_z"], "ceiling_z": geo[sid]["ceiling_z"],
                "wall_loop_count": geo[sid]["wall_loop_count"], "wall_count": count,
                "floor_picnum": int(fields["floor_picnum"]),
                "ceiling_picnum": int(fields["ceiling_picnum"]),
                "floor_shade": int(fields["floor_shade"]),
                "ceiling_shade": int(fields["ceiling_shade"]),
                "ceiling_parallax": bool(int(fields["ceiling_stat"]) & 1),
            },
            "wall_tile_histogram": dict(sorted(wall_tiles.items(), key=lambda kv: -kv[1])),
            "sprite_count": len(sprites),
            "sprite_picnums": sorted(set(sprites)),
        })
    return rows


def main() -> int:
    entries = []
    for item in CONSULTATIONS:
        entries.append({
            "precedent_id": item["precedent_id"],
            "question": item["question"],
            "source": source_identity(Path("maps/blood") / item["map"], game="blood"),
            "observation": observe(item["map"], item["sectors"]),
            "relationship_consulted": item["relationship_consulted"],
            "abstract_lesson": item["lesson"],
            "new_implementation": item["implementation"],
            "reuse_policy": "principles only; no coordinates, vertices, or fragments were copied",
        })
    payload = {
        "$schema": "llmapper.precedent-packet",
        "schema_version": 1,
        "scope": "bounded pilot packet for projects/reasoned-authoring-v1; not a corpus atlas",
        "admissibility": (
            "Only original Blood maps are evidence here. Generated candidates may never "
            "be cited as evidence for original Blood design patterns."
        ),
        "precedents": entries,
        "rejected_candidates": REJECTED,
        "derivation_tool": "tools/mine_precedents.py plus tools/precedent_detail.py plus inspection",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT}: {len(entries)} precedents, {len(REJECTED)} rejected candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
