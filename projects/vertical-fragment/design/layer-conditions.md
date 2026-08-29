# Layers: the three questions, and the conditions they answer

Written before any geometry, because everything else in this pilot is verified
through it.

Build's sector is a 2D polygon with one floor and one ceiling. A level that
wants space above space has to work around that, and the campaign works around
it three ways: **plan overlap** (two sectors sharing ground, kept apart by z),
**room-over-room** (a link marker pair translating the player at a plane), and
**blocking floor-aligned sprites** (a deck with no sector at all). Measured over
the 43-map campaign by `tools.mine_layers`:

| technique | maps | share |
| --- | --- | --- |
| plan overlap | 37 / 43 | 86.0% |
| blocking floor-aligned sprite | 37 / 43 | 86.0% |
| both in the same map | 34 / 43 | 79.1% |

Overlap is the one that can break a level, so it is the one that gets
conditions. The other two are safe by construction and are simply used.

---

## 1. What the engine actually does

Blood sets `enginecompatibilitymode = ENGINE_19960925`
(`NBlood/source/blood/src/blood.cpp:1890`). That one line decides everything
below, because it routes every sector lookup through the `_compat` paths.

> **Revised after building.** §1a and §3 below were written before the fragment
> existed. Building it showed the portal-hop condition was measuring a proxy, and
> §3b records what replaced it. The engine facts in §1 all held.

### 1a. Movement: `clipmove_compat` — plan only, z ignored

`NBlood/source/build/src/clip.cpp:1823` — at the end of every `clipmove`, any
mode that is not `ENGINE_EDUKE32` calls `clipmove_compat`
(`clip.cpp:1112`), which resolves the mover's sector in two stages:

```c
for (native_t j=0; j<clipsectnum; j++)
    if (inside(pos->x, pos->y, clipsectorlist[j]) == 1)
    { *sectnum = clipsectorlist[j]; return; }        // clip.cpp:1114-1119
```

**The first stage does not look at z at all.** `clipsectorlist` is seeded with
the mover's current sector (`clip.cpp:1508`) and grown by breadth-first search
across two-sided walls (`clip.cpp:1688`), bounded by the move's own radius
(`clip.cpp:1500`, `rad = move + MAXCLIPDIST + walldist + 8`). So it is a
**portal-graph BFS bounded by planar distance**, and the first sector in BFS
order that contains the point in plan wins — whatever height the player is at.

Only if nothing in that list contains the point does it fall through to

```c
for (native_t j=numsectors-1; j>=0; j--)
    if (inside(pos->x, pos->y, j) == 1) { ...compare ceilingz/floorz to pos->z... }
```

(`clip.cpp:1122-1157`), and **this** stage does consult z, preferring the sector
whose ceiling sits closest above the player and returning immediately for the
first sector — scanning downward from the highest index — that actually contains
the player's z between its ceiling and floor.

This inverts the usual telling of the story. Portal separation is not a
secondary nicety behind z separation; it is the *primary* protection, because
the path that runs on every single move is the z-blind one. Z separation is what
rescues the cold lookup once two overlapping sectors are already in the same
clip list.

### 1b. Cold lookups: `updatesector_compat` / `updatesectorz_compat`

`engine.cpp:13324` and `engine.cpp:13454`. Both are sticky (return immediately
if the point is still inside the incoming sector), then scan the incoming
sector's direct wall neighbours — one hop, not a BFS — then fall through to
`for (int i = numsectors - 1; i >= 0; --i)`. The plain version tests
`inside_p` only; the z version tests `inside_z_p` (`build.h:1733`), which is
`z >= cz && z <= fz && inside_p(...)`.

So the linear fallback is not arbitrary: it is deterministic and picks the
**highest-numbered** matching sector. That is worse than arbitrary for our
purposes, because sector numbering is an artifact of emission order and carries
no design meaning at all.

### 1c. Player start and teleport destinations — a claim that does not hold

The premise this pilot was handed says player starts, teleport destinations and
spawn points are "the cold lookups that reach the arbitrary scan". **In Blood
they are not lookups at all.**

- `warpInit` (`warp.cpp:43`) copies `pSprite->sectnum` straight off the
  `kMarkerSPStart` sprite into `gStartZone[n].sectnum` (`warp.cpp:62-70`).
- `playerStart` (`player.cpp:870`) then calls
  `actSpawnSprite(pStartZone->sectnum, ...)` — the sector is passed in, never
  derived from x/y.
- `OperateTeleport` (`triggers.cpp:1575-1577`) sets the player's position from
  the destination marker and calls `ChangeSpriteSect(nSprite, pDest->sectnum)`
  — again the marker's recorded sector.
- `dbLoadMap` (`db.cpp:1184-1195`) byte-swaps and then trusts every sprite's
  recorded `sectnum`; it does not recompute any of them.

So the hazard is real but it lives on **our** side of the boundary, not the
engine's: whatever sector our compiler writes into that sprite is the sector the
engine will use forever, and our compiler resolves a placement's owning region
**in plan**. Over an overlap, a marker's owner is decided by which region the
compiler happened to test first.

The condition therefore survives, restated honestly, and it is a toolchain
invariant rather than an engine one. That is condition D below.

---

## 2. What the campaign keeps true

`tools.mine_layers`, over the same 43 maps, found **2,614 genuinely overlapping
sector pairs** (`polygon_relation` reporting `partial_area_overlap` or either
containment — the same predicate `PlanarLayout._validate_regions` already uses,
so the measurement and the enforcement are the same test).

| question | answer |
| --- | --- |
| overlap pairs whose z bands also intersect | 430 / 2,614 = **16.4%** |
| overlap pairs closer than 5 portal hops | 21 / 2,614 = **0.8%** |
| overlap pairs that are **both** z-clashing **and** under 5 hops | **4 / 2,614 = 0.15%** |

Portal separation over all overlap pairs: q1 **9**, median **12**, q3 **15**,
and a further 594 pairs are not joined through the portal graph at all.

The four sub-5-hop z-clashing pairs are E1M1 45/55 (1 hop), E6M3 68/126 and
69/126 (3 and 4), E6M4 67/69 (4). The one-hop case is not stacked space: E1M1's
sector 55 is a self-touching wall loop that revisits `(11776, 36608)` three
times and carries zero-width spurs, so the two "proper crossings" the predicate
reports are against a degenerate boundary rather than a second storey.

**The law is the conjunction, and only the conjunction.** Requiring disjoint z
bands on its own would enforce a habit the campaign breaks one time in six — a
`note` on the registry's own scale. Requiring 5 portal hops on its own is a
`warning` at 0.8%. Requiring that an overlap be resolved by *at least one of
them* is broken 0.15% of the time, which is an `error`: the campaign essentially
never does it, and the engine explains exactly why not.

This is also why the number quoted to this pilot — "campaign median 6 hops, q1
5" — is not the number that comes out of the single-player corpus, where the
median is 12 and q1 is 9. It is very close to what comes out of BB4 (median 7,
q1 6, §2b), which suggests the quoted figures were measured on the compact
bloodbath maps rather than the campaign. Either way 5 is not a middle. It is the
**floor**: the value below which the campaign essentially stops.

---

## 2b. BB4 — the map this pilot is trying to be

BB4 sits outside the `E[1-46]M[1-9]` selector, so the campaign numbers above do
not contain it. Measured with the same predicate it turns out to be the worked
example of everything here, at exactly the size this pilot is aiming for:

- **71 sectors**, 651 walls, 165 sprites, in a plan 97 × 85 body-widths across.
- **68 overlapping sector pairs and not one z-clash.** Every overlap is resolved
  by disjoint bands; separation runs min 4, q1 6, median 7, max 12.
- All three techniques in one map: 68 plan overlaps, one room-over-room `link`
  pair with its partner parked at z = 2,899,968 in free map space, and nine
  blocking floor-aligned sprites (all picnum 256).

Its vertical grammar is startlingly regular. Three bands, each **32,768 z of
clear height — 1.93 bodies** — stacked on a **8,192 z slab (0.48 bodies)**:

| layer | ceiling_z | floor_z | clear | floor height |
| --- | --- | --- | --- | --- |
| ground | −24,576 | 8,192 | 1.93 bodies | +0.48 |
| middle | −65,536 | −32,768 | 1.93 bodies | −1.93 |
| upper | −98,304 | −65,536 | 1.93 bodies | −3.86 |

Floor to floor is **40,960 z = 2.41 bodies**, and rooms that want height simply
span two bands at 65,536 (3.86 bodies) rather than inventing a new one.

Two consequences this pilot takes directly:

1. **The slab is the layer boundary, and it is never zero.** Across all 68 pairs
   the thinnest slab is 4,096 and the median is 8,192; nothing interpenetrates.
   Campaign-wide the median slab is 12,160 with q1 2,048, so BB4 is at the tight
   end of normal rather than outside it.
2. **2.41 bodies floor-to-floor is inside the painless drop.** One storey down
   costs nothing; two storeys (4.83 bodies) costs about 30 hp. The vertical
   grammar and the fall thresholds in §4 are the same design decision seen twice.

The fragment below adopts BB4's bands unchanged and adds a fourth below the
street, because the brief wants an undercroft.

---

## 3. The four conditions

For every pair of regions whose plans overlap:

- **A — bands.** Their `[ceiling_z, floor_z]` intervals must not intersect.
  *Measured: 16.4% of campaign overlap pairs violate this. Enforced only in
  conjunction with B.*
- **B — separation.** Their shortest portal-graph distance must be at least
  **5**, or they must not be joined at all. *Measured: 0.8% violate. Enforced
  only in conjunction with A.*
- **A∨B — the law.** Every overlap must satisfy A or B. *Measured: 0.15%
  violate → `error`.*
- **C — sight.** No region may see into both members of an overlapping pair.
  Where two sectors share ground, the renderer floods to both through portals
  and draws them in an order nothing in the map controls.
- **D — declared owners.** No player start, teleport destination, warp marker
  or spawn point may stand over an overlap, because the compiler resolves its
  owning region in plan and the engine then trusts that answer forever
  (`db.cpp:1195`, `warp.cpp:69`, `triggers.cpp:1577`).

A **layer** is what makes these checkable rather than case-by-case: a named
planar arrangement with its own height band. Overlap *within* a layer stays
forbidden outright. Overlap *between* layers is permitted, and is exactly the
place these five checks run.

---

## 3b. What building it changed — the condition that survived

The first version of condition B enforced "at least 5 portal hops". Run against
the fragment it produced **eighteen findings, every one false**: it fired on the
brewhouse's loft over its mash floor, on the kiln's, on the yard over its cellar.
A small building cannot put five portals between a room and the room above it,
and a rule a correct map cannot satisfy is the exact failure this project already
has a memory about.

Two things about `clipmove` explain why five was the wrong number:

1. **`clipsectorlist` is seeded with the mover's own sector** (`clip.cpp:1508`)
   and scanned **in order** (`clip.cpp:1114`), so index 0 wins whenever it still
   contains the point. A mover is only misplaced just after leaving a sector, and
   then the right answer is a portal neighbour — depth 1 of the walk. A wrong
   sector has to arrive no later to win it. **Two hops, not five.**
2. **The walk is bounded by a box, not by hops.** `rad = move + MAXCLIPDIST +
   walldist + 8` (`clip.cpp:1500`), and a wall wholly outside that box is never
   even examined (`clip.cpp:1574`). `MAXCLIPDIST` is 1024 (`engine_priv.h:19`);
   a player's `walldist` is `0x30 << 2` plus the 16 `MoveDude` adds
   (`dude.cpp:1581`, `actor.cpp:4593`). About **2,264 units** — six body widths.

So two rooms one above the other are zero apart in plan and perfectly safe when
the only way between them goes out to a stairwell and back. That is what a
building is.

**The condition, restated:** an overlap is confusable when the two regions are
within **two portal hops** *and* a walk between them stays inside one clip box.
It is a fault only when it is also unresolved in z.

Re-measured over the same 2,614 campaign overlap pairs:

| | pairs | share |
| --- | --- | --- |
| confusable at all | 5 | 0.19% |
| **confusable and z-clashing** | **1** | **0.038%** |

One pair, in one map — E1M1's 45/55, the degenerate loop from §2. Under the
registry's own scale that is an **error**, and it is the law the module enforces.

The hop distribution is still reported beside it, because comparing a level
against the campaign is worth doing. It is just a statement about Blood's levels
being large, not about what is safe.

The fragment, measured this way: 20 overlaps, **0 findings**.

---

## 4. The three spatial queries, and who calls them

Nothing in this project can answer a three-dimensional question:
`reachability.py` is a pure portal graph with no `floor_z`, no step height, no
clearance. This pilot builds the three functions the conditions need and stops
there.

| query | answers | called by |
| --- | --- | --- |
| `column_at(layout, x, y)` | what is above and below this point, and how much air is between | condition A (band containment and the overlap inventory); the fragment's "look down through an opening" acceptance |
| `can_see(layout, a, b)` | can this place see that place | condition C |
| `drop_between(layout, a, b)` | how far is this drop, does it hurt, is it lethal | the fragment's descent authoring, and its acceptance |

`drop_between` is graded against Blood's own arithmetic rather than a guess.
`MoveDude` integrates a falling dude as `z += zvel>>8` then
`z += (kDudeGravity*2)>>8; zvel += kDudeGravity` per tick
(`actor.cpp:4595`, `4628-4631`), and on landing computes
`nDamage = mulscale30(vax, vax) - kFallDamageFloor` (`actor.cpp:4835-4846`)
where `vax` is the impact z-velocity exactly, because `actFloorBounceVector`
with `elastic = 0` over a flat floor returns its input (`actor.cpp:2691-2699`).
`kDudeGravity = 58254` and `kFallDamageFloor = 100<<4` (`actor.h:186-187`).

Simulating that integration gives thresholds rather than folklore, in units of
one standing body (16,960 z):

| drop | z units | bodies | cost |
| --- | --- | --- | --- |
| last painless | 62,564 | 3.69 | none |
| first that hurts | 68,025 | 4.01 | 4 hp |
| | 85,772 | 5.06 | 34 hp |
| | 98,741 | 5.82 | 55 hp |
| lethal from full health | 127,411 | 7.51 | 102 hp |

Damage turns positive the moment impact z-velocity passes `0x140000`
(1,310,720), which is what `sqrt(kFallDamageFloor << 30)` comes to exactly.

**A fragment that wants the player to drop between layers has about three and a
half bodies of free height to play with, and seven and a half before the drop
is a death.**

## Stacked storeys: the one rule, and why there is no way around it

Two sectors on one outline, more than a standing body apart in z, that one view
can hold, is a fault the geometry cannot fix. It has to be designed out.

### What Blood does

| | pairs on one footprint | co-drawn in a view | of those, the sort failed |
| --- | --- | --- | --- |
| BB4 | 1 | 11 views | 0 |
| E1M1 | 4 | 85 | 0 |
| E3M1 | 5 | 69 | 0 |
| E4M2 | 8 | 493 | 0 |

658 views hold such a pair and the sort ranks it every time. Every
same-footprint pair in those maps is either **near-coplanar** -- floors 0 to
5,120 apart, which is a step between two rooms whose outlines happen to match --
or a **room-over-room link**, which the engine draws in its own pass with its
own occlusion. There is no third case. Blood does not build a plain second
storey on one footprint and let you look into both halves.

### Why there is no geometry that would let it

For a building envelope the upper storey's outer walls have two options.

**Flush.** They lie on the lower storey's walls. `wallfront`
(`engine.cpp:2227`) returns `-1` for two segments on one line, and the sort
answers a negative with `continue` (`engine.cpp:9736`), so which of the two
draws first falls out of enumeration order.

**Set in.** Now no wall is on a line with another -- and every wall of the upper
storey stands *strictly inside* the lower storey's plan. A one-sided wall
retires its screen columns whole once drawn, `umost[x]=1; dmost[x]=0`
(`engine.c:3216`), however few rows it painted; and `scansector` will not
recurse past a retired column (`engine.c:3156`). So it blots out whatever is
behind it **in plan**, however far apart the two are in z.

Both fail, and height never enters either one: the sort has no z in it. Setting
the upper storey in is not a mitigation, it is the other failure mode. This
project introduced a 256-unit inset on exactly that mistaken theory and it was
what tore the frame.

### The rule

**The space you enter the ground floor from must not also open into the storey
above it.** Give each storey its own way in -- a stair inside the building is
the usual one -- or make the pair a declared room-over-room stack. Rooms that go
different ways before they overlap satisfy this for free.

`layer-stacked-and-seen-together` is the check, graded an **error**, and scoped
to pairs on one outline because that is what the 658 views measure. A cellar
strictly inside the street above it has parallel rather than coincident walls,
the sort ranks them, and Blood builds that everywhere;
`layer-overlap-in-one-view` is the warning that speaks to those.

### Detecting it at all

This was invisible for a long time because `overlapping_pairs` dropped it.
`loops_equivalent` wants matching vertex lists, and a storey and the storey over
it never have those -- each has its own doorways splitting its own walls, so the
same rectangle carries different points along its edges. The pair fell through
to `polygon_relation`, which calls it `exactly_shared_boundary`, which was not
in `OVERLAPPING_KINDS`. `planar_geom.same_ground` compares corner-for-corner in
either winding, and is narrower than `exactly_shared_boundary` on purpose: a
sector filling a *hole* in another satisfies that and shares no ground at all.

## Draw order, and the two conditions that bear on it

Everything the renderer puts on screen rests on one predicate. `wallfront`
(`engine.cpp:2227`) takes two walls and the viewer and answers which is in
front -- except for two answers that are not answers: `-1` when the two segments
lie on one infinite line, `-2` when they properly cross. `bunchfront` passes both
through, and the sort does this with them (`engine.cpp:9736`)::

    closest = 0;              //Almost works, but not quite :(
    for (i=1; i<numbunches; i++)
        if ((j = bunchfront(i,closest)) < 0) continue;

A skipped pair is not resolved. Draw order falls out of enumeration order.

`bloodmap.drawsort` is that predicate transcribed, `dmulscale2`'s two-bit shift
included -- it floors, so a cross product of 3 reads as zero and two segments a
unit apart are called collinear. Because `-1` and `-2` do not depend on the
viewer, the whole map can be asked at once.

### It is a note, and the campaign is why

| | share of the campaign's 7,533 overlapping sector pairs |
| --- | --- |
| a collinear or crossing wall pair anywhere | 92.4% |
| ...with the spans actually meeting, or crossing | 91.1% |

Blood stacks space by putting one sector directly over another on the same
outline. Every wall of the one then lies on a wall of the other; that is the
technique, not a defect in it. Severity comes from the rate, so
`layer-unorderable-walls` reports and does not refuse.

**Read it next to `layer-overlap-in-one-view`.** What keeps the campaign's
stacked pairs safe is that the two halves are almost never reached by one flood.
A pair that is *both* unorderable and co-visible is the one to move. On MALTX
that conjunction named the two loading doors, which a pose sweep had already
found from the other end.

### The mechanism that actually tore this fragment

Not the skipped comparison -- instrumenting the sort's own skip site and
sweeping 1,696 poses showed only 11 of 64 holed views had one, and 39 views had
a skip with no hole. It was two other lines:

* a one-sided wall retires its screen columns whole once scanned
  (`engine.c:3216`), however few rows it painted; and
* `scansector` recurses into a neighbour only while a column of the portal is
  still open (`engine.c:3156`).

A sector whose floor is above the viewer's eye therefore paints almost nothing,
retires the columns anyway, and the room behind it is never scanned. **Do not
run an upper storey out to the wall line of the space below it, and do not put
an upper opening directly above a lower one.** Insetting the store roof and
widening two facade piers took the fragment from 64 holed views to 8, and the
worst frame from 93,972 unwritten pixels to 9,697.

### What does not work

`CSTAT_WALL_1WAY` (`engine.c:3134`) stops the flood, and it stops it in one
direction only, so it cannot resolve a symmetric fault: cutting the yard side
left the roof side intact. It was tried, measured (64 to 9, and the 9 were the
other half of the same problem), and reverted.
