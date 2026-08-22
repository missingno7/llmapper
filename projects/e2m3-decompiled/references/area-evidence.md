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
| with co-visibility | 25 | 98, 81, 72, 19, 17 | **270 of 340** |

Eight of the groups are identical either way. The rest differ. Of the 98 merges
the visual run made, 78 cite visibility and 29 of those cite *mutual* visibility --
a representative view of each shows the other.

The difference is not that the visual run found more merges. It is that without
visibility the level breaks into a long tail of medium fragments, and with it
three principal areas absorb most of the level and become distinguishable from
each other:

| seed | sectors | median floor z | sky | dominant surfaces | centre (PW) |
| --- | --- | --- | --- | --- | --- |
| `space:005` | 98 | 8192 | 71% | 2499, 2448, 2474 | 97.2, 35.1 |
| `space:037` | 81 | -11264 | 18% | 20, 153, 28 | 141.7, 89.6 |
| `space:013` | 72 | 8192 | 44% | 329, 2499, 2448 | 119.0, 49.4 |
| `space:010` | 19 | -24576 | 0% | 2499, 2448, 329 | 93.3, 71.0 |

Read down the columns and they separate. `space:005` is the outdoors -- ground level,
71% sky-lit. `space:013` is ground level too but only 44% sky-lit and built from a
different surface family. `space:037` sits nineteen thousand units higher, is almost
entirely enclosed, and shares no dominant tile with either.

## What is deliberately not here

**No names.** Every area is identified by the space it was seeded on. Calling
`space:005` "the courtyard" would be interpretation printed as measurement, and
`references/names.json` is where interpretation goes, with a confidence on each.

**No claim that this is the grouping.** The document keeps a second run at a
lower threshold and a larger size cap, and the eight strongest merges the primary
run refused, with their scores and reasons. The strongest refusal is
`space:005` + `space:013` at 0.632 — one is visible from a representative view
of the other; both are open to the sky; median floors within 0.0 player
heights; dominant surfaces overlap 25%; openings between them total 12.2
player widths. That is a defensible merge that the threshold
declined, and a reader who disagrees can see exactly what they would be
agreeing with.

**No revisiting.** Greedy agglomeration never reconsiders an early merge. A
different order would give a different answer and the code does not pretend
otherwise.

**No geometry the player cannot reach.** E2M3's eleven off-map sectors are one
switch closet, one sealed pocket and nine letters spelling an author's handle.
They are excluded and the proposal records which spaces it dropped. See
[Blood mechanics and conventions](../../../docs/blood-mechanics-and-conventions.md).

## The effect on the source

`build_main_complex` went from 138 lines listing 123 space builders to **41
lines listing 25 zone builders**, each of which is its own function carrying its
measured character in its docstring:

```python
def build_main_complex_zone_01(area) -> object:
    """zone_01: 25 spaces, 98 sectors.

    Grouped from measurement rather than from a name: median floor z
    8192, 71% of its sectors open to the sky, dominant surfaces [2499, 2448, 2474],
    centred at [97.2, 35.1] player widths. Seeded on assembly:001/space:005.

    Origin is the corner of this zone, so outlines below are local to it.
    """
    zone = area.assembly('zone_01', frame=Frame(0, 0), style=Style(parallax_ceiling=True))
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
