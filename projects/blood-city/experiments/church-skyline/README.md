# Experiment: does St Gallow's look like a church from the street?

> **Superseded the same day by `../church-roofs`.** The method here -- lowering
> the sky in front of a face -- hides everything beyond that face, which the
> owner saw at once in NBlood. The measurements and reviews below stand as a
> record of what was built and seen; the technique does not.

2026-11-17. One building, three rounds, the same twelve street cameras
throughout (`look.py --set skyline`). Before/after pairs:
[`before-after.png`](before-after.png).

Kinds of thing in this folder, kept apart on purpose:

| what | where | kind |
|---|---|---|
| what was expected, written first | `hypothesis.json` | prediction |
| the maps looked at | `<run>/observed.MAP` | compiled geometry |
| the frames | `<run>/frames/*.png` | rendering (observer, not NBlood) |
| the numbers | `result.json`, `measurements.txt` | measurement |
| what a stranger took it for | `critic-round{1,2,3}.md` | interpretation |
| whether a route exists | `route/static-route.json` | map reading, not play |

Authored source: `level/l3_church.py` (`massing`, `glaze`, `street_hole`),
on `bloodmap/skyline.py`. Rebuild with `python level/build_skeleton.py`; it
is deterministic (same sha256 twice).

## The observation

From every street pose the church was a blank pale slab 11.6 bodies tall, the
height of every other block. Measured: all 141 one-sided walls under open sky
in the city were drawn to one height. The room called "tower" was 5.8 bodies
clear inside a wall twice that.

## The cause

A mass is a hole in the street. Its face is a wall of the street's sector,
and a one-sided wall is drawn to its own sector's ceiling. Height was never a
property of a building here.

## The rounds

| round | change | map sha256 | sectors |
|---|---|---|---|
| before | — | `5a1aac2ed778…` | 259 |
| 1 | aprons: body 6.8 bodies, flat tower 15.5 proud of the avenue face; belfry room | `e91eb78417ee…` | 263 |
| 2 | body to 3.9; churchyard wall 3.1 and the churchyard's own sky; buttresses; 14 lancets; six tower gables of 1.9 | `8b043cbdb22c…` | 270 |
| 3 (`after/`) | gables to 3.9, ridge 17.4; avenue portal 1.9 to 2.4 bodies | `ebfe5628812e…` | 270 |

## The predictions, scored

| | prediction | result |
|---|---|---|
| P1 | sky share +0.15 in `avenue_front`, +0.25 in `avenue_front_up` | **failed** in round 1 (+0.000, +0.082). After round 2: +0.133 (still short) and +0.341 |
| P2 | tower walls paint 300+ px in five named views | held: 5,355 to 95,438 |
| P3 | the tallest street wall is a tower wall; three distinct heights | first half held; **the count is 5, not 3**, because round 2 added the churchyard wall and changed the eaves |
| P4 | `cemetery_side` pixel-identical | held in round 1 (0 px). Broken on purpose in round 2, which lowers the churchyard's sky |
| P5 | nave, chancel, aisle, narthex frames pixel-identical | held: 0 px in all, every round |
| P6 | read-back agrees; deterministic; only new rule finding is the sky-step one | held as written. **Not predicted:** the aperture audit counted every sky step as a lintel (real findings 23 to 45 before its repaint pass) |
| P7 | no sky seam drawn | held: no `upper` surface on any sky-to-sky wall in any frame |

## What the failures taught

**P1.** At 6.8 bodies the eaves cannot show sky from across a 7-unit avenue;
a wall shows its top at a level gaze only from about 1.7 times its height
away. So the height that matters on a street is the height of what *fronts*
it — here the low side range, 1.9 to 2.4 bodies inside — and round 2 drew the
body at 3.9. This became a record of the visual construction atlas, now a finding
(`python -m tools.findings find <words>`).

**P6's blind spot.** The shared aperture audit did not know that a step
between two parallax ceilings paints nothing. Fixed in
`tools/mine_apertures.py` with the engine citation. After the build's own
lintel pass the city now has 6 real aperture findings where the baseline had
14: the baseline carried the same false positives wherever two open sectors
of slightly different sky met.

**The rule that would have nagged.** `open-neighbours-share-a-sky` warned on
every apron (14 warnings). Its own text says the concern is clipping. It now
fires only when the lower sky is within three bodies of the floor: 0 in the
city, still 4, 20, 6 and 1 in E1M1, E1M3, E3M1 and E4M1.

## What a stranger saw

Three separate reviewers, each shown only one round's frames:

| | round 1 | round 2 | round 3 |
|---|---|---|---|
| the building | warehouse / fortress (guess) | church (likely) | church (likely) |
| the tower, far | factory chimney (likely) | obelisk | church steeple (certain) |
| the tower, near | plain shaft (guess) | chimney or pillar | plain shaft, flat top (guess) |
| the door | shed or service door | garage door | church door (likely) |

Massing alone did not make a church: round 1 gave it a height and a tower and
it was still a warehouse. The glass did (the reviewers say so in as many
words), the steeper gable made the far silhouette, the taller portal made the
door. **The tower from its own foot is unsolved**, and the author's own note
on round 3 ("reads as a steeple") was right for two frames and wrong for two.

This is an ablation by history, with one reviewer a round. It says which
change coincided with which reading. It does not isolate the glass from the
buttresses or the lower eaves; removing the glass alone and reviewing again
would.

## Does it still work as a level?

Not known. `route/static-route.json`: the map contains a chain of openings
from the spawn through the avenue apron and the portal to the new belfry,
with one door on it (sector 79). `a_player_was_moved: false`. NBlood was not
launched; this project's rules forbid it.

Standing checks, before and after: `conformance.py` 12/13 both times (the
same pre-existing four-sector drift), `tree_tests.py` fails on the same 13
pre-existing findings, the full unit suite passes, and the build's rule
report is the baseline's (13 errors, 6 warnings, none new).

## Not done, and known

- The tower's near read (above).
- The church's nave still cannot be seen from the street: an apron hides
  everything behind its wall. A clerestory over the low range needs roof
  sectors with raised floors, which means stacking over the interior.
- The churchyard wall is low on the avenue and Theatre Row and still 11.6
  bodies on the west street and Market Street.
- The buttresses step the cornice and read as battlements.
- Lancets are sprites, not glazed openings; nothing is lit by them inside.
- The other 113 street walls in the city.
