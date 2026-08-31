# What is in the toolkit, and when to reach for it

Read this at the start of a session that is going to build a map.

This page exists because of one measurement: Blood City's agent never imported
`aperture.py`. The module existed, was tested, solved exactly its problem — and
107 of that level's 109 openings violate the rule it enforces. The catalog was
not unqueryable. The agent never learned it was there.

So: one page, no search, no index to maintain. If you are about to write
something, look for it here first.

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

## Knowing what Blood does

Everything measured lives in `knowledge/blood/design/`. Before inventing a
number, look for it: `layers-v1.json` (stacking, and BB4), `norms-v1.json`,
`wall-thickness-v1.json` (median 544, commonest 512), `overlooks-v1.json`,
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
