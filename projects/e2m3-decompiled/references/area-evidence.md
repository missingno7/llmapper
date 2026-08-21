# E2M3 major areas: what the grouping is made of

The architecture audit named the gap: `decompile_level` defines an assembly as
a connected component of the portal graph, and a normal level is one component.
327 of E2M3's 340 sectors landed in `assembly:001`, so the middle of the tree
was 123 calls in one function and a reader who wanted one wing had to read the
level.

Areas are a spatial grouping, and connectivity does not produce them.

## What went into it

Seven signals, weighted flat and visibly, in `tools/propose_areas.py`:

| Signal | Weight | Source |
| --- | --- | --- |
| each is visible from a representative view of the other | 2.0 | the renderer |
| one is visible from a representative view of the other | 1.0 | the renderer |
| same sky class | 1.5 | geometry |
| median floors within two player heights | 1.5 | geometry |
| dominant surfaces overlap | 1.5 × Jaccard | materials |
| centres within sixteen player widths | 1.0 × falloff | geometry |
| total opening width between them | 1.0 × falloff | geometry |

Greedy agglomeration over the portal graph, one merge at a time, each recorded
with the reasons that justified it. A merge is refused below 0.35 of the maximum
score, or if it would make one area more than 30% of the assembly.

## What the visual evidence changed

Both runs use the same weights, the same threshold and the same code. The only
difference is whether a visual observation packet was supplied.

| | areas | top five areas, by sector count | sectors in the top four |
| --- | --- | --- | --- |
| geometry and materials only | 26 | 94, 41, 39, 28, 19 | 202 of 340 |
| with co-visibility | 23 | 98, 81, 69, 39, 15 | **287 of 340** |

Eight of the groups are identical either way. Thirty-three differ. Of the 100
merges the visual run made, 79 cite visibility and 28 of those cite *mutual*
visibility — a representative view of each shows the other.

The difference is not that the visual run found more merges. It is that without
visibility the level breaks into a long tail of medium fragments, and with it
four principal areas absorb 85 more sectors and become distinguishable from each
other:

| seed | sectors | median floor z | sky | dominant surfaces | centre (PW) |
| --- | --- | --- | --- | --- | --- |
| `space:003` | 98 | 8192 | 38% | 2492, 34, 91 | 110.9, 65.6 |
| `space:037` | 81 | -11264 | 18% | 20, 153, 28 | 141.7, 89.6 |
| `space:011` | 69 | 8192 | 74% | 2448, 2499, 2474 | 97.1, 18.5 |
| `space:010` | 39 | -4096 | 36% | 2499, 2448, 329 | 94.8, 66.4 |

Read down the columns and they separate cleanly: `space:011` is the outdoors —
ground level, three quarters sky-lit. `space:003` is ground level too but mostly
enclosed, and shares almost no surface vocabulary with `space:037`, which sits
nineteen thousand units higher and is built out of a different tile family
entirely.

## What is deliberately not here

**No names.** Every area is identified by the space it was seeded on. Naming
`space:011` "the courtyard" would be interpretation printed as measurement, and
`references/names.json` is where interpretation goes, with a confidence on each.

**No claim that this is the grouping.** The document keeps a second run at a
lower threshold and a larger size cap (20 areas instead of 23), and the eight
strongest merges the primary run refused, with their scores and reasons. The
strongest refusal is `space:010` + `space:011` at 0.487 — one-way visibility,
both enclosed, 43% surface overlap, 7.3 player widths of opening between them.
That is a defensible merge that the threshold declined, and a reader who
disagrees can see exactly what they would be agreeing with.

**No revisiting.** Greedy agglomeration never reconsiders an early merge. A
different order would give a different answer and the code does not pretend
otherwise.

## The effect on the source

`build_main_complex` went from 138 lines listing 123 space builders to **39
lines listing 23 zone builders**, each of which is its own function carrying its
measured character in its docstring:

```python
def build_main_complex_zone_03(area) -> object:
    """zone_03: 17 spaces, 69 sectors.

    Grouped from measurement rather than from a name: median floor z
    8192, 74% of its sectors open to the sky, dominant surfaces [2448, 2499, 2474],
    centred at [97.1, 18.5] player widths. Seeded on assembly:001/space:011.

    Origin is the corner of this zone, so outlines below are local to it.
    """
    zone = area.assembly('zone_03', frame=Frame(0, 0), style=Style(parallax_ceiling=True))
    build_far_open_ground(zone)
    build_arrival_yard(zone)
    ...
```

A zone is a real `Assembly` in the program with its own frame, so the spaces
inside it hold coordinates local to the zone rather than to the whole level.
Region ids gained the zone in their path, which is why a compiler refusal now
reads `region:e2m3/main_complex/zone_02/large_interior/sector_21` and says where
it is.

## Regenerating

```bash
python -m tools.observe decompiled maps/blood/E2M3.MAP \
    --hierarchy projects/e2m3-decompiled/hierarchy.json \
    -o work/obs-e2m3 --purpose room_center --purpose room_entry --structures

python -m tools.propose_areas maps/blood/E2M3.MAP \
    --hierarchy projects/e2m3-decompiled/hierarchy.json \
    --packet work/obs-e2m3/packet.json \
    -o projects/e2m3-decompiled/references/area-proposals.json

python -m tools.emit_level_program maps/blood/E2M3.MAP \
    --art-dir reference/blood \
    --names projects/e2m3-decompiled/references/names.json \
    --areas projects/e2m3-decompiled/references/area-proposals.json \
    -o projects/e2m3-decompiled/source/E2M3.py
```
