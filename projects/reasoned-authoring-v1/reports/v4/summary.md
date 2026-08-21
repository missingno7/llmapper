# Iteration v4

- source: `projects/reasoned-authoring-v1/level/candidate_v4.py`
- MAP sha256: `1f358e5d3dd42c6125f0e7c2a44a580cb38462283722184423f1b8f0517d6ca3`
- counts: {'sectors': 38, 'walls': 250, 'sprites': 60, 'regions': 38, 'connections': 49}
- deterministic compile: True

## Hard gates

- **PASS** `native_structure_valid` — native Blood validation reports no errors
- **PASS** `authored_geometry_valid` — 0 authored error(s), 0 warning(s)
- **PASS** `no_unintended_overlaps` — no unintended XY footprint overlap
- **PASS** `no_unresolved_boundary_contacts` — no T-junctions, partial collinear overlaps, or proper crossings
- **PASS** `intended_adjacency_realized` — every intended adjacency became a portal and no portal is unintended
- **PASS** `geometry_conservation` — 211 source edges -> 250 emitted; split 39
- **PASS** `portals_realized` — 49 authored connections realized
- **PASS** `player_start_valid` — start sector:0 of 38
- **PASS** `player_relative_clearance` — start clear height 33792 = 6.0 player heights
- **PASS** `required_reachability` — 36/36 mandatory regions reachable
- **PASS** `exit_reachable` — an exit is reachable under the declared progression
- **PASS** `object_attachment_valid` — sprite attachments and use poses are consistent
- **PASS** `deterministic_emission` — two independent compiles produced identical bytes
- **PASS** `nblood_load_smoke` — NBlood load smoke pass; revisions=['rlocal-agtst10']

## Independently derived hierarchy

- assemblies 1, spaces 16, singletons 9, detail groups 10
- cross-space connections 26, vertical overlap relations 0

### Authored assembly vs derived spaces

| authored | sectors | derived spaces | dominant share | singletons |
| --- | --- | --- | --- | --- |
| arrival approach | 3 | 1 | 1.0 | 0 |
| arrival courtyard | 8 | 2 | 0.9564 | 1 |
| chapel | 8 | 2 | 0.961 | 1 |
| lower crypt | 10 | 4 | 0.8188 | 2 |
| optional ossuary | 2 | 2 | 0.9048 | 2 |
| upper gallery | 4 | 3 | 0.9328 | 2 |
| exit chamber | 3 | 2 | 0.937 | 1 |

### Discrepancies

- none raised by the current rules

## Probes

- `probe:reach_chapel` (access) -> **pass** — sector:6 is reachable from sector:0
- `probe:reach_apse` (access) -> **pass** — sector:9 is reachable from sector:0
- `probe:reach_crypt` (access) -> **pass** — sector:18 is reachable from sector:0
- `probe:route_start_to_exit` (route) -> **pass** — Route found with 10 steps
- `probe:gallery_seen_late` (visibility) -> **pass** — sector:28 is visible at 7 steps (88% of route)
  - {"first_visible_step": 7, "route_fraction": 0.875, "total_steps": 8, "visible_at_steps": [7, 8]}
- `probe:reveal_contrast` (transition) -> **pass** — 
  - {"area_ratio": 35.9107, "clear_height_delta": 61952, "dest_area": 148267008.0, "dest_clear_height": 90112, "floor_delta": 0, "source_area": 4128768.0, "source_clear_height": 28160}
- `probe:arch_contrast` (transition) -> **pass** — 
  - {"area_ratio": 27.375, "clear_height_delta": 45056, "dest_area": 64585728.0, "dest_clear_height": 67584, "floor_delta": 0, "source_area": 2359296.0, "source_clear_height": 22528}
- `probe:crypt_contrast` (transition) -> **pass** — 
  - {"area_ratio": 0.173, "clear_height_delta": -61952, "dest_area": 25657344.0, "dest_clear_height": 28160, "floor_delta": 12288, "source_area": 148267008.0, "source_clear_height": 90112}
- `probe:gallery_contrast` (transition) -> **pass** — 
  - {"area_ratio": 0.4356, "clear_height_delta": -22528, "dest_area": 64585728.0, "dest_clear_height": 67584, "floor_delta": -12288, "source_area": 148267008.0, "source_clear_height": 90112}
- `probe:ossuary_reachable_while_shut` (access) -> **fail** — sector:23 is not reachable from sector:0 under the declared world state
- `probe:gallery_choices` (escape) -> **pass** — 
  - {"blocked_exit_count": 0, "blocked_exits": [], "dead_end_depth": 0, "viable_exit_count": 4, "viable_exits": [{"edge": "portal:189", "sector": "sector:27", "status": "open"}, {"edge": "portal:201", "sector": "sector:29", "status": "open"}, {"edge": "portal:195", "sector": "sector:33", "status": "open_via_world_state"}, {"edge": "portal:203", "sector": "sector:36", "status": "open"}]}
- `probe:revisit_after_crypt_gate` (revisit) -> **pass** — 
  - {"newly_reachable_count": 10, "newly_reachable_sectors": ["sector:13", "sector:14", "sector:15", "sector:16", "sector:17", "sector:18", "sector:19", "sector:20", "sector:21", "sector:35"], "reachable_after_count": 33, "reachable_before_count": 23, "still_unreachable_count": 5}
- `probe:courtyard_choices` (escape) -> **pass** — 
  - {"blocked_exit_count": 0, "blocked_exits": [], "dead_end_depth": 0, "viable_exit_count": 6, "viable_exits": [{"edge": "portal:13", "sector": "sector:2", "status": "open"}, {"edge": "portal:50", "sector": "sector:4", "status": "open"}, {"edge": "portal:34", "sector": "sector:5", "status": "open_via_world_state"}, {"edge": "portal:26", "sector": "sector:13", "status": "open_via_world_state"}, {"edge": "portal:21", "sector": "sector:24", "status": "open"}, {"edge": "portal:23", "sector": "sector:32", "status": "open"}]}
- `probe:gatehouse_choices` (escape) -> **pass** — 
  - {"blocked_exit_count": 0, "blocked_exits": [], "dead_end_depth": 0, "viable_exit_count": 2, "viable_exits": [{"edge": "portal:9", "sector": "sector:1", "status": "open"}, {"edge": "portal:13", "sector": "sector:3", "status": "open"}]}
- `probe:chapel_choices` (escape) -> **pass** — 
  - {"blocked_exit_count": 0, "blocked_exits": [], "dead_end_depth": 0, "viable_exit_count": 5, "viable_exits": [{"edge": "portal:60", "sector": "sector:5", "status": "open_via_world_state"}, {"edge": "portal:63", "sector": "sector:7", "status": "open"}, {"edge": "portal:68", "sector": "sector:8", "status": "open"}, {"edge": "portal:66", "sector": "sector:9", "status": "open"}, {"edge": "portal:65", "sector": "sector:10", "status": "open"}]}
- `probe:crypt_choices` (escape) -> **pass** — 
  - {"blocked_exit_count": 0, "blocked_exits": [], "dead_end_depth": 0, "viable_exit_count": 5, "viable_exits": [{"edge": "portal:126", "sector": "sector:17", "status": "open"}, {"edge": "portal:147", "sector": "sector:19", "status": "open"}, {"edge": "portal:142", "sector": "sector:20", "status": "open"}, {"edge": "portal:139", "sector": "sector:21", "status": "open"}, {"edge": "portal:137", "sector": "sector:35", "status": "open"}]}

## ART and visual composition

- catalog: loaded
- unresolved assets: 0
- visually empty derived spaces: 6
- decorative distribution: 0.2167 of 60 space sprites in one space
- identical dominant room surfaces:
  - ['assembly:crypt', 'assembly:ossuary'] -> {'floor': 1097, 'ceiling': 1097, 'wall': 1097}

## Corpus-relative scale and shape

| derived space | player areas | clear player heights | height pct vs same-size corpus |
| --- | --- | --- | --- |
| assembly:001/space:002 | 1053.5 | 15.5 | 59.3 |
| assembly:001/space:013 | 444.0 | 11.92 | 56.5 |
| assembly:001/space:008 | 253.0 | 4.44 | 8.2 |
| assembly:001/space:005 | 197.0 | 8.57 | 35.5 |
| assembly:001/space:016 | 119.0 | 7.9 | 39.7 |
| assembly:001/space:001 | 104.0 | 5.27 | 10.5 |
| assembly:001/space:011 | 76.0 | 3.0 | 3.5 |
| assembly:001/space:003 | 48.0 | 14.91 | 88.1 |
| assembly:001/space:007 | 32.0 | 4.0 | 5.7 |
| assembly:001/space:009 | 16.0 | 3.91 | 6.6 |

| shape metric | candidate | corpus percentile |
| --- | --- | --- |
| orthogonal_length_fraction | 0.8556 | 90.5 |
| diagonal_length_fraction | 0.1074 | 61.9 |
| orientation_5deg_bins_occupied | 5.0 | 0.0 |
| orientation_diversity | 0.1389 | 0.0 |
| chamfer_fraction | 0.2632 | 100.0 |
| segmented_arc_chain_count | 9.0 | 14.3 |
| rectangular_sector_fraction | 0.6316 | 100.0 |
| convex_sector_fraction | 0.9737 | 100.0 |
| median_outer_vertex_count | 4.0 | 59.5 |

- sprite scale: measured, 0 oversized decoration(s)

### Scale and shape findings

- `space_much_lower_than_corpus_for_its_size` — derived space assembly:001/space:007 covers 32 player areas but is only 4.0 player heights clear (area-weighted), at the 5.7 percentile of the 2845 corpus sectors of comparable footprint
- `space_much_lower_than_corpus_for_its_size` — derived space assembly:001/space:008 covers 253 player areas but is only 4.44 player heights clear (area-weighted), at the 8.2 percentile of the 741 corpus sectors of comparable footprint
- `space_much_lower_than_corpus_for_its_size` — derived space assembly:001/space:011 covers 76 player areas but is only 3.0 player heights clear (area-weighted), at the 3.5 percentile of the 1941 corpus sectors of comparable footprint
- `shape_outside_corpus_mass` — orthogonal_length_fraction is 0.8556, at the 90.5 percentile of 42 original maps
- `shape_outside_corpus_mass` — orientation_5deg_bins_occupied is 5.0, at the 0.0 percentile of 42 original maps
- `shape_outside_corpus_mass` — orientation_diversity is 0.1389, at the 0.0 percentile of 42 original maps
- `shape_outside_corpus_mass` — rectangular_sector_fraction is 0.6316, at the 100.0 percentile of 42 original maps

## Render

- capture status: pass
- `view:start` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v4\views\view_start.png`
- `view:gate_approach` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v4\views\view_gate_approach.png`
- `view:gatehouse` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v4\views\view_gatehouse.png`
- `view:courtyard_center` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v4\views\view_courtyard_center.png`
- `view:courtyard_corner` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v4\views\view_courtyard_corner.png`
- `view:chapel_interior` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v4\views\view_chapel_interior.png`
- `view:chapel_apse` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v4\views\view_chapel_apse.png`
- `view:chancel_stair` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v4\views\view_chancel_stair.png`
- `view:planter` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v4\views\view_planter.png`
- `view:crypt_hall` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v4\views\view_crypt_hall.png`
- `view:gallery_arch` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v4\views\view_gallery_arch.png`
- `view:gallery` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v4\views\view_gallery.png`
- `view:courtyard_from_stair` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v4\views\view_courtyard_from_stair.png`
- `view:chapel_reverse` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v4\views\view_chapel_reverse.png`
