# Independent Critics, Validation and Scoped Repair

## Do not use one global critic score

Bad:

```text
level_quality = 0.73
```

A scalar hides the failure.

Use independent critics. Several already exist and feed
`bloodmap/authoring_loop.py`: geometry (`analysis.validate_map`,
`geometry_audit.py`, the overlap validator), corpus comparison
(`level_profile.py` — explicitly a vector of independent measurements,
never one number), runtime (`oracle.py`, NBlood: loads, spawns, moves),
and rendered views (`visual.py` + XMapEdit observer).

Standing warning from project history: critic rules have repeatedly
measured the wrong thing (e.g. validators passing a map that segfaulted;
72 stairs to nowhere passing every gate). Every new critic must name its
independent oracle and demonstrate at least one failure it provably
detects.

Recommended critics:

- geometry,
- mechanism,
- topology/progression,
- functional,
- gameplay,
- architecture,
- visual,
- readability,
- corpus/style.

## Critic output

Prefer structured diagnoses.

Example:

```yaml
issue: FACADE_CONTINUITY

scope:
  assembly: building_3/facade_1/bay_4

status: fail

observed:
  storefront_plane_equals_facade_plane: true
  reveal_present: false
  header_datum_offset: 512

expected:
  opening_subordinate_to_facade: true

repair_scope: assembly
```

## Scoped repair

Default to the smallest possible repair scope.

Suggested hierarchy:

```text
LOCAL
  one primitive / one tiny detail

ASSEMBLY
  one shelf / door / facade bay / mechanism

SPACE
  one room or functional region

REGION
  several spaces

PROGRESSION
  connectivity and gating may change

GLOBAL
  entire level may change
```

A visual facade issue should not automatically trigger a topology rewrite.

## Progressive commitment

Avoid:

```text
generate whole level
-> critique whole level
-> regenerate whole level
```

Prefer staged synthesis:

```text
1. design intent
2. structural spaces/relations
3. topology validation
4. architecture
5. architecture validation
6. mechanisms
7. dynamic/progression validation
8. content/furniture
9. functional validation
10. surfaces/lighting/decoration
11. rendered visual critique
12. play/gameplay critique
13. scoped repairs
```

Later stages should have less freedom to rewrite earlier high-level decisions
unless an earlier hard constraint is proven wrong.

## Independent evidence

Critics should use different oracles where possible.

Examples:

### Geometry critic
Source:
- parsed MAP.

### Mechanism critic
Source:
- XSECTOR/XWALL/XSPRITE,
- `Assembly`,
- engine-state observations.

### Topology critic
Source:
- derived traversability,
- conditional topology,
- optional bot/play simulation.

### Visual critic
Source:
- rendered player views.

### Corpus critic
Source:
- original/curated population statistics and pattern precedents.

### Gameplay critic
Source:
- topology, encounter placement, play traces.

Do not let the proposal model simply review its own prose.

## Specialized questions

Useful targeted visual/semantic critics:

- Does this read as shelving rather than stacked crates?
- Which side of this cabinet is the front?
- Do these openings belong to one facade?
- Does this passage read as designed or merely cut through?
- Which object blocks intended circulation?
- Does the storefront detach visually from the building?
- Does the room have functional organization?
- Is the asymmetry authored or accidental?

## Semantic delta

After a repair, compare high-level meaning before and after.

A local visual fix should ideally preserve:

- topology,
- progression,
- functional region identity,
- mechanism semantics.

This prevents "fix one thing, accidentally redesign the level".
