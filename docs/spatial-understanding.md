# Spatial Understanding

`llmapper` derives several independent views over `BuildIR`. These are sensors
for a future LLM client, not serialized map state and not a canonical `Room`
model. A sector can appear in multiple derived selections, and no view assigns
every sector to exactly one region.

## Multi-view analysis

`python -m bloodmap analyze-space MAP` emits `bloodmap.spatial-analysis` with:

- `geometry`: raw sector/portal adjacency, portal walls, flat-surface opening,
  and multi-loop geometry counts;
- `traversability`: a deliberately limited at-rest check using portal width,
  vertical opening, and wall blocking flags;
- `visibility`: direct-portal candidates only, not renderer-verified sightlines;
- `vertical`: flat floor/ceiling Z intervals where sector XY bounds overlap;
- `mechanism`: Blood TX/RX memberships or source-backed Duke Sector Effector
  tag groups;
- `progression`: static reachability from the start plus possible world-state
  changes; it does not claim to solve keys or mechanism state;
- `material`: raw tile-ID/shade continuity, without inventing material families.

The output labels every approximation in its `model`, `basis`, and provenance.
The renderer, locked states, slopes, occlusion, and long-term player knowledge
remain future sensors or interpretations. Source-backed paired water, stack/link,
and teleporter links are listed as non-portal transitions when recognized, but their
runtime activation conditions are not simulated.

## Region hypotheses

`hypotheses` are overlapping selections, not rooms. The current conservative
vocabulary is:

- `perceptual_space`: direct portal continuity, limited floor-height continuity,
  and bounded shade difference;
- `navigation_region`: an at-rest connected component under the traversal model;
- `material_region`: portal-connected sectors with raw-tile/shade continuity;
- `mechanism_region`: native behavior membership, which may be spatially
  discontinuous;
- `vertical_layer`: an XY-overlapping above/below pair.

Each record names its source sectors and evidence and states that it is a derived
hypothesis. The system deliberately permits a hall, balcony, switch network, and
material run to overlap in different ways.

## Contextual selection observation

Blood `observe --sectors` now adds `spatial_context`. It exposes external portal
connectors, adjacent-sector area/height/floor contrast, touching vertical
relationships, mechanism relationships, and every overlapping hypothesis touching
the selection. A large area ratio is evidence; calling it a dramatic reveal is
still a heuristic decision for an LLM or designer.

## Design memory index

The existing index can retain several granularities:

```text
python -m bloodmap design-index maps/blood --include-spatial -o work/blood.spatial-index.json
python -m bloodmap design-search work/blood.spatial-index.json \
  --region-kind mechanism_region --limit 10
```

An `--include-spatial` index contains whole-level fingerprints, per-sector
structural records, overlapping candidate selections, and mechanism memberships.
Similarity remains a whole-level aid today; region results are source-grounded
precedents that a future LLM can inspect and rank by a chosen intent.

## Boundaries

No output proves a perceived room, combat arena, landmark, gameplay quality, or
player intent. These views are intentionally additive: a malformed accepted
original map leaves ordinary lossless parsing available while the derived sensor
reports that its wall ownership cannot safely support a spatial analysis.

## Player-relative presentation

`analyze-space` still speaks native units. `inspect-space`, `inspect-connection`,
and `compare-space` add a compact player-relative and corpus-relative view for
an LLM client without replacing those native measurements. See
[player-space.md](player-space.md).
