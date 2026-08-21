# Iteration v0

- source: `projects/reasoned-authoring-v1/level/candidate_v0.py`
- MAP sha256: `385472cc8708f4060344f99e7ee548559170c48536e644d21064d95077a8e9f6`
- counts: {'sectors': 30, 'walls': 157, 'sprites': 5, 'regions': 30, 'connections': 33}
- deterministic compile: True

## Hard gates

- **PASS** `native_structure_valid` — native Blood validation reports no errors
- **PASS** `authored_geometry_valid` — 0 authored error(s), 0 warning(s)
- **PASS** `no_unintended_overlaps` — no unintended XY footprint overlap
- **PASS** `no_unresolved_boundary_contacts` — no T-junctions, partial collinear overlaps, or proper crossings
- **PASS** `intended_adjacency_realized` — every intended adjacency became a portal and no portal is unintended
- **PASS** `geometry_conservation` — 128 source edges -> 157 emitted; split 29
- **PASS** `portals_realized` — 33 authored connections realized
- **PASS** `player_start_valid` — start sector:0 of 30
- **PASS** `player_relative_clearance` — start clear height 22528 = 4.0 player heights
- **PASS** `required_reachability` — 28/28 mandatory regions reachable
- **PASS** `exit_reachable` — an exit is reachable under the declared progression
- **PASS** `object_attachment_valid` — sprite attachments and use poses are consistent
- **PASS** `deterministic_emission` — two independent compiles produced identical bytes
- **PASS** `nblood_load_smoke` — NBlood load smoke pass; revisions=['rlocal-agtst10']

## Independently derived hierarchy

- assemblies 1, spaces 9, singletons 7, detail groups 4
- cross-space connections 8, vertical overlap relations 0

### Authored assembly vs derived spaces

| authored | sectors | derived spaces | dominant share | singletons |
| --- | --- | --- | --- | --- |
| arrival approach | 2 | 1 | 1.0 | 0 |
| arrival courtyard | 2 | 1 | 1.0 | 0 |
| chapel | 2 | 2 | 0.973 | 2 |
| lower crypt | 9 | 2 | 0.9615 | 1 |
| optional ossuary | 2 | 2 | 0.8889 | 2 |
| upper gallery | 11 | 1 | 1.0 | 0 |
| exit chamber | 2 | 2 | 0.9375 | 2 |

### Discrepancies

- `authored_assemblies_share_one_perceptual_space` — authored assemblies ['assembly:arrival', 'assembly:courtyard', 'assembly:gallery'] were grouped into the single derived space assembly:001/space:001, so their intended identities are not perceptually separated
  - rule: one derived space contains sectors from more than one authored assembly
  - evidence: decompiled:assembly:001/space:001, intent:assembly:arrival, intent:assembly:courtyard, intent:assembly:gallery

## Probes

- `probe:reach_chapel` (access) -> **pass** — sector:5 is reachable from sector:0
- `probe:reach_crypt` (access) -> **fail** — sector:13 is not reachable from sector:0 under the declared world state
- `probe:route_start_to_exit` (route) -> **pass** — Route found with 10 steps
- `probe:route_through_hierarchy` (visibility) -> **pass** — sector:5 is visible at 3 steps (75% of route)
  - {"first_visible_step": 3, "route_fraction": 0.75, "total_steps": 4, "visible_at_steps": [3, 4]}
- `probe:reveal_contrast` (transition) -> **pass** — 
  - {"area_ratio": 63.5, "clear_height_delta": 78848, "dest_area": 149815296.0, "dest_clear_height": 90112, "floor_delta": 0, "source_area": 2359296.0, "source_clear_height": 11264}
- `probe:crypt_contrast` (transition) -> **pass** — 
  - {"area_ratio": 0.126, "clear_height_delta": -77824, "dest_area": 18874368.0, "dest_clear_height": 12288, "floor_delta": 12288, "source_area": 149815296.0, "source_clear_height": 90112}
- `probe:gallery_contrast` (transition) -> **pass** — 
  - {"area_ratio": 0.3858, "clear_height_delta": -56320, "dest_area": 57802752.0, "dest_clear_height": 33792, "floor_delta": -15360, "source_area": 149815296.0, "source_clear_height": 90112}
- `probe:ossuary_optional` (access) -> **fail** — sector:16 is not reachable from sector:0 under the declared world state
- `probe:gallery_choices` (escape) -> **pass** — 
  - {"blocked_exit_count": 0, "blocked_exits": [], "dead_end_depth": 0, "viable_exit_count": 3, "viable_exits": [{"edge": "portal:115", "sector": "sector:21", "status": "open"}, {"edge": "portal:123", "sector": "sector:23", "status": "open"}, {"edge": "portal:120", "sector": "sector:28", "status": "open_via_world_state"}]}
- `probe:revisit_after_crypt_gate` (revisit) -> **pass** — 
  - {"newly_reachable_count": 1, "newly_reachable_sectors": ["sector:6"], "reachable_after_count": 18, "reachable_before_count": 17, "still_unreachable_count": 12}
- `probe:courtyard_choices` (escape) -> **pass** — 
  - {"blocked_exit_count": 0, "blocked_exits": [], "dead_end_depth": 0, "viable_exit_count": 6, "viable_exits": [{"edge": "portal:7", "sector": "sector:1", "status": "open"}, {"edge": "portal:31", "sector": "sector:3", "status": "open"}, {"edge": "portal:26", "sector": "sector:4", "status": "open_via_world_state"}, {"edge": "portal:17", "sector": "sector:6", "status": "open_via_world_state"}, {"edge": "portal:12", "sector": "sector:17", "status": "open"}, {"edge": "portal:14", "sector": "sector:27", "status": "open"}]}
- `probe:tunnel_choices` (escape) -> **pass** — 
  - {"blocked_exit_count": 0, "blocked_exits": [], "dead_end_depth": 0, "viable_exit_count": 2, "viable_exits": [{"edge": "portal:2", "sector": "sector:0", "status": "open"}, {"edge": "portal:7", "sector": "sector:2", "status": "open"}]}

## ART and visual composition

- catalog: loaded
- unresolved assets: 0
- visually empty derived spaces: 5
- decorative distribution: 0.4 of 5 space sprites in one space
- near-identical surface vocabularies:
  - ['assembly:arrival', 'assembly:courtyard'] overlap 1.0
  - ['assembly:arrival', 'assembly:gallery'] overlap 1.0
  - ['assembly:courtyard', 'assembly:gallery'] overlap 1.0
- identical dominant room surfaces:
  - ['assembly:chapel', 'assembly:gallery'] -> {'floor': 294, 'ceiling': 416, 'wall': 5}
  - ['assembly:chapel', 'assembly:exit'] -> {'floor': 294, 'ceiling': 416, 'wall': 5}
  - ['assembly:crypt', 'assembly:ossuary'] -> {'floor': 1097, 'ceiling': 1097, 'wall': 1097}
  - ['assembly:gallery', 'assembly:exit'] -> {'floor': 294, 'ceiling': 416, 'wall': 5}

## Corpus-relative scale and shape

| derived space | player areas | clear player heights | height pct vs same-size corpus |
| --- | --- | --- | --- |
| assembly:001/space:001 | 1624.0 | 12.4 | 54.8 |
| assembly:001/space:003 | 288.0 | 7.0 | 25.0 |
| assembly:001/space:005 | 200.0 | 2.36 | 2.0 |
| assembly:001/space:009 | 120.0 | 4.0 | 4.5 |
| assembly:001/space:007 | 64.0 | 2.0 | 0.8 |
| assembly:001/space:002 | 8.0 | 0.0 | 1.5 |
| assembly:001/space:004 | 8.0 | 0.0 | 1.5 |
| assembly:001/space:006 | 8.0 | 0.0 | 1.5 |
| assembly:001/space:008 | 8.0 | 0.0 | 1.5 |

| shape metric | candidate | corpus percentile |
| --- | --- | --- |
| orthogonal_length_fraction | 1.0 | 100.0 |
| diagonal_length_fraction | 0.0 | 0.0 |
| orientation_5deg_bins_occupied | 2.0 | 0.0 |
| orientation_diversity | 0.0556 | 0.0 |
| chamfer_fraction | 0.0 | 0.0 |
| segmented_arc_chain_count | 0.0 | 2.4 |
| rectangular_sector_fraction | 0.7667 | 100.0 |
| convex_sector_fraction | 1.0 | 100.0 |
| median_outer_vertex_count | 4.0 | 59.5 |

- sprite scale: measured, 0 oversized decoration(s)

### Scale and shape findings

- `space_much_lower_than_corpus_for_its_size` — derived space assembly:001/space:005 covers 200 player areas but is only 2.36 player heights clear (area-weighted), at the 2.0 percentile of the 976 corpus sectors of comparable footprint
- `space_much_lower_than_corpus_for_its_size` — derived space assembly:001/space:007 covers 64 player areas but is only 2.0 player heights clear (area-weighted), at the 0.8 percentile of the 2166 corpus sectors of comparable footprint
- `space_much_lower_than_corpus_for_its_size` — derived space assembly:001/space:009 covers 120 player areas but is only 4.0 player heights clear (area-weighted), at the 4.5 percentile of the 1430 corpus sectors of comparable footprint
- `shape_outside_corpus_mass` — orthogonal_length_fraction is 1.0, at the 100.0 percentile of 42 original maps
- `shape_outside_corpus_mass` — diagonal_length_fraction is 0.0, at the 0.0 percentile of 42 original maps
- `shape_outside_corpus_mass` — orientation_5deg_bins_occupied is 2.0, at the 0.0 percentile of 42 original maps
- `shape_outside_corpus_mass` — orientation_diversity is 0.0556, at the 0.0 percentile of 42 original maps
- `shape_outside_corpus_mass` — chamfer_fraction is 0.0, at the 0.0 percentile of 42 original maps
- `shape_outside_corpus_mass` — segmented_arc_chain_count is 0.0, at the 2.4 percentile of 42 original maps
- `shape_outside_corpus_mass` — rectangular_sector_fraction is 0.7667, at the 100.0 percentile of 42 original maps

## Render

- capture status: pass
- `view:start` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v0\views\view_start.png`
- `view:gate_approach` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v0\views\view_gate_approach.png`
- `view:courtyard_center` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v0\views\view_courtyard_center.png`
- `view:chapel_interior` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v0\views\view_chapel_interior.png`
- `view:crypt_hall` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v0\views\view_crypt_hall.png`
- `view:gallery` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v0\views\view_gallery.png`
- `view:courtyard_from_stair` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v0\views\view_courtyard_from_stair.png`
- `view:chapel_reverse` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v0\views\view_chapel_reverse.png`
