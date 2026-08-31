# Semantic Anchors and Recursive Subgraph Mining

## Goal

Teach the system to discover larger authored structures from sparse low-level
clues and recurring relations.

The target capability is:

> Given a primitive, answer: "What larger thing is this part of?"

## Semantic anchors

Manual labels are sparse high-confidence anchors.

Examples:

```text
tile 1234 = drawer front
tiles 812..816 = carpet family
material group X = wood
these source maps/regions = sewer examples
sprite 2915 = floor decoration
```

Anchors are not complete concepts. They seed corpus queries.

## Existing precedent in the repository

Two working single-anchor miners already implement this discipline and are
the style to generalize, not replace:

- `tools/mine_e6m1_shop.py` — owner-identified shop assets, complete
  carrying sectors, one-hop neighborhoods, explicit refusal to infer that a
  tile elsewhere is also a shop;
- `tools/mine_sewer_kit.py` — role-separated tile occurrences with the
  densest original map and complete technical setting.

Related CLI: `sprite-context-mine`, `door-mine`, `materials-mine`,
`pattern-mine` (unsigned side in `bloodmap/patterns.py`). The candidate
lifecycle below matches the DERIVED / INTERPRETED split already used in
`knowledge/blood/design/`.

## Multi-scale neighborhood extraction

For every anchor occurrence, inspect context at several scales.

Conceptually:

```text
scale 0: primitive itself
scale 1: immediate adjacency
scale 2: likely object-scale cluster
scale 3: enclosing functional region / room
scale 4: architectural context
scale 5: progression/gameplay context
```

Do not hard-code graph radii if better adaptive grouping exists.

## Relation vocabulary

Keep the relation set minimal and evidence-driven.

Candidate relations:

```text
part_of
attached_to
contains
inside
supports
supported_by
against_wall
faces
open_to
accessible_from
aligned_with
parallel_to
perpendicular_to
coplanar_with
above
below
between
stacked_on
repeats_along
shares_height_with
shares_style_with
belongs_to_facade
belongs_to_region
triggers
changes
blocks
connects_when
```

Relations should be derived from geometry or native Blood semantics whenever
possible, not guessed by prose.

## Normalize before comparing

Recurring structures should survive:

- translation,
- rotation,
- wall winding,
- mirror symmetry where meaningful,
- limited scale variation where meaningful,
- repeated-part count variation.

Do not search for byte-identical geometry.

## Structure discovery loop

```text
semantic anchor
    |
    v
all original-map occurrences
    |
    v
extract relational neighborhoods
    |
    v
cluster recurring structures
    |
    v
unsigned structural candidates
    |
    v
form hypotheses
    |
    v
search entire corpus for anchor-free matches
    |
    v
counterexamples + variants
    |
    v
interpret / review / promote
```

## Example: drawer front -> drawer unit

Do not learn:

```text
picnum == 1234 -> drawer
```

Instead search for repeated context:

```text
drawer-front faces
    repeated vertically
    inside shallow aligned sectors
    surrounded by wood
    common front direction
    free access space in front
```

Then search for structurally equivalent examples using different art.

Possible hierarchy:

```text
drawer-front wall
    -> drawer
    -> drawer stack
    -> cabinet
    -> desk/cabinet assembly
    -> office region
```

## Contrastive mining

For confusing pairs, explicitly mine the differences.

Examples:

- shelf vs crate pile,
- shelf vs cabinet,
- cabinet vs drawer unit,
- table vs counter,
- chair vs stool,
- shelf vs railing,
- storefront vs generic window,
- window vs wall decoration,
- column vs furniture.

Store candidate discriminators such as:

```text
privileged_front
open_front
repeated_horizontal_support_surfaces
against_wall
contains_smaller_props
solid_closed_volume
stackable_identical_units
requires_access_clearance
```

Do not invent numeric confidence values without measured evidence.

## Structure before naming

Preferred order:

```text
discover recurring structure
-> characterize relations
-> inspect contexts
-> propose semantics
```

Avoid:

```text
guess object name
-> search for evidence supporting the guess
```

The latter creates confirmation bias.

## Recursive abstraction

Once a concept is learned, use it as a higher-level atom.

Example:

```text
low-level primitives
    -> SHELF

SHELF + boxes + aisle
    -> STORAGE_ASSEMBLY

STORAGE_ASSEMBLY + counter + entrance
    -> SHOP_REGION

SHOP_REGION + facade + back room
    -> STREET_SHOP_PATTERN
```

This recursive step is essential. Without it the knowledge base remains a flat
catalog of small objects.

## Candidate lifecycle

Recommended states:

```text
observed
candidate
hypothesis
supported_pattern
strong_norm
constructor_ready
```

Promotion requires:

- recurrence,
- counterexample search,
- understood invariant,
- provenance,
- usefulness for generation or critique,
- tests.
