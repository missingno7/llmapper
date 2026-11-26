# Experience Atlas and level projects

The Experience Atlas is a derived, bounded Level-0 sensor for how a player may
move through a map. It is not a second Blood/Duke engine and it does not claim to
measure atmosphere, combat quality, or renderer-accurate visibility.

## Replayable probes

Each probe works from `BuildIR`, the multi-view spatial analysis, and a declared
world state. It returns concise JSON with its model and limitations.

```text
python -m bloodmap probe-route maps/blood/campaign/E1M1.MAP \
  --from-sector 22 --to-sector 0 -o work/route.json
python -m bloodmap probe-transition maps/blood/campaign/E1M1.MAP \
  --from-sector 22 --to-sector 59
python -m bloodmap probe-visibility maps/blood/campaign/E1M1.MAP \
  --from-sector 22 --target-sector 0
python -m bloodmap probe-progression maps/blood/campaign/E1M1.MAP
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
