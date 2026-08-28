# Hierarchical level decompiler

`bloodmap.decompiler` is the first single-level source-reconstruction pilot. It
joins existing exact and derived layers rather than replacing them:

```text
Blood MAP -> LevelIR (authoritative)
          -> BuildIR / spatial evidence (derived)
          -> LevelSource primary hierarchy (reviewable)
          -> JSON and executable Python
```

## Current-component audit

| Need | Reused component | Pilot responsibility |
| --- | --- | --- |
| Exact native truth | `DiskMap` and `LevelIR` | Embed the complete `LevelIR`; compile only this field |
| Geometry/topology evidence | `BuildIR` and `analyze_spatial` | Cite portal components and perceptual candidates |
| Player-relative scale | `player_space` profile | Summarize footprint, bounds, and clearance per node |
| Materials/ART identity | native `picnum` usage and `materials` separation rules | Expose role-specific tile use; leave aliases/meaning unreviewed |
| Local composition | `LevelIR` fragments and `composition` | Preserve source refs so a reviewed node can later become a slice/fragment |
| Searchable precedent memory | `design-index` and workspace `LevelSlice` | Emit inspectable nodes; cross-map node indexing remains next work |
| Authored validation | geometry audit and native validation | Validate the exact rebuild; generic-plus-residual experiments remain next work |
| Engine testing | NBlood oracle/bot infrastructure | Deliberately not invoked or modified by this geometry-first pilot |

## Knowledge boundaries

A `llmapper.level-source` document has four important parts:

- `exact_level_ir` is the only compilation authority. Hierarchy edits cannot
  silently rewrite native sectors, walls, sprites, extended records, or channels.
- `hierarchy.nodes` is the primary readable tree. Assemblies use persistent
  portal topology; spaces use perceptual-continuity candidates within those
  assemblies. Ungrouped sectors remain explicit reviewable singleton spaces.
- `hierarchy.relations` retains internal and cross-space portals and overlapping
  vertical relationships with exact wall/sector evidence.
- `hierarchy.alternative_candidates` preserves all spatial hypotheses, including
  navigation, material, mechanism, and vertical views. They are not forced into
  the primary tree.

Every primary node records exact sector/wall/sprite IDs. Level nodes cover every
native object, and primary spaces partition every sector exactly once. Validation
rejects missing, duplicate, out-of-range, or cyclic provenance.

Neutral names such as `space_001_004` are intentional. They make the Python
source navigable without claiming that a portal-continuity cluster is a lobby,
crypt, staircase, or garden. An LLM or human review can fill `interpretation`
with a semantic name, description, and confidence while retaining the evidence.

## Pilot commands

Decompile one original Blood level to the canonical document and a Python view:

```text
python -m bloodmap decompile maps/blood/E1M1.MAP \
  -o work/E1M1.level-source.json \
  --python work/E1M1.level-source.py
```

The Python file contains local build functions for the level, assemblies,
spaces, and sprite-detail groups. It also exposes `level_source()` so tooling can
recover the complete typed document.

Rebuild authoritative source truth:

```text
python -m bloodmap compile-source work/E1M1.level-source.json \
  -o work/E1M1.rebuilt.MAP
```

For unchanged source, this rebuild is byte-exact. Semantic hierarchy edits are
therefore safe annotations until a future explicit lowering step translates a
reviewed authoring operation into `LevelIR` geometry.

## What this proves and does not prove

The pilot proves that one complex native level can live in a versioned document
that is simultaneously lossless, hierarchical, evidence-backed, player-scaled,
asset-aware, and readable as Python. It creates the seam where an LLM can revise
decomposition without corrupting source truth.

It does not yet claim good semantic naming, a reusable staircase/alcove/shell
vocabulary, generic-plus-residual reconstruction, held-out abstraction quality,
or a cross-map node atlas. The next useful test is to have a reviewing agent name
and reorganize one level, then measure whether an authoring agent actually opens
and reuses those nodes instead of dropping back to raw sector emission.


## A hole flush with its own outer edge

Build walks wall loops; it does not require a sector to be a planar
subdivision. So a sector may carry an inner loop whose edge lies **exactly on**
its outer loop -- a bite out of the sector's edge, drawn as a hole rather than
as an indentation. E2M3's sector 212 has one: four inner loops, and the one
sector 326 fills sits flush against the outer boundary along `y = 36352`.

Nothing is wrong with the map. All four walls pair reciprocally, and the
renderer never notices. But a `PlanarLayout` *is* a subdivision, so the host's
outer boundary and the filling region both draw the same piece of line in the
same direction, which cannot be paired as a portal. The round trip stopped there
with `same-direction coincident atomic segments`, and for a long time that read
like a decompiler bug.

It is not. The fix is to emit the same shape the other way round: when an inner
loop touches the outer loop at two or more vertices, `_splice_flush_hole` folds
it into the outline as an indentation. The boundary and the enclosed area are
identical; the region that filled the hole now abuts the indentation instead of
overlapping an edge.

Across the 43 campaign maps this folds **47 holes in 33 sectors**, and
introduces no degenerate outline anywhere: the 11 sectors whose outer loop
repeats a vertex already did so before the splice, and they still do after.

The seam needs care in both directions. The walk has to go *through* the hole
rather than along the edge already on the boundary -- the short way round would
just repeat the outer segment's endpoints -- and the hole's touching corners are
usually vertices of the outer loop already, so the join has to collapse the
repeats rather than refuse them.

E2M3 now gets past that whole structural class and stops later, on 12 unpaired
portal candidates across 9 sectors in one area. That is a bounded remainder
rather than a wall.


## The XSprite a sprite cannot do without

A map can pass every structural check the project has and still segfault the
engine. The monastery did: `validate_map` returned 0 diagnostics,
`validate_authored_level` 0 errors, and all thirteen hard gates were green,
including `native_structure_valid`. NBlood loaded it, printed
`This map *does not* provide modern features`, and took SIGSEGV.

The cause was that its dudes had no XSprite. Blood reaches through
`sprite.extra` into `xsprite[]` for sprites on certain statnums, so a sprite with
`extra = -1` sends the engine to index -1. `actInit` happens to guard its own
loop with `xspriRangeIsFine`, which is why the crash lands later and away from
the cause.

The rule is not a style preference. Across the 43 campaign maps, sprites on
statnum 3 (items), 4 (things), 6 (dudes), 11 (traps) and 12 (ambient sound)
carry an XSprite in **15,071 of 15,071** cases, without one exception, while
decoration (statnum 10) never carries one and statnum 0 carries one 63% of the
time. The split is that sharp because it is structural.

The bug was one line in `PlanarLayout.compile`:

```python
if placement.behavior:                      # an empty dict is falsy
    builder.set_behavior("sprite", sprite_id, **placement.behavior)
```

An author who wanted a plain enemy passed no behaviour, so no XSprite was ever
allocated. It now reads `if placement.behavior or placement.status in
XSPRITE_REQUIRED_STATNUMS`, and `validate_map` emits `sprite-missing-xsprite` as
an error, which is silent on all 43 campaign maps.

### How it was found

Analysis did not find it -- the winding, wall links, loop closure and portal
reciprocity were all clean, and the first winding check was wrong about its own
sign convention until it was compared against E1M1. What found it was bisecting
against the real engine: strip a category of content, rebuild, run
`nblood.exe -j <gamedir> -map <name>`, and grep the output for `Caught signal`.
Sprites crashed it, dudes were the category, one dude was enough, and an empty
XSprite on that one dude cured it. That loop is worth keeping: the corpus says
what Blood's designers did, but only the engine says what Blood accepts.

## Two ways a mechanism is wrong without being invalid

Both of these passed every gate, loaded, and were visibly broken.

### Blood centres a sprite on its z

`GetSpriteExtents` (db.h) is the entire rule, and it is shorter than the
assumption usually made about it:

```c
*top = *bottom = pSprite->z;
if ((cstat & 0x30) != 0x20) {          // anything but floor-aligned
    int center = tilesiz[picnum].y / 2 + picanm[picnum].yofs;
    *top    -= (yrepeat << 2) * center;
    *bottom += (yrepeat << 2) * (height - center);
}
```

There is no `cstat & 128` test in it. Bit 128 is Duke's y-centring flag and
Blood sets it on nearly everything, so reading it as "this sprite is centred and
the others hang from z" is the natural mistake. Blood centres them all; only a
floor-aligned sprite is a flat plane at z.

So `z = floor_z` buries exactly half of a standing object, and that was 15 of
the monastery's 58 decorations, fences included. The campaign puts the *bottom*
on the floor: 43 of its 65 fence sprites sit at `bottom - floor_z == 0` exactly.
`picanm.yofs` matters too -- tile 641 carries -60, so it is not centred on its
own middle.

`placement.sprite_extent` / `seated_z` do the arithmetic, `PlanarLayout` takes a
`tile_extents` map and a `seat` of `"floor"`/`"ceiling"`/`"centre"`, and
`place_on_floor` and `place_on_ceiling` now mean what they say. A layout built
without the game's ART keeps the old behaviour rather than failing, but an
explicit `seat` for an unknown tile is an error.

### `state` and `busy` are one fact written twice

`trInit` translates a slide or rotate sector to `busy = -65536`, takes *that* as
the base, and only then translates to the authored `busy`. So **busy 65536 is
the pose the geometry was drawn in**, and busy 0 is a pose the author never saw.

The campaign never separates the two: of 659 slide and rotate sectors, 579 rest
at `(state 0, busy 0)` and 80 at `(state 1, busy 65536)`. Nothing rests at
`(1, 0)` -- which is what both of the monastery's doors were, claiming to be open
while drawn shut.

The visible symptom came from the other end. `SetSectorState` opens with:

```c
if ((pXSector->busy & 0xffff) == 0 && pXSector->state == nState)
    return 0;
```

A `kCmdOn` sent to a sector already at state 1 does nothing at all. The campaign
sends a state-1 sector `kCmdToggle` 42 times and `kCmdOff` 34, and `kCmdOn` not
once. Both monastery switches sent `kCmdOn`.

### A percentile band is not a limit

Fixing the fences turned up a third error, in the checking rather than the level.
`decoration.height_range` returned p10/p90 while its docstring said "ever drawn
at", and a test used it as a hard bound. 6% of the campaign's own decorations
fall outside their tile's p10..p90, so that check rejects Blood: tile 1044 has
p10 5.09 and a true minimum of 3.64, and three shipped fences sit at 4.36.
`height_bounds` now carries the observed min and max, and the bound-shaped
question asks it. This is the same mistake as ranking raw counts as consensus
norms -- a description of where something usually sits, used as a rule about
where it may.

## Three mechanisms that were valid and did not work

Reported by looking at the level. None was a malformed map; each was a rule the
engine enforces and the corpus states plainly.

### A sprite is dispatched by its statnum, not its type

The wall crack never fired its charges, and the reason was one field. All 108
campaign cracks sit on statnum 4, `kStatThing`; this one sat on 0.
`actDamageSprite` runs the health-and-trigger path under `case kStatThing`, and
`actInit` hands out `startHealth` on the same list. Off it the crack could not
be hurt, so it never reached zero health, never called `trTriggerSprite`, and
never transmitted. It kept its type and its picture and quietly stopped being a
crack.

Two related facts fell out of the same look. `thingInfo` for `kThingWallCrack`
has `dmgControl` `{0, 0, 0, 256, 0, 0, 0}`, and index 3 is `kDamageExplode` —
every other damage type, `kDamageBullet` included, is multiplied by zero. A
crack is opened by a blast and by nothing else, so `trigger_vector` on one is
decoration. And `kTrapExploder` explodes on any command *except* `kCmdOn`; the
fuse is `SetSpriteState` line 98, which posts a `kCmdOff` after `waitTime`.

`tools.unattested_values` now reports sprites on a statnum the campaign never
uses for their type, alongside the field-value check.

### A door's face belongs on the room's wall

Build draws the top section of a two-sided wall from **that wall's own
`picnum`** (`engine.c`; `overpicnum` is only for masked one-way walls), and a
shut Z-door is all top section. So a door face declared as the door region's
`wall_picnum` lands on the inside of the frame — the one set of surfaces a
player standing outside never sees. The level showed masonry where the door
should be and the door tile on the jambs.

`RegionSpec.door_face` puts it where the engine reads it: on both faces of every
portal the region owns, leaving the solid cheeks to `wall_picnum`.

### A sliding leaf must retract its own width

A leaf carried by a slide sector moves by the marker separation and no further,
so a leaf wider than that distance is still standing in the doorway when the
gate has finished opening. This gate's leaves were 1536 wide — the full width of
the opening, each — against 768 of travel, so half of it stayed shut when open.

The campaign builds to just inside the limit: E1M1 travels 1448 against a 1536
leaf and E1M5 1600 against 1792, 0.94 and 0.89 of the width. That both sit a
shade under one is what says the rule is the leaf clearing *itself*, not any
proportion of the doorway. `placement.leaf_repeat` and `blocked_when_open` state
it.

### Two more from the same pass

A wall-aligned sprite's `angle` is its **face normal**, so a fence lies across an
opening only when its angle is a quarter turn from the wall it sits on — ±512 in
59 of the campaign's 65 fence sprites. All three of this level's moving fences
were set to the wall's own direction and stood edge-on in their own doorways.
The mistake had a specific source: the two markers of a slide sector *are* both
authored at angle 0, for a real reason, and that rule was carried onto the
leaves, which are ordinary sprites whose angle is simply which way they face.

And a fence that opens is the switch for the sector it stands in. All twelve of
the campaign's pushable fences transmit to their own sector — you push the bars
and the bars part — and E1M1's gate, which this one copies, is exactly that.


## Decompiling into mechanisms, not into shape

Everything else here decompiles a level into architecture: regions, walls,
portals, a hierarchy of rooms. That is the right decomposition for a building
and the wrong one for machinery, and the cost was paid one fault at a time.

A sliding gate in Blood is six objects -- a sector, two markers, two leaves, and
whatever operates it -- bound by about a dozen facts. **Half of those facts are
not properties of any single object.** A leaf's angle is only correct relative to
the wall it sits on; its width only relative to the distance the markers are
apart; its z only relative to the floor. Mining field values one type at a time
cannot see a relation, which is exactly why `tools.unattested_values` reported
the crypt gate clean while it stood edge-on in its own doorway at twice its own
travel.

`bloodmap/assembly.py` closes over a mechanism instead. From a root sector it
follows three bindings -- **containment** (a sprite in the sector),
**reference** (`marker_0` naming a sprite), **channel** (an object transmitting
to what this receives) -- names each member by the part it plays, and records
the relations between parts alongside the fields of each.
`tools/mine_assemblies.py` does that across the campaign and reports a template.

The validation that matters: pointed at 308 campaign gates, it recovers
unprompted the facts that took four sessions to find by hand -- both markers at
angle 0, tile 3997, statnum 10, `cstat 32896`; `(state, busy)` as a single fact
taking only `(0, 0)` or `(1, 65536)`; leaf width as a ratio to travel rather
than an absolute. It also found things nobody had looked for: a sector-sound
sprite in 86% of gates, and `cstat 32896` on markers where this level had 32768
-- on the slide markers *and* the rotate pivot, in a level that had already been
audited five times.

### Four ways it was wrong first, all the same way

Each is worth recording, because each is the same mistake in a new costume: a
statistic quoted without the thing that makes it mean something.

1. **A role too coarse to describe anything.** "Carried by the sector" grouped
   gate leaves with the exploder charges that ride moving platforms, and the
   modal fields then described neither -- the template asserted a gate leaf
   should be tile 908 at `x_repeat` 4, which is a bomb. The role has to keep
   what the sprite *is*.
2. **Uncommon reported as wrong.** The first check flagged any value that was
   not modal. Its output for a correct gate was nineteen lines of which one was
   real: a `(state, busy)` pair used by 9% of campaign gates, a switch of the
   other of the two switch types. A value the campaign never uses is a fault; a
   value it uses less often is a choice.
3. **An absolute judged where a ratio applies.** A leaf in a narrow doorway must
   be narrower than one in a wide doorway, so `x_repeat` is not comparable
   across maps and `width_over_travel` is.
4. **A share with no denominator.** Exactly one campaign sludge sector has a
   switch in it, and the template announced that switch's picnum, type and cstat
   as 100% conventions, then failed this level for using a different switch.
   `MIN_OBSERVATIONS` now gates every assertion.

That last one is the same error as reading a percentile as a limit
(`height_range` vs `height_bounds`), and as ranking raw counts as consensus
norms (`SIZE_FEATURES`). Three times in one project, in three different tools.
It is worth naming as a class: **a corpus statistic is only a rule when the
sample supports it, the units are comparable, and "rare" has been distinguished
from "never".**


## Building from the template

`tools/mine_assemblies.py` states what a working gate looks like. `bloodmap/mechanism.py`
builds one. That closes the loop the extractor opened: a mechanism stops being a
dozen decisions and becomes one call taking the two things that actually differ
between one gate and the next -- where the opening is, and how far the leaves
travel.

```python
sliding_gate(layout, "region:crypt_gate", R(30, 40, 34, 42),
             threshold=(P(30, 40.5), P(34, 40.5)),
             travel=GATE_TRAVEL, channel=CH_CRYPT_GATE,
             floor_z=COURT, ceiling_z=COURT - tex(4))
```

Everything else comes from the template: the `(state, busy)` resting pose as one
fact; both markers at angle 0 on tile 3997, statnum 10, cstat 32896; each leaf's
angle as the threshold direction plus a quarter turn; each leaf no wider than the
travel; the seat on the floor; the two carry bits; the push wiring to its own
sector. The crypt gate's 86 hand-written lines became four, and the second gate
in the level cost one call rather than another four sessions of debugging.

The measure of whether this works is not that it compiles. It is that
`mine_assemblies --against` reports both gates clean apart from a single
deliberate difference -- these leaves fill their arch top to bottom where campaign
gates hang in taller halls.

## Scale: where the monastery stands against E1M1

| | before this pass | now | E1M1 |
| --- | ---: | ---: | ---: |
| sectors | 50 | 64 | 155 |
| walls | 388 | 471 | 1498 |
| loops | 8 | 13 | 38 |
| loops per 100 sectors | 16.0 | 20.3 | 26.0 |
| mean degree | 2.28 | 2.38 | 2.51 |
| moving sectors | 7 | 8 | 27 |
| secrets | 2 | 3 | 11 |

The wing added is a cloister -- the room a monastery is organised around, and the
one this level did not have. Four covered walks around an open garth, with a
chapter house and refectory opening off two walks each, a walled-up cell behind
the north range, and a dorter stair tying the whole wing to the gallery at the
far end of the map.

It was chosen for the shape of the graph as much as for the architecture. A
cloister is a cycle by construction, the garth opening onto all four walks adds
three more, and every room reached from two walks closes another. That is why
`loops_per_100_sectors` moved from 62% of E1M1's to 78% while the sector count
moved from 32% to 41%: the wing is denser in routing than the level it was added
to.

**What is honestly not closed.** E1M1 is still 2.4x the sectors and 2.9x the
loops. Reaching it is not another cloister; it is roughly ninety more rooms, and
the thing that would make that tractable is the same move made here for
mechanisms -- constructors for the *architectural* forms, so a colonnade or a
stair-and-landing or an arcaded hall is one call from a mined template rather
than thirty hand-written regions. The mechanism side of that now exists and
works. The architectural side does not yet.


## The XMapEdit sample maps

133 maps, each demonstrating one mechanism with nothing else in the way. They
are a better oracle than the campaign for anything mechanical, because a
campaign map answers *what did the designers usually do* and a sample answers
*what does the engine require*.

Reading them: all 133 parse and re-encode **byte for byte**, and none produces a
structural error. The warnings that do appear are concentrated in exactly the
maps that demonstrate unusual geometry -- `MODELLING-HIDDENAREA1/2`,
`MODELLING-NEWSOS`, `MODELLING-BASICS` -- where non-reciprocal portals and
two-wall sectors are the point rather than a mistake.

### What they caught immediately

`ENVIRONMENT-SLIDETRICKS` stores marker indices of 107 and 108 in a map with 62
sprites. That is only survivable if nothing reads them, and nothing does:

```c
for (nSprite = headspritestat[kStatMarker]; ...) {
    switch (sprite[nSprite].type) {
        case kMarkerOff: case kMarkerAxis: case kMarkerWarpDest: {
            int nOwner = sprite[nSprite].owner;
            if (nOwner >= 0 && nOwner < numsectors) {
                int nXSector = sector[nOwner].extra;
                if (nXSector > 0 && nXSector < kMaxXSectors) {
                    xsector[nXSector].marker0 = nSprite;
                    continue;
                }
            }
        }
        break;
        case kMarkerOn: { ... marker1 = nSprite; continue; }
    }
    DeleteSprite(nSprite);
}
```

`dbLoadMap` **rebuilds** `marker0` and `marker1` from each marker sprite's
`owner`. The stored values are derived, not authoritative -- which is why a
sample can carry nonsense there and still work.

And note the last line. A marker whose `owner` does not name a sector with an
XSECTOR is not merely unbound; **it is deleted**. This project's level wrote both
marker fields correctly and left `owner` at -1 on all five of its markers, so
every one of them was destroyed at load and its moving sectors then dereferenced
freed sprite slots. Five audits missed it, because every check the project had
was looking at the field the engine ignores. All 1,055 campaign markers and all
1,824 sample markers carry an owner.

Two refinements the samples also forced:

* `owner` is the sector the marker *controls*, not the one it stands in -- 387
  campaign markers differ, so a constructor cannot simply copy the containing
  sector;
* the rule is keyed on the **statnum**, not the type. Three Modern samples file a
  `kMarkerWarpDest` on statnum 0, untouched by the loader's marker loop, and
  they carry `owner -1` quite legitimately.

`mechanism.bind_markers` now sets `owner` and derives the marker fields from it,
and `validate_map` reports `marker-unowned` as an error -- silent on all 43
campaign maps and all 133 samples.

### The campaign is not a complete demonstration of the engine

The samples use **two sector types, one wall type and 48 sprite types that
appear nowhere in the 43 shipped maps**, including `kSectorPath` (612), which has
no campaign instance at all. Every piece of knowledge in this project had been
mined from the campaign, so those were blind spots by construction.

`mine_assemblies --samples` mines the samples instead, and produces a path-sector
template the campaign could not have taught: `kMarkerPath`, tile 2319, on
**statnum 16** rather than the marker statnum, drawn at repeat 144, carrying
`wave` in 86% of cases, at 1.67 markers per path sector.


## Why the weirdness was never obvious

Thirteen faults in this level were found by a person looking at it and none by
the checks. Sorting them by *what would have made them visible* turns out to be
more useful than sorting them by what they were:

**Visible in one frame from eye height.** A fence sunk to its waist, a grille
edge-on in its doorway, a door face on the inside of its own frame, a sconce
floating in front of a niche. The observer could have shown every one of these
from the start. It was used to check two or three hand-picked viewpoints after
the fact, which is not the same as looking.

**Visible only in motion.** Gate leaves crossing instead of parting; a gate that
travels less than its own width. Both rest correctly at *both* ends of the
travel and are wrong only in between -- so every check that reads the map file,
which describes one frozen instant, passes them. `tools/inspect_mechanisms.py`
steps a mechanism through its travel and reports how much of the opening is
covered at each point. The crossing bug reads as `100% 100% 100% 100% 100%`
followed by the leaves having swapped sides; the correct gate reads
`100% 75% 50% 25% 0%`.

**Visible only against the engine.** A missing XSprite, a marker with no owner,
a crack on the wrong statnum. These are not visible at all -- the level looks
right and does nothing -- and the only oracle is the source.

**Visible only against other levels.** "Feels odd", "too interconnected". These
need the corpus, and they need the *right* statistic, which is where most of the
mistakes were.

## The thing the corpus cannot supply

Building the travel checker made the limit explicit. Three attempts at a
universal fault rule, each measured against the campaign:

1. Judge every carried mechanism -- disagreed with the corpus on **133 of 136**.
   Most sprites carried by a moving sector are not gate leaves; they are crates
   on a lift and charges on a platform, and nothing about them should cover a
   doorway.
2. Judge only *closures* -- still called **34 of 40** broken.
3. Flag anything that blocks more midway than at rest -- fired on **59%** of
   campaign closures, because plenty of Blood mechanisms rest *open* and close.
   A trap that shuts is not a gate that fails to open.

There is no corpus-derived rule here and there cannot be. **The corpus records
what mechanisms do; whether that is right depends on what the author meant.** A
gate and a trap have the same profile read backwards.

So the checker takes the intent as an argument. `expect_closure(series,
opens=True)` states the claim -- shut when found, fully clear when open, never
blocking more than it started -- and that claim is strong enough to test.
`mechanism.sliding_gate` is what makes the claim, because it is the thing that
knows it built a gate.

That generalises past mechanisms. The reason so many of these checks had to be
recalibrated is that they were trying to infer intent from convention. The next
real improvement to this system is not another statistic: it is for the
authoring side to *say what it is building*, so the checking side has something
falsifiable to check against.
