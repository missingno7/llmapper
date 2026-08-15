# Experience Atlas and level projects

The Experience Atlas is a derived, bounded Level-0 sensor for how a player may
move through a map. It is not a second Blood/Duke engine and it does not claim to
measure atmosphere, combat quality, or renderer-accurate visibility.

## Replayable probes

Each probe works from `BuildIR`, the multi-view spatial analysis, and a declared
world state. It returns concise JSON with its model and limitations.

```text
python -m bloodmap probe-route maps/blood/E1M1.MAP \
  --from-sector 22 --to-sector 0 -o work/route.json
python -m bloodmap probe-transition maps/blood/E1M1.MAP \
  --from-sector 22 --to-sector 59
python -m bloodmap probe-visibility maps/blood/E1M1.MAP \
  --from-sector 22 --target-sector 0
python -m bloodmap probe-progression maps/blood/E1M1.MAP
```

Level 0 currently supports deterministic shortest routes, static reachability,
source-backed water/teleport transitions, explicit portal-open overrides, and
direct-portal visibility candidates. It reports area, clearance, route-choice,
and material evidence at sampled `ExperienceNode`s. A transition may emit a
`spatial_expansion_candidate`, but that is a heuristic for a designer or LLM to
investigate—not a claim of a dramatic reveal.

## World state and player knowledge

The probe input keeps these separate:

- `world_state`: currently caller-declared `opened_portals` and
  `activated_mechanisms` assumptions;
- `player_knowledge`: `seen_sectors`, explicitly known landmarks, and explicitly
  known locked routes.

A route updates only `seen_sectors`. It lists nearby state-change candidates as
potential evidence rather than silently deciding that the player noticed or
understood them. Runtime behavior, key ownership, switch order, moving geometry,
slopes, and true visual perception remain outside Level 0.

## Persistent level project

Create a non-destructive design workspace:

```text
python -m bloodmap project-init projects/crypt --name "Monastery crypt" \
  --brief-file design-brief.md
python -m bloodmap project-evidence projects/crypt --concept rotating_bridge \
  --status verified --claim "Source/runtime evidence supports this form" \
  --evidence "[\"sprite:12\", \"docs/source-note\"]"
python -m bloodmap project-decision projects/crypt \
  --intent "Make the gate memorable" \
  --decision "Keep it visible from the church entrance" \
  --expected "The player forms a long-term objective"
python -m bloodmap project-slice projects/crypt maps/blood/E1M1.MAP \
  --sectors 22,59,120 --id precedent:approach
```

The resulting project separates:

```text
design/brief.md          user and agent intent
design/plan.md           revisable plan
design/decisions.jsonl   intent -> decision -> expected result
level/                   replayable recipe and generated MAP artifact
reports/                 validation, probes, visual/runtime reports
memory/evidence-ledger.json  append-only semantic claims and uncertainty
memory/design-memory.json    contextual LevelSlice precedents
memory/episodes.jsonl        observed outcome and correction history
```

`LevelSlice` records source identity, a selected sector set, fingerprint,
spatial context, and relevant static progression evidence. It is a contextual
precedent, not a prefab room.

## Evidence states

The evidence ledger accepts `verified`, `heuristic`, `disputed`, `superseded`,
and `rejected`. It appends records rather than overwriting old claims, so later
engine/corpus/runtime research can correct a concept while preserving why it was
previously believed.

## Next fidelity levels

Level 1 should add source-verified player clearance, slopes, doors, lifts, and
stateful interactions. Level 2 should selectively add NBlood/EDuke32 render
samples and bounded visibility routes. Level 3 can report approximate threat,
cover, escape, and resource observations. Each promotion needs engine-source,
corpus, and runtime evidence.
