# Design-pattern discovery

This layer sits between grounded sensors and LLM interpretation.

```text
RAW MAP
  → exact native facts
  → grounded sensors
  → recurring relationships
  → design pattern knowledge
  → LLM interpretation
  → Design Contract / prose
  → agentic construction
  → independent understanding
  → semantic delta
```

A pattern is a **hypothesis over evidence**, usually a relation, not a prefab
and not a room name. The same place may match several patterns.

## Populations

Provenance is **the directory a map lives in**, resolved by the corpus registry
in `bloodmap/patterns.py`; filename prefixes are only a sanity cross-check.
Populations are never mixed while mining. Layout and owner-provenance notes:
[`maps/blood/README.md`](../maps/blood/README.md) (local-only) and
`docs/llmapper_level_understanding_handbook/07_...md`.

| population | directory | files | standing |
| --- | --- | --- | --- |
| `blood-campaign` | `campaign/` | `E*M*.MAP` | authoritative Blood SP convention |
| `blood-bloodbath` | `campaign/multiplayer/` | `BB1`–`BB9` | authoritative Blood MP convention |
| `community-curated` | `curated/` | `DWE*`, `TEDE*`, `SS*`; MP `DWBB*`, `DM*` | vetted precedent |
| `own-conversion` | `conversions/` | `DNE*` | cross-game evidence only |
| `community` | `community/` (= `tiered/`) | arbitrary names | wide precedent |
| `mechanism-tutorial` | `mechanism/` | `#*.MAP`, `Modern/`, `Vanilla/` | mechanism wiring, not norms |
| `generated` | — | `*RECONSTRUCTION*`, `*-BLOOD.MAP` | never evidence |

**Owner correction, 2026-08-31.** An earlier version of this table listed
`DWE*`, `TEDE*` and `DNE*` together as `conversion`. That was wrong. `DWE*`
(Death Wish) and `TEDE*` are hand-picked *community source maps*; only `DNE*`
are conversions, and those are the owner's own manual Duke3D→Blood work, usable
as cross-game correspondence evidence and never as Blood design convention.

Authoritative Blood design statistics come only from `blood-campaign` and
`blood-bloodbath`. `community-curated` supplies vetted precedent ("hand-picked,
demonstrated to work well in Blood"); bulk `community` supplies wide precedent,
always labeled as such. Tier metadata (`S|A|B|C|questionable|multiplayer|
mechanism`, from a heuristic classifier) is a sampling order, never an evidence
weight.

Named views over populations:

```text
reference = campaign/ + curated/     the quality yardstick
original  = campaign/ (both modes)   the only populations citable as convention
```

## What is measured first

Unsigned candidates are discrete signatures over:

- spawn neighborhoods (BloodBath multiplayer starts)
- route exposure sequences (cover/sky, hops, Z, shade)
- local morphology (normalized loop metrics, not coordinates)
- vertical transitions on at-rest walkable edges
- object context: what a sector holds, what holds it up, and how the sector
  sits among its neighbours, from Phase 1 relations
  (`reports/blood-object-context-families.md`)

No taxonomy of room / corridor / arena is searched for. After a signature
recurs, an INTERPRETED label may be attached. Counterexamples can dispute or
split it.

## Commands

```text
python -m bloodmap pattern-mine --maps maps/blood --population blood-bloodbath \
  -o work/blood-pattern-unsigned-bloodbath.json
python -m bloodmap pattern-mine --maps maps/blood --population blood-campaign \
  -o work/blood-pattern-unsigned-campaign.json
python knowledge/blood/design/compile_catalog.py
python -m bloodmap pattern-query knowledge/blood/design/catalog-v1.json \
  --view spawn-neighborhood --require "{\"hops\":\"0\"}" --limit 8
python -m bloodmap pattern-inspect knowledge/blood/design/catalog-v1.json \
  pattern:spawn:open-hunting-cell
python -m bloodmap understand maps/blood/campaign/multiplayer/BB6.MAP \
  --multiplayer-only --patterns knowledge/blood/design/catalog-v1.json \
  -o reports/BB6-understanding.json
```

`--maps` is the corpus **root**; the registry descends into the population
directories itself. To mine vetted precedent or a community tier instead:

```text
python -m bloodmap pattern-mine --maps maps/blood --population community-curated \
  -o work/blood-pattern-unsigned-curated.json
python -m bloodmap corpus-health --maps maps/blood --population community --tier S \
  -o reports/blood-community-tier-S-health.json
```

`pattern-query` returns multiple hits. It does not pick a single best match.

Object-scale relations and anchor queries are separate surfaces:

```text
python -m bloodmap relation-dump maps/blood/campaign/E6M1.MAP \
  --sector 32 --hops 1 -o work/e6m1-shop-relations.json
python -m bloodmap anchor-mine --name mannequin --tile 2377 \
  --view reference -o work/anchor-mannequin.json
```

See [`reports/blood-object-relations-pilot.md`](../reports/blood-object-relations-pilot.md)
and [`reports/anchor-queries.md`](../reports/anchor-queries.md).

## Knowledge store

Versioned hypotheses live in [`knowledge/blood/design/`](../knowledge/blood/design/).
Catalog v1 is compiled from unsigned mines plus INTERPRETED labels in
`compile_catalog.py`. Occurrences point at original maps. Generated maps may
be *scored* against the catalog during reconstruction, but they are not
evidence for the patterns.

## First validation

BB6 (Twin Fortress), not BB2:

- [pattern-aware understanding](../reports/BB6-understanding.md)
- [small blind reconstruction](../reports/BB6-semantic-roundtrip.md)
- [examples](../reports/blood-pattern-examples.md)
- [counterexamples](../reports/blood-pattern-counterexamples.md)
- [corpus summary](../reports/blood-pattern-corpus-summary.json)
