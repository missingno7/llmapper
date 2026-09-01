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
