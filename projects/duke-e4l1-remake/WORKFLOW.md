# How this map is worked on

The cycle is every level's: **name the place → study how Blood built that
kind of place → state a visible prediction → change the map → look from fixed
poses → hand the frames to blind readers → read back → publish what is open**.
What differs here is one thing: the native MAP is authoritative and is edited,
never rebuilt.

## What is shared, and where this map keeps its part of it

| Step | Tool | This map's part |
| --- | --- | --- |
| Name a place | — | `places.json`: explicit sector boundary, intent, pose set, the `kind` a reader must name, the shelf `study`, the place's own `notes`. `areas.json` is a provisional whole-map index. |
| Study Blood's precedent | `tools.study`, `tools.catalog find` | Studies are on the shelf (`knowledge/blood/studies/works-yard`, `front-office`, `washroom`); a place's notes say what this level took from them. Look at the one sector: a catalogue seed names a cluster. |
| Predict, then compare | `tools.judge_experiment` | `experiments/<name>/hypothesis.json`, written against the input map's hash before the pass. |
| Look | `tools.look duke-e4l1-remake --set <set>` (`--empty`, `--mute`, `--posed "sprite N"`) | `poses.json`: absolute poses in Build units, each naming its sector. |
| Blind readers | `tools.critique --project duke-e4l1-remake prepare <place> --poses <set> --kind <kind> --study <study>` | Rounds under `reports/critique/<place>/`. A prepared round is not a review. |
| Status | `status.py` | Baseline geometry kept, mechanism extensions changed on purpose, each pass's read-back, and each place's last round (current or historical by hash). |
| Mechanism state | `bloodmap.posed`, `tools.mechanism_look`, `wiring.Circuit` | `weather.py`, `briefing.py` declare their wires around the channels the map already uses. |
| Tests | `tools.suite --project duke-e4l1-remake` | `tests/`: the patch guard, the status's evidence rules, the briefing circuit. |

## What does not transfer

A build script (`level/build.py`, Gravesend's `build_skeleton.py`) writes a
map from source; here that would overwrite the editor's work. Change the map
only through a new guarded pass (`edit_map.py`, see README.md); no old pass is
a recipe for rebuilding it, and `tools.project status` (which reads a build
manifest) does not apply: `status.py` is this map's status.

Portal-grown rooms merge several halls and mechanisms in this converted map:
confirm a boundary before editing. Camera-only scenery 535-542 and mirror
support 57 are not rooms to dress.

## After any editor save

Run `status.py`; every frame and round taken of the old bytes is now
historical, and says so. Author review does not replace blind readers or the
owner's playthrough.
