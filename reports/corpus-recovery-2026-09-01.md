# Corpus loss and recovery — 2026-09-01

**What happened.** The supervising session had junctioned `maps/` from agent
worktrees to the main checkout so isolated agents could read the corpus.
`git worktree remove --force` on a finished worktree followed the junction
and deleted `D:\Games\DOS\llmapper\maps` in the main checkout: every
population under `maps/blood`, `maps/duke3d`, the review pen, the corpus
manifest and `xmapedit.chm`. Only the tracked `maps/README.md` survived.
`reference/` (ART) survived because its junctions had been unlinked by hand
first. Nothing in git was affected; the corpus is gitignored and had never
been backed up.

**Recovery method.** The tracked health reports carry a sha256 per map:
`reports/blood-reference-corpus-health.json` (102), `blood-community-corpus-
health.json` (1500), `blood-mechanism-corpus-health.json` (172),
`blood-own-conversion-corpus-health.json` (4), `duke3d_corpus_inventory.json`
(41). Every `.map/.MAP` on `D:\Games` and in the archives under
`C:\Users\jiriv\Downloads` was hashed and copied back to its manifest path
on an exact match. Name-only matches were quarantined, never placed in a
population.

| population | manifest | restored byte-exact | source | still missing |
| --- | --- | --- | --- | --- |
| blood-campaign | 43 | 43 | Blood installs on D: | — |
| blood-bloodbath + community-curated | 59 | 55 | D: installs, `Downloads\maps.7z` | SSEVICT, SSFACE, SSHIVE, SSMALL |
| own-conversion | 4 | 4 | D: | — |
| community | 1500 | 1500 | D: installs, `Downloads\maps.7z` (BME pack), `AANDAHL.zip` | — |
| mechanism-tutorial | 172 | 171 | `xmapedit` submodule samples; `maps.7z\BME\tutorial` for the `#` primers | helix_stairs.map |
| duke3d | 41 | 41 | D: | — |

Not in any manifest and not found anywhere on disk: **`mechanism/casket.map`
and `casket.bak`** (owner-authored planar-door oracle, 2026-09-01; four tests
in `tests/test_mechanism_demos.py` depend on it) and **`xmapedit.pdf`**
(`xmapedit.chm`, the same manual, was restored from the submodule).
`SSEVICT.MAP` and `SSMALL.MAP` exist on D: as different versions (hash
mismatch) and sit in `maps/review/recovered-by-name/` with `HOS-E1M3.MAP`.

**Verification.** `corpus-manifest` regenerated; `corpus-health` re-run:
campaign 43/43, community-curated 46/46, own-conversion 4/4,
mechanism-tutorial 171/171, community 1462/1500 with the same 38 hard
structural failures as before the loss. The `tiered/` view is regenerated
by `corpus-tier` from the community population (navigation metadata only).

**Backup.** `D:\Games\DOS\llmapper-corpus-backup\maps` (robocopy mirror,
1820 files). Refresh it after any corpus change.

**Rule adopted.** Never run a recursive delete (`git worktree remove`,
`Remove-Item -Recurse`, `rm -rf`, `rmdir /s`) on a tree that may hold a
junction; enumerate reparse points and unlink each with
`[IO.Directory]::Delete(path)` first. For agent worktrees prefer
`BLOODMAP_CORPUS` and absolute paths over junctions.

## Addendum, 2026-09-02: `reference/blood` was lost too

The first, "permission denied" `git worktree remove` attempt had already
deleted through a `reference` junction left in P2's worktree.
`reference/blood` was empty when P7 reported it; `reference/doom`,
`duke3d`, `eduke32`, `gzdoom` were untouched.

`reference/blood` is the Blood GAME DIRECTORY the tools and the XMapEdit
observer run against, not only ART. Rebuilt from `D:\Games\DOS\BLOOD`
(v1.21; `TILES000/017.ART` sha256 identical across the GOG, vanilla and
BLOODTT installs) and the `xmapedit` submodule:

| restored | from |
| --- | --- |
| `TILES000`–`TILES017.ART` | `D:\Games\GOG Games\One Unit Whole Blood` |
| `BLOOD.RFF`, `SOUNDS.RFF`, `GUI.RFF`, `COMMIT/SURFACE/TABLES/VOXEL/CHARSET.DAT` | `D:\Games\DOS\BLOOD` |
| `xmapedit/` (editor tree incl. `palettes/import/BLOOD.PAL`) | `D:\Games\DOS\BLOOD\xmapedit` |
| `xmpdocs/` | `xmapedit/doc` (submodule) |
| `nblood.exe` (the bot fork) | `NBlood/nblood.exe` (2026-08-27 build) |

Not found anywhere and therefore lost: the bot test maps
`AGTST*.map` (AGTST3/5/7/8/14/18 are cited by the bot docs and
`NBlood/corpus/`) and `overlap1.map`, plus the bot artifacts
`llmapper-bot-iter27.{ndjson,trajectory.ndjson,dem}`. Whether any of the
AGTST maps can be regenerated is an open question for the bot's owner
session. Backup mirror extended: `D:\Games\DOS\llmapper-corpus-backup\reference`.

## Addendum 2, 2026-09-02: `maps/doom` and the Duke extras

`maps/doom/doom.wad` (used by `tests/test_player_space.py`) and `DOOM2.WAD`
were restored from `D:\Games\DOS\chocolatedoom`. `maps/duke3d` had held
more than the 41 campaign maps in `reports/duke3d_corpus_inventory.json`:
the Duke motion corpus test needs more than five distinct slide extents and
found exactly five with the 41 alone. `DukCity1`–`DukCity5.map` (the city
project's Duke norm sources) were restored from the World Tour install and
the Duke tests pass again (28 OK). Whether anything else was in
`maps/duke3d` is unknown; no manifest lists it. Both backups refreshed by
`tools\backup_corpus.ps1` (maps 3292 files, reference 9533 files, on D: and C:).
