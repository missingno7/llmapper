# Material evidence and discovered annotation

Texture understanding in `llmapper` is evidence-first. The package does **not**
start from a hand-written taxonomy such as `metal|stone|wood` or
`wall|floor|door` and then tag tiles into it.

```text
ASSET APPEARANCE
+ REAL CORPUS USAGE
+ ENGINE/RENDERING PROPERTIES
+ RELATIONSHIPS
+ REPRESENTATIVE IN-GAME CONTEXT
        ↓
unlabeled clusters and relations
        ↓
offline multimodal review proposes facets
        ↓
imported INTERPRETED annotations, with contradiction checks
```

The deterministic package stays usable without an LLM. Semantic labels are
never native facts.

Supporting this layer does **not** make `BuildIR` a universal material IR.
Blood and Duke share Build ART tiles; Doom contributes named textures as a
separate native identity. Cross-game matching compares usage signatures and
appearance features, not numeric IDs.

## Provenance

Every claim is one of:

- `VERIFIED` — native identity, ART pixels/picanm, measured map usage
- `DERIVED` — clusters, co-occurrence, palettes, contradiction reports
- `INTERPRETED` — imported facet names and per-asset labels

Imported annotations cannot be marked `VERIFIED`. Unknown, ambiguous, and
mixed-use are valid terminal statuses.

## Commands

Original Blood campaign maps can be selected with `--glob E*.MAP` so Duke
conversions (`DWE*`, `DNE*`) and Doom recreations (`TEDE*`) do not enter the
usage statistics. Those derived maps are useful as conversion evidence, not as
Blood-native material authoring.

```text
python -m bloodmap materials-mine --game blood --maps maps/blood --glob E*.MAP \
  --art reference/blood --output work/blood.materials.json

python -m bloodmap materials-mine --game duke3d --maps maps/duke3d \
  --art reference/duke3d --palette reference/blood/xmapedit/palettes/import/DUKE3D.PAL \
  --output work/duke.materials.json

python -m bloodmap materials-mine --wad maps/doom/doom.wad \
  --output work/doom.materials.json

python -m bloodmap materials-export-batch work/blood.materials.json \
  --art reference/blood --limit 80 -o work/blood.material-batch.json

python -m bloodmap materials-import work/blood.materials.json \
  knowledge/blood/ontology-v1.json -o work/blood.material-knowledge-v1.json

python -m bloodmap materials-import work/blood.material-knowledge-v1.json \
  knowledge/blood/ontology-v2.json -o work/blood.material-knowledge-v2.json

python -m bloodmap materials-audit work/blood.material-knowledge-v2.json \
  --art reference/blood -o work/blood.materials.html

python -m bloodmap materials-query work/blood.material-knowledge-v2.json \
  --require "{\"architectural_role\":\"masked_separator\"}"

python -m bloodmap materials-kit work/blood.material-knowledge-v2.json \
  --roles "{\"floor\":{\"surface_applicability\":\"horizontal_floor\"}}"

python -m bloodmap materials-packet work/blood.materials.json \
  --maps maps/blood --art reference/blood -o work/material-review-packets
```

The classification batch asks a reviewer to propose **facets** from the sample,
not to force each tile into one class. Parameters may name a facet or a
threshold. They must not supply truth values such as `is_floor=true`.

## What is measured before any label

For each Blood/Duke ART tile, when ART is present:

- native id, width, height
- transparent / masked pixel counts (index 255)
- `picanm` animation type, frame count, offsets, speed
- a deterministic appearance feature used only as a similarity cue

For each original-map placement:

- wall / floor / ceiling / overwall / sprite / decal counts
- masked, translucent, one-sided vs two-sided
- mechanism-associated and moving-sector vs static
- world-space wall width, sector height, xrepeat/yrepeat, shade, pal
- neighboring assets and floor/ceiling pairings

Distributions keep exact counts when the cardinality is small, otherwise
quantiles. Representatives are a compact stratified sample (typical, rare,
masked, mechanism, other maps), not every occurrence.

Doom mining records named textures (`STARTAN2`, `F_SKY1`, …) the same way.
Patch/PLAYPAL appearance decoding is intentionally out of this first pass.

## Local evidence snapshot

These numbers come from a local original-map run. They are not checked in.
Regenerate with `--glob E*.MAP` (Blood) / `E*.MAP` (Duke) and the Doom IWAD.

| Corpus | Maps | Assets | Substantial usage | Appearance | Animation families | Clusters |
| --- | --- | --- | --- | --- | --- | --- |
| Blood `E*.MAP` + ART | 43 | 4418 tiles | 895 | 4417 | 113 | 160 |
| Duke `E*.MAP` + ART | 41 | 3253 tiles | 1191 | 2774 | 63 | 141 |
| Doom IWAD names | 36 | 345 textures | 330 | 0 | 0 | 1 |

Blood now has a reviewed ontology under `knowledge/blood/`: v1 from an
appearance-heavy pass, then v2 after contradiction-driven refinement. The
package still ships with an empty ontology until that JSON is imported. See
[materials-discovery.md](materials-discovery.md).

Isolated appearance remains misleading: tile 2500 looks like a vertical stone
strip but is ceiling-only across 17 maps; tile 330 is a masked fence used only
as `overpicnum`; tile 2521 is a sprite-only sound marker; tile 0 looks like
masonry and is the default/empty picnum; tile 270 is a noisy brown bitmap that
is predominantly a floor. Unused ART is `appearance_only` and must not be
described as “normally a wall.”

Facets that survived refinement are orthogonal: placement kind, surface
applicability, rendering behavior, architectural role, interaction role, scale
behavior, and a low-value visual material name. A single class such as "stone"
or "door" did not survive.

## Clusters before names

Candidate groups are unlabeled:

- visual — ART feature distance
- usage — cosine of placement-kind vectors
- native_animation — consecutive ART `picanm` frames (`VERIFIED`)

Numeric tile adjacency is not a cluster kind. Animation membership is native
metadata, not a visual guess.

Relations currently reported from evidence:

- `observed_adjacent`
- `observed_with_floor`
- `observed_with_ceiling`
- `native_animation_frame`

Those names describe measured co-occurrence. They are not an architectural
ontology. Local palettes are per-sector surface sets, not canonical rooms.

## Ontology import

A reviewed JSON document may add facets, for example whatever distinctions the
sample actually supports. Each facet stores `id`, allowed values, basis, and
`useful_for`. Per-asset values keep confidence, basis, supporting examples,
and contradicting evidence.

The importer then searches for contradictions such as:

- a floor-like label on an asset that never appears on floors
- an opaque label on an asset whose placements are mostly masked
- a visual cluster whose members have dissimilar usage

Those reports go back to the reviewer. Blood v1 over-trusted isolated
previews; v2 is the refined schema. Provenance of the revision is kept in
`ontology_history`. Imported labels cannot be `VERIFIED`.

## Retrieval and conversion

`materials-query` ranks candidates by usage signature first, then appearance.
`--require` keys must be facets that were actually imported. Unused assets are
excluded from usage queries. `materials-kit` picks corpus-backed tiles for
named authoring roles using those same facets.

This catalog is optional for Duke/Doom → Blood conversion. Existing role-aware
ART matching remains the default so conversion tests stay independent of local
knowledge artifacts. A separable ontology-aware probe is documented in
[materials-discovery.md](materials-discovery.md); it does not replace
`e3l11._apply_materials`.

Doom mining still records named textures only. Patch/PLAYPAL composed-texture
appearance decoding is out of scope until the Blood workflow is the thing being
generalized.

`material-scale` can re-express a catalog asset's measured world coverage in
player widths and heights. That is presentation, not a new texture taxonomy.
See [player-space.md](player-space.md).

## Tests

`tests/test_materials.py` covers identity, usage mining, representative
sampling, cluster determinism, ontology versioning, import rejection of
self-certified truth, contradiction detection, unused `appearance_only`
status, authoring-kit retrieval, and usage-first cross-game ranking. It uses
synthetic ART and maps, plus a schema check of `knowledge/blood/ontology-v2.json`.
Optional corpus mining skips cleanly when original maps are absent.
