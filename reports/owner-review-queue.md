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

## 9. Which map did you see inside out? (2026-09-01)

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
