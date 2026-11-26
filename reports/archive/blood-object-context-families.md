# Object-scale unsigned families: Phase 3

One new family in the existing pattern pipeline, not a new framework:
`object-context`, one sample per sector that holds objects, keyed by its
Phase 1 relation neighborhood. The three families already there measure a
sector's *shape* (`local-morphology`), its *route* (`route-exposure`) or its
*edges* (`vertical-transition`). This one measures what a sector is for at
object scale: what it holds, what holds those objects up, and how it sits
among its neighbours.

```text
python -m bloodmap pattern-mine --maps maps/blood --population blood-campaign \
  -o work/blood-pattern-unsigned-campaign.json
python -m bloodmap pattern-mine --maps maps/blood --population community \
  --tier S --limit 20 -o work/blood-pattern-unsigned-tierS.json
```

## Regenerated 2026-08-31 after the mining-hygiene fix

**The first run counted wiring as furniture.** Every sample now carries two
labels and nothing is dropped:

- `sector_kind` from `reachability.sector_kinds` -- `reachable`, or the
  off-map kind (`logic_closet`, `signature`, `helper`, `sealed`, `bare`);
- the visible/wiring split of what it holds, from
  `blood_types.sprite_visibility`. Sector-sound markers, link markers,
  player starts and generators are not objects a player can see.

A sample is in the **default scope** when it sits in reachable geometry and
holds at least one visible object. Everything else is `excluded` and is
clustered under its own heading -- a sound-marker pocket is evidence about
wiring, not garbage. Reachability is computed once per map.

### What changed against the polluted run

```text
                                   before          after
object-context candidates          1328            1076
object-context occurrences         6599            4637
share in candidates spanning        80%             78%
  three or more maps
excluded and reported              none            173 candidates, 1962 occurrences
```

**1962 of 6599 object-context occurrences (30%) left the default
statistics.** Split by reason:

```text
all objects are wiring or markers   1889
off-map geometry                      79   (50 logic_closet, 29 sealed)
```

The off-map share matches what was measured before the fix (81 of 6803,
1.2%); the wiring share is far larger and was invisible until the sprite
catalog was consulted. The cross-map stability figure barely moved (80% ->
78%), which says the recurring structure was never the wiring -- but the
*membership* of several families changed a great deal, and one dissolved
almost entirely (see below).

## The bands are measured, not chosen

Quartiles of the 2837 sprite-carrying sectors in the first 15 campaign maps:
area p25/p50/p75 = 3.7/14.2/56.7 player areas, clear height 1.57/1.93/3.50
player heights. The first version guessed round numbers (1.0/2.0/4.0 on
height) and put nearly every campaign sector in one bucket, which would have
made the facet decorative.

## Candidate stability and cross-map coverage

| population | `object-context` candidates | occurrences | in >=3 maps | share of occurrences |
| --- | ---: | ---: | ---: | ---: |
| `blood-campaign` | 1076 | 4637 | 351 | 78% |
| `blood-bloodbath` | 182 | 396 | 19 | 36% |
| `community tier S` | 781 | 2402 | 178 | 59% |

**78% of campaign object-context occurrences fall in a candidate that recurs
across three or more maps.** For comparison, in the same run `route-exposure`
puts half its occurrences in candidates spanning three or more maps, and none
in BloodBath. The new family is more stable than one already in the pipeline.

### The vocabulary transfers between populations

```text
campaign signatures                      1076
also seen in BloodBath                   152 = 89% of BloodBath occurrences
also seen in community tier S (20 maps)  481 = 81% of tier-S occurrences
```

Populations stay separate as evidence -- this is a *coverage* statement, not
a claim that community maps follow campaign convention.

## Clusters nobody programmed

- **188 occurrences across 40 maps** (BloodBath x17; tier S x61)
  `portals:3+|enclosed:no|stacked:none|coplanar:yes|objects:3+|seated:some|wallbound:some|run:no|size:hall|clear:lofty`
- **78 occurrences across 31 maps** (tier S x51)
  `portals:3+|enclosed:no|stacked:none|coplanar:yes|objects:3+|seated:some|wallbound:some|run:no|size:hall|clear:open`
- **88 occurrences across 30 maps** (BloodBath x13; tier S x34)
  `portals:3+|enclosed:no|stacked:none|coplanar:yes|objects:3+|seated:some|wallbound:some|run:no|size:hall|clear:standing`
- **58 occurrences across 28 maps** (BloodBath x5; tier S x18)
  `portals:3+|enclosed:no|stacked:none|coplanar:yes|objects:3+|seated:some|wallbound:some|run:no|size:room|clear:standing`
- **46 occurrences across 25 maps** (BloodBath x10; tier S x8)
  `portals:3+|enclosed:no|stacked:none|coplanar:yes|objects:3+|seated:some|wallbound:none|run:no|size:hall|clear:lofty`

### The contrast pair, after the fix

The pair this report originally led with -- a tiny two-portal niche holding
one wall-bound object, `seated:none` against `seated:all` -- **was mostly
sound-marker placement**:

```text
                     before                after (visible objects only)
seated:none            77 occ / 28 maps         13 occ / 10 maps
seated:all             72 occ / 24 maps         10 occ /  7 maps
```

Phase 4 followed this up as a contrast and found the same thing from the
other direction: picnum 2520, which was 83% of *both* classes, is
`kSoundSector`'s editor icon. See the re-run section of
`reports/blood-contrast-niche-pair.md`. The structural niche shape is still
there; the two-variant reading was carried by where the editor drops a
marker.

## Excluded: the wiring, under its own heading

173 candidates, 1962 occurrences. The largest are sectors whose only
contents are markers -- reachable geometry, so not off-map, but not
furnished either:

| occurrences | maps | sector kinds | signature |
| ---: | ---: | --- | --- |
| 165 | 34 | reachable 165 | `portals:2|enclosed:no|stacked:none|coplanar:yes|objects:0|se...` |
| 144 | 31 | reachable 144 | `portals:2|enclosed:no|stacked:none|coplanar:yes|objects:0|se...` |
| 116 | 32 | reachable 116 | `portals:3+|enclosed:no|stacked:none|coplanar:yes|objects:0|s...` |
| 109 | 26 | reachable 109 | `portals:2|enclosed:no|stacked:none|coplanar:yes|objects:0|se...` |
| 64 | 21 | reachable 64 | `portals:3+|enclosed:no|stacked:none|coplanar:yes|objects:0|s...` |
| 63 | 25 | reachable 63 | `portals:3+|enclosed:no|stacked:none|coplanar:yes|objects:0|s...` |

These are where the ambient-sound wiring of a level lives, and they are kept
for the conditional-topology phases rather than deleted.

## Limitations

- Only sectors holding at least one sprite are sampled. An empty sector has
  no object-scale content.
- The tier-S run is **20 maps of 294**, taken in enumeration order so a rerun
  mines the same ones. It is a bounded sample and says so.
- `E6M7.MAP` produces no samples in any family: its sector 144 has invalid
  wall ownership and `analyze_spatial` validates the whole map before any
  selection. Reported in `observe_errors`, not silently dropped.
- Visibility is a Blood judgement, from sprite type category plus Build's
  invisible cstat bit. Neither signal alone is enough: `start` sprites never
  carry the bit and are still invisible, and 730 campaign `thing` sprites
  carry it while their category is visible.
- Every candidate is `unsigned`. The signature describes a sector's role
  among its neighbours, not its shape.
- Community and tier-S occurrences are precedent, never campaign convention.

