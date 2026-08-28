# Blood City — handoff

Gravesend, the demonstration city. What it is, how to run it, what is
actually wrong with it, and what to do next.

## Where it stands

**182 sectors / 1,210 walls / 297 sprites.** 11/11 conformance rows, 16/16
L1 contract rows. Wall budget is 7,000, so there is room for roughly five
more districts' worth of content.

Built: four districts (Theatre Row, Old Crossing, Market Slip, Foundry
Ward); the Aldermack complex with saloon, shooting parlor and pawn shop;
St Gallow's with its cemetery and pitched nave; the Gravesend Arcade with
six retail units and a locked service corridor; a parked sewer ring on ROR
stack links with two legible entrances; a pumping station. Sixteen signs.

```bash
python projects/blood-city/level/build_skeleton.py      # build
python projects/blood-city/level/conformance.py         # 11 standing rows
python projects/blood-city/level/plan_review.py         # 16 L1 contract rows
python projects/blood-city/level/look.py --set church --tag next
python projects/blood-city/level/object_loop.py         # per-object packets
```

The playable artifact is `level/blood-city-current.MAP`. Render frames are
gitignored — regenerable, 135 MB, and the reference frames among them are
renders of commercial maps.

## The finding that matters most: we were not using the grammar

Of 31 authoring-relevant `bloodmap` modules, the city used **13**. Worse,
four of the eighteen unused ones had been **reimplemented here, badly**:

| project-local | the general module | what the reimplementation got wrong |
|---|---|---|
| `doorswitch.py` | `bloodmap.switches` | omitted `trigger_push` and `trigger_on`, which 230 and 316 of the campaign's 356 tile-1070 levers set — **our levers could not be pushed**; and rediscovered the 0.79 mount height the module already returns |
| `keysign.py` | `bloodmap.keys` | hand-specified a literal wall segment where `sign_the_locks` finds every keyed region and its approach wall automatically, and reports what it could not sign |
| `props.py` wet gating | `bloodmap.furniture` | hand-listed `{660, 664, 668}`; `wet_only()` is `{546, 660, 664, 668}` |
| `materials.py` | `bloodmap.surfaces` | parallel vocabulary for the same idea |

`bloodmap.switches` and `bloodmap.furniture` are now adopted, which fixed
the inert levers. The rest is listed under "next" below.

Knowledge was worse: of 20 files in `knowledge/blood/design/`, the city
**loaded one** (`set-pieces-v1`), and referred to two others only in
comments. `keys-v1` and `switches-v1` were read by a human (me) and
transcribed by hand, when the modules that consume them already existed.

**The rule this suggests:** before writing a helper in
`projects/blood-city/level/`, grep `bloodmap/` for the noun. If the noun
exists there, use it and file a grammar request for what it lacks. Four of
this project's modules would not exist under that rule.

## Standing disciplines

- **`bloodmap/` is the parallel grammar agent's tree.** Never patch it.
  Gaps go to `reports/grammar-requests.md` (#1–#10 so far).
- **The NBlood and xmapedit submodules are off-limits.** Never stage their
  pointers.
- **Never launch NBlood.** Verification goes through the XMapEdit observer
  (`look.py`, `object_loop.py`) and the static checks.
- **Bot runs are crash-smoke only**, never navigation evidence.
- **Labels are interpreted; signatures, proportions and occurrences are
  derived.** Say which is which in every knowledge file.
- **An object with a mined class is authored through its constructor.** A
  one-off with no precedent is allowed but says so in the source and still
  gets the render loop.
- **A fix you did not re-render did not happen.**

## Traps that have bitten more than once

- Two rooms may share an edge only if the faces are exactly equal or
  strictly inside, anchored from the smaller. A partly-shared edge leaves
  unpaired coincident walls — join through a neck whose whole face is the
  mouth.
- `carve` adds a hole; it does not union with an existing one.
- A face sprite's z is its centre.
- A room flush with a mass face contains its own doorway.
- A locked room legitimately has no walkable-at-rest exit; declare
  `declared_zero_exit` rather than weakening the lock.
- A slope hinge must be an edge of the outline **in its own winding order**.
- Free-standing masses in streets add walk-around loops; a monument (no
  doorway) is declared in `conformance.MONUMENTS` and set aside before the
  CN 2 block band.

## What is planned next, ordered by measured gap

**1. Finish adopting the grammar.** `bloodmap.keys` (replace `keysign.py`;
`sign_the_locks` + `check` are strictly better), `bloodmap.surfaces`
(fold into `materials.py`), `bloodmap.aperture` (`pierce` / `framed_door` /
`snap_leaf` replace every hand-built door+porch chain in five modules), and
`bloodmap.prefab`'s `alcove_run`, `parapet` and `breakable`. Cheap, and it
removes four sources of drift.

**2. Slopes: 0 → 21.7%.** The nave now has a pitched roof and it is the
only sloped surface in the city; the campaign median is 21.7% of sectors.
`bloodmap.slope` is the tool and a sloped ceiling "costs nothing but
headroom". Candidates: the arcade concourse, the sewer legs (vaults), the
auditorium, roof pitches once masses have tops.

**3. Named uses: ~9 → ~10 per map.** DukCity names roughly ten uses per map
on its walls. `oc_block_a` (12×14 plan units) and `market_block_a` are the
next interiors; `references/dukcity-signs.txt` has the vocabulary.

**4. Rectangularity: 11% → 23–35% diagonal walls.** Chamfered masses got us
from 7% to 11%. The ceiling is structural: every interior room is an
axis-aligned rectangle because `Assembly.room` joins on named compass
faces. Grammar request **#10** asks for faces on arbitrary polygons.

**5. No skyline.** Every mass rises to the same sky, so the church tower —
which `church-patterns.md` asks for as the vista silhouette — cannot be
seen from the street at all. A massing-layer change, and E3M1's own
differentiator is its stepped roofscape.

**6. Light props at 19% against the campaign's 3%.** Two reasoned
deviations (nine street light pools, six sewer corner lights) cover 15 of
the 20; the interiors could lean further on shade.

**7. Set-piece coverage.** Three objects are under the object loop
(fountain, saloon counter, church altar). Market stalls and the stove are
declared in `setpieces.py` and not wired. The furnace seed is still not
reproduced as one piece — E1M1's 80/81/88/89 chain through a connecting
room, so the detector splits them. Left honest rather than tuned away.

**8. Duke conversion: 26%.** Across 56 Duke maps and 5,968 sector
effectors, `bloodmap`'s Duke support handles the teleport, door, bridge and
rotation families. The unhandled majority is **lighting and destruction,
not motion**: random lights (757, 39 maps), light switch (574), conveyor
(474), explosive (427), ceiling/floor rise-fall (736), door auto close
(315, 45 maps). Ordered roadmap in `knowledge/duke3d/mechanisms-v1.json`.

## Open taste calls

`reports/review-queue.md` holds what passes measurably but needs a human:
the three object-loop frame pairs, and every fun-critical judgement. The
automation verifies walkability, budgets, norms, conformance and visual
checks. It cannot judge fun.
