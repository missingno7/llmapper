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

## Pilot

the 3 sprite-densest sectors of the first 5 maps, expanded 1 portal hop(s), population `blood-campaign`,
2432 relations over 5 maps.

| map | seed sectors | sectors | sprites |
| --- | --- | ---: | ---: |
| `E1M1.MAP` | [65, 122, 59] | 26 | 204 |
| `E1M2.MAP` | [19, 244, 14] | 18 | 101 |
| `E1M3.MAP` | [284, 291, 289] | 44 | 255 |
| `E1M4.MAP` | [321, 320, 382] | 38 | 229 |
| `E1M5.MAP` | [231, 216, 267] | 32 | 119 |

```text
above               17
adjacent_to        307
against_wall       464
faces_wall         297
in_sector          908
inside              18
repeats_along        1
rests_on           310
shares_material     46
shares_plane        64
```

## What the numbers say

### Blood snaps objects to the floor plane

Of 310 `rests_on` relations, **268 sit at clearance 0.0000 player heights** --
within one Build unit of the plane, i.e. exactly on it. Only 42 are merely
*near* a surface. Objects are placed on the plane, not eyeballed at it.

```text
band       5
exact      268
step       12
sub_step   25
```

### And it turns them square to the wall

**261 of 297 (87.9%)** `faces_wall` relations are at
*exactly* 0 from the wall's inward normal. A sprite that faces a wall in Blood
faces it square; approximate angles are the rare case.

### `against_wall` distance is bimodal, and the second mode is one map's habit

```text
flush      212
near       16
offset     109
loose      127
```

Objects are pressed against a wall or clearly off it; the 0.3-0.5 band is
nearly empty. But the 0.35-player-width spike inside `offset` is **not** a
campaign norm: 61 of its 96 occurrences are in E1M3 alone, and 44 of them are
one picnum (2521). That is one map's repeated furnishing, and it is exactly
the sort of thing a five-map pilot will mistake for a convention. Recorded as
a counterexample, not a rule.

### Evenly spaced identical objects are rare

Across the sampled neighborhoods, `repeats_along` fired **1 time(s)**:

```text
E1M5.MAP picnum 552 x3 spacing 6.5 player widths, variation 0.0
```

The drawer/shelf premise in `03_...md` assumes repeated identical parts are
common. At these thresholds (>=3 members, spacing variation <= 0.12) they are
not, in the campaign. That is a negative result about Blood, not about the
detector: the detector does find them where they exist --

### It recovers the E6M1 shop display row without being told

Seeded on the shop sectors `tools/mine_e6m1_shop.py` identifies by hand
(32, 34, 45, 50, 61, 63, 79), one hop out, the extractor produces 460
relations, among them:

```text
repeats_along  sprite:474 sprite:475 sprite:476
               picnum 2377, count 3, spacing 2.6667 player widths,
               spacing_variation 0.0
```

picnum 2377 is `mannequin` in that script's owner-identified asset table. The
extractor is told no such thing. It finds three identical sprites, collinear,
evenly spaced -- a display row -- and says so without a name. It also finds
`sector:33` and `sector:34` **inside** `sector:32`, the counter's sub-volumes,
at 0.1 area fraction each. This is the `03_...md` target restated: a larger
structure than the label that seeded it.

## Limitations

- A pilot over sampled neighborhoods, not a corpus statistic. It says what the extractor produces, not what Blood usually does.
- Seeds are the sprite-densest sectors, so the sample is biased toward furnished rooms -- deliberately, since that is where object-scale relations exist at all.
- Every relation is an OBSERVATION. Nothing here is interpreted.
- Frame independence is claimed for translation and quarter-turn rotation --
  the exact-integer transform Build geometry admits. Mirroring reverses wall
  winding and is not claimed.
- `plan_bbox_overlap_fraction` is a bounding-box overlap, not a polygon
  intersection. `inside` does test true containment (bounds *and* an exact
  rational centroid inside the outer loop), which a bbox test would get wrong
  for an L-shaped room; `tests/test_relations.py` pins that with a notched
  fixture.
- `repeats_along` covers sprites only. A run of repeating *sectors* is a stair
  or a landing and `structures.py` already recovers those with a richer
  parameter set; duplicating it would give one fact two names.
- `rests_on` does not read tile heights, so it states proximity to a plane,
  not contact.
- Nothing here is interpreted. Every relation is an OBSERVATION.

