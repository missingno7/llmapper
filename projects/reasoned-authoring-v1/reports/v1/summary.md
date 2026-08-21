# Iteration v1

- source: `projects/reasoned-authoring-v1/level/candidate_v1.py`
- MAP sha256: `12128af3e0f8b96a7a8f6de9c7621b6faa55b07ec4c87279c99ca839e3914f12`
- counts: {'sectors': 31, 'walls': 167, 'sprites': 5, 'regions': 31, 'connections': 34}
- deterministic compile: True

## Hard gates

- **PASS** `native_structure_valid` — native Blood validation reports no errors
- **PASS** `authored_geometry_valid` — 0 authored error(s), 0 warning(s)
- **PASS** `no_unintended_overlaps` — no unintended XY footprint overlap
- **PASS** `no_unresolved_boundary_contacts` — no T-junctions, partial collinear overlaps, or proper crossings
- **PASS** `intended_adjacency_realized` — every intended adjacency became a portal and no portal is unintended
- **PASS** `geometry_conservation` — 132 source edges -> 167 emitted; split 35
- **PASS** `portals_realized` — 34 authored connections realized
- **PASS** `player_start_valid` — start sector:0 of 31
- **PASS** `player_relative_clearance` — start clear height 22528 = 4.0 player heights
- **PASS** `required_reachability` — 29/29 mandatory regions reachable
- **PASS** `exit_reachable` — an exit is reachable under the declared progression
- **PASS** `object_attachment_valid` — sprite attachments and use poses are consistent
- **PASS** `deterministic_emission` — two independent compiles produced identical bytes
- **PASS** `nblood_load_smoke` — NBlood load smoke pass; revisions=['rlocal-agtst10']

## Independently derived hierarchy

- assemblies 1, spaces 14, singletons 9, detail groups 4
- cross-space connections 14, vertical overlap relations 0

### Authored assembly vs derived spaces

| authored | sectors | derived spaces | dominant share | singletons |
| --- | --- | --- | --- | --- |
| arrival approach | 3 | 1 | 1.0 | 0 |
| arrival courtyard | 8 | 1 | 1.0 | 0 |
| chapel | 5 | 2 | 0.9677 | 1 |
| lower crypt | 8 | 3 | 0.8765 | 1 |
| optional ossuary | 2 | 2 | 0.9091 | 2 |
| upper gallery | 3 | 3 | 0.9245 | 3 |
| exit chamber | 2 | 2 | 0.9375 | 2 |

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
  - {"area_ratio": 42.3333, "clear_height_delta": 73216, "dest_area": 149815296.0, "dest_clear_height": 90112, "floor_delta": 0, "source_area": 3538944.0, "source_clear_height": 16896}
- `probe:arch_contrast` (transition) -> **pass** — 
  - {"area_ratio": 24.5, "clear_height_delta": 22528, "dest_area": 57802752.0, "dest_clear_height": 33792, "floor_delta": 0, "source_area": 2359296.0, "source_clear_height": 11264}
- `probe:crypt_contrast` (transition) -> **pass** — 
  - {"area_ratio": 0.1969, "clear_height_delta": -77824, "dest_area": 29491200.0, "dest_clear_height": 12288, "floor_delta": 12288, "source_area": 149815296.0, "source_clear_height": 90112}
- `probe:gallery_contrast` (transition) -> **pass** — 
  - {"area_ratio": 0.3858, "clear_height_delta": -56320, "dest_area": 57802752.0, "dest_clear_height": 33792, "floor_delta": -11520, "source_area": 149815296.0, "source_clear_height": 90112}
- `probe:ossuary_reachable_while_shut` (access) -> **fail** — sector:19 is not reachable from sector:0 under the declared world state
- `probe:gallery_choices` (escape) -> **pass** — 
  - {"blocked_exit_count": 0, "blocked_exits": [], "dead_end_depth": 0, "viable_exit_count": 3, "viable_exits": [{"edge": "portal:129", "sector": "sector:23", "status": "open"}, {"edge": "portal:137", "sector": "sector:25", "status": "open"}, {"edge": "portal:134", "sector": "sector:29", "status": "open_via_world_state"}]}
- `probe:revisit_after_crypt_gate` (revisit) -> **pass** — 
  - {"newly_reachable_count": 8, "newly_reachable_sectors": ["sector:10", "sector:11", "sector:12", "sector:13", "sector:14", "sector:15", "sector:16", "sector:17"], "reachable_after_count": 27, "reachable_before_count": 19, "still_unreachable_count": 4}
- `probe:courtyard_choices` (escape) -> **pass** — 
  - {"blocked_exit_count": 0, "blocked_exits": [], "dead_end_depth": 0, "viable_exit_count": 6, "viable_exits": [{"edge": "portal:11", "sector": "sector:2", "status": "open"}, {"edge": "portal:37", "sector": "sector:4", "status": "open"}, {"edge": "portal:32", "sector": "sector:5", "status": "open_via_world_state"}, {"edge": "portal:23", "sector": "sector:10", "status": "open_via_world_state"}, {"edge": "portal:18", "sector": "sector:20", "status": "open"}, {"edge": "portal:20", "sector": "sector:28", "status": "open"}]}
- `probe:gatehouse_choices` (escape) -> **pass** — 
  - {"blocked_exit_count": 0, "blocked_exits": [], "dead_end_depth": 0, "viable_exit_count": 2, "viable_exits": [{"edge": "portal:7", "sector": "sector:1", "status": "open"}, {"edge": "portal:11", "sector": "sector:3", "status": "open"}]}
- `probe:chapel_choices` (escape) -> **pass** — 
  - {"blocked_exit_count": 0, "blocked_exits": [], "dead_end_depth": 0, "viable_exit_count": 4, "viable_exits": [{"edge": "portal:43", "sector": "sector:5", "status": "open_via_world_state"}, {"edge": "portal:46", "sector": "sector:7", "status": "open"}, {"edge": "portal:50", "sector": "sector:8", "status": "open"}, {"edge": "portal:48", "sector": "sector:9", "status": "open"}]}
- `probe:crypt_choices` (escape) -> **pass** — 
  - {"blocked_exit_count": 0, "blocked_exits": [], "dead_end_depth": 0, "viable_exit_count": 3, "viable_exits": [{"edge": "portal:84", "sector": "sector:14", "status": "open"}, {"edge": "portal:96", "sector": "sector:16", "status": "open"}, {"edge": "portal:93", "sector": "sector:17", "status": "open"}]}

## ART and visual composition

- catalog: loaded
- unresolved assets: 0
- visually empty derived spaces: 10
- decorative distribution: 0.4 of 5 space sprites in one space
- identical dominant room surfaces:
  - ['assembly:chapel', 'assembly:exit'] -> {'floor': 294, 'ceiling': 416, 'wall': 5}
  - ['assembly:crypt', 'assembly:ossuary'] -> {'floor': 1097, 'ceiling': 1097, 'wall': 1097}

## Corpus-relative scale and shape

| derived space | player areas | clear player heights | height pct vs same-size corpus |
| --- | --- | --- | --- |
| assembly:001/space:002 | 1120.0 | 15.5 | 59.0 |
| assembly:001/space:011 | 392.0 | 6.0 | 19.1 |
| assembly:001/space:007 | 284.0 | 2.19 | 2.5 |
| assembly:001/space:004 | 240.0 | 5.66 | 11.5 |
| assembly:001/space:014 | 120.0 | 4.0 | 4.5 |
| assembly:001/space:001 | 104.0 | 3.46 | 3.9 |
| assembly:001/space:009 | 80.0 | 2.0 | 0.9 |
| assembly:001/space:006 | 32.0 | 3.0 | 4.4 |
| assembly:001/space:010 | 16.0 | 2.0 | 2.5 |
| assembly:001/space:012 | 16.0 | 2.0 | 2.5 |

| shape metric | candidate | corpus percentile |
| --- | --- | --- |
| orthogonal_length_fraction | 1.0 | 100.0 |
| diagonal_length_fraction | 0.0 | 0.0 |
| orientation_5deg_bins_occupied | 2.0 | 0.0 |
| orientation_diversity | 0.0556 | 0.0 |
| chamfer_fraction | 0.0 | 0.0 |
| segmented_arc_chain_count | 0.0 | 2.4 |
| rectangular_sector_fraction | 0.7419 | 100.0 |
| convex_sector_fraction | 1.0 | 100.0 |
| median_outer_vertex_count | 4.0 | 59.5 |

- sprite scale: measured, 0 oversized decoration(s)

### Scale and shape findings

- `space_much_lower_than_corpus_for_its_size` — derived space assembly:001/space:001 covers 104 player areas but is only 3.46 player heights clear (area-weighted), at the 3.9 percentile of the 1612 corpus sectors of comparable footprint
- `space_much_lower_than_corpus_for_its_size` — derived space assembly:001/space:006 covers 32 player areas but is only 3.0 player heights clear (area-weighted), at the 4.4 percentile of the 2845 corpus sectors of comparable footprint
- `space_much_lower_than_corpus_for_its_size` — derived space assembly:001/space:007 covers 284 player areas but is only 2.19 player heights clear (area-weighted), at the 2.5 percentile of the 652 corpus sectors of comparable footprint
- `space_much_lower_than_corpus_for_its_size` — derived space assembly:001/space:009 covers 80 player areas but is only 2.0 player heights clear (area-weighted), at the 0.9 percentile of the 1903 corpus sectors of comparable footprint
- `space_much_lower_than_corpus_for_its_size` — derived space assembly:001/space:014 covers 120 player areas but is only 4.0 player heights clear (area-weighted), at the 4.5 percentile of the 1430 corpus sectors of comparable footprint
- `shape_outside_corpus_mass` — orthogonal_length_fraction is 1.0, at the 100.0 percentile of 42 original maps
- `shape_outside_corpus_mass` — diagonal_length_fraction is 0.0, at the 0.0 percentile of 42 original maps
- `shape_outside_corpus_mass` — orientation_5deg_bins_occupied is 2.0, at the 0.0 percentile of 42 original maps
- `shape_outside_corpus_mass` — orientation_diversity is 0.0556, at the 0.0 percentile of 42 original maps
- `shape_outside_corpus_mass` — chamfer_fraction is 0.0, at the 0.0 percentile of 42 original maps
- `shape_outside_corpus_mass` — segmented_arc_chain_count is 0.0, at the 2.4 percentile of 42 original maps
- `shape_outside_corpus_mass` — rectangular_sector_fraction is 0.7419, at the 100.0 percentile of 42 original maps

## Render

- capture status: pass
- `view:start` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v1\views\view_start.png`
- `view:gate_approach` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v1\views\view_gate_approach.png`
- `view:gatehouse` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v1\views\view_gatehouse.png`
- `view:courtyard_center` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v1\views\view_courtyard_center.png`
- `view:chapel_interior` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v1\views\view_chapel_interior.png`
- `view:chapel_apse` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v1\views\view_chapel_apse.png`
- `view:crypt_hall` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v1\views\view_crypt_hall.png`
- `view:gallery_arch` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v1\views\view_gallery_arch.png`
- `view:gallery` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v1\views\view_gallery.png`
- `view:courtyard_from_stair` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v1\views\view_courtyard_from_stair.png`
- `view:chapel_reverse` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v1\views\view_chapel_reverse.png`
