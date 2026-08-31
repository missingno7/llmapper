# Long-Term Target and Non-Goals

## Long-term target

The system should eventually be able to understand and synthesize a request such
as:

```text
Build a small street-facing shop with:
- coherent two-bay facade,
- recessed storefront,
- side entrance,
- display shelving,
- counter separating customer and staff,
- small rear storage,
- one optional breakable shortcut,
- lighting that makes the entrance readable.
```

without the LLM directly inventing raw Build coordinates.

The internal reasoning should roughly be:

```text
intent
-> semantic scene graph
-> functional regions
-> architecture
-> negative-space constraints
-> mechanisms
-> conditional topology
-> style inheritance
-> deterministic authoring primitives
-> map
-> independent validation
-> scoped repair
```

## What success looks like

### Furniture

Not:

```text
added a shelf prefab
```

But:

```text
system can explain why shelf != crate pile,
find several structural variants,
and generate a new shelf preserving the defining relations.
```

### Facades

Not:

```text
added windows
```

But:

```text
system can explain why openings form one facade,
what maintains continuity,
and adapt the facade to another width.
```

### Mechanisms

Not:

```text
added an elevator constructor
```

But:

```text
system can distinguish a lift from a door despite similar engine motion,
explain the topology delta,
and place the mechanism for a design reason.
```

### Gameplay

Not:

```text
map has enough enemies and loops
```

But:

```text
system understands why a loop exists, when it becomes available,
and what gameplay/progression role it serves.
```

## Non-goals

Do not aim for:

- a complete universal ontology of all level design,
- imitation by screenshot alone,
- optimization to campaign medians,
- manual annotation of every object,
- one monolithic canonical scene graph,
- LLM-generated coordinate soup,
- one giant prefab per room type,
- a critic that outputs one quality number.

## Core thesis

> AI should stop building things that merely resemble a level and instead learn
> to compose space using the same kinds of structural, functional, mechanical,
> visual and gameplay relationships that authored maps contain.

And the learning direction is:

> Existing maps first. Generation second.

The system should decompile authored level design deeply enough that synthesis
becomes recombination of understood relationships rather than imitation.
