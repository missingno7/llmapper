# Which population is this evidence? A label, priced

Five miners describe themselves as measuring *the campaign*. All five were
reading campaign **plus the curated community sets**, because they globbed a
flat `maps/blood` directory that happened to hold both, and nothing in their
output said so.

`10_AGENT_EXECUTION_PROTOCOL.md` is explicit: community maps are cited as
*precedent*, never as campaign convention. So either the label is wrong or
the evidence is, and one of them has to change. This prices both.

```text
tools/mine_{run_rhythm,set_pieces,monuments,prop_catalogue,style_combinations}.py
tests/test_mining_population.py
reports/blood-mining-population.json
```

## How the population was identified

The flat directory is gone, so what it held is not directly recoverable --
but the numbers it produced are. `run-rhythm-v1.json`, mined 2026-08-28,
records 702 runs and a median gap of 0.5 plan units. Running the miner's own
`main()` against each candidate population:

```text
  view reference     102 maps   blood-campaign, blood-bloodbath, community-curated
  view original       52 maps   blood-campaign, blood-bloodbath
```

| population | maps | runs | median gap |
| --- | --- | --- | --- |
| campaign only | 43 | 99 | 1.56 |
| campaign + BloodBath (`original`) | 52 | 123 | 1.16 |
| **campaign + BB + curated (`reference`)** | **102** | **790** | **0.50** |
| everything, bulk community too | 1776 | 5879 | 0.62 |

`reference` reproduces the published distribution exactly -- median 0.50 and
q3 1.25 identical, q1 0.23 against 0.24 -- with counts 12% higher because the
curated set has grown since. That is what the flat directory was.

## What the campaign-only reading costs

Every miner run at both views, against the file it published:

```text
                                    published  reference   original

mine_run_rhythm  ->  knowledge/blood/design/run-rhythm-v1.json
  runs examined                         702        790        123
  gaps measured                        4755       5354        288
  median gap, plan units                0.5        0.5       1.16
  q3 gap, plan units                   1.25       1.25        2.5

mine_set_pieces  ->  knowledge/blood/design/set-pieces-v1.json
  sectors examined                    29966      33567       9515
  pieces found                         7014       7620       2653

mine_monuments  ->  knowledge/blood/design/monuments-v1.json
  monuments                             421        431         68
  maps with one                          66         63         30
  carrying statuary                      77         73         17
  median top, plan units                2.0        2.0        2.0

mine_prop_catalogue  ->  projects/blood-city/references/prop-catalogue.json
  tiles catalogued                      263        313         71

mine_style_combinations  ->  projects/blood-city/references/style-combinations.json
  rooms examined                      19504      20710       7247
  distinct styles                      6316       6767       2276
```

Counts collapse by 60--85% everywhere. Two things are worth separating out.

**Shape statistics mostly survive; headline rates do not.** The monument's
median top stays 2.0 plan units at every view -- a monument is the same shape
wherever it is built. But run rhythm's median gap moves from 0.50 to 1.16
plan units, better than double. The published rhythm number is a
reference-set fact, and re-mining it campaign-only does not refine it, it
replaces it.

**The prop catalogue is the severe one.** 313 tiles at `reference`, 71
campaign-only: 242 tiles lose their evidence entirely.

## What BloodCity actually depends on

The catalogue is not an abstraction; the level is built from it.

```text
decoration sprites placed in blood-city-current.MAP   296
distinct tiles among them                               52
  attested in the reference catalogue                   47
  attested campaign-only                                22
  would lose their evidence                             25   (88 sprites)
```

The tiles that would go unattested:

```text
  52 218 269 431 617 676 761 793 823 847 956 965 1417 3809 3810 3811 3813 3814 3815 3818 3820 3828 3829 3830 3832
```

Twelve of those twenty-five are 3809-3832 -- the lettering alphabet. The
campaign barely writes signs: the facade study found 26 campaign letters on
3 facades in 2 maps, against 60 curated ones. A campaign-only corpus cannot
attest a shopfront sign at all, and signage is the owner's stated first wish
for the city.

## Recommendation

**Keep `reference` as the evidence base and fix the label.** The protocol's
rule is about not passing community practice off as Monolith convention, and
that is satisfied by saying which is which -- not by discarding 30% of the
decoration the project has already placed, and the whole of its sign
vocabulary, to buy a narrower claim nobody needs.

Done here, so the question cannot go unanswered again: all five miners take
`--view`, defaulting to `reference`, and **stamp the population into their
output**. A file mined from now on names its own evidence.

Not done, because it is the owner's call and it rewrites published numbers:

- re-mining the five artifacts so they carry the stamp, and
- deciding whether any specific claim in them should be restated as
  precedent rather than convention.

`tests/test_mining_population.py` records that none of the five is stamped
today, and fails when that changes -- which is the signal to revisit this
page rather than a reason not to.

## Limitations

- The flat directory's exact contents are inferred from the numbers it
  produced, not recovered. `reference` reproduces the distribution and the
  count is 12% low, which is consistent with a smaller curated set in August
  and with nothing else tested here.
- `mine_assemblies` is not in this table. Its docstring names "the shipped
  episodes" specifically and `tests/test_assembly` pins it to the campaign
  directory, so campaign-only is right there and was left alone.
- The dependency count is decorations only -- `status 0, type 0` sprites,
  the population the prop catalogue describes. Walls, floors and mechanisms
  have their own evidence and are not priced here.

