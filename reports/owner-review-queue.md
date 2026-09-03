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
## 28. E3M1 decompiled, layers 1-3: what the readers found in the writer (P15, 2026-09-02)

The experiment of decisions section 23 on E3M1. Every number below is read
off `maps/blood/campaign/E3M1.MAP` by a reader in `bloodmap/`, and each
question names a node id in its layer's review pack
(`projects/e3m1-decompiled/review/layer<N>.html`). No writer module was
touched.

**28a. `joins.py`'s pavement|pavement row cites two sectors that are not
pavement.** The row's evidence reads "E3M1 s10/s11: a pavement-only path
between abutting islands". Both sectors have `floor_z == ceiling_z == 8192`:
zero clear height, ceiling tiles 414 and 401. They are solid masses -- Build
draws nothing inside one and no body stands in it. The ROW is still attested
(14 pavement|pavement records in E3M1, between the shadow-cut pavement
bands); only its citation is wrong.
*Recommended default:* correct the evidence string to name the shadow-cut
bands, and leave the row. Node `row:pavement|pavement|equal`, layer 3.

**28b. `TILE_CLASSES["facade stone"] = 400` is our choice, not E3M1's.** All
3 road|end_wall records wear 414 and all 3 block; the 13 pavement|end_wall
records wear {414: 6, 181: 2, 384: 2, 417: 2, 488: 1}. The kerb row by
contrast is exact: 11 of 11 road-side records wear tile 6, and none blocks.
*Recommended default:* keep 400 as Gravesend's choice, record 414 as E3M1's,
and mine the class over the campaign before either is called a default.
Node `kind:end_wall`, layer 3.

**28c. Four "end wall" records do not block, and all four face a mover.**
Sectors 172 and 174 carry sector type 600. The reader classifies them as
wall-top masses because at rest nothing can step onto them, and the join
table's blocking clause is then wrong about them and right about the eleven
static records.
*Recommended default:* a raised outdoor mass carrying a sector type is a
mechanism at rest, not an end wall; the reader should name it apart so the
end-wall row keeps its blocking clause. Node `kind:end_wall`, layer 3.

**28d. E3M1 restarts its materials at corners.** 514 of 1537 same-tile joins
continue in u (33.4%): 88% of collinear solid-solid joins, 51% of
solid-solid bends, 15% of solid-portal reflex corners. Only 779 of 2481
records (31.4%) sit in a shared projection at all. The writer's
`RUN_BREAK_DEGREES` of 100 carries a run straight through a bend.
*Recommended default:* change nothing yet -- decide the bend break on a
campaign-wide census, not on one map. Node `surface:0898`, layer 2.

**28e. The join table describes the street and nothing inside the
buildings.** 1312 of 1386 two-sided records (94.66%) are pairs with no row,
and 1122 of those are interior|interior.
*Recommended default:* that is the table's honest scope; adding indoor rows
should follow an indoor census. Node `level`, layer 3.

Confirmed, not disagreed: the rise is 2048 on 11 of 11 steps, measured; the
road is the network's base plane at z 10240 and is recovered without looking
at tile 352; exactly three end walls are met by a road record, and they are
s0, s339 and s343.

## 29. E3M1 layer 4, and two defects the readers found in the writer (P15, 2026-09-02)

Every number is read off `maps/blood/campaign/E3M1.MAP` by `bloodmap.read_islands`
and `bloodmap.read_light`. Node ids are in `projects/e3m1-decompiled/review/layer4.html`.

**29a. E3M1's own shadow step is 24-26, not 12, and 20 of its 22 boundary
records fall outside the gate's envelope [8, 16].** The map the city's street
language was read from fails the light gate the writer enforces. What holds:
the lit base is 8 (as cited) and the field has 3 significant levels (inside
2-4). What does not: `base + k*12` reproduces only shades 8 and 32; E3M1 also
uses 14, 24, 34 and 46, and 15 of its 24 street sectors fit no level.
Re-measured over the campaign myself, two ways, and the definition of the
network moves the answer: over ALL parallax sectors, 38 maps, 1496 boundary
records, median 12, 53% inside [8, 16] -- which reproduces decisions section
21 exactly; over the largest outdoor component only, 398 records, median 15,
43% inside.
*Recommended default:* keep 12 and the envelope as CAMPAIGN values, state that
E3M1 is outside them, and make the gate say which network it means -- the
number depends on that and the gate does not currently say. Node `field`.

**29b. `overlay.kerb_records` claims 81 kerb records where E3M1 makes 11.**
Replayed over the three islands the reader recovered, it emits one entry per
edge of the island's outline and never reads its `ground_outline` argument, so
it asks for a kerb on the 56 edges facing the void, the 18 facing an interior
and the 13 facing an end wall. The 11 it gets right are exactly the map's 11,
all wearing tile 6, none blocking.
*Recommended default:* `kerb_records` should use the `ground_outline` it
already takes and emit a record only where the island's edge is also a ground
edge. A writer change, reported and not made. Node `islands`.

**29c. `joins.is_water`'s panning clause never runs on a decompiled level.**
It reads `getattr(sector, "extra", None)`, which is `None` for every `LevelIR`
sector -- they carry the extra under the key `"blood"` -- so only its palette
clause fires. On DWE3M10, the map the shore and sea rows were mined from, that
loses 4 of its 22 panning sectors (393-396, palette 0). E3M1 has no water, so
nothing here depended on it.
*Recommended default:* give `is_water` the accessor `assembly._x` already has.
`bloodmap.read_joins.reads_as_water` is the reader-side version and the
measurement above is what it found.

**29d. The casters are not recovered, and the reader says so.** The sun's
throw comes back as 479 build units against the cited 478 -- 0.18 degrees, the
axis from 14 oblique boundaries spanning 82.87-86.42 and the sign unanimous
(6 far-end boundaries, 6-0). But the test for WHICH mass threw each shadow --
the shadow's side edge should start at a mass corner up-sun -- is a tie: 8 of
16 oblique edges have a mass corner at their up-sun end and 8 have one at
their down-sun end.
*Recommended default:* report the bearing as recovered and the casters as not.
Node `depth:0`.

**29e. The wave exclusion is a true zero here.** Sectors whose XSECTOR carries
`amplitude` or `shade_always` drive their own shade and are excluded from the
shade-boundary population before anything is measured. E3M1 has 61 of them;
exactly one (s174) is in the street network and it lies on no same-z shade
boundary, so the exclusion removes 0 of the 22 shade-edge records and one
sector from the field's levels. The rule is in place and untested by this map.

Also corrected, in this agent's own work: an earlier pass read Blood extras
through an `extra` attribute and reported E3M1 as having none. It has 133
XSECTORs, 41 XWALLs and 716 XSPRITEs, and
`tests/test_read_overlays.test_the_extras_are_read_through_the_key_a_levelir_uses`
now fails if that is read the wrong way again.

## 30. E3M1 layers 5, 6, 7, 8, and the decompilation as a fact store (P15, 2026-09-02)

The store is `projects/e3m1-decompiled/facts/`, one JSONL per predicate with
provenance on every derived row; `source/query.py` computes every number any
report quotes. Node ids are in the layer packs.

**30a. The plan's width class does not say whether it means the carriageway
or the full width, and E3M1 lands in different classes either way.** Its main
street is 7.28 pu of carriageway (nearest class AVENUE, residual 0.28) and
10.78 pu with its pavements (still AVENUE, residual 3.78); its east arm is
4.00 pu of carriageway (LANE, residual 1.00) and 6.00 with its pavement (ROW,
residual 0.00). The reader gives both because the plan does not say.
*Recommended default:* the FULL width. `city_plan`'s grid is a running sum of
street widths and block columns, and a pavement is part of the street rather
than of the block — under that reading E3M1's east arm is a ROW exactly, with
no residual at all. State it in `city_plan.py`. Node `streets`, layer 7.

**30b. A block recovered by connectivity is a whole side of the city.** 23
blocks; the largest holds 123 sectors in a 14.62 x 12.00 pu envelope, because
E3M1's masses run together through their interiors. `city_plan`'s block is one
buildable rectangle.
*Recommended default:* the reader should cut a mass at its street frontages.
Named as missing rather than guessed. Node `blocks`, layer 7.

**30c. The schematic costs 12% of the ground at the median and 78% at the
worst.** Every plan element is a rect and a sector is not: E3M1's ground fills
its own bounding rectangles 0.882 of the time at the median, 0.219 at the
worst.
*Recommended default:* state it rather than bound it, and have the solver's
own output carry the same number so the two can be compared. Node `level`,
layer 7.

**30d. Five of E3M1's 136 sentences use a (type, shape, slot) combination the
taught course never shows** — s41's type 615 with "part of the sector travels"
and a shade wave, for one. The course teaches 6 lessons of type 615 and 77
constructs, and 3 of them have that shape; none has that slot set.
*Recommended default:* a finding, and the interesting one — the course teaches
each slot alone and the campaign combines them. It belongs in the curriculum's
own gaps list. Node `sentence:sector:41`, layer 5.

**30e. All three of E3M1's room-over-room stacks carry the same fault: the
floor marker sits 256 units below the plane it links.** Three of three is a
convention, not a mistake, and `curriculum.stack_faults` reports it as
"the floor marker floats".
*Recommended default:* the fault text should say "256 below, as all three of
E3M1's are" — a convention the campaign keeps three times out of three is not
a defect our checker gets to name. Node `kind:room_over_room`, layer 5.

**30f. A chain is one sentence and our writer has no construct that fans out
like one.** E3M1's biggest is one channel (116) whose two switches tell 159
records at once; 63 of its 69 channels have receivers.
*Recommended default:* one sentence per channel, with the fan-out as a
parameter. Splitting it per receiver would make the collapsing house 159
mechanisms that happen to share a number. Node `sentence:channel:116`, layer 5.

**30g. Layer 8 refuses 84 of 136 mechanisms and 26 of 36 grouped spaces, and
names by the curriculum's own file names.** A mechanism is named by the modal
PREFIX of the lesson files teaching its (type, shape), taken only at a 60%
majority: 16 sentences come back `door` and 36 are candidates where no prefix
holds a majority. Places are named only where exactly one measured rule fires:
4 `stepped_run`, 2 `street`, 4 candidates, 26 refusals.
*Recommended default:* keep the refusal rate. What is missing is named rather
than guessed — what distinguishes a Blood interior is its furniture, and the
prop reader is not wired into this layer. Node `level`, layer 8.

**30h. E3M1's boundary is 16 terminations, 65 records of void and 19 ways
in.** A residue of zero on the edge classifier is easy, because
`building_back` catches every one-sided record; the number that measures the
edge FAMILY is its own share. Node `edge:building_back`, layer 6.

**30i. The review pack's script was dead in every pack for one commit, and
the tool exited 0 the whole time.** The page is built by one f-string, so a
JavaScript `\n` has to be spelled with TWO backslashes in the Python source;
the fact panel and the aspect selector I added used one, the f-string emitted
a REAL newline into a JavaScript string literal, and the script died at the
first one — blank tree, inert map, valid-looking HTML. Fixed, and
`tests/test_review_pack.py` now builds a pack and refuses one whose script has
a string literal spanning lines, whose JSON constants do not parse, or whose
`build` has lost the "+Y down. Never flip." orientation.
*No default needed; recorded because it is the project's own lesson (verify
the thing, not the call) failing in a new place: a tool that returns HTML is
not evidence that the HTML runs.*

## 31. Two fact stores landed on the same day with the same name (P15, 2026-09-02)

`bloodmap/facts.py` arrived on `blood-city-arcade` (9a76dde, "The compiler
writes its facts beside the map") while a file of the same name was being
written here for the decompilation. Both implement section 2.1 of
`RESEARCH-OVERLAPPING-LAYERS-2026-09-02.md`, from opposite ends, and neither
knew about the other.

**Resolved without touching the writer:** the compiler keeps `facts.py`; the
reader's is now `bloodmap/read_store.py`, and its docstring says why there are
two. Nothing of the compiler's was edited and the E3M1 store is byte-identical
across the rename.

They are not interchangeable:

| | compiler (`facts.py`) | reader (`read_store.py`) |
| --- | --- | --- |
| row | `{key, lod, source, fields}` | `{id, ...attrs, _from, _reader, _layer}` |
| predicates | 14, a closed tuple | 37, declared with what each row is |
| holds | the declarations a build makes | the map's own records, plus what readers derive |
| ledger | `claims` | `claims`, `candidate`, `selection`, `conflict`, `residue` |
| gate | a pass at LoD N leaves every fact below N byte-identical | a claim reproduces its field |

**The question:** should they become one? The argument for is strong and it is
the project's own: with one store the compiler's facts and the reader's facts
are diffable directly, and *that diff is the symmetry test of decisions
section 20* — "decompile, recompile, diff STRUCTURE" becomes "diff two sets of
rows". Today the two shapes have to be translated before they can be compared
at all.

*Recommended default:* unify, on the READER's shape, with `lod` added as an
attribute — it is the superset (it holds base records, and the ledger's four
extra predicates), its provenance is per-row rather than per-declaration, and
its predicate table carries a description per predicate so a new one cannot
appear unannounced. The compiler's LoD gate keeps working as a query over
`_layer`/`lod`. But this is a writer change and it is P14b's to make or
refuse, so nothing was done to `facts.py` here.

## 32. Slice 4: what the readers found in the writer, and what the writer found in itself (P14b, 2026-09-03)

Every number here is read off `projects/blood-city/level/slice2-streets.MAP`
or off the campaign, and the four decided questions from
`projects/blood-city/reports/owner-review-queue.md` are folded in here --
that file was the wrong one and this is the queue.

**32a. A curtain at a shell's mouth drags the pavement's walls, and a welded
street has no jamb to give it.** The read-back leaves exactly one difference
per building and it is `members`: the sentence declares the door's own five
records and `motion_sim.drag_closure` finds it reaches sectors 35, 99 and 101
as well, because the weld made the door's corner and the pavement's corner one
vertex and `DragPoint` walks the ring through it. That is the owner's
motion-aperture law arriving from the other direction.

*Recommended default:* build the leaf in a SLOT -- Blood's own `void` dialect,
where the fabric walls are one-sided and the leaf retracts into solid geometry
-- so the moving vertices belong to nothing else. That is a geometry change to
`city.shell` and it is the next slice's first job.

*The A/B, and the fixture:* `void` slot (one-sided fabric, retracts into the
wall) against `pocket` (two-sided into a recess). `tests/test_rule_two.py`
passes under both -- neither changes which points move, which is the whole
point of a slot -- and they differ on one reading: a pocket needs a sector of
its own behind the jamb and a void does not, so the wall count moves and the
sector count does not. Measure both before choosing.

**32b. The shopfront doors are shutters, not curtains, and the reason is the
compiler's.** `kSectorSlideMarked` names its two positions by SPRITE INDEX and
the sweep validator runs during `PlanarLayout.compile`, before any sprite has
one: "sector 101 has no marker0", nine times. A marked slide needs a
first-class constructor that declares its markers as part of the layout.

*Recommended default:* keep the Z-motion shutters (type 600, two ceiling
heights, no markers) and add the marked-slide constructor when a mechanism
actually needs to slide sideways. The construct's NAME changed with the
mechanism -- a sentence that says "curtain" about a shutter is worse than a
shutter.

**32c. The compiler and the readers disagree about 296 joins, all of them at a
facade, an opening or a room.** With one store the diff is row for row: 1058
joins declared and 762 recovered with the SAME ID, and the 296 the reader
cannot name come back as `unknown_join`. The writer's table has FACADE,
OPENING and INTERIOR rows; `read_joins.surface_kinds` has no kind for a
facade or an opening, so it names those sectors `interior` or `end_wall` and
the pair falls through.

*Recommended default:* P15 adds the two kinds to the reader's classifier -- a
raised mass with a roof tile and a mouth is a facade; a sector between a
pavement and an interior at the pavement's z is an opening. Reader-side, so
it is P15's to make.

**32d. A reader defect the diff found on its first run, and it is fixed.**
`surface_kinds` names water, a horizon and a solid before it looks at the
street network, and then elected a base plane BY AREA over every sector of
that network, water included. Gravesend has 41 water and shore sectors and
1.2 billion square units of them, so the SEA was elected the base plane,
called the road, and every pavement and carriageway fell through unnamed --
124 `outdoor_ground`, 41 "road" and 900 unnamed joins. Both the election and
the naming now respect what the first pass decided; E3M1 reads exactly as it
did, 4 road and 9 pavement.

**32e. My shade census is not P15's, and the difference is the definition.**
Over the largest outdoor component I count 192 boundaries in 36 maps, median
13, quartiles 9 to 18.75; P15 counts 398 records, median 15. Over all outdoor
sectors I count 365 boundaries, median 12; P15 counts 1496 records, median 12
-- the medians agree exactly. The difference is the unit (I count a boundary
once where a pair of sectors may share several walls) and the wave exclusion.

*Recommended default:* the boundary is the unit, because the step is a
property of a boundary and not of a record, and both censuses state their own
population so the two can be compared rather than argued about.

**32f. The seven L3 interiors are not re-parented, and each is a port of its
own.** `l3_church`, `l3_foundry`, `l3_mall`, `l3_market`, `l3_sewer`,
`l3_shed` and `l3_theatre` are written against the old builder's API --
`build(city, street, ground, gates)`, `dress(district, ...)` -- and the new
pipeline takes declarations. The rooms they belong in exist, are named after
the plan's own venues, and are entered through a real opening behind a
working door.

*Recommended default:* one module per slice, each with its own read-back
sentence, so a failure names one building. The church is the smallest and is
the one to start with.

**32g. Four legs of the circuit are the sewer and are not built.** The
manhole, the trunk, the junction and the stair back up. Each carries
`built: false` with its reason, so an absent leg is a row rather than a
silence, and the other twelve are checked on the built map and all reachable.

**32a, withdrawn and corrected (P14b, 2026-09-03).** The recommended default
was a slot, and the diagnosis it rested on was wrong. A Z-motion door deforms
nothing -- it moves its ceiling, and no point in the map travels -- so the
`0x4000` on its leaf was a claim the mechanism never makes, and `DragPoint`
believed it. Unflagged, the read-back agrees on all nine buildings: 9
sentences, 0 differences. **No slot is needed for a shutter**, and the A/B
between void and pocket is not this question's; it returns when something in
this city actually slides.
## 33. The four reader corrections landed, and one of them moved a census (P15, 2026-09-03)

Items 28c, 30b, 30e and 30g of decisions section 30, all reader-side.

**33a. 28c: a raised outdoor mass that carries a sector type is now
`mechanism_at_rest`, not `end_wall`.** On E3M1 that is sectors 172 and 174.
Three consequences, each measured: the end-wall row's blocking clause now
holds on 3 of 3 road-side and 8 of 9 pavement-side records (the one remaining
exception is wall 1529, facing the raised ledge s237, which is not a
mechanism); layer 3 describes 66 records rather than 74, because a street
meeting a mechanism has no row — correctly, since what it meets depends on the
state; and the four boundary records that faced those masses are now `gate`,
which section 14 already names in the family.

**And it moved the 28b census by nearly half.** Before 28c the same census
found 285 `road|end_wall` records over 21 maps; after, 149 over 17. The 136
that left were band records against masses that move. Every one of the two
tiles that wore `facade stone`'s 400 left with them, so 400 is now attested on
**none** of the 191 end-wall band records in the campaign.
*Recommended default:* accept the narrower kind; the reports keep both figures
so the conditioning is visible. Node `kind:end_wall`, E3M1 layer 3.

**33b. 30b: a block is cut at its street frontages.** A mass is walked from
each frontage at once, breadth-first through the mass itself, and a block is
the part one street serves. E3M1's 123-sector mass becomes 74 + 49, fronting
`island:001` and the unnamed ground s65; blocks go 23 to 24. Sector 28 is
reached by both walks in the same step and is emitted as a `candidate` rather
than tie-broken — which building a shared back room belongs to is not a
reader's to decide quietly.
*Recommended default:* as built. Node `blocks`, E3M1 layer 7.

**33c. 30e: the stack marker offset is a convention, 38 of 38.** Every
campaign stack puts its UPPER marker 256 above the floor it links and its
lower marker at exactly 0 — all 38, no exception. `curriculum.stack_faults`
no longer calls it a fault; a marker at any OTHER offset still is, and the
manual's own negative example (`STACKS3DSPACES-BADROR`) is still caught by the
concavity clause. E3M1's three stacks now report no faults.
*Recommended default:* as built. `UPPER_MARKER_OFFSET = -256` carries the
count in its comment. Node `kind:room_over_room`, E3M1 layer 5.

**33d. 30g: the prop reader is in layer 8, and the refusal rate held.** Two
rules were added, both measured: one campaign-named, VISIBLE prop
(`furniture.FURNITURE` for the name, `blood_types.sprite_visibility` to drop
the quarter of sprites that are wiring) holding 60% of at least three; and
holding an authored bundle (`anchors.find_bundles`). On E3M1 the prop rule
fires once — space:023, 12 of 12 named props are planks — and the bundle rule
never, because its six bundles sit in singleton spaces the tree does not group.
Named 6 to 10, refused 26 to 25, candidates 4 to 1.

Most of that rise is a separate fix: **several rules firing with the SAME name
is not an ambiguity.** Three stepped runs in one space still say
`stepped_run`, and counting agreement as doubt had put four spaces in the
queue for nothing.
*Recommended default:* as built. The refusal rate is 25 of 36 (69%), which is
the honest answer for a map whose interiors are furnished with tiles nobody
has named. Node `level`, E3M1 layer 8.

## 34. The residue curve, and what it says about the readers (P15, 2026-09-03)

All eight layers over 43 campaign maps,
`projects/campaign-census/references/residue-curve.json`, full table in
`reports/residue-curve-2026-09-03.md`.

**34a. E6M7 cannot be decompiled, and it is layer 1's reader.**
`decompiler.decompile_level` raises `KeyError(144)` because `analyze_spatial`
returns no geometry record for that sector. The census runs the other seven
layers on it and records `layer1_error` on the row rather than dropping the
map.
*Recommended default:* leave it. One map of 43, in a reader that predates this
work and belongs to the space tree rather than to the street model; fixing
`analyze_spatial` is its own task with its own fixture. Node `level`, E3M1
layer 1.

**34b. Layer 2 makes 92-97% of every map's claims, and the curve is
therefore a wall count.** Surfaces and stairs are the only readers that reach
a map's bulk; layers 3, 4, 6, 7 and 8 together claim between 9 and 441 fields
per map against layer 2's thousands. The maps with the MOST street rank
lowest — E1M3 (17 road sectors), E2M9, E6M8 and E3M1 are four of the five
lowest street maps — because a street is outdoor sectors whose fields nothing
claims yet.
*Recommended default:* report the claimed share per layer and stop treating
the total as a ranking. The number worth watching for the sleep phase is
layer 3's, because that is the grammar; and it is 33, 12, 6, 2 and zero
everywhere else. Node `level`, E3M1 layer 3.

**34c. The second-map rule was ambiguous and the default decided it.** The
literal ranking gives E1M6, whose whole street is one road sector and four
kerb records and 96.6% of whose claims are layer 2; ranking without layer 2
gives E4M8, an 80-sector fragment. Neither is stable under a change to layer
2. The stated default, **E1M2**, is also the best on the criterion the sleep
phase needs: it is the only map besides E3M1 where the join table describes
more than a handful (12 claims), it has the same four road sectors, seven kerb
records, and 313 sectors against E3M1's 382.
*Recommended default:* E1M2, as chosen and recorded as a `selection` fact with
its criterion and the ambiguity that triggered it.
**Superseded by 36a:** re-running the census under my own step-2 reader
corrections removed the ambiguity and the rule now names E4M8 outright. Both
maps are decompiled; this paragraph is kept because it is what the choice was
made on.

**34d. Only 19 of 43 campaign maps have a street in the model's sense.** 37
have a base plane, which is the flag "any outdoor ground exists"; 19 have a
road with an island standing on it and a kerb at the join. The street model's
population is under half the campaign, which is worth stating before any norm
derived from it is called Blood's.
**Corrected: it is 16 of 43, and 36 with an outdoor network.** Item 28c
stopped reading a raised outdoor mass carrying a sector type as an island, and
four maps -- E1M3, E1M6, E2M9, E4M6 -- turned out to have no island on their
road at all. The population is smaller than this item first said, and it
shrank because a reader stopped mistaking mechanisms for street furniture.

## 35. The envelope was written twice, and the better one won (P15, 2026-09-03)

`read_light.shade_step_envelope` landed on main from queue item 29a (64eb4d0)
while the same function was being written here. Two implementations of one
census, like the two fact stores of item 31 — and this time one is measurably
better, so there was nothing to arbitrate.

**Theirs counts one entry per BOUNDARY; mine counted one per record.** A
two-sided wall is yielded from both sides and a sector pair may share several
walls, so mine weighed a boundary once per record it happened to have. The
duplicate is deleted and the census calls theirs, which is also what the
writer's gate calls — one census, not two.

They also differ on what "the largest outdoor component" IS, and that is worth
recording because the same name meant two populations for a day: theirs takes
every parallax sector, mine took only walkable ones and picked the largest by
AREA rather than by count. Theirs finds a component on 36 maps, mine on 21.

The published numbers move with it. Under `largest_outdoor_component`: 192
boundaries over 36 maps, median **13.0**, quartiles **[9.0, 18.75]**, the
gate's [8, 16] holding 50.5%. Under `all_outdoor`: 365 over 37, median 12,
quartiles [8.0, 16.0], 52.3%.
*No default needed; recorded because a reader that measures the same thing
twice is the thing the sleep phase exists to find, and this one was found by
a rebase rather than by the refactoring pass.*

## 36. The sleep phase over three decompilations (P15, 2026-09-03)

Measured by `projects/campaign-census/source/sleep_phase.py` over E3M1, E1M2
and E4M8; every number is a query over the three fact stores. Full write-up in
[reports/sleep-phase-2026-09-03.md](sleep-phase-2026-09-03.md). **No
constructor has been added to bloodmap — P14b owns `bloodmap/city.py` and this
is the list.**

**36a. The second-map rule now names E4M8, not E1M2, and I had already
decompiled E1M2.** Re-running the residue curve under my own step-2 reader
corrections moved six of 43 rows: item 28c stopped reading a raised outdoor
mass with a sector type as an island, so E1M3, E1M6, E2M9 and E4M6 lost their
islands and with them their streets. The street population falls from 19 maps
to 16, the ambiguity that triggered the stated E1M2 default is gone, and
"largest claimed share among street maps" gives E4M8 (6.693%) unambiguously.
I decompiled E4M8 as well rather than discard either reading: E4M8 because the
rule names it, E1M2 because the join grammar reaches it four times better (12
layer-3 claims over 313 sectors against 6 over 80).
*Node:* `projects/e4m8-decompiled/review/layer3.html`, node `level`.
*Recommended default:* keep all three. The rule was applied and its answer is
recorded; the extra map cost one afternoon and turned "what did both maps
need" into "what did three maps from three episodes need", which is a much
harder question to answer by coincidence.

**36b. `dressing(anchor, [prop…], *, spread=, facing=)` — 773 residue facts,
all three maps (330 / 371 / 72).** The largest construct gap on every map. The
readers exist already: `read_intent.named_props` names the props and
`anchors.find_bundles` groups them. Nothing authors them, because our language
can place a sprite only by absolute coordinate.
*Node:* `projects/e1m2-decompiled/review/layer5.html`, node `level`.
*Recommended default:* build it first. It is the biggest, it has a reader to
check it against, and it is the only one of the five whose residue is one fact
per record the player actually sees.

**36c. `stair(from_, to, *, treads=, width=, clear_height=)` — 321 facts, two
maps (219 / 102 / 0).** A stepped run as one construct owning every tread AND
the projection across them. The residue it lowers is in **layer 2**, not layer
1: a tread is its own sector, so its side walls have no same-material
neighbour and no frame can be attested on any of them. E4M8 has no stepped run
at all, which is why this is the one macro on two maps rather than three.
*Node:* `projects/e3m1-decompiled/review/layer2.html`, node `level`.
*Recommended default:* build it second, and make it a SURFACE owner rather
than a space group — the whole 321 is surface residue.

**36d. `channel(number, tx=[…], rx=[…], *, on=, wave=)` — 121 facts, all three
(41 / 72 / 8); `self_lit(space, amplitude=, phase=, wave=)` — 44, all three
(26 / 17 / 1); `breakable(surface, *, on=, reveals=)` — 24, two maps (18 / 6 /
0).** Three smaller construct gaps. `channel` is the fan-out our one-pair
writer cannot express. `self_lit` is a sector the reader reads perfectly and
files as residue only because it is not a mechanism. `breakable` is kWallGib
— and layer 8 refuses to name those because **the taught course has no lesson
of type 511 at all**, a mechanism the campaign uses and its own curriculum
omits.
*Node:* `projects/e3m1-decompiled/review/layer5.html`, node `kind:breakable_wall`.
*Recommended default:* all three, after `dressing` and `stair`. The type-511
gap in the curriculum is worth a note to whoever maintains the lessons; it is
not a defect in our reader.

**36e. The two largest residues on all three maps are not macro work, and
should not be counted as if they were.** 3814 facts are layer 2 unable to
attest a frame on a wall with no same-material neighbour or on one whose
neighbour breaks the projection — that is the Surface/Frame representation
item, and no constructor touches it. 2590 facts are the join table having no
row for two interiors meeting, in any height relation — that is the 11
proposed rows of item 32e, still none added. Together they are 78% of the
8227 residue facts across the three maps, and the five macros above account
for 1283, or 16% -- with 321 counted in both, because `stair`'s residue IS
surface residue, on the walls of treads that are each their own sector.
*Node:* `projects/e3m1-decompiled/review/layer2.html`, node `level`.
*Recommended default:* state the split in any roadmap item that quotes a
residue number, so "lower the residue" does not become "write more
constructors". The cheapest large win is the 11 rows; the largest is the
surface representation.

## 37. The three censuses landed: two of the writer's clauses are the campaign's exception (P15, 2026-09-03)

Numbers from `projects/campaign-census/facts/`, full table in
`reports/campaign-census-2026-09-03.md`. Node ids are in E3M1's packs.

**37a. The reader's `end_wall` kind is broader than "a termination".** It
means "an outdoor mass no body can step onto", which over 43 maps finds 285
`road|end_wall` records whose step quartiles are 32 768 and 263 168 — so a
quarter of these masses stand under two player heights and are ledges, not
walls. The census numbers below are conditioned on that kind.
*Recommended default:* keep the criterion (it needs no tile and it recovered
E3M1's three exactly) and add a REPORTED split at two player heights rather
than a second kind, so one census serves both readings. Node `kind:end_wall`,
E3M1 layer 3.

**37b. `TILE_CLASSES["facade stone"] = 400` is worn by 2 of 285 road-side
end-wall records — 0.7%.** The class has 27 members on that side; its
commonest is 449 (75, 26%), then 2490 (56), 91 (34), 28 (19). E3M1's 414 is 3.
*Recommended default:* keep 400 as Gravesend's stated CHOICE, and record the
campaign's distribution as the envelope rather than promoting 449 — a modal
tile over 21 maps is not a law, and section 22 says a choice needs only to lie
inside an attested class. Writer change, P14b's. Node `kind:end_wall`.

**37c. The `road|end_wall` row's `cstat=1` holds on 5.6% of the campaign.**
269 of 285 road-side band records do NOT block; 41 of 49 pavement-side do not.
It is not a height rule: blocking records sit at a median step of 88 064 and
non-blocking ones at 114 688, and the non-blocking set spans both the lowest
and the highest masses. E3M1's three blocking records are the exception the
row was written from.
*Recommended default:* drop `cstat=1` from the row and let gravity be the
gate, which is what 94% of the campaign does; keep it as a per-project choice
where a mass is low enough to walk onto. Writer change, P14b's. Node
`row:road|end_wall`, E3M1 layer 3.

**37d. 28d needs no change, and my own earlier reading of it was wrong.**
Report 28d said E3M1 "restarts its materials at corners" from its 50.6% on
bend solid-solid. The campaign is **67.9%** over 43 maps; collinear
solid-solid is 93.7% and reflex solid-solid 19.1%. Blood does carry a run
through an ordinary bend and stops at a reflex corner, which is exactly
`RUN_BREAK_DEGREES = 100`. E3M1 is the outlier, not the writer.

**37e. The eleven proposed indoor rows are one law, not eleven.** 49 821
`interior|interior` records fall in 25 classes, mirrored in pairs; the `draws`
column is `wallVisible`, the engine's own law, so the pairs say one thing:
*the band is on the side that stands above* — the kerb's law, indoors. The
evidence about authorship is the residual: 132 `level|level` records draw
where the geometry exposes nothing, and every one is overridden by hand (126
masked, 6 one-way).
*Recommended default:* one indoor row keyed on the height relation with a
tile class per context, plus a `masked` row for the 132. Proposed only; P14b
consumes it in slice 5. Node `level`, E3M1 layer 3.

**37f. The shade-step envelope depends on the network, and now says so.**
`read_light.shade_step_envelope(network=...)`: on
`largest_outdoor_component` — the definition section 30 names — 362
boundaries over 21 maps, median **15**, quartiles **[8, 18]**, and the gate's
current [8, 16] holds 45.3% of them; on `all_parallax`, 1362 boundaries over
29 maps, median 12, quartiles [8, 16], 56.2% inside.
*Recommended default:* the gate calls the reader and uses the quartile
envelope of the network it names — [8, 18] for the street definition. E3M1's
own 24–26 stays recorded as the precedent's value and outside both.

## 38. Two kinds, one recount and the first symmetry diff (P15, 2026-09-03)

Items 32c and 32e/37f done, plus `tools/symmetry_diff.py`. Numbers are queries
over `projects/blood-city/references/symmetry-diff.json`,
`projects/*-decompiled/residue-ledger.json` and
`read_light.shade_step_envelope`.

**38a. The city's 296 unnamed joins fall to 134, and the writer's table needed
no new row.** `read_joins.surface_kinds` gained `facade` (a raised outdoor
mass that holds rooms AND roofs them) and `opening` (a sector at the
pavement's own z with the pavement on one side and a room on the other).
`bloodmap/joins.py` has carried `pavement|facade`, `facade|opening`,
`interior|facade` and `opening|pavement` since the grammar was written — the
READER could not produce the kinds, so 162 of the writer's own rows were
unreachable on the map the writer built, and 122 more records were described
by a row that called a building a termination. 284 records now reach a row.
Everything the city still leaves undescribed is its waterfront: `water|water`
52, `shore|water` 38, `water|solid` 44.
*Node:* `projects/e3m1-decompiled/review/layer3.html`, node `level`.
The band census re-ran with the split and is exact: 179 records before, 179
after, 31 of them under the new name, nothing lost. It also says something new
— **tile 91 leads the buildings (15 of 27 `road|facade` records) and 2490
leads the plain terminations (28 of 116 `road|end_wall`)** — which is the
first evidence the campaign dresses a facade differently from a wall, and it
was invisible while the two were one kind.
*Recommended default:* keep both kinds. The roof test is RELATIONAL — the
mass's top must wear a tile one of its rooms wears as a ceiling — rather than
`ROOF_TILE = 379`, which is E3M1's own and would have been item 37b's mistake
a second time.

**38b. The two kinds cost the three decompiled maps nothing, and E3M1 has a
building.** Claimed share before and after: E3M1 3.883% / 3.883%, E1M2 4.083%
/ 4.083%, E4M8 6.693% / 6.693%, and every layer's claim count is identical.
What moved is residue: E3M1's layer 3 falls 1320 → 1316 and E1M2's 1224 →
1222. E3M1's four-sector mass 118/165/166/343 is a facade (top 379, and its
room is ceilinged 379) and sector 206 is a shopfront; E1M2 gains only sector
128; E4M8 gains neither, because its raised mass roofs nothing. E1M2's mass
126 holds three rooms and is NOT a facade: its top is 49 and its rooms are
ceilinged 68, which is the case the relational test exists for.
*Node:* `projects/e1m2-decompiled/review/layer3.html`, node `level`.
*Recommended default:* no action. Reported because a kind that changes a
claim quietly is worse than one that changes nothing.

**38c. A facade is still a mass, and forgetting that cost E3M1 two shadow
casters.** `read_light.casters` counted `solid` and `end_wall`; the day
`facade` was added, E3M1's up-sun corner count fell from 8 to 6 without any
geometry moving. It now counts `facade` and `mechanism_at_rest` too, and the
end-wall band census counts `road|facade` and `pavement|facade` beside
`road|end_wall` and `pavement|end_wall`.
*Node:* `projects/e3m1-decompiled/review/layer4.html`, node `islands`.
*Recommended default:* the rule is worth stating once: a new kind is a
REFINEMENT of an old one, and every reader that consumed the old kind has to
be told, or the refinement reads as a loss.

**38d. The envelope recount confirms 37f rather than moving it.**
`shade_step_envelope` already counted one entry per sector pair, so there was
nothing to correct: `largest_outdoor_component` gives **192 boundaries over 36
maps, median 13.0, quartiles [9.0, 18.75]**, and `all_outdoor` gives **365
over 37, median 12, quartiles [8.0, 16.0]** — the published numbers, unchanged.
The gate's chosen [8, 18] on the largest component holds on **58.9%** of
boundaries; [8, 16] holds on 50.5%. What changed is that the answer now states
its `network`, its `population`, its `unit` ("boundary: one entry per sector
pair, never per wall record"), and both map counts (`maps_read` 43,
`maps` 36), so a later reading cannot silently be a different one.
*Node:* `projects/e3m1-decompiled/review/layer4.html`, node `islands`.
*Recommended default:* keep [8, 18] on `largest_outdoor_component` and let the
gate print the population line the census now returns.

**38e. The symmetry diff's one content disagreement is mine, and a single lamp
causes it.** On 143 of the 146 sectors both halves name, the reader reads the
shade depth exactly ONE deeper than the compiler declared. The three it agrees
with — sectors 35, 54 and 73 — are the three carrying two lamps each, which
puts them at shade -4 against the compiler's declared base of 8.
`read_light.field` elects the base as the lightest shade with area, so those
three elect themselves and every other sector reads one level deeper. The
reader already excludes a sector that drives its own shade with a wave; it
does not exclude one a lamp lit.
*Node:* `projects/e3m1-decompiled/review/layer4.html`, node `depth:0`.
*Recommended default:* exclude lamp-lit sectors from the base election, the
same way `shade_edges` excludes a light wave, and re-run the campaign curve to
show what it costs. This is a reader defect and it is mine to fix; it is
reported first because it moves a number on every map and the owner should see
the measurement before the change.

**38f. What the diff says about the two stores, apart from that.** 2490 rows
declared, 8661 recovered, 1070 ids on both sides. The strongest positive
result is that **the compiler and the readers agree on the join grammar row
for all 924 records they both name** — `a`, `b`, `height`, `frame` and `shows`,
924 times, not one disagreement. The rest is shape rather than content:
`join` is `picnum`/`shade` on one side and `record`/`row`/`wears_tile`/
`blocking` on the other; the compiler declares a `join` for all 1058 two-sided
records where the readers emit `join` for 924 and `unknown_join` for 134 (the
same 134). `fill`, `void` and `lamp_delta` are declared and no reader recovers
them — three claims nothing checks. Two words are a real vocabulary gap
rather than a shape one: the compiler says `sea` where the reader says
`water`, and the compiler has no `solid` at all. Every other kind the diff
lists as unknown is known on the other side, in a different predicate, and
the report now says where.
*Node:* `projects/blood-city/reports/symmetry-diff.md` (the report itself; it
is not a pack, and this is the one item without a node id, because the diff
is not a reading of a tree).
*Recommended default:* take the three unchecked predicates one at a time —
`lamp_delta` first, because 38e says the reader needs a lamp model anyway.

**38i. I edited one line of a test P14b owns, and say so here.**
`tests/test_joins.py::test_e3m1_s_indoor_residue_falls` pinned E3M1's
undescribed count at 198; item 32c landed a day later and named E3M1's
shopfront an `opening`, so the two records between it and the room behind it
now reach rows the table already had, and the count is 196. The indoor law's
own result — the three `interior|interior` classes gone — is untouched and
still asserted. The protocol says a conflict in a file you do not own is
reported rather than resolved; this was not a conflict but a number my change
moved, and a red suite is not pushed, so the number is corrected with the
reason beside it.
*Node:* `projects/e3m1-decompiled/review/layer3.html`, node `level`.
*Recommended default:* fine as done. If P14b would rather own the edit, the
line to revisit is the comment above the assertion.

## 38. Slice 5: what landed, and three things the readers and I disagree about (P14b, 2026-09-03)

**38a. `read_surfaces`'s continuation law is not `AlignWalls`'s, or I have
misread one of them.** The stair fixture differs in exactly one field -- the
flank's `x_panning`, a cursor running the length of each side against zero at
every tread, with the repeat taken from each record's own length in both, and
a tread depth of 2816 so a record does not consume a whole number of tiles.
`read_surfaces` explains the ZERO case (0 broken of 20) and calls the
accumulated one broken (9). `AlignWalls` accumulates `x_repeat * 8` and would
call the zero case broken. One of the two is not the law I think it is.
*Recommended default:* P15 states the law `read_surfaces` fits in one
sentence, and if it is world-anchored rather than accumulated, the writer's
frame gate and the reader's residue are measuring different things and the
roadmap's "surface representation is 46% of the residue" needs that footnote.
The numbers are asserted in `tests/test_stair.py` so the day it changes,
something says so.

**38b. The waterfront is 134 records the join table does not describe, and
they are all of it.** `water|water|equal`, `water|shore|equal`,
`water|solid|equal` and their mirrors. The writer has SEA|SEA, SHORE|SEA and
SHORE|SHORE rows; the reader names those sectors `water`, not `sea`.
*Recommended default:* the reader's `water` and the writer's `sea` are the
same kind under two names, and the cheaper fix is the writer's -- rename `SEA`
to `WATER` in `joins.py` so one word means one thing on both sides. Writer
change, mine, held for slice 6 because it touches every waterfront row and
this slice's suite is already carrying four number updates.

**38c. Four of P15's tests asserted counts of a map I then changed.** St
Gallow's took eight sectors where the city had one, so `two_sided_records`
went 1058 -> 1112, `records_described` 924 -> 978, the nine shopfronts' sector
ids moved, and `same_id` went 924 -> 978. I updated the numbers and left the
claims alone, each with the reason in place; the residue stayed at 134 and the
agreement stayed total, which is the part that was being asserted.
*Recommended default:* a test that pins a count of the built city belongs to
whoever builds it -- either the number moves to a fixture P15 owns, or the
assertion becomes a relation ("every shared record agrees") rather than a
count. Reported, not decided.

**38d. Six L3 interiors remain, and the church is the pattern.** foundry,
mall, market, sewer, shed, theatre. The foundry is next and it is the
interesting one: a hall with a gallery over it is the same relation as rooms
in a mass, one level up, and whether that is the same word is what porting it
answers.

## 38. Triage by the supervisor (2026-09-03): the queue is closed at its defaults

Two walks of the built city produced twelve findings no gate had caught;
eight layer packs with 22 questions produced none, because the owner
cannot judge a layer without hunting every detail in the editor. So the
owner's channel is the walk, and this queue changes shape.

**Every item 1-37 is closed at its recommended default**, with the
supervisor's decisions in sections 16-32 of the street-model decisions
document taking precedence where they differ, and two edits: item 4
deletes nothing (the two Duke maps move; the autosave stays in the pen,
because nothing is deleted in this project any more), and item 32a is
withdrawn by its author.

**From now on a question reaches the owner only in one of two forms:**

1. **A walk.** A built map, a start position, and at most five lines of
   "look at this". The owner's findings come back as a list and each
   becomes a gate. Every slice ends with one.
2. **A fragment.** A sector set cut out of a map into a small playable
   map (`bloodmap extract` / `fragment`) with ONE line of question
   ("this is what the readers call a storefront bay: does it read as
   one?"), at most a handful per week, and only where a census or an
   invariant cannot answer. A question with no fragment or walk
   attached is answered by the agent with a census and closed.

Layer review packs remain the agents' instrument, not the owner's.

## 39. The owner's second walk consumed: a building is a void, and P15's facade kind has nothing to name (P14b, 2026-09-03)

Eight findings, each a gate that failed first and now reads 0 off
`slice2-streets.MAP`. Two of them changed the model rather than a number, and
both consequences land on the reader side.

**39a. A building is no longer a SECTOR, and `read_joins`'s `facade` and
`opening` kinds have nothing to name.** W12's engine reading is why:
`engine.cpp:4688` raises `umost` to the far ceiling line whenever one of two
ceilings is not parallaxed, so a roof-height slab beside the street cut off
everything above it behind -- 85 records of it. Sky against sky never clips.
E3M1's buildings are not sectors at all: its facades ARE the one-sided records
of its outdoor sectors, 122 of them, and the stone between its rooms is simply
absent. So a building here is a hole in the island with its rooms inside it.

The reader's classifier looked for a raised mass with a roof. There is none,
so the city now reads 0 facades and 0 openings where it read 9 and 9, and the
undescribed join classes are 188 -- the waterfront's 134 plus
`pavement|interior` and `interior|solid` at the mouths.

*Recommended default:* a facade is a one-sided record of an outdoor sector,
not a sector -- which is what P15's own E3M1 census already measures (28e's
122). The `opening` kind wants the other half of the same idea: a sector at
the pavement's z between a pavement record and an interior. Seven of P15's
tests in `test_read_facade_and_opening.py` are marked `expectedFailure` with
this reason rather than deleted, so the finding they record survives and the
suite stays green. P15's to re-derive; I have not touched the classifier.

**39b. "Realised" needed a third clause, and it was mine to add.** Slice 4
reported nine links `realised: true` on the evidence that a sprite carried the
tx and a sector carried the matching rx. `triggers.cpp:102-104` gates every
message on the send-when bit of the state being ENTERED, and all nine switches
had `trigger_on = 0` and `trigger_off = 0`: they could never send, and the
report said they were realised. **Realised now requires the send-when bit and
a body that can reach the sprite** -- the nine sat 5120 above the SHELL's
roof. The gate reads both off the map.

*Recommended default:* P15's link reader takes the same third clause before it
emits `realised: true`, so the two halves cannot disagree about what a working
wire is.

**39c. Street lamps are gone and the choice claim is rewritten.** Two attempts
produced a chained lantern hanging from the sky and a wall plate on a red wall
mid-street; the corpus said the same thing both times -- 0 visible outdoor
lamps in 43 maps. Gravesend now chooses what the campaign chose. The lamp
construct stays for a real ceiling. **A tile is chosen by ROLE and never by a
brightness statistic**, and `PROP_ROLES` is that table.

One consequence worth the line: with the lamps gone, the reader and the
compiler agree on EVERY shade depth. The 143-sector disagreement was three
sectors carrying two lamps each at shade -4, which moved the reader's elected
base and shifted the whole field.

## 40. The round trip, and the last per-layer questions (P15, 2026-09-03)

The owner's channel is the walk and the fragment, so this is the last item
that mentions a review pack. Numbers are queries over
`projects/*-decompiled/round-trip/*.json` and
`reports/questions-closed-2026-09-03.md`.

**40a. A transmitter that cannot send is not a link, and the city has nine.**
`read_mechanisms` now calls `conditional.can_send` before it writes a chain
sentence: the engine sends only when `txID` is set, `command != kCmdLink` (5)
AND one of `triggerOn`/`triggerOff` is set
(`triggers.cpp`, SetSpriteState 100-106, SetWallState 121-127, SetSectorState
138-155 — the same three clauses for all three record kinds). All nine of the
city's switches have a channel and both send-when bits at 0, so **no link on
that map is realised and no chain sentence is written**; the nine sprites
become residue naming their own channel, and the doors keep their own
sentences, because a door is a mechanism whether or not anything can open it.
The campaign is barely touched: E3M1 keeps 56 of 63 chains, E1M2 80 of 83,
E4M8 24 of 28. The 15 it drops are channels Blood itself shipped dead.
*Recommended default:* the rule as written. The seven dead channels in E3M1
are a finding about the shipped map, not about the reader.

**40b. All three decompilations round-trip byte-identical, and that is worth
less than it sounds.** `tools/round_trip.py` writes every claimed field back
from the claim's own value and copies everything else. E3M1: **4298 of 123280
fields rebuilt (3.49%)**, 0 misreadings. E1M2: 4114 of 112579 (3.65%), 0.
E4M8: 1631 of 27836 (5.86%), 0. Each rebuilt file is byte-identical to the
original — and 96% of those bytes were COPIED. The two numbers belong in the
same sentence every time one of them is quoted.
*Recommended default:* quote them together. "Byte-identical" alone reads as
"we understand the map"; the pair reads as what it is.

**40c. The result is not vacuous, and the tests say why.** A rebuild that
writes nothing is byte-identical too, so `tests/test_round_trip.py` first
proves the detector fails: a claim one off the original comes back as a named
misreading with both values, on a map field and on an extra. And the claims
are model REPLAYS, not read-backs — 3895 of E3M1's are "one frame replays
through `texture_frame.resolve_run`", 136 are a mechanism's state-anchored z
quartet, 97 are a stair's fitted progression. Writing those back and getting
the original byte is a test of the model.
*Recommended default:* keep the "what the claims promise" table in the report;
it is the only thing that stops the round trip being a copy check.

**40d. Nineteen open questions closed: 8 by invariant, 5 by census, 3 already
decided, 3 turned into fragments.** Full text in
`reports/questions-closed-2026-09-03.md`. Two are worth surfacing:
`reachability.classify_offmap` does NOT raise on every map — section 14 passed
it a `LevelIR` and it takes a `DiskMap`; on a DiskMap it reads E3M1 without
complaint, so the enclosure member has a reader after all and the caller is
the bug. And the singleton-space share is 28%, 35%, 30% across three maps
from three episodes, which makes it a property of the reader rather than of
the maps.
*Recommended default:* no owner action. The three fragments are the ask.

**40e. Two of the "nine P16 failures" were only a missing junction.** The
worktree had `maps/` junctioned and not `reference/`; adding it fixed
`test_pattern_zoo.setUpClass` and `test_stair`'s new surface test, and
un-skipped 27 tests. Eight failures remain and they are the genuine relative
`NBlood/` set. `tests/test_stair.py:99` hardcodes `wall_art_sizes("reference/
blood")` and would fail the same way on any machine without that directory.
*Recommended default:* P16's item still, with the count corrected from nine to
eight and one concrete line to fix.

**40f. Both fail-firsts landed on the same day, and their tests are re-pinned
rather than left expected-to-fail.** P14b's rebuild (item 39) set the nine
switches' `trigger_on`, so all nine city links are realised, nine chains are
sentences, and no switch is residue — the rule I added is now green on the map
that raised it. The same rebuild made a building a VOID in the island rather
than a sector, following `engine.cpp:4688` and E3M1's own construction, so the
city has **no facade and no opening left to name**. Seven of my tests were
marked `@unittest.expectedFailure` in that commit; an expected failure that
can never pass again is dead weight, so each is rewritten: the city classes
pin what the city IS now (10 solids, 3 end walls, 854 two-sided records, 666
described, 188 undescribed of which 134 is the waterfront), and the two rules
themselves move onto E3M1 and E1M2, where the kinds are attested. No
`expectedFailure` remains in either file.
*Recommended default:* fine as done. The order is worth noting: `facade` was
proposed against our own map and is now justified only by the campaign's,
which is the right way round and would not have been visible without the
rebuild.
