# Blood material ontology discovery

This is the first end-to-end pass from unlabeled evidence to a compact,
queryable Blood vocabulary. The deterministic package still has no LLM runtime
dependency. The review artifact is versioned JSON under `knowledge/blood/`.

```text
mine original E*.MAP + ART
        ↓
stratified sample + isolated previews + cropped 2D context
        ↓
ontology v1 (appearance-heavy INTERPRETED labels)
        ↓
contradiction report against VERIFIED usage
        ↓
ontology v2 (usage + context + scale)
        ↓
facet queries, palettes, scratch authoring, conversion probe
```

Doom composed-texture appearance decoding is explicitly out of this pass.
See [doom.md](doom.md). The Duke/Blood converter still uses role-aware ART
matching; the ontology probe is separable.

## Evidence base

Local Blood campaign snapshot (not checked in): 43 `E*.MAP` maps, 4418 ART
tiles, 895 substantial-use assets, 3365 `appearance_only` tiles, 113 native
animation families.

The reviewer inspected a stratified sample of 96 assets covering high-usage,
mixed-use, masked, sprite-only, animation, mechanism, ceiling, floor,
ambiguous, and unused tiles, plus extras needed for authoring (1070, 180, 292,
318, 104). Each representative occurrence records why it was kept (map,
placement kind, masked/mechanism, typical vs outlier repeat, neighbor palette).

Context packets are cropped 2D SVG plus isolated PNG, not 3D screenshots.

## Surviving facets (v2)

| Facet | Values that earned their keep | Why it survives |
| --- | --- | --- |
| `placement_kind` | surface, sprite, marker | 2521 is editor text; 1070 is a switch sprite; neither is a wall. |
| `surface_applicability` | vertical, horizontal_floor, horizontal_ceiling, sky_parallax, mixed, none | 2500 is 64×400 and 100% ceiling across 17 maps; 270 is 82% floor; 90/255 mix surfaces. |
| `rendering_behavior` | opaque, masked, translucent | 330 is 560/560 masked overwalls; 1067 is a hanging cobweb overlay. |
| `architectural_role` | structural_fill, complete_wall_band, masked_separator, hanging_overlay, narrow_strip, sky_sheet, control_face, marker, placeholder | Function split independently of stone/metal names. |
| `interaction_role` | static, mechanism_associated, animated_surface, interactive_control, marker | 1100-1104 is an animated wall; 1070 is a one-tile control; 195 is mechanism-associated but not a door. |
| `scale_behavior` | repeating_fill, discrete_instance, narrow_repeat | 110 tiles at ~0.17 player widths/repeat; 330 is 0.03; 195 is 0.005; 1067 is a discrete overlay. |
| `visual_material` | stone_masonry, brick, metal, organic_earth, liquid, unknown | Palette mood only. Does not predict usage. |

Rejected after v1: a single primary class, visual theme (gothic/industrial),
`is_door`, indoor/outdoor as a facet, and damage-progression families (no
sample evidence).

v1 → v2 changes, preserved in `ontology_history` when imported in order:

- sky strips 2500/3491/3678 were vertical fills from isolated previews; usage is ceiling-only
- tile 0 looked like masonry and is the default/empty picnum (0 walls)
- 1000-1003 were labeled walls; they are unused animation tails of 997-1003
- 90/255/281 were over-confident vertical fills; they are mixed_use
- 319 (emblem) was lumped with fence separators; it is a hanging overlay
- tile 80 gained `complete_wall_band` (header/footer) instead of generic fill

11 annotation-driven contradictions fired on v1. Zero fired on v2.

## Authoring kit from v2 queries

Intent: dark old interior with a structural wall, coherent floor/ceiling, a
door opening, one masked separator, one interactive control, limited trim.

| Role | Query (imported facets only) | Chosen tile |
| --- | --- | --- |
| structural wall | vertical + opaque + structural_fill + repeating_fill | 110 |
| floor | horizontal_floor + opaque + structural_fill | 270 |
| ceiling | horizontal_ceiling + structural_fill + static | 416 |
| masked separator | masked_separator + masked | 330 |
| interactive control | interactive_control | 1070 |
| narrow trim | narrow_strip + vertical + static | 93 |

Native IDs stay explicit. Tile 110 already co-occurs with 270 and 330 in
original maps.

## Naive vs knowledge (same geometry)

Appearance-only assignment used nearest ART neighbors of wall 110 for every
slot. Construction defaults 180/292/385/104 were also built for reference.

| Slot | Naive nearest-to-110 | Corpus fact | Knowledge |
| --- | --- | --- | --- |
| wall | 110 | 86% wall repeating stone | 110 |
| floor | 273 | mixed 53/19/27 wall/floor/ceiling | 270 (82% floor) |
| ceiling | 100 | 99% wall | 416 (97% ceiling) |
| separator | 113 | 4 uses, 50% masked | 330 (560 masked overwalls) |
| control | 512 | mixed surface fill | 1070 (32×32 sprite, 100% mechanism) |
| trim | 42 | 90% wall repeating fill | 93 (32×128, 0.01 player widths) |

Default ceiling 385 is 93% wall. Default door 104 has two original-map
placements. Knowledge does not invent a door family; the door sector uses the
structural wall plus the masked fence on the portal.

Maps: `work/material-authoring/naive-appearance.MAP` and
`work/material-authoring/ontology-aware.MAP`. Both validate. Comparison is
functional/role/scale/palette, not a fake quality score.

## Conversion probe (converter unchanged)

Role-aware matching still treats “used as a ceiling at least once” as one
pool. Ranking brick wall 385 into that pool prefers other walls that merely
have a tiny ceiling share (474/177/373 are 83–96% wall). Ontology indoor
ceiling query returns 454/416/422.

Matching indoor ceiling 416 into the same old pool still ranks animated
liquid 1030 second. Ontology `structural_fill + static` keeps 454/422/455.

`bloodmap.e3l11._apply_materials` is not globally replaced.

## What is still missing

- 3D/runtime screenshots (packets are 2D crops)
- Broader annotation coverage beyond the stratified sample
- A verified door-face family
- Switch on/off ART pairs (1070 has no native picanm)
- Doom composed-texture appearance
- Material suitability as a preflight rule in the typed authoring loop

The hypothesis is supported for Blood: a general reviewer can derive a useful
vocabulary from appearance plus usage, and that vocabulary chooses better
concrete tiles than raw IDs or visual nearest-neighbour alone.
