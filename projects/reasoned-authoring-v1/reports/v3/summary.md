# Iteration v3

- source: `projects/reasoned-authoring-v1/level/candidate_v3.py`
- MAP sha256: `6eba6d63f5a1654345d20890a7d83e1d5caec5870fe810dce2f98258d4fbdbbd`
- counts: {'sectors': 31, 'walls': 208, 'sprites': 60, 'regions': 31, 'connections': 38}
- deterministic compile: True

## Hard gates

- **PASS** `native_structure_valid` — native Blood validation reports no errors
- **PASS** `authored_geometry_valid` — 0 authored error(s), 0 warning(s)
- **PASS** `no_unintended_overlaps` — no unintended XY footprint overlap
- **PASS** `no_unresolved_boundary_contacts` — no T-junctions, partial collinear overlaps, or proper crossings
- **PASS** `intended_adjacency_realized` — every intended adjacency became a portal and no portal is unintended
- **PASS** `geometry_conservation` — 178 source edges -> 208 emitted; split 30
- **PASS** `portals_realized` — 38 authored connections realized
- **PASS** `player_start_valid` — start sector:0 of 31
- **PASS** `player_relative_clearance` — start clear height 33792 = 6.0 player heights
- **PASS** `required_reachability` — 29/29 mandatory regions reachable
- **PASS** `exit_reachable` — an exit is reachable under the declared progression
- **PASS** `object_attachment_valid` — sprite attachments and use poses are consistent
- **PASS** `deterministic_emission` — two independent compiles produced identical bytes
- **PASS** `nblood_load_smoke` — NBlood load smoke pass; revisions=['rlocal-agtst10']

## Independently derived hierarchy

- assemblies 1, spaces 14, singletons 9, detail groups 9
- cross-space connections 14, vertical overlap relations 0

### Authored assembly vs derived spaces

| authored | sectors | derived spaces | dominant share | singletons |
| --- | --- | --- | --- | --- |
| arrival approach | 3 | 1 | 1.0 | 0 |
| arrival courtyard | 8 | 1 | 1.0 | 0 |
| chapel | 5 | 2 | 0.9602 | 1 |
| lower crypt | 8 | 3 | 0.8693 | 1 |
| optional ossuary | 2 | 2 | 0.9048 | 2 |
| upper gallery | 3 | 3 | 0.9319 | 3 |
| exit chamber | 2 | 2 | 0.9355 | 2 |

### Discrepancies

- none raised by the current rules

## Probes

- `probe:reach_chapel` (access) -> **pass** — sector:6 is reachable from sector:0
- `probe:reach_apse` (access) -> **pass** — sector:9 is reachable from sector:0
- `probe:reach_crypt` (access) -> **pass** — sector:15 is reachable from sector:0
- `probe:route_start_to_exit` (route) -> **pass** — Route found with 10 steps
- `probe:gallery_seen_late` (visibility) -> **pass** — sector:24 is visible at 7 steps (88% of route)
  - {"first_visible_step": 7, "route_fraction": 0.875, "total_steps": 8, "visible_at_steps": [7, 8]}
- `probe:reveal_contrast` (transition) -> **pass** — 
  - {"area_ratio": 35.9107, "clear_height_delta": 61952, "dest_area": 148267008.0, "dest_clear_height": 90112, "floor_delta": 0, "source_area": 4128768.0, "source_clear_height": 28160}
- `probe:arch_contrast` (transition) -> **pass** — 
  - {"area_ratio": 27.375, "clear_height_delta": 45056, "dest_area": 64585728.0, "dest_clear_height": 67584, "floor_delta": 0, "source_area": 2359296.0, "source_clear_height": 22528}
- `probe:crypt_contrast` (transition) -> **pass** — 
  - {"area_ratio": 0.189, "clear_height_delta": -61952, "dest_area": 28016640.0, "dest_clear_height": 28160, "floor_delta": 12288, "source_area": 148267008.0, "source_clear_height": 90112}
- `probe:gallery_contrast` (transition) -> **pass** — 
  - {"area_ratio": 0.4356, "clear_height_delta": -22528, "dest_area": 64585728.0, "dest_clear_height": 67584, "floor_delta": -11520, "source_area": 148267008.0, "source_clear_height": 90112}
- `probe:ossuary_reachable_while_shut` (access) -> **fail** — sector:19 is not reachable from sector:0 under the declared world state
- `probe:gallery_choices` (escape) -> **pass** — 
  - {"blocked_exit_count": 0, "blocked_exits": [], "dead_end_depth": 0, "viable_exit_count": 3, "viable_exits": [{"edge": "portal:163", "sector": "sector:23", "status": "open"}, {"edge": "portal:175", "sector": "sector:25", "status": "open"}, {"edge": "portal:169", "sector": "sector:29", "status": "open_via_world_state"}]}
- `probe:revisit_after_crypt_gate` (revisit) -> **pass** — 
  - {"newly_reachable_count": 8, "newly_reachable_sectors": ["sector:10", "sector:11", "sector:12", "sector:13", "sector:14", "sector:15", "sector:16", "sector:17"], "reachable_after_count": 27, "reachable_before_count": 19, "still_unreachable_count": 4}
- `probe:courtyard_choices` (escape) -> **pass** — 
  - {"blocked_exit_count": 0, "blocked_exits": [], "dead_end_depth": 0, "viable_exit_count": 6, "viable_exits": [{"edge": "portal:13", "sector": "sector:2", "status": "open"}, {"edge": "portal:50", "sector": "sector:4", "status": "open"}, {"edge": "portal:34", "sector": "sector:5", "status": "open_via_world_state"}, {"edge": "portal:26", "sector": "sector:10", "status": "open_via_world_state"}, {"edge": "portal:21", "sector": "sector:20", "status": "open"}, {"edge": "portal:23", "sector": "sector:28", "status": "open"}]}
- `probe:gatehouse_choices` (escape) -> **pass** — 
  - {"blocked_exit_count": 0, "blocked_exits": [], "dead_end_depth": 0, "viable_exit_count": 2, "viable_exits": [{"edge": "portal:9", "sector": "sector:1", "status": "open"}, {"edge": "portal:13", "sector": "sector:3", "status": "open"}]}
- `probe:chapel_choices` (escape) -> **pass** — 
  - {"blocked_exit_count": 0, "blocked_exits": [], "dead_end_depth": 0, "viable_exit_count": 4, "viable_exits": [{"edge": "portal:60", "sector": "sector:5", "status": "open_via_world_state"}, {"edge": "portal:63", "sector": "sector:7", "status": "open"}, {"edge": "portal:67", "sector": "sector:8", "status": "open"}, {"edge": "portal:65", "sector": "sector:9", "status": "open"}]}
- `probe:crypt_choices` (escape) -> **pass** — 
  - {"blocked_exit_count": 0, "blocked_exits": [], "dead_end_depth": 0, "viable_exit_count": 3, "viable_exits": [{"edge": "portal:111", "sector": "sector:14", "status": "open"}, {"edge": "portal:124", "sector": "sector:16", "status": "open"}, {"edge": "portal:121", "sector": "sector:17", "status": "open"}]}

## ART and visual composition

- catalog: loaded
- unresolved assets: 0
- visually empty derived spaces: 5
- decorative distribution: 0.2167 of 60 space sprites in one space
- identical dominant room surfaces:
  - ['assembly:crypt', 'assembly:ossuary'] -> {'floor': 1097, 'ceiling': 1097, 'wall': 1097}

## Corpus-relative scale and shape

| derived space | player areas | clear player heights | height pct vs same-size corpus |
| --- | --- | --- | --- |
| assembly:001/space:002 | 1101.5 | 15.54 | 59.0 |
| assembly:001/space:011 | 438.0 | 12.0 | 56.8 |
| assembly:001/space:007 | 266.0 | 4.49 | 8.5 |
| assembly:001/space:004 | 193.0 | 8.58 | 35.4 |
| assembly:001/space:014 | 116.0 | 8.0 | 41.0 |
| assembly:001/space:001 | 104.0 | 5.27 | 10.5 |
| assembly:001/space:009 | 76.0 | 3.0 | 3.5 |
| assembly:001/space:006 | 32.0 | 4.0 | 5.7 |
| assembly:001/space:010 | 16.0 | 4.0 | 7.0 |
| assembly:001/space:012 | 16.0 | 4.0 | 7.0 |

| shape metric | candidate | corpus percentile |
| --- | --- | --- |
| orthogonal_length_fraction | 0.8378 | 88.1 |
| diagonal_length_fraction | 0.1171 | 71.4 |
| orientation_5deg_bins_occupied | 6.0 | 0.0 |
| orientation_diversity | 0.1667 | 0.0 |
| chamfer_fraction | 0.3053 | 100.0 |
| segmented_arc_chain_count | 9.0 | 14.3 |
| rectangular_sector_fraction | 0.5484 | 100.0 |
| convex_sector_fraction | 1.0 | 100.0 |
| median_outer_vertex_count | 4.0 | 59.5 |

- sprite scale: measured, 0 oversized decoration(s)

### Scale and shape findings

- `space_much_lower_than_corpus_for_its_size` — derived space assembly:001/space:006 covers 32 player areas but is only 4.0 player heights clear (area-weighted), at the 5.7 percentile of the 2845 corpus sectors of comparable footprint
- `space_much_lower_than_corpus_for_its_size` — derived space assembly:001/space:007 covers 266 player areas but is only 4.49 player heights clear (area-weighted), at the 8.5 percentile of the 706 corpus sectors of comparable footprint
- `space_much_lower_than_corpus_for_its_size` — derived space assembly:001/space:009 covers 76 player areas but is only 3.0 player heights clear (area-weighted), at the 3.5 percentile of the 1941 corpus sectors of comparable footprint
- `shape_outside_corpus_mass` — orientation_5deg_bins_occupied is 6.0, at the 0.0 percentile of 42 original maps
- `shape_outside_corpus_mass` — orientation_diversity is 0.1667, at the 0.0 percentile of 42 original maps
- `shape_outside_corpus_mass` — rectangular_sector_fraction is 0.5484, at the 100.0 percentile of 42 original maps

## Render

- capture status: pass
- `view:start` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v3\views\view_start.png`
- `view:gate_approach` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v3\views\view_gate_approach.png`
- `view:gatehouse` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v3\views\view_gatehouse.png`
- `view:courtyard_center` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v3\views\view_courtyard_center.png`
- `view:courtyard_corner` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v3\views\view_courtyard_corner.png`
- `view:chapel_interior` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v3\views\view_chapel_interior.png`
- `view:chapel_apse` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v3\views\view_chapel_apse.png`
- `view:crypt_hall` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v3\views\view_crypt_hall.png`
- `view:gallery_arch` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v3\views\view_gallery_arch.png`
- `view:gallery` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v3\views\view_gallery.png`
- `view:courtyard_from_stair` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v3\views\view_courtyard_from_stair.png`
- `view:chapel_reverse` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v3\views\view_chapel_reverse.png`
