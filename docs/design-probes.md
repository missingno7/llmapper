# Design Probe System

The Design Probe system lets a future LLM test specific hypotheses about a level
in the same way a coding agent runs tests against software.

## Core principle

The LLM should not be expected to infer the entire player experience from static
MAP data. It should be able to:

1. Propose a design hypothesis
2. Run a bounded deterministic experiment against the level
3. Inspect the result
4. Revise its design

This is the level-design analogue of:
write code → compile → test → inspect failure → modify

For llmapper:
construct/edit level → validate → run design probes → inspect experience
evidence → render selectively if useful → modify

## Architecture

### State layers

The probe system introduces explicit state layers separate from the static
BuildIR:

- **PlayerState** (`bloodmap/state_model.py`): position, sector, angle, keys
- **WorldState** (`bloodmap/state_model.py`): doors open/closed, lifts
  position, switches, destructible barriers, water/teleport links,
  enabled/disabled routes
- **PlayerKnowledge** (`bloodmap/state_model.py`): seen sectors, known
  landmarks, known locked routes, visited areas, known objectives

This separation is important because:
same geometry + different knowledge = different player experience

### Design Probe schema

A Design Probe is a replayable question about a level. It has:

- Starting state (player, world, knowledge)
- Question / hypothesis
- Bounded inputs
- Deterministic procedure
- Structured result with evidence

Schema: `llmapper.design-probe` (version 1)

### Probe result

Every probe returns a structured result with:

- Status: pass, fail, inconclusive, error
- Evidence: list of evidence with source classification
- Measurements: dict of measured values
- Route: compressed sector path (if applicable)
- Blocking reasons: list of strings
- Required keys/mechanisms: list of IDs
- State changes: list of state change records
- Limitations: list of strings
- Fidelity level: L0, L1, L2, L3

Schema: `llmapper.probe-result` (version 1)

### Evidence classification

Every probe result includes evidence with source classification:

- `static_exact`: derived from exact map structure (geometry, topology,
  references)
- `static_approximate`: derived from approximate static analysis (heuristics,
  bounds)
- `semantic_simulation`: derived from semantic mechanism model (doors, lifts,
  switches)
- `real_engine`: derived from real engine runtime (NBlood/EDuke32 oracle)

## Fidelity levels

### L0 — graph/state reasoning

Cheap reasoning over geometry topology, known semantic mechanisms, keys,
switches, state-dependent connectivity.

Questions:
- Is target reachable?
- Which mechanism blocks it?
- What becomes reachable after switch X?
- Does a route exist without key Y?
- Is the exit reachable in the initial state?

This is deterministic and fast.

### L1 — spatial traversal

Uses actual Build geometry and per-game player profiles where needed.
Accounts for understood:
- player dimensions
- vertical clearance
- step height
- slopes
- blocking walls
- door states
- lift states
- water/teleport transitions

The goal is to distinguish:
- a graph connection exists
from:
- the player can physically traverse it

Blood and Duke3D have different player scale/clearance characteristics; use the
existing game-profile abstractions rather than scattering constants.

### L2 — perceptual traversal

Begins implementing or preparing observations about what changes along a route.

Possible evidence:
- newly visible regions
- newly visible landmarks
- visible route choices
- approximate view depth
- opening width
- relative ceiling height
- lighting/material transition

Do not pretend to solve human perception exactly.
Keep this evidence grounded and mark approximations.
Use actual NBlood/EDuke32 rendered views selectively when a visual observation
cannot be derived safely from geometry.

### L3 — abstract gameplay reasoning

Keep this mostly architectural for now.
Potential future concepts:
- enemy exposure
- cover opportunities
- retreat paths
- resource pressure

Do not implement precise enemy AI, combat, projectile simulation, or weapon
balance in this task.

## Probe types

### probe_access

Question: «Can the player reach X under world state Y?»

Return:
- reachable
- blocking reasons
- required keys
- required mechanisms
- candidate route

### probe_route

Question: «What is a plausible traversable route from A to B?»

Return a compressed route, not thousands of micro-steps.

### probe_progression

Analyze known progression dependencies.

Possible output:
- initial reachable region
- locked objectives
- key/switch dependencies
- state transitions
- exit reachability
- potential sequence breaks

This should be based on verified semantic mechanisms only.
Unsupported mechanisms must remain visible as uncertainty.

### probe_transition

Compare two sides of a traversal transition.

Measure differences such as:
- visible spatial extent
- ceiling height
- opening width
- branch count
- material family
- shade/brightness
- vertical range

Example use:
«Does entering the church from the crypt create a strong spatial release?»

The deterministic system should return measurements.
The LLM may later interpret whether they create the intended experience.

### probe_visibility

Question: «Is target T visible from this route or from these approach
positions?»

Initially this may use conservative geometry-derived approximations plus
optional real-engine samples.

Useful targets:
- door
- landmark
- switch
- key
- exit

Return evidence such as:
- first observed at 31% of route
- visible from 4/8 sampled decision points
- lost from view after transition X

Do not invent binary certainty if visibility is approximate.

### probe_revisit

Compare the same area in different world/knowledge states.

Example:
- before key acquisition
- after key acquisition

Useful output:
- new paths
- changed mechanisms
- new visibility
- changed route choices
- known-vs-new landmarks

This is important for levels that deliberately reuse spaces after world-state
changes.

### probe_escape

Given a position/region and world state, determine available traversal
options.

Do not simulate combat.

Return things such as:
- number of viable exits
- blocked exits
- dead-end depth
- routes requiring passing through same bottleneck

This may later help an LLM reason about arenas and retreat options.

## Design Contract

A Design Contract connects user intent to hard assertions and soft evidence
questions.

### Hard assertions

Structural properties that must be true for the level to be valid.

Examples:
- player start exists
- blue key is reachable initially
- graveyard gate is not traversable initially
- graveyard gate becomes traversable after key
- exit is reachable after required progression
- no hard sequence break

### Soft evidence questions

Experiential properties that produce evidence through probes.

Examples:
- "crypt should feel spatially constrained"
  → transition probe
  → relative area
  → ceiling delta
  → visibility delta
  → route-choice delta
  → optional engine views
- "church should produce a strong increase in perceived scale"
- "locked graveyard route should be observable before key acquisition"
- "return through church should expose a meaningful world-state change"

Do not automatically claim soft goals are objectively testable.
Instead bind them to evidence-producing probes.

The LLM then judges whether the evidence satisfies the design intent.

## Counterfactual design probes

This is an important capability.

Allow an agent to evaluate candidate edits without committing them to the main
authored state.

Example:
Current:
    church entrance width = 3072
Candidate A:
    1536
Candidate B:
    4096

Run the same probe suite against each candidate.
Return comparable results:

```
           current    A       B
opening width     3072   1536    4096
view depth        ...    ...     ...
spatial change    ...    ...     ...
route choices     ...    ...     ...
```

The LLM can then choose a candidate based on the design goal.

This is implemented through deterministic snapshots/clones/temporary IR
variants, not destructive edits.

## Replayability

Every probe must be serializable.

The same probe must be runnable:
- before edit
- after edit
- Blood source
- Duke source
- converted candidate (where semantics allow)

This is critical for regression and comparative evaluation.

## Probe results must be concise

Do not return raw traversal logs unless explicitly requested for debugging.

The normal result should answer the question.

Example:
```
Probe: locked-gate-before-key
Result:
PASS
Gate becomes observable:
  29% through start → key route
Key acquired:
  78%
Gate visible from:
  3 subsequent decision locations
Conclusion data:
  player can plausibly form the gate objective before acquiring the key
```

The final interpretation may remain the LLM's responsibility.

## Agentic experimental workflow

Design the API around this loop:

1. Agent forms a hypothesis.
2. Agent makes or proposes a bounded edit.
3. Structural validation runs.
4. Relevant Design Probes run.
5. If useful, selected engine renders/runtime checks run.
6. Agent compares evidence against the Design Contract.
7. Agent accepts, rejects, or revises the edit.

The LLM is the decision-maker.
llmapper is the experiment environment.

## Important: do not make one giant "quality score"

Avoid:
```
level_quality = 0.83
```

This would hide too much and encourage fake precision.

Keep evaluation decomposed.

For example:
```
progression: valid
exit reachability: pass
gate-before-key visibility: supported
crypt→church spatial contrast:
    area ratio 4.1
    ceiling ratio 2.3
    view-depth ratio 3.4
visual coherence:
    not evaluated
combat quality:
    not evaluated
```

The LLM can reason over these dimensions.

## Use deterministic algorithms as tools

One strong idea from agentic PCG is that the LLM should orchestrate
algorithms rather than perform every low-level computation itself.

Continue this philosophy.

The future design agent should have a hierarchy of operations:

LOW LEVEL
- move vertex
- split wall
- change height
- move sprite

MID LEVEL
- extrude alcove
- create stairs
- connect areas

SEMANTIC
- create door
- create lift
- create destructible wall

ANALYTIC
- probe route
- probe transition
- probe visibility
- probe progression

The LLM decides what to do.
Deterministic code executes geometry and measurement correctly.

## Use real engines as expensive sensors

NBlood and EDuke32 remain important.

Do not run full engine automation for every cheap question.

But allow Design Probes to escalate when needed.

Example:
```
visibility probe
    ↓
geometry result uncertain
    ↓
sample 3 real engine viewpoints
    ↓
return images + structured pose metadata
```

Or:
```
mechanism probe
    ↓
semantic model predicts door opens
    ↓
NBlood runtime oracle verifies state transition
```

The probe report should record whether evidence came from:
- static exact
- static approximate
- semantic simulation
- real engine

## What the probe model does NOT simulate

The Design Probe system is intentionally not a replacement game engine.
It models only the aspects needed to answer bounded design questions cheaply
and deterministically.

### Not simulated: full player movement physics

The probe system does not simulate:
- Acceleration/deceleration
- Jump arcs and momentum
- Slope physics (walking up/down slopes)
- Swimming physics
- Crouch/uncrouch timing
- Player collision against walls (beyond portal blocking flags)
- Step-up/step-down mechanics for individual steps

What it does instead:
- Uses static graph traversal (BFS shortest path) over portal-connected
  sectors
- Checks portal width and at-rest vertical opening against fixed thresholds
- Identifies state-change candidates (blocked portals, mechanism groups)
  without simulating their runtime behavior

### Not simulated: combat, enemies, and weapons

The probe system does not model:
- Enemy AI, pathfinding, or aggro
- Weapon damage, range, or projectile physics
- Health/armor/resource management
- Cover mechanics
- Enemy placement impact on difficulty

What it does instead:
- Identifies enemy sprites in sectors (via the semantic observation layer)
- Reports mechanism groups that could affect combat (explosive walls,
  touchplates)
- Leaves combat quality as "not evaluated"

### Not simulated: full renderer visibility

The probe system does not:
- Cast rays through the Build engine renderer
- Model occlusion, view angle, or perspective
- Simulate lighting changes as the player moves
- Recognize landmarks from rendered views

What it does instead:
- Uses direct-portal adjacency as a conservative visibility approximation
- Reports "direct-portal-candidate" visibility only
- Marks all visibility evidence as "static_approximate" with "medium"
  confidence
- Escalates to real engine renders only when explicitly requested

### Not simulated: dynamic mechanism state over time

The probe system does not:
- Simulate doors opening/closing over time
- Model lift motion and timing
- Track switch state changes and their cascading effects
- Simulate touchplate triggers and their consequences
- Model conveyor belt motion
- Simulate explosive wall destruction sequences

What it does instead:
- Identifies mechanism groups (Blood TX/RX channels, Duke Sector Effector
  tags)
- Reports state-change candidates without simulating the changes
- Uses world_state overrides (opened_portals, activated_mechanisms) to model
  specific post-change states
- Records evidence source as "semantic_simulation" when mechanism semantics
  are used

### Not simulated: player intent and decision-making

The probe system does not:
- Model what the player wants to do
- Simulate player exploration strategies
- Track player emotional state
- Predict which route the player will choose at a branch

What it does instead:
- Reports all available routes and branches
- Measures spatial properties (area, height, width) that may influence player
  perception
- Leaves interpretation of whether evidence satisfies design intent to the LLM

### Not simulated: multiplayer and networking

The probe system does not model:
- Network play mechanics
- Player-player interactions
- Spawn point balancing for deathmatch

### Not simulated: save/load state

The probe system does not:
- Track save/load boundaries
- Model checkpoint placement
- Simulate the effect of save scumming on difficulty

## Research before abstraction

The AI implementing this system does not inherently know Blood or Duke3D.

Therefore do not invent traversal rules, mechanism semantics, or player
dimensions from intuition.

Use:
- engine source
- original map corpus
- runtime experiments

as evidence.

If a probe depends on uncertain semantics, fail closed or report uncertainty.
Do not hide unsupported mechanisms.

## Tests

Add focused tests for probe semantics.

At minimum create synthetic fixtures for:
- simple reachable path
- locked path
- key unlock
- vertical clearance failure
- lift-enabled path
- teleporter/water transition
- state-dependent revisit
- branching/escape options

Also run useful probes against existing real Blood and Duke maps.

Do not hardcode conclusions about specific maps into general algorithms.

## First empirical experiment

After implementing the foundation, test whether Design Probes actually help a
general LLM make a better design decision.

Use a small controlled authored Blood level or the existing scratch puzzle
room.

Create an intentionally weak design variation, for example:
- poorly visible objective
- weak crypt→hall spatial contrast
- unnecessarily wide connector
- confusing progression branch

Give the agent:
- design intent
- normal llmapper tools

and compare against:
- design intent
- normal tools
- Design Probes

Record whether the agent:
- identified the intended problem
- made a relevant edit
- improved the probe evidence
- preserved structural/gameplay correctness

Do not overclaim from one experiment.

The purpose is to determine whether this direction provides useful leverage.

## Immediate deliverables

By the end of this iteration:

- Add explicit lightweight "PlayerState", "WorldState", and "PlayerKnowledge"
  concepts where needed.
- Implement a replayable Design Probe schema.
- Implement at least:
    - access
    - route
    - progression
    - transition
    - basic visibility
    - revisit or escape
- Keep probe execution bounded and deterministic.
- Add source/evidence classification to results.
- Support counterfactual candidate evaluation on temporary IR copies.
- Add Design Contract representation connecting user intent to hard assertions
  and soft evidence questions.
- Add focused synthetic tests.
- Demonstrate probes on at least one existing real level and one
  authored/synthetic fixture.
- Document exactly what the probe model does not simulate.
- Preserve all current Blood/Duke roundtrip, conversion, composition, and
  oracle guarantees.
- Avoid introducing an LLM dependency into the deterministic core.

## Guiding principle

The important experiment is not:
«"Can an LLM generate a Blood level?"»

It is:
«"Can a general LLM make meaningfully better level-design decisions when it
can actively test hypotheses about traversal, progression, perception, and
world-state changes instead of reasoning from static MAP data alone?"»

Build the smallest rigorous system that can answer that question.

If the answer is yes, expand from there.
