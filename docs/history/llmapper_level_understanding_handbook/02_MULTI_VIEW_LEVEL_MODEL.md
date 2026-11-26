# Multi-View Level Model

## Core idea

A level does not have one correct representation.

The same physical area can simultaneously be:

- a geometric corridor,
- a topological edge,
- a service passage,
- a combat chokepoint,
- a required progression route,
- a dark visual transition,
- a reveal into another architectural region.

The system should preserve several overlapping views and only reconcile them when
a design decision requires it.

## Recommended views

### 1. Physical / geometric view

Questions:

- What sectors, walls and sprites physically exist?
- What are their dimensions, heights and surfaces?
- Which primitives touch or overlap?
- Which walls are portals?
- Which sectors are small geometric helpers?

Evidence source:

- exact MAP data.

### 2. Semantic / architectural view

Questions:

- Which low-level primitives form one object?
- Which objects form assemblies?
- Which openings belong to one facade?
- Which sectors are trims, reveals, stairs, shelves, railings, furniture, etc.?

Important property:

```text
one semantic object != one Build primitive
```

A semantic object may be an arbitrary graph of sectors, walls, sprites and
properties.

### 3. Functional view

Questions:

- What is this space used for?
- What side of an object is meant to be accessed?
- What region acts as storage, shop floor, office, staff area, circulation,
  display, entrance, service corridor?

A room may contain multiple functional regions.

### 4. Mechanic / dynamic view

Questions:

- What can change?
- Which parts change together?
- What causes the change?
- What are stable states?
- Is the transition reversible?
- What physical property changes?

Examples:

- doors,
- lifts,
- rotating sectors,
- sliding sectors,
- crushers,
- raising/lowering floors,
- breakable barriers,
- flooding,
- lighting state changes.

### 5. Topology / progression view

Questions:

- What can the player reach at rest?
- What connections are conditional?
- Which mechanism opens/closes a route?
- Which key/switch/event gates a region?
- Which actions close loops or create shortcuts?

This view should eventually include **conditional topology**, not only static
reachability.

### 6. Gameplay view

Questions:

- What does the player do here?
- Is this an encounter space, traversal segment, resource detour, secret,
  chokepoint, staging area, escape route?
- How many approaches/exits exist during combat?
- Where are enemies, pickups and cover relative to routes?

Do not infer gameplay solely from decoration.

### 7. Visual / aesthetic view

Questions:

- What visual hierarchy is created?
- What material patches propagate?
- What lighting direction is implied?
- What facade rhythm exists?
- What is visually dominant?
- Where are authored asymmetries?

Evidence should include rendered player views.

### 8. Readability / communication view

Questions:

- Does the player understand that something is a door?
- Does a passage look intentional or merely like a hole?
- Can the player read the front of a cabinet?
- Does a storefront belong visually to the same facade?
- Does the level communicate locked/openable/destructible state?

Readability is neither pure geometry nor pure aesthetics.

## Design intent

Generation should not go directly from prose to coordinates.

Use an intermediate design-intent representation.

Example:

```yaml
space: street_shop

function:
  - public retail
  - optional exploration

architecture:
  parent: facade_17
  role: ground_floor_bay

gameplay:
  role: optional_resource_detour

visual:
  role: bright_glass_opening_in_dark_masonry

readability:
  entrance_must_read_as_enterable: true

relationships:
  - adjacent_to: alley_3
  - belongs_to: facade_17
  - overlooks: street_1

constraints:
  - storefront_header_aligns_with_facade_datum
  - recessed_glass_preserves_facade_plane
  - entrance_remains_walkable
```

Authoring code then solves how to express this in Build geometry.

## View conflicts are expected

Examples:

```text
AESTHETICS:
  long symmetrical hall

GAMEPLAY:
  symmetry produces flat combat

READABILITY:
  player loses orientation

ARCHITECTURE:
  asymmetrical service entrance is plausible
```

The correct result may combine views rather than average them:

```text
symmetrical ceremonial hall
+
asymmetrical service wing
```

## Hard, soft and stylistic constraints

### Hard

Violation means broken or unusable.

Examples:

- doorway cannot fit player,
- stair lacks clearance,
- mandatory key appears after locked gate,
- sector geometry invalid,
- shelf access side intersects wall.

### Soft

Violation may produce weaker design.

Examples:

- combat has only one approach,
- facade rhythm is inconsistent,
- room lacks focal point,
- lighting does not support orientation.

### Stylistic preference

Intentional axis of variation.

Examples:

- more vertical,
- more cramped,
- more urban,
- more grotesque,
- more E1-like.

Do not accidentally turn soft/style observations into hard validation failures.
