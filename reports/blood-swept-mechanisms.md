# Slide and rotate, unparked — and what the embedding will not tell you

657 campaign mechanisms used to come back `not decidable from z alone`. They
are now read with the same vocabulary as everything else: **659 swept
sectors described**, with what the engine drags, how wide a gap that vacates,
and where the naming stops.

The owner's eleven E1M1 cases are the specification — one slide/rotate/ROR
machinery, many design objects — and they are also what proves the reading
incomplete. Both halves are below.

```text
bloodmap/effects.py       motion_markers, payload, swept_opening, leaf_blocks
bloodmap/conditional.py   the swept branch, level_start_closure, design_role
reports/blood-swept-mechanisms.json
tests/test_swept.py       30 tests, 15 of 15 mutants caught
work/_e1m1_cases.py  work/_swept_report.py
```

## The vocabulary

One primitive, from the engine's own instruction. `TranslateSector`
interpolates a sector between two marker sprites: `marker_0` is the rest pose
and `marker_1` the moved one, so a **slide** is the vector between them and a
**rotate** is the turn about the single marker it carries.

### What moves is not always the geometry

`TranslateSector`'s last argument is `bAllWalls`, and the caller passes
`type == kSectorSlide` / `kSectorRotate`. So the **unmarked** types 616 and
617 drag every wall they own, while the **Marked** types 614 and 615 drag
only walls flagged `cstat & 16384` (with the motion) or `& 32768` (against
it). Sprites are dragged on their own flags, `& 8192` and `& 16384`, **and
they are dragged whether or not any wall is**.

That is the owner's second structural fact, and the campaign bears it out:

```text
its own walls              511
walls and carried sprites  101
carried sprites             35    <- no geometry moves at all
nothing that moves          12
```

**35 campaign mechanisms move only sprites.** E1M1's sector 65 is the case
that names the pattern: 49 walls, not one of them flagged, and two wall
sprites (37 and 38, carrying 8192 and 16384) doing the whole job of a
sliding gate. A reading that sweeps geometry alone sees a mechanism that does
nothing.

### How wide a gap it vacates

A leaf of length `L` sliding `d` along its own line leaves `min(d, L)`:
travel beyond its own length buys nothing, and a leaf longer than its travel
is still partly in the way. A leaf hinged at one end and swung by `theta`
leaves the chord `2 L sin(theta/2)`. Then one question — is that wider than a
body's 384 units?

**538 of 659 swept mechanisms open a body's width.**

## The two structural facts, encoded

**Room-over-room participates in mechanism composition.** E1M1's casket is
one: the player-start sector 30 is slide-marked *and* stack-linked to sector
28. `ror_sectors()` names them and `design_role` reads the pairing.

**ROR is a budget.** Two ROR volumes must not be in view at once, so a level
gets few and authors reuse the ones they have. Measured across the campaign:

```text
maps with any room-over-room     32 of 43
link pairs per map               0 x11   1 x4   2 x5   3 x1   4 x3   5 x2
                                 6 x6    ... and two outliers at 32 and 37
```

Eleven maps have none and most of the rest have a handful. E1M1 spends part
of its allowance making one big ROR volume also carry a sliding gate rather
than building a second sector for the gate — an engine visibility constraint
reshaping the authoring, visible in the map as one sector doing two unrelated
jobs. `design_role` returns **technical workaround** for the 12 campaign
mechanisms in that position.

## A level has already started before the player moves

E1M1's player start is inside a closed casket. The switch that opens it sits
in another sector, listening on **rx 7 — kChannelLevelStart** — with a
six-tick wait. No body ever reaches that switch.

A frontier that waits for a player to work it reported the whole level
unreachable: **2 sectors of 155**. `level_start_closure` fires channel 7 and
everything it transitively reaches before the player does anything, and E1M1
returns to 98 at rest and 121 after acting.

## The owner's eleven, and where the reading stops

```text
sector  owner's reading        payload                    opening  role from embedding
30      narrative             its own walls                 1024   narrative
26      secret                its own walls                  548   recorded, not placed
4       progression           its own walls                  896   recorded, not placed
50      progression           its own walls                 1434   recorded, not placed
51      progression           its own walls                 1429   recorded, not placed
65      technical workaround  carried sprites                768   technical workaround
90      technical workaround  nothing that moves               0   technical workaround
99      ambush                walls and carried sprites     1015   recorded, not placed
125     furnishing            walls and carried sprites     1024   recorded, not placed
63      passage               its own walls                  960   recorded, not placed
70      secret entrance       walls and carried sprites     1792   recorded, not placed
86      fixture               z-motion, 2048 of travel         —   fixture
139     fixture               z-motion, 2048 of travel         —   fixture
```

**Five of thirteen named; eight recorded and not placed.** Every one of the
eight has a measured payload and a measured opening. What is missing for
them is one thing: **which of the two states blocks.**

### Why that is missing, concretely

The cheap test is to run the line from one portal's midpoint to the other and
ask whether a leaf segment crosses it — at rest, and once moved. It is
correct where it fires, and it fires almost nowhere: **5 of 628** swept
mechanisms across the campaign.

E1M1's sector 63 shows why. Its two portals sit at (7424, 34304) and
(7424, 33792) — 512 apart, on the *same side* of the sector. The leaf runs
from x 5952 to 6976, nowhere near the straight line between them. The way
across that sector is not a straight line, and a door's two portals are
adjacent as often as they are opposite.

Assuming instead that the rest state is the shut one is much worse, and the
campaign said so immediately: it cut E1M2 from 226 reachable sectors to 26.
That reading is not in the code.

### The eight names cross-cut the embedding

Worth stating plainly, because it is the owner's test and the answer is
partly no. Measured on E1M1 with the gating that *was* available:

- **s99 (ambush) and s125 (furnishing)** have identical topological
  signatures — each loses exactly one sector when struck out, each has dudes
  in the sector immediately beyond. Rats bursting out and a curtain being
  drawn are the same shape.
- **s63**, which the owner calls a plain standalone sliding door, is *more*
  load-bearing than **s50/s51**, the double rotating door built as the way
  on: 17 sectors against 1.
- **s26 (secret)** and **s70 (secret entrance)** both have a secret sector
  one hop beyond. So does s63, which is neither.

So `secret_within_reach` and `dudes_immediately_beyond` are **recorded and
never used to name**. They are necessary and not sufficient, and a spatial
rule tuned to split eleven hand-labelled cases would be fitting noise.

What the embedding does determine, and does: **narrative** (the sector holds
the player start), **technical workaround** (half of an ROR pair), **fixture**
(never opens a body's width), and — where gating is measurable — **required
passage** against **side passage**.

## The campaign

```text
swept sectors read                 659      (previously: 657 undecided)
  open a body's width              538
  gated, which state blocks known    5
  recorded, not placed             623
mechanisms with no reading at all   10

roles assigned    side passage 631   fixture 395   required passage 137
                  technical workaround 12   narrative 3
```

## Limitations

- **The polygon sweep is still the gap, and it is now the only one.** Which
  state of a swept mechanism blocks is answered for 5 of 628. Everything else
  about them — primitive, payload, leaf, opening — is measured.
- The leaf test needs exactly two portal neighbours and a solid moving wall
  between them. A sector all of whose walls are portals has no leaf at all;
  what blocks it is its whole geometry moving.
- `swept_opening` reads the leaf, not the room. It cannot see a leaf sliding
  into a recess too small for it, or two leaves fouling each other.
- A wall sprite's drawn width assumes a 64-pixel tile. Where that is wrong
  the number is wrong by a factor, never by a sign.
- Three of the owner's eight names are not recovered, and two more are
  recovered only by flags this deliberately does not name from. That is a
  statement about what where-it-sits can tell you, not a to-do.
- Campaign only. Community maps are precedent, never convention.
