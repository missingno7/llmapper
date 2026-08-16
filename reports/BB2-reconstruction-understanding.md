# Independent understanding: `work/BB2-semantic-reconstruction.MAP`

This reading uses only the candidate MAP, general llmapper sensors, Blood type
and material knowledge, and the construction/runtime contract. It does not use
a prior description of another map.

Sensors: lossless parse, `contents`, `inspect-space`, `analyze-space`,
`sightline --spawns`, `spawn-neighborhood`, `route-exposure`, `morphology`,
Blood ontology v2 for tile roles. 2D sight ignores height, sprites, and
lighting. Traversal is at-rest portal walkability plus recognized water links.

---

## What this map is

A Blood v7 (`0x0700`) deathmatch compound: eight `kMarkerMPStart` sprites with
bloodbath launch, one unused-for-DM single-player start, Team A/B flag bases,
and no unknown sprite types. The file roundtrips and validates. The authored
board is a square 80 × 80 player-width AABB.

The playable idea is an **enclosed outdoor majority** with a **west indoor
strip**, a **south covered porch**, a **central covered pavilion**, **north
covered sheds**, and an **east water / underwater pocket**. Sky-parallax
ceilings cover 78 of 112 sectors and about three-quarters of the 2D footprint
(4885 of 6544 player-areas). Covered space is the remainder (34 sectors, 1658
player-areas). One at-rest navigation region holds 100 sectors; 11 sectors are
statically unreachable from the start (closed Z-doors, the deeper underwater
cell, and leftover grid cells that were never portaled).

---

## Exact contents

| | count |
| --- | ---: |
| sectors / walls / sprites | 112 / 448 / 64 |
| XSECTOR / XWALL / XSPRITE | 5 / 1 / 64 |
| parallax ceilings | 78 |
| masked walls | 1 |
| DM starts / SP starts | 8 / 1 |
| pickups | 41 |
| Z-motion sectors (type 600) | 3 |
| one-way switches | 4 |
| water up/down markers | 2 pairs |
| Ambient SFX (710) | 3 |
| player SFX (711) | 1 |
| water drip generator (701) | 1 |
| gib wall (511) | 1 |

Pickup mix: 2 flags, 8 weapons, 18 ammo, 6 health, 5 armor, 2 powerups.
No keys. No unknown types.

Header visibility is 800. Sky type 2, sky bits 4. Lighting is almost uniform:
floor shade 16 on 109 sectors (8 on the three water-surface cells), wall shade
8 everywhere, ceiling shade 0 everywhere.

---

## Player-relative scale

Blood body width 384, standing height 5632.

- Board AABB: **80 × 80** player-widths, nearly square.
- Whole footprint: **6544** player-areas (slightly above the 6400 AABB because
  the underwater stack overlaps XY).
- Sky selection: AABB 80 widths, footprint 4885 areas, **clear height 20
  player-heights** on every sky sector (floor Z = 0, ceiling Z = −112640).
- Covered selection: same 80-width AABB (structures are scattered through the
  square), footprint 1658 areas, **median clear height 6 player-heights**.
  Range includes 0 (three rest-closed Z-doors) and a max of 8 heights in the
  deeper underwater cell.
- Openings among selected portals: min **2.67** widths (1024), median **8**
  widths (3072), max **24** widths (9216). The same min/median/max appear in
  both sky and covered selections — the grid uses a small set of cell sizes.

Outdoor floor Z is a single plane. Covered floors are that same plane except
the two underwater sectors (Z = 6 and 8 player-heights below). There is no
outdoor terrace, step, or lift.

Relative to a standing Blood player, the outdoor volume is a tall sky box
(~20 heights) and the interiors are ordinary rooms (~6 heights). The indoor →
outdoor start-group height ratio is **3.33**. Sky exposure of those groups is
0.0 → 1.0.

---

## Traversability and circulation

`analyze-space` reports 126 walkable-at-rest portal edges and 6
blocked/state-dependent edges (the closed Z-doors). Two `paired_water_link`
non-portal transitions join east surface water to the underwater chamber.

The map is a **Cartesian grid of rectangles**. Circulation is ring-like around
a central covered pavilion, with:

- a long **west indoor** north–south run (brick, 6-height ceiling);
- a **south covered porch** opening toward the south ring;
- **north covered sheds** that break the north yard;
- an **east water bay** in the outdoor ring.

Indoor multiplayer starts sit 1, 3, and 5 portal hops from the largest sky
component. Several outdoor starts are already in that component (0 hops). One
northwest outdoor start is 2 hops away and only 5/32 of its 2D rays sample
into that main sky region — a sky-ceiling pocket that does not see the main
yard.

Shortest start → largest-sky-sector routes:

| start | hops | sky sample fraction | cover↔sky transitions | mean max 2D sight (widths) |
| --- | ---: | ---: | ---: | ---: |
| sprite:54 (north yard) | 12 | 1.00 | 0 | 50 |
| sprite:55 (NE) | 8 | 1.00 | 0 | 56 |
| sprite:56 (NW pocket) | 14 | 0.93 | 2 | 56 |
| sprite:57 (SW) | 10 | 1.00 | 0 | 56 |
| sprite:58 (SE) | 4 | 1.00 | 0 | 60 |
| sprite:59 (west indoor south) | 13 | 0.64 | 1 | 48 |
| sprite:60 (south porch) | 7 | 0.88 | 1 | 46 |
| sprite:61 (west indoor hall) | 11 | 0.75 | 1 | 54 |

Outdoor routes stay under sky once they leave any local shed. Indoor routes
have a **single** cover→sky transition, then travel the open ring. Mean
maximum 2D sight along those routes is ~46–60 player-widths — on the order of
the board itself — while **median spawn-local sight is only ~6.5–8.7 widths**.
Players leave a short-sight pocket and, after a few grid cells, occupy a long
sight field. The hop counts are large because the grid is finely sliced, not
because the Euclidean travel is long.

This is not a combat simulation. It distinguishes “spawn, then immediately
occupy a broad sky field” from “spawn, then walk a covered strip before the
field.” The west indoor starts are the latter. Most outdoor starts are the
former in sky-fraction terms, but still have short median sight at the spawn
point itself.

---

## 2D visibility and spawn concealment

Pairwise 2D sight among the eight DM starts: **0 of 28 pairs clear**. Mutual
spawn concealment is complete under the 2D occluder model.

Spawn depth roses (32 rays) show short medians everywhere (about 6–8 widths).
Maximum occluder distance varies:

- NE outdoor: 80 widths (a ray can travel the full board);
- SE outdoor: 59 widths;
- north yard: 36 widths;
- south porch: 33 widths;
- NW and SW outdoor: 18 widths;
- west indoor starts: 16–19 widths.

So concealment is not “everyone stands in a closet.” Some outdoor starts can
see far in at least one direction; others cannot. No start can see another
start.

---

## Spawn neighborhoods

`spawn-neighborhood` (local reachable area within 16 player-widths, hops into
the largest sky component of 72 sectors / 4679 player-areas, and the fraction
of 32 rays that sample that component):

| start | sky ceiling | spawn sector area | local area (16w) | portals | hops to main sky | max sight | sky-ray fraction |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 54 north yard | yes | 56 | 280 | 2 | 0 | 36 | 1.00 |
| 55 NE | yes | 144 | 280 | 1 | 0 | 80 | 1.00 |
| 56 NW | yes | 112 | 331 | 2 | 2 | 18 | 0.16 |
| 57 SW | yes | 112 | 293 | 2 | 0 | 18 | 1.00 |
| 58 SE | yes | 144 | 176 | 2 | 0 | 59 | 1.00 |
| 59 west south | no | 162 | 653 | 2 | 5 | 16 | 0.31 |
| 60 south porch | no | **32** | 162 | 3 | 1 | 33 | 0.25 |
| 61 west hall | no | 93 | 649 | 3 | 3 | 19 | 0.28 |

Measurements, not labels:

- Five starts begin under sky; three under a solid ceiling.
- Spawn *sector* footprints are modest (32–162 player-areas). The smallest is
  the south porch (32). The largest outdoor cells are 144.
- Local 16-width reachable area is larger than the spawn cell for every start.
  West indoor starts reach ~650 areas because the west building is a connected
  indoor cluster. Several outdoor starts only gather 176–331 areas in that
  radius — they sit in small sky cells next to solid grid walls.
- Immediate movement choices are 1–3 portals. Nobody spawns at a many-way
  junction.
- Sky-ray fraction splits the set: four outdoor starts paint the main field
  with every ray; the NW pocket and all three indoor/porch starts do not.

The important experiential split this sensor is built to expose: **pairwise
spawn LOS is zero for everyone**, yet some starts already occupy (or look into)
the large sky component while others are one to five hops inside a covered
cluster whose spawn cell is a few dozen player-areas.

---

## Architectural morphology

Every measured wall is axis-aligned. Every outer loop is a rectangle.

| metric | value |
| --- | --- |
| orthogonal length fraction | 1.00 |
| diagonal length fraction | 0.00 |
| 5° orientation bins occupied | 2 (0° and 90°) |
| orientation diversity (bins/36) | 0.056 |
| rectangular sector fraction | 1.00 |
| convex sector fraction | 1.00 |
| outer vertices | 4 / 4 / 4 (min/median/max) |
| AABB fill | 1.00 |
| corner angles | 90° exclusively |
| chamfer fraction | 0.00 |
| segmented-arc chain count | 0 |
| wall length | 2.67–24 widths (median 4.67) |

The architecture is an **orthogonal rectangular grid**. There is no chamfer,
diagonal, irregular polygonal mass, or curved-chain candidate. Boundary
articulation is the grid’s cell-size variation (mostly 3–8 widths, a few 24-width
runs), not a change of orientation language.

---

## Materials / visual grammar

Ontology v2 (INTERPRETED, not native facts):

| role | dominant picnum | ontology |
| --- | ---: | --- |
| outdoor floor | 270 | horizontal floor, organic earth |
| outdoor wall | 110 | vertical structural fill, stone masonry |
| sky ceiling | 2500 | sky sheet (64×400 parallax) |
| indoor floor | 2448 | horizontal floor, organic earth |
| indoor wall | 5 | vertical brick fill |
| indoor ceiling | 416 | indoor ceiling fill, not a sky sheet |
| water / under | 90 | mixed-use; visual_material unknown |
| door faces | 104 | construction-door tile; rare in campaign |
| one masked overpic | 330 | masked separator (fence) |

Outdoor vs indoor is readable as **earth + stone + sky** versus **earth-floor +
brick + indoor ceiling**. Both floors are organic-earth family; the indoor/
outdoor split is carried by walls and ceilings, not by a different ground
material class. Tile 90 is used as water floor (and underwater ceiling) despite
mixed campaign usage and no liquid visual label — water is encoded by
underwater XSECTOR flags, depth, and up/down markers more than by a dedicated
liquid tile. Palette and shade do not further differentiate rooms: one shade
band, no pal shifts except floor pal 1 on the surface water cells.

---

## Mechanisms

Dynamic vocabulary is small and purpose-tied:

1. **Three Z-motion doors** (type 600), rest-closed (ceiling Z = floor Z = 0),
   opening ceiling to −6 player-heights. RX channels 100, 101, 102. Each is a
   gated item closet.
2. **Four one-way switches** (type 21 / tile 1070): two TX 100, one TX 101, one
   TX 102. Push-on. They are the only way the at-rest graph opens those doors.
3. **Paired water** (types 9/10, two pairs, data_1 1 and 2) into an underwater
   XSECTOR (depth 2) that contains the Tesla cannon. A second underwater cell
   (depth 3) sits inside it and is not on the at-rest walkable graph.
4. **One gib wall** (type 511, masked overpic 330, vector trigger).
5. **Match-start sting**: toggle sprite TX 119 → player SFX 711 (once).
6. **Three ambient SFX** (710) and a water drip generator (701).

There are no slide-marked sectors, rotators, locked keys, teleporters, or
elevators. World-state variation that changes circulation is the three doors.
Water changes locomotion/medium, not the 2D plan. The gib is a local
destructible, not a route.

---

## Resources and multiplayer incentives

Opposite-side flag anchors:

- Flag A (`kItemFlagABase`, RX 80) in the **north outdoor yard** (sky).
- Flag B (`kItemFlagBBase`, RX 81) on the **south covered porch** (solid
  ceiling). Same X, opposite Y extrema.

Gated high-value pickups behind the Z-doors:

- Super armor in the northwest indoor vault (channel 100, two switches).
- Two-guns (akimbo) in a west indoor closet (channel 101).
- Shadow cloak in a covered room off the south/east court (channel 102).

Risk/reward water: Tesla cannon is underwater in the east bay; Tesla ammo sits
on the east outdoor ring, not in the water. Ordinary weapons (sawedoff,
tommy, flare, napalm) and ammo are scattered on both the ring and the west
indoor. Napalm is in the central outdoor cell beside the pavilion. Armor
types are split indoor/porch/ring rather than stacked. Health is light (two
doctor bags, one life seed, three essences).

Nearest-resource probes (distance only, not balance): several starts spawn on
top of a weapon or ammo sprite. Flag B’s porch start is also the Flag B
sprite’s sector. Flag A is 3.7 widths from the north-yard start with clear 2D
sight. Tesla is ~34 widths from the NE and SE outdoor starts, without 2D sight
into the underwater cell.

---

## Landmarks and orientation

Cues a player can use without a minimap:

- **Square outer wall** and sky — you are inside a compound, not an open
  wilderness.
- **North flag vs south porch flag** — opposite Y anchors; enclosure differs
  (sky yard vs covered porch).
- **West brick interiors** vs **east water** vs **center pavilion**.
- **Height**: 20-height sky versus 6-height brick rooms.
- Material: stone outdoor walls vs brick indoor walls.

There is little unique mass to memorize: sheds, porch, pavilion, and west
block are all rectangles on the same grid. Orientation is by **cardinal
program** (flags, water, indoor strip) more than by distinctive silhouette.

---

## Spatial transitions

Measured indoor-start group → outdoor-start group:

- sky exposure 0 → 1
- clear height ×3.33
- navigable area ×1.98

Covered → sky along indoor start routes happens once, then the traveler is in
the tall ring. Tight → open is the spawn-median-sight (~7 widths) versus
route-mean-max-sight (~50 widths) gap. Ordinary route → water is an east-bay
floor-tile / underwater-link change, not a height terrace. Prize rooms are
zero-height at rest and become 6-height indoor cells when opened — a
mechanical gate, not a spatial funnel.

---

## Multiplayer design interpretation

This is a **Blood deathmatch / capture-the-flag compound**, not a campaign
map. Eight mutually blind starts, opposite flags, three switch-gated prizes,
and an underwater Tesla are the incentive structure. The outdoor ring is the
hunting ground in *route* statistics (long max sight, sky fraction near 1).
The *spawn cells themselves* are small grid rooms with short median sight and
one to three exits. West indoor starts add a covered approach. Concealment is
achieved by local walls and sheds, not by distance across a large shared
neighborhood.

Lighting, outdoor Z, and architectural orientation are almost unused as
expressive channels. The map’s design meaning is carried by **mode, enclosure
contrast, flags, gated prizes, water Tesla, and spawn-pair blindness**.

---

## Limitations of this reading

- 2D sight, not the renderer.
- Closed doors are treated as blocked; NBlood was not stepped here.
- “Hunting ground” is not a label in the sensors; the claim above is an
  interpretation of neighborhood area, hops, sky-ray fraction, and route sky
  fraction.
- Corpus percentiles were not attached; comparisons are player-relative.
- Tile 90’s water readability is an ontology gap, not a measured liquid
  appearance.
