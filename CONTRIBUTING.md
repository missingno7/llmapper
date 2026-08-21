# Contributing

## Development setup

Use Python 3.10 or newer. The package has no runtime dependencies.

```text
python -m unittest discover -s tests -v
python -m bloodmap --help
```

Original Blood and Duke3D maps are not distributed. See `maps/README.md` and
`docs/corpus.md` for optional local corpus setup.

Game-neutral editing APIs must operate on `BuildIR`. Blood-specific authoring APIs
operate on `LevelIR` or a documented derivative such as `LevelFragment`.
`DiskMap` and `DukeDiskMap` are lossless import/export representations, not
authoring APIs. New LLM-facing observations must use stable semantic references
and label unknown numeric semantics instead of inventing names.

## Change gates

Changes to binary parsing, packing, models, or conversion logic must include:

1. evidence from XMAPEDIT, NBlood, EDuke32, or an isolated reproducible fixture;
2. a focused unit or mutation test;
3. a full available-corpus direct and IR roundtrip run;
4. a validator run with every new warning investigated;
5. a short update to `docs/format.md` or `docs/duke3d.md` for non-obvious format knowledge.

Changes to fragment composition, map writing, or structural limits should also run
the optional baseline/candidate NBlood load smoke when local game data is available:

```text
python -m bloodmap oracle-nblood work/candidate.MAP \
  --baseline maps/blood/E1M2.MAP \
  --nblood reference/blood/nblood.exe \
  --game-dir reference/blood \
  -o work/oracle.json
```

This gate proves that both files reach NBlood's initialized game loop and remain
healthy for the configured grace period. It does not by itself prove gameplay
equivalence.

Changes to `bloodmap.levelprog`, `bloodmap.vocabulary`, or the emitters that
produce level programs must hold three properties, each of which has a test:

1. **locality** -- `room.summary()` answers everything about that room, and
   changing one room changes only that room in the compiled MAP;
2. **exact frames** -- a parent's frame moves its children without altering a
   single number in any child's local outline;
3. **traceable inheritance** -- every resolved style value names the node that
   set it, and a value with no answer anywhere is refused by field name.

A new constructor in the authoring vocabulary needs cross-map evidence in
`projects/e2m3-decompiled/references/abstraction-candidates.json`: occurrence
counts across the corpus, a fit/held-out split by episode, and the residual it
deliberately does not reproduce. A justified rejection is a valid outcome and
belongs in `CORPUS_SUPPORT` with its reason. Historical jitter never becomes a
parameter, and expressiveness is added by composition rather than by another
argument.

Geometry the model cannot express goes to `Room.raw` with a note, or to
`NATIVE_ESCAPES` when decompiling. Do not repair an original's geometry to make
it compile: 0.95% of campaign sectors have outlines the authoring compiler
refuses, and silently fixing them would invent evidence about what was drawn.

Changes to `bloodmap.visual`, `bloodmap.viewplan`, or the XMapEdit observer must
hold the role split:

1. **the renderer is asked only what it alone knows** -- which native objects it
   painted, where on screen, and how much survived occlusion. Distance, size,
   naming and player-relative measurement stay in llmapper, where they already
   exist and can be checked against the map file;
2. **JSON is the product** -- a frame is an optional artefact for one named view,
   never the evidence itself, and never produced for every candidate pose;
3. **no key, no window, no timing** -- a camera pose is a number in a request.
   Adding an input-injection path back into the observation route is the thing
   this replaced;
4. **a pose is refused, never nudged** -- the planner drops what geometry rules
   out and the observer reports `invalid_pose` with its reason, because a
   silently moved camera answers a question nobody asked;
5. **no score** -- keep the evidence decomposed. `visual_quality = 0.81` is
   exactly the shape this must not take.

Evidence packets stay byte-deterministic, so wall-clock timings belong in tool
output rather than in an `AuthoringIteration`.

NBlood keeps the questions only a running game answers: does the MAP initialise,
does the mechanism fire, is it playable. It is no longer the way to look at a
room. See [structured visual observation](docs/visual-observation.md).

Duke writer and cross-game geometry changes should run the corresponding EDuke32
baseline/candidate smoke. Cross-game changes must also update or reproduce the
fidelity report and must never equate native tags solely because their numbers
match.

Room-attachment changes must additionally cover automatic rotation, repeated room
copies, channel remapping, blocked-wall policy, and slope-aware endpoint clearance.
When the original-map corpus is present, reproduce the attachment fixture in
`docs/reference-oracles.md` and run its NBlood load smoke.

Changes to fragment allocation, channel remapping, or extended-record ownership
should also run the Windows behavior oracle when local NBlood game data is
available. It briefly foregrounds the NBlood window to send raw keyboard input:

```text
python -m bloodmap oracle-nblood-behavior \
  --nblood reference/blood/nblood.exe \
  --game-dir reference/blood \
  -o work/behavior-oracle.json
```

This gate covers the synthetic wall-trigger/channel/Z-motion scenario documented
in `docs/reference-oracles.md`; it is not evidence for untested gameplay systems.

Do not normalize values in lossless paths, rely on compiler bitfield layout, retain
the complete input blob, or silently discard references.

Changes to the reasoned authoring loop must keep three properties. Authored
labels stay out of every observation section of the iteration packet; a skipped
evaluator is never reported as a pass; and every evidence reference a packet or a
review emits must resolve inside that packet. New hierarchy, scale, or shape
rules must state the rule that produced each finding, and must be cross-checked
against a rendered frame before being trusted -- three rules in the first pilot
counted sectors where they should have weighed floor area, and each was caught
that way. Corpus-relative measures report percentiles against a named mined
corpus and never against universal constants.

## Commit hygiene

- Keep proprietary maps and original-map SVG renderings out of commits.
- Keep generated scratch output under ignored `work/`.
- Make commits focused and describe the verified behavior they add.
- Do not mix semantic guesses into binary-format changes.

## Adding operations

An editing operation must document its preconditions, exact fields touched,
reference-remapping behavior, expected diagnostics, and reparse/validation checks.
Unknown fields remain unchanged unless their meaning has been verified.
