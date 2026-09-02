# Supervisor brief — systemic engine mismatches, and the prompts that close them

Date 2026-09-01. Written by the supervising architect after re-reading the
engine (`NBlood/`, `xmapedit/`, both read-only submodules), the mechanism
curriculum (`maps/blood/mechanism/`, 173 maps + the 981-page manual) and the
newest mechanism the project built (the Aldermack curtain, uncommitted). Every
claim below was measured this session; the engine lines are cited so an agent
can re-read them instead of trusting this note.

The pattern behind the failures is not missing knowledge. The curriculum JSON
already states the laws that the city curtain breaks. The pattern is:

1. **Laws live in JSON and in the readers; the writers do not consult them.**
   `curtain_spec` knows the fin; the tree's `carve` idiom turned the fin's
   slot into portals; nothing between the spec and the compiled map enforces
   the fin's isolation. Gates run in the zoo, not where the mechanism is built.
2. **Readers model the mover; the engine moves the neighbourhood.** `DragPoint`
   drags every wall sharing the vertex across `nextwall`; the swept-state gate
   sweeps only the moving sector's polygon and treats its neighbours as static.
3. **The project has no rendering law.** Which tile the engine actually draws
   on a wall band (`picnum` vs `overpicnum`, one-sided vs two-sided, step bands)
   is never read, so fabric on a two-sided wall passes every gate and shows
   nothing in the walkable band.
4. **The editor's own recipes are unmined.** `xmapedit/src_blood/xmpdoorwiz.cpp`
   writes curtains and slide doors with concrete defaults; the constructors
   carry different defaults and cite the tutorial maps the wizard produced.

Sections: §1 evidence tables · §2 standing rules for every agent · §3 prompts.

---

## 1. Evidence

### 1a. The curtain, three dialects the constructor does not know

| source | leaves | slot interior | fabric walls | flags | extras |
| --- | --- | --- | --- | --- | --- |
| `Vanilla/DOOR-CURTAINS.map` s3 | 1 | **void** (walls 38–40 `next -1`) | one-sided, pic 146, x_repeat 16/1/16 | tip wall 39 `0x4000` | XWALL push on each fabric wall; rx 100; busy 15/15 |
| `Vanilla/DOOR-CURTAINSD.map` s2, s8 … | **2** | void | one-sided | `0x8000` on one tip, `0x4000` on the other | converge from both jambs |
| `Vanilla/DOOR-CURTAINSD.map` **s4** | 2 | **pocket sectors 5 and 6** | two-sided into the pockets; pocket-side walls `cstat 0x51` (block+masked+hitscan) with `over_picnum 1060` | as above | the pocket dialect: fabric is a MASKED wall so it draws in the middle band |
| `E1M1.MAP` s125 (owner-attested) | 2 | void | one-sided 1200/1201/1209/1210 (+XWALL push); **1203–1207 two-sided into s122 with a −65536 ceiling step, pic 146 = over 146, cstat 0x4** | 1200 `0x4000`, 1210 `0x8000` | tx 126 cmd 5 **Link** with trigger_on/off, busy_wave 1, busy 40/25 → s124 amplitude −8 |
| campaign census, 43 maps | 26 one-leaf, 12 two-leaf, 1 three-flag (E2M1 s95) | mostly void; E3M4 has zero-step two-sided fabric (s111 wall 670/684 into neighbouring 614 sectors) | | | 39 sectors of type 614 wearing 146/147 |

`bloodmap.mechanism.curtain_spec` builds the one-leaf void-slot fin only.
The city's `curtains.py` then carved that fin as a hole in the auditorium, so
all eight walls, slot included, became portals into sector 23:

```text
city sector 37 (type 614): walls 276–283 all next_sector 23
  277 flagged 0x4000, pic 146 on 276/277/278 -- two-sided, no masked bit
conformance.measure_curtain: DEVIATES isolation, motion_set [23, 37]
DragPoint closure by coordinate: walls 209, 210 (sector 23) share the tip
```

Engine: `triggers.cpp:817-854 DragPoint` walks `nextwall` and moves every
coincident wall; `triggers.cpp:897-910` a flagged wall drags its own vertex
AND its `point2`'s when that wall carries no flag. The auditorium's hole loop
therefore deforms with the curtain (measured: its area moves 983040 →
1302528 over the travel; it does not invert, so the defect is visual and
topological, not geometric).

### 1b. What the engine draws on a wall

`NBlood/source/build/src/engine.cpp:4940`:
`setup_globals_wall1(wal, (nextsectnum < 0) ? wal->picnum : wal->overpicnum)`.
The middle band of a two-sided wall draws `overpicnum`, and only when the
wall is masked (cstat 16) or one-way (cstat 32); `picnum` draws on the upper
and lower step bands (the lower one swaps to the partner's picnum under cstat
2). Consequences the project never checks:

- city curtain fabric (pic 146, two-sided, not masked): invisible in the
  walkable band; visible only as an upper step if the auditorium ceiling sits
  higher than the curtain's;
- `usage-kinds-v1.json` counts tile 146 as `wall_two_sided` 129 times; those
  are E1M1-style pelmet steps and pocket-masked walls, not middle-band uses —
  the slot vocabulary (`wall_one_sided` / `wall_two_sided` / `over_picnum`)
  conflates storage with what renders.

### 1c. Link → light, verified in the engine

- Sender: every busy proc sends the link per tick when the sector's own
  command is 5 — `triggers.cpp:1198, 1247, 1346, 1374, 1401, 1434`
  (`if (pXSector->command == kCmdLink && pXSector->txID) evSend(..., kCmdLink)`).
  `SetSectorState` never sends ON/OFF for a command-5 sector (`:140, :152`).
- Receiver of type 0: `LinkSector` default branch copies the source busy
  (`:1795-1799`).
- Shade: `sectorfx.cpp:161-166` — when `!shadeAlways && busy`, amplitude is
  scaled by busy, then `GetWaveValue(wave, phase*8 + freq*totalclock, amp)`.
  So a Link-driven dimmer needs `shadeAlways 0`, a wave, an amplitude, and
  its `freq` term still advances the phase with the clock.
- The city wiring (s37 tx 341 cmd 5 → s24 rx 341, amplitude −24, shade
  floor/ceiling/walls) is consistent with this; nothing in the stack READS
  it (`tests/test_attested_constructs.py` expectedFailure "light link as a
  facet").

### 1d. Timing

`trProcessBusy` (`triggers.cpp:2091-2099`) adds `delta*4` per game tick at
`kTicsPerSec = 30`; `AddBusy` delta is `65536 / (busyTime*12)`. Full travel =
`busyTime*3` ticks = `busyTime/10` s. **busyTime is tenths of a second**; the
project's "tenths" is right. Keep it.

### 1e. `Drag`, the unmodelled carry flag

`db.h:161 Drag`; `triggers.cpp:964`: a sprite in a moving sector that carries
neither move flag rides the motion only if `pXSector->Drag` and it stands on
the floor (`floorZ <= bottom`, not a wall/floor sprite). The player is such a
sprite. The project's only mention is the field name in `format.py:76`. This
is the difference between a platform that carries you and one that slides
out from under you, and it changes what "passage through a rotor" means.

### 1f. Loop winding ("inside-out sectors")

Measured this session with a shoelace census (first loop = outer):

```text
campaign      outer positive 13543 · genuinely reversed single-loop sectors: 1 (E6M4 s161, 3 walls)
              (515 "negative first loops" are sectors listed hole-first; 514 of them have a positive biggest loop)
blood-city    259 outer positive, 101 inner negative, 0 against convention
pattern-zoo   93 outer positive, 0 against
turnstile.MAP 4 outer positive, 0 against
motion sweep  no sign flip and no self-intersection in any 614–617 sector of city or zoo (16 steps)
```

So winding is enforced (`construction.py:124`, `planar_layout.py:867`) and
holds. An "inside-out" sector seen by the owner is therefore one of: (a) an
older build (the zoo casket cover inverted in motion before the swept-state
gate); (b) a NEIGHBOUR deformed by DragPoint, which no gate sweeps (§1a,
prompt P3); (c) a two-sided wall whose middle band draws nothing, so the
room behind shows through (§1b, prompt P2); (d) a mechanism drawn in the OFF
pose so the loader snapped it the wrong way (drawn = ON law). The owner is
asked which map and exhibit; until then P3 and P2 cover (b) and (c).

### 1g. The editor's curtain recipe (`xmapedit/src_blood/xmpdoorwiz.cpp`)

`gSMDoorTypes {0 Standard, 1 Curtain}`; curtain = 4 inserted points
(`Start: reqPoints 4`), wall offset 2 gets the move flag (`SetupWalls case 1`),
every added wall gets `xrepeat 8` except offset 3 (`1`), `yrepeat 8`, pic 0,
and — with "Set push trigger flags" on — an XWALL `txID channel, kCmdToggle,
triggerOn/Off/Push`; the sector gets `busyTimeA 8, busyTimeB 6,
interruptable 1, rxID channel` (`SetupSector`); marker1 sits at the door
line, marker0 `height − padding` forward; "double door when possible"
produces the two-leaf form. The constructor uses busy 15/15, no
interruptable, and its own repeat rule. Neither is wrong; they are two
dialects, and only one of them is written down.

### 1h. Tutorials the miner reads as empty

`mechanism-curriculum-v1.json`: 18 of 136 mined maps have no constructs,
stacks or buttons: `0-CLIMBWALL 0-GILL 0-GLASS ENVIRONMENT-ICE SPRITE-DROPS
SPRITE-GAMEPLAY SPRITE-STATNUM WALLS-WINDOWS #FFIELD #MIRROR #NWSMOKE #PITFALL
#SPR18 #SPR22 #SPR6+7 #SPR701 #SPR703 #STNGARG`. Each is a named lesson the
stack cannot read. `Modern/` (45 maps) is excluded on purpose.

---

## 2. Standing rules for every prompt below

Paste this block at the top of each agent prompt.

```text
You are working in D:\Games\DOS\llmapper on branch blood-city-arcade. Read
docs/llmapper_level_understanding_handbook/AGENT_START_HERE.md and
10_AGENT_EXECUTION_PROTOCOL.md first; 09_IMPLEMENTATION_ROADMAP.md is the
single source of truth and you append your status there in the format the
protocol gives.

Evidence rules
- Original maps only (maps/blood/campaign, maps/blood/mechanism/Vanilla and
  the '#' primers, casket.map). Generated maps are scored, never mined.
- Every engine claim cites a file:line in NBlood/source/... or
  xmapedit/src_blood/... . Read the line before citing it. Check whether the
  code sits under NOONE_EXTENSIONS / gModernMap; if it does, say so and use
  the vanilla branch. maps/blood/mechanism/Modern is out of scope.
- The manual is maps/blood/mechanism/xmapedit.pdf; quote page numbers.
- A gate you add is written to FAIL on a known defect first, then to pass.
  A detector that measures nothing reports itself unsupported.
- Build -> read back through the understanding stack -> compare to intent.
  Unread-back building is unfinished work.

Repository rules
- NEVER delete a directory tree: no `git worktree remove`, `Remove-Item
  -Recurse`, `rm -rf`, `rmdir /s`, `git clean`. Never create a junction or
  symlink into maps/, reference/, NBlood/ or xmapedit/; reach the corpus
  with BLOODMAP_CORPUS and absolute paths. maps/ and reference/ are
  irreplaceable and were lost once this way (reports/corpus-recovery-
  2026-09-01.md). If something must be deleted, report it and stop.
- Never launch NBlood or xmapedit. Verification is static checks,
  bloodmap.motion_sim, the XMapEdit observer renders (tools.render_precedent)
  and the suite.
- NBlood and xmapedit are submodules: never stage them, never edit them.
- Never git add -A. Diff each file, then add by name. Corpus files under
  maps/ are never committed.
- Run the suite as: python -m unittest discover -s tests > suite.log 2>&1;
  then grep suite.log for ^Ran and ^OK/^FAILED. Never pipe it through tail.
- Commit only when the suite is green. Commit message ends with
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>

Report format
Finish with: what you measured (numbers), what you built, which gate failed
first and on what, what is still unproven, and the owner questions if any,
appended to reports/owner-review-queue.md with a recommended default.
```

---

## 3. Prompts

Dependencies: P2 and P3 are engine-law readers and go first (they can run in
parallel). P1 needs P2's rule to be honest about visibility, but can start
on topology at once. P4, P5, P6, P8 are independent. P7 is the systemic fix
and goes after P1–P3 so it has something to enforce.

### P1 — The curtain family: read all four dialects, then rebuild the Aldermack's

```text
Task: make the project's curtain match the engine and the corpus, then
rebuild the city's stage curtain so it reads back clean.

Evidence to start from (verify each yourself):
- maps/blood/mechanism/Vanilla/DOOR-CURTAINS.map sector 3: one-leaf fin,
  slot walls 38-40 next_sector -1 (void), tip wall 39 cstat 0x4000,
  fabric pic 146 x_repeat 16/1/16, XWALL push on the fabric, rx 100,
  busy 15/15, markers 336 (type 3, OFF) and 337 (type 4, ON), statnum 10.
- DOOR-CURTAINSD.map: two-leaf curtains (s2, s8, s10 ...) with 0x8000 on one
  tip and 0x4000 on the other; AND sector 4 whose slots are pocket SECTORS
  5 and 6 -- pocket-side walls cstat 0x51 with over_picnum 1060.
- maps/blood/campaign/E1M1.MAP sector 125: two leaves (1200 0x4000, 1210
  0x8000), one-sided fabric with XWALL push, walls 1203-1207 two-sided into
  s122 with a -65536 ceiling step carrying pic 146 = over 146 (the pelmet),
  tx 126 command 5 with trigger_on/off, busy_wave 1, busy 40/25, driving
  s124 (type 0, rx 126, amplitude -8, shade floor+walls).
- Campaign census (43 maps, type 614 wearing 146/147): 26 one-leaf, 12
  two-leaf, 1 three-flag (E2M1 s95). Re-run it; put it in the report.
- xmapedit/src_blood/xmpdoorwiz.cpp DOOR_SLIDEMARKED, type 1 "Curtain":
  the editor's own recipe (4 points, offset-2 flag, xrepeat 8 / 1, yrepeat 8,
  busyTime 8/6, interruptable 1, push XWALLs, marker placement in
  SetupSector). Record it as the EDITOR dialect beside the tutorial one.

Engine laws you must cite: DragPoint closure (triggers.cpp:817-854, 897-910);
drawn geometry is the ON pose and state decides the snap (triggers.cpp
trInit, ~2200-2250); what a two-sided wall draws (engine.cpp:4940).

Deliverables
1. bloodmap/mechanism.py: curtain_spec grows `leaves=1|2` and
   `slot="void"|"pocket"`; a pocket slot is a real region with masked
   pocket-side walls (over_picnum, cstat masked|blocking|hitscan as the
   tutorial has it). Keep the one-leaf void default. Repeats stay authored
   for the CLOSED span.
2. bloodmap/conformance.measure_curtain: accept both leaf counts and both
   slot dialects; the isolation relation becomes "the motion set equals the
   declared members" (void: the fin alone; pocket: fin + its pockets), not
   "the fin alone" -- the curriculum law motion-crosses-storage-boundaries-
   by-default says deforming a declared pocket is normal. Add a relation
   "fabric is visible": every fabric wall is one-sided, or masked with an
   over_picnum, or on a step band with a height difference. Write the
   fabric-visibility check to FAIL on the current city curtain
   (projects/blood-city/level/blood-city-current.MAP sector 37) before
   fixing it.
3. tests/test_attested_constructs.py: fixtures for DOOR-CURTAINS s3,
   DOOR-CURTAINSD s2 and s4, E1M1 s125 -- the reader parses each into its
   dialect (leaves, slot kind, pelmet present, link present).
4. projects/blood-city/level/curtains.py: the proscenium becomes a DOORWAY
   region between the house and the stage (the zoo's idiom, stalls.py
   curtain stall), not a hole carved in the house. Slot void, fabric
   one-sided, XWALL push on the fabric, two leaves if the Aldermack's
   proscenium is wider than the campaign's one-leaf spans (measure them).
   Keep the Link to the stage light.
5. projects/blood-city/level/build_skeleton.py: run the conformance sweep
   (projects/pattern-zoo/sweep.py generalised, or bloodmap.conformance
   directly) over every mechanism in the city build, and fail the build on
   a deviation. This is the missing gate; it must fail on the old curtain
   first.
6. Read back: self-read (type set, rx/tx as declared), swept-state
   (motion_sim.blood_sweep over the fin AND its DragPoint neighbours -- if
   P3 has landed use it, else compute the closure by coordinate as the
   supervisor did), motion-set, state-preview: render the house at OFF and
   ON with tools.render_precedent and put both frames in
   projects/blood-city/reports/wave1b-review.md, with the shade numbers of
   the stage sector in each pose.
7. Zoo: a two-leaf exhibit beside the one-leaf one; regenerate the zoo;
   conformance test forces it.

Do not commit the submodule pointers. Report per the standing rules.
```

### P2 — A rendering law: which tile the engine draws on which band

```text
Task: give the project a reader for what the Build renderer actually shows
on a wall, and turn it into a gate and a re-mined usage table.

Engine: NBlood/source/build/src/engine.cpp. Start at line 4940
(`(nextsectnum < 0) ? wal->picnum : wal->overpicnum`) and read the wall
drawing path around it and the masked-wall path near 7231. Establish and
cite, for a two-sided wall: which band draws picnum (upper step; lower step
unless cstat&2 swaps to the partner's picnum), which draws overpicnum
(middle, only if cstat&16 masked or cstat&32 one-way), what cstat&1
blocking and cstat&64 hitscan do without a drawn band, and what a
one-sided wall draws. Also cite how the sky/parallax and mirror cases
bypass this (rules_blood already has the mirror tile).

Deliverables
1. bloodmap/render_slots.py: for every wall, the list of (band, tile,
   reason) triples the engine would draw from each side, using the two
   sectors' floor/ceiling z. Pure function over a disk map.
2. A rule in bloodmap/rules_blood.py: "a tile authored on a wall is drawn
   somewhere" -- a wall whose picnum is not sky, not the mirror tile, and
   draws on no band from either side is a finding. Severity from the
   campaign violation rate, as the other rules do. It must FAIL FIRST on
   projects/blood-city/level/blood-city-current.MAP sector 37 walls 276-278
   (fabric 146 on unmasked two-sided walls); report how many other city and
   zoo walls it catches.
3. Re-mine knowledge/blood/design/usage-kinds-v1.json by RENDERED slot
   (one_sided_middle, two_sided_upper, two_sided_lower, masked_middle,
   floor, ceiling, sprite kinds) instead of storage slot; keep the old table
   beside it and diff. Tile 146's 129 "wall_two_sided" uses are the test:
   say how many are steps (E1M1 1203-1207 style) and how many masked
   middles.
4. Fold the rendered-slot vocabulary into the usage-kind gate in the zoo
   and city builds.

Cite lines; write the gate to fail first; report the campaign rate.
```

### P3 — The swept-state gate must sweep the DragPoint closure

```text
Task: bloodmap/motion_sim.blood_sweep moves only the mover's own polygon
and sweep_health treats every neighbour as static. The engine does neither:
DragPoint (NBlood/source/blood/src/triggers.cpp:817-854) moves every wall
that shares the vertex across nextwall chains, and a flagged wall also
drags its point2 when that wall has no flag (:897-910). The gate therefore
cannot see a neighbour that inverts, self-intersects or overlaps during a
travel. The curriculum law motion-crosses-storage-boundaries-by-default
(knowledge/blood/design/mechanism-curriculum-v1.json) says this is the
normal case, so the gate is blind to the normal case.

Deliverables
1. motion_sim.drag_closure(level, sector_id): the set of (wall, vertex)
   pairs DragPoint would move for each flagged wall, walking nextwall both
   ways exactly as the engine does (do not use coordinate coincidence; use
   the nextwall chain, and say when the two disagree -- that disagreement
   is itself a map defect worth a rule).
2. motion_sim.blood_sweep returns frames for EVERY loop touched by the
   closure, keyed by sector and loop; sweep_health evaluates all of them:
   sign flip of signed area (inversion), self-intersection, overlap with
   loops that do not move. Write it to FAIL FIRST on a fixture you build
   with PlanarLayout: a slide-marked strip whose flagged wall is shared
   with a thin neighbour so the neighbour inverts at busy 1.
3. Run it over the curriculum's 256 swept mechanisms and the campaign's
   slide/rotate sectors: how many deform a neighbour, how many neighbours
   invert or self-intersect at any pose (report the list -- these are the
   'inside-out' sectors the owner has seen if any exist), and how many are
   the fin/isolation technique. Add the numbers to
   reports/blood-mechanism-curriculum.md.
4. Wire the closure sweep into the zoo sweep and the city build gate.

Vanilla only (skip gModernMap branches, cite that you did). Fail first.
```

### P4 — `Drag`: what a moving sector carries

```text
Task: model the XSECTOR Drag flag, which the project stores
(bloodmap/format.py:76 "drag") and never reads.

Engine: NBlood/source/blood/src/triggers.cpp:929-975 TranslateSector's
sprite loop -- kStatMarker/kStatPathMarker never move; cstat&8192 moves
with, cstat&16384 against; otherwise ONLY if pXSector->Drag and the sprite
stands on the floor (GetSpriteExtents, floorZ <= bottom, not cstat&48).
Confirm that the player sprite takes this path (player.cpp / actor.cpp:
find where the player's position is updated by a moving sector) and cite.
Also read ZTranslateSector for the vertical case and say whether Drag
matters there.

Deliverables
1. bloodmap/effects.py: payload() and physical_effects() report drag:
   'carries standing bodies' vs 'slides under them'; design_object uses it
   (a conveyor, a train, a rotating platform carry; a door does not).
2. Census over campaign + Vanilla curriculum: Drag on 614-617 sectors by
   type and by the design object the embedding assigns; MACHINERY-TRAIN,
   MACHINERY-CONVEYOR, MACHINERY-1WAYVEHICLE, MACHINERY-CARPATH,
   E1M4 151/314 are the checks. Put the table in a report.
3. Constructors: lift, turnstile, sliding_gate, planar_door, curtain declare
   Drag explicitly in their spec, with the corpus default per family.
4. The turnstile question: with the measured Drag of E1M4 151/314, state
   what happens to a body inside the rotor (rotated with it, or pushed by
   the blades). This feeds the passage argument in
   REASSESSMENT-ARCHITECT-2026-09-01.md §3c; do not claim passage, state
   the mechanics with citations.

Fixtures for each census claim; fail-first for the reader.
```

### P5 — The 18 tutorial maps the miner cannot read

```text
Task: the curriculum mine (knowledge/blood/design/mechanism-curriculum-v1.json,
bloodmap/curriculum.py) returns nothing for these maps in
maps/blood/mechanism: Vanilla/0-CLIMBWALL 0-GILL 0-GLASS ENVIRONMENT-ICE
SPRITE-DROPS SPRITE-GAMEPLAY SPRITE-STATNUM WALLS-WINDOWS, and the primers
#FFIELD #MIRROR #NWSMOKE #PITFALL #SPR18 #SPR22 #SPR6+7 #SPR701 #SPR703
#STNGARG.

For each map: read it field by field (llmapper inspect / dump), find its
lesson in xmapedit.pdf (quote the page), find the engine code that
implements it (cite), and decide honestly which of these it is:
(a) a mechanism the stack should read -> write the reader in
    bloodmap/effects.py or curriculum.py, a fixture in
    tests/test_attested_constructs.py, and a law entry only if the engine
    line supports it;
(b) a surface/material lesson (0-GLASS, WALLS-WINDOWS, #MIRROR) -> record
    the recipe to the field in knowledge/blood/design and hand it to the
    rendering law (P2) as a test case;
(c) a lesson with no map-level construct (SPRITE-STATNUM) -> say so, with
    what the map teaches, and mark it 'no mechanism' in the curriculum.

Do not invent a construct to make a map non-empty. Regenerate the
curriculum JSON and reports/blood-mechanism-curriculum.md; the totals
must change only by what you read. Modern/ stays excluded.
```

### P6 — XMapEdit as the dialect authority

```text
Task: mine the editor's source for what it WRITES, and diff it against the
constructors. The tutorials in maps/blood/mechanism were made with this
editor, so its defaults are the dialect the curriculum speaks.

Source: xmapedit/src_blood/ -- xmpdoorwiz.cpp (door wizard: slide marked
door, curtain, rotate door, reverse position), xmptrig.cpp (what the
trigger/channel dialogs write), aadjust.cpp (auto texture alignment),
maproc.cpp and xmpmisc.cpp (map processing helpers), nnexts*.cpp is the
Modern dialect and is out of scope except to confirm a function is modern.

Deliverables
1. knowledge/blood/design/editor-dialect-v1.json: for each wizard/dialog,
   the fields it writes with values and the source line: busyTime 8/6 and
   interruptable 1 for slide doors, xrepeat 8 / 1 and yrepeat 8 on inserted
   walls, marker placement (SetupSector: marker1 on the door line, marker0
   height-padding forward), push XWALL wiring (kCmdToggle, on+off+push),
   channel allocation (findUnusedChannel, kChannelUser), the rotate door's
   pivot and angle, the auto-align rules.
2. A table of disagreements against bloodmap/mechanism.py, doors.py,
   motion.py defaults (CURTAIN_*, BUSY, leaf repeats, interruptable,
   wave). Grade each: editor default / tutorial value / campaign modal
   value (measure the campaign one). None of the three is 'right'; record
   all three and make the constructors take the campaign modal value by
   default with the others selectable.
3. knowledge_index entries graded EDITOR provenance (new grade; say in the
   README what it means: what the tool writes, not what the corpus does).
4. Where the editor and the engine disagree (e.g. a wizard writing a field
   the engine ignores), that is a finding; list them.

No edits inside xmapedit/. Cite lines.
```

### P7 — Round-trip closure at the constructor, not the gallery

```text
Task: Phase 11 item 3 in 09_IMPLEMENTATION_ROADMAP.md ("every constructor's
test builds, reads back through effects/conditional, and asserts the parse
equals the grammar sentence the constructor claims") is done only for the
zoo. The city built a curtain that fails conformance and no gate said so,
because gates live in projects/pattern-zoo/sweep.py and selfread.py.

Deliverables
1. bloodmap/readback.py: one function taking a built disk map and a list of
   declared mechanism sentences (the *_spec dicts plus placement: sector
   id, members, wiring, drag, visibility) and returning structural
   equality or a typed diff, using effects, conditional, conformance,
   motion_sim (with P3's closure if landed), render_slots (P2 if landed),
   and the state-preview measurement in reports/zoo-state-check.json's
   generator.
2. Every public constructor in bloodmap/mechanism.py, doors.py, glass.py,
   aperture.py, street.py gets a unit test that builds it in a minimal
   PlanarLayout AND (for the ones with a tree placer in blood-city) in a
   minimal levelprog tree, reads back, and asserts equality. A constructor
   without such a test fails a registry test the way the zoo's
   conformance test fails a constructor without an exhibit.
3. projects/blood-city/level/build_skeleton.py and
   projects/pattern-zoo/build_zoo.py call readback over their manifests
   and fail on a diff. Fail first on the current city curtain.
4. Make the three expectedFailure fixtures in
   tests/test_attested_constructs.py the acceptance test: the light link
   as a facet (P8), the stack-linked casket, the wall-level route. Report
   which of the three pass after this work and why the rest do not.

This is the on-ramp to MechanismDecl (roadmap Phase 13): the sentence you
compare against is the schema. Keep it a dict with a documented shape; do
not build the typed layer yet.
```

### P8 — Read the Link as a facet of the mechanism

```text
Task: the reader cannot say "the room light follows the curtain" although
E1M1 s125/s124 and the city's s37/s24 are wired for it. Engine facts to
cite: every busy proc sends kCmdLink each tick when the sector's command is
5 (NBlood/source/blood/src/triggers.cpp:1198, 1247, 1346, 1374, 1401,
1434); SetSectorState sends no ON/OFF for such a sector (:140, :152); a
type-0 receiver copies the source busy (LinkSector default, :1795-1799);
DoSectorLighting scales amplitude by busy when shadeAlways is 0
(sectorfx.cpp:161-166) and still advances the phase with freq*totalclock.

Deliverables
1. bloodmap/effects.py (or conditional.py): a facet 'drives' on a mechanism
   record: channel, command, receivers, and per receiver what busy does to
   it (dimmer via shade wave; another mover via its busy proc; a counter).
   Report the receiver's required fields and flag a receiver that cannot
   respond (shadeAlways 1 with a Link; a type-0 sector with no wave).
2. tests/test_attested_constructs.py: the expectedFailure
   test_the_light_link_is_read_as_a_facet_of_the_mechanism becomes a
   passing test; add DOOR-CURTAINS s21 -> s20 and DOOR-CURTAINSD s18 as
   fixtures.
3. Run over the campaign: how many mechanisms transmit a Link, to what
   kinds of receiver; add to reports/blood-conditional-topology.md.
4. Verify the city's stage light reads as 'follows the curtain', and say
   what the shade does at OFF and ON with the numbers.
```

---

## 4. What the supervisor did not do

- Did not fix the city curtain, the visibility gap or the sweep; those are
  P1–P3 and each needs a gate written to fail first.
- Did not settle which "inside-out" case the owner saw; §1f lists the four
  candidates and P3/P2 cover the two the current builds could still hide.
- Did not mine Modern/. Keep it out until the vanilla dialect is closed.

---

## 5. What the XMapEdit manual adds (`maps/blood/xmapedit.chm`, read 2026-09-01)

The CHM is the same third-edition manual as the PDF, 319 pages decompiled
(`hh.exe -decompile` or 7-Zip). Read against the project's representation,
it offers five things the project does not have, and corrects one claim.

**5a. The Xsystem is a state machine first, geometry second.** The manual's
model of every Xobject: four functions (send/receive messages; hold a State;
interpret State by Type; detect physical triggers) over a hierarchy Type ›
Channel › State › Command › Trigger › Flag. Commands come in named groups
(State: OFF r=0, ON r=1, State r=s, Toggle r=1-r, NotState r=1-s; Link:
master/slave; Lock: Lock/Unlock/ToggleLock; Stop: StopOff/StopOn/StopNext;
numeric 64+ for secrets and messages). Flags have precise semantics the
readers do not model as first-class: **Decoupled** (interaction transmits
but does not control the object), **Locked** (ignores interaction, still
obeys messages), **1-shot** (does not apply to commands from outside),
**Interruptable** (reverses mid-travel), **Player Only**, **RestState +
WaitTime** (auto-return). `bloodmap.motion` has the command numbers and
`conditional.rest_state`; nothing reads Decoupled/Locked/1-shot as a
topology fact. A locked door with a remote unlock is a different progression
sentence from a pushed door, and today both parse the same.

**5b. An operations vocabulary.** The editor's own verbs (3.3/3.4): white
vs red sector; five red-sector typologies (adjacent interior, adjacent
exterior, child, island, split); K / Shift+K marks a wall or one face for
motion; F sets the first wall (slope orientation and panning direction); X
slope auto-align; M / Right-Shift+M / 1 for masked, one-sided masked and
one-way walls; F9 Sector Tricks (step height, light phase, z phase, clean
matching); Alt+F3/F4 set OFF/ON heights; Alt+F2 reverse door position; Tab
copies attributes; the Door Wizard, Arc Wizard, Loop Split. This is the
authoring grammar the tutorials were written in. The project's constructors
name none of it; a MechanismDecl whose primitives are these verbs would read
like the manual and diff against it.

**5c. Five door-frame mediations, named by the manual (3.8).** Basic frame
(door not inside the frame; "red sectors cannot pass through other ones"),
door within the frame (frame split so the door fits), wide frame (door is
room height, no frame), sprite frame, true sector frame (E1M1: red sector
pegged to the white wall). This is an owner-independent source for the
mediation taxonomy (frame/seat/holder) and it ranks them by campaign use.

**5d. A 791-tile human taxonomy with sign texts** (Texture List, tiles
< 800). Owner anchors cover 104 tiles; 76 overlap; 715 manual tiles have no
anchor. The manual gives categories the anchors lack (Curtains 48/145/146/
147/159; Fabric; Facades 380–401; Metal masks 142; Stone masks 113/114;
Windows 10/144/263–266/347/389/451/482/516/569; Metal door tracks 115/195/
448 — the jamb tiles the aperture grammar mined) and the TEXT of 40 sign
tiles (14 "brain storage", 74 "Kmarché", 225 "Pandemonium Shadow Show", 646
"Miskatonik Station", 741 "Cask of Amontillado Pub and Grille" …). It also
disagrees with anchors in a few places worth a look: 144 manual Windows vs
owner "wooden lattice wall"; 142 manual Metal masks vs owner "skull
fireplace"; 502 manual Grates vs owner wall. Grade: MANUAL provenance,
never overwriting OWNER, beside it.

**5e. The Preview Mode is an in-editor oracle** (3.6, `xmapedit/src_blood/
preview.cpp`): it runs trigger sequences, sector motion, ROR and explosions
without the game, with LMB = cmd State, RMB = cmd Off, MMB = cmd On. The
project already builds an observer against the editor (`xmapedit/src_blood/
observe/`); driving PREVIEW_MODE::Process headlessly would give a
state-machine oracle that the game's `-bot` cannot (it refuses rotors). Not
a driver for passage, but a driver for "does the wiring fire".

**One correction.** The manual says "if both Going ON and Going OFF are
disabled but TX ID is not zero, both are enabled automatically after
saving". In the source that fixup exists only on the Modern path
(`xmapedit/src_blood/nnexts.cpp:1585` inside `nnExtInitModernStuff`; NBlood
`nnexts.cpp:1198`, same guard). Vanilla maps get no such rescue, so the
wave-1 finding (secret total declared with tx 1 / command 66 and no
trigger_on never fires) stands.

**Also confirmed by the manual:** busyTime "10 = 1 second"; amplitude
negative = brighter; markers rotate a slide only in multiples of 1024;
Drag "drags the character or objects with physics" (FX dialog, §1e); the
sky family {2500, 3491, 3678} + 4037 (Cryptic Passage); ROR limits (8
see-through in editor, 16 in game; 64 stack sprites); "never place two ROR
sectors so the player sees both at once" (the E1M1 s65/s90 workaround's
reason); "never draw a red sector within a link sector".

### P9 — The manual as a graded knowledge source

```text
Task: mine maps/blood/xmapedit.chm (decompile with `hh.exe -decompile` or
7-Zip; the CHM's .htm pages carry <title>) into knowledge/blood/design as
MANUAL-grade entries, never overwriting OWNER entries, and put it in front
of the readers where it changes a reading.

Deliverables
1. knowledge/blood/design/manual-textures-v1.json: the Texture List parsed
   (tile -> category, description, sign text), plus a diff table against
   owner-anchors-v1.json: overlap 76, manual-only 715, and every
   disagreement (start with 142, 144, 502) queued for the owner in
   reports/owner-review-queue.md with a recommended default.
2. knowledge/blood/design/manual-xsystem-v1.json: the Xsystem model as data
   -- command groups with their r= formulas, trigger flags with the
   manual's semantics, reserved channels (RX 7/8/9/10/15/16/80/81; TX
   1..5, 90..97), sector types with the manual's example maps, wave names
   for busy and for lighting, key ids, damage types. Cross-check each
   against bloodmap/blood_types.py and the engine; where the manual and the
   engine disagree, the engine wins and the disagreement is recorded.
3. bloodmap/conditional.py: read Decoupled, Locked, 1-shot, Interruptable,
   Player Only, RestState/WaitTime as first-class facts on a mechanism
   record; a locked-until-unlocked door becomes its own progression edge
   kind. Fixture: a campaign door that is Locked with a remote Unlock (find
   one; E1M4 or E2M2 likely); fail-first on the current parse that treats
   it as pushable.
4. knowledge: the five door-frame mediations (3.8) as named templates with
   a campaign census of each (which frame idiom each campaign door uses);
   hand the counts to the aperture grammar.
5. A short editor-verbs vocabulary (5b) as a document in
   docs/llmapper_level_understanding_handbook/, cross-referenced to the
   xmapedit source functions that implement each verb (edit2d.cpp,
   edit3d.cpp, xmpdoorwiz.cpp, xmparcwiz.cpp), for MechanismDecl's
   primitive names.
6. Note in the README that the Modern-only trigger-flag fixup is NOT a
   vanilla guarantee, with the two source lines.

Do not launch the editor. Cite pages by their .htm title and source lines.
```

---

## 6. Owner walk, 2026-09-02: texture continuity and the "sunken rectangles"

Two observations from the owner, both measured before being turned into
prompts.

### 6a. Texture continuity across adjacent walls

The editor's own law (`xmapedit/src_blood/xmpmaped.cpp:3024-3050 AlignWalls`,
`:3070-3140 ED32_AutoAlignWalls`): for consecutive walls wearing the same
tile, `xpanning[next] = (xpanning[this] + xrepeat[this]*8) % tilesizx`,
`yrepeat[next] = yrepeat[this]`, and `ypanning[next] = ypanning[this] +
((zpeg[next] - zpeg[this]) * yrepeat) / (tilesizy*8)` where the peg z is the
ceiling or, under cstat&4, the floor (`GetWallZPeg`, `:2991`). With flag
0x04 the editor also carries the texels-per-unit quotient (`getlenbyrep`,
`fixxrepeat`) so scale stays constant along a run. Bottom-swapped walls
(cstat 2) align against `nextwall` instead.

Measured with exactly that formula on consecutive same-tile wall pairs
(43 campaign maps vs the two built maps; ART sizes from `reference/blood`):

```text
                            campaign          blood-city        pattern-zoo
collinear solid-solid       n=6760  x 95% y 99%   (too few)         (too few)
bend      solid-solid       n=20021 x 70% y 99%   n=209  x 74% y 100%  n=130 x 42%
bend      portal-portal     n=28216 x 31% y 93%   n=768  x 55% y 100%
bend      solid-portal      n=13366 x 34% y 49%   n=198  x 92% y 55%   n=238 x 61%
collinear solid-portal      n=4442  x 81% y 40%   n=73   x 95% y 78%   n=114 x 42%
reflex    solid-portal      n=2836  x 25% y 55%   n=24   x 0%  y 0%
collinear portal-portal     n=3588  x 58% y 85%   n=16   x 38% y 100%
```

What this says. The city has almost no collinear solid-solid joins: its
straight faces are cut by portals at every doorway and window, so the
largest class is `bend portal-portal` (768 pairs), which is the interior
shop-front and arcade condition — continued 55%. `align_wall_runs`
(bloodmap/texture_align.py) deliberately does not carry a run between two
portal walls except for the one opted-in concourse sector, and it carries
only x; y across a step is left to the floor-anchored y pass, which anchors
each wall to its OWN sector's height and therefore breaks the y phase at
every kerb, sill and lintel (solid-portal y 55%, reflex 0/24). The zoo is
worse on the plain case: 42% where the campaign continues 70%.

### 6b. The rectangles sunk into the street

The carriageways are the culprit. E3M1 (the only campaign city street):
every pavement is tile 4 (11/11), every kerb step is 2048, and the kerb
face wears facade stone (401, 400, 393, 414, 380). Gravesend today:

```text
sidewalk tile 4 sectors        0        (bloodmap/street.py promises it; nothing wears it)
roadway s74  2816 x 7424       tile 352 inside a tile-352 street region
roadway s75  2816 x 6912       same
roadway s165 3072 x 14848      same
kerb step heights              2048 x16, 1536 x12, 3072 x12, 1024 x4   (E3M1: 2048 only)
kerb face tiles                417 x25, 384, 28, 2293 (the glass base tile), 380
```

So a roadway is a four-wall rectangle of the same tile as its surroundings,
dropped 2048, with brick or glass on the drop: it reads as a pit because it
is one. Two more pits: `s136`, a single-tier 1024x1024 water hole (tile 1120)
sunk 3052 into the market roadway (the `basin` setpiece with one tier is a
hole, not a fountain), and `s85`, the works-yard manhole: a 1024 square
sunk 1024 with a see-through ROR floor and a bubble generator, no grate.
The light pools are NOT the problem: all nine are flush (delta 0) and only
differ in shade.

### P11 — Texture continuity as the editor defines it

```text
Task: make wall texture continuity in built maps match the campaign, class
by class, using the editor's own alignment law, and gate it.

Law to port, cited: xmapedit/src_blood/xmpmaped.cpp AlignWalls (:3024-3050),
ED32_AutoAlignWalls (:3070-3140), GetWallZPeg (:2991), getlenbyrep /
fixxrepeat (xmpmaped.h:279-290). Read them; do not re-derive.

Deliverables
1. bloodmap/texture_align.py: replace the x-only run carry with a port of
   AutoAlignWalls semantics: x panning, y repeat, y panning with the z-peg
   offset, bottom-swapped walls via nextwall, optional scale carry
   (lenrepquot). A RUN is defined by loop geometry (the campaign's own
   break: reflex > 100 degrees), NOT by wall kind: solid-portal and
   portal-portal joins inside a run are carried, because the visible band
   of a portal wall is the same tile continuing. Keep a per-sector opt-out
   for deliberate restarts.
2. The floor-anchored y pass must not fight the run carry: anchor once per
   run (its first wall), then propagate by the peg formula.
3. Gate: a continuity measure by class (collinear/bend/reflex x
   solid-solid/solid-portal/portal-portal) reported as rates beside the
   campaign's, and a rule that fails when a class in a built map falls
   more than 15 points below the campaign rate with n >= 30. Write it to
   FAIL FIRST on pattern-zoo.MAP (bend solid-solid 42% vs 70%) and on the
   city's reflex solid-portal joins (0/24).
4. Apply to the zoo and the city builds; re-render four frames the owner
   can compare (a facade with a door in it, an arcade shop-front run, a
   kerb, an interior corner) before/after with tools.render_precedent.
5. Report the table above re-measured after the change, the Ran line, and
   any join class where the campaign itself is below 50% (those are
   deliberate restarts and must not be "fixed").
```

### P12 — Street anatomy that reads as a street, and no pits

```text
Task: the three carriageways in Gravesend read as rectangular pits because
they are the same tile as their surroundings, dropped 2048, with brick on
the drop and no pavement. Make the street anatomy match E3M1 to the field,
and remove or redesign the two real pits.

Evidence (measure again yourself): E3M1 pavements tile 4 (11/11 walls
above a 352 road), kerb step 2048 without exception, kerb faces 401/400/
393/414/380. City: 0 sectors wear tile 4; steps 1024..3072; faces 417/384/
28/2293/380; roadways s74, s75, s165 are 4-wall rectangles inside a
tile-352 region.

Deliverables
1. bloodmap/street.py + projects/blood-city/level/streets.py: a run is
   roadway + two SIDEWALK SECTORS (tile 4, band 2048) + kerb; the sidewalk
   sectors must exist and wear tile 4, the step is exactly 2048, the kerb
   face (the pavement-side wall's picnum, which draws the lower step) wears
   a facade-stone tile from the E3M1 set, chosen per district material.
   Where a run is too narrow for the anatomy, do not drop a bare rectangle:
   leave it pavement, as wave 1 already does for the 3072 lanes.
2. Carriageways are continuous strips: where the seam decision (owner
   queue) blocks a run, the roadway ends at a kerb return, not mid-block.
3. The market water hole s136: either the full basin (concentric tiers to
   water, as setpieces.basin is meant to build) with a rim you can see, or
   nothing. The works-yard manhole s85: a grate over the ROR hole (floor
   sprite or maskwall on the E1M1 sewer-grate precedent; measure the
   campaign's manholes first) so the sinkhole reads as a manhole.
4. Gate: a rule "a sunken sector on a walkable surface declares what it is"
   -- every sector lower than all its neighbours by 512..4096 on a
   street/plaza tile must be a declared roadway (with its sidewalks and
   kerb faces), basin, manhole or stair; anything else is a finding. Fail
   first on the current city (s74/s75/s165 undeclared as anatomy, s136,
   s85).
5. Rebuild, read back (bloodmap.readback), render the west street and the
   market square before/after, and report the E3M1 comparison table.
```

### 6c. Owner additions, 2026-09-02: windows are held, crate tops are cut, and the fix is representational

Three measurements behind the owner's three remarks.

**The shop window is not on the facade.** E6M1's four glass walls (22, 373,
381, 490; over_picnum 266, cstat 0xd5, XWALL) all lie between a **display
recess sector** and the shop interior: s4 and s64 are 4096 x 512 four-wall
sectors, floor 81920 against the shop's 90112 (a sill 8192 up), ceiling
36864 against −40960, open to the street on their outer side. The pane is
the recess's INNER face; the facade material runs over the recess mouth as
a lintel band. So a shopfront is `facade wall run → recess sector (512
deep, raised sill, lowered head) → pane → interior`, four sectors deep, and
the facade texture never meets the glass. The city glazes spans on the
facade line itself (`glaze` over the room's own face).

**Crate tops.** 247 raised crate-top sectors in the campaign (floor tiles
95/298/375/452/456/462): 165 use the floor's expanded bit (floorstat 8),
146 carry a floor panning, 90 have their first corner on the tile grid, 11
use first-wall-relative alignment (floorstat 64). The city's 11 crates: none
expanded, none panned, none on the grid, all world-aligned defaults — so a
1024 crate that does not sit on a 1024 world grid wears a cut tile. The
campaign fits the tile to the crate; the city fits the crate to nothing.

**Why the current representation cannot get this right.** Wall texture
fields are set per wall (`planar_layout.py:2526` derives x_repeat from
length/128; panning is patched afterwards by `texture_align` passes in
wall-list order). There is no object that says "this material is projected
onto this run from this origin at this scale". The editor's `>` key
(AutoAlignWalls with flag 0x01, recursing through nextwall) is a
*sequential* fix for a *global* fact; the campaign mappers used it after
drawing. A generator can state the fact directly.

### P11 (revised) — Texture frames: position textures in world space, derive Build fields

```text
Task: give the source representation a MATERIAL MAPPING per wall run and
per surface, resolve it in the compiler with the editor's alignment law in
closed form, and gate continuity by class against the campaign.

Laws to cite: xmapedit/src_blood/xmpmaped.cpp AlignWalls (:3024-3050),
ED32_AutoAlignWalls (:3070-3140, the '>' key with flag 0x01),
GetWallZPeg (:2991), getlenbyrep/fixxrepeat (xmpmaped.h:279-290); for
floors the Build floor mapping (engine.cpp: world units per texel, the
expanded bit floorstat 8, relative-to-first-wall floorstat 64, panning).
Measure E6M1's shopfront (walls 22/373/381/490, sectors 4/64/52/50) and
the 247 campaign crate tops before designing.

Deliverables
1. bloodmap/texture_frame.py (or inside levelprog): WallRunFrame =
   (material tile, u-origin as a world point on the run, texels per unit,
   v-origin as a world z, flip) attached to a RUN, where a run is the
   maximal chain of walls sharing a material with turns < 100 degrees,
   portal walls included. SurfaceFrame = (tile, anchor: world | object
   corner | first wall, scale: normal | expanded, panning) for floors and
   ceilings. Both are source-level objects; PlanarLayout and levelprog
   carry them; the compiler derives x_repeat, x_panning, y_repeat,
   y_panning, cstat flip bits, floor_stat and floor panning from them in
   CLOSED FORM from world coordinates (x_panning = (u(wall start) −
   u0) mod tilesizx, y_panning from (zpeg − v0) * y_repeat / (tilesizy*8)),
   so the result is order-independent and portal cuts change nothing.
   `>` semantics become a test: applying AutoAlignWalls to a compiled run
   must change nothing.
2. Replace the per-wall guesses (planar_layout.py:2526, texture_align's
   floor-anchored pass and align_wall_runs) with frame resolution; keep the
   old passes only as a fallback for walls no frame covers, and count them.
3. Shopfronts: the glass constructor (bloodmap/glass.py) takes a HOLDER
   RECESS: 512 deep, sill and head per E6M1's measured offsets, pane on
   the inner face; the facade run frame continues across the recess mouth.
   Re-glaze the city's six spans this way; the zoo's SHOP WINDOW exhibit
   follows.
4. Crate tops and every raised solid: an object-anchored SurfaceFrame by
   default (tile grid starts at the object's own corner; expanded bit when
   the campaign's crate class uses it, measured); verify all 11 city crates
   wear an uncut top.
5. Readers: `bloodmap.render_slots` or a sibling computes each wall's
   world u-origin (x_panning − u(start)) so runs can be RECOVERED from an
   original map; the continuity census by class (collinear/bend/reflex x
   solid/portal) becomes a rule that fails when a built map's class rate
   falls 15+ points under the campaign's with n >= 30. Fail first on
   pattern-zoo.MAP (bend solid-solid 42% vs 70%) and the city's reflex
   solid-portal joins (0/24).
6. Rebuild zoo and city; render before/after pairs of: a facade with a
   door and a window, an arcade shop-front run, a kerb, an interior
   corner, a crate stack; report the class table re-measured and the Ran
   line. Do not "fix" classes where the campaign itself restarts (reflex
   joins, portal-to-portal bends under 35%): those are deliberate.
```

### 6d. The law behind the holder sector: one wall record, one frame (owner, 2026-09-02)

A Build wall record has exactly one set of texture fields — `picnum`,
`over_picnum`, `x_repeat`, `x_panning`, `y_repeat`, `y_panning`, the flip
bits. The step bands (`picnum`) and the masked middle (`over_picnum`) SHARE
the repeat and the panning. So a material that needs its own scale and
phase — a pane fitted to its opening, a door leaf, a grille — cannot live on
a record that also carries a facade run: whichever frame wins, the other
is wrong, and they fight. The only way to give a material its own record
is a sector boundary: a HOLDER (recess, reveal, porch, leaf sector) whose
return walls end the facade run at the jambs and whose own wall carries
the insert. The facade's continuity across the opening is then a property
of the facade's FRAME (world-anchored), not of the records the opening
happens to cut.

The owner's formulation: **a building's facade provides holes and has its
own aligned texture; shopfronts, windows and doors are put INTO the
holes.** Facade = Surface with openings. Insert = a construct that owns
its sectors and its frames. The opening mouth records (two-sided to the
holder) carry the facade frame in their bands, pegged so the upper band
continues (cstat 4 where E3M1 does it); the insert's records carry the
insert's frame.

Audit against this law (masked two-sided records, where the overlay sits):

```text
                         held by a holder sector      between two rooms
E6M1 shop glass          4/4 (recess on the street side, run continues past)
E3M1                     16/16
E1M1                     14 held; 18 between rooms with their own phase (interior grates: they END runs deliberately)
blood-city glass         24 records: the "holder" is a DISPLAY BOX behind; the pane sits on the facade line,
                         and glass.glaze overwrites x_repeat/y_repeat/y_panning on BOTH records of the pair
                         (bloodmap/glass.py:140-145) -- the binding the owner describes, in code
blood-city doors         13/13 have reveal sectors on both sides (door_frames): already lawful
aperture.maskwall_panel  sets over_picnum + cstat only and inherits the host record's scale and
                         phase: lawful only when the host is a holder record
```

Gate to add (P13): **no record carries two frames.** A wall record with a
masked overlay whose `picnum` continues a surface run is a violation; an
insert may only sit on records owned by its holder; a two-sided record
whose `picnum` continues a run must be an opening mouth (bands pegged to
the run's v0), never an insert. Fail first on the 24 city panes.

### P13 addendum — facades with holes, inserts with holders

```text
Add to P13, before re-glazing: implement the owner's model. A FACADE is a
Surface (architect review §3) with its own WallRunFrame and a list of
OPENINGS (rectangles in the facade plane). An INSERT (shopfront = recess +
pane; window = reveal + glass or grille; door = reveal sectors + leaf
sector + jambs, which the city already builds) is a construct bound to
one opening; it owns its sectors and its frames and never writes fields
on a record it does not own. The compiler: facade records take the facade
frame; opening-mouth records (two-sided into the holder) take the facade
frame in their bands with the peg chosen so the upper band continues
(cstat 4 per E3M1's headers, measured); holder records take the insert's
frame. glass.glaze must stop writing x_repeat/y_repeat/y_panning on the
facade side of a pair: it glazes only records the holder owns.
aperture.maskwall_panel likewise requires a holder record. Gate: "no
record carries two frames" as in brief 6d; fail first on the 24 city
panes; report how many facade-line records lost a competing frame.
```
