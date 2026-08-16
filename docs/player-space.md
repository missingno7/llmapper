# Player-relative spatial presentation

Exact native geometry stays available. This layer does **not** replace engine
coordinates, invent a canonical room model, or encode a taxonomy of corridors,
halls, and indoor/outdoor types.

It adds a derived presentation so a future LLM can reason about space in terms
of the player's body, movement affordances, original-map distributions, and
relative change between neighboring spaces.

```text
RAW native units
    + player collision / movement profile
    + original-map distributions
    + neighbor relationships
        ↓
NORMALIZED player-relative quantities
CORPUS-RELATIVE percentiles
RELATIONAL ratios
optional INTERPRETED heuristics
```

Meters are optional intuition only. They are never the primary abstraction.
`BuildIR` remains a Build-engine contract; Doom uses this layer through
`DoomDiskMap`, not by entering `BuildIR`.

## Player profiles

`PlayerSpatialProfile` is evidence-backed per game:

| Game | Body width | Standing height | Step | Jump | Crouch |
| --- | ---: | ---: | ---: | --- | --- |
| Blood | 384 (`clipdist<<2`) | 0x1600 | 4096 at-rest | yes | yes (0x800) |
| Duke3D | 328 (`clipdist` 164) | 38<<8 | 20<<8 autostep | yes | yes, no named crouch clip height |
| Doom | 32 (radius 16) | 56 | 24 | no | no |

Collision dimensions, movement affordances, and camera/view height are stored
separately. Doom's eye height is 41, not 56.

```text
python -m bloodmap player-profile --game blood
python -m bloodmap player-scale-report
```

`player-scale-report` compares existing conversion XY/Z scales with player-body
ratios. It does **not** replace the measured 3:2 Duke→Blood or ×16 Doom→Blood
geometry scales.

## Commands

Default output is a compact LLM-facing view. `--full` restores layered
raw / player-relative / corpus-relative evidence. `--question` returns only the
requested facet.

```text
python -m bloodmap inspect-space maps/blood/E1M1.MAP --sectors 12 \
  --corpus work/blood.spatial-corpus.json
python -m bloodmap inspect-space maps/blood/E1M1.MAP --sectors 12 --full
python -m bloodmap inspect-space maps/blood/E1M1.MAP --sectors 12 --question enclosure
python -m bloodmap inspect-connection maps/blood/E1M1.MAP --wall 44 \
  --corpus work/blood.spatial-corpus.json
python -m bloodmap compare-space maps/blood/E1M1.MAP --from 12 --to 18
python -m bloodmap spatial-corpus --maps maps/blood --glob E*.MAP \
  -o work/blood.spatial-corpus.json
python -m bloodmap spatial-corpus --wad maps/doom/doom.wad \
  -o work/doom.spatial-corpus.json
python -m bloodmap material-scale work/blood.materials.json --asset blood:tile:180
```

## Provenance layers

Important measurements keep every layer inspectable:

- `raw` — native Build or Doom units
- `player_widths` / `player_heights` / `player_areas`
- `corpus_percentile` — against that game's original-map samples
- `relative_to_neighbor` — when comparing a transition
- `interpretation` — optional heuristic, never a verified fact

Physical traversal is separate from comfort:

- `can_fit`, `can_walk_through`, `can_step_up`, `requires_jump`,
  `requires_crouch`, `cannot_traverse` are deterministic against the player
  profile
- "unusually narrow" is a percentile heuristic, not a universal threshold

The existing `analyze-space` at-rest thresholds (width 512, opening 4096) are
unchanged. They remain a coarser static sensor.

## Enclosure

Enclosure is faceted, not a binary indoor/outdoor flag:

- `sky_exposure` — parallax/sky fraction of the selection
- `lateral_enclosure` — 1 − boundary opening width / outer perimeter
- `vertical_enclosure` — reduced by sky and by very tall volumes
- `openness` — complement of mean lateral/vertical enclosure

If a later LLM reads a profile as courtyard-like or crypt-like, that reading
is interpretation. The package does not assign those labels.

## Clusters

`spatial-corpus` may emit unlabeled elongation/area bins. A heuristic such as
"elongated small space" is attached only when the bin supports it. Those are
not canonical map structures.

## Material world scale

`material-scale` uses measured wall coverage and, when ART appearance is
present, tile pixel size. Build x-repeat 8 is 1:1. Coverage is then expressed
in player widths/heights so a door tile that is usually one instance per
opening can be distinguished from a surface that is tiled many times.

## Corpus notes

All non-blocking portal widths are mined. `traversable_opening_width_player_widths`
keeps only openings the player can physically fit. Percentiles for openings prefer
that traversable population when it is present, so sliver geometry does not define
"narrow."

Maps the spatial sensor cannot analyze (invalid wall ownership) are recorded in
`skipped` and omitted from the distributions. Lossless parsing of those maps is
unchanged.

## Boundaries

This layer does not:

- simulate combat or perception
- detect rooms
- score design quality
- replace native geometry or conversion scales
- require an LLM client
