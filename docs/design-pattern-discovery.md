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

Filename provenance is fail-closed. These are never mixed while mining:

| population | files |
| --- | --- |
| `blood-campaign` | original `E*M*.MAP` |
| `blood-bloodbath` | original `BB*.MAP` |
| `conversion` | `DWE*`, `DNE*`, `TEDE*`, `*-BLOOD.MAP` |
| `generated` | reconstructions (`*RECONSTRUCTION*`) |

Authoritative Blood design statistics come only from the original campaign and
BloodBath populations.

## What is measured first

Unsigned candidates are discrete signatures over:

- spawn neighborhoods (BloodBath multiplayer starts)
- route exposure sequences (cover/sky, hops, Z, shade)
- local morphology (normalized loop metrics, not coordinates)
- vertical transitions on at-rest walkable edges

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
python -m bloodmap understand maps/blood/BB6.MAP --multiplayer-only \
  --patterns knowledge/blood/design/catalog-v1.json \
  -o reports/BB6-understanding.json
```

`pattern-query` returns multiple hits. It does not pick a single best match.

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
