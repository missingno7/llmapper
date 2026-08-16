"""Compile Blood ontology v1/v2 review artifacts from the offline discovery pass.

This is the inspectable review document, not an LLM runtime. Import with
`python -m bloodmap materials-import`.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent

REJECTED = [
    {
        "id": "single_primary_class",
        "reason": "A tile can be stone and still be a sky sheet, or metal and still be a masked separator. One class hides the useful split.",
    },
    {
        "id": "visual_theme",
        "reason": "Gothic/industrial labels did not predict wall vs floor vs sky better than placement shares already do.",
    },
    {
        "id": "is_door",
        "reason": "Almost no sampled wall is both a complete authored door face and moving-sector-associated. Tile 104, used as a scratch door in construction defaults, has only 2 corpus placements.",
    },
    {
        "id": "indoor_outdoor",
        "reason": "Sky/parallax is a ceiling rendering/placement fact. Indoor/outdoor is not independently evidenced by ART usage.",
    },
    {
        "id": "damage_progression",
        "reason": "The stratified sample contained no verified damage-state tile runs. Native picanm families were liquid, wall, floor, or sprite loops, not wreckage sequences.",
    },
]

FACETS_V1 = [
    {
        "id": "placement_kind",
        "label": "placement kind",
        "values": ["surface", "sprite", "marker", "unknown"],
        "basis": "Sprite-only tiles (2520/2521) never appear on walls/floors; surface tiles almost never appear only as sprites.",
        "useful_for": ["authoring", "retrieval", "conversion"],
    },
    {
        "id": "surface_applicability",
        "label": "surface applicability",
        "values": ["vertical", "horizontal_floor", "horizontal_ceiling", "sky_parallax", "mixed", "none", "unknown"],
        "basis": "Tile 2500/3491/3678 are 64x400 and ceiling-only; 270/44 are floor-dominant; 110/5/80 are wall-dominant; 90/281 mix wall+floor.",
        "useful_for": ["usage_prediction", "conversion", "authoring"],
    },
    {
        "id": "rendering_behavior",
        "label": "rendering behavior",
        "values": ["opaque", "masked", "translucent", "unknown"],
        "basis": "Tile 330 is 560/560 masked overwalls; 1067 is often translucent hanging overlay. Opaque fill tiles have ~0 masked share.",
        "useful_for": ["replacement", "authoring", "retrieval"],
    },
    {
        "id": "architectural_role",
        "label": "architectural role",
        "values": [
            "structural_fill", "masked_separator", "hanging_overlay", "narrow_strip",
            "sky_sheet", "control_face", "marker", "placeholder", "unknown",
        ],
        "basis": "Function split independently of stone/metal names: 330 fence separator, 1067 cobweb overlay, 195/93 thin strips, 2500 sky sheet, 1070 32x32 mechanism sprite, tile 0 default/placeholder.",
        "useful_for": ["authoring", "family_grouping", "retrieval"],
    },
    {
        "id": "interaction_role",
        "label": "interaction role",
        "values": ["static", "mechanism_associated", "animated_surface", "interactive_control", "marker", "unknown"],
        "basis": "Native picanm families 1029-1036 and 1100-1104 are animated surfaces. 1070 is sprite+mechanism on 28 maps. High moving_sector on adjacent walls is not enough to call a tile a door.",
        "useful_for": ["authoring", "family_grouping"],
    },
    {
        "id": "scale_behavior",
        "label": "scale behavior",
        "values": ["repeating_fill", "discrete_instance", "narrow_repeat", "unknown"],
        "basis": "Player-relative coverage: 110 tiles many times; 330/195 have tiny player_widths_per_repeat; 1067 sprite x-repeat is a discrete overlay instance.",
        "useful_for": ["authoring", "replacement"],
    },
    {
        "id": "visual_material",
        "label": "visual material",
        "values": ["stone_masonry", "brick", "metal", "organic_earth", "liquid", "unknown"],
        "basis": "Useful for palette mood only. Does not predict placement: stone-looking 110 is a wall, stone-looking 2500 is sky, brown-noise 270 is a floor.",
        "useful_for": ["retrieval"],
    },
]

FACETS_V2 = deepcopy(FACETS_V1)
for facet in FACETS_V2:
    if facet["id"] == "architectural_role":
        facet["values"] = [
            "structural_fill", "complete_wall_band", "masked_separator", "hanging_overlay",
            "narrow_strip", "sky_sheet", "control_face", "marker", "placeholder", "unknown",
        ]
        facet["basis"] = (
            facet["basis"]
            + " Tile 80 is a 100% wall treatment with header/footer; collapsing it into structural_fill hid that distinction from 110."
        )


def _a(asset: str, status: str, values: dict[str, str], basis: str, *, confidence: float = 0.8, supporting: list[str] | None = None) -> dict:
    return {
        "asset": asset,
        "status": status,
        "provenance": "INTERPRETED",
        "confidence": confidence,
        "basis": basis,
        "supporting": supporting or [],
        "values": values,
    }


def _vals(**kwargs: str) -> dict[str, str]:
    return kwargs


def v2_annotations() -> list[dict]:
    wall_stone = _vals(
        placement_kind="surface", surface_applicability="vertical", rendering_behavior="opaque",
        architectural_role="structural_fill", interaction_role="static",
        scale_behavior="repeating_fill", visual_material="stone_masonry",
    )
    wall_brick = dict(wall_stone, visual_material="brick")
    wall_unknown = dict(wall_stone, visual_material="unknown")
    floor_earth = _vals(
        placement_kind="surface", surface_applicability="horizontal_floor", rendering_behavior="opaque",
        architectural_role="structural_fill", interaction_role="static",
        scale_behavior="repeating_fill", visual_material="organic_earth",
    )
    floor_stone = dict(floor_earth, visual_material="stone_masonry")
    ceil_fill = _vals(
        placement_kind="surface", surface_applicability="horizontal_ceiling", rendering_behavior="opaque",
        architectural_role="structural_fill", interaction_role="static",
        scale_behavior="repeating_fill", visual_material="unknown",
    )
    sky = _vals(
        placement_kind="surface", surface_applicability="sky_parallax", rendering_behavior="opaque",
        architectural_role="sky_sheet", interaction_role="static",
        scale_behavior="repeating_fill", visual_material="stone_masonry",
    )
    mixed = _vals(
        placement_kind="surface", surface_applicability="mixed", rendering_behavior="opaque",
        architectural_role="unknown", interaction_role="static",
        scale_behavior="repeating_fill", visual_material="unknown",
    )
    unused = _vals(
        placement_kind="unknown", surface_applicability="unknown", rendering_behavior="unknown",
        architectural_role="unknown", interaction_role="unknown",
        scale_behavior="unknown", visual_material="unknown",
    )
    sprite_actor = _vals(
        placement_kind="sprite", surface_applicability="none", rendering_behavior="unknown",
        architectural_role="unknown", interaction_role="mechanism_associated",
        scale_behavior="discrete_instance", visual_material="unknown",
    )
    notes = [
        _a("blood:tile:110", "annotated", wall_stone, "86% wall / 6613 uses / 23 maps; tileable irregular stone; rarely_tiled false.", supporting=["E1M1.MAP", "preview", "neighbors:330"]),
        _a("blood:tile:449", "annotated", wall_stone, "87% wall / 4971 uses; opaque repeating fill."),
        _a("blood:tile:5", "annotated", wall_brick, "98% wall / 4562 uses; running-bond brick 64x128."),
        _a("blood:tile:80", "annotated", dict(wall_stone, architectural_role="complete_wall_band"), "100% wall / 4054 uses; header/footer band. Not a floor/sky candidate.", supporting=["preview"]),
        _a("blood:tile:20", "annotated", wall_unknown, "74% wall / 3730 uses; remaining share is floor/ceiling, still wall-dominant."),
        _a("blood:tile:91", "annotated", wall_stone, "100% wall / 3132 uses."),
        _a("blood:tile:194", "annotated", wall_brick, "99% wall / 2658 uses; 32% mechanism-associated but still a repeating wall fill, not a proven door face."),
        _a("blood:tile:2499", "annotated", wall_stone, "97% wall / 2639 uses; 64x256 tall repeating wall."),
        _a("blood:tile:1011", "annotated", wall_stone, "98% wall / 2152 uses."),
        _a("blood:tile:427", "annotated", wall_stone, "97% wall / 1761 uses."),
        _a("blood:tile:109", "annotated", wall_stone, "100% wall / 1735 uses; co-occurs with fence 330."),
        _a("blood:tile:28", "annotated", wall_unknown, "99% wall / 1547 uses."),
        _a("blood:tile:492", "annotated", wall_unknown, "95% wall / 1484 uses."),
        _a("blood:tile:67", "annotated", wall_unknown, "71% wall / 1462 uses; wall-dominant, not mixed by the 0.2/0.2 test."),
        _a("blood:tile:230", "annotated", wall_stone, "89% wall / 1393 uses."),
        _a("blood:tile:406", "annotated", wall_unknown, "100% wall / 1327 uses."),
        _a("blood:tile:84", "annotated", wall_unknown, "100% wall / 1297 uses."),
        _a("blood:tile:414", "annotated", wall_stone, "95% wall / 1255 uses."),
        _a("blood:tile:411", "annotated", wall_stone, "97% wall / 1205 uses."),
        _a("blood:tile:130", "annotated", wall_stone, "99% wall / 1149 uses."),
        _a("blood:tile:385", "annotated", wall_brick, "93% wall / 1125 uses. Isolated brick preview is a wall; construction default ceiling 385 is role-confused.", supporting=["preview"]),
        _a("blood:tile:567", "annotated", wall_unknown, "94% wall / 1081 uses."),
        _a("blood:tile:369", "annotated", wall_brick, "99% wall / 1041 uses."),
        _a("blood:tile:2491", "annotated", wall_stone, "100% wall / 1010 uses; neighbor of fence 330."),
        _a("blood:tile:123", "annotated", wall_unknown, "100% wall / 1002 uses."),
        _a("blood:tile:452", "annotated", wall_unknown, "82% wall / 983 uses."),
        _a("blood:tile:421", "annotated", wall_stone, "95% wall / 957 uses."),
        _a("blood:tile:108", "annotated", wall_stone, "100% wall / 897 uses."),
        _a("blood:tile:180", "annotated", wall_unknown, "97% wall / 335 uses / 7 maps. Scratch-room default wall; corpus-backed but not the highest-usage stone fill."),
        _a("blood:tile:181", "annotated", wall_unknown, "98% wall / 549 uses."),
        _a("blood:tile:556", "annotated", wall_unknown, "94% wall / 2455 uses; 27% mechanism-associated, still a repeating fill."),
        _a("blood:tile:2490", "annotated", dict(wall_stone, interaction_role="mechanism_associated"), "96% wall / 1880 uses; 47% mechanism / 46% moving. Not labeled door: no complete door-face evidence."),
        _a("blood:tile:255", "mixed_use", mixed, "56/14/30 wall/floor/ceiling. Do not pick a single surface.", confidence=0.55),
        _a("blood:tile:90", "mixed_use", mixed, "60/27/13 wall/floor/ceiling across 2557 uses.", confidence=0.6),
        _a("blood:tile:281", "mixed_use", mixed, "60/30/9 wall/floor/ceiling.", confidence=0.6),
        _a("blood:tile:21", "mixed_use", mixed, "64/16/20 wall/floor/ceiling.", confidence=0.55),
        _a("blood:tile:379", "mixed_use", mixed, "44/12/44 wall/floor/ceiling.", confidence=0.5),
        _a("blood:tile:273", "mixed_use", mixed, "53/19/27 wall/floor/ceiling.", confidence=0.5),
        _a("blood:tile:512", "mixed_use", mixed, "59/10/32 wall/floor/ceiling.", confidence=0.5),
        _a("blood:tile:491", "mixed_use", mixed, "22/48/29 wall/floor/ceiling; floor-leaning mixed.", confidence=0.5),
        _a("blood:tile:253", "mixed_use", mixed, "49/32/20 wall/floor/ceiling. E1M1 local palette member.", confidence=0.55),
        _a("blood:tile:529", "mixed_use", mixed, "35/62/3 wall/floor/ceiling; tall-as-floor ambiguous bucket.", confidence=0.45),
        _a("blood:tile:456", "mixed_use", dict(mixed, surface_applicability="mixed"), "23% wall / 74% ceiling. Ceiling-leaning mixed.", confidence=0.55),
        _a("blood:tile:68", "mixed_use", dict(mixed, architectural_role="narrow_strip", scale_behavior="narrow_repeat"), "64x16 strip used as wall/floor/ceiling (64/10/17). Not a clean trim class.", confidence=0.45),
        _a("blood:tile:330", "annotated", _vals(placement_kind="surface", surface_applicability="vertical", rendering_behavior="masked", architectural_role="masked_separator", interaction_role="static", scale_behavior="narrow_repeat", visual_material="metal"), "100% overwall, 100% masked, 560 uses / 5 maps. Isolated preview is a wrought-iron fence. 0.03 player widths/repeat.", supporting=["preview", "neighbors:110,109"]),
        _a("blood:tile:331", "annotated", _vals(placement_kind="surface", surface_applicability="vertical", rendering_behavior="masked", architectural_role="masked_separator", interaction_role="static", scale_behavior="narrow_repeat", visual_material="metal"), "100% masked overwall; 32x128 fence variant of 330."),
        _a("blood:tile:463", "annotated", _vals(placement_kind="surface", surface_applicability="vertical", rendering_behavior="masked", architectural_role="masked_separator", interaction_role="static", scale_behavior="narrow_repeat", visual_material="unknown"), "100% masked overwall / 62 uses."),
        _a("blood:tile:266", "annotated", _vals(placement_kind="surface", surface_applicability="vertical", rendering_behavior="masked", architectural_role="masked_separator", interaction_role="mechanism_associated", scale_behavior="repeating_fill", visual_material="unknown"), "94% masked / 55% mechanism / 22 maps. Grate-like separator, not a generic wall."),
        _a("blood:tile:319", "annotated", _vals(placement_kind="surface", surface_applicability="vertical", rendering_behavior="masked", architectural_role="hanging_overlay", interaction_role="static", scale_behavior="discrete_instance", visual_material="unknown"), "78x44 100% masked overwall emblem. Co-occurs with 2448 floor and 2500 sky, not a repeating fence."),
        _a("blood:tile:1067", "annotated", _vals(placement_kind="surface", surface_applicability="vertical", rendering_behavior="translucent", architectural_role="hanging_overlay", interaction_role="static", scale_behavior="discrete_instance", visual_material="unknown"), "Cobweb overlay; 47% masked + 53% sprite; rarely_tiled_horizontally true.", supporting=["preview"]),
        _a("blood:tile:2342", "annotated", _vals(placement_kind="surface", surface_applicability="vertical", rendering_behavior="unknown", architectural_role="unknown", interaction_role="mechanism_associated", scale_behavior="repeating_fill", visual_material="unknown"), "100% wall but 46% masked / 67% mechanism. Ambiguous rendering; not structural_fill.", confidence=0.4),
        _a("blood:tile:502", "annotated", _vals(placement_kind="surface", surface_applicability="vertical", rendering_behavior="masked", architectural_role="hanging_overlay", interaction_role="static", scale_behavior="unknown", visual_material="unknown"), "55% overwall masked + 45% sprite; low count.", confidence=0.45),
        _a("blood:tile:58", "annotated", _vals(placement_kind="surface", surface_applicability="vertical", rendering_behavior="masked", architectural_role="hanging_overlay", interaction_role="static", scale_behavior="unknown", visual_material="unknown"), "72% masked overwall + 28% sprite.", confidence=0.45),
        _a("blood:tile:2521", "annotated", _vals(placement_kind="marker", surface_applicability="none", rendering_behavior="unknown", architectural_role="marker", interaction_role="marker", scale_behavior="discrete_instance", visual_material="unknown"), "ASOUND editor text; 100% sprite / 100% mechanism / 41 maps. Isolated preview looks like signage, context is a marker.", supporting=["preview"]),
        _a("blood:tile:2520", "annotated", _vals(placement_kind="marker", surface_applicability="none", rendering_behavior="unknown", architectural_role="marker", interaction_role="marker", scale_behavior="discrete_instance", visual_material="unknown"), "Same 8x49 marker family as 2521; 1250 sprite uses."),
        _a("blood:tile:2519", "annotated", _vals(placement_kind="marker", surface_applicability="none", rendering_behavior="unknown", architectural_role="marker", interaction_role="marker", scale_behavior="discrete_instance", visual_material="unknown"), "8x41 sprite-only marker."),
        _a("blood:tile:908", "annotated", sprite_actor, "42x80 sprite-only / 1102 uses / 100% mechanism. Not a surface material."),
        _a("blood:tile:3997", "annotated", sprite_actor, "Sprite-only / 1096 uses; no ART size in catalog."),
        _a("blood:tile:2825", "annotated", sprite_actor, "Shotgun-cultist-sized sprite; 885 uses. Actor, not a wall."),
        _a("blood:tile:2820", "annotated", sprite_actor, "Tommy-cultist-sized sprite; 692 uses."),
        _a("blood:tile:1170", "annotated", sprite_actor, "58x125 sprite-only / 691 uses."),
        _a("blood:tile:2169", "annotated", dict(sprite_actor, interaction_role="animated_surface"), "Native anim 2169-2172; sprite pickup/actor frames, not a wall family."),
        _a("blood:tile:506", "annotated", dict(sprite_actor, interaction_role="animated_surface"), "Native anim 506-509; sprite-only."),
        _a("blood:tile:660", "annotated", dict(sprite_actor, interaction_role="animated_surface"), "Native anim 660-663; sprite-only."),
        _a("blood:tile:938", "annotated", dict(sprite_actor, interaction_role="animated_surface"), "Native anim 938-941; 100% mechanism sprites."),
        _a("blood:tile:2101", "annotated", dict(sprite_actor, interaction_role="animated_surface"), "Native anim 2101-2114; sprite-only, 0% mechanism."),
        _a("blood:tile:1070", "annotated", _vals(placement_kind="sprite", surface_applicability="none", rendering_behavior="opaque", architectural_role="control_face", interaction_role="interactive_control", scale_behavior="discrete_instance", visual_material="unknown"), "32x32; 283 uses / 28 maps; 0 wall/floor/ceiling; 100% mechanism. Blood switch sprite. No native picanm; do not invent extra states.", supporting=["designs.py type 21"]),
        _a("blood:tile:318", "annotated", _vals(placement_kind="marker", surface_applicability="none", rendering_behavior="unknown", architectural_role="marker", interaction_role="marker", scale_behavior="discrete_instance", visual_material="unknown"), "78x44; 46 uses / 42 maps (~1/map); 100% sprite+mechanism. Exit/marker, not the 319 overlay."),
        _a("blood:tile:1100", "annotated", dict(wall_unknown, interaction_role="animated_surface"), "Native anim 1100-1104; 100% wall / 346 uses. Animated wall run, not per-frame materials."),
        _a("blood:tile:1030", "annotated", _vals(placement_kind="surface", surface_applicability="horizontal_ceiling", rendering_behavior="opaque", architectural_role="unknown", interaction_role="animated_surface", scale_behavior="repeating_fill", visual_material="liquid"), "99% ceiling / 213 uses; native family 1029-1036. Liquid animated ceiling, not a generic indoor fill. Later frames are mostly appearance_only because the engine plays them from the first tile.", supporting=["anim:1029-1036", "cooccur:1120"]),
        _a("blood:tile:1029", "mixed_use", dict(mixed, interaction_role="animated_surface", visual_material="liquid"), "First frame of the 1029-1036 liquid run; mixed surface use / 51 placements.", confidence=0.5),
        _a("blood:tile:1120", "mixed_use", dict(mixed, interaction_role="animated_surface", visual_material="liquid"), "Native anim 1120-1126; 75% floor / 21% ceiling; 105 pairings with 1030. Liquid floor/ceiling family, not a wall.", supporting=["anim:1120-1126"]),
        _a("blood:tile:2915", "mixed_use", dict(mixed, interaction_role="animated_surface"), "Native anim 2915-2924; 38% floor / 27% ceiling / 34% sprite. Water-like mixed family.", confidence=0.45),
        _a("blood:tile:997", "mixed_use", dict(mixed, interaction_role="animated_surface"), "First frame of 997-1003; 53 mixed uses. Later frames 998-1003 have zero map placements.", confidence=0.4),
        _a("blood:tile:0", "annotated", _vals(placement_kind="marker", surface_applicability="none", rendering_behavior="unknown", architectural_role="placeholder", interaction_role="unknown", scale_behavior="unknown", visual_material="unknown"), "2633 uses on every map, 0 walls, mixed sprite/floor/ceiling. Isolated preview looks like masonry; it is the default/empty picnum, not a material.", supporting=["preview"]),
        _a("blood:tile:200", "annotated", _vals(placement_kind="surface", surface_applicability="vertical", rendering_behavior="opaque", architectural_role="narrow_strip", interaction_role="mechanism_associated", scale_behavior="narrow_repeat", visual_material="metal"), "32x16 riveted plate; 85% wall / 40% mechanism. Small panel, not a switch and not a door face."),
        _a("blood:tile:195", "annotated", _vals(placement_kind="surface", surface_applicability="vertical", rendering_behavior="opaque", architectural_role="narrow_strip", interaction_role="mechanism_associated", scale_behavior="narrow_repeat", visual_material="unknown"), "16x128; xrepeat 1; 0.005 player widths/repeat; 62% mechanism / 52% moving. Door-adjacent jamb scale, not a proven door texture."),
        _a("blood:tile:93", "annotated", _vals(placement_kind="surface", surface_applicability="vertical", rendering_behavior="opaque", architectural_role="narrow_strip", interaction_role="static", scale_behavior="narrow_repeat", visual_material="stone_masonry"), "32x128; 100% wall / 1220 uses; 0.01 player widths/repeat. Narrow authored strip / baseboard."),
        _a("blood:tile:2500", "annotated", sky, "64x400; 100% ceiling / 1028 uses / 17 maps. Isolated preview looks like a vertical stone strip; context is sky/parallax.", supporting=["preview", "E1M1 palettes"]),
        _a("blood:tile:3491", "annotated", sky, "64x400; 98% ceiling / 388 uses."),
        _a("blood:tile:3678", "annotated", sky, "64x400; 100% ceiling / 364 uses. E1M1 outdoor palettes."),
        _a("blood:tile:416", "annotated", ceil_fill, "97% ceiling / 472 uses / 14 maps. Indoor ceiling fill, not a sky sheet."),
        _a("blood:tile:455", "annotated", ceil_fill, "96% ceiling / 293 uses."),
        _a("blood:tile:454", "annotated", ceil_fill, "88% ceiling / 277 uses."),
        _a("blood:tile:422", "annotated", ceil_fill, "90% ceiling / 94 uses."),
        _a("blood:tile:270", "annotated", floor_earth, "82% floor / 1151 uses / 23 maps. Noisy brown dirt; isolated preview matches floor, not wall.", supporting=["preview", "E1M1.MAP"]),
        _a("blood:tile:2448", "annotated", floor_earth, "79% floor / 885 uses; neighbors fence 330 and emblem 319."),
        _a("blood:tile:280", "annotated", floor_earth, "93% floor / 372 uses."),
        _a("blood:tile:290", "annotated", floor_earth, "89% floor / 360 uses."),
        _a("blood:tile:294", "annotated", floor_stone, "98% floor / 271 uses."),
        _a("blood:tile:287", "annotated", floor_earth, "98% floor / 265 uses."),
        _a("blood:tile:301", "annotated", floor_earth, "85% floor / 227 uses."),
        _a("blood:tile:44", "annotated", floor_stone, "100% floor / 224 uses; geometric dark stone/marble tile.", supporting=["preview"]),
        _a("blood:tile:292", "annotated", dict(floor_stone, interaction_role="mechanism_associated"), "100% floor / only 58 uses / 7 maps. Scratch-room default floor; corpus-backed but sparse."),
        _a("blood:tile:104", "ambiguous", _vals(placement_kind="surface", surface_applicability="vertical", rendering_behavior="masked", architectural_role="unknown", interaction_role="mechanism_associated", scale_behavior="unknown", visual_material="unknown"), "Only 2 original-map placements, both masked+mechanism. Construction uses it as a door. Insufficient evidence to claim a door family.", confidence=0.2),
        _a("blood:tile:1000", "appearance_only", unused, "Zero campaign placements. Member of native anim 997-1003; later frames are played from tile 997. Do not claim wall usage."),
        _a("blood:tile:1001", "appearance_only", unused, "Zero campaign placements; animation continuation of 997-1003."),
        _a("blood:tile:1002", "appearance_only", unused, "Zero campaign placements; animation continuation of 997-1003."),
        _a("blood:tile:1003", "appearance_only", unused, "Zero campaign placements; animation continuation of 997-1003."),
        _a("blood:tile:1014", "appearance_only", unused, "Unused ART; appearance-only. Candidate visual similarity is speculative."),
        _a("blood:tile:1015", "appearance_only", unused, "Unused ART; appearance-only."),
        _a("blood:tile:1016", "appearance_only", unused, "Unused ART; appearance-only."),
        _a("blood:tile:1017", "appearance_only", unused, "Unused ART; appearance-only."),
        _a("blood:tile:1018", "appearance_only", unused, "Unused ART; appearance-only."),
    ]
    return notes


def v1_annotations() -> list[dict]:
    notes = {item["asset"]: deepcopy(item) for item in v2_annotations()}
    appearance_traps = {
        "blood:tile:2500": (
            "annotated",
            _vals(placement_kind="surface", surface_applicability="vertical", rendering_behavior="opaque", architectural_role="structural_fill", interaction_role="static", scale_behavior="repeating_fill", visual_material="stone_masonry"),
            "v1 appearance pass: 64x400 dark stone strip looks like a tall wall treatment.",
        ),
        "blood:tile:3491": (
            "annotated",
            _vals(placement_kind="surface", surface_applicability="vertical", rendering_behavior="opaque", architectural_role="structural_fill", interaction_role="static", scale_behavior="repeating_fill", visual_material="stone_masonry"),
            "v1 appearance pass: same 64x400 strip shape as 2500.",
        ),
        "blood:tile:3678": (
            "annotated",
            _vals(placement_kind="surface", surface_applicability="vertical", rendering_behavior="opaque", architectural_role="structural_fill", interaction_role="static", scale_behavior="repeating_fill", visual_material="stone_masonry"),
            "v1 appearance pass: 64x400 strip classified as wall from isolated preview.",
        ),
        "blood:tile:0": (
            "annotated",
            _vals(placement_kind="surface", surface_applicability="vertical", rendering_behavior="opaque", architectural_role="structural_fill", interaction_role="static", scale_behavior="repeating_fill", visual_material="stone_masonry"),
            "v1 appearance pass: default tile looks like running-bond masonry.",
        ),
        "blood:tile:1000": (
            "annotated",
            _vals(placement_kind="surface", surface_applicability="vertical", rendering_behavior="opaque", architectural_role="structural_fill", interaction_role="static", scale_behavior="repeating_fill", visual_material="unknown"),
            "v1 appearance pass: unused animation frame classified as a wall from pixels alone.",
        ),
        "blood:tile:90": (
            "annotated",
            _vals(placement_kind="surface", surface_applicability="vertical", rendering_behavior="opaque", architectural_role="structural_fill", interaction_role="static", scale_behavior="repeating_fill", visual_material="unknown"),
            "v1 over-confident wall label on a mixed-use tile (60/27/13).",
        ),
        "blood:tile:255": (
            "annotated",
            _vals(placement_kind="surface", surface_applicability="vertical", rendering_behavior="opaque", architectural_role="structural_fill", interaction_role="static", scale_behavior="repeating_fill", visual_material="unknown"),
            "v1 over-confident wall label on a mixed-use tile (56/14/30).",
        ),
        "blood:tile:281": (
            "annotated",
            _vals(placement_kind="surface", surface_applicability="vertical", rendering_behavior="opaque", architectural_role="structural_fill", interaction_role="static", scale_behavior="repeating_fill", visual_material="unknown"),
            "v1 over-confident wall label on a mixed-use tile (60/30/9).",
        ),
        "blood:tile:319": (
            "annotated",
            _vals(placement_kind="surface", surface_applicability="vertical", rendering_behavior="masked", architectural_role="masked_separator", interaction_role="static", scale_behavior="repeating_fill", visual_material="metal"),
            "v1 lumped the 319 emblem with fence/grate separators because it is 100% masked overwall.",
        ),
        "blood:tile:80": (
            "annotated",
            _vals(placement_kind="surface", surface_applicability="vertical", rendering_behavior="opaque", architectural_role="structural_fill", interaction_role="static", scale_behavior="repeating_fill", visual_material="stone_masonry"),
            "v1 collapsed the header/footer wall band into generic structural_fill.",
        ),
    }
    for asset, (status, values, basis) in appearance_traps.items():
        notes[asset] = _a(asset, status, values, basis, confidence=0.55)
    # v1 facet vocabulary has no complete_wall_band.
    for item in notes.values():
        if item["values"].get("architectural_role") == "complete_wall_band":
            item["values"]["architectural_role"] = "structural_fill"
    return list(notes.values())


FAMILIES_V2 = [
    {
        "id": "family:iron-fence",
        "kind": "functional",
        "members": ["blood:tile:330", "blood:tile:331"],
        "roles": {"blood:tile:330": "primary_separator", "blood:tile:331": "narrow_variant"},
        "basis": "Both 100% masked overwall fence ART; 330 neighbors stone 110/109. No missing door/trim role invented.",
    },
    {
        "id": "family:editor-markers",
        "kind": "functional",
        "members": ["blood:tile:2520", "blood:tile:2521", "blood:tile:2519"],
        "roles": {"blood:tile:2521": "asound", "blood:tile:2520": "marker", "blood:tile:2519": "marker"},
        "basis": "8-px-wide sprite-only mechanism markers; isolated 2521 reads as ASOUND text.",
    },
    {
        "id": "family:sky-sheets",
        "kind": "functional",
        "members": ["blood:tile:2500", "blood:tile:3491", "blood:tile:3678"],
        "roles": {"blood:tile:2500": "primary_sky", "blood:tile:3491": "sky_variant", "blood:tile:3678": "sky_variant"},
        "basis": "Shared 64x400 identity and ceiling-only campaign usage across many maps.",
    },
    {
        "id": "family:liquid-e1m8",
        "kind": "stateful",
        "members": ["blood:tile:1029", "blood:tile:1030", "blood:tile:1120"],
        "roles": {"blood:tile:1030": "animated_ceiling", "blood:tile:1120": "animated_floor", "blood:tile:1029": "animation_head"},
        "transitions": [
            {"from": "blood:tile:1029", "to": "blood:tile:1036", "evidence": "VERIFIED native picanm forward 7 frames on 1029"},
            {"from": "blood:tile:1120", "to": "blood:tile:1126", "evidence": "VERIFIED native picanm forward 6 frames on 1120"},
        ],
        "basis": "Native animation plus 105 floor/ceiling pairings between 1120 and 1030. Later 1031-1035 frames are appearance_only.",
    },
    {
        "id": "family:animated-wall-1100",
        "kind": "stateful",
        "members": ["blood:tile:1100", "blood:tile:1101", "blood:tile:1102", "blood:tile:1103", "blood:tile:1104"],
        "roles": {"blood:tile:1100": "animation_head"},
        "transitions": [{"from": "blood:tile:1100", "to": "blood:tile:1104", "evidence": "VERIFIED native picanm forward 4 frames"}],
        "basis": "100% wall usage on the head tile; do not classify continuation frames as independent materials.",
    },
    {
        "id": "family:anim-997-unused-tail",
        "kind": "stateful",
        "members": ["blood:tile:997", "blood:tile:1000", "blood:tile:1001", "blood:tile:1002", "blood:tile:1003"],
        "roles": {"blood:tile:997": "placed_head", "blood:tile:1000": "appearance_only_frame"},
        "transitions": [{"from": "blood:tile:997", "to": "blood:tile:1003", "evidence": "VERIFIED native picanm forward 6 frames"}],
        "basis": "Only 997 is placed. 1000-1003 are appearance_only continuation frames, not unused walls.",
    },
    {
        "id": "family:switch-1070",
        "kind": "stateful",
        "members": ["blood:tile:1070"],
        "roles": {"blood:tile:1070": "interactive_control"},
        "transitions": [],
        "basis": "Single 32x32 control sprite. No native picanm pair. Blood rest/on state is XSPRITE, not a four-state ART family.",
    },
]


def payload(version: str, status: str, facets: list, annotations: list, **extra: object) -> dict:
    return {
        "$schema": "llmapper.material-ontology",
        "schema_version": 1,
        "version": version,
        "status": status,
        "basis": extra.pop("basis"),
        "useful_for": ["usage_prediction", "retrieval", "authoring", "conversion", "family_grouping"],
        "rejected_distinctions": REJECTED,
        "facets": facets,
        "families": extra.pop("families", []),
        "annotations": annotations,
        **extra,
    }


def main() -> None:
    v1 = payload(
        "v1",
        "proposed",
        FACETS_V1,
        v1_annotations(),
        families=[],
        basis=(
            "Offline multimodal review of a stratified Blood E*.MAP sample plus isolated ART "
            "previews. v1 over-trusts appearance for sky strips, the default tile, unused "
            "animation frames, and mixed-use fills."
        ),
    )
    v2 = payload(
        "v2",
        "refined",
        FACETS_V2,
        v2_annotations(),
        families=FAMILIES_V2,
        revision_of="v1",
        revision_notes=[
            "Split sky_sheet/sky_parallax from vertical structural_fill for 2500/3491/3678 after ceiling-only usage contradicted the appearance pass.",
            "Downgraded tile 0 from masonry wall to placeholder; isolated preview is masonry, corpus usage is never a wall.",
            "Marked 1000-1003 appearance_only animation tails instead of walls.",
            "Downgraded 90/255/281 from annotated vertical fill to mixed_use.",
            "Split 319 hanging_overlay from the 330/331 masked_separator fence family.",
            "Introduced complete_wall_band for tile 80 (header/footer) rather than collapsing it into structural_fill.",
            "Did not add is_door: 104 has 2 placements; 195 is a narrow mechanism-associated jamb, not a door face.",
            "1070 remains a one-member interactive_control family; no invented off/on ART pair.",
        ],
        basis=(
            "Contradiction-driven refinement of v1 against VERIFIED Blood E*.MAP usage, "
            "ART picanm, player-relative scale, and cropped map context."
        ),
    )
    (ROOT / "ontology-v1.json").write_text(json.dumps(v1, indent=2) + "\n", encoding="utf-8")
    (ROOT / "ontology-v2.json").write_text(json.dumps(v2, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "v1_annotations": len(v1["annotations"]),
        "v2_annotations": len(v2["annotations"]),
        "v2_families": len(v2["families"]),
        "v2_facets": [facet["id"] for facet in v2["facets"]],
    }, indent=2))


if __name__ == "__main__":
    main()
