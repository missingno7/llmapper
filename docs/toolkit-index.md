# What is in the toolkit, and when to reach for it

Read this at the start of a session that is going to build a map.

This page exists because of one measurement: Blood City's agent never imported
`aperture.py`. The module existed, was tested, solved exactly its problem — and
107 of that level's 109 openings violate the rule it enforces. The catalog was
not unqueryable. The agent never learned it was there.

So: one page, no search, no index to maintain. If you are about to write
something, look for it here first.

This page is the short list of things to reach for. The complete list -- every
library module and every tool, one line each, generated from the code so it
cannot go stale -- is [the module map](module-map.md). Which module owns which
kind of fact is [architecture](architecture.md).

## Before any of it: the map, the record, the body

| I want to… | Reach for | Not |
| --- | --- | --- |
| every campaign map | `corpus.campaign_maps()` | `glob("maps/blood/*.MAP")`, which matches nothing |
| one map by name | `corpus.corpus_map_path("E3M1")` | a path typed by hand |
| the maps a conversion draws Blood's vocabulary from | `corpus.named_maps()` | a directory listing |
| a record's fields, on a `DiskMap` or a `LevelIR` | `model.record_fields`, `model.record_extra` | `item.fields`, `getattr(item, "extra", None)` |
| which sector owns a wall; a sector's loops; a wall's ends | `sector_geom.wall_owners`, `sector_loops`, `wall_segment` | a loop over `wall_ptr` |
| the player's height, width and step | `player_space.PLAYER_PROFILES["blood"]` | 16960, 384, 4096 |
| every opening in a built map, classified | `aperture.observe_openings` | walking two-sided walls yourself |
| what a tile is, a mechanic is, or where Blood has one | `python -m tools.catalog find <word>` | reading maps until one turns up |
| the settings of one thing in a campaign map | `python -m tools.catalog record E3M5 sector 20` | dumping the whole map to JSON |

---

## Building a level

| I want to… | Reach for | Not |
| --- | --- | --- |
| write a level as a tree of named parts | `levelprog.LevelProgram` | building a `PlanarLayout` by hand |
| nest a building's floors inside the building | `Assembly.assembly()` | sibling rooms with a name prefix |
| give a whole area one material | `Style` on the assembly | restating picnums per room |
| put a first floor over a ground floor | `declare_layer` + `Style(layer=…)` | `declare_special`, which turns every check off |
| name a surface set | `surfaces.material("city_service")` | three raw picnums |
| join two rooms | `Assembly.connect(face, face)` | computing an edge |
| move a room to touch another | `Room.place_against` | coordinate arithmetic |

## Geometry a room is made of

| I want to… | Reach for |
| --- | --- |
| a run of steps | `vocabulary.staircase` — knows 4096 is the player's max step |
| a niche in a wall | `vocabulary.recess` |
| a curved wall | `vocabulary.arc_through`, `arc_points` |
| a repeated fixture along a wall | `prefab.alcove_run` |
| a ledge you can be shot from | `prefab.parapet` — knows the corpus rise is 1.93 bodies |
| a hole in a floor | `Room.carve` + a room filling it, joined on `hole_face` |
| a shadow, a worn patch, a rug, a painted line: a different look on part of a floor | `PlanarLayout.add_overlay(id, region, shape, floor_shade_offset=..., floor_picnum=...)`, then `bloodmap.overlays.lay(disk, compiled)` as the map's LAST change. Not a room and not a carve: the region stays one space in the source, and the finished map is cut after every pass has read it whole. A patch over the whole floor shifts it without a cut |
| light a finished map: lights of the kind each room wants, sun, lamps, a bounce, and floors and long walls cut where the light changes | `bloodmap.light_stage.run(disk, region_of, rule_for)` as the map's last change (the city: `build_skeleton.LIGHTING = "model"`, rules in `projects/blood-city/level/lights.py`, one line per kind of place; a place a study lit itself is named in its `OWN_LIGHT` and left as it is; a place's lamps are made weaker or stronger in `LAMP_SCALE`; glass on a roofed wall lets daylight in and is drawn bright). The general dials, for tuning by walking: lamp weight, base light and bounce in `light_stage.Model`, pool sharpness `daylight.LAMP_POWER`, the step a cut must make `light_stage.FLOOR_BAND`/`FLOOR_SHOW`/`WALL_BAND`; `work/lightstage/budget.py`-style counts compare a map's light cuts with the campaign's. Derived on every build and never written into the layout; cuts only shade-only sectors, appends pieces (`report["parent"]`), and writes the same bytes on any number of workers. Light kinds and what may be a texture: `bloodmap.light_kinds`; the model and its calibration: `bloodmap.daylight` |
| the sun's shadows on the ground | `bloodmap.sunlight.cast_shadows(layout, shade=, sunlit=)` before compile: masses (buildings, roofed rooms, the world's edge, raised floors) thrown away from the sun, laid as overlays. The campaign's ground step between lit and dark is 8 to 18 (median 12, `light_field`); E3M1's lit quarter sits 10 to 26 under its base |
| a wall, roof or building lower than what stands beyond it | `skyline.roof` — a sector whose floor is its top, under the common sky, then `skyline.dress_steps`. **Never lower the sky**: a low parallax ceiling hides everything above the wall (`skyline.lowered_skies` lists them) |
| the one thing taller than the city | `skyline.apron` with a raised sky, sloped for a gable |
| the end of a street, or anything with only sky behind it | a mass a few bodies up and, behind it, a parallax sector of NO height at grade: the eye goes over into sky (E3M1 s340). `bloodmap.skyline.is_sky_backing`; Blood City's `streets.end_walls`. Light the face (-8) and make it blocking |
| a door into a building whose roof is seen over | not in the low wall: `skyline.leaks_under_roofs` — the room paints into the sky. Enter through a tower or full-height block; `doors.z_motion_door(close_after=30)` for the inner leaf |
| bars across an opening | `bloodmap.glass.grille(level, spans, tile=...)` — blocking, masked, unbreakable; reports a wall whose two sides are not level, because bars share their record's scale with a step band as glass does |
| glass in a wall | never on a record that also carries a step band: its scale is the band's too. Put the pane between two volumes at one floor and ceiling (reveal, sash pocket, box); `bloodmap.glass.glaze(fit=True)` for the pane, `recess_faults` / `panes_without_a_recess` to read it back. Blood City's `level/glass.py: shopfront()` lays the frame out |
| a material that has a base (a dado, a ground storey, a kerb) | `texture_frame.frame_map(v_anchor="floor")` — one vertical origin per run, the tile's bottom row on the floor the run stands on. The default is the editor's first-wall peg, which keeps a run continuous and means nothing |
| the side of something raised in a street | it is drawn from the STREET's record: `skyline.dress_steps(level, {sector: tile}, only_from=street_sectors)`. A carriageway is the lower side, so its own `wall_picnum` is the kerb's face |

## Space over space — three techniques, and which to use

Build's sector has one floor and one ceiling. See
`projects/vertical-fragment/design/layer-conditions.md`, and BB4, which does all
three in 71 sectors.

| The space below is… | Use | Because |
| --- | --- | --- |
| enclosed (a room under a room) | **plan overlap** + `declare_layer` | the slab between them is real masonry; `bloodmap.layers` proves the engine can tell them apart |
| something you must **see into** | **room-over-room**, `roomoverroom.room_over_room` | mirror tile 504 is the only thing that draws the far side; the floor stops being solid |
| **open to the sky** | **a sprite deck**, `prefab.sprite_bridge` | a sector over an open volume cannot be separated in z; this is why the campaign uses a deck on 86% of maps |

## Openings

**Every opening goes through `aperture.py`.** An opening is a leaf plus a
mediation: `Aperture(id, leaf=Leaf(width=2.0, height=1.93), mediation="lintel")`.
The mediation is not optional when the facade stands taller than the leaf — a
tall room quietly donating its height to a doorway is the failure the type
exists to stop. `aperture.audit` reads a built map back and says what the grammar
would have required.

A doorway in a wall with thickness is its own **region**, `role="doorway"`, and
that is what gives a door a reveal. The campaign's commonest wall is 512 units.

## Rules

`rules.evaluate(disk)` in the build path, failing the build on errors.
**A rule's severity comes from how often Blood itself breaks it**, never from
judgement: under 1% is an error, under 5% a warning, otherwise a note. An
ungraded rule is not enforced at all. `tools/grade_rules.py` measures them.

Do not add a check anywhere else. If it is worth enforcing it is worth grading.

## Asking the level a question

| Question | Reach for |
| --- | --- |
| what is above and below this point | `layers.column_at` |
| can this place see that place | `layers.can_see` (2D), `sight.line_of_sight` (built map) |
| how far is this drop, does it hurt | `layers.drop_between`, `layers.fall_cost` |
| what connects to what | `reachability.portal_graph` — **portals only, no z, no step height** |
| is this opening walkable | `player_space` |
| does this map stack safely | `layers.report` |
| what is *around* this object, without naming it | `relations.extract_relations` — object-scale relations, frame-independent |
| which sectors here are worth looking at | `relations.sprite_dense_seeds` |
| what surrounds a tile I have a name for | `anchors.mine_anchor` — and it tells you whether that context means anything (enrichment) |
| is this a bundle or props in a heap | `anchors.compare_placements` — support, never sprite count |
| how much free floor does this fixture need | `player_space.check_clearance` — an access front; 73% of campaign counters back onto something |
| did my change do what I said it would | write `hypothesis.json` first, render the same poses before and after, then `python -m tools.judge_experiment <dir>` — sky share, changed pixels, drawn sky seams, every map and frame hashed |
| which PART of my change did the work | `python -m tools.whatif built.MAP -o variant.MAP --edits edits.json` — a variant of a built map with one thing unlit, repainted or removed, in a second. Render the variants beside the full build and the before and hand all of them, unlabelled, to a blind reviewer. Blood City writes `<map>.tags.json` so an edit can say `"intent": "shop_display"` |
| does every sprite fit where it was put (sunk, through a ceiling, squeezed, covering another) | `python -m tools.sprite_fit MAP` — a lint of the built map as the renderer draws it; `--rates maps...` for the campaign's own numbers, which are the thresholds. `bloodmap.placement.drawn_extent` is the box; the city build prints the lint and `tests/test_sprite_fit.py` holds it |
| what do the goods in Blood's town maps stand ON | `python -m tools.mine_stands [maps...]` — every indoor standing thing by what is under it (floor, island, ledge, niche, floating), from the sector and its neighbours; rise, head, size and tiles of the fixtures. Blood City's `fixtures.BAR` and `fixtures.shelf_niche` are built on it |
| what do Blood's own town maps dress a place with, and how is each thing set down | `python -m tools.mine_city_assets [maps...]` — every decoration tile in a named handful of maps, which maps, indoors or out, alignment, and the repeats, cstat, shade, palette, type, status and height it is given; a contact sheet of the ones a built map does not use. Blood City's `level/goods.py` is a plan by place built on it |
| how complex are these interiors, against the campaign's | `python -m tools.city_profile --interiors <maps...>` — per interior: floor and ceiling heights, floor range in bodies, floor and wall tiles, shade spread, slopes. E3M1 is the target; the largest gap is light |
| how does another Build game (or a campaign map) do this, in terms I can use | `python -m tools.city_profile <maps...>` — one list of structural questions (street-wall heights, kerb, pavement, glass and its records, openings, sky backings, light) answered in bodies and shares, so a Duke map, a Blood map and a built map are columns of one table. Tiles and raw coordinates do not cross; ratios do |
| stand in a Duke Nukem 3D map and look | `python -m tools.duke_view <map> -o DIR [--pose name:x,y,tx,ty] [--sectors a,b]` — a viewing copy in Blood's format (nothing scaled), Duke's ART, and Duke's own palette, shade table and palette swaps in an archive the observer can read, through the same observer. Shape, colour and light as authored are Duke's; the sky is not. Never a conversion |
| how has something recognisable been built before, and did it read | `knowledge/blood/design/visual-construction-atlas-v1.json` — native facts, derived counts and viewers' readings kept apart, with a status per record |
| is there a way from the start to this place | `conditional.build_graph` — gates and what works them; Blood City's `walk_static.py` renders the chain. **A reading of the map, not a walk** |

## Knowing what Blood does

Everything measured lives in `knowledge/blood/design/`. Before inventing a
number, look for it: `layers-v1.json` (stacking, and BB4), `norms-v1.json`,
`wall-thickness-v1.json` (median 528, commonest 512), `overlooks-v1.json`,
`apertures-v1.json`, `sprite-heights-v1.json`, `stacks-v1.json`,
`surface-palettes-v1.json`, `rules-v1.json` (the grades), `e3m8-reference-v1.json`.

Units: one body width is **384**; one standing human is **16,960**. Not `0x1600`
— that is an offset from a sprite's centre, and treating it as a height put this
project's camera at chest level for months.

## Before you say it works

It has to load in the engine and be walked. See the `nblood-map-smoke-test`
memory, and `tools/botrun.sh <map> <tag>`.

This is not a formality. The monastery passed `validate_map`, `validate_authored_level`
and all 13 hard gates, and took SIGSEGV. `roomoverroom.py` was finished,
documented from the engine source, unit-tested, and put its markers on a statnum
Blood deletes at load — for as long as it had never built a map. **A tool that
has not changed a map is a hypothesis, not an asset.**
