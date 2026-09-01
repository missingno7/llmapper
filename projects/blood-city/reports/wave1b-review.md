# City Enrichment Wave 1b — review sheet

Frames: `reports/looks/wave1b/frames/` (7, walk order). No game launched.
Districts touched: **Old Crossing**, **Market Slip**, and every district with
a shopfront (signage).

Wave 1b was the autonomous continuation. It cleared wave 1's own debt,
corrected two things wave 1 got wrong, and prepared the seam decision without
touching it.

---

## What to walk, in order

| # | frame | what to check |
| --- | --- | --- |
| 1 | `west_street_road` | the carriageway between its pavements |
| 2 | `west_street_kerb` | the 2048 kerb, and **now a street lamp standing on the pavement** |
| 3 | `spur_road` | the spur south carriageway |
| 4 | `lychgate` | the way in |
| 5 | `green_in` | turf, not tarmac |
| 6 | `green_path` | **new** — the dirt path, planting either side. This is the frame that shows the green working |
| 7 | `green_stones` | **re-aimed** — it faced a mausoleum wall in wave 1 |

---

## Part 0 — the walk-fix four, verified

All four had landed. Verified against the built map rather than assumed:

```text
crack barrier   1 thing, statnum 4, cstat 722, trigger_impact; 3 exploders   OK
key law         0 pickup-art faults                                          OK
shelf secret    leaf sprite wears bookcase front 31, recess 33; 0 secret     OK
                faults; the level declares its total
fabric repeat   DOOR-CURTAINS s3 [2.0,2.0,2.0], s53 [2.0,2.0,2.0],           OK
                s24 [4.0,2.0,4.0] -- the one deliberate outlier
                zoo curtain closed [2.0,2.0,2.0] open [0.08,2.0,0.08]
```

**But one of them was not GATED, and finding that out is the point.**

`measure_curtain` was written for the old opposed-cap model and routed on the
payload shape that model produces. When the curtain was rebuilt to the
tutorial's fin the shape changed — and the check silently stopped running.
**The zoo reported 13 of 13 conforming because the curtain was never asked.**

It is rewritten to the fin (one flagged wall, isolated motion, fabric on the
fin only, and the closed-span repeat within tolerance of natural) and routed
on the fabric TILE, which does not change when the topology does. The sweep
now checks **14** constructs, and there is a test that breaks the repeat and
watches the gate speak.

---

## Part D — wave 1's own follow-ups, all three done

**(1) Slot lattices that respect a notched outline.** Wave 1 laid its lattice
over the ground's bounding box and dropped 11 of 20 plants, because a green
with a church and two mausolea in it is mostly not green. The lattice is
oversampled and filtered against the room's actual outline now, with real
clearance from every edge.

```text
wave 1     9 planted, 11 dropped, no path
wave 1b   13 planted,  7 dropped, path laid
          (oak, elm, pine, 2 headstones, 5 bushes, 3 straw)
```

The path took four attempts and each failure was worth keeping:

- straight down the middle of the bounding box, it walks through the church;
- clear of the solids is not the same as inside the room — the ground's
  outline is notched, and a strip running past the end of the turf carves a
  hole through nothing;
- corner probes one unit inside pass while the strip's edge lies flush
  against a mausoleum, and a carve sharing an edge with a notch is degenerate
  — which surfaced, bizarrely, as **the cemetery overlapping a street two
  districts away**;
- and the carve must be in the ground's own coordinates. It has no frame of
  its own, so its local space IS world space; subtracting the bounding-box
  origin (which the roadways correctly do, because a street room *is* framed)
  put the hole a district away from the path standing in it.

It is now sampled down its centreline with a real clearance, and nothing
stands on it.

**(2) A consumer for the lamp slots.** Wave 1 derived them and placed
nothing. **6 slots, 6 lamps, 0 skipped**, on tile 640 — DWE3M1's
ground-standing street lamp, the same fixture the light pools use.

**(3) The green_stones pose re-aimed**, and a new `green_path` pose added.

---

## Part A — facade signage

Signage already existed and wrote 15 signs. What it got wrong was **how high**.

`reports/blood-lintel-band.md` measures a campaign sign letter at a median
**2.536 player heights above the street floor** (n=86, range 1.691–5.132,
cv 0.33). The city hung its frontages at **1.2–1.5** — below the whole
measured range, so every shopfront read as a notice rather than as a sign you
see from down the street. The nine frontages now sit at 2.54.

**A caution about which row of that report gets quoted.** The same table
gives a median of 0.725 player heights above *the opening's own head*, and
that is a different, much noisier anchor (cv 0.79 against 0.33). The floor is
the stable measurement and it is the one used. The brief for this wave asked
for "~2.5 player heights above the opening's head", which mixes the two.

Interior notices — CRYPT, PUMP HOUSE, STAFF ONLY, OUTFALL, NO EXIT, STAGE
DOOR — keep 1.3. The evidence is about signs seen from the street; applying
the street median to a service corridor would put STAFF ONLY two and a half
bodies up a wall.

15 signs, 114 letters, 0 missing.

---

## Gates

```text
structural validation   0 errors, 0 warnings
rules                   97 diagnostics: 96 notes, 1 warning, 0 errors
zoo sweep               14 constructs (was 13 -- the curtain now runs), all conforming
budget                  258 sectors, 1680 walls, 428 sprites
                        walls cap 7000 -- 5320 spare
frames                  7, fixed-pose, XMapEdit observer
```

---

## Part E — the seam decision brief

Written, **implemented nothing**, appended to
[`reports/owner-review-queue.md`](../../../reports/owner-review-queue.md).

Three options quantified: paired half-roads (small, contained, riskiest —
needs a deferred join, the mechanism that fought the compiler four times in
wave 1); moving the seams off the centrelines (a data change, not a code
change, because nothing in the level program is seam-aware today); streets as
first-class tree nodes (largest, and the only one that also solves the next
problem). **Recommended: move the seams.**

The measured size of the blocker: **8 of 13 roadable runs sit on a seam**,
and Theatre Row and Foundry Ward have no roadable run that does not.

---

## Not done

**Part B (storefront glass)** and **Part C (venue presentation chains)** were
not started. The Aldermack still has no curtains and `l3_theatre`'s gib-wall
pane is still hand-built.

Nothing is half-built.

---

## For the promotion queue

1. **Storefront glass** (queue rank 13) — still unpromoted.
2. **The venue presentation chain** — curtain plus a command-5 Link, with the
   arbiter reporting the collision.
3. **Paired half-roads or a seam move** — blocked on the owner's answer.

---

# Continuation: Parts B and C

Frames: `reports/looks/wave1c/frames/` (3).

## Part B — storefront glass, promoted

`projects/blood-city/level/glass.py` had the E6M1 recipe read to the field
and had been glazing Gravesend for phases. It was **city-local**, so no other
project could call it and the zoo's conformance rule could not bind it.

Now `bloodmap/glass.py`, with:

- **the HOLDER mediation** — `holder(inside, outside, span)`. A window is a
  relationship between two rooms, not a property of a wall, and one room
  cannot hold a pane. Glazing a one-sided wall gives a translucent pier;
  `glaze` reports `skipped_solid` rather than quietly doing nothing.
- **`pane_faults`** — the two ways a pane dies silently. Without an XWALL it
  is permanent (NBlood needs `wall.extra > 0` before it even looks at
  `triggerVector`); on a one-sided wall it has nothing behind it.
- **`breaks_to`** — what a cstat becomes after the break, so a map's
  post-break topology is readable without running the engine. kWallGib is
  the one mechanism in Blood that REOPENS a blocked wall.

**A zoo exhibit came with it**: SHOP WINDOW, in the SHOP section — a display
box with two urns and a pane between it and the bay. 2 panes (both sides of
the pair, which is what `trTriggerWall` clears), 3 solid walls correctly
skipped, 0 faults.

**And the conformance rule was not binding either new module.**
`COVERED_MODULES` in `tests/test_pattern_zoo.py` is an explicit tuple, and
`bloodmap.glass` and `bloodmap.street` were not in it — so a promotion could
land with nothing holding it to anything. Both are added; `street`'s
functions carry honest skip reasons (the zoo is a gallery of bays with no
street runs and no district seams, so there is nothing for a carriageway to
be laid on — its exhibit is Gravesend's own west street).

City: 24 panes, 0 faults. Zoo: 26 self-read claims, 14 constructs conforming,
0 errors.

## Part C — the Aldermack's curtain

Built, wired, and **it reports one deviation against the tutorial**, which is
the authoring-loop law doing its job.

The city speaks the levelprog tree and `mechanism.curtain` speaks
PlanarLayout, so this follows `turnstiles.py`: a new `mechanism.curtain_spec`
returns the FACTS — outline, fabric edges, flagged edge, marker points and
the closed-span repeats — and `level/curtains.py` builds the geometry in the
tree, then furnishes on the compiled layout.

```text
markers  2      state-anchored: type 3 for OFF, type 4 for ON
flagged  1      the fin's free end, and only that
fabric   3      the tab's two sides and its end
buttons  3      an XWALL on each cloth face, as the tutorial wires a shove
closed texel scale  [2.0, 2.0, 2.0]   -- exactly natural
```

**The fabric law holds to the unit.** The repeat is authored for the CLOSED
span, so the drape reads naturally drawn across and squashes as it gathers.

**The deviation, reported by the city's own build output:**

```text
curtain s37: motion_set [23, 37]
    DEVIATES isolation: wanted [37], found [23, 37]
```

The fin is cut as an ISLAND in the auditorium floor, so all eight of its
walls are shared with the house — including the tab's, where
DOOR-CURTAINS s3 has its tab walls ONE-SIDED. The motion therefore drags the
auditorium's hole along with it. That is geometrically consistent (the hole
tracks the fin exactly, and the swept gate passes 1/1 sound with 0 problems)
but it is **not how a curtain is built**: the tutorial's hangs in a wall
opening with solid ends, so nothing outside it can move at all.

The template was NOT loosened to make this pass. Relocating the curtain into
the wall between stage-side and house-side is the fix, and it is filed below.

**The command-5 Link is wired**: the curtain transmits on channel 341 with
`CMD_LINK`, the stage receives it as a shade wave. kCmdLink is sent outside
`SetSpriteState`'s edge guards precisely because it couples state
continuously — the light tracks the curtain rather than switching when it
finishes. The arbiter was asked before the link was wired and reported **no
collision**: the curtain's rx and tx are different slots, and the stage's
shade wave is a different sector.

**On the frames:** `curtain_close` shows the fin at its SAVED pose, which is
ON — gathered to one side as a narrow ribbon. That is correct. The closed
pose is the one you see in game with `state` 0, and seeing it here would need
the state-preview snap the zoo uses.

## Still not done

- The curtain's isolation deviation (above).
- A state-preview pair for the city's mechanisms, the way the zoo has one.
- The seam decision remains with the owner.

## For the promotion queue

1. **Set the Aldermack's curtain in a wall, not in the floor** — so its tab
   is one-sided and the house cannot move.
2. **State-preview pairs for blood-city**, so a city mechanism gets the same
   OFF/ON read-back the zoo's do.

---

# P1: the curtain family, and why the deviation had a second half

Frames: `reports/looks/stateOFF/frames/` and `reports/looks/stateON/frames/`
— **the state pair this sheet filed as missing**.

| pose | what it shows |
| --- | --- |
| `stateOFF/stage_side` | the fabric **drawn across** the proscenium, at natural scale, filling the walkable band |
| `stateON/stage_side` | the same view with the leaf **gathered** and the stage open |

## What the deviation actually was

Wave 1b reported the curtain deformed the house and left the template strict.
Re-reading the engine found the other half:

**`engine.cpp:4938-4940`** — a wall's middle band is drawn from `picnum` only
when the wall is ONE-SIDED, and from `overpicnum` only when it is two-sided
AND one-way. A two-sided unmasked wall reaches its middle band through
neither. The city's fabric was on two-sided unmasked walls with a ceiling
step, so it drew as a **valance above head height and nothing where a body
walks**. "Not built as a curtain" also meant "not visible".

The cause of both halves was one thing: the tree idiom carved the fin's own
outline, so hole and room were the same polygon and all eight walls paired as
portals. DOOR-CURTAINS s3 cuts the slot as a **notch** whose interior belongs
to nobody. The house now gives up the doorway rect and the notch stays solid.

```text
before   motion_set [23, 37]   fabric_visible 0/3
after    motion_set [37]       fabric_visible 3/3   texel [2.0, 2.0, 2.0]
```

## The census

43 campaign maps, **39** type-614 sectors wearing 146/147: **26 one-leaf, 12
two-leaf, 1 three-flag** (E2M1 s95). A first pass said 40 and 13 — the extra
was a second editor autosave still in the campaign directory, now in the
holding pen (queue item 8).

## Two templates that would have rejected the tutorial

Both were nearly shipped, and both are the same mistake:

- **"every fabric wall visible"** fails DOOR-CURTAINSD s4 — six fabric walls,
  two visible, and those two are the masked pocket pair. The rule is at least
  one **per leaf**.
- **"texel scale 2.0 ± 0.35"** fails s2 (1.33) and E1M1 (2.83, 4.0). Over 355
  fabric walls in the originals, 2.0 is the mode (171) but the envelope runs
  1.0–8.0. The constructor authors the mode; the gate flags the envelope.

## What the Aldermack's curtain now reads as

```text
leaves 1 | slot void | fabric 3 walls, all one-sided | push on all three
motion_set [37], no undeclared neighbours
closed texel scale [2.0, 2.0, 2.0]
link: command 5 -> stage s24 (rx 341, amplitude -24, shade 32 -> 8)
conformance: no deviations
```

**Owner question (queue item 7):** one leaf or two. 5120 is inside the
attested one-leaf range (max 6400) and 768 beyond the widest two-leaf sector
the campaign has. Recommended default: leave it at one.

## Zoo

A **CURTAIN PAIR** exhibit beside the one-leaf CURTAIN — two leaves
converging, tips flagged opposite ways. 33 exhibits, 27 self-read claims,
15 constructs conforming, 0 errors.

### The "imprecision" was a defect, and the number found it

This sheet first recorded the two-leaf repeat as an imprecision: derived from
`span/2` = 1536 while the swept closed length measured 1280, leaving the pair
at texel 1.67 instead of 2.0. Inside the attested envelope, so every gate
passed it.

**It was not an imprecision. The two leaves were travelling OUTWARD.**

Measuring where each tip actually goes: the west leaf's tip sat 128 inside
the doorway and moved to 1280 *past its own jamb*, and the east leaf did the
same in the other direction. The pair rested OPEN and "closing" retracted it
out of the opening entirely. The 256 was the two retractions, not a pocket
mouth.

The cause is which leaf carries which flag, and it is not free.
DOOR-CURTAINSD s2 settles it: its span runs y −3072 (low) to −1024 (high),
its marker delta is +960 toward high, and the LOW-end tip carries `0x8000`
AGAINST while the HIGH-end tip carries `0x4000` WITH. Ours had them the other
way round. Swapped, both tips close to exactly midspan, `closed_len` is 1536
= span/2 as the derivation always assumed, and the texel scale is **2.0 on
all six fabric walls**.

Worth stating plainly: a number that sat inside a tolerance was the only
visible trace of a mechanism that worked backwards. The envelope check
passed it, the conformance passed it, and the swept gate passed it.
