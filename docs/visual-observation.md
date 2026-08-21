# Structured visual observation

How a source node gets asked what it looks like, and what comes back.

```text
LevelProgram node
    -> compiler allocations        which sectors, walls and sprites it owns
    -> MAP
    -> xmapedit-observe            one process, one map load, many poses
    -> visible native ids          what the renderer actually painted
    -> visible source nodes        the join, back in the author's own names
    -> optional PNG
```

The product is the JSON. A frame is written only where one is asked for, from
the same pose, so a picture can be checked against the numbers rather than
standing in for them.

## Why not NBlood

The old path was: launch the game, find its window, focus it, inject a key
bound to `screenshot`, wait, hope a file appeared. It worked, slowly, and the
frames had the game in them — a red pain flash at 52 health, a cultist walking
into shot, an automap someone had left toggled on. Four monastery iterations
recorded "the sky renders very dark" as an unexplained unknown partly because
the evidence was that noisy.

NBlood keeps the jobs only a running game can do:

| Question | Answered by |
| --- | --- |
| does the MAP initialise, does the player spawn | `run_nblood_oracle` |
| does a door move, does a switch fire, is it playable | `run_nblood_action_oracle`, `run_nblood_behavior_oracle` |
| what does this room look like, what is visible from here | `bloodmap.visual` + the observer |

`run_nblood_viewpoint_capture` and the window-focus and key-injection helpers
under it are deprecated. They are the third row, and the third row moved. They
still work, and there is one thing they can still do that the observer cannot:
photograph a *running* state — a door mid-travel, a switch after it fires.

## The extension seam

The fork's engine is JFBuild's classic software renderer (`xmapedit/src/engine.c`).
Every surface it draws goes through one of seven scan functions, and each of
them receives the screen columns it is about to paint together with the clip
window that survived the front-to-back bunch sort:

| Scan | Painted rows per column |
| --- | --- |
| `wallscan` | `[max(uwal, umost), min(dwal, dmost))` |
| `maskwallscan`, `transmaskwallscan` | the same, against the view window |
| `ceilscan`, `grouscan` (ceiling) | `[umost, min(uplc, dmost))` |
| `florscan`, `grouscan` (floor) | `[max(dplc, umost), dmost)` |

So the hook is one line in each, plus four globals set where the caller knows
which wall or sprite it is. Nothing is recomputed and nothing is estimated:
the accumulator runs the same clip expression the scan runs one line later.

That gives the one fact llmapper genuinely cannot derive from the map file:
**post-occlusion painted area**. Classic Build narrows `umost`/`dmost` as it
draws, so a wall hidden behind a nearer one is handed a window of zero height
and contributes zero pixels. A surface that reached the renderer and painted
nothing is kept separately, under `occluded`, because "the gallery is in the
traversal but no pixel of it survives" is a different fact from "the gallery is
not there".

`obs.c` merges records by `(kind, sector, wall/sprite, picnum)` — one wall is
often scanned in several column chunks because bunches interleave.

## What each side owns

**XMapEdit** — renderer traversal, camera and frustum state, which native
objects reach the renderer, screen-space placement, occlusion, optional frames.

**llmapper** — the hierarchy, semantic ids, the allocation mapping, all
player-relative measurement, ART knowledge, authored intent, aggregation across
views, and what to point a camera at.

Depth is on the llmapper side deliberately. Once you know which wall is visible
and where the camera is, distance is geometry, and llmapper reports it in player
widths from the map rather than in whatever the renderer happened to keep.

## Running it

```bash
mingw32-make -C xmapedit/src_blood/observe
python -m tools.observe program experiments.nested_authoring -o work/obs-nested --structures
python -m tools.observe decompiled maps/blood/E2M3.MAP \
    --hierarchy projects/e2m3-decompiled/hierarchy.json -o work/obs-e2m3
```

The observer is a separate ~200 KB binary built from the fork's engine sources
with `USE_POLYMOST=0 USE_OPENGL=0`: no SDL, no GL, no audio, no GUI, no message
loop. It reads Blood MAPs directly and takes its palette and shade tables from
`BLOOD.RFF`.

Frames default to 640×480. The engine treats 320×200 and 640×400 as Mode 13h and
leaves the pixels non-square; every other size gets the aspect correction, and a
4:3 size gets it without also being too coarse to read a room from. Anything up
to 7680×4320 works.

Getting the colours right took two facts about Blood's own data, and one wrong
turn worth recording because the wrong version looked plausible.

**Bit `0x10` of an RFF directory entry means the first 256 bytes of the payload
are encrypted** with `byte ^= index >> 1`. The data settles it: decrypted,
`NORMAL.PLU` shade level 0 is the identity map in all 256 positions, which is
what shade 0 has to be, and `BLOOD.PAL` becomes byte-for-byte the palette the
game displays. Undecrypted it is neither.

**Blood stores eight-bit colour**, and the engine's ordinary path builds its
display palette by shifting a six-bit VGA palette up two bits — so feeding it
Blood's palette either overflows every channel or, if you shift down first,
quantises away the low two bits of every colour. `setbrightness_replace` is the
engine's own hook for a port whose palette is already eight-bit, and what it
writes is used verbatim.

The wrong turn: the first version decrypted correctly but fed the eight-bit
palette through the six-bit path, which overflowed, and the brightest surfaces
came out as magenta speckle. Removing the decryption *and* adding a `>> 2`
cancelled the two errors well enough to look like a plausible dark Blood frame —
it was neither the right palette nor full colour depth. Both are now checked
against what NBlood displays: all 256 entries match exactly.

## Measured cost

E2M3, 340 sectors, 163 planned views at 640×480:

| | ms |
| --- | --- |
| engine init | 25 |
| ART load | 2 |
| map load | 0 |
| all 163 views | 55 |

About a third of a millisecond a view once the map is up, and roughly 35 ms of
fixed cost for the process. There is no reason to keep a server alive.

## Poses

`bloodmap.viewplan` decides what is worth looking at; the observer only renders
what it is handed. A plan is deterministic, so two observations of the same
place are comparable and a source edit shows up as a change in what is visible
rather than as a change in where the camera stood.

Poses that geometry already rules out are dropped in the planner with a reason.
The observer checks again — inside the sector, between floor and ceiling — and
reports `invalid_pose` rather than nudging the camera. Both ends declining is
deliberate: a silently moved camera answers a question nobody asked.

A plan is derived from geometry, so an edit that moves geometry moves the camera
too. For a before/after read, pin the pose:

```bash
python -m tools.observe program experiments.nested_authoring \
    -o work/after --replay work/before/packet.json
```

## Reading one view

```text
View: nested_manor_lobby__entry -- room_entry
  camera: sector 0, angle 0, horiz 100
  of: nested/manor/lobby
  visible:
    nested/manor/lobby: dominant, 79.6% of frame at 4.18-14.14 PW
    nested/manor/lobby/stairs:grand: present, 8.1% of frame at 13.15-21.01 PW
    nested/manor/upper_gallery: present, 5.5% of frame at 21.01-32.94 PW
    nested/manor/lobby/recess:lobby_niche: present, 3.9% of frame at 7.38-10.47 PW
    nested/grounds/porch: present, 3.2% of frame at 7.38-14.05 PW
  dominant surfaces: tile 5 (48%), tile 294 (31%), tile 454 (8%)
```

"dominant", "prominent", "present", "a trace" are read straight off the frame
fraction and say only what was measured. There is no score. Whether 8.1% is
enough for a staircase is a question about the brief, and the brief is not
something this code has seen.

## Known limitations

Always restated in every manifest:

* one static world state — no door moves, no sector effect runs, no gameplay;
* the editor renderer, not the game renderer; NBlood differs on sprites and effects;
* coverage is post-occlusion painted pixels, and sprite occlusion follows the
  engine's own sprite clipping rather than an exact per-pixel test;
* voxels and models are not drawn;
* `painted` can exceed the frame's pixel count, because masked walls and sprites
  paint over what is already there;
* a hole's walls belong to the host sector in Build, so an embedded building's
  exterior faces are attributed to the space around it rather than to the
  building.
