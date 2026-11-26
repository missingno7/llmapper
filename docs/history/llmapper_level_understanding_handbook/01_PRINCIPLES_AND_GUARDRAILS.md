# Principles and Guardrails

## 1. Original maps are the source of truth

Generated maps, reconstructions and AI-authored examples may be evaluated against
knowledge, but they must never become evidence for that knowledge.

Keep source populations separate (authoritative layout and registry in
`07_...md`):

- `blood-campaign` — original Monolith maps (`campaign/E*M*.MAP`),
- `blood-bloodbath` — original BloodBath (`campaign/multiplayer/BB1-9`),
- `community-curated` — the owner's hand-picked community sources
  (`curated/`: `DWE*` Death Wish, `TEDE*`, `SS*`;
  `curated/multiplayer/`: `DWBB*`, `DM*`): vetted precedent, not campaign
  convention,
- `own-conversion` — the owner's manual Duke3D→Blood conversions (`DNE*`):
  cross-game evidence only, never Blood design convention,
- `community` — bulk maps (the heuristic tier S/A/B/C/questionable is
  metadata, not evidence weight),
- `generated` — never evidence.

Provenance is fail-closed and comes from the directory a map lives in;
filename prefixes are only a sanity cross-check. (Older filename tables that
labeled `DWE`/`TEDE` as conversions are wrong — owner correction 2026-08-31.)

A curated community corpus is useful for widening the design vocabulary, but it
must not silently redefine "what the original campaign normally does".

Use language such as:

- **original campaign convention**
- **community precedent**
- **project hypothesis**
- **authoring preference**

instead of collapsing all evidence into one pool.

## 2. Observation and interpretation must remain separate

Bad:

```text
sector type 600 = elevator
```

Good:

```text
OBSERVATION
  one sector has two Z configurations
  floor travels 16384 Build units
  the sector is occupiable
  lower state aligns to region A
  upper state aligns to region B

INTERPRETATION
  likely elevator
```

The same rule applies to static structures:

```text
OBSERVATION
  four shallow aligned sectors
  repeated vertical spacing
  wooden faces
  free space in front

INTERPRETATION
  likely drawer unit
```

## 3. Learn relations, not lookup tables

Tile identity is often episode-specific. Coordinates are map-specific.

Portable knowledge usually lives in:

- relative geometry,
- adjacency,
- alignment,
- repetition,
- containment,
- orientation,
- accessibility,
- topology,
- causal relations,
- style inheritance,
- visual rhythm.

Prefer:

```text
opening is recessed from facade plane
```

over:

```text
use tile 1234 at X=8192
```

## 4. Sparse human labels are semantic probes

Manual hints such as:

- "this tile is a drawer front",
- "these are carpet tiles",
- "this material is wood",
- "these maps contain sewers",

are not final classifications.

Treat each as a probe:

1. find all occurrences,
2. inspect their neighborhoods at several scales,
3. find common relations,
4. form a structural hypothesis,
5. search for similar structures without the original anchor,
6. inspect counterexamples,
7. only then consider semantic promotion.

## 5. Structure may be known before its name

It is acceptable and desirable to store:

```text
candidate:structure:0187
```

before deciding whether it is a cabinet, shelf, drawer unit or something else.

Do not force every cluster into a human noun.

## 6. Counterexamples are first-class evidence

Every hypothesis should preserve:

- supporting occurrences,
- counterexamples,
- ambiguous cases,
- known variants,
- confidence,
- rejected interpretations.

A rule without counterexamples is probably an anecdote.

## 7. Do not turn corpus medians into laws

A campaign median is not a target.

Distinguish:

- hard engine constraints,
- strong campaign conventions,
- soft tendencies,
- free design choices.

Do not optimize every level toward corpus medians. That produces "Blood soup":
statistically plausible, authorially bland.

## 8. Prefer the smallest useful abstraction

Do not build:

```text
UniversalDynamicSemanticSceneGraphFramework
```

before several concrete cases demand it.

Promote an abstraction only when:

- the same need recurs,
- the invariant is understood,
- counterexamples are known,
- the abstraction makes future work cheaper,
- tests can distinguish correct from incorrect behavior.

## 9. Diagnose before repair

When something is wrong, classify the failure before changing coordinates.

Possible failure classes:

- semantic misclassification,
- wrong grouping,
- wrong parent assembly,
- wrong facing/orientation,
- missing negative space,
- bad hard constraint,
- bad geometry compile,
- broken mechanism,
- wrong topology,
- style inheritance failure,
- visual readability failure,
- gameplay failure,
- over-regularization,
- random clutter,
- unsupported inferred rule.

## 10. Prefer independent oracles

A claim is valuable when another view can falsify it.

Examples:

- geometry from parsed MAP,
- mechanism facts from Blood fields/engine behavior,
- traversability from derived spatial checks or play simulation,
- visual readability from rendered player views,
- style claims from corpus comparison.

Do not let one LLM output become both proposal and proof.
