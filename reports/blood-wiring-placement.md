# What the excluded remainder actually is

The mining-hygiene fix moved 30% of campaign object-context occurrences out
of the default statistics and promised they were "wiring evidence for the
later phases". That promise is worth checking, because *wiring* was doing a
lot of work in one word. This report opens the bin.

```text
python -m bloodmap pattern-mine --maps maps/blood --population blood-campaign \
  -o work/blood-pattern-unsigned-campaign.json      # excluded_candidates
reports/blood-wiring-placement.json                 # per-sprite measurements
```

## It is three different things, and only one is mechanism evidence

The 553 excluded candidates (1962 occurrences) are now keyed on the
wiring they hold rather than on the visible objects they lack -- otherwise
every sound-marker pocket in the campaign files under one meaningless
`objects:0` bucket. By sprite category:

```text
sound                    1765
marker                    990
hidden-thing              156
start                     144
hidden-switch              85
generator                  75
hidden-decoration          32
```

The word *wiring* was carrying three unrelated things:

- **Ambience** (`sound`, 1765) -- a `kSoundSector` does not change what is
  reachable and has no state. It is level dressing that happens to be
  invisible. Mining it as a mechanism would repeat the original mistake one
  layer up.
- **Navigation and spawn wiring** (`marker` 990, `start` 144) -- link and
  warp markers are already load-bearing in `reachability.py`, which crosses
  them to decide what the player can reach. They are consumed, not mined.
- **Hidden mechanism parts** (`hidden-switch` 85, `generator` 75,
  `hidden-thing` 156) -- these *are* Phase 8/9 material: triggers and
  spawners wired by RX/TX rather than by geometry, plus 85 switches a mapper
  deliberately made invisible. Together with the `logic_closet` sectors (50
  of the excluded occurrences) they are the trigger evidence the later
  phases were promised.

Roughly two thirds of the remainder is ambience and navigation, which no
mechanism phase should touch. Anyone reaching for the excluded set as "the
wiring" has to split it first. What follows measures the ambience part,
because it is the part the niche-pair contrast tripped over.

## Where a sector-sound marker sits

1247 `kSoundSector` sprites in 1227 sectors across 42 of the 43 campaign maps -- so this is a
campaign-wide practice, not one mapper's habit.

```text
sectors holding no visible object at all   1047/1247  (84%)
sectors that are off-map                   0/1247  (0%)
```

Two facts worth having. The first validates the exclusion rule: these really
are dedicated ambience pockets, not furnished rooms that happen to contain a
marker. The second is a small surprise -- **every one of the 1247 is in
reachable geometry**. Ambience is placed where the player goes; switch
closets are by definition the opposite. The three parts of the excluded set
do not even live in the same kind of sector.

## The height is absolute, not proportional

The obvious hypothesis is that a marker goes in the middle of the space it
voices. It does not.

```text
concentration of the top three choices
  absolute height above the floor    55%   (204 distinct values)
  position as a fraction of clear    32%   (135 distinct values)

markers within 2% of the sector midpoint    29/900   (3%)
median position within clear height         0.195
```

Absolute placement is the more concentrated of the two by a wide margin, and
the marker sits low in the sector rather than centred. A proportional rule
would have shown the opposite.

## Two preferred heights, and they are mostly one practice

```text
       0 units  x 336  in 39 maps   (0.000 player heights)  27%
    6400 units  x 241  in 29 maps   (0.377 player heights)  19%
    8192 units  x 106  in 29 maps   (0.483 player heights)  9%
   20224 units  x  43  in 20 maps   (1.192 player heights)  3%
    6144 units  x  29  in  8 maps   (0.362 player heights)  2%
distinct heights used: 204
```

`6400` is the number the Phase 4 contrast surfaced, and it is real: 241
instances across 29 maps. But it is second to *on the floor*, and the top
three together cover 55% of 204 distinct values. **A preference, not a
rule** -- worth stating before anyone promotes 6400 to a constructor
default.

The two look like competing conventions and mostly are not. They differ by
how much room the sector has:

```text
                       n     clear height (median)   area (median)
on the floor (0)     336     7,167 units             1.78 player areas
6400 units           241    32,768 units             3.56 player areas
```

```text
where a 6400 mounting does not fit (clear <= 6400):   56% sit at 0
where there is real headroom (clear > 12800):         24% at 6400, 15% at 0
```

Sector height **predicts** the choice without determining it. Half the
on-the-floor cases are in sectors with no room for anything else; with
headroom, 6400 becomes the single commonest choice but nothing dominates.
The honest reading is one practice -- put the marker a little above the
floor, at an absolute height, when there is space for it.

## Counterexamples, preserved

```text
markers below their sector's floor plane      116  (9%), down to -12.6443 player heights
markers at 6400 in a sector shorter than that 23  (above their own ceiling)
the tallest mounting recorded                 59.2754 player heights
```

These are not errors to clean up. An invisible marker has no volume to
respect, and the engine does not care where inside -- or outside -- the
sector it sits. That is precisely why its z was never a design decision, and
why reading it as furniture mounting produced a family of 149 sectors that
dissolved to 23 the moment visibility was consulted.

It also closes the last open item from the Phase 4 contrast, which recorded
10 raised objects sitting below their floor as "real and unexplained". They
were markers. Here are 116 more.

## What this does and does not license

- It does **not** license a `kSoundSector` constructor that places at 6400.
  27% of the corpus disagrees, and the choice depends on the sector.
- It does license *ignoring* marker z when reading a space, which is what
  the object-scale mining now does by default.
- The hidden-mechanism part of the excluded set (316 occurrences across
  `hidden-switch`, `generator` and `hidden-thing`, plus the `logic_closet`
  sectors) is untouched here and remains the input Phases 8 and 9 were
  promised. Nothing in this report is about mechanisms.

## Limitations

- Campaign only. Community maps would be precedent, not convention, and are
  not mixed in.
- `kSoundSector` only. The other 2255 campaign sound sprites (`Ambient SFX`,
  `kGenSound`, `kSoundPlayer`) are counted but not analysed; they are
  different mechanisms with different placement rules.
- Sector clear height is floor-to-ceiling at rest. A sector whose ceiling
  moves is measured in one of its states.
- Every row is an OBSERVATION. "One practice under different constraints"
  is an interpretation, offered with the numbers that would refute it.

