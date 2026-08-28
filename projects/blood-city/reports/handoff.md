# Blood City — handoff

Gravesend, the demonstration city. What it is, how to run it, what is
actually wrong with it, and what to do next.

## Where it stands

**215 sectors / 1,378 walls / 367 sprites.** 13/13 conformance rows, 16/16
L1 contract rows, 5/5 tree properties, 50 rule diagnostics with no errors.
Wall budget is 7,000, so there is room for roughly four more districts'
worth of content.

The level program is a **six-deep tree**: city, district, venue, space,
template, run, fixture. Read it from any distance without loading it all:

```bash
python projects/blood-city/level/citytree.py stats
python projects/blood-city/level/citytree.py zoom saloon --depth 2 --cost
python projects/blood-city/level/citytree.py at 46080,49152
python projects/blood-city/level/citytree.py find pawn
python projects/blood-city/level/tree_tests.py
```

`reports/city-tree.md` is the generated listing. `citytree.py` also carries
`nest`, which reparents a node while proving its world frame did not move,
and `join`, which declares a connection on the lowest assembly that owns
both sides.

## Update — shared door and lighting semantics

The current generated artifact is **208 sectors / 1,314 walls / 297 sprites**.
The extra geometry is intentional: all thirteen type-600 doors now compile
through `bloodmap.aperture.frame_z_doors`, which inserts reveal frames around
the moving leaf.  Their `bloodmap.doors.z_motion_door` declarations carry
`busy_time_a/b=5`, so no door changes state instantly; the five theatre doors
keep both direct Use and their lever RX channels.  The build manifest records
`door_frames: 13` and semantic LightBomb sources.

The reusable route and the full authoring-tool map are in
[`docs/authoring-toolkit.md`](../../../docs/authoring-toolkit.md).  Use it before
adding project-local helpers.  Shared `bloodmap` changes are appropriate only
when they are a tested generalisation of a concrete map case; do not edit
unrelated primitives or the NBlood/xmapedit submodules.

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

- **`bloodmap/` is shared grammar.** Consume existing constructors first.
  Promote a repeated, tested map case into it; otherwise leave a documented
  `Room.raw` escape and add a concrete `reports/grammar-requests.md` entry.
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

## The invariant that makes restructuring safe

`level/fingerprint.py` reduces a compiled MAP to an **order-independent**
multiset of sectors, walls and sprites. Reparenting renames every region
and reorders the compile, so a byte diff cannot tell a restructure from a
redesign; this can.

```bash
python projects/blood-city/level/fingerprint.py before.MAP after.MAP
```

Use it for any change that is meant to move structure and not geometry.
Every step of the tree overhaul passed it with zero differences, and it
caught three inheritance faults on the way -- see iteration 25 in
`refinement-log.md`.

## A wall is a 2D surface

`level/wallplane.py` treats a wall as the plane it is: every wall sprite
reserves the rectangle it actually draws (tile width x `x_repeat` along,
`sprite_extent` down), and nothing may be hung over it. Two things stacked
at different heights are legal -- that is the point -- so a caption sits
under its painting.

```bash
python tools/mine_wall_sprites.py projects/blood-city/level/city-skeleton.MAP
python tools/mine_wall_sprites.py --corpus     # the rate to stay under
```

Gravesend was at **18.86 clashing pairs per 100 wall sprites with 26 fully
hidden**, against a campaign 0.0-8.0 and 0-4. It is now **0 and 0** with more
on the walls than before (203 against 175). The audit runs inside the build.

Use `wallplane.sprite` and `wallplane.text` rather than `place_on_wall` or
`lettering.write_on_wall` directly.

**Name a style rather than a size and a palette.** `wallplane.TextStyle` is
`fixtures.Family` one layer up: it pins size, palette and shade, frees the
words, and steps down its own ladder when the wall is short.
`wallplane.STYLES` is the corpus's table of them -- `works` is what DWE puts
on POWER PLANT, `department` is MEDLAB, `breach` is WALL BREACH -- and
`wallplane.style("fascia", initial=(1.4, "warning"))` varies one. For raw
control, `text` still takes `size`, `palette` and `shade` as a scalar or a
sequence; a sequence pads with its last value, so `size=(112, 72)` is a drop
capital, and `cycle()` opts into repetition.

`vertical=True` writes downward at the corpus's own **1.095** letter pitch
(11 columns: ABALCO, HOTEL, FRIES); stacked LINES sit **1.455** apart, which
is what `LINE_GAP` comes from. `wallplane.composition` stacks blocks;
`venue_detail.COMPOSITIONS` is the table of the four Gravesend has.

## Every node says what it is for

Names carry intent; notes carry what a name cannot -- the precedent, the
measurement, the reason.

```bash
python projects/blood-city/level/citytree.py find stage
python projects/blood-city/level/citytree.py stats          # to-do list, rhythm faults
python projects/blood-city/level/citytree.py zoom saloon --cost
```

* **A template names what it places.** If you are about to write a loop over
  a table of rectangles, write a template instead: the names come out right
  as a side effect. `theatre_house`, `shooting_range`, `chapel_furnishing`
  are the ones that replaced the last two hand loops.
* **An index means a rhythm.** Numbered siblings must share one note; if
  they need different notes they are different things. Checked in
  `conformance.py` and `tree_tests.py`.
* **Declared-but-unbuilt is legal.** `citytree.plan(parent, id, purpose)`
  makes a named empty node, listed by `stats` as the city's to-do list.
  Prefer it to leaving a planned space absent.
* **Every venue node declares its L1 slot** with `citytree.declare_venue`,
  and conformance checks plan-to-tree in both directions plus the type.

## Detail at every scale

Three constructor layers now sit under the templates, each mined from a map
that does it well and each landing in the tree:

| layer | module | source | what it makes |
|---|---|---|---|
| wall | `wallplane.py` | corpus | signs, paintings, compositions |
| surface | `surface.py` | 10 maps | what stands ON a fixture |
| sewer | `sewerkit.py` | E3M3 | mouths, towpath, tunnel register |

```bash
python tools/mine_surface_items.py -o knowledge/blood/design/surface-items-v1.json
python projects/blood-city/level/citytree.py zoom saloon --depth 4
```

**`surface.py`** is `wallplane`'s horizontal counterpart: a fixture's top is
a plane, items stand on it at the mined rhythm, and it refuses two things in
one place. Items are `native_detail` declarations on the fixture room, so
`citytree zoom` reaches them and an agent can change them without reading
the level. `CARRY_SHARE` is **0.047** -- 56 of 1,198 campaign surfaces carry
anything -- so nothing is dressed unless a caller says `every=True`.

**`sewerkit.py`** carries E3M3's register with its own heights, the ledge
family, and `line_mouths`: tile 194 goes on a *short* opening with a band
above it, which is 2.6% of E3M3's two-sided walls, not all of them.

**Text styles** now carry `tracking` and `jitter` as well as size, palette
and shade. `carnival` is E1M4's ROTTEN CANDY -- 2.0 drawn widths of tracking
and 0.73 of jitter; `fortune` is the corpus's one regular palette cycle.
Only 5.6% of campaign signs mix palettes at all, and they sit where the
identity carries them, so a church does not get one.

## Composing, not placing

`templates.py` is the layer above `fixtures.py`. A template takes the space
it is handed and returns a node whose children are the templates it placed:

    retail_row -> shop -> run -> fixture -> goods
    bar        -> counter run + tables

`retail_row` derives its count from the frontage at E4M9's measured rhythm
(2,560-unit units opening on 1,536), so the arcade responds to its site
instead of carrying a 3x2 grid of absolute rectangles. Range-tested 1 to 13
shops. When adding a venue, reach for a template first and add one if
nothing fits -- the same rule as `bloodmap`: grep for the noun.

## What is planned next, ordered by measured gap

**0. Slopes, still: 3 sectors of 215 against a campaign 21.7%.** Now the
cheapest large win, and the tree makes it a per-node change: an assembly can
state a ceiling slope its rooms inherit. Candidates unchanged -- the arcade
concourse (already pitched), the sewer legs as vaults, roof pitches once
masses have tops.

**0b. Shutter some fronts.** `fixtures.close_front` exists and is still
unused, so the city shows exactly as many units as it furnishes. Mine the
open-to-closed ratio from DWE3M1 and DWE3M10 first; the constructor is one
line once the number is known.

**1. Finish adopting the grammar.** `bloodmap.aperture` is now adopted for all
thirteen Z-doors (`frame_z_doors` plus `z_motion_door`). Next: `bloodmap.keys`
(replace `keysign.py`; `sign_the_locks` + `check` are strictly better),
`bloodmap.surfaces` (fold into `materials.py`), and `bloodmap.prefab`'s
`alcove_run`, `parapet` and `breakable`. This removes the remaining sources of
project-local drift.

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
