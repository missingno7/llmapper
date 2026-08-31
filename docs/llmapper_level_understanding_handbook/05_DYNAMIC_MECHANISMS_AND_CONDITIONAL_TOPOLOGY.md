# Dynamic Mechanisms and Conditional Topology

## Principle

Dynamic understanding should extend the existing `Assembly` concept, not create a
parallel framework.

`Assembly` answers:

> Which objects belong to one mechanism?

The missing generic layer should answer:

> What physical state change can this assembly perform?

Then specialized interpretation answers:

> What design object is that change? Door? Lift? Crusher? Floodgate? Secret wall?

And spatial analysis answers:

> What does the change do to reachability, visibility and progression?

Most of the first two questions are already answered in the repository:
`assembly.py` (membership, travel, pivot, carried parts), `doors.py`
(rest/open geometry + interaction/condition/feedback/signifier facets),
`mechanism.py` (template-driven construction), `motion_sim.py`
(engine-exact motion replay as the oracle), `state_model.py`
(PlayerState/WorldState/PlayerKnowledge). The genuinely missing layer is
the neutral effect vocabulary below and the conditional-topology view —
read those as *readings over* the existing modules, not rewrites.

## Do not encode two complete maps

Represent:

```text
base geometry + state delta
```

instead of separate copies of the whole level.

## Neutral physical effects

Start with a small evidence-backed vocabulary:

```text
move_z_floor
move_z_ceiling
move_z_split
translate_xy
rotate_xy
change_blocking
destroy
spawn
despawn
change_surface
change_light
change_medium
```

Do not force all mechanisms into one universal state-machine model immediately.

## Stable states and transitions

Common stable-state forms:

```text
closed / open
lower / upper
intact / destroyed
off / on
dry / flooded
```

Keep the option for continuous transition values:

```text
door angle
elevator z
water height
light waveform
```

but most design reasoning can start from stable states plus transition semantics.

## Example: door

```yaml
assembly: gate_17

rest:
  aperture: blocked

active:
  aperture: walkable

effects:
  - type: move_z_ceiling
    target: sector_53

transition:
  reversible: true
```

Semantic interpretation:

```text
vertical door
```

## Example: elevator

```yaml
assembly: lift_3

low:
  aligns_with: floor_1

high:
  aligns_with: floor_2

effects:
  - type: move_z_floor
  - type: move_z_ceiling

semantic:
  elevator
```

The important distinction from a door is spatial role, not low-level motion type.

## Example: breakable barrier

```yaml
assembly: barrier_8

intact:
  blocks: region_A_to_B

destroyed:
  enables: region_A_to_B

transition:
  reversible: false
  cause: destruction
```

Motion and destruction are different physical mechanisms but may have the same
design consequence: opening a connection.

## Conditional topology

Extend spatial analysis with a derived view such as:

```text
conditional_traversability
```

Example:

```yaml
edge:
  from: region_A
  to: region_B

at_rest: blocked

conditions:
  - when: door_17 == open
    traversable: true
```

Elevator:

```yaml
connection:
  floor_1 -> elevator
  when: elevator == low

connection:
  elevator -> floor_2
  when: elevator == high
```

Breakable wall:

```yaml
connection:
  A -> B
  when: barrier_8 == destroyed
  irreversible: true
```

## Causal graph

Blood channels already provide a native causal substrate.

Lift the native relationship:

```text
TX channel -> RX channel
```

into an interpreted chain:

```text
player uses switch
    -> switch transmits
    -> gate changes state
    -> topology changes
    -> new region becomes reachable
```

This eventually becomes progression knowledge.

## Mining dynamic design patterns

Do not stop at mechanism families.

After enough lower-level understanding, discover patterns such as:

- shortcut opener,
- arena lock-in,
- delayed escape route,
- keyed progression gate,
- reversible lift connection,
- destructible alternate route,
- environment transformation,
- trap activation chain.

## Recommended first experiment

Use similar low-level Z-motion mechanisms and intentionally ignore their names.

Find at least:

1. a door,
2. a lift,
3. a non-door/non-lift Z-motion mechanism.

For each report:

```text
LOW LEVEL
  what fields and state deltas are similar?

SPATIAL EFFECT
  what changes in occupancy/reachability?

SEMANTICS
  why does the same engine mechanism mean a different design object?
```

If the system can explain this distinction from map context, the abstraction
boundary is correct.
