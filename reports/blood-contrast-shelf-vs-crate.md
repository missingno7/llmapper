# Contrast pilot 1: shelf against crate pile

`03_...md` lists shelf vs crate pile as a confusing pair and names candidate
discriminators for it: `privileged_front`, `open_front`,
`repeated_horizontal_support_surfaces`, `against_wall`,
`requires_access_clearance`, `stackable_identical_units`,
`solid_closed_volume`. All seven are measured here, relationally, from Phase 1
relations. **None of them survives.**

```text
python -m bloodmap anchor-contrast --positive-tile 2026 --positive-tile 2635 \
  --comparison-tile 95 --comparison-tile 452 --comparison-tile 462 \
  --comparison-tile 456 --view reference -o reports/blood-contrast-shelf-vs-crate.json
```

Anchor tiles are the owner's (`knowledge/blood/design/owner-anchors-v1.json`):
shelf 2026/2635, crate 95/452 with broken pair 462 and similar 456. Every
feature measured is relational and reads no picnum.

## The sets

```text
shelf-carrying sectors           16  in 3 maps
crate-carrying sectors         1047  in 59 maps
carrying both (held out)         10
```

The imbalance is the first result. Shelf tiles occur 45 times in the whole
reference view; two more shelf sectors are lost because TEDE1M5 fails
whole-map wall-ownership validation. Sixteen positives from three maps --
two of which are shops -- cannot support a generalization, and the report
says so rather than reporting a percentage of sixteen.

## Measured separation

Balanced accuracy, because a 16-vs-1047 split rewards a rule that never
fires. Threshold fitted on the same rows it is scored on, so these are
separations observed, not a validated classifier.

| balanced acc. | feature | positive | comparison |
| ---: | --- | --- | --- |
| 0.729 | `portals` | median 2.0 | median 4.0 |
| 0.721 | `solid_wall_share` | median 0.5625 | median 0.25 |
| 0.717 | `min_opening_player_heights` | median 1.9321 | median 1.5094 |
| 0.716 | `objects_resting` | median 2.0 | median 0.0 |
| 0.706 | `objects_held` | median 2.5 | median 1.0 |
| 0.690 | `max_step_player_heights` | median 0.2717 | median 0.966 |
| 0.675 | `shares_a_plane` | 62% | 98% |

### Rejected

| balanced acc. | feature | positive | comparison |
| ---: | --- | --- | --- |
| 0.629 | `rise_over_neighbours_player_heights` | median 0.2264 | median 0.3623 |
| 0.626 | `objects_against_wall` | median 1.5 | median 0.0 |
| 0.613 | `area_player_areas` | median 10.2222 | median 7.1111 |
| 0.612 | `clear_height_player_heights` | median 1.9623 | median 1.9925 |
| 0.603 | `raised_above_all_neighbours` | 50% | 29% |
| 0.556 | `inside_another_sector` | 6% | 17% |
| 0.534 | `twin_neighbours` | median 0.0 | median 0.0 |
| 0.524 | `enterable` | 50% | 55% |
| 0.524 | `solid_closed_volume` | 50% | 45% |
| 0.520 | `in_a_repeating_run` | 6% | 2% |
| 0.510 | `stands_under_a_neighbour` | 0% | 2% |
| 0.507 | `stands_above_a_neighbour` | 0% | 1% |

**Every discriminator `03_...md` predicted for this pair is in the rejected
table.** `stackable_identical_units` (as `twin_neighbours`) scores 0.53,
`solid_closed_volume` 0.52, `requires_access_clearance` (as `enterable`)
0.52, `repeated_horizontal_support_surfaces` (as `shares_a_plane`) separates
in the *wrong direction* -- 98% of crate sectors share a plane with a
neighbour against 62% of shelf sectors.

### The hypothesis was re-encoded before it was rejected

The first feature set mapped `stackable_identical_units` onto the `above`
relation, and that was wrong: `above` means one volume stacked over another,
while a crate inside a room stands above that room's **floor**, not above its
ceiling. `above` could never have fired for a crate. Two features were added
to carry the platform reading properly -- `raised_above_all_neighbours` and
`rise_over_neighbours_player_heights` -- and the contrast re-run.

The answer did not change:

```text
raised_above_all_neighbours              0.60   rejected
rise_over_neighbours_player_heights      0.63   rejected

crate sectors standing proud of every neighbour : 307/1047 (29%)
shelf sectors standing proud of every neighbour :    8/16  (50%)
```

Fewer than a third of the sectors wearing crate tiles are raised platforms,
and a *higher* share of shelf sectors are. A rejection that survives having
its hypothesis re-encoded correctly is worth more than the first one.

## Why: the best rule is a map artifact

The strongest feature is `portals < 1.5` at 0.729. The built-in transfer
check disposes of it:

```text
E6M1.MAP         0% of 7 positives match
SSMALL.MAP       89% of 9 positives match
spread 0.89

fitted without E6M1.MAP         holds on 89% of the rest, 0% of the held-out map
fitted without SSMALL.MAP       holds on 0% of the rest, 89% of the held-out map
```

The rule separates SSMALL's shelf sectors from E6M1's. It transfers to
neither. Printing all sixteen positives shows why:

```text
E6M1    7 sectors   portals 3-15   area 3.6-268 player areas   solid walls 0.17-0.38
SSMALL  9 sectors   portals 1 (x7) area 2.7-14.2               solid walls 0.75-0.83
```

In SSMALL the shelf tile is on small, one-portal, mostly-solid recesses --
shelves. In E6M1 the same tile is on the walls of the shop's retail floor,
which is a room. **One tile, two structures.** The anchor does not delimit a
relational class, which is exactly what an anchor is warned to be in
`03_...md`: a seed for a query, not a concept.

## And the comparison set is worse

The crate side is not crates. Measured over its 1047 sectors:

```text
plan size   tiny (<4)   30.3%      small (4-14)  32.4%
            room (14-57) 21.1%     hall  (>57)   16.2%
56 maps, median 13 crate-carrying sectors per map
```

A sixth of the sectors wearing crate tiles are halls. The tiles are bulk
industrial wall material, used at every scale, and Phase 2 already measured
this from the other direction: `crate_surface` scored an enrichment of 2.77
and `shaft_metal` 0.75, the signature of a material rather than an object.

## Companion contrast: bookcase fronts against crate

The owner's anchor list also carries bookcase fronts (31, 32, 33), which are
shelf-like and far commoner. Running the same contrast gives a real n and a
real map spread, and still does not separate the classes:

```text
bookcase_front    157 sectors in 31 maps
crate            1050 sectors in 59 maps
ambiguous           7
```

| balanced acc. | feature | positive | comparison |
| ---: | --- | --- | --- |
| 0.663 | `enterable` | 87% | 55% |
| 0.663 | `solid_closed_volume` | 13% | 45% |
| 0.653 | `portals` | median 8.0 | median 4.0 |
| 0.651 | `rise_over_neighbours_player_heights` | median 0.0 | median 0.3623 |

Best rule `enterable is True`: it misses 20 of 157 positives and wrongly matches 574 of 1050 comparisons. Per-map spread 0.50 over 28 maps -- it transfers better than the shelf rule and still
classifies more than half the crate side as bookcase.

## Verdict

Rejected as a contrast. Not because the relations are too coarse, but
because neither anchor set delimits a class:

- `2026`/`2635` sit on shelves in one map and on room walls in another;
- `95`/`452`/`456`/`462` are bulk wall material spanning every plan size.

This is a negative result about the *anchors*, not about the method. The
experiment that would settle it is owner-labelled crate and shelf
**instances** -- 20 of each, pointed at by sector -- instead of tiles;
`anchors.anchor_from_regions` already accepts that input.

## Independent confirmation (2026-08-31)

While this pilot was being written the owner added a **binding strength** field
to `owner-anchors-v1.json` and to `03_...md`: how reliably a tile carries its
meaning depends on how visually distinctive it is, and Phase 2's enrichment is
its empirical estimator. Three anchors are tagged so far, and they line up with
what this contrast measured from the other direction:

```text
2377  mannequin                                    binding=strong   enrichment 30.4x
 456  "crate look, but often a plain wall/ceiling  binding=weak     crate_surface 2.77x
       texture ... treat as material, not object
       identity"
 202  "worn wall/facade texture, bricks showing    binding=weak
       through"  -- one of mine_e6m1_shop's three
       shelf_wall tiles
```

Tile 456 is in this pilot's comparison set, and the owner's reading of it is
the same conclusion this report reached by measurement: it is material, not an
object. Tile 202 is one of the three tiles the shop miner calls `shelf_wall`,
and it is a wall texture -- which is exactly why the shelf tiles land on E6M1's
retail-floor walls as well as on SSMALL's recesses.

Two independent routes to the same finding: the owner reading the art, and the
contrast measuring the relations. Neither was told the other's answer. This is
the falsification the report asked for and did not get to run itself.

## Preserved counterexamples and ambiguity

```text
sectors carrying both anchors, held out : 10
positives the best rule misses          : 8
comparisons it wrongly matches          : 45
maps skipped (wall-ownership failure)   : 3
```

Full rows for both classes, including every ambiguous sector, are in
`reports/blood-contrast-shelf-vs-crate.json` and
`reports/blood-contrast-bookcase-vs-crate.json`.

