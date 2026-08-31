# Functional regions: one room, several zones

Phase 6. A zone candidate is a connected run of sectors sharing a floor
plane and a floor tile; Phase 5 bundles hang off the zones that host them.
The output is hierarchical -- complex, zone, sectors, bundle, core and caps
and props -- and the zones are **unnamed**, for reasons the middle of this
report is about.

```text
bloodmap/spatial.py  zone_partition        the derived view, knows nothing of bundles
bloodmap/anchors.py  region_candidates     composes it with Phase 5 bundles
reports/blood-assembly-regions.json
```

## E6M1's shop, which is what the phase asks for first

Two hops out from the cashwrap's host gives a 20-sector complex, and the
partition finds 11 zones. The largest is the one that matters:

```text
zone:0    8 sectors  floor 90112  tile  290   746.4 player areas  36 props
zone:75   2 sectors  floor 90112  tile 1011    81.1              5 props
zone:32   1 sector   floor 83968  tile   20    17.8              3 props   <- the counter
zone:33   1 sector   floor 81920  tile 2476     1.8              0         <- a register cap
zone:60   1 sector   floor 73728  tile  452     3.6              3 props
...11 zones in all
```

`zone:0` is the public shop floor: the apparel bay, the display window, the
selling floor and the connectors between them, all one plane and one tile,
recovered as a single place. The cashwrap is its own zone, its register caps
are two more, and the sunken back office is another. That is the exit
criterion -- one room explained as several zones, each with its evidence.

## What the partition cannot do, measured

The owner's shop reference names the apparel bay, the display window and the
selling floor as three distinct zones. Geometry cannot separate them:

```text
sector  floor_z  floor tile   owner's name
    45    90112         290   apparel bay
    50    90112         290   display window
    61    90112         290   selling floor
    63    90112         290   selling floor
```

One plane, one tile. They differ in what they *hold* -- seventeen hanging
clothes in S45, three mannequins in S50 -- which is anchor evidence, not
geometric evidence. So this view is honest about its ceiling: it separates
a counter from the floor it stands in, and a sunken office from a shop, and
it does not separate one shop floor's bays from each other.

## Corpus survey

For every Phase 5 bundle, the two-hop complex around its host:

| | campaign (n=146) | curated (n=238) |
| --- | ---: | ---: |
| complex size, median sectors | 10 | 14 |
| zones per complex, median | 7 | 9 |
| complexes with >= 2 zones | 146/146 (100%) | 238/238 (100%) |
| counter in a different zone from its host | 146/146 (100%) | 238/238 (100%) |
| counter alone in its zone | 135/146 (92%) | 223/238 (94%) |
| host's zone is the complex's biggest | 112/146 (77%) | 158/238 (66%) |

**Every complex containing a counter contains at least two zones, and in
every one of the 146 campaign cases the counter is in a different zone from
its host.** That is not a tautology: the partition is by floor plane and
tile, and a counter built at its host's floor height with its host's tile
would land in the same zone. None does.

## Two namings, both rejected

`04_...md` offers a shop grammar with `customer_front` and
`employee_workspace` either side of a counter boundary. Phase 5 measured
that 95% of campaign counters are asymmetric, which looked like exactly that
distinction. Two ways of naming the sides were tested and both failed.

**a counter's wide side is the customer front, because that is where the ways out are**

- measured: 84.1% of a host's ways out are on the wide side, but the wide side also carries 83.2% of the host's wall: a lift of +0.024, and only 43% of bundles beat their own wall share (a coin flip is 50%)
- rejected: the wide side has the exits because it has the wall, not because it is the public side

**merchandise stands on the customer side, so the wide side is denser in props**

- measured: props on the wide side 0.651 against a floor share of 0.730 -- a lift of -0.080, and the wide side is the denser one in only 40% of bundles
- rejected, and in the opposite direction to the guess

The first is the instructive one. 84.1% of a host's ways out really are on
the counter's wide side -- a number that would have looked like a finding if
it had been reported on its own. Normalising by the wall available on each
side leaves a lift of +0.024. The wide side has the exits because it has the
wall.

So the asymmetry Phase 5 measured is a **shape** fact and not a **zoning**
fact, and the zones stay unnamed. `03_...md`: discover recurring structure,
characterize relations, inspect contexts, *then* propose semantics -- and
the last step is not earned here.

## Counterexamples, preserved

```text
counters sharing a zone with another sector   11/146
host zones that are not the complex's biggest 34/146
```

The 11 campaign counters that share a zone are counters built as a run of
sectors at one height -- an L-shaped bar is two sectors, one plane, one
tile, and the partition correctly calls it one zone. They are not errors.

## Limitations

- Zones are candidates, not a room's meaning, and they carry no names.
- The partition uses the floor plane and tile only. Ceiling height, light
  and material of the walls are untried and might separate the bays that
  this cannot.
- Two hops is a chosen radius, not a measured one; it is stated so a reader
  can see the complex was bounded rather than discovered.
- `curated` is precedent. Nothing here reads community geometry as Blood
  convention.

