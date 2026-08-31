# Hidden switches: not what they command, and not where they are

Phase 8 asked whether a concealed trigger *commands* a different kind of thing
than an exposed one and got a flat no — not one feature of channel role or of
what is commanded reached the 0.65 discriminator floor. That result is what
made this question sharp: if concealment is not about *what*, the remaining
candidate is *where*.

Measured. It is not about where either.

```text
work/_switch_placement.py
reports/blood-hidden-switch-placement.json
```

## The rule of the experiment

Every feature is spatial and none reads a picnum — the exact counterpart of
Phase 8's list, which was channel role only. Scored: `same_sector`,
`adjacent_sector`, `hops_to_target`, `target_unreachable_by_portal`,
`sees_the_target`, `targets`, `distance_to_target`,
`switch_in_a_logic_closet`, `switch_in_reachable_geometry`.

Sight is `sight.line_of_sight` — an XY ray against occluding walls, no new
machinery. Distances and hops are over `reachability.portal_graph`. Discipline
borrowed intact from `anchors.contrast_anchor_sets`: balanced accuracy on a
badly imbalanced split, a per-map transfer check, counterexamples preserved,
and switches with nothing to measure held out rather than scored as zero.

Two scopes, because the sharp one is small. **gated** is placement relative to
the crossings the switch actually opens, from the conditional view. **listening**
is placement relative to every sector that listens on its channel — looser
about what "what it opens" means, and a bigger sample.

## The population, and the 115-against-85 reconciliation

```text
1396 switch sprites in the campaign      1281 visible   115 hidden
```

The roadmap recorded 85 hidden switches and the Phase 8 contrast found 115.
Both are right and they count different things, which this run computed rather
than assumed:

```text
115 hidden switch sprites
 =  85 whose sector is in mine_object_contexts' excluded scope
 +  30 whose sector is reachable AND holds something a player can see
```

85 counts hidden-switch *occurrences inside the excluded bin*; 115 counts the
*sprites*. The 30 that differ are hidden switches sharing a furnished,
reachable sector with visible objects, so their sector's sample lands in the
default scope and its wiring is never tallied in the excluded one.

## The result: nothing separates them, in either scope

```text
scope gated       22 hidden in 11 maps   363 visible in 42 maps   1011 held out
  distance_to_target            0.640    hidden 24989    visible 15656
  targets                       0.610    hidden 2        visible 1
  sees_the_target               0.559    hidden 14%      visible 25%
  target_unreachable_by_portal  0.548    hidden 64%      visible 54%
  adjacent_sector               0.547    hidden  9%      visible 18%
  switch_in_a_logic_closet      0.532    hidden 55%      visible 48%
  same_sector                   0.505    hidden  5%      visible  4%

scope listening   37 hidden in 14 maps   705 visible in 43 maps    654 held out
  distance_to_target            0.603    hidden 22448    visible 19207
  adjacent_sector               0.570    hidden  5%      visible 19%
  target_unreachable_by_portal  0.563    hidden 70%      visible 58%
  sees_the_target               0.561    hidden 11%      visible 23%
  switch_in_a_logic_closet      0.529    hidden 59%      visible 54%
```

**No feature reaches the floor in either scope.** The best is
`distance_to_target` at 0.640 and 0.603.

What is worth saying is that the weak signals all point the same way: a hidden
switch sits **further** from what it opens (≈25000 against ≈15700 units), is
**less often adjacent** to it (9% against 18%), and **less often sees** it (14%
against 25%). That is a coherent story — concealment goes with distance — and
at 0.60–0.64 balanced accuracy it is a tendency, not a distinction. On a
22-switch positive class it is also barely more than a rumour.

## The thing that is true of both

```text
sector kind of the switch sprite itself
  hidden    logic_closet 65 (57%)   reachable 50 (43%)
  visible   logic_closet 752 (59%)  reachable 511 (40%)   sealed 18 (1%)
```

**Well over half of all campaign switch sprites sit in a logic closet** —
geometry the player never enters — and the hidden and visible shares are
within two points of each other (balanced accuracy 0.53).

That is the finding that reframes both experiments. Blood's mappers routinely
put a switch *sprite* in a closet and wire it by channel; what the player
pushes is an XWALL on a wall somewhere else. So the invisible cstat bit on a
switch sprite is largely a **construction detail of closet wiring**, not a
design decision to hide a trigger from a player — and a sprite in a closet is
invisible to the player whether or not the bit is set.

That explains why both contrasts came back empty. They have been comparing two
populations that are mostly the same thing.

## What this closes and what it opens

The Phase 8 handoff asked where hidden switches sit. Answered: not
distinguishably anywhere. Concealment, as measured by that cstat bit, is
neither a property of what a trigger commands nor of where its sprite is.

The question that survives is a different one, and it is about the **XWALL**
rather than the sprite: the face a player actually pushes. Nothing here
measured those, and they are where a deliberately concealed trigger would
have to live.

## Limitations

- Thresholds are fitted on the rows they are scored on. These are separations
  observed, not a validated classifier.
- The gated scope has 22 hidden switches. A tendency at 0.64 on that sample is
  not something to build on.
- 1011 of 1396 switches gate nothing in the conditional view and are held out.
  Most command lights, sounds, sprites, or Z-motion that changes no crossing —
  and the view only covers Z-motion, so a switch driving a rotor is invisible
  to it.
- `sees_the_target` is a 2D ray against occluding walls: no height, no slopes,
  no sprites. It answers "is there a wall in the way on the floor plan".
- Distance is to the nearest commanded sector's centroid, not along a route.
- Campaign only, 43 maps. Community maps are precedent, never convention.
