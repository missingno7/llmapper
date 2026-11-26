# E4L1 Blood remake

The live editable map is **`E4L1-current.MAP`**. Open that file in XMapEdit.
`E4L1-baseline.MAP` and `conversion-report.json` are the preserved starting
point. The original Duke MAP remains a reference. This project edits native
Blood records; it does not run a conversion or regenerate the level.

The owner chose a **disused quarry and pumping works used by the Cabal**.
Keep the original Mission Impossible facility's covert infiltration mood,
night storm, lightning and industrial scale. The first area is the quarry
approach and service entrance; the interiors still need their own passes.

## Start here

- [Design, references and work order](DESIGN.md)
- [How this map is worked on](WORKFLOW.md)
- [Generated current status](reports/STATUS.md)
- [Converter bugs, bathroom repair and manual mechanism work](reports/converter-mechanism-audit.md)
- [Named place briefs and explicit editing boundaries](places.json); each place's own notes in `notes/`
- [Area membership and interpretation](areas.json)
- [First-pass read-back](reports/first-pass-readback.json)
- [Weather circuit read-back](reports/storm-wire-readback.json)
- [Before / current / lightning comparison](evidence/comparison.png)
- [Historical provisional area plan](evidence/area-plan.png) (room 389 was
  misidentified; use the corrected `areas.json` and `places.json`)

The images are local observer renders. The comparison hides enemies and
pickups to make architecture legible; actor-present frames are under
`evidence/pass-03/with-actors/frames`. A posed lightning peak is an endpoint
illustration, not a recording of runtime events or sound.

## Editing and preserving manual work

Save normal XMapEdit work to `E4L1-current.MAP`. The map is authoritative;
Python files and JSON patches are editing aids. Finish saving in the editor
before applying an automated pass.

Each file in `passes/` is a reviewed incremental change with exact old/new
field values and native record identities. `edit_map.py` reads the current
map, preserves unrelated fields and manual edits, checks every touched
field, validates and reparses the result, saves a content-addressed backup,
then replaces the working file. It refuses conflicting edits and record
renumbering instead of overwriting them. Appended sprites are tracked to
prevent duplication. A missing pass report can be recovered from matching
native sprite records.

For a **new** reviewed pass:

```powershell
python projects/duke-e4l1-remake/edit_map.py projects/duke-e4l1-remake/passes/NEW-PASS.json --dry-run
python projects/duke-e4l1-remake/edit_map.py projects/duke-e4l1-remake/passes/NEW-PASS.json
```

Do not replay the old passes as a build process. Later passes deliberately
refine earlier fields, so old preconditions can cease to hold. Write a new
patch against the current native map. Resolve a conflict by inspecting the
live record and revising the **new** pass; preserve the editor's work.

Applied during this first editing session:

1. `01-quarry-approach`: geology, ground, facade, practical lamps, loose rocks,
   wind and the lightning/thunder circuit.
2. `02-storm-panorama-and-service-gate`: full 16-panel cloud sky and the inner
   service threshold. Shared playable sky surfaces use the same panorama.
3. `03-service-gate-panels`: recognisable Blood metal-door panels at the
   native texture scale, following review of the first frames.
4. `04-intake-hall`: slab work floor, pressed-metal ceiling, brickwork,
   clock and three ceiling fixtures; ART-aware saved positions for three cultists.
5. `05-intake-scale-and-frames`: correct brick proportions after rendering
   and replace ornate frame strips with riveted metal cladding.
6. `06-briefing-recorder`: restore the owner-identified self-destructing tape
   player's missing Use/delay circuit; wooden desk and cabinet device treatment.
7. `07-recorder-panel-scale`: fit cabinet art to the retained device face.
8. `08-converter-motion-repairs`: source-backed swing direction, motor speed,
   easing and return timing; protect motors from independent light conversion.
9. `09-static-bathroom-room`: keep actual bathroom 152 static; preserve its
   entry signal and the separate swinging stall door 61.
10. `10-washhouse`: tiled workers' facilities, metal partitions, stone toilets
    and urinals, local flush sounds, practical lights and vent treatment.

Exact backups are in `snapshots/<sha256>.MAP`. Pass application reports are
in `reports/`. The baseline is rejected as an edit target. MAPs and rendered
commercial-map images stay gitignored; retain the original local data.

## Look and verify

Looking, critique and tests are the shared tools'; `project.json` tells them
where this map and its poses are.

```powershell
python -m tools.look duke-e4l1-remake --list                                  # the pose sets (poses.json)
python -m tools.look duke-e4l1-remake --set quarry --empty -o work/e4l1-quarry
python -m tools.look duke-e4l1-remake --set quarry --empty --posed "sprite 334" -o work/e4l1-lightning   # storm clock at its peak
python -m tools.look duke-e4l1-remake --set intake -o work/e4l1-intake         # with actors; --mute hides every word
python -m tools.critique --project duke-e4l1-remake prepare washhouse --poses washhouse --kind bathroom --study washroom
python -m tools.critique --project duke-e4l1-remake verdict washhouse
python projects/duke-e4l1-remake/inspect_briefing.py
python -m tools.verify_motion maps/duke3d/E4L1.MAP --converted projects/duke-e4l1-remake/E4L1-current.MAP -o work/e4l1-motion.json
python projects/duke-e4l1-remake/status.py
python -m tools.sprite_fit projects/duke-e4l1-remake/E4L1-current.MAP
python -m tools.suite --project duke-e4l1-remake
```

Each look writes `render.json` (map, poses and frame hashes); each critique
round's `packet.json` does the same, and `status.py` calls a place's evidence
historical once the map is saved or a pose moves. The kind, study and pose set
of each place are in `places.json`. Blood's own precedents for these places are
shelf studies: `knowledge/blood/studies/{works-yard,front-office,washroom}`.

`weather.py` declares its wire through `bloodmap.wiring.Circuit`, allocating
around existing channels. It adapts existing native objects for declaration
and read-back; it compiles no geometry. Its current wire and listeners are
recorded in `reports/storm-wire-readback.json`.

The first pass preserves all 546 sectors, 3488 walls, original sprites,
topology, heights, slopes, start and existing mechanism fields. It adds
seven sprites. Native read-back has zero structural errors; the original
structural warnings remain. Four visible additions have no new fit faults.

The first-pass report is historical, tied to its recorded hash. Current
read-back is generated by `status.py`. Pass 10 leaves 404 sprites. Saved
sector/wall geometry remains unchanged. The recorder's Use circuit and the
source-backed motor repairs are intentional extension changes; pass 09 also
retires one incorrectly generated rotation marker. Three original sprite Z
values were corrected during the intake pass. Current fit results and the
remaining manual mechanism work are in the generated status and audit.

Owner walking, audio/timing verification and independent visual review are
still pending. The exit sequence is unverified. The saved-map fit reader now
finds 69 partly buried actors, down from 72; Blood seats actors at spawn, so
this is an authoring diagnostic. The review packets once prepared by a private
`review.py` (`reviews/`, map `57f31fb5`) were never answered by any reader and
held no judgement; they were retired on 2026-11-26. The washhouse has a shared
critique round 1, prepared and unanswered. See the generated status.
