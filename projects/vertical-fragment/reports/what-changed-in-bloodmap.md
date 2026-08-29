# What the pilot changed in bloodmap

The fragment is not the deliverable. This is.

The rule the pilot was built under was: **no local workarounds — when the pilot
cannot express something, the fix goes into `bloodmap`, not into the pilot.** The
list below is what that produced. Twelve changes landed upstream; the fragment
itself contains no geometry helper that a second project could not reach.

If this list were short, the pilot was built too carefully. It is not short, and
two of the entries are corrections to things this project believed and had
written down.

---

## A. The one new thing

### 1. `bloodmap/layers.py` — space that stacks, and the conditions that let it

New module, 700 lines. A **layer** is a named planar arrangement with its own
height band. Overlap within a layer stays forbidden; overlap between layers is
permitted and checked.

`RegionSpec.layer` already existed as a field. It was written into a dict by
`to_dict` and read by nothing — a label with no consequences. It now means
something.

What it enforces, each with its measured campaign rate from
`knowledge/blood/design/layers-v1.json`:

| condition | what it catches | campaign violates |
| --- | --- | --- |
| `layer-undeclared` | a region in a band nobody declared | — |
| `layer-band-escape` | a region taller than the layer it claims | — |
| `layer-overlap-within` | two rooms of one layer sharing ground | — |
| `layer-bands-intersect` | two "layers" at the same height sharing ground | — |
| `layer-overlap-unresolved` | an overlap the engine cannot resolve at all | **0.038%** (1 pair of 2,614) |
| `layer-overlap-close` | resolved by bands alone, where movement cannot read them | 0.19% |
| `layer-overlap-in-one-view` | one vantage holding both halves | — |
| `layer-owner-over-overlap` | a marker whose sector we have to guess | — |

Plus the three spatial queries the conditions needed and nothing more:
`column_at` (what is above and below a point, with the air between),
`can_see` (2D sightline between two regions), and `drop_between` (how far, does
it hurt, is it lethal). Each was written on the day it had a caller.

### 2. The planar pipeline became layer-aware — `planar_layout.py`

Four surgical changes, all inert when no layer is declared:

- `declared_joins()` / `separate_arrangements()` — two regions of different
  declared layers are two plans on one sheet of paper unless the author has
  explicitly joined them.
- `_validate_regions` no longer refuses a cross-layer overlap outright.
- `_collect_split_points` no longer splits one layer's edges against another's.
  Without this, the street's kerb inserted a vertex into the cellar's wall.
- `_pair_portals` no longer reports cross-layer coincident walls as unexplained
  unpaired portals.
- `compile()` runs `layers.enforce` and carries the approved overlaps forward.

`declare_layer` was added to both `PlanarLayout` and `LevelProgram`.

---

## B. Corrections — things this project believed that are not true

### 3. Player starts and teleport destinations are not lookups

The directive this pilot was given states that player start, teleport
destinations and spawn points "are the cold lookups that reach the arbitrary
scan". **In Blood they are not lookups at all.** `warpInit` copies
`pSprite->sectnum` straight off the start marker (`warp.cpp:62-70`);
`OperateTeleport` calls `ChangeSpriteSect(nSprite, pDest->sectnum)`
(`triggers.cpp:1577`); `dbLoadMap` trusts every sprite's recorded sector without
recomputing it (`db.cpp:1195`).

The hazard is real but it is **ours**: whatever sector our compiler writes into
that sprite is what the engine believes forever, and our compiler resolves a
placement's owner in plan. The condition survives, restated as a toolchain
invariant, and is enforced as `layer-owner-over-overlap`.

### 4. Portal separation is not a hop count, and five is not the number

This is the correction that mattered most, because the first version of the rule
fired on every stacked building in the fragment — eighteen findings, all false.
A rule that cannot be satisfied by a correct map is the failure mode this project
already has a memory about.

What the engine actually does:

- `clipmove_compat` (`clip.cpp:1112`) resolves the mover's sector from
  `clipsectorlist` **in plan alone**, z never consulted.
- That list is seeded with the mover's *own* sector (`clip.cpp:1508`) and scanned
  **in order** (`clip.cpp:1114`), so index 0 wins whenever it still contains the
  point. A mover is only ever misplaced just after leaving a sector — and then
  the right answer is a portal neighbour, at depth 1 of the walk. For a wrong
  sector to win it must arrive no later. **Two hops, not five.**
- The walk is bounded by a *box* about the mover (`clip.cpp:1500`) that no wall
  outside it is even examined through (`clip.cpp:1574`). `MAXCLIPDIST` is 1024
  (`engine_priv.h:19`); a player's `walldist` is `0x30 << 2` plus 16
  (`dude.cpp:1581`, `actor.cpp:4593`). The radius is about **2,264 units** — a
  distance, not a hop count.

So two rooms one above the other are zero apart in plan and still perfectly safe
when the only way between them goes out to a stairwell and back, which is how a
building is built. The measured campaign rate moved accordingly:

| predicate | campaign rate |
| --- | --- |
| the quoted "median 6 hops, q1 5" | not what the corpus says — median is **12**, q1 **9** |
| under 5 hops (first attempt) | 0.8% — a warning |
| **≤2 hops and inside one clip box, with clashing bands** | **0.038%, one pair in one map — an error** |

The single campaign violation is E1M1's sectors 45 and 55, and it is not a second
storey: 55's wall loop revisits `(11776, 36608)` three times and carries
zero-width spurs, so the crossings the predicate finds are against a degenerate
outline.

Both attempts are kept in the module, one enforced and one reported, because the
hop distribution is still the right thing to compare a level against — it just
is not the thing that decides safety.

---

## C. Installed, not built — six things that existed and were unused

### 5. `roomoverroom.py` in a build path for the first time — and it was broken

The malt hatch is a `stack` pair: mirror tile 504 on both surfaces, two markers
sharing a link id. It works because `GetZRange` (`gameutil.cpp:726`) replaces a
sector's floor with the linked sector's floor whenever `gUpperLink` is set, so
the hatch floor stops being solid and the player falls through and lands below.

**The first build shipped the mirror tiles and no link at all.** The owner
played it and said so. The module put its markers on `kStatMarker` — statnum 10
— on the stated grounds that "markers live on the decoration list and are never
drawn". The intent was right and the number was wrong: the decoration list is
statnum **0**, and statnum 10 is the marker list, which Blood *culls*.
`PropagateMarkerReferences` (`db.cpp:681`) walks every sprite on statnum 10 and
`DeleteSprite`s any whose type is not Off, On, Axis or WarpDest. It runs inside
`dbLoadMap` at `db.cpp:1325`; `warpInit` runs at `blood.cpp:750`. The markers
were destroyed before anything could pair them.

Nothing in the map file looks wrong. Both surfaces carry tile 504, both markers
carry their XSprite and their matching `data_1`, every validator passes. The only
way to find it is to walk the map — which is the same lesson this project already
has a memory about, arriving through a different door.

Checked against the corpus afterwards: **all 502 link markers in the campaign are
on statnum 0**, across all four families, without exception. The same census
fixed two more fields the module had guessed — cstat (128, not 32768) and the
marker tiles (2332 upper / 2331 lower, unanimous, not 3997).

The proof it now works is in the bot's own world model. Before the fix, the yard
region was `blood_sectors=[0,1,2,...]` — the hatch merged into the yard as
ordinary floor. After it, the yard is `[0,2,...]` with a hole where the hatch is,
and the bot's trajectory inside the hatch footprint runs from z −85 down to
37,777: it falls through into the cellar.

That is the pilot's own thesis turned on the pilot's own toolkit. `roomoverroom.py`
was finished, documented from the engine source, tested, and wrong, because it
had never built a map. **A tool that has not changed a map is a hypothesis, not
an asset.**

### 6. `prefab.sprite_bridge` in a build path for the first time

The gantry, seven blocking floor-aligned slabs of picnum 256 — the same tile
BB4 uses for its nine. The bot walked 341 trajectory points on it.

### 7. `rules.evaluate` in the build path, failing the build

`projects/vertical-fragment/level/build.py` runs it and returns non-zero on any
error. All 23 registered rules are graded. It earned its place immediately:
`wall-between-rooms-is-not-paper` caught four walls where the store's floor and
its stairwell were butted together with **16 units** of stone between two rooms
at the same height. The fix was a real 512 wall with a doorway through it, which
is what the campaign does.

### 8. `levelprog`'s nesting, used to its depth

`Assembly.assembly()` existed and was unused. The fragment's tree is 39 nodes at
**depth 3** — level → building → floor → room — against Blood City's 201 nodes at
depth 2, where a building's storeys were siblings told apart by a name prefix.
Containment is real: `brewhouse/first/loft` is inside `brewhouse/first` is inside
`brewhouse`.

### 9. The vocabulary constructors as the authoring surface

Three staircases through `vocabulary.staircase` — thirty of the fragment's
fifty-seven sectors. Ten equal steps of 4096 each, which the constructor already
knew was the player's maximum step and the corpus's commonest rise.

### 10. `aperture.py` audited in the build path

Every opening in the fragment is a doorway *region* in a wall with real
thickness, and `aperture.audit` runs over the built map. The fragment reports no
violations. (Honest caveat: the doorways are built as regions rather than through
`aperture.pierce`, for the reason in finding #4 below.)

---

## D. Smaller fixes the fragment forced

### 11. `Style.layer`, and structures inheriting it

`Style` carries `floor_z` and `clear_height` down the tree; `layer` now travels
with them, because a layer is a property of a *place* — the whole first floor of
a building is upper — and stating it once on the assembly is the only way it
stays true as rooms are added.

`LevelProgram._build_structure` passes the room's layer into the structure it
grows. Without it every step of a staircase landed in the default layer and the
level was refused for standing somewhere it had never been declared.

### 12. A room names its own faces

`Room.__init__` now derives compass faces from its own outline when none are
given — `rect_room` always did this, and a room with a *shape* had to be handed a
face map. Handing it the rectangle's map (four names against the first four
indices) silently named a chamfer "south" and put a door on the diagonal. That is
exactly what happened, and the error surfaced 1,500 units away as a wall too
short for its opening.

### 13. `permitted_band` — connectors span, rooms do not

A stair between two layers belongs to neither: it stands on the lower floor and
is open to the upper ceiling. A region whose role is a connector (`stair`,
`doorway`, `lift`, `ramp`) may reach into the bands of the layers it joins, and
may reach *through* other connectors, because a ten-step stair is one object cut
into ten sectors and the middle steps touch nothing else. An ordinary room
borrows only from what it directly touches.

An open sector is not roofed by the layer above it either — the sky belongs to no
layer — so a yard may be as tall as the buildings round it and nothing else may.

### 14. The geometry audit learned about layers

`audit_geometry` gained `separate_arrangements`. Every question on that page is
about two walls' relationship *in plan*, and two sectors at different heights
have no plan in common: a kerb crossing over a cellar wall is not a T-junction,
and a loft's doorjamb landing halfway along the wall of the room below is not an
unsplit wall. Four checks now consult it, and `sub_body_wall_fragment` also
learned to exempt *declared* pairs — every other check on the page already did,
which is why a level could satisfy the layer conditions and still be refused for
the exact geometry those conditions exist to permit.

### 15. `find_overlaps` catches identical footprints

`polygon_relation` reports two identical outlines as `exactly_shared_boundary`,
because neither has a vertex strictly inside the other. That is the commonest
overlap there is — a loft directly over the room it belongs to — and it was
being missed. Two rooms with one footprint share all of their ground, not none.

### 15b. A plan point stops having an answer once layers exist

Found in this project's own tooling, rendering the acceptance frames. Every
pose-resolution helper here — `look.py`'s `sector_at`, and `viewpoints._contains`
behind it — asks "which sector is at (x, y)". With layers the answer is three
sectors, and the first version put the malt loft's camera on the mash floor
beneath it and the cellar's camera in the yard above it.

This is the same fault `layers.check` refuses under `layer-owner-over-overlap`,
appearing on our own side of the boundary rather than the engine's, and it will
appear again anywhere a tool resolves a point in plan. A standing pose is
(x, y, **z**), the way `inside_z_p` asks it. `look.py` now names a band per pose
and resolves against that band's floor.

The gantry is the case that has no sector answer at all: it stands in the yard's
sector at the upper band's height, because a blocking floor-aligned sprite is a
surface with no sector behind it. It has to be told its height.

### 16. The measured city palette moved into `bloodmap/surfaces.py`

Twenty-one materials — the E3M1 / DWE3M1 / TEDE1M2 / E3M3 census, contact-sheet
verified — were defined inside `projects/blood-city/level/materials.py` and could
not be reached from a second project. The census is the expensive part and it is
not project-specific. `Material` also gained `sky_tile`, because levels do not
share a sky: the monastery's is 2500 and all 45 of E3M1's parallax sectors name
3491, and without the field a city built from these materials stood under the
monastery's sky.

### 17. `tools/mine_layers.py` and `knowledge/blood/design/layers-v1.json`

One narrow question asked of the corpus, as the addendum allows: *what does the
campaign keep true when two sectors share ground?* It also measures BB4
separately, on the owner's suggestion, and BB4 turned out to be the map this
fragment is trying to be — see below.

---

### 18. Two faults the renders caught that no validator could

The acceptance frames are not a formality either. Two things passed every check
and were wrong to look at:

- **The store roof was a walled box.** Its sector stopped at the room below it,
  so standing on the roof you saw a wall in every direction. Of the campaign's
  309 measured overlooks only 5% put a blocking wall along the edge they
  overlook — Blood builds a walk you can step off. The roof now reaches the
  yard's own edge and is open along it, and stepping off is a one-storey drop
  `layers.fall_cost` prices at nothing.
- **The roof's sky was 1.93 bodies over its head**, because it inherited the
  layer's clear height like an interior. 94% of the campaign's adjacent
  open-to-open sector pairs hold their sky at one z; two different ones draw as a
  band of wall hanging in the air. It now shares the yard's sky plane.

Both are visible in one frame and invisible in every number.

---

## What Blood City and the monastery inherit for free

- **Buildings can have storeys.** Blood City's districts are flat because the
  layout refused any footprint overlap. `declare_layer` plus a `Style(layer=...)`
  on an assembly is the whole change needed to put a first floor on a venue.
- **The city palette is importable**, so Blood City's `materials.py` can become a
  thin set of local additions over `bloodmap.surfaces` instead of a private copy.
- **`Room` naming its own faces** removes a class of silent fault from every
  non-rectangular room already in Blood City.
- **`Style.layer` and structure inheritance** mean a staircase inside a venue
  keeps its building's identity instead of falling into a global default.
- **The geometry audit's `separate_arrangements`** is what makes any of this
  survive the downstream validators.
- **The fall-cost arithmetic** (`layers.fall_cost`) is Blood's own integration
  rather than a guess, and answers "is this drop survivable" for any level.

## The tear in the yard, and the two detector bugs that hid it

The fragment tore: from the yard, black rectangles up to 93,972 pixels, a third
of the frame. Three diagnoses were tried and two were wrong. What follows is the
measured account, because the wrong ones each looked convincing.

**Wrong: the flood.** `CSTAT_WALL_1WAY` (engine.c:3134) stops `scansector`, so
cutting the yard's side of the offending portals should stop the yard reaching
what it should not. It took 64 holed views to 9 and stopped. It could not do
better: the flag is directional, so it cannot resolve a symmetric fault, and the
nine survivors were the other half of the same problem. Reverted.

**Wrong: the skipped comparison.** `wallfront` returns -1 for collinear segments
and -2 for crossing ones, and the sort answers either with `continue`
(engine.cpp:9736 -- `//Almost works, but not quite :(` is Build's author's own
comment). Real, and now detected exactly by `bloodmap/drawsort.py`. But graded
against the campaign it is a **note**: 91.1% of overlapping pairs have such a
wall pair, because one sector directly over another on one outline is how Blood
stacks space at all. And instrumenting the sort's own skip site showed only 11
of 64 holed views had a skip, with 39 skips producing no hole.

**Right, and it took two detector fixes to see it.**

`overlapping_pairs` was blind to the single most overlapping thing two sectors
can be. `loops_equivalent` demands matching vertex lists, and a storey and the
storey over it never have those -- each has its own doorways splitting its own
walls, so the same rectangle carries different points along its edges. The pair
fell through to `polygon_relation`, which calls it `exactly_shared_boundary`,
which was not in `OVERLAPPING_KINDS`. **Blood's normal way of stacking space was
invisible to every check built on that function**, this project's own lofts
included. `planar_geom.same_ground` now compares corner-for-corner in either
winding -- and is deliberately narrower than `exactly_shared_boundary`, because
a sector filling a *hole* in another satisfies that and shares no ground at all.

With the detector fixed, the campaign answers the design question outright:

| | same-footprint pairs | co-drawn in a view | of those, sort failed |
| --- | --- | --- | --- |
| BB4 | 1 | 11 views | **0** |
| E1M1 | 4 | 85 | **0** |
| E3M1 | 5 | 69 | **0** |
| E4M2 | 8 | 493 | **0** |
| MALTX (before) | 50 | 8 | **8** |

658 campaign views hold a pair on one footprint and the sort ranks it every
time. It never has to do otherwise, because **every same-footprint pair Blood
ships is one of two things**: two near-coplanar rooms whose outlines happen to
match -- floors 0 to 5,120 apart, a step -- or a room-over-room link, which the
engine draws in its own pass. MALTX's kiln pair was 40,960 apart: a storey.

Blood does not build a plain second storey on one footprint and let you look
into both halves, and for a building envelope there is no geometry that would
let it. The upper storey's outer walls are either **on** the lower storey's --
coincident, unorderable -- or **inside** them, and then a one-sided wall stands
in the middle of the other's plan, retires its screen columns whole once drawn
(engine.c:3216) and stops `scansector` recursing past them (engine.c:3156).
Inset and flush are the only two options and both fail. Height never enters it.

So the constraint is architectural and it is about what can see what: **the space
you enter the ground floor from must not also open into the storey above it.**

### What was done to the fragment

* the store roof is on its own plan and reached by the stair inside, not run out
  to the yard's edge;
* both lofts are on their floors' outlines rather than set in 256 -- the inset
  was introduced earlier on the wrong theory and was actively harmful, since it
  put every loft wall inside the room below and forced each loading door to
  reach past that room's own wall to meet it;
* the loading doors are gone. They were the second opening off the yard, and
  there is no version of them that is safe while the ground-floor door is on the
  same yard. The lofts are reached by their stairs. **This costs the gantry its
  crossing**, which is a real loss and is recorded as one rather than dressed up.

| | clear-camera holed views | worst frame |
| --- | --- | --- |
| before | 64 | 93,972 px (31% of frame) |
| after | **2** | **1,504 px (0.5%)** |

Both survivors are on the store roof. For scale, the same observer on shipped
Blood maps reports unwritten pixels in 21% to 38% of clear-camera views -- art
the headless build does not have. MALTX is at 0.12%, and one overlapping pair is
co-drawn anywhere in the sweep, which the sort ranks without trouble.

## What went into the library

- **`planar_geom.same_ground` / `canonical_ring`**, and `overlapping_pairs`
  using them: the detector fix above.
- **`layers.layer-stacked-and-seen-together`**, an **error**: two regions on one
  outline, more than a standing body apart in z, undeclared, and `covisible`
  finds a vantage. Scoped deliberately to one outline, because that is what the
  658 views measure; a cellar strictly inside the street above it has walls that
  are parallel rather than coincident, the sort ranks them, and Blood builds
  that everywhere. `layer-overlap-in-one-view` speaks to those.
- **`bloodmap/drawsort.py`**: `wallfront` transcribed from engine.cpp:2227,
  `dmulscale2`'s two-bit shift included -- it floors, so a cross product of 3
  reads as zero and two segments a unit apart are called collinear. Graded a
  note at 91.1%.
- **`overlap_visibility.safe_to_draw`** beside `safe`. Asked about MALTX, `audit`
  called all 73 pairs safe, 72 of them `band_separated`, while two were tearing
  the frame. Disjoint bands stop `updatesectorz_compat` confusing which sector
  the player is in; they say nothing about draw order, because `wallfront` has
  no z in it. Bands are not in `RENDER_PROOFS`.
- **`solid_edges`** cancels on any declared join whatever the layers, and by
  interval rather than wholesale. It used to keep one side of a cross-layer
  opening as masonry, so `can_see` called a real opening an occluder from one
  side only.
- **The observer** logs the sort's own skip site, with both walls, and no longer
  discards pairs whose two bunches belong to one sector -- which was most of
  them, and why it first reported nothing at all.

## What the pilot did not do, and why

Cut by the addendum and still cut: the intent resolver, the catalog query layer,
templates instantiating templates, and a general spatial model. In their place:

- Instead of the resolver, `literal-coordinates.md` records every place the
  author had to write a number they meant as intent. That list is the honest
  specification for a resolver, if one is ever built.
- Instead of the query layer, `docs/toolkit-index.md` is one page naming what
  exists and when to reach for it. The real problem was never that the catalog
  could not be queried; it is that an agent building a city never learned
  `aperture.py` existed.
