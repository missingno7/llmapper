# BB2 — level understanding

This document is a design reading of Blood deathmatch map `BB2.MAP`. It is meant
to be usable by a later reconstruction agent that **never sees the MAP**. Exact
wall coordinates, sector indices, and tile-ID dumps are omitted on purpose.

Knowledge is marked:

- **Fact** — native parse, roundtrip, type catalog, or other source-backed field
- **Derived** — reproducible measurement (player-relative size, 2D sight, enclosure)
- **Interpreted** — design reading that an LLM or mapper may reject

---

## Level identity / overview

BB2 is a **square, walled deathmatch ground** with a large open exterior and a
cluster of masonry interiors punched into it. It is not a single-player
progression map: there are no enemies, no keys, and no exit channel.

**Fact.** The file is Blood v7 (`0x0700`). Native, LevelIR, and BuildIR
roundtrips are byte-exact. Structural validation reports 0 errors. Counts:
179 sectors, 1413 walls, 230 sprites; 58 XSECTOR, 20 XWALL, 171 XSPRITE.
Every sprite/sector/wall type used in the map is named in the NBlood catalog.

**Derived.** The axis-aligned bounding box is square: about **128 player-widths
on a side** (Blood body width 384). Sky-parallax sectors occupy about
**two-thirds of the footprint**; covered sectors occupy about one-third, even
though they are more numerous (116 covered vs 63 sky). The outdoor clear height
is typically **17–23 player heights**; covered interiors sit near the Blood
corpus median of about **5–6 player heights**.

**Interpreted.** The map reads as a cold, gray, open killing field wrapped
around brick-and-stone buildings, not as a white alpine vista. The community
label “snowy” is plausible for the outdoor floor, but isolated ART of that
floor is mottled gray and the current ontology calls it organic earth. The
stronger verified exterior signal is **sky parallax + huge vertical clearance +
gray ground**, not a dedicated snow material family.

---

## Game mode / purpose

**Fact.**

- 1 single-player start sprite and **8 deathmatch starts** (`kMarkerMPStart`)
- No dude sprites
- Reserved channel 8 (`kChannelLevelStartMatch`) is wired
- Team flag **bases** (`kItemFlagABase`, `kItemFlagBBase`) exist, and reserved
  channels 80/81 (`kChannelTeamAFlagCaptured` / `kChannelTeamBFlagCaptured`)
  listen on those sprites
- Pickups are weapons, ammo, health, armor, one cloak, Guns Akimbo, and the
  two flag bases

**Interpreted.** Primary purpose is **free-for-all deathmatch** on a shared
outdoor/indoor circuit. Flag bases and capture channels mean the same geometry
can host Blood’s team-flag mode, but nothing here proves the author balanced
it as CTF first. Treat flag bases as **team anchors and outdoor landmarks**
unless a later runtime check shows unique capture scripting.

---

## Spatial layout

Do not start from “courtyard / corridor / arena.” The independent views disagree
on how to cut the map, which is the point.

**Derived — geometry.** One large portal-connected component dominates. The
static traversal model finds **two navigation regions** (151 + 3 sectors). From
the single-player start, **154 sectors are reachable at rest** and **25 are
not**. Those 25 include closed movers, a few interiors, and the match-start
sound pocket. Deathmatch players do not spawn only in the at-rest reachable
set: some DM starts sit in covered interiors.

**Derived — overlapping hypotheses.**

- 19 perceptual-space clusters (largest 19 sectors): local portal+shade continuity
- 24 material-region clusters: raw tile continuity, not named rooms
- 23 mechanism regions: doors, slides, rotators, switches
- 11 vertical-layer pairs: XY-overlapping height relationships, including water

**Derived — outdoor vs covered.** Sky sectors: sky exposure 1.0, vertical
enclosure 0, openness ~0.56, still **laterally enclosed** (~0.87) because the
ground is a walled compound, not an open plane. Covered sectors: sky exposure
0, vertical enclosure ~0.59, openness ~0.25, slightly tighter lateral walls.

**Interpreted.** The useful cut is not sector count. It is:

1. a **large walled exterior** with sky and long sight
2. **masonry interiors** with lower ceilings and short sight
3. **gated pockets** behind movers (power items)
4. a **small underwater volume** on one side of the compound

The exterior is one continuous ground in the traversal model, but it is not one
perceptual room: buildings, fences, and height steps break sight and create
cover without disconnecting walkability.

---

## Important areas / spatial hypotheses

These are overlapping readings, not a room list.

### Open exterior ground

**Fact.** 63 sectors use ceiling parallax. Their floor tile is almost uniformly
the gray mottled ground; their ceiling tile is the sky sheet.

**Derived.** Several deathmatch starts sit here with footprints of **110–455
player-areas** and clear heights of **17–23 player heights**. 2D depth roses
from those starts reach **up to ~70 player-widths** before a wall, but every
ray eventually hits the compound boundary (`open_ray_count` 0).

**Interpreted.** This is the map’s shared hunting ground. Players leaving an
interior enter a space that is taller, brighter (sky), and much longer-sighted.

### Covered masonry interiors

**Fact.** Dominant interior fill tiles are brick/stone walls and a repeating
stone floor used against the ontology’s usual “vertical stone” role.

**Derived.** Indoor DM starts have footprints of **28–173 player-areas** and
clear heights around **5–11 player heights**. Maximum 2D sight from the most
enclosed of them is only about **12 player-widths**.

**Interpreted.** These are not a separate level; they are **buildings inside
the compound**. They compress sight, hide spawns, and store denser pickups.

### Flag-anchored ends

**Derived.** Flag A base sits next to an outdoor northern spawn (about 4.7
player-widths away, 2D sight clear). Flag B base sits next to a southern
covered spawn (about 3.6 player-widths, 2D sight clear).

**Interpreted.** The two flag bases mark **opposite ends** of the compound and
give those ends a unique identity even in free-for-all.

### Gated power pockets

**Fact.** Super armor lives in a sector whose ceiling is a Z-motion receiver
driven by two push switches. Guns Akimbo sits in a sector that is **not
reachable from the single-player start at rest**. Shadow Cloak sits with a
one-way switch. Tesla Cannon sits in an **underwater** sector.

**Interpreted.** High-value items are not sprinkled evenly on the snow. They
are **reasons to enter interiors, water, and switch rooms**.

### Water

**Fact.** Paired Blood water markers (`kMarkerUpWater` / `kMarkerLowWater`)
link two surface sectors to two underwater sectors. A third underwater sector
has the underwater XSECTOR flag but no marker pair. Surface floors use a
different tile than the outdoor gray ground.

**Interpreted.** A swimable pocket, probably at the compound’s edge, holding
the Tesla as a high-risk pickup. The unpaired underwater sector is a
connected pool continuation, not a second water system.

---

## Connectivity and circulation

**Derived.**

- 291 portals walkable at rest; 119 blocked or state-dependent
- Median portal width **2.67 player-widths**, matching the original Blood
  corpus median exactly
- Extreme portal slivers exist (down to 0.005 player-widths) — typical Blood
  decorative/sub-body geometry, not player routes
- Widest portals ~21 player-widths
- Two paired water links are the only recognized non-portal transitions
- No teleporters

**Interpreted.** Circulation is a **loop around and through buildings**, not a
hub-and-spoke with a single choke. The outdoor ground is the default connector
between interiors. Closed doors at rest create **optional indoor shortcuts and
item rooms**, not a required single-player lock sequence. The 25 at-rest
unreachable sectors are mostly those optional rooms plus movers.

Bottlenecks are **building entries and mover openings**, not the outdoor
field. The outdoor field is wide; the interiors are where routes collapse.

---

## Player-relative scale

Blood profile used: clip radius 192, body width 384, standing height 5632,
crouch 2048, step 4096. Corpus comparisons use original Blood map distributions
(median opening 2.67 widths, median clear height 5.82 heights, median sector
AABB width 3.5 widths).

| Observation | Player-relative | vs corpus |
|---|---|---|
| Whole-map AABB | 128 × 128 widths | Unusually large as a whole level box (not comparable to per-sector AABB) |
| Outdoor spawn footprints | ~110–455 player-areas | Large versus typical indoor rooms |
| Indoor spawn footprints | ~28–173 player-areas | Closer to ordinary Blood interiors |
| Outdoor clear height | ~17–23 heights | Unusually tall (corpus median ~5.8) |
| Indoor clear height | ~5–11 heights | Typical to slightly tall |
| Median portal | 2.67 widths | Typical |
| Comfortable fit | Almost all player routes | Sub-body slivers exist but are not the circulation graph |

**Fact / derived.** Floor Z is not a single plane. Unique floor elevations span
from a high outdoor/water band down through interiors and an underwater
volume. The outdoor playable ground itself sits on a small number of related
elevations; the “mostly flat” reading applies to **the sky-exposed ground**,
not to the whole MAP.

---

## Visibility / exposure / cover

Portal adjacency is **not** line of sight. A 2D XY ray vs occluding walls was
added for this experiment. Limitations: no height, slopes, sprites, lighting,
or translucency. Masked walls are treated as see-through.

**Derived.**

- Of 28 deathmatch spawn pairs, **only one pair has clear 2D sight**
- That pair is two **outdoor** starts; indoor starts do not see other starts
- Every spawn’s 32-ray depth rose is fully bounded by walls
- Outdoor starts: median occluder distance ~2–14 player-widths, max ~50–73
- Most enclosed indoor start: median ~2.7 widths, max ~12 widths
- From a large outdoor sector centroid: median sight ~26 widths, max ~45

**Interpreted.** Spawns are **mutually concealed** except across the open
ground. The design does not dump eight players into one visible pit. Cover is
produced by building mass and by the compound wall, not by a lot of blocking
world geometry (only 16 walls have the movement-blocking flag; 18 are masked).
Moving from interior to exterior is the main **exposure transition**.

Masked gib walls (see Mechanisms) are see-through until destroyed: they can
act as **visual windows / breakable screens** rather than hard cover.

---

## Enclosure / exterior character

The map supports an outdoor reading **from evidence**, not from the filename.

| Signal | Outdoor sectors | Covered sectors |
|---|---|---|
| Ceiling parallax | 63 / 63 | 0 / 116 |
| Sky sheet ceiling tile | yes | no |
| Vertical enclosure | 0 | ~0.59 |
| Sky exposure | 1.0 | 0 |
| Openness | ~0.56 | ~0.25 |
| Clear height | unusually tall | typical |
| Floor tile | gray mottled ground | stone/brick interiors |

**Interpreted.** Call the sky-exposed part an **open exterior compound**, not
wilderness: lateral enclosure stays high because a boundary wall exists. Call
the rest **interior-like pockets and buildings**. Some covered areas may be
porches or sheds rather than deep interiors; the sensor distinguishes sky vs
not-sky and height, not “porch.”

---

## Material and visual language

119 unique tiles appear. Only **30** are annotated in ontology v2. The Blood
campaign ontology was sampled from E-series maps; BB2’s heavy tiles 2455 and
2492 were not in that sample.

### What establishes the exterior

**Derived + appearance.**

- **Outdoor floor** — gray mottled repeating tile, 63 floor uses, ontology:
  horizontal floor, organic earth. Isolated appearance is dirty snow / stone /
  earth; **not a white snow field**.
- **Sky** — tall parallax sheet, 63 ceilings, ontology: sky sheet. Isolated
  preview is a dark vertical strip and is a poor human description of the sky.
- **Outdoor walls** — mix of gray masonry, dark pebble/organic fill, and brick.

### What establishes buildings

- **Red brick** fill (unannotated; BB2’s most-used wall tile after one
  campaign stone) — building skins
- **Campaign stone / brick** tiles used as both walls and, unusually, as
  **interior floors** (vertical-applicability stone used horizontally)
- **Interior ceilings** — a brick tile the ontology marks as vertical
  structural fill; BB2 uses it as a ceiling, matching a known conversion
  pitfall (this tile is mostly walls in the campaign)

### Trim, masked, interactive

- Masked overwalls use a small set of see-through / decal tiles (white streak
  panels, narrow overlays). 18 masked walls.
- Breakable gib walls share those masked faces.
- Switches: standard 32×32 switch family plus a second 32×32 control tile.
- Editor markers (ASOUND / SSOUND tiles) are invisible at runtime.

### Families that actually fire

Ontology families present: sky sheet, editor markers, switch-1070. The
iron-fence family is **not** a BB2 dominant. No liquid animation family on the
water surface.

**Gap.** 89 BB2 tiles have no ontology row. A reconstruction agent given only
this prose will know “gray ground, brick buildings, sky sheet, masked
breakables” but not the exact unused-in-campaign brick.

---

## Landmarks and orientation

**Derived / interpreted.** How a player knows where they are:

1. **Sky vs ceiling** — the strongest cue. Outdoor is tall and open; indoor is
   low and masonry.
2. **Flag bases** — unique team objects at opposite ends.
3. **Water / Tesla** — the only swimable volume, on one side, with a unique
   weapon.
4. **Super armor switch room** — two identical push switches for one ceiling
   mover; a memorable interior.
5. **Compound wall** — the world is a square box; the sky never continues
   forever.

Repetition risk: outdoor ground and sky tiles are uniform. Brick interiors can
feel similar. Flags, water, and the unusually tall outdoor height are what
break the camouflage. There is no unique skyline object (tower, statue) proven
from materials; landmarks are **mode objects and enclosure changes**, not a
named monument.

Lighting is not observed. Shade fields exist but were not turned into a
landmark sensor.

---

## Spawns and resources

**Fact.** 8 DM starts, 1 SP start (the SP start shares the large southern
outdoor ground with one DM start).

**Derived spawn character.**

| Spawn reading | Enclosure | Sight | Nearby resources |
|---|---|---|---|
| Large southern outdoor | sky, very open | long; the one mutual-sight pair | shotgun ammo almost underfoot |
| Other outdoor starts | sky, moderately open | long | armor / guns a short jog away, often without spawn-to-item sight |
| West indoor cluster | no sky, lower | short | TNT, gasoline, voodoo ammo; one indoor start can see voodoo ammo |
| Southern covered start | no sky | short | **Flag B** in clear sight, spirit/basic armor nearby |
| Northern outdoor start | sky, most open laterally | long | **Flag A** in clear sight, shotgun weapon in sight |

**Fact — pickup mix.** 8 weapons (shotgun, Tommy, flare ×2, Tesla, napalm),
47 ammo piles (heavy on flares, shotgun, TNT, remote, gasoline, Tommy drums),
7 health, 7 armor (including body, fire, spirit, super), Guns Akimbo, Shadow
Cloak, two flag bases. No Life Leech, no keys.

**Interpreted deathmatch logic.**

- Spawns are **spread around the square**, not stacked in one building.
- Indoor spawns are **protected from spawn-to-spawn peeking**.
- Outdoor spawns are exposed to the field but not to most other spawns.
- Flag bases double as **end-of-map beacons**.
- Tesla is a **high-risk swim**.
- Super armor and Akimbo are **gated**, so they pull players off the field
  into interiors / switch puzzles.
- Napalm sits on outdoor ground nearer the middle than Tesla — a field prize
  rather than a water prize.
- Ammo is abundant; the map expects constant fire, not resource famine.

---

## Mechanisms and dynamic behavior

Every extended/special object was inventoried. None remain unnamed. Runtime
was **not** stepped in NBlood; busy-time motion is described from XSECTOR
off/on Z, markers, and NBlood type semantics.

### Match start

Reserved channel 8 (DM/team start) is received by an invisible toggle sprite
that one-shots channel 119 into a `kSoundPlayer` (sample 3301). Launch flags
on that pair are not bloodbath-enabled. **Interpreted:** a start sting for
single/coop loads of this DM map; whether NBlood plays it in bloodbath is
unverified.

### Flag capture listeners

Channels 80/81 have **no map transmitters**. The engine is the sender. The
receivers are the flag-base sprites. No extra map-side capture choreography
was found.

### Water

Two marker-paired water links (ids 1 and 2). Three underwater XSECTORs.
Surface is sky-exposed; underwater is covered. Tesla is in the underwater
volume.

### Push Z-motion (lifts / hatches / doors)

Several sectors are `kSectorZMotion` with wall-push or push triggers and no
RX. They move floor and/or ceiling between authored off/on Z:

- Outdoor floor drop (~6 player heights) — a sky-exposed lift/platform
- Ceiling-only movers (doors/hatches), some with wait times so they close
- Combined floor+ceiling squeezes (crushing or window-like opens)
- A fast floor+ceiling pair driven by a wall-crack transmitter (destructible
  opens a mover)

Busy times are short (often 5–10). These are **local doors and lifts**, not a
map-wide elevator network.

### Linked door chains

User channels 100–119 implement ordinary Blood TX/RX:

- Floor trigger in a vestibule **slides** a marked door (channel 100)
- A Z-motion **links** a dummy receiver (101) — lighting or companion sector
- Four push walls open a **slide-marked** door (103)
- Two 1070 switches raise a **ceiling** then **link** a companion sector
  (104 → 105) — the super-armor treatment
- Toggle walls drive a slide that starts **already on** (106)
- Push walls open another slide (107)
- A big Z-motion **links five receivers** (108) — a multi-sector door/light
  group on an indoor spawn’s neighborhood
- Push Z-motion links one companion (109)
- Two **rotators** toggle/link each other (110/111) — a paired spinning
  door/poly
- A switch opens three Z-motion floors together (112), one of which **ons** a
  ceiling mover (113) and another **links** two more sectors (116)
- Another switch turns a rotator (115)
- A rotator links two companions (114)
- A slow rotator links one companion (117)
- Wall crack opens a squeeze mover (118)

**Interpreted.** This is a **toybox of Blood door types** (Z, slide-marked,
rotate) wrapping item rooms, not a puzzle campaign. Most movers start **off**
(closed). One slide starts **on**.

### Breakable walls

Ten `kWallGib` walls, vector-triggered, data 12 or 13, masked and blocking.
They are local destructibles (windows/screens), not wired into the channel
graph except where a crack sprite transmits.

### Ambient and sector sound

37 `Ambient SFX` sprites (type 710, stat ambience, picnum ASOUND). NBlood
`asound.cpp` uses data1/data2 as distance range, data3 as SFX id, data4 as
volume-related. All start **on**. Distinct ranges cluster as close/medium/far
beds (SFX ids include 18, 27, 29, 32, 34, 39).

17 `kSoundSector` sprites sit on mover sectors (door sounds). 10 water-drip
generators decorate interiors. One player SFX is the match-start sting.

### Decor and hazards

Wall cracks, gib objects, explode objects, two torches, one candle, plus
ordinary decoration sprites (trees/props). Explode objects carry data that
looks like blast parameters; they are not channel-wired.

**Nothing unexplained remains except runtime feel** (exact door speed in
seconds, whether crush kills, whether type-710 beds are audible in bloodbath).
Those are oracle gaps, not missing object names.

---

## Important relative transitions

Measured differences; names are interpreted.

1. **Interior → exterior.** Sky 0→1, vertical enclosure ~0.6→0, clear height
   ~5→~18 player heights, 2D sight max ~12→~50+ widths. This is the map’s
   strongest change.
2. **Wide ground → building mouth.** Median portals stay ~2.7 widths, but
   visible depth collapses and the floor tile switches from gray ground to
   stone/brick.
3. **Field → water.** Sky remains on the surface; crossing the marker pair
   puts the player underwater with a unique weapon and no sky.
4. **Open spawn → gated item.** Super armor / cloak / Akimbo require a switch
   or a closed mover. Choice count goes up (fight on the field vs commit to a
   room).
5. **Low-choice outdoor edge → high-choice building cluster.** The west indoor
   cluster is where indoor DM starts, TNT, and gasoline pile up.

None of these is proven as a scripted “reveal.” They are the places the
sensors show the largest relative jumps.

---

## Likely deathmatch design logic

**Interpreted.**

BB2 wants players to **circulate the compound**, duck into buildings for
armor and ammo, and periodically risk a gated prize or the water Tesla. The
open ground is the meeting space; interiors are respawn cover and loot
closets. Mutual spawn sight is almost zero, so spawn camping across the map
is hard, but an outdoor player can still control long sightlines once they
leave their alcove. Flags, if used, turn the north and south ends into
objectives; in FFA they still prevent the two ends from feeling identical.

The map is generous with ammo and light on unique weapons. Power is in
**position and armor**, plus a few gated/high-risk pickups.

---

## Uncertainties / things not proven

- Isolated ART does **not** prove “snow.” Gray ground + sky is proven.
- 2D sight can lie about windows, ledges, and height separation.
- No renderer, so lighting, fog, vis, and true 3D occlusion are unknown.
- Mover gameplay (crush, exact timing, whether a slide blocks sight while
  closed) is inferred from types and Z deltas, not from an NBlood tick.
- Channel 8 / 80 / 81 engine sends were not captured in a runtime log.
- Type 710 ambience volume/falloff was not heard.
- Unpaired underwater sector  — connected pool vs authoring leftover.
- Whether Guns Akimbo is reachable in DM without the SP-start traversal graph
  (likely yes via a mover or a DM spawn neighborhood; not measured as a
  player route).
- 89 tiles have no ontology annotation.
- Corpus percentile attachment failed on a summaries-only JSON; comparisons
  above use published medians, not per-observation percentiles.

---

## Reconstruction bottleneck (what this text still cannot give)

If BB2.MAP were erased and only this document remained, a competent mapper
could reproduce: square walled compound, sky exterior vs brick interiors,
eight spread spawns, flag-end anchors, water Tesla, gated super armor,
toybox doors, gray ground, brick skins, almost no spawn-to-spawn sight.

They would still lack:

- Exact building footprints and courtyard proportions
  (**deliberately omitted**)
- Which brick variant goes on which wall (**sensor + ontology gap**)
- True 3D vis from eye height (**sensor gap**)
- Lighting mood (**sensor gap**)
- The precise switch-to-door choreography timing (**partially derived**)

That split is the point of the later reconstruction experiment.
