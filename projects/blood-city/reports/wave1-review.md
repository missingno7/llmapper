# City Enrichment Wave 1 — review sheet

Two districts touched: **Old Crossing** and **Market Slip**. Frames are in
walk order under `reports/looks/wave1/frames/`.

This wave delivered **Part A (street anatomy)** and **Part C (the park
corner)**. Parts B, D and E were not started — see *What is not here*.

The headline is not the geometry. It is that **the city plan's own district
seams block street anatomy on eight of the thirteen roadable runs**, and that
is a finding about the plan, not about the constructor.

---

## What to walk, in order

| # | frame | what to check |
| --- | --- | --- |
| 1 | `west_street_road` | the carriageway running south between its pavements — Old Crossing |
| 2 | `west_street_kerb` | the kerb: a 2048 step up from road to pavement, which is E3M1's measured rise |
| 3 | `spur_road` | the spur south carriageway — Market Slip |
| 4 | `lychgate` | the way into the green from the west street |
| 5 | `green_in` | **turf, not tarmac** — the cemetery ground was wearing tile 352, the roadway tile |
| 6 | `green_stones` | the headstones and planting |

**Known bad pose:** `green_stones` faces a mausoleum wall. The grass reads
underfoot but the stones do not. The pose wants re-aiming, not the green.

---

## Part A — street anatomy

`bloodmap/street.py`, promoting queue ranks 3 and 6 into one constructor.
Every number is measured off E3M1, Blood's own city street:

| thing | value | evidence |
| --- | --- | --- |
| sidewalk tile | 4 | E3M1 |
| roadway tile | 352 | E3M1 |
| kerb rise | **2048** | all 22 shared 4/352 walls, zero variation, pavement above |
| sidewalk band | **2048** | modal narrow dimension, 5 of 9 sectors touching a roadway |

**A correction to the brief:** it specified a kerb "raised 1024, a quarter
step". The measurement says 2048 on every one of the 22 shared walls. 1024 is
the rise of this project's existing *grate* kerb — a ring around a drain, a
different object. 2048 is used, and it is still well inside the 4096 Blood
lets a body climb.

**What was applied:** 3 carriageways, in 2 districts.

```text
the_west_street   old_crossing   2816 wide   (2 pieces)
spur_south        market_slip    3072 wide
```

Five runs are pavement end to end **by design** — the 3072 lanes, where a
road plus two pavements does not fit. A lane is a pedestrian lane; the
campaign's are too.

### The blocker, which is the real finding

Eight runs were refused, and one reason dominates:

> **Gravesend draws its district seams down street CENTRELINES.** So a main
> street belongs half to each side of it, and neither half is wide enough for
> a carriageway plus its pavements.

Four ways round it were tried and each fails for a structural reason worth
recording:

1. **Clip to the owning district** — leaves half a road; take a pavement off
   that and nothing survives.
2. **Span the seam with one room** — the compiler exempts a region whose
   outline *is* one of another's holes, and nothing weaker. One room cannot
   be the hole of two streets.
3. **Split at the seam into paired halves** — each half's seam-side edge then
   lies flush on its street's own outer edge, which is two same-direction
   coincident segments, not a portal.
4. **Slide the road wholly into the owning district** — it lands in the
   block, because the district's side of a seam street is built up.

The fix is (3) done properly: **paired half-roads joined across the seam**,
which needs the two halves to exist simultaneously and their seam edges
paired to each other rather than to their streets. That is filed below as the
next promotion. The alternative is a plan change — moving seams off the
centrelines — which is the owner's call, not the machine's.

`the_rail_spur` was refused for a different and genuine reason: its
carriageway **would run through the gatehouse**. That is the plan and the
massing disagreeing, and it is reported rather than trimmed away.

### Prefab slots

Lamp positions are derived from run length, not written out: `lamp_slots`
spaces them from the middle outwards so the ends stay clear for junctions and
doorways, and insets each by half a pavement band so no lamp overhangs the
drop. 6 slots on the roaded runs. **The slots are computed and reported but
nothing is placed in them yet** — placing the lamp prefab is the obvious next
step and is not claimed here.

---

## Part C — the park corner

The cemetery was already the right shape: a walled, gated ground off Old
Crossing, entered through a lychgate, which is the E1M1 grammar. It was a
flat empty floor **wearing tile 352 — the roadway tile**. A yard of tarmac
behind a lychgate.

Now:

- ground retiled to **grass 361** (owner anchor, binding strong);
- planted from slots derived from the ground's own area — 1 pine, 1 RIP
  headstone, 4 bushes, 3 straw tangles;
- every slot checked against what already stands on the green.

```text
planted   9
dropped  11   -- landed in the church or the mausolea and were refused
path      0   -- refused: would run through 3 things standing on the green
```

**Eleven of twenty slots dropped is a poor yield and it is the honest
number.** The slot lattice is laid over the ground's bounding box, and this
green is not a rectangle: a church and two mausolea stand in it. A lattice
that respected the actual notched outline would place all twenty. The dirt
path was refused for the same reason — laid down the middle of the bounding
box it walks through the church.

So the green is turf with some planting, not yet a designed garden.

---

## Gates

```text
structural validation    0 errors, 0 warnings
rules                    97 diagnostics: 96 notes, 1 warning, 0 errors
budget                   257 sectors, 1672 walls, 417 sprites
                         walls cap 7000 -- 5328 spare
frames                   6, fixed-pose, XMapEdit observer (no game launched)
```

**Two pre-existing city defects were found and fixed on the way in**, both by
gates added in earlier runs:

- **the secret count was never declared.** The sprite carrying `tx_id 1,
  command 66` had no `trigger_on`, so `SetSpriteState` never called `evSend`
  for it and the player would never have been told a secret was found. It now
  goes through `motion.secret_total`, which cannot forget the edge.
- **eight attested-slot errors**: tile 2635 on the supermarket's shelf-bank
  faces. A raised solid's faces are two-sided and the campaign attests 2635
  only on one-sided walls. Swapped for 2026 — the same owner-anchored
  "shelf", attested two-sided in 8 slots.

---

## What is not here

**Parts B, D and E were not started.** Part A's geometry consumed the run.

- **B — facade signage:** not started.
- **D — storefront glass:** not started. `l3_theatre`'s hand-built gib-wall
  is still hand-built.
- **E — venue presentation chains:** not started. The Aldermack has no
  curtains and no command-5 light link.

No new owner decisions came out of this wave, so
`reports/owner-review-queue.md` is unchanged.

---

## For the promotion queue

1. **Paired half-roads across a district seam** — the blocker above. Without
   it, street anatomy cannot reach Theatre Row or Foundry Ward at all.
2. **Slot lattices that respect a notched outline** — wanted by both the
   green (11 of 20 dropped) and any future courtyard. The bounding box is the
   wrong domain for a room with things standing in it.
3. **Placing the lamp prefab into a derived slot** — the slots exist and are
   reported; nothing consumes them.
