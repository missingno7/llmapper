# Authored planar geometry

Scratch-built Blood maps need a stricter gate than original-map parsing.
`validate_map()` stays the native structural checker: original maps may use
engine tricks that are legal to load and illegal to author from a blueprint.

## Two validators

| function | used for | fails on |
| --- | --- | --- |
| `validate_map()` | original Blood/Duke files, lossless roundtrips | broken wall ownership, portal field pairing, extra-index errors |
| `validate_authored_geometry()` / `validate_authored_level()` | newly compiled or substantially regenerated maps | crossings, T-junctions, partial collinear overlaps, accidental XY overlap, unpaired shared boundaries, isolated DM starts |

Both return **all** diagnostics. The first conflict does not stop the scan.

```text
python -m bloodmap validate maps/blood/BB2.MAP
python -m bloodmap validate-authored work/BB2-semantic-reconstruction-v3.MAP
python -m bloodmap geometry-audit work/BB2-semantic-reconstruction-v2.MAP \
    --json reports/BB2-v2-geometry-audit.json \
    --svg reports/BB2-v2-geometry-audit.svg
```

`geometry-audit` / `validate-authored` on a frozen MAP are fail-closed unless
the caller passes blueprint declarations (water stacks, partitions, gated
pockets). Compile-time validation does pass those declarations. The v2 forensic
narrative in `reports/BB2-v2-geometry-audit.md` is hand-authored from the JSON
packet; re-running `--markdown` overwrites it with a compact machine summary.

## PlanarLayout

`PlanarLayout` is the replayable source representation above `LevelIR`. Semantic
IDs (`region:main_exterior`, `connection:north_mouth`) are design identity.
Wall indices are compiler output.

The compiler:

1. collects directed boundary segments
2. splits at T-junctions and collinear overlap endpoints
3. rejects proper crossings (including non-integer intersections)
4. reconstructs outer/hole loops
5. pairs intended reversed coincidences as portals
6. emits contiguous Build sector/wall arrays
7. reports conservation: no dropped or duplicated source edges; each emitted wall owned once

Partial example: wall A `0→100` and wall B `80→20` become atomic `20↔80` and
that shared interval is portaled. Callers do not compute post-split wall IDs.

Holes and masonry use `carve_hole` / `insert_building_shell`. A building is an
outer footprint carved from the host plus a strictly smaller inner footprint.
The gap is wall mass. Doorways are real sectors that cross the thickness.
Coincident unpaired walls are allowed only when declared as a thin/solid
partition.

Stacked water is an explicit special pair: same XY, disjoint or touching Z,
markers 9/10. It is not inferred from overlap alone.

## Construction vs layout

`LevelBuilder.add_sector` still validates only the new polygon.
`LevelBuilder.connect` still requires exact reversed endpoints.
`LevelBuilder.build` still runs `validate_map()` only, because Doom lowering and
campaign conversion reuse the builder on geometry that may include original-map
tricks.

New irregular maps should go through `PlanarLayout.compile()`.

## Deathmatch feasibility

`validate_authored_level` additionally requires that every DM start reaches the
largest at-rest circulation component, that intended adjacencies exist as
reciprocal portals, and that ordinary resources are not stranded unless marked
gated. Spawn concealment must not be implemented by disconnecting starts.

Hard design-contract assertions name these evaluators. Caller-supplied booleans
such as `player_start_valid=True` are ignored.
