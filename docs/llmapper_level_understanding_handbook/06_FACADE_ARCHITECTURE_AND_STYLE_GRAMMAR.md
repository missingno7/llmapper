# Facade, Architecture and Style Grammar

## Core principle

> The facade owns the openings. The opening does not own the facade.

Do not implement storefronts as isolated windows inserted into arbitrary walls.

Mine and represent the larger architectural composition.

Existing starting points: `bloodmap/aperture.py` already encodes the
project's aperture grammar (an opening is a leaf plus mediation; dress the
reveal, never the band above the mouth), `bloodmap/texture_align.py` and
`bloodmap/lettering.py` handle surface continuity and signage, and
`knowledge/blood/design/run-rhythm-v1.json` / `wall-thickness-v1.json`
record measured rhythm and trim evidence. Rendered street views of a real
storefront exist under `projects/blood-city/references/e6m1-shop-views/`.

## Hierarchy

Candidate model:

```text
BUILDING
  -> FACADE
      -> BAY
          -> WINDOW
          -> STOREFRONT
          -> ENTRANCE
              -> reveal
              -> frame
              -> glass
              -> door
              -> signage
```

This hierarchy must be derived from original/curated evidence rather than assumed
from real-world architecture textbooks.

## Thin sectors are not noise

A thin sector may be:

- reveal,
- shadow gap,
- frame,
- recess,
- material separator,
- facade continuity device,
- architectural trim.

A sector that is almost empty may carry a strong design role.

This is analogous to `gap` or `padding` in UI layout: empty space is part of the
composition.

## What to mine

For street-facing facades, measure:

- main facade plane,
- bay segmentation,
- opening width,
- opening depth/recess,
- sill datum,
- header datum,
- cornice datum,
- repeated columns,
- material continuity,
- trim family,
- signage placement,
- rhythm and intentional breaks,
- door centering/asymmetry,
- storefront-to-window relationships.

## Style inheritance

Prefer hierarchical style propagation:

```text
building
    -> facade
        -> bay
            -> opening
                -> explicit exception
```

Useful inherited properties may include:

- material family,
- trim,
- shade,
- palette,
- repeated dimensions,
- sill/header alignment.

This is consistent with the broader observation that surfaces are often
propagated regionally rather than selected independently per sector.

## Rhythm

Mine relations such as:

```text
same
approximately_same
repeating
alternating
centered
aligned
mirrored
intentionally_broken
```

Do not regularize away authored irregularity.

## Facade pilot

Select several original Blood urban/street-facing examples.

For each:

1. identify facade extent,
2. identify main plane,
3. identify openings,
4. inspect thin helper sectors,
5. infer bay hierarchy,
6. measure repeated datums,
7. render street views,
8. search cross-map analogues,
9. inspect counterexamples.

Only after recurrence is established should a constructor such as
`facade_run()` or `storefront()` be promoted.

## Minimal constructor philosophy

Prefer composable primitives:

```text
facade_run
facade_bay
window_with_reveal
storefront
recessed_entrance
```

Avoid a giant:

```text
generate_shop()
```

that hides design logic and becomes impossible to generalize.
