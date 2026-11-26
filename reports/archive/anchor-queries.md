# Anchor queries: Phase 2

`tools/mine_e6m1_shop.py` and `tools/mine_sewer_kit.py` did the same four
things by hand -- resolve a role to tiles, find every occurrence, collect the
carrying sectors, widen by one portal hop -- and then stopped at "here is the
tile and its neighbours". `bloodmap/anchors.py` is the general form of both,
and it goes one step further: it reduces each carrying sector's Phase 1
relation neighborhood to a discrete **context signature**, clusters the
occurrences by it, and asks the two questions a tile lookup cannot.

```text
python -m bloodmap anchor-mine --name mannequin --tile 2377 \
  --maps maps/blood --view reference -o work/anchor-mannequin.json
python -m bloodmap anchor-mine --kit projects/blood-city/references/sewer-kit.json \
  --maps maps/blood --view reference -o reports/anchor-sewer-kit.json
```

An anchor is a tile list, a named `surfaces.Material`, or example regions of
a map (`--regions-map` + `--region`). `--kit` reads a `role_assets` table --
which both reference reports already contain, so each is reproduced through
the general path by pointing the tool at its own role table rather than
re-typing it.

## Reproduction of the two reference reports

Occurrence counting is identical. `tests/test_anchors.py` pins it two ways:
against the hand-written functions themselves on a synthetic map, and against
the committed reference JSONs.

- **e6m1-shop**: all 11 roles' `asset_counts` reproduce exactly
  (sprites/walls/surfaces).
- **sewer-kit**: all 5 roles' densest maps reproduce exactly -- same map, same
  `uses`, same `affected_sectors` list.

`maps_with_use` differs by one for `machinery` and `pipe_walls` (49 vs 50).
The extra map in the old path is `maps/blood/campaign/ASAVE1.map`, an XMapEdit
autosave that landed in the campaign directory. The hand-written miner globs
that directory raw and counts the autosave as a campaign map; the Phase 0a
registry quarantines it. **The new number is the correct one** -- and this is
the first measured statistic the quarantine has changed.

## Enrichment: the number that stops the tool believing itself

A dominant context that half the map shares says nothing about the anchor. So
for each anchor the report measures how much more often the anchor's sectors
carry the dominant context than sectors with none of the anchor tiles, in the
same maps. 1.0 means the signature is describing the map, not the anchor.

| anchor | kit | uses | maps | enrichment | counterex. | analogues |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `mannequin` | e6m1-shop | 14 | 2 | **30.42** | 7 | 8 |
| `chair` | e6m1-shop | 261 | 36 | **11.58** | 7 | 103 |
| `outlet` | e6m1-shop | 34 | 9 | **9.38** | 7 | 85 |
| `hanging_clothes` | e6m1-shop | 118 | 10 | **6.97** | 9 | 138 |
| `wall_clock` | e6m1-shop | 28 | 15 | **6.11** | 6 | 169 |
| `sewer_grate` | sewer-kit | 308 | 18 | **5.77** | 10 | 80 |
| `cash_register_surface` | e6m1-shop | 271 | 33 | **4.15** | 21 | 260 |
| `machinery` | sewer-kit | 585 | 47 | **3.14** | 39 | 287 |
| `crate_surface` | e6m1-shop | 4036 | 52 | **2.77** | 153 | 73 |
| `shelf_wall` | e6m1-shop | 656 | 15 | **2.56** | 32 | 446 |
| `sewer_light` | sewer-kit | 341 | 46 | **2.22** | 49 | 248 |
| `wood_casework` | e6m1-shop | 4041 | 66 | **1.4** | 169 | 765 |
| `pipe_walls` | sewer-kit | 1899 | 46 | **1.15** | 193 | 550 |
| `drawer_surface` | e6m1-shop | 311 | 41 | **0.83** | 31 | 820 |
| `shaft_metal` | e6m1-shop | 1263 | 26 | **0.75** | 62 | 370 |
| `sewer_door` | sewer-kit | 433 | 31 | **0.53** | 66 | 725 |

The split is clean, and it is a fact about what anchors *are*:

- **Object anchors** -- mannequin (30.4x), chair (11.6x), outlet (9.4x),
  hanging clothes (7.0x), wall clock (6.1x), sewer grate (5.8x), cash register
  (4.2x) -- sit in strongly enriched contexts. The tile marks a *place with a
  particular structure around it*.
- **Bulk surface anchors** -- pipe walls (1.15x), wood casework (1.4x), shaft
  metal (0.75x), drawer surface (0.83x), sewer door (0.53x) -- are not
  enriched. Those tiles are spread across a map as generic material, and their
  "dominant context" is just the commonest context in the maps that use them.

An enrichment at or below 1.0 is the tool reporting that its own dominant
cluster is meaningless for that anchor. Context signatures answer questions
about objects; for material vocabulary the right query is `materials-mine`,
which already exists.

## What one anchor produces beyond a tile lookup

`mannequin` (picnum 2377), the sharpest case:

```text
uses            14 across 2 map(s)
dominant        portals:1|enclosed:no|stacked:none|coplanar:yes|objects:3+|seated:some|wallbound:some|run:no
anchored        2/9 = 0.2222
unanchored      8/1095 = 0.0073
enrichment      30.42x
counterexamples 7
analogues       8 sectors with that context and no mannequin tile
```

Read it back: a mannequin sits in a sector with one portal, sharing a floor
plane with a neighbour, holding three or more objects, some resting on a
surface and some against a wall. That context is 30 times more common where
mannequins are than where they are not. The analogues are candidate display
areas built from different art -- **candidates**, not a claim that they are
displays. Naming happens by review, never here.

Phase 1's `repeats_along` already recovered the three-mannequin row from the
same map without being told what 2377 is. Together that is the `03_...md`
target: the system learned a larger structure than the label it was given.

## What was skipped, and why

`spatial.analyze_spatial` validates wall ownership across the **whole map**
before analysing any selection, so one malformed sector costs every local
query on that map. Two of the sewer kit's densest maps are affected:

```text
TEDE1M4.MAP       7 uses  SpatialAnalysisError: sector:332 has invalid wall ownership
SSHIVE.MAP        3 uses  SpatialAnalysisError: sector:250 has invalid wall ownership
TEDE1M5.MAP       3 uses  SpatialAnalysisError: sector:0 has invalid wall ownership
```

They are named in `skipped_maps` with the reason and do **not** consume a
study slot -- the tool moves to the next densest analysable map instead. The
first version of this tool swallowed that exception and reported
`signatures_computed: 0` with no explanation, which is how it lost
TEDE1M4 (149 uses) silently.

## Limitations

- An analogue shares the anchor's dominant context signature and carries none of its tiles. That makes it a candidate, not the same thing: this module never decides an analogue IS the anchored object.
- Signatures describe a sector's role among its neighbours -- portals, enclosure, stacking, coplanarity, and what its objects do. They do not describe shape, so two differently shaped rooms can key alike.
- Occurrence counts span the whole population; signatures, clusters and analogues cover only the densest maps named in `studied`. Maps that could not be analysed are named in `skipped_maps` with the reason, and did not consume a study slot.
- Every row is an OBSERVATION. Role names come from the anchor spec and are the owner's, never inferred here.
- Enrichment compares against sectors in the *same studied maps*. A map-wide
  idiom will still look enriched if it is absent from other maps.
- Signatures describe a sector's role among its neighbours, not its shape.
  Two differently shaped rooms can key alike.
- Occurrence counts span the whole population; signatures, clusters and
  analogues cover only the densest analysable maps named in `studied`.

