# Owner review queue

Everything currently waiting on a decision, in one place, with the evidence
and a recommended default. **A single reply settles the batch** — "defaults"
takes all six recommendations; otherwise name the numbers you want changed.

Nothing here blocks the city enrichment wave. These are decisions the machine
should not make alone, not obstacles.

Companion: **[`reports/owner-prescreen.html`](owner-prescreen.html)** — the
phone-friendly state sheet, every mechanism at OFF and ON with the measured
difference on each card. Items 1 and 2 have their evidence in it.

---

## 1. Tiles 142 and 2464 — family or accident?

**The question.** The mask law says a tile carrying the transparent colour
belongs on a one-sided wall or a sprite, never on a two-sided wall where the
engine would see through it into the next room. The campaign breaks that in
**23 slots out of 60839**, and every one of them is tile 142 or tile 2464.

**The evidence.** Both tiles are rendered as cards at the end of the
pre-screen sheet. 142 sits in the 140s run alongside 146 and 147, which are
the curtain fabrics — if it is family, the law needs a two-sided exception
for cloth, and the theatre district will want it. 2464 is nowhere near that
run and near no cloth.

**Why it matters now.** The city wave will hang a lot of fabric. If cloth on
a two-sided wall is legitimate, the validator should stop calling it an
error before we author fifty of them.

> **Recommended default: family for 142, accident for 2464.** The 140s
> reading is coherent and the isolated one is not. If you disagree on either,
> say so and the law changes shape rather than gaining an exception list.

---

## 2. Zoo topology-norms exemption — yes or no?

**The question.** The zoo measures `mean_degree` **2.09** against a campaign
median of **2.74**, and a dead-end fraction of **0.344** against a campaign median of
**0.159**. As a level it would fail the topology norms. It is not a level.

**Draft exemption text**, to go in the norms if you say yes:

> *A gallery is structurally terminal-heavy by construction. Its purpose is
> to present each exhibit in a bay entered and left the same way, so a high
> dead-end fraction and a low mean degree are the shape of the thing rather
> than a defect in it. `projects/pattern-zoo` is therefore exempt from
> `mean_degree` and `dead_end_fraction`. The norms remain authoritative for
> every map that is a level, and the exemption is named per project, never
> inferred from a map's shape — a real level that measures like a gallery is
> still a finding.*

**Why it matters now.** Until this is settled the zoo's norm report has two
standing red numbers that everyone learns to ignore, which is how a real
regression gets missed.

> **Recommended default: yes, adopt the text above.** It is scoped to one
> named project and says plainly what stays authoritative.

---

## 3. Crate and shelf sector labels — still open from the contrast pilot

**The question.** The contrast pilot asked you to name the sector kinds
behind a set of crate-side and shelf-side renders. It is **optional and
crate-side only**; nothing depends on it.

**The evidence.** [`reports/blood-contrast-shelf-vs-crate.md`](blood-contrast-shelf-vs-crate.md),
unchanged — the same sheet you were sent, no rework. Its bookcase-vs-crate
companion is `reports/blood-contrast-bookcase-vs-crate.json`.

**Why it is here.** So it stops being an item you half-remember. If you do
not want to do it, saying "drop 3" closes it for good and it will not
reappear in this queue.

> **Recommended default: drop it.** The naming would improve retrieval
> slightly and nothing is waiting on it.

---

## 4. `maps/review/` trio — delete or move?

The holding pen has held these since the Phase 0a corpus gate on
2026-08-31. One line each:

| file | what it is | recommended |
| --- | --- | --- |
| `ASAVE1.map` | XMapEdit autosave that strayed into `blood/campaign/`; not a map anyone authored | **delete** |
| `POWER06.MAP` | a Duke3D v7 map filed under `blood/community/` | **move to `maps/duke3d/`** — the Duke conversion work can use it |
| `TWISTER.MAP` | the same | **move to `maps/duke3d/`** |

**Why it matters now.** They are excluded from every population already, so
this is tidiness rather than correctness — but the holding pen is supposed to
be a pen, not a shelf.

> **Recommended default: delete the autosave, move the two Duke maps.**

---

## 5. `maps/blood/mechanism/ASAVE1.map` + `.bak` — DONE, for information

The curriculum mine found XMapEdit autosave debris sitting among the
mechanism tutorials. **Moved this run** to the holding pen as
`maps/review/ASAVE1-mechanism.map` and `.bak` — renamed on the way in,
because `ASAVE1.map` was already taken by the campaign one — with a row added
to `maps/review/README.md`.

`maps/blood/corpus.json` is regenerated. The mechanism-tutorial population is
now **173 maps**, and it turns out the old manifest was **stale by two**: it
predated your `casket.map`, which was missing from the corpus entirely.

> **No decision needed** unless you want them deleted outright rather than
> held, which item 4's answer probably covers.

---

## 6. Six tile-kind drifts — the owner anchor against the campaign

Six anchors say a tile is one thing and the campaign never once uses it that
way. These are **drift, not conflict**: nothing is broken, but one of the two
readings is a better description than the other.

| tile | your anchor says | what the campaign does use it as | count |
| --- | --- | --- | --- |
| 144 | wall (wooden lattice, e.g. windows) | `sprite_wall` | 15 |
| 147 | maskwall (curtain, translucent) | `sprite_wall` | 7 |
| 464 | wall (grate door) | `sprite_wall` | 2 |
| 468 | wall (vertical ceiling light, unlit) | `sprite_face` | 20 |
| 469 | wall (vertical ceiling light, lit) | `sprite_face` | 12 |
| 502 | wall (sewer grate) | `over_picnum` 27, `sprite_floor` 28, `sprite_wall` 1 | 56 |

**The question for each is the same:** is the kind a first-glance label to
correct, or is the campaign simply not using the tile the way it could be?

> **Recommended default: leave all six as they are, and record the campaign
> usage beside the anchor rather than overwriting it.** Your anchors are
> OWNER provenance and describe what a tile IS; the usage table describes
> what Blood happened to do with it. Where they differ, that difference is
> worth keeping — it is exactly where our own maps could legitimately do
> something the campaign never did. Overwrite only if you meant the anchor as
> a usage rule.

---

## Also open, no decision needed yet

Two items the queue holds that are notes to us, not questions for you:

- **`mechanism.BLADE_PICNUM` is tile 332, graded "untested: grate/lattice".**
  A weak name on a tile we place. It wants a look when the turnstile is next
  touched.
- **`mechanism.FENCE_PICNUM` is tile 1044, which no anchor names.** Either it
  earns an anchor or the constructor should use a tile that has one.

---

## What was settled without you

Recorded so the queue is honest about what it stopped asking:

- **The oracle casket's `s2 state=1`** was carried as an open question and an
  "editor leftover" for weeks. It is neither: `trInit` treats the drawn
  geometry as the ON pose, so a sector that declares `state=1` starts exactly
  where it was drawn. Intent, not leftover. Settled by the engine, not by a
  judgement call.
- **Whether the zoo's mechanisms actually change state.** Previously this was
  checked by looking at rendered frames, which cannot answer it. Both poses
  are now measured out of the snapped maps
  (`reports/zoo-state-check.json`): all 19 mechanisms change measurably, none
  disagrees with its own declared travel, and the three pairs that look
  identical are rotors turning whole circles — they genuinely end where they
  began.

---

## Resolved 2026-09-01 (owner walk + tile ruling)

- **Item 1 settled, and the recommended default was WRONG on 142:** tile
  142 is a skull-shaped FIREPLACE maskwall (owner) — not curtain family,
  nothing to do with 2464; its two-sided uses are the legitimate
  see-through fireplace mouth. 2464 is an ejected shotgun shell casing,
  decorative; its two wall slots are mapper accidents. Both are now owner
  anchors; the mask law keeps two-sided walls out of scope with 142 cited
  as the legitimate masked case.
- **Walk results:** casket WORKS; lift WORKS; keyed door works but the
  key PICKUP art does not match the lock sprite (different key); CRACK
  BARRIER does not work — the type-408 thing was given switch-style
  properties (cstat 128, hand trigger_vector) instead of its native thing
  record (E1M4 sprite 373: cstat 209, thing statnum, transmits on death);
  SHELF SECRET is unintelligible — reads as a sliding gate with unrelated
  props instead of a bookshelf that slides (E1M1 s70 blueprint).
- Items 2, 3, 4, 6 remain open for the owner.

---

# The seam decision — a brief, 2026-09-01

**Nothing here has been implemented. This is analysis so the decision can be
made over numbers.**

## The blocker, in one line

Gravesend draws its district seams **down street centrelines**. So a main
street belongs half to each side of the seam, and neither half is wide enough
for a carriageway plus its two pavements. Street anatomy therefore cannot be
laid on those runs at all.

**The measured size of it: 8 of the 13 roadable runs sit on a seam.**

```text
Theatre_Row_street_west   Theatre_Row_street_east   the_avenue_north
the_avenue_mid            the_avenue_south          market_street_west
market_street_mid         market_street_east
```

Wave 1 laid 3 carriageways, all on the 5 runs that do NOT touch a seam. Two
districts — **Theatre Row and Foundry Ward — get no roadway at all** until
this is settled, because every roadable run they have is a seam run.

---

## Option A — paired half-roads across the seam

Each district lays its own half of the carriageway and the two halves are
joined to each other across the seam.

**What must become seam-aware:** the road layer only. `streets.lay` gains a
second pass that matches half-roads by seam and span, and pairs them to each
other instead of to their own street.

**Call sites:** `DISTRICT_BOUNDS` is read in **11 places**; only the one in
`streets.lay` would change. Nothing else in the level program needs to know.

**The measured fact you cannot see from prose:** the pairing has to happen
between two rooms that do not exist at the same moment — a run is laid
district by district — so `lay` needs a deferred join, and a deferred join is
the mechanism that already caused the `same-direction coincident atomic
segments` failure four times in wave 1. This is the cheapest option to
*describe* and the one most likely to fight the compiler.

**Cost: small and contained. Risk: the highest of the three.**

---

## Option B — move the seams off the centrelines

Redraw district boundaries to run down the middle of blocks, so each street
belongs wholly to one district.

**L1 contract rows that change:** the 4 district bound rows, and the
re-parenting of the masses they cross — **2 blocks each for Theatre Row, Old
Crossing and Foundry Ward, 3 for Market Slip**. 9 blocks total, every one of
which changes owner or keeps it by a new rule.

**Who inherits each boundary street** becomes a decision per street rather
than an accident of arithmetic: 8 streets, each needing an owner.

**The measured fact:** `DISTRICT_BOUNDS` is read in 11 places and 8 things
reference district street regions by name. All of them would keep working —
the bounds simply hold different numbers — so this is a **data change, not a
code change**. Nothing in the level program is seam-aware today, which is
exactly why moving the seams costs so little.

**Cost: the plan edit and one rebuild. Risk: low. It invalidates the
district-level norm comparisons until they are re-baselined.**

---

## Option C — streets as first-class parts of the tree

A street stops being a leftover region owned by a district and becomes its
own node, with districts owning only their blocks.

**What the plan gains:** a street is addressable — "what is on Theatre Row"
gets an answer, which is the same failure the city tree fixed for venues.
Roadways, pavements, lamps and signs all hang off the street rather than off
whichever district happened to contain them.

**What it loses:** style inheritance. A district's facade material currently
reaches its street through containment; a street that is nobody's child needs
its register stated or inherited by a new rule.

**Nodes:** 13 exist; 18 edges become 18 street nodes, so the tree grows by
**18 assemblies plus their rooms** — roughly a doubling of the top two
levels.

**The measured fact:** the conformance check at `conformance.py:142` asserts
that *every district's street region plus the cemetery and gate rooms join
one at-grade component*. Under C that row stops making sense as written and
has to be restated over street nodes — so the conformance diff is not
cosmetic, it is one of the checks that has actually caught a regression
before (light pools joining the street network).

**Cost: the largest. Risk: moderate. It is the only option that also solves
the *next* problem.**

---

## What the future costs, per option

The rail spur and the harbor (wave 2) both add street runs.
`the_rail_spur` is already refused for an unrelated reason — its carriageway
**would run through the gatehouse** — and the harbor will add quay runs along
the water's edge, which is a district boundary by nature.

```text
option   cost now         cost per future street
A        small            small, but each new seam run is a new pairing
B        one plan edit    zero -- a street belongs to one district by then
C        large            zero, and the street is addressable
```

---

## Recommendation

**Option B.** It is a data change rather than a code change — nothing in the
level program is seam-aware today, so moving the numbers costs almost
nothing — and it makes every future street free. Option A is cheapest to
write and most likely to fight the compiler; Option C is the right long-term
shape and too large to do as a side effect of laying roads.

If B is chosen, C stays available and gets cheaper: with streets already
belonging to one district each, promoting them to their own nodes is a
re-parenting rather than a redrawing.

**Implemented: none. This wave worked only on what does not depend on the
answer.**

---

## 7. The Aldermack's proscenium: one leaf or two? (2026-09-01)

**The question.** The Aldermack's proscenium spans **5120**. The curtain is
built with ONE leaf. A theatre curtain is conventionally two, converging.

**The evidence**, measured over the originals (43 campaign maps + the
DOOR-CURTAIN tutorials, autosave debris excluded):

```text
one-leaf curtains   n=47   min 1024   median 1024   max 6400
two-leaf curtains   n=34   min 1024   median 2048   max 4352
the Aldermack               span 5120
```

5120 is **inside** the attested one-leaf range and **768 beyond** the widest
two-leaf sector the campaign contains. So the corpus supports one leaf at
this span and does not support two.

Against that: E1M1's own curtain -- the one you attested -- is two-leaf, and
two converging leaves is what a stage curtain looks like.

> **Recommended default: leave it at one leaf.** It is the reading the corpus
> supports, it is built and green, and the two-leaf dialect is now
> constructible (`curtain_spec(leaves=2)`) and exhibited in the zoo, so
> switching later is a one-line change. Say "two" and it becomes two, with
> the note that the span exceeds anything the campaign does.

## 8. A second autosave was still in the campaign corpus — DONE, for information

`maps/blood/campaign/ASAVE1.map` + `.bak`: a second XMapEdit autosave, of
different content from the one already in the holding pen, still sitting in
the campaign directory. Its s125 duplicates E1M1's curtain exactly, so it
inflated the curtain census from 39 sectors to 40 and the two-leaf count from
12 to 13.

Moved to `maps/review/ASAVE1-campaign2.map` + `.bak` with a README row; the
corpus manifest is regenerated and the campaign population is 43 again.

> **No decision needed** unless you want it deleted outright rather than
> held, which item 4's answer covers.

## 9. Five city tiles are authored on walls the engine never draws (2026-09-01)

**The finding.** The rendering law (`bloodmap/render_slots.py`,
`engine.cpp:4686/4690/4801/4938`) says a two-sided wall shows its `picnum`
only on a step -- where one sector's ceiling is lower or its floor higher
than the other's -- and reaches its middle band only when masked (cstat 16)
or one-way (cstat 32). Run over `blood-city-current.MAP`, five authored wall
tiles are on screen **nowhere in the level**:

```text
tile   68    walls 124, 127, 134, 170, 172         materials.parlor.opening
tile   93    9 walls (501, 504, 508, 509, 519 ...)  materials.church.opening
tile  194    walls 1264, 1316                       sewerkit.MOUTH_TILE
tile  203    walls 238, 243, 257                    materials.theatre.opening
tile 1011    walls 510, 512, 513                    materials.crypt.opening
```

Every one is the same shape. Wall 124, for instance, is sector 14 -> sector
15 with both ceilings at -20480, both floors at 8192, cstat 0, and the
partner wall also wearing 68. It is a doorway threshold with no step and no
mask, so the lining tile chosen for it is never rasterised. This is the stage
curtain's defect (fixed in wave 1b) repeated in four districts plus the
sewer, with less conspicuous materials.

The campaign does the same thing on 26.5% of its walls, so *a* wall with an
unread tile is a habit, not a defect. What is not a habit is a tile that
appears **nowhere in the map**: 97 of 1979 authored campaign wall tiles,
4.9%, and E1M1 has none at all.

**The options.**

* **A. Give the threshold a reveal.** Step the doorway's ceiling (or floor)
  against the room so the lining draws on a real band -- the aperture
  grammar's own idiom, and what `frame_z_doors` already does for type-600
  doors. Costs geometry in five places.
* **B. Mask the threshold wall.** cstat 16 with the lining as `over_picnum`,
  the DOOR-CURTAINSD s4 pocket dialect. One flag and one field per wall, but
  a masked wall is a draw-order cost and blocks nothing unless cstat 1 goes
  on too.
* **C. Stop authoring the tile.** If the doorway is meant to read as an
  opening rather than a lining, the `opening` field is decoration that never
  had anywhere to go; drop it from `Material` and let the room's own wall
  tile run through.

> **Recommended default: C for the four `Material.opening` tiles, A for the
> sewer mouth.** The four thresholds are all flush, which says the design
> never wanted a band there; the tile was chosen because `Material` has a
> field for it. The sewer mouth (194, E3M3's circular tunnel lining) IS
> meant to be seen -- it is the pipe's mouth -- so it wants a real reveal.
> Say the word and either becomes a build change; until then the gate reports
> the five and the city build prints them by name.

**Why it is not fatal to the build yet.** `wall-tile-is-drawn-somewhere` is
graded a *warning* (4.9% campaign rate) and the city build prints it rather
than refusing. The zoo passes it with zero and runs it as a LAW rule. Once
these five are resolved the city can adopt the same law.

## 10. E1M1's "pelmet" is an editor leftover, not a valance (2026-09-01)

**For information; it corrects something this project wrote down.** The
supervisor brief and the wave-1b roadmap entry both record E1M1 sector 125's
walls 1203-1207 -- `picnum` 146 = `over_picnum` 146, cstat 4, two-sided into
s122 with a 65536-unit ceiling step -- as the campaign's attested way to hang
a pelmet above a curtain, and the city's curtain was excused partly on the
grounds that it was "accidentally the E1M1 pelmet".

Read through `render_slots`, tile 146 on those five walls is drawn **nowhere**.
s125's ceiling is -10240 and s122's is -75776, so the neighbour's ceiling is
*higher*: from the curtain's side there is no upper step at all
(`engine.cpp:4690`). The step is on s122's side, and its walls 1102-1106 draw
their own `picnum` 109, the hall's stone; their `over_picnum` 146 sits behind
cstat 0x6 (swap + align, no mask bit) and is never read (`:4686`, `:4938`).

The visible fabric in E1M1 is the four one-sided leaves 1200/1201/1209/1210.
There is no attested pelmet idiom. `conformance.curtain_dialect` still counts
`pelmet: 5` for s125 because the PORTAL genuinely steps -- that is the
geometric fact -- but it now measures it through `render_slots` and the
rendering law is what says the tile on it is not seen.

> **No decision needed.** Fixtured in `tests/test_render_slots.py`
> (`test_e1m1_pelmet_is_the_auditoriums_tile_not_the_fabric`) so it cannot
> quietly revert. Flagging it because a future curtain built "like E1M1's
> pelmet" would be building an invisible one.

## 11. Which map did you see inside out? (2026-09-01)

The supervisor listed four candidate causes for the inside-out sectors you
reported. P3 closed case (b) -- a neighbour deformed by `DragPoint` that no
gate swept -- and the answer is that the vanilla curriculum has **none**: zero
inverting and zero self-crossing neighbours across 429 taught mechanisms. The
campaign has one inversion and eighteen folds, all of them in ORIGINAL maps,
none of them anything we built:

```text
inverts   E4M2 s201 (615) -> s200, inside out at 11 of 17 poses, the
                              load pose included
folds     E2M5 s95/s96 -> s708 - 15 of 17 poses
          E2M5 s521/s522 -> s525 - 13 of 17
          E3M3 s0/s263 -> s1..s12, s13 -> s14 - about 10 of 17
          E3M1 s66 -> s71 - 6 of 17
          plus ten shallower ones, one or two poses each
```

Neither build has any: the zoo sweeps clean and the city's curtain is isolated
since P1 rebuilt it as a doorway. So if what you saw was in OUR maps, it was an
older build, and case (b) is now gated; if it was in a Blood level, E4M2 and
E2M5 are where to look.

The measurement is a transcription of `TranslateSector`, not the engine, and it
rounds the marker angle where the engine rounds coordinates. None of these has
been observed in play.

> **Recommended default: treat these as noted-and-gated and move on.** The gate
> is in both builds and fails first on a fixture; chasing eighteen original-map
> geometry hairs has no product behind it. If you remember the map and exhibit,
> say so and the specific one gets read.


## 12. 168 campaign mechanisms were being described to you as "find a switch" (2026-09-01)

Reading a mechanism's INTERACTION only looked at XWALLs on the sector's
PORTAL walls. Blood's canonical doors put the push on the sector's own leaf,
which is routinely a one-sided wall -- `#SLDOOR` and `#SWDOOR` do it, E1M1 s4
does it, and this project's own `mechanism.curtain` does it. Every one of those
read as `remote_rx`: true of the sector, and the wrong answer for a player, who
is told to look for a switch the level does not contain.

The engine settles it. `player.cpp:1637-1641`: the use raycast reads the hit
wall's own XWALL and operates it when `triggerPush` is set, without consulting
`nextsector` -- the `nextsector >= 0` branch under it is the FALLBACK to the
neighbour's `Wallpush`. `trTriggerWall` (`triggers.cpp:1865-1884`) then reaches
`OperateWall` (`:692`), whose default branch calls `SetWallState`
(`:112-128`), which sends the wall's own `txID` on the state edge. So a
one-sided wall is pushed exactly like a portal wall.

Measured over the 43 campaign maps, 2027 mechanisms:

```text
                                        before   after
remote_rx  ("find a switch")              1515    1347
wall_push  ("push the thing itself")       254     425
wall_push+remote                           170     167
171 readings change: 168 remote_rx -> wall_push, 3 lose a spurious +remote
```

The `+remote` suffix is now withheld when the push transmits on the sector's
OWN rx: that channel is how a wall reaches a sector at all, not a second route
from somewhere else. E1M1 s4's owner-attested fixture asserted exactly this and
was `expectedFailure`; it passes now, with the assertion unchanged.

> **Recommended default: accept, and re-mine the door precedents.** The
> knowledge under `knowledge/blood/design/` and the mined door reports were
> written against the old reading, so their interaction histograms are stale by
> 8.4%. Nothing regenerates them automatically and this agent did not, because
> re-mining is a separate deliverable with its own report pair. Nothing depends
> on the stale numbers today.

## 13. The two mechanism facets still unread, and which layer each needs (2026-09-01)

Both are `expectedFailure` fixtures over owner-attested E1M1 constructs, and
both were re-measured this session rather than assumed.

**The Link that drives a light -- CLOSED 2026-09-02 (P8).** Every field was in
the file and legible one at a time -- s125 `tx_id 126, command 5`, s124 `rx_id
126, amplitude -8, shade_always 0` -- and what was missing was that nothing in
the stack read a SECTOR's `command` as a verb. `effects.transmission` now
does, as a fifth plane on the mechanism record, and the fixture passes with
its assertion unchanged. E1M1 s125 -> s124 reads *follow me*, continuous,
floor shade 36 at OFF and 28 at ON.

**The casket as one construct.** `reachability.link_pairs` already reports
`{link 10, sectors [28, 30], sprites [47, 46]}`; `motion.stack_pairs` reports
nothing for them, because it looks for the floor-picnum-504 see-through
marking and this pair does not carry it. What is missing is the COMPOSITION
step -- nothing joins a per-sector mechanism record to the mechanism on the
other side of its ROR plane. A construct that is four sectors in two planes
cannot be expressed by a per-sector record at all, so this one is genuinely
blocked on the typed declaration layer (roadmap Phase 13, MechanismDecl:
members plus roles).

> **Recommended default: the casket stays open, and do not loosen its
> fixture.** It is now the whole countable gap. Inventing a `stack_partner`
> key on the per-sector record to make one test pass would put the
> composition in the wrong place.

## 14. The bot's AGTST test maps are gone — DONE, for information (2026-09-02)

A supervisor cleanup (`git worktree remove --force` on a worktree holding a
junction to the main checkout) deleted `maps/` and `reference/blood`. The
corpus was rebuilt byte-exact from on-disk copies against the sha256
manifests in `reports/` (see `reports/corpus-recovery-2026-09-01.md`), and
the game directory from `D:\Games\DOS\BLOOD`. **Not recoverable:** the bot's
`AGTST1`–`AGTST18.map`, `overlap1.map`, the iter27 bot artifacts, your
`casket.map`, `helix_stairs.map`, `SSFACE.MAP`, `SSHIVE.MAP` and
`xmapedit.pdf`. `tools/botcorpus.sh` has no maps to run until AGTST is
re-authored. Two backup mirrors now exist (`D:\Games\DOS\llmapper-corpus-
backup`, `C:\Users\jiriv\llmapper-corpus-backup`, refreshed by
`tools\backup_corpus.ps1`) and the agent protocol forbids recursive deletes
and junctions outright.

> **No decision needed.** If you still have `casket.map` or any AGTST map
> elsewhere, dropping them into `maps/blood/mechanism/` and
> `reference/blood/` restores the tests that depend on them.

## 15. Should our own builds REFUSE a Link receiver that cannot answer? (2026-09-02)

Reading the Link as a verb turned up four ways a receiver can sit on the
channel and be unmoved by it, each with every field individually legal:
`shade_always 1` (`sectorfx.cpp:166` then never scales the amplitude by busy),
`amplitude 0` (`InitSectorFX:363` never lists the sector for lighting at all),
amplitude with none of the three `shade_*` faces set, and `locked`
(`trMessageSector:1916` drops the Link before it arrives).

Over the 43 campaign maps, **one receiver of 269 is in that state**: E4M2 s33
-> s200, a marked rotator driving a flicker light whose `shade_always` bit is
set, while its three fellow listeners on channel 103 all respond. And **eight
of the 146 Link senders (5.5%) transmit on a channel nobody receives on** --
E1M3 s307, E1M4 s218, E1M5 s197, E1M8 s109, E2M5 s80, E2M5 s673, E3M2 s45,
E3M6 s35.

Neither is necessarily a mistake. A light meant to flicker regardless of a
door is a legitimate thing to want, and a channel left empty is what a cut
mechanism looks like. Static reading cannot tell either from a slip.

The question is only about **our** output: when `curtains.link_stage_light`
or any future constructor wires a Link, should the build refuse on a receiver
that cannot answer?

> **Recommended default: yes for constructed maps, never for mined ones.**
> In a generated map an inert receiver is always a defect, because the
> constructor asked for the coupling explicitly; in an original it is
> evidence, and flagging it would be this project telling Monolith it was
> wrong. That is the same split the rendering-law reader already uses. It
> needs a `drives` key on `readback.sentence()` to enforce, which is the next
> step named in the roadmap section and is NOT built yet -- so today the
> reading reports and nothing refuses.

## 16. Two passes want the facade's panning. Which wins? (2026-09-02)

`facade_pass.world_align_facades` sets a facade wall's `x_panning` from its
WORLD position, so the bay grid is identical everywhere in a district — E3M1's
own practice, and the reason a row of shopfronts reads as one street rather
than as eight buildings. `texture_frame.frame_map` sets it from the RUN, so a
material continues across a doorway instead of restarting at it — the editor's
own law, and the fix for the owner's walk.

They want the same field on the same walls. Before this run the facade pass
phased 128 walls; after it, 1, because the frames now set a scale its own
check declines to override. Nothing decided that: it fell out of the order the
two passes happen to run in.

The measurable cost is one class: blood-city's `bend solid-portal` x went from
91% to 83%. That is still two and a half times the campaign's 34% and well
clear of the gate, so nothing is broken — but a silent winner between two
deliberate passes is the kind of thing that turns into a mystery later.

The third option is real and is what the campaign appears to do: a district is
ONE frame. Give the whole street front a single `WallRunFrame` whose u-origin
is a world point, and both facts hold at once — the bay grid is district-wide
AND the material crosses every doorway, because they were never in conflict
except in the per-wall representation.

> **RESOLVED 2026-09-02 (P13): the district frame, and neither pass.**
> `texture_frame.world_u` gives a run a world u-origin, so the bay grid and
> the run carry hold together -- 640 of 1694 walls on the world grid against
> `world_align_facades`'s 607, with continuity rising (bend solid-solid x 91%
> -> 98%). That function is deleted. `align_headers` stays: it sets cstat 4,
> which the frame depends on rather than replaces.
>
> ~~Recommended default: leave the frames winning for now, and make the
> district frame the next step rather than choosing between the two passes.~~
> The frames fixed six classes and cost one, all of them still far above the
> campaign; and `world_align_facades` is now nearly inert, so deleting it
> would be tidier than keeping it as a coin-toss. Not deleted here, because it
> encodes the E3M1 bay-grid observation and that observation should move into
> the district frame rather than be lost.

## 17. The 8x facades shipped, were rendered, and nobody saw it (2026-09-02)

Between 8b70d51 and f843e2c every framed wall in blood-city and the pattern
zoo was drawn eight times too narrow -- median 8.00 texels per sixteen world
units against the campaign's 1.00, on 1634 and 436 walls. It passed the
continuity gate, the read-back, the conformance sweep and the `>`-invariance
test, and it was rendered into a before/after sheet and reported as an
improvement.

The reason is structural rather than careless: **every texture check this
project had was relative.** Each compares a wall to its neighbour, or a build
to its own claims, and a uniform error moves both sides together. The
continuity gate did worse than miss it -- at 8x every `x_repeat` is a multiple
of 8, so the panning never advances and every join "continues", and the broken
map scored HIGHER in every class.

`material-is-drawn-at-campaign-size` closes this particular hole. The general
question is yours: **how much of the rest of the stack is relative in the same
way?** The conformance templates are ratios; the design-role readings are
comparisons; `readback` compares a build to what its own constructor said,
which cannot catch a constructor that is wrong in a consistent way.

> **Recommended default: one absolute, corpus-anchored magnitude check per
> family of construct, added when that family next gets worked on rather than
> as a sweep.** A sweep would be guessing at which quantities have a campaign
> distribution tight enough to gate on; this one was worth having because the
> corpus turned out to be extraordinarily tight (every map 0.84-1.00). The
> cheap general rule meanwhile: when a gate is added, ask what it would say
> about a map where the quantity is uniformly wrong, and if the answer is
> "nothing", say so in the docstring.

## 18. The two street questions are answered, and one new one (2026-09-02)

**§5 question 2 — plazas at pavement level without a kerb: taken as YES**, per
the assignment. Noting a correction while adopting it: tile 379 is not "the
plaza tile at pavement level" in E3M1. It has 50 sectors wearing 379, at z
-122880, -90112 and -136192 — interiors, not the street. The plaza-at-pavement
decision stands on its own merits; it just is not E3M1's evidence.

**§5 question 3 — pavement bands on lanes and alleys: taken as ALWAYS.** E3M1
supports it: its fourteen pavement sectors band at 512 x2, 1024 x1, 2048 x6
and 2560 x1, so the narrow cases exist and are never zero.

**§5 question 1 — the light direction convention: answered and written down.**
`resolution.SUN_BEARING = 478`, a Build angle (0..2047, zero along +x,
increasing as `sprite.ang` does), naming the direction a shadow is cast
towards. 84.02 degrees, which is E3M1's oblique shade-edge cluster.

### The new one: what is a kerb, for a gate to count?

The assignment asks for "every kerb band wears the kerb tile on its road-side
record (absolute: tile 6 or a tile the campaign attests in that slot)". The
fail-first half is clean — **0 of 261 kerb-condition records in the current
city wear tile 6**, and its steps are 1024/1536/2048/3072/4096 where E3M1 uses
2048 without exception. The absolute half does not calibrate:

* over the 43 campaign maps' **1046 outdoor kerb-condition records** the tiles
  are 2490 (149), 67 (65), 110 (51), 2499 (49), 6 (38), 2474 (37)... the top
  eight sharing 43% between them. Tile 6 is E3M1's street, not a law.
* the narrower clause "the band must not wear the material of the surface
  standing above it" scores the **campaign at 16% and the city at 0%** — the
  city is already better by it.

The trouble is the population, not the tile. Both readings guess at which
two-sided steps are kerbs from geometry alone, and a campaign map's outdoor
steps include harbour walls, rubble, ledges and rooftops.

> **CLOSED 2026-09-02 (P14b slice 1).** The kerb is now a record
> `overlay.HeightIsland` declares, so `street_model.kerb_faults` checks a
> stated population instead of inferring one, and the rule is exact with no
> corpus threshold: the band wears the declared tile, never the material
> standing above it, and the rise is 2048 absolutely (E3M1, 11 of 11). Slice
> 1 passes it on 3 declared records; the committed city fails it on all 74
> faces a body sees from its outdoor ground, which wear 380/417/384/28/393/400.
>
> ~~Recommended default: do not ship the kerb gate until the rebuild emits
> kerbs.~~ Once a kerb is a record `overlay.HeightIsland` declares, the
> population is stated rather than inferred and the rule becomes "the tile on
> a declared kerb record is the island's `kerb_tile`" — which is exact, needs
> no corpus threshold, and is the same shape as P13's record-ownership ledger.
> The E3M1 numbers stay as the constructor's defaults (tile 6, rise 2048), not
> as a corpus-wide law. Ship a miscalibrated gate and it joins the ones that
> passed an 8x map.

## 19. One sun means north-south streets are never cross-shadowed (2026-09-02)

Not a defect, but a consequence of a decision, and it should be decided
knowingly rather than discovered later.

`SUN_BEARING` is 478 -- 84 degrees, very nearly due +y -- measured from E3M1's
own oblique shade edges. A shadow therefore drifts about 7100 units in x for
every 67500 in y, so on a **north-south** street it runs ALONG the road and
reaches the far pavement only after roughly 125,000 units of run. No street in
Gravesend is a fifth of that. On an **east-west** street the same sun cuts
straight across the road and both its pavements.

Gravesend's graph is mostly north-south (the avenue, the west street, the two
spurs) with three east-west runs (Theatre Row, market street, the quay). So
with one sun, the avenue and the west street get shadow edges running along
them -- long thin lit and shadowed strips -- and only the three east-west runs
get the crossing shadow that reads as a building's shade thrown over a street.

E3M1 has it both ways for the same reason: s8 is 7456 x 21504 north-south and
s45 is 18048 x 4096 east-west, and its oblique shade edges are the ones its
east-west road carries.

> **Recommended default: keep the one sun and accept the asymmetry.** It is
> what E3M1 does and it is physically what a low sun does to a grid city --
> one axis of streets in shade, the other striped along its length. Two
> alternatives exist if the look disappoints: turn the bearing 45 degrees so
> both axes are cut obliquely (cheap, one constant, but no longer E3M1's
> measured angle), or rotate the city's grid against the sun instead (dearer,
> and it changes every solved coordinate). Neither is worth doing before the
> whole graph compiles and the effect can actually be looked at.

## 20. Where does `enclosure_backdrop` come from? (2026-09-02)

The map-edge family has four members. Three are measured:

* **END WALL** — E3M1 s0/s339/s343: a raised mass whose floor is the wall top
  (379), sky ceiling, blocking faces in the district's stone, 3.86–5.80 player
  heights up.
* **CHASM** — DWE3M1: its deepest sectors sit 26.9 player heights below the
  median floor (z 526336 against 70656), wearing rock 274, 270, 411.
* **HORIZON OVER WATER** — DWE3M10 s404: a zero-height sector (floor_z ==
  ceiling_z == 21504) with tile 3678 on both surfaces and the parallax bit on
  both, meeting the quay at delta 0; the sea itself is 2490 under palette 10,
  panning at velocity 10 on angle 900 with drag.

**ENCLOSURE WITH BACKDROP is named and has no row**, because I could not find
a corpus precedent for it: a city ringed by walls with fake masses beyond and
no interiors behind them. `joins.EDGE_KINDS` carries the name so the gap stays
countable, and asking for its row raises rather than inventing one.

Two related notes. Tile 2490 is **stone that Blood palettises** — 25 of its 34
campaign sectors carry palette 10 and pan, 8 carry palette 0 and do not — so
the water test is the palette and the behaviour, never the tile; that is now
`joins.is_water`. And `reachability.classify_offmap`, which the brief says
raises TypeError on every map, **does not**: it returns clean results on six
campaign maps and on both Death Wish maps. I have not touched it.

> **Recommended default: leave `enclosure_backdrop` without a row until a
> precedent is named, and give Gravesend's three landward sides END WALLS,
> which are measured.** The city's boundary chain already says so. If you have
> a map in mind for the backdrop idiom, name it and the row is an afternoon;
> if there is not one, the honest position is that Blood does not build that
> edge and the family has three members, not four. Inventing the row would put
> a guess into the one table whose whole value is refusing to guess.

## 21. A shadow has to cut a concave ground plane (2026-09-02)

The junction decision resolves one thing and creates another, and it is worth
seeing before slice 3 runs into it.

The street network is now ONE ground-plane region per connected network, which
is right -- it is why the three `zero_exit_gameplay_sector` refusals went away,
and it is why a junction needs no exits of its own. But that region is a
lattice: concave, twelve vertices for a single crossing and many more for the
whole graph. `overlay.split_convex` refuses a concave polygon **on purpose**,
because guessing at a concave cut is the "insert a sector where there is room"
idiom this whole model replaces.

So a shadow cannot currently cut the plane it is supposed to fall across.
Three ways out, and they are not equal:

1. **A simple-polygon splitter.** Walk the boundary, insert crossings, rebuild
   chains, close them along the cut line. About sixty lines, exact in
   integers, and it handles every case including a cut that leaves several
   pieces. It is the honest general answer and it is the only one that also
   serves interiors later.
2. **Convex decomposition of the plane before cutting.** Cheap for a grid
   (the strips are already rectangles) but it re-introduces the pieces the
   junction decision just removed, and the seams between them would need join
   rows saying "nothing" -- which is exactly the road|road row, so it would
   work, but the plane stops being one region and the model gets its junction
   squares back through the side door.
3. **Do not cut the plane; carry shade per piece another way.** Not available:
   a Build sector has one floor shade, which is the whole reason overlays
   exist.

> **CLOSED 2026-09-02 (slice 2c): the splitter is built.** Even-odd chord
> pairing over all rings at once, so holes need no special case; area
> conserved exactly in integers on a concave plane, on a square with two
> island holes cut three ways, and on a U whose arms come back as two
> disconnected pieces. Slivers are absorbed and reported. The plane was NOT
> decomposed into convex pieces.
>
> ~~Recommended default: write the simple-polygon splitter (1).~~ It is the
> only option that keeps the model the supervisor just decided, it is exact,
> and it is bounded work with an obvious test -- area conservation across the
> pieces, and the pieces re-joining to the original. Option 2 would land
> faster and quietly undo the junction fix, which is the kind of trade this
> project has already paid for twice.

## 22. The light field needs its levels re-measured before it can quantise
    (2026-09-02)

Deliverable 3 asks for the sun as a directional source, lamps as point
sources, the field summed and **quantised to the campaign's levels**, and the
cut set as that field's iso-lines. The clipper and the domains are now in
place to do it; the levels are not.

What I have is E3M1 alone: over its 68 street sectors the floor shades are 8
on nine of them, 34 on seventeen, 32 on three, 24 on seven, and 44 on thirteen
-- and I read the 44 as the quay and the far bank, outside the lit street. So
E3M1 says three levels, 8 / 24 / 34, with 32 as a near-neighbour of 34 and 44
as something else entirely.

That is one map. Quantising the whole city's light to three levels taken from
one map is the same shape of mistake as the continuity threshold and the
magnitude envelope: a number that looks measured but has a sample of one, and
both of those had to be re-thresholded once the corpus was actually asked.

> **ANSWERED 2026-09-02 (slice 2d), and the decision holds with one premise
> corrected.** Measured over the 38 campaign maps with outdoor ground: the
> step's MEDIAN is exactly 12 (not its mode -- the distribution is flat and
> the commonest value, 16, takes 9%), half of all boundaries lie in [8, 16],
> and at a ten-per-cent significance floor the median map uses 3 levels with
> 81% using 4 or fewer. So `base + k*12`, capped at four, is right; "the
> campaign's modal shadow step" is not how it was arrived at.
>
> ~~Recommended default: measure the levels over every campaign map's outdoor
> street sectors before quantising, and state how many levels the corpus
> actually uses rather than adopting E3M1's three.** If the corpus turns out
> to cluster at three, the number is E3M1's and now it is also everyone's; if
> it clusters at four or five, three would have been flattening the city's
> light for no reason. Either way the penumbra question answers itself --
> section 17's "penumbra only where the corpus measurement says so" cannot be
> settled without this measurement, and I have not made it.

## 23. Who owns a sector's shade? (2026-09-02)

The light field now writes `floor_shade` on every outdoor piece. So do three
other things already in the build: `lighting.flicker_lit_sectors`, LightBomb's
own pass, and any Link-driven shade wave a mechanism declares (P8's
`kCmdLink` receivers -- E1M1 s124, the city's s24).

Nothing says who owns it. That is precisely the shape of the collision P13
found between `glass.glaze` and `texture_frame.frame_map`, where two passes
wrote the same four fields and **pass order decided per record** -- fifteen
panes kept one number and nine got the other, and nobody chose. It was
invisible until somebody diffed.

Deliverable 4 of this slice is the answer and it is not built: one two-column
table, channel -> ADDITIVE | EXCLUSIVE, with light additive and floor z,
sector type, frames and holder roles exclusive; a second writer on an
exclusive channel raises by name; PRESENTATION claims yield and are listed.

> **Recommended default: build the channel table before anything else writes
> to a map, and make shade ADDITIVE rather than exclusive.** A shade wave, a
> lamp pool and the sun are all deltas, so summing them is both the physically
> right answer and the one that needs no arbitration -- which leaves the
> arbiter for the genuinely exclusive channels. The alternative, making shade
> exclusive and letting the sun win, would silently drop every Link-driven
> light in the city, and P8 measured 146 of those in the campaign.

## 24. Does the field's depth mean twelve, or does it mean base plus twelve?
    (2026-09-02)

The light field and LightBomb now meet, and I have not tested that they mean
the same thing by a number.

`light_field` gives each piece a DEPTH -- 0, 1, 2, 3 -- and `shade_for(base,
k)` turns that into `base + k*12`, an absolute shade. `lightbomb.
apply_shade_channel` sums DELTAS into a sector's existing `floor_shade`.
Nothing converts one to the other, and the obvious reading is that a piece at
depth k contributes `k*12` as its delta, leaving the region's own base where
it was.

That reading is probably right and it is an assumption. If it is wrong -- if
the field's base is meant to replace the region's rather than add to it --
the whole city comes out one step too dark, and **every gate in this slice
passes anyway**, because they all check the field's shape (levels, bearings,
step interval) and none checks the shade a sector actually ends up with.

That is the same hole the 8x texture regression went through: relative checks
all green, one absolute number nobody looked at.

> **CLOSED 2026-09-02 (slice 2e).** The conversion is `k * 12` and it is now
> read off a compiled map: full sun 8, one shadow 20, two overlapping shadows
> 32, a lamp in full sun 2. The fail-first breaks it to `k` and the absolute
> gate speaks while every shape gate stays green, which was the whole worry.
>
> ~~Recommended default: make the field contribute `k * 12` and nothing else,
> and add one absolute gate before the whole graph is built -- a sector known
> to be in full sun ends at the plan's stated lit base, and one known to be in
> one shadow ends at base + 12.** Two numbers, read off the built map, checked
> against the plan. It is the check the P13 regression should have had, and it
> costs one assertion.

## 25. Does a convex cut partition its input? (2026-09-02)

The whole-graph build fails on `independent regions col_a/row_1#0 and
col_a/row_1#3 have XY partial_area_overlap`. Two pieces of ONE island overlap,
so `overlay.cut_by_convex` is not partitioning the surface it cuts.

The suspect is `cut_region`'s sliver branch. When one side falls under
`MIN_PIECE_AREA` it returns the CUT piece and discards the scrap, rather than
returning the polygon whole on the side it is mostly on. If that is what
happens, `inside` and `outside` stop being a partition of the input and a
later edge can produce a piece overlapping an earlier offcut.

That is a hypothesis. I did not prove it, and guessing would be the fourth
guess in this pipeline rather than the first measurement.

What makes it worth an owner note rather than just a bug: **the clipper's
tests assert area conservation and never assert non-overlap**, and those are
different properties. `sum(inside) + sum(outside) == whole` is satisfied by a
partition AND by a set of pieces that double-count one region and lose
another of the same size. The same shape of gap as the 8x regression, one
level down.

> **CLOSED 2026-09-02 (slice 2f), and the assertion was right to come first.**
> It named the case: a single oblique cut gains 334 units over 276 million and
> puts a vertex 0.05 units inside its neighbour. The sliver branch was
> innocent of the overlap, though it had its own defect -- it reported an
> EMPTY side as an absorbed sliver, so the counts in slices 2d and 2e were
> mostly phantom. A clockwise shadow also cut nothing at all. Both fixed with
> fail-firsts.
>
> ~~Recommended default: before touching the sliver branch, add the missing
> assertion to the clipper's existing tests -- no inside piece overlaps an
> outside piece, and no two pieces of one side overlap each other -- and let
> it name the case.** Then fix what it names. If the sliver branch is
> innocent, that assertion is still the one the clipper should have had from
> the start, and it costs a few lines against a module three slices now
> depend on.

## 26. Weld the pieces, or snap the grid? (2026-09-02)

The captured cause: every oblique half-plane cut rounds its crossings to
Build's integer grid **independently**, so two pieces that ought to share an
edge diverge by a fraction of a unit. Measured on one island of the real
graph: 334 units of area gained over 276 million, and a vertex 0.05 units
inside its neighbour. `PlanarLayout` reads that as `partial_area_overlap` and
refuses the build.

It is not a tolerance question. Loosening the assertion would be choosing not
to see the thing it was written to see, and the compiler would still refuse.

**Weld.** After all cuts, run a T-junction pass over the piece set: every
crossing point one cut created is inserted into any neighbouring piece whose
edge passes within half a unit of it, so the shared edges become literally the
same vertices. Exact, no geometry moves, and it is the answer that also serves
interiors and any future cut. It touches every piece and needs its own tests.

**Snap.** Round every crossing to a coarser grid -- 8 or 16 units -- so two
independent roundings land on the same point. Perhaps twenty lines. It moves
geometry by up to half the grid, which on a 2048 kerb is invisible and on a
512 pavement path is a twelfth of its width, and it would quietly change the
band widths the E3M1 gate checks.

> **CLOSED 2026-09-02 (slice 2g) BY A GATE, not by a judgement.** G1 (vertex
> fidelity: every declared vertex present in the built map, unmoved) separates
> the options: snapping to 8 moves 2 of slice 1's 11 distinct points and G1
> names both, so snap fails by construction. The weld is built and closes the
> captured regression with zero partition faults. This should not have been an
> owner question -- an invariant existed and I did not look for it before
> asking.
>
> ~~Recommended default: weld.~~ The snap is tempting because it is small, but
> it buys correctness by moving the geometry the plan solved, and this project
> has already paid twice for a cheap fix that quietly changed a measured
> number -- the 8x scale and the junction squares. Welding leaves every
> coordinate where the solver put it and makes the shared edges true rather
> than nearly true. If welding proves harder than it looks, snapping to 8 is
> the fallback and the E3M1 band gate will say what it cost.

> **Decided by the supervisor (2026-09-02): weld, by edge identity, not
> by a half-unit search.** See section 25 of
> `projects/blood-city/reports/street-model-decisions-2026-09-02.md`.
> The choice was decidable by two gates the project already states
> (vertex fidelity; partition + PlanarLayout acceptance), so it should
> not have reached this queue; that is now a standing rule.

## 27. A T-junction the registry cannot see (2026-09-02)

**No invariant separates the two options here, which is why it is in the
queue** rather than settled by a gate.

The weld inserts a crossing into the edge it was computed from, keyed by that
edge's undirected identity. The graph's remaining failure is a different
shape: one island edge is abutted by three neighbouring pieces in
sub-segments, and those sub-segment endpoints were crossings on a DIFFERENT
edge -- piece B's corner happens to sit on piece A's edge without ever having
been a crossing of it. The registry has no record tying them, so the weld
cannot act.

**A. Edge identity plus containment.** After welding, insert any piece vertex
that lies within another piece's edge span. It closes the case, and it
reintroduces exactly the containment test that edge identity was chosen to
avoid -- with a tolerance, because a rounded corner is not exactly on the edge
it touches.

**B. Record the containment at cut time.** When a cut produces a piece, note
which existing pieces' boundaries its new vertices fall on, and register those
too. No tolerance at cut time (the geometry is still exact there), but it
means every cut consults the whole piece set rather than just its own input.

Both give the same map. A is a few lines and a tolerance; B is a wider change
with no tolerance. G1 does not separate them -- neither moves a vertex. G2
does not separate them -- both would pass. The wall counts would be identical.

> **CLOSED 2026-09-02 (slice 2h), and my framing of it was wrong.** Neither A
> nor B: edges have a GENEALOGY, and a split records its children's parentage
> so a crossing reaches any ring carrying its key or an ancestor. No tolerance
> constant anywhere.
>
> And the claim that no invariant separated A from B was false. A crossing is
> rounded PER COORDINATE, so it can sit up to 0.707 units off its edge --
> measured worst case 0.702 over 20000 random oblique edges -- and a half-unit
> containment misses every crossing rounded toward the far corner of its unit
> cell. That bound separates them, and I asserted "no invariant" instead of
> looking for one. From here that claim needs a fixture both options pass.
>
> ~~Recommended default: B, record it at cut time.~~ The argument is only that
> this project has repeatedly paid for tolerances that looked harmless (the
> 0.05 that read as an overlap; the exact-collinearity test that rejected its
> own crossings), and B is the option with none. But I want to record that
> the case for A is real -- it is small, local, and testable -- and that if B
> turns out to need the whole piece set threaded through every cut, A with a
> half-unit tolerance is the honest fallback rather than a defeat.

> **Item 27, decided by the supervisor (2026-09-02): neither A nor B as
> stated; edges get a genealogy (child -> parent recorded at the cut,
> crossings owed to every carrier of the key or its ancestors). A gate
> does separate the options: a crossing rounded 0.6-0.7 units off its
> edge, which a half-unit containment misses. See section 26 of the
> decisions document.**
