# Object-scale relations: Phase 1 pilot

What is next to what, said without naming it. At *space* scale
`decompiler.py` already emits relations between perceptual spaces
(`connects`, `part_of`, `overlaps`, `embedded_in`). At *object* scale --
the sprite, the wall segment, the two-player-widths sector -- nothing did.
`bloodmap/relations.py` fills that gap and stops.

```text
python -m bloodmap relation-dump maps/blood/campaign/E6M1.MAP \
  --sector 32 --sector 34 --sector 45 --hops 1 -o work/e6m1-shop-relations.json
python -m bloodmap relation-mine --maps maps/blood --population blood-campaign \
  --map-limit 5 --seeds 3 -o reports/blood-object-relations-pilot.json
```

## Regenerated 2026-08-31 after the mining-hygiene fix

**The first run of this pilot counted wiring as furniture.** Two defects,
both owner-flagged and both fixed by labelling rather than dropping:

- **Off-map seeds.** `sprite_dense_seeds` ignored `reachability.py`, and a
  logic closet is routinely a map's sprite-densest sector. Three of the
  original fifteen seeds were off-map -- E1M2 sector 19, the map's densest,
  is its switch closet; also E1M3 291 and E1M5 231.
- **Invisible sprites.** Roughly a quarter of every campaign map's sprites
  are sector-sound markers, link markers, starts and generators, which the
  engine never draws. They were being counted as objects.

Seeds are now reachable sectors ranked by *visible* objects, and every
statistic below covers visible objects only. Nothing was deleted: what the
filters held back has its own heading, because a switch closet is evidence
about how a level is wired.

### What changed against the polluted run

```text
                                    before        after (visible only)
seeds                        3 of 15 off-map      0 of 15 off-map
rests_on exactly on plane    268/310  86.5%       106/167  63.5%
faces_wall exactly square    261/297  87.9%       170/192  88.5%
repeats_along runs found     1                    3 visible, 0 wiring
```

The floor-snapping headline was the casualty: **the 86.5% figure was
inflated by sound markers**, which sit exactly on the floor plane 41 times
out of 42. Among objects a player can see the norm is 63.5% -- still the
commonest single behaviour, no longer overwhelming. The square-facing
finding is untouched, which is what you would expect of a fact about
things that are drawn.

## The claim, and how it is falsified

Every measure is a count, a ratio, a distance normalized to player widths or
heights, or an angle **relative to a referenced wall's inward normal**. No
world coordinate and no world bearing reaches a relation. So the same
neighborhood of a translated or quarter-turn-rotated map must produce a
byte-identical document.

That is checked, not asserted. `tests/test_relations.py` re-extracts from
transformed copies of a synthetic map and of three campaign maps and requires
equality. **The first run of that check failed**: `repeats_along` sorted its
members by position, so a half turn read the row backwards. The fix orients a
run by whichever end gives the smaller id sequence, which is a property of the
run rather than of north.

## Relation kinds

Ten, each with the consumer that justifies it (`10_...md`: do not add
relations no consumer needs yet).

| kind | why it exists |
| --- | --- |
| `above` | 03 above/below; overlooks, lofts, stacked volumes |
| `adjacent_to` | 03 open_to/accessible_from at object scale |
| `against_wall` | 03 discriminator against_wall; shelf vs crate pile |
| `faces_wall` | 03 discriminator privileged_front / open_front |
| `in_sector` | anchor: which space carries the object (03: contains) |
| `inside` | 03 inside/contains; a volume cut into another |
| `repeats_along` | 03 repeats_along + stackable_identical_units |
| `rests_on` | 03 supports/supported_by; what holds the object up |
| `shares_material` | 03 shares_style_with, the cheapest style relation |
| `shares_plane` | 03 coplanar_with/shares_height_with; a run of surfaces |

Every `in_sector` relation additionally carries `visibility`
(`visible` / `wiring`), and every sector in the document carries its
reachability kind. Both are labels; neither filters the dump.

## Pilot

the 3 sprite-densest sectors of the first 5 maps, expanded 1 portal hop(s), population `blood-campaign`, scope *visible objects in reachable sectors*:
2049 relations over 5 maps.

| map | seed sectors | sector kinds | visible | wiring |
| --- | --- | --- | ---: | ---: |
| `E1M1.MAP` | [65, 59, 82] | reachable | 107 | 70 |
| `E1M2.MAP` | [14, 244, 270] | reachable | 61 | 20 |
| `E1M3.MAP` | [115, 121, 66] | reachable | 114 | 48 |
| `E1M4.MAP` | [320, 382, 156] | reachable | 173 | 35 |
| `E1M5.MAP` | [394, 216, 267] | reachable | 75 | 42 |

```text
above               13
adjacent_to        289
against_wall       406
faces_wall         263
in_sector          745
inside              19
repeats_along        3
rests_on           209
shares_material     47
shares_plane        55
```

## What the numbers say

### Blood snaps visible objects to the floor plane, but not as often as it looked

Of 167 `rests_on` relations on visible objects, **106 sit at
clearance 0.0000 player heights** -- within one Build unit of the plane.

```text
exact      106
sub_step   37
step       18
band       6
```

The same measurement over the wiring that used to be mixed in:

```text
exact      41
step       1
```

41 of 42 sound markers sit exactly on the floor
plane. That is a fact about how the editor drops a marker, not about how a
designer places furniture, and it is why the two are now counted apart.

### And it turns them square to the wall

**170 of 192 (88.5%)** `faces_wall` relations on visible
objects are at *exactly* 0 from the wall's inward normal. A sprite that faces
a wall in Blood faces it square; approximate angles are the rare case. This
figure barely moved when the wiring was separated out (87.9% -> 88.5%).

### `against_wall` distance is bimodal

```text
flush      149
near       6
offset     30
loose      94
```

Visible objects are pressed against a wall or clearly off it; the `near` band
is nearly empty. The earlier report noted a 0.35-player-width spike inside
`offset` that turned out to be one map's repeated furnishing -- recorded as a
counterexample then, and a reminder that a five-map pilot will mistake a
mapper's habit for a convention.

### Evenly spaced identical objects are rare

`repeats_along` fired **3 times** on visible objects:

```text
E1M3.MAP picnum 574 x11 spacing 0.3333 player widths, variation 0.0
E1M4.MAP picnum 470 x3 spacing 2.7474 player widths, variation 0.0246
E1M5.MAP picnum 552 x3 spacing 6.5 player widths, variation 0.0
```

and 0 times on wiring.

The drawer/shelf premise in `03_...md` assumes repeated identical parts are
common. At these thresholds (>=3 members, spacing variation <= 0.12) they are
not, in the campaign. That is a negative result about Blood, not about the
detector: the detector does find them where they exist --

### It recovers the E6M1 shop display row without being told

Seeded on the shop sectors `tools/mine_e6m1_shop.py` identifies by hand
(32, 34, 45, 50, 61, 63, 79), one hop out, the extractor produces
`repeats_along sprite:474 sprite:475 sprite:476, picnum 2377, count 3,`
`spacing 2.6667 player widths, spacing_variation 0.0`.

picnum 2377 is `mannequin` in that script's owner-identified asset table, and
sprite type 0 -- a visible decoration, so this finding is untouched by the
hygiene fix. The extractor is told no such thing. It finds three identical
sprites, collinear, evenly spaced, and says so without a name.

## Excluded: what the filters held back

Not garbage. Wiring evidence for the conditional-topology phases.

| map | sector | sprites | visible | kind | why |
| --- | ---: | ---: | ---: | --- | --- |
| `E1M1.MAP` | 122 | 33 | 15 | `reachable` | 18 of 33 sprites are wiring |
| `E1M2.MAP` | 19 | 42 | 25 | `logic_closet` | off-map: logic_closet; 17 of 42 sprites are wiring |
| `E1M3.MAP` | 284 | 59 | 19 | `reachable` | 40 of 59 sprites are wiring |
| `E1M3.MAP` | 291 | 54 | 43 | `logic_closet` | off-map: logic_closet; 11 of 54 sprites are wiring |
| `E1M3.MAP` | 289 | 51 | 15 | `reachable` | 36 of 51 sprites are wiring |
| `E1M4.MAP` | 321 | 72 | 16 | `reachable` | 56 of 72 sprites are wiring |
| `E1M5.MAP` | 231 | 43 | 31 | `logic_closet` | off-map: logic_closet; 12 of 43 sprites are wiring |

Three of these are the off-map switch closets the original pilot seeded on.
The other four are reachable but wiring-dominated: E1M4 sector 321 holds 72
sprites of which 56 are wiring, and E1M3 sector 284 holds 59 of which 40 are.
A furniture survey that ranks by raw sprite count finds these first.

## Limitations

- A pilot over sampled neighborhoods, not a corpus statistic. It says what the extractor produces, not what Blood usually does.
- Seeds are the sprite-densest sectors, so the sample is biased toward furnished rooms -- deliberately, since that is where object-scale relations exist at all.
- Every relation is an OBSERVATION. Nothing here is interpreted.
- Seeds are reachable sectors ranked by *visible* objects; what the two filters held back is under `excluded`, with the reason. Reachability is computed once per map.
- Frame independence is claimed for translation and quarter-turn rotation --
  the exact-integer transform Build geometry admits. Mirroring reverses wall
  winding and is not claimed.
- `plan_bbox_overlap_fraction` is a bounding-box overlap, not a polygon
  intersection.
- `repeats_along` covers sprites only. A run of repeating *sectors* is a stair
  or a landing and `structures.py` already recovers those.
- `rests_on` does not read tile heights, so it states proximity to a plane,
  not contact.
- Visibility is a Blood judgement: BuildIR keeps Blood's sprite type in the
  shared `lotag` slot, which means something else on Duke, so the label is
  `unknown` off Blood.
- Nothing here is interpreted. Every relation is an OBSERVATION.

