# Negative Space, Functional Regions and Object Assemblies

Existing starting points: `bloodmap/player_space.py` (openings, clearance,
enclosure vs source-backed player profiles), `bloodmap/furniture.py`
(named props with mounting semantics), `bloodmap/placement.py`,
`bloodmap/reachability.py` (role assignment for non-playable geometry is
the precedent for role assignment generally). The e6m1-shop reference
(`projects/blood-city/references/e6m1-shop.md`) records one real shop's
counter / retail floor / display clusters.

## Negative space is a design object

Many important design constraints are about intentionally empty space.

Examples:

- cabinet-door swing clearance,
- drawer pull-out volume,
- chair seating/approach space,
- aisle in front of shelving,
- staff workspace behind a counter,
- doorway approach zone,
- storefront reveal,
- visual separation gap,
- stair head clearance,
- landing clearance,
- combat circulation,
- sightline.

These spaces may exist only in the design model. They do not always need their
own Build sector.

## Why this matters

A shelf can be geometrically valid and still be functionally wrong if the player
cannot access its front.

A storefront can use the right glass and trim but still look wrong if the facade
plane has no reveal or visual separation.

A passage can be traversable but still read as "a hole in the wall" rather than
an authored connector.

## Suggested negative-space representation

Example:

```yaml
clearance:
  id: shelf_12_access
  owner: shelf_12
  role: access_front
  shape: prism
  hard: false
  required_free_from:
    - static_solids
  preferred_free_from:
    - decoration
```

Do not over-engineer geometry representation initially. The important step is to
represent the concept and validate obvious violations.

## Object assemblies

Discover and represent recurring bundles, not only isolated objects.

Candidate assemblies:

```text
table + chairs
desk + chair
desk + lamp
shelf + bottles/boxes
counter + props + workspace behind
display + merchandise
cabinet + drawer fronts
storage rack + crate piles
shop shelf rows
```

Grouping signals may include:

- proximity,
- alignment,
- consistent orientation,
- repeated spacing,
- shared wall,
- common height,
- contact/support,
- enclosure,
- complementary semantics,
- shared functional region.

Proximity alone is insufficient.

## Functional regions

A room may contain several semantic sub-regions.

Examples:

- shop floor,
- display region,
- counter region,
- staff-only region,
- rear storage,
- office corner,
- seating zone,
- warehouse aisle,
- reception,
- transition zone.

Functional regions are useful because they bridge object-level understanding and
whole-room semantics.

## Pilot region grammar

For a shop:

```text
SHOP
 |
 +-- public_floor
 |     +-- display_shelves
 |     +-- circulation
 |
 +-- counter_boundary
 |     +-- counter
 |     +-- customer_front
 |     +-- employee_workspace
 |
 +-- storage
 |
 +-- entrance
 |
 +-- facade
       +-- storefront
       +-- signage
```

The system should mine whether Blood maps actually support these relationships
before turning them into authoring rules.

## Affordances

Useful object affordances:

```text
supports
contains
displays
blocks
opens
can_be_used
can_be_broken
can_be_walked_on
requires_front_access
requires_clearance
provides_cover
```

Affordances are often more transferable than art identity.

## Random-prop-scattering detector

A common AI failure is to achieve correct density by scattering objects randomly.

Look for the absence of authored structure:

- no grouping,
- no orientation,
- no relation to walls,
- no functional zoning,
- no access clearance,
- no repeated spacing,
- no support/contact relationship,
- no visual hierarchy.

A map may match sprite counts and still fail composition.

## Authored imperfection

Do not over-regularize.

Blood may use:

- nearly regular rhythms,
- one missing element,
- slightly irregular spacing,
- broken crate,
- rotated chair,
- partially empty shelf,
- asymmetrical clutter.

Learn the difference between:

```text
intentional irregularity
```

and:

```text
generation error
```

by comparing neighborhoods across the corpus.
