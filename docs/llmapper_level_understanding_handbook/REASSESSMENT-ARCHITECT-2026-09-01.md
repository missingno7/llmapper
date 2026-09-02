# Architect reassessment — 2026-09-01

A fresh reading of `HANDOFF-ARCHITECT-2026-09-01.md`, checked against the
repository rather than taken on trust. It keeps what the handoff got right,
corrects what it got wrong, and proposes a different order of work. It is a
proposal for the owner's batch, not a decision.

Verification performed for this note: the working tree was diffed, the
roadmap's phase statuses and promotion queue were read, the two wave review
sheets and the seam brief were read, the unit suite was run against the
uncommitted tree, and the city was rebuilt with the uncommitted curtain and
glass work. Results are in section 1.

---

## 1. What the handoff says versus what the tree says

**"Everything pushed" is true of commits and false of the tree.** HEAD equals
`origin/blood-city-arcade`, but the working tree carries the second half of
wave 1b, uncommitted:

| file | what it is |
| --- | --- |
| `bloodmap/glass.py`, `tests/test_glass.py` | Part B done: breakable glass promoted out of the city into bloodmap, with a `holder` mediation, `pane_faults`, `breaks_to` |
| `projects/pattern-zoo/{registry,stalls}.py` + rebuilt zoo MAP and reports | a SHOP WINDOW exhibit, so the conformance rule is satisfied |
| `bloodmap/mechanism.py` (`curtain_spec`) | the curtain's FACTS split from its PlanarLayout placement, the same move `turnstile_spec` made |
| `projects/blood-city/level/curtains.py`, `l3_theatre.py`, `build_skeleton.py` | Part C: the Aldermack's proscenium fin carved in the tree, furnished on the layout, and the command-5 stage-light Link arbitrated and wired |

So the handoff's "Parts B, D and E not started" is stale by one session:
B and the curtain half of E are written. What is NOT done is the read-back
the authoring-loop law requires. The wave 1b review sheet still says the
Aldermack has no curtains, and the gates (self-read, swept-state,
motion-set, state-preview) have not been run over the new fin. By the
project's own law that is unfinished work.

**Two submodule pointers show as modified** (`NBlood`, `xmapedit`). The memory
note and the recorded staging incident both say: never stage them. Whoever
commits wave 1b must diff each file and add by name.

### What the read-back found, 2026-09-01

The city was rebuilt from the uncommitted tree and the Aldermack curtain was
read back through `bloodmap.conformance.measure_curtain`, the same check
the zoo's sweep runs. Results:

```text
city build            exit 0; 259 sectors, 1696 walls, 430 sprites; validate 0 errors
stage curtain         sector 37, type 614, rx 340, busy 15/15, markers 8/9
stage light Link      sector 37 tx 341 command 5 -> sector 24 rx 341,
                      amplitude -24, shade floor/ceiling/walls   WIRED
shop glass            24 panes over 6 spans, 12 solid piers skipped
curtain conformance   DEVIATES: isolation. motion_set [23, 37] -- the fin's
                      moving vertices drag the AUDITORIUM (sector 23, 30 walls)
zoo curtain           sector 16 conforms, motion_set [16]
```

**The curtain defect is real and it is a topology choice, not a bug in the
spec.** In the zoo, the slot the fabric bounds (walls 110 to 113) has
`next_sector -1`: the slot is void, the fabric walls are one-sided, and the
moving tip owns its vertices. In the city the fin was carved as a hole in
the auditorium, so all eight of its walls, slot included, are portals into
sector 23. The tip's vertices are therefore shared with the auditorium's
hole loop, and when the curtain draws, the house deforms with it. That is
the motion-set failure mode the handoff lists, reproduced on the newest
mechanism in the repo. The fix direction is the zoo's: the proscenium
band must be a doorway region between house and stage with the slot cut
into nothing, not a room carved out of the house. The city has no gate that
would have said so, because only the zoo runs the conformance sweep; a
city-side sweep is a missing gate and should be added before Part C is
called done.

Suite: one failure in the uncommitted tree, the zoo's own rule that every
public constructor has an exhibit or a skip reason, raised for the new
`curtain_spec`. Fixed in this pass with a SKIP entry mirroring
`turnstile_spec`; the zoo tests pass again.

```text
full suite, before the SKIP fix   Ran 1573; FAILED (failures=1, skipped=1, expected failures=7)
tests.test_pattern_zoo, after     Ran 31; OK
```

The only failure was the one above, so the tree is green once the SKIP
entry is in. Note for whoever runs the suite next: piping it through
`tail` returns tail's exit code and drops the summary line; capture it to
a log and read the `Ran` line.

---

## 2. Where I agree with the handoff

- **The evidence discipline is the asset.** Every gate written to fail on a
  known defect first, contradictions preserved rather than smoothed, refusals
  reported as evidence. Nothing below weakens that.
- **The seam blocker is a plan finding, not a constructor bug.** Four
  workarounds tried and recorded is enough; a fifth from the machine would be
  gaming the compiler.
- **MechanismDecl is the keystone.** Reading and writing meet nowhere today
  except post-hoc self-read; the three `expectedFailure` fixtures in
  `tests/test_attested_constructs.py` are exactly the sentences the readers
  cannot emit.
- **Harbor needs the water link first** (queue rank 11). No shortcut.

---

## 3. Where I disagree, with the reason

### 3a. The seam decision need not block: build Option B and let the owner review it

The brief recommends B (move seams off centrelines) and calls it "a data
change, not a code change", eleven readers of `DISTRICT_BOUNDS` all
unaffected. If that is true, the cheapest way to present the decision is a
built city, not a brief. The project's own norm is batched review over
always-playable builds. Proposal: lay B on a branch, rebuild, re-baseline the
district norms in the same commit, and put the frames (all four districts
roaded) in the review sheet beside the current build. The owner then chooses
between two maps instead of three paragraphs, and reverting is one commit.

Two conditions. First, the norm re-baseline must ship with the plan edit,
or the district comparisons become a second set of red numbers everyone
learns to ignore, which is the exact failure the zoo exemption exists to
prevent. Second, the sheet must state which of the eight seam streets each
district inherited and why, because the brief says that assignment is a
decision per street and not arithmetic.

### 3b. The one-language unification is mostly already true; do not migrate the zoo

The roadmap's Phase 13 prerequisite says the TREE must become the only
source and PlanarLayout be "demoted to compiler IR". `bloodmap/levelprog.py`
already says of itself that it "is not a new IR" and compiles to
PlanarLayout. The demotion is architecturally done. What is not done is
that mechanism constructors take a `PlanarLayout` and tree projects have to
re-adapt them.

The tree has answered that twice now, both times the same way:
`turnstile_spec` and `curtain_spec` separate the FACTS of a mechanism
(outline, markers, flagged walls, repeats, wiring) from its PLACEMENT, and
the city writes a thin placer (`turnstiles.py`, `curtains.py`). That
split is the seed of MechanismDecl's data half. Recommendation:

1. Factor the remaining flat constructors the same way: `planar_door`,
   `lift`, `sliding_gate`, `maskwall_panel`, `shade_wave`, `stack_link`,
   and glass. One spec, two thin placers.
2. Type the spec. That is MechanismDecl's members-and-roles, primitives,
   and wiring; add the function field and evidence.
3. Leave the pattern zoo flat. It is a gallery of bays; the tree's value is
   locality and style inheritance, which a gallery does not exercise. A zoo
   migration is the largest cost in the plan and proves the least. The
   handoff's own open question, "whether the tree can express everything the
   flat projects need", is avoided rather than answered, and it does not
   need answering for the city.

Measured basis: 20 blood-city modules import the tree, 2 import
PlanarLayout; the zoo has 3 flat modules; `reasoned-authoring-v1` has 8 and
is a frozen reference project.

### 3c. The turnstile passage blocker is weaker than stated

The stated blocker is "no driver can walk a body through a rotating
aperture". Two things the project already holds make that less absolute:

- **Precedent.** The constructor copies E1M4 151/314 to the field: 32768
  clear, four vanes, blade offset, period 255, travel -8192. Players finish
  E1M4 through those rotors. A rotor that conformance measures as identical
  in every relation that matters is passable by precedent, in the same way
  the campaign's curtain repeat is "natural" by precedent. Today the
  conformance relation covers angular spacing, stand-off and span fraction;
  it does not cover period or rotor radius. Add those two, and the argument
  closes for parameter-identical rotors.
- **Kinematics.** For a rotor that departs from precedent, passage is a
  necessary-condition calculation with constants the repo already cites:
  angular rate from `busyTime` (triggers.cpp `AddBusy`, 65536 over
  `busyTime*12` ticks), the quarter-turn gap of a four-vane rotor, the
  player's wall clearance (`player_space.py`: clipdist 0x30, walldist 192),
  and the posture's forward acceleration (`player.cpp` `gPostureDefaults`).
  It cannot prove passage, but it can refuse impossible rotors and report a
  margin, which is more than a driver that refuses to enter.

Recommendation: keep the blocker for non-precedent parameters, lift it for
conformance-identical rotors, and leave the owner's ten-second playtest of
`projects/facade-pilot/level/turnstile.MAP` in the batch as confirmation.
The Aldermack forecourt can then be sealed, which is the district's
intended entry.

### 3d. Phase 11's novelty frontier should wait until after the harbor

Every finding so far came from a question someone asked, and wave 2 will
ask more of them than a search over 1462 community maps would. The one
piece worth running now costs nothing: `llmapper contradictions` over each
wave's build, as a gate rather than a report.

---

## 4. Things the plan does not mention

- **The boat has no anchor.** The harbor wishlist wants a harbor that
  "reads as a harbor (with a boat)". Owner anchors cover 104 tiles; before
  wave 2 is prompted, the knowledge index should be asked what hull, quay,
  bollard and water-surface tiles are attested, and the gaps queued for the
  owner as anchor requests. Otherwise the boat becomes the next 25%-wrong
  tile guess.
- **Stage-light sign convention is asserted, not rendered.** The Link is
  wired in the map (section 1), and `curtains.py` says a negative amplitude
  brightens. That is consistent with Build's shade sense, but it is
  precisely the kind of claim the state-preview gate exists for: render the
  house at curtain OFF and ON and check the shade moves the way the comment
  says.
- **The unparallaxed sky residue (5/1780)** is small enough to close by
  listing: if all five are one map or one author, it is a mapper slip and
  the law gains a note, not an exception. Low priority, half an hour.
- **Tier instability (14.6%)** is contained because tiers are navigation
  metadata, never evidence. Do not spend more on it.

---

## 5. Proposed order of work

1. **Finish wave 1b** (hours). Rebuild the proscenium as a doorway with a
   void slot so the curtain's motion set is its own sector; add a city-side
   conformance sweep so the next such defect is caught by the build; render
   OFF/ON of the house; update `wave1b-review.md`; commit by name after
   diffing. Do not stage the submodule pointers.
2. **Option B on a branch, with re-baselined norms and a review sheet**
   showing all four districts roaded. Owner picks a map. If B lands, the
   rail spur's gatehouse conflict is the next plan finding to report.
3. **Spec-factor the flat constructors; type the spec as MechanismDecl.**
   Exit criterion: the three `expectedFailure` fixtures pass, and the zoo
   curtain and the Aldermack curtain declare the same sentence and read back
   equal. This is the on-ramp to Phase 13 without a migration.
4. **Wave 2, harbor.** Water link promoted as a spec (rank 11), anchors
   queried and gaps queued before the prompt is written, boat as an assembly.
5. **Streets as tree nodes (Option C)** once B has made it a re-parenting
   rather than a redraw. This, not the zoo, is the tree-unification pilot.
6. Phases 12 to 15, and the novelty frontier, after the harbor.

Not in this order: rotor passage. It is unblocked by 3c's precedent
argument as soon as period and radius join the conformance relation, and
that is a small change that can ride with step 3.

---

## 6. Open questions I could not settle from the repo

- Whether the owner wants the district seams moved at all, or prefers C
  outright. The brief costs it; only the owner ranks addressability against
  the plan edit.
- Whether `curtain_spec`'s one-flagged-end fin generalises to a two-leaf
  theatre curtain (E1M1 s125 has walls 1200/1210 converging with opposite
  flags). The tutorial fin is one leaf; the Aldermack may want two.
- Whether the harbor's quay runs are streets (Option C makes them nodes) or
  edges of a water body. That decides which constructor owns them.
