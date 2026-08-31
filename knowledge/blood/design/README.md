# Blood design-pattern knowledge

Versioned hypotheses discovered from original Blood maps. Names are
**INTERPRETED**. Signatures and occurrence counts are **DERIVED**.

Do not treat generated reconstructions as evidence.

```text
python knowledge/blood/design/compile_catalog.py
```

requires local unsigned mines in `work/` (gitignored). The compiled
[`catalog-v1.json`](catalog-v1.json) is the retrieval surface.

| file | role |
| --- | --- |
| `compile_catalog.py` | pattern templates + occurrence attach |
| `catalog-v1.json` | versioned hypotheses with original-map occurrences |
| `door-families-v1.json` | compact campaign door-family / key-emblem retrieval hints |
| `owner-anchors-v1.json` | owner hand-tagged picnum semantic anchors (probes, not lookup rules); records dual roles (e.g. 1165 wall clock is also a shootable switch) and intact/broken state pairs |

Door implementation families and key-signifier co-occurrence live in
[`reports/blood-door-families.json`](../../../reports/blood-door-families.json)
and [`reports/blood-key-signifiers.json`](../../../reports/blood-key-signifiers.json).
They are retrieval, not prefabs.

See [docs/door-affordances.md](../../../docs/door-affordances.md).

## How this knowledge reaches a map

This directory is a retrieval surface, not a second authoring language.  A map
uses it through the shared constructors: `art` supplies tile dimensions,
`surfaces`/`materials` carry finish vocabulary, `decoration` supplies attested
appearance, `doors`/`aperture` implement mechanism and leaf conventions, and
`lightbomb` derives illumination from declared sources.  A project should record
its one-off choice in source and its evidence in a report; a repeated need must
be promoted to the relevant `bloodmap` constructor and regression test.  The
[shared authoring toolkit](../../../docs/authoring-toolkit.md) gives the full
routing and ownership rule.

SP mechanism compositions from E2M2 (fan-out TX/RX, single motion gates) were
searched on the 43-map campaign and stored in
[`reports/E2M2-mechanism-patterns.json`](../../../reports/E2M2-mechanism-patterns.json).
They are not catalog-v1 entries until `compile_catalog.py` grows a mechanism view.

See [docs/design-pattern-discovery.md](../../../docs/design-pattern-discovery.md).

## Campaign design norms

[`norms-v1.json`](norms-v1.json) is the observed range of 42 measurements across
the 43 campaign maps, built by `tools/design_norms`:

```text
python -m tools.design_norms --corpus maps/blood -o knowledge/blood/design/norms-v1.json
python -m tools.design_norms --against <candidate>.MAP --norms knowledge/blood/design/norms-v1.json
```

The range is what the campaign happens to contain, never a target, and there is
no score. What makes it usable is the `consensus` list, which ranks each metric
by how tightly the campaign holds it. A metric held within a narrow band across
43 levels of wildly different themes is a convention; one that ranges over an
order of magnitude is a free choice, and being outside it means nothing.

The ten tightest, in order:

| axis | q1 | median | q3 |
| --- | ---: | ---: | ---: |
| `topology.mean_degree` | 2.51 | 2.7 | 2.92 |
| `shape.median_height` | 32768 | 33280 | 39936 |
| `shape.walls_per_sector` | 7.1 | 7.8 | 8.9 |
| `shape.height_iqr_ratio` | 1.71 | 2.0 | 2.21 |
| `population.weapons_and_ammo` | 52 | 59 | 76 |
| `population.pickups` | 71 | 84 | 107 |
| `population.pickups_per_dude` | 0.71 | 0.9 | 1.14 |
| `topology.dead_end_fraction` | 0.135 | 0.176 | 0.223 |
| `population.distinct_dude_types` | 7 | 11 | 13 |
| `topology.loops_per_100_sectors` | 27 | 36.4 | 47.4 |

Sky fraction, key count, absolute loop count and moving-sector count are at the
*loose* end: the designers varied them freely, so a candidate that differs there
is exercising a choice rather than breaking a convention.

Placement follows conventions of its own, measured the same way: 89% of playable
sectors hold no enemy at all, the nearest one is a median 3 hops from the spawn,
and pickups sit in dead ends slightly more often than enemies do (17% against
12%, where dead ends are 17% of sectors).

## Which texture, which decoration, which mechanism

Three mining passes, each answering an authoring question rather than a census
question. They share a discipline: the evidence has to be conditioned on
something the designer knows *before* deciding, or it can only mark work already
done.

### Textures — inherit, do not look up

[`surface-palettes-v1.json`](surface-palettes-v1.json), from
`tools/mine_surface_palettes`. Read `predictors` before the tables. Four ways to
guess a sector's surface, scored against the campaign:

| predictor | wall | floor | ceiling |
| --- | ---: | ---: | ---: |
| the map's favourite tile | 38% | 35% | 34% |
| the space context (area, height, sky) | 45% | 49% | 54% |
| **its portal neighbours** | 58% | 67% | 71% |
| **neighbours in the same context** | **60%** | **71%** | **76%** |

So a surface is mostly *inherited* and only occasionally *decided*. That is what
a person does: paint a region, change the finish where the space changes. A
generator that picks each sector's tile independently from a per-context table
cannot produce that, however good the table is.

It is also why the per-context tile lists transfer badly between episodes: held-
out agreement is only 11-23%, because **each episode has its own art set**. The
conditioning is sound (it saves 1.5-5 bits against the marginal); tile identity
simply is not a portable fact. Use the tables within a map, and the propagation
rule between them.

The existing visual clusters cannot stand in for the tiles here: `cluster:usage:0000`
holds 1,053 tiles and covers 99.9% of wall surfaces, so grouping by it makes any
transfer test pass trivially.

### Decoration — the size belongs to the tile

[`decoration-v1.json`](decoration-v1.json), from `tools/mine_decoration`, over
the 3,159 visible untyped sprites in reachable sectors.

* **60% are drawn at `y_repeat` 64** -- the tile's natural size -- and 73% at a
  power of two. The whole campaign uses 53 distinct repeats.
* **15 of the 36 common decoration tiles are never resized at all**; only 5
  genuinely scale with the room (median |r| between drawn size and room height
  is 0.20).
* **Alignment belongs to the tile too**: 506 is face-aligned in 100% of its 138
  uses, 2540 wall-aligned in 100% of 69, 2915 floor-aligned in 100% of 147.

`bloodmap.vocabulary.sprite_repeats` asks the author how tall a decoration
should be and derives the repeat. That is the right calculation and the wrong
question -- the height is a consequence of choosing the tile, and asking for it
invites a size the campaign never uses.

Density: only about 10% of playable sectors carry any decoration at all, a
median of 1 in those that do, p90 of 5.

### Mechanisms — a level is dozens of small networks

[`mechanisms-v1.json`](mechanisms-v1.json), from `tools/mine_mechanisms`.
The median campaign map runs **47 user channels** (p90 96, max 147), a median of
3 objects each.

| shape | share |
| --- | ---: |
| fan-out (one trigger, several receivers) | 29% |
| one-to-one (a switch and its door) | 32% |
| fan-in (several triggers, one receiver) | 16% |
| mesh | 11% |
| orphan receiver / transmitter | 7% / 5% |

Fan-out and fan-in together (45%) outnumber the plain switch-and-door pairs, so
"advanced" is the normal case rather than the exception. The commonest receivers
are the exploder (459), Z-motion (600), switches (20), marked slides (614) and
generators (708/710).

The orphans are worth noting: the campaign carries 12% of its channels with one
end missing, so a converted or generated map with a few dangling channels is in
normal company rather than broken.

### From evidence to behaviour

Two of the three findings are now code rather than only knowledge.

[`bloodmap/decoration.py`](../../../bloodmap/decoration.py) is generated from
`decoration-v1.json` and answers "how is tile N normally drawn": canonical
repeat, structural cstat, shade. `decoration_appearance(picnum)` is the
decoration counterpart of `item_display.sprite_appearance`, which only ever
covered sprites that carry a gameplay type. `is_confident(picnum)` says whether
the campaign is settled enough to copy -- 20 of the 60 well-attested tiles agree
on both size and mounting above 60%, and the rest genuinely vary, so presenting
their mode as a convention would be inventing one.

`materials.floor_patch_share` and `materials.ceiling_patch_share` in
`bloodmap/level_profile.py` measure the propagation finding directly: the share
of a level's sectors sitting in a run of three or more that share a finish. The
campaign runs 0.66-0.83 on floors and 0.70-0.85 on ceilings. A level that names
a finish per room scores near zero however plausible each choice was, which is
what makes the measure worth having.

No adjacency-propagation mechanism was added, because the hierarchy already is
one: an assembly carries a `Style` and its rooms inherit it, which produces
exactly the few-large-patches-plus-exceptions shape the campaign has. The gap
was never the mechanism, only the measurement.

### Water

191 marker pairs across 24 of the 43 campaign maps. `kMarkerUpWater` (tile 2332)
sits in the pool and `kMarkerLowWater` (2331) in the sunk sector, matched on
`XSPRITE.data1`, both on statnum 0 at cstat 128.

The geometry is the surprising part. **152 of the 191 pairs join sectors that
are congruent but somewhere else entirely** -- the underwater room is a copy of
the pool's footprint parked in free map space, not a volume beneath it. That is
how Blood gets a dive without stacking geometry, and it means the sunk rooms
share no wall with the dry level at all.

* the *lower* sector carries `Underwater`; the upper one does not, in 180 of 191
  pairs -- the surface is air you dive through;
* the up marker sits between its sector's floor and ceiling (187 of 191), the low
  marker on the sunk sector's ceiling (169);
* sunk volumes run a median **8.7 player heights** deep, and a map with water has
  a median of **15** underwater sectors, so it is an area rather than a pool.

#### A count is not a norm

`consensus` ranks metrics by how narrow a band the campaign holds them in, on
the reasoning that a narrow band is a convention and a wide one is a free
choice. That reasoning fails for metrics that are *counts*. The campaign's 43
maps are all roughly one size, so `population.pickups` looks like one of its
tightest agreements -- and then reads as a five-fold failure on any level built
to a different scale, which says nothing about the level except how big it is.

The monastery is the worked example. It failed `population.pickups` (13 against
71..107) and `population.weapons_and_ammo` (8 against 52..76) while sitting at
**26.0 pickups and 16.0 weapons per 100 sectors**, both inside the campaign's own
rates of 22.8..44.3 and 15.2..34.6. Nothing was wrong with its population; it is
a sixth the size.

`design_norms.SIZE_DEPENDENT` now keeps such metrics out of `consensus` while
leaving them in `metrics`, because the count is still a real fact about the
campaign -- it just cannot judge a level. Where a count mattered, the rate is
carried alongside it (`pickups_per_100_sectors`, `weapons_per_100_sectors`,
`dudes_per_100_sectors`).

#### The dive must not be a wormhole

Because the sunk rooms sit in free map space, nothing in the format stops two
pools that share one flooded region from diving by *different* offsets. When
that happens the player swims a few seconds between two mouths that a walk would
take a minute to connect, and the water reads as a teleporter with a swimming
animation.

The campaign's rule for this is sharp once the condition is stated correctly.
Over every pool pair sharing a single underwater region:

| both mouths reachable on foot? | same translation | different | agree |
| --- | ---: | ---: | ---: |
| **yes** | 630 | 4 | **99%** |
| no | 8 | 100 | 7% |

So the translation is pinned exactly when the player can make the same trip both
ways and compare them, and is free otherwise. Two genuinely separate flooded
places owe each other nothing. This is worth stating carefully, because the first
reading of the same data -- "32% of underwater regions keep one translation" --
averaged a near-law together with a free choice and concluded, wrongly, that it
was a weak convention.

`level_profile.water_wormholes` reports the offending pairs, and `water.wormholes`
carries the count. The four campaign exceptions miss by 4 to 18 player widths
(E4M3, E1M6, E2M5, E2M7), which is mapper drift rather than a second convention.

This changed a measurement as well. `topology` now counts the graph
`analyze_reachability` walks -- walls plus water links, stack links and
teleporters -- rather than the wall graph. A level whose shortcut is a dive has
that loop in play whether or not it has it in geometry, and 24 of 43 campaign
maps carry water, so it is not a corner case. The norms were recomputed against
the same graph: `mean_degree` q1 rose 2.51 to 2.60 and `loops_per_100_sectors`
q1 27 to 30.


## Looking at the level, not at the file

Every mining pass above reads the map. `tools/mine_visual_norms.py` reads the
*frame*: it stands the camera in each room of each campaign map, asks the
XMapEdit observer what the renderer painted, and aggregates 1,673 frames across
the 43 maps into bands a level can be judged against.

That is worth a separate pass because the faults found by looking at the
monastery were never faults the map file could show -- a fence sunk to its
waist, a door face on the inside of its own frame, a grille edge-on in a
doorway. The map says what exists; only the renderer says what is seen.

Four things per frame, all ratios so a large map and a small one compare:
`composition` (the share of painted pixels that is floor, wall, upper, lower,
sprite, ceiling, sky, masked), `tile_variety`, `depth` (distinct sectors in
frame) and `shade_spread`. Each map contributes its own median, so a
three-hundred-sector level does not outvote a fifty-sector one.

### How Blood lights a room

The first thing the visual norms caught was that the monastery was flat, and the
map file agreed: the **spread of shade across a single sector's walls** was 0 in
every room, against a campaign median of 12 (q1 2, q3 22). One `shades(value)`
call had given each room one wall shade.

Three hypotheses, measured across the campaign's playable sectors:

| grouping walls within a room by | explains |
| --- | ---: |
| the **direction each wall faces** | **81%** |
| the **texture** each wall carries | 52% |
| whether the wall is a portal or solid | 0% |

And a fourth: walls within four player widths of a lamp sit at q1 −10 against
+8 for walls beyond one — real, but lamps are rare (about one torch per hundred
playable sectors), so they cannot account for much.

The important part is what has **no** global bias. The median shade offset is 0
for every one of the eight facing octants, and 0 for every common wall tile. So
there is no rule that north walls are dark or that brick is bright. The rule is
*within a room*: walls facing the same way share a shade, and the room has an
implied direction the light comes from — chosen by the author, differing room to
room, which is exactly why the octant medians cancel.

`bloodmap/lighting.py` reproduces the reconstructible part. Every room gets a
direction — its lamp where it has one, its widest opening where it does not —
and its walls are offset by ±6 on the cosine of how they face it. The monastery
went from 0 rooms with any variation to 50, at a median spread of 12, which is
the campaign's own median.

The honest limit: this recovers the *structure* of Blood's lighting, not its
judgement. A mapper choosing which corner of a room is bright is making a
decision about where the player should look, and a widest-opening heuristic is
only a plausible stand-in for it.


## Asking whether it would pass

"Inside q1..q3 on most metrics" is a weak claim: a level can sit inside every
band one at a time and still be obviously synthetic, because what gives it away
is the combination. `tools/map_discriminator.py` asks it properly. Every map,
campaign and candidate alike, becomes one feature vector; each is scored against
the *others*, leave-one-out, so a campaign map is never judged against itself;
and the scores are ranked together.

The score is the 90th percentile of per-feature distance from the others'
median, in units of their IQR. A high percentile rather than a mean, because a
level is given away by its worst few properties -- averaging lets one absurd
property hide behind fifty ordinary ones.

Two mistakes are worth recording, because both would have made the exercise
meaningless.

**Counting size as character.** The first run put `topology.sectors` (50 against
a campaign median of 302), `topology.portals` and `topology.independent_loops`
among the candidate's worst deviations. All three said the same uninteresting
thing -- the level is smaller -- and a discriminator that scores small maps as
fakes has learned to detect size, not authorship. `SIZE_FEATURES` excludes every
raw count; rates, shares and ratios stay.

**Reading a low score as success.** The outlier score is one-sided. A level
fitted to a corpus passes it easily, and passing it *too well* is its own tell.
So the tool reports a second statistic, `blandness`: the share of features
sitting within a quarter IQR of the corpus median. Every real map has
idiosyncrasies -- one unusually vertical, another unusually dark -- because it
was built to be a place rather than to match a distribution.

The monastery, as of this pass:

| | candidate | campaign |
| --- | ---: | --- |
| outlier score | **0.81** | 0.60 .. 4.00, median 1.18 |
| blandness | **0.54** | 0.17 .. 0.65, median 0.38 |

So it is not separable by either statistic -- but it is blander than 38 of the
43, which is the honest reading: it sits near an edge that a better
discriminator could still exploit. Matching a distribution is not the same as
having been designed, and this measures the first.


## Light that moves

The `LIGHTING-LIGHTS` sample carries an `amplitude` on 52 of its sectors, and
around it a whole subsystem the campaign mining had never named: `shade_wave`,
`shade_frequency`, `shade_phase`, `shade_always`, which of floor/ceiling/walls
the effect touches, and `colored_lights` with a second palette per surface.

Measured back against the campaign, it is not a curiosity. **20.7% of playable
sectors animate their shade** -- a median of 17% per map, q1 8.7%, q3 29%. The
monastery animated none.

`sectorfx.cpp` adds `GetWaveValue(wave, phase*8 + freq*totalclock, amplitude)`
to the sector's shade each tick, and the wave is a table index rather than a
shape: 0 is constant, 5 is a sine, 10 is a strobe, and **6 to 9 are four
irregular flicker tables**. The campaign's commonest is wave 7, `flicker2`, in
1,205 of its 2,823 animated sectors -- which is a torch, not a pulse.

Two conditions decide whether anything happens at all:

* `shadeAlways` -- the code reads `if (pXSector->shadeAlways || pXSector->busy)`,
  so without it the effect runs only while the sector is *moving*. The 1,194
  campaign sectors that leave it clear are lifts and doors. A room that merely
  has a torch in it needs it set.
* a lamp -- 65% of campaign sectors containing a torch or hanging lamp are
  animated, against 20% of those without.

`lighting.flicker_lit_sectors` follows that: every room with a lamp gets wave 7
at amplitude -4, all three surfaces, `shadeAlways`, and a phase derived from the
sector index so the torches do not breathe in unison. The campaign spreads 148
distinct phases across its 1,629 always-on sectors, which is the same intent.

The monastery now animates 9 of its 64 sectors, 14%, inside the campaign band.

### A pass that reported nine and changed none

Worth recording because it very nearly shipped. The first version allocated its
XSECTORs through `LevelBuilder`, whose constructor is
`self.level = copy.deepcopy(level)`. So the pass mutated a throwaway, returned
`sectors_flickering: 9`, and the emitted map had none. A finishing pass has to
edit the level it was handed, and the only reason this was caught is that the
check afterwards read the built file rather than the pass's own return value.


## What a Blood level is made of

The plan to reach E1M1's complexity started from a wrong premise -- that it
needed ninety more *rooms*. It does not. **E1M1 is not 155 rooms.** 68% of its
sectors are under 20 player widths squared and 40 are under 4: it is roughly 46
real spaces and roughly 100 small ones, and the small ones are what the player
walks past.

`tools/mine_prefabs.py` classifies every small sector in the campaign by what it
does for its neighbours -- which is a question about the graph, not the shape,
since the same rectangle is an alcove, a bay or a tread depending on what it
opens onto:

| kind | count | per map (q1/med/q3) | what it is |
| --- | ---: | --- | --- |
| junction | 2548 | 24 / 47 / 95 | three or more ways meet, and a cycle closes |
| link | 2337 | 24 / 45 / 66 | a short run between two spaces |
| alcove | 1793 | 22 / 39 / 56 | a dead end cut into one wall |
| arch | 812 | 6 / 18 / 27 | a lowered ceiling between two spaces |
| tread | 797 | 4 / 11 / 26 | a step |
| bay | 614 | 7 / 12 / 20 | a niche opening onto two spaces that touch |
| branch | 593 | 2 / 10 / 19 | three or more ways meet, no cycle |

**A third of all 9,494 small sectors close a triangle** -- their neighbours
already touch, so the small sector is an alternative way round rather than a
pocket. The campaign median is 60 per map. This level had 5 of 38, which is why
its loop count and its sector count were short by the same factor: they were one
shortfall counted twice.

### And the props

The single largest difference between this level and E1M1 was not architecture
at all. E1M1 carries **183 breakable things** -- `kThingObjectGib` (416) and
`kThingObjectExplode` (417) -- against this level's 3. The campaign runs a median
of 33 per 100 playable sectors. Both types sit on statnum 4 and both need
`data_1`, which names the gib or the explosion; a prop without one breaks into
nothing.

### The plan, and where it stands

1. **Mine what the small sectors are** -- done, `mine_prefabs`.
2. **Constructors that produce them by the wall rather than one at a time** --
   `prefab.alcove_run` takes a wall and fills it, skipping the spans where a
   doorway or another room is already behind it. Alcoves went 5 to 31, inside
   the campaign band, in eleven calls.
3. **Props** -- `prefab.BREAKABLES` carries the campaign's modal form for three
   tiles. Things per 100 sectors went 3 to 39.
4. **Still to build**: `bay` and `junction` constructors. Alcoves are dead ends,
   so adding thirty of them raised the sector count and *lowered* mean degree.
   Loops are still 13 against E1M1's 38, and that gap will not close until the
   small sectors being added are the kind that close cycles.

| | before | after | E1M1 |
| --- | ---: | ---: | ---: |
| sectors | 64 | 90 | 155 |
| walls | 471 | 627 | 1498 |
| sprites | 134 | 166 | 559 |
| things per 100 sectors | 3 | 39 | 125 |
| loops | 13 | 13 | 38 |

### Two tool lessons from building it

`alcove_run` needed the region's own outline to tell it which way to cut, because
the same two points build a niche in the wall or a niche in the middle of the
room depending on the order they are given in -- not a decision an author should
be making. And its collision test needed edges as well as point probes: two
rectangles can overlap at a corner with neither's sampled interior inside the
other, which is exactly what slipped through the first version.


## The camera was in the wrong place

Every visual measurement in this project was taken from 3000 z units above the
floor. Blood's standing eye is `eyeAboveZ` in the posture table, `0x1600` =
**5632**; 2048 is the crouch. So the camera was somewhere between crouching and
standing, and the number was invented when `player_space.PLAYER_PROFILES`
already carried the right one.

The campaign and the candidate were both measured that way, so the *comparisons*
were not nonsense -- but the ranking they produced was, and it flattered the
level badly:

| | from 3000 | from 5632 |
| --- | ---: | ---: |
| discriminator score | 0.65 | **1.36** |
| rank against the campaign | 3 of 44 | **32 of 44** |
| `visual.depth` | 3.0, reported as a top failing | **5.0, inside the band** |
| `visual.composition.wall` | inside the band | **0.665 vs 0.472..0.547** |
| `visual.contrast` | inside the band | **28 vs 44..51.5** |

Two conclusions were simply wrong. Sightline depth was named as one of the
level's largest gaps across several passes; from standing height it is fine. And
the three faults that actually dominate -- too much wall in frame, too little
contrast, too little shade spread -- were invisible, because crouching puts more
floor and less upper wall in view.

The general lesson is narrow and worth keeping: **a measurement taken from the
wrong place is worse than no measurement**, because it produces a number that
looks like evidence. The eye height was available from the profile, derived from
the engine, and was not used.
