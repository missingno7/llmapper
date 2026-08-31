# Blood corpus health (Phase 0a)

Native parse/losslessness gate over the reorganized local corpus, run
fail-closed: a map that does not parse, does not rebuild byte-for-byte, or
carries a hard structural error is **skipped and reported**, never normalized
and never silently dropped. Machine-readable per-map records:

```text
reports/blood-community-corpus-health.json        community/ (1500)
reports/blood-reference-corpus-health.json        reference view (102)
reports/blood-mechanism-corpus-health.json        mechanism/ (172)
reports/blood-own-conversion-corpus-health.json   conversions/ (4)
```

The gate is the one in `docs/corpus.md`: supported major version, byte-exact
native disk roundtrip, byte-exact `BuildIR` reconstruction, zero hard
validation errors.

## Result

| population | selected | pass | skipped |
| --- | ---: | ---: | ---: |
| `community` | 1500 | 1462 | 38 |
| `reference view` | 102 | 102 | 0 |
| `mechanism-tutorial` | 172 | 171 | 1 |
| `own-conversion` | 4 | 4 | 0 |

**1462/1500 community maps pass the gate (97.5%); 38 are skipped and reported.**

## What actually fails

Nothing fails on parse or on either roundtrip:

```text
parse failures        0
byte roundtrip fails  0
BuildIR roundtrip     0
hard validation error 38
```

Every skipped community map is a *structural* failure in an otherwise
byte-exact file. Counts by first reported error code:

```text
next-sector              7
next-wall                3
point2-sector-range      7
portal-pair              6
sector-wall-range        1
start-sector             10
wall-loop-open           4
```

## Map versions found

```text
0x0600   8
0x0700   1490
7        2
```

`0x0700` and `0x0600` are the supported Blood majors. Two files in
`community/` are **Duke3D v7 maps, not Blood maps**:

- `community/POWER06.MAP`
- `community/TWISTER.MAP`

They pass the Duke gate, but they are not Blood precedent and should not be
cited as such. Blood v6 files (`0x0600`):

```text
GMBABRTH.MAP GMBORGO.MAP GMDACIA.MAP GMMADNES.MAP GMRUBBLE.MAP JALTAR.MAP JCRYPT.MAP JFORT.MAP
```

## Failure correlates with the heuristic tier

Tier is a sampling aid, never an evidence weight -- but the gate result is a
measured, independent check on it:

| tier | maps | skipped | skip rate |
| --- | ---: | ---: | ---: |
| `S` | 294 | 0 | 0.0% |
| `A` | 139 | 0 | 0.0% |
| `B` | 150 | 0 | 0.0% |
| `C` | 50 | 0 | 0.0% |
| `questionable` | 152 | 20 | 13.2% |
| `multiplayer` | 548 | 16 | 2.9% |
| `mechanism` | 10 | 0 | 0.0% |
| `untiered` | 157 | 2 | 1.3% |

Every `S`, `A`, `B` and `C` map passes. All 38 skipped maps sit in
`questionable` (20), `multiplayer` (16) or untiered (2). That is a genuine
(if narrow) validation of the classifier's distrust bucket: the maps it
distrusted are the ones that are structurally broken.

## Other populations

The reference view (`campaign/` + `curated/`, 102 maps) passes 102/102, so
the quality yardstick is intact under the new layout.

`mechanism/` skips:

```text
mechanism/helix_stairs.map: start-sector: start sector -1 is outside 0..30
```

## Corpus hygiene finding

- `campaign/ASAVE1.map` sits in an authoritative population directory but
  its filename is not part of that set. It appeared during this run
  (an editor autosave). It is **quarantined**: not enumerated as
  `blood-campaign`, and reported here instead of being
  silently mined as original campaign convention. Move or delete it.

## Known limitations

- The gate measures format and structure, not playability. A map that passes
  may still be unplayable, and a skipped map may play fine in the engine.
- `community/` mode is unknown from the directory; the `multiplayer` tier is
  the heuristic classifier's guess, not a player-start count.
- Community maps are **precedent**, never original-campaign convention.

