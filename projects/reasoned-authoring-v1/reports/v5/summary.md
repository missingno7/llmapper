# Iteration v5

- source: `projects/reasoned-authoring-v1/level/candidate_v5.py`
- MAP sha256: `8fb5288e73833498ed487636f8446b69967dc328b968d6ef396101b254b1eee9`
- counts: {'sectors': 38, 'walls': 295, 'sprites': 60, 'regions': 38, 'connections': 57}
- deterministic compile: True

## Hard gates

- **PASS** `native_structure_valid` — native Blood validation reports no errors
- **PASS** `authored_geometry_valid` — 0 authored error(s), 0 warning(s)
- **PASS** `no_unintended_overlaps` — no unintended XY footprint overlap
- **PASS** `no_unresolved_boundary_contacts` — no T-junctions, partial collinear overlaps, or proper crossings
- **PASS** `intended_adjacency_realized` — every intended adjacency became a portal and no portal is unintended
- **PASS** `geometry_conservation` — 256 source edges -> 295 emitted; split 39
- **PASS** `portals_realized` — 57 authored connections realized
- **PASS** `player_start_valid` — start sector:0 of 38
- **PASS** `player_relative_clearance` — start clear height 33792 = 6.0 player heights
- **PASS** `required_reachability` — 36/36 mandatory regions reachable
- **PASS** `exit_reachable` — an exit is reachable under the declared progression
- **PASS** `object_attachment_valid` — sprite attachments and use poses are consistent
- **PASS** `deterministic_emission` — two independent compiles produced identical bytes
- **PASS** `nblood_load_smoke` — NBlood load smoke pass; revisions=['rlocal-agtst10']

## Independently derived hierarchy

- assemblies 1, spaces 16, singletons 9, detail groups 10
- cross-space connections 34, vertical overlap relations 0

### Authored assembly vs derived spaces

| authored | sectors | derived spaces | dominant share | singletons |
| --- | --- | --- | --- | --- |
| arrival approach | 3 | 1 | 1.0 | 0 |
| arrival courtyard | 8 | 2 | 0.9663 | 1 |
| chapel | 8 | 2 | 0.9601 | 1 |
| lower crypt | 10 | 4 | 0.821 | 2 |
| optional ossuary | 2 | 2 | 0.9048 | 2 |
| upper gallery | 4 | 3 | 0.9333 | 2 |
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
  - {"area_ratio": 36.643, "clear_height_delta": 61952, "dest_area": 151290244.0, "dest_clear_height": 90112, "floor_delta": 0, "source_area": 4128768.0, "source_clear_height": 28160}
- `probe:arch_contrast` (transition) -> **pass** — 
  - {"area_ratio": 27.6132, "clear_height_delta": 45056, "dest_area": 65147677.0, "dest_clear_height": 67584, "floor_delta": 0, "source_area": 2359296.0, "source_clear_height": 22528}
- `probe:crypt_contrast` (transition) -> **pass** — 
  - {"area_ratio": 0.1733, "clear_height_delta": -61952, "dest_area": 26219293.0, "dest_clear_height": 28160, "floor_delta": 12288, "source_area": 151290244.0, "source_clear_height": 90112}
- `probe:gallery_contrast` (transition) -> **pass** — 
  - {"area_ratio": 0.4306, "clear_height_delta": -22528, "dest_area": 65147677.0, "dest_clear_height": 67584, "floor_delta": -12288, "source_area": 151290244.0, "source_clear_height": 90112}
- `probe:ossuary_reachable_while_shut` (access) -> **fail** — sector:23 is not reachable from sector:0 under the declared world state
- `probe:gallery_choices` (escape) -> **pass** — 
  - {"blocked_exit_count": 0, "blocked_exits": [], "dead_end_depth": 0, "viable_exit_count": 4, "viable_exits": [{"edge": "portal:226", "sector": "sector:27", "status": "open"}, {"edge": "portal:246", "sector": "sector:29", "status": "open"}, {"edge": "portal:236", "sector": "sector:33", "status": "open_via_world_state"}, {"edge": "portal:248", "sector": "sector:36", "status": "open"}]}
- `probe:revisit_after_crypt_gate` (revisit) -> **pass** — 
  - {"newly_reachable_count": 10, "newly_reachable_sectors": ["sector:13", "sector:14", "sector:15", "sector:16", "sector:17", "sector:18", "sector:19", "sector:20", "sector:21", "sector:35"], "reachable_after_count": 33, "reachable_before_count": 23, "still_unreachable_count": 5}
- `probe:courtyard_choices` (escape) -> **pass** — 
  - {"blocked_exit_count": 0, "blocked_exits": [], "dead_end_depth": 0, "viable_exit_count": 6, "viable_exits": [{"edge": "portal:13", "sector": "sector:2", "status": "open"}, {"edge": "portal:68", "sector": "sector:4", "status": "open"}, {"edge": "portal:44", "sector": "sector:5", "status": "open_via_world_state"}, {"edge": "portal:31", "sector": "sector:13", "status": "open_via_world_state"}, {"edge": "portal:26", "sector": "sector:24", "status": "open"}, {"edge": "portal:28", "sector": "sector:32", "status": "open"}]}
- `probe:gatehouse_choices` (escape) -> **pass** — 
  - {"blocked_exit_count": 0, "blocked_exits": [], "dead_end_depth": 0, "viable_exit_count": 2, "viable_exits": [{"edge": "portal:9", "sector": "sector:1", "status": "open"}, {"edge": "portal:13", "sector": "sector:3", "status": "open"}]}
- `probe:chapel_choices` (escape) -> **pass** — 
  - {"blocked_exit_count": 0, "blocked_exits": [], "dead_end_depth": 0, "viable_exit_count": 5, "viable_exits": [{"edge": "portal:86", "sector": "sector:5", "status": "open_via_world_state"}, {"edge": "portal:89", "sector": "sector:7", "status": "open"}, {"edge": "portal:94", "sector": "sector:8", "status": "open"}, {"edge": "portal:92", "sector": "sector:9", "status": "open"}, {"edge": "portal:91", "sector": "sector:10", "status": "open"}]}
- `probe:crypt_choices` (escape) -> **pass** — 
  - {"blocked_exit_count": 0, "blocked_exits": [], "dead_end_depth": 0, "viable_exit_count": 5, "viable_exits": [{"edge": "portal:155", "sector": "sector:17", "status": "open"}, {"edge": "portal:184", "sector": "sector:19", "status": "open"}, {"edge": "portal:179", "sector": "sector:20", "status": "open"}, {"edge": "portal:172", "sector": "sector:21", "status": "open"}, {"edge": "portal:170", "sector": "sector:35", "status": "open"}]}

## ART and visual composition

- catalog: loaded
- unresolved assets: 0
- visually empty derived spaces: 6
- decorative distribution: 0.2167 of 60 space sprites in one space

## Corpus-relative scale and shape

| derived space | player areas | clear player heights | height pct vs same-size corpus |
| --- | --- | --- | --- |
| assembly:001/space:002 | 1074.0 | 15.51 | 59.4 |
| assembly:001/space:013 | 447.81 | 11.92 | 56.3 |
| assembly:001/space:008 | 256.81 | 4.45 | 8.6 |
| assembly:001/space:005 | 192.62 | 8.58 | 35.4 |
| assembly:001/space:016 | 119.0 | 7.9 | 39.7 |
| assembly:001/space:001 | 104.0 | 5.27 | 10.5 |
| assembly:001/space:011 | 76.0 | 3.0 | 3.5 |
| assembly:001/space:003 | 37.5 | 14.91 | 89.0 |
| assembly:001/space:007 | 32.0 | 4.0 | 5.7 |
| assembly:001/space:009 | 16.0 | 3.91 | 6.6 |

| shape metric | candidate | corpus percentile |
| --- | --- | --- |
| orthogonal_length_fraction | 0.8264 | 88.1 |
| diagonal_length_fraction | 0.0898 | 52.4 |
| orientation_5deg_bins_occupied | 17.0 | 4.8 |
| orientation_diversity | 0.4722 | 4.8 |
| chamfer_fraction | 0.1849 | 97.6 |
| segmented_arc_chain_count | 15.0 | 31.0 |
| rectangular_sector_fraction | 0.6316 | 100.0 |
| convex_sector_fraction | 0.9737 | 100.0 |
| median_outer_vertex_count | 4.0 | 59.5 |

- sprite scale: measured, 0 oversized decoration(s)

### Scale and shape findings

- `space_much_lower_than_corpus_for_its_size` — derived space assembly:001/space:007 covers 32 player areas but is only 4.0 player heights clear (area-weighted), at the 5.7 percentile of the 2845 corpus sectors of comparable footprint
- `space_much_lower_than_corpus_for_its_size` — derived space assembly:001/space:008 covers 257 player areas but is only 4.45 player heights clear (area-weighted), at the 8.6 percentile of the 736 corpus sectors of comparable footprint
- `space_much_lower_than_corpus_for_its_size` — derived space assembly:001/space:011 covers 76 player areas but is only 3.0 player heights clear (area-weighted), at the 3.5 percentile of the 1941 corpus sectors of comparable footprint
- `shape_outside_corpus_mass` — orientation_5deg_bins_occupied is 17.0, at the 4.8 percentile of 42 original maps
- `shape_outside_corpus_mass` — orientation_diversity is 0.4722, at the 4.8 percentile of 42 original maps
- `shape_outside_corpus_mass` — rectangular_sector_fraction is 0.6316, at the 100.0 percentile of 42 original maps

## Render

- capture status: fail
- `view:start` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v5\views\view_start.png`
- `view:gate_approach` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v5\views\view_gate_approach.png`
- `view:gatehouse` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v5\views\view_gatehouse.png`
- `view:courtyard_center` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v5\views\view_courtyard_center.png`
- `view:courtyard_sky` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v5\views\view_courtyard_sky.png`
- `view:nave_vault` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v5\views\view_nave_vault.png`
- `view:crypt_vault` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v5\views\view_crypt_vault.png`
- `view:gallery_vault` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v5\views\view_gallery_vault.png`
- `view:courtyard_corner` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v5\views\view_courtyard_corner.png`
- `view:chapel_interior` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v5\views\view_chapel_interior.png`
- `view:chapel_apse` fail -> `None`
- `view:chancel_stair` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v5\views\view_chancel_stair.png`
- `view:planter` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v5\views\view_planter.png`
- `view:crypt_hall` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v5\views\view_crypt_hall.png`
- `view:gallery_arch` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v5\views\view_gallery_arch.png`
- `view:gallery` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v5\views\view_gallery.png`
- `view:courtyard_from_stair` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v5\views\view_courtyard_from_stair.png`
- `view:chapel_reverse` pass -> `D:\Games\DOS\llmapper\projects\reasoned-authoring-v1\reports\v5\views\view_chapel_reverse.png`
