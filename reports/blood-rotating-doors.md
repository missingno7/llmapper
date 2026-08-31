# Rotating doors: the category, censused

The turnstile template was mined from four rotors in two maps and generalized
from there. The owner's correction, in two parts: the category is wider than
that, and **a single rotor is a complete door** when both sides are reachable.

Both are right, and the census changes two things I had committed as facts.

```text
work/_rotor_census.py
projects/facade-pilot/reports/rotor-census.json
bloodmap/mechanism.py          turnstile_spec, blade_offset
tests/test_turnstile.py
```

## Method

Every sector of type 613, 615 or 617 in every population. A rotor is a
**door** when its portals reach two or more different sectors -- that is the
spatial test the reference already names, and it is what makes it an aperture
rather than a spinning ornament. A door of the turnstile family also carries
grate vanes, tiles 332 or 465.

## What is out there

```text
4160 rotating sectors in 601 maps
  reaching two or more sectors                937 in 177 maps
  of those, carrying grate vanes               25 in   6 maps

  population              rotors   doors   with vanes
  community                 3303     615            0
  community-curated          353     157            2
  blood-campaign             263      77            2
  mechanism-tutorial         191      78           17
  blood-bloodbath             31       3            0
  own-conversion              19       7            4
```

The six maps are E1M4, DWE1M9, DNE3L6, and XMapEdit's own
`DOOR-ROTATING`, `DOOR-SWINGINGGATE` and `DOOR-SWINGINGGATED` samples. The
samples are the majority of the evidence and they are not campaign
convention -- they are how the engine works, which is exactly what
`mine_assemblies` says the samples are for.

DNE3L6 has **four** rotors, not the two the earlier reference recorded:
sectors 3, 11, 364 and 367.

## One rotor is a door

**All 25 grated rotating doors reach exactly two sectors.** Not one of them
needs a partner. DNE3L6's sector 3 joins rooms 4 and 10; its sector 11 joins
12 and 13 -- two independent doors, not a mirrored pair.

So E1M4's pair is a *composition* someone chose for a carnival entrance, and
calling it "the convention" was reading two maps as a rule. `turnstile_pair`
stays because the campaign really does build one, but it is a convenience over
`turnstile`, not the shape of the mechanism.

## The vane count is the variant

The same kSectorRotateMarked sector with a different number of leaves on it:

```text
1 vane     15 rotors    a swinging gate   DOOR-SWINGINGGATE, DOOR-SWINGINGGATED
2 vanes     1 rotor     a double gate     DOOR-SWINGINGGATE s52
4 vanes     9 rotors    a turnstile       E1M4, DWE1M9, DNE3L6, DOOR-ROTATING
```

A turnstile is the four-vane case of a rotating door, not a thing of its own,
so `vanes` is now the argument that says which.

## A fact I had committed, and it was wrong

The last fix said the vane's stand-off from the axis is "a constant, not a
derived quantity -- all 16 blades sit at exactly 384". That was true of the 16
blades I had looked at and false of the category:

```text
                       x_repeat   half drawn width   offset
E1M4 151/314                 48                384      384
DWE1M9 61/64                 56                448      384
DNE3L6 (four rotors)         56                448      448
DOOR-ROTATING s4             56                448      448
DOOR-SWINGINGGATE[D]         64                512      510-512
```

**A vane stands off the axis by half its own drawn width** -- its inner edge
meets the pivot -- in **45 of 53 vanes**. The eight exceptions are DWE1M9's,
every one exactly 64 short, so its vanes cross the centre slightly. 384 was
never a constant; it is what `x_repeat` 48 produces, and I had two maps that
agreed by coincidence.

This is the second time on this mechanism that a number measured across two
maps turned out to be a coincidence. The first was the blade z; this is the
offset.

## Two ways to build the same cross, both attested

```text
E1M4, DWE1M9      two angles and the flip bit    0, 0, 512, 512   cstat 8593/8597
DNE3L6, samples   four distinct angles           0, 512, 1024, 1536   one cstat
```

Both put four outward-facing vanes on the pivot; the rule underneath is that a
vane faces **perpendicular to its own radius**, because a wall sprite's angle
is the normal of its face. The campaign's form stays the default so the
existing built map still round-trips; the four-angle form is the general one
and is what a 1- or 2-vane gate uses.

## What did not change

The sector fields are unchanged and the wider census supports them: type 615,
`rx_id` 7 on the `level_start` broadcast, both waves retriggering, and a
kMarkerAxis at the pivot whose *angle* is the travel. The blade still spans the
rotor from floor to ceiling.

## Limitations

- "Door" here is a spatial test on portals, not a proof that a body fits
  through. Passage is still unverified for every one of these.
- The 937 rotors that reach two sectors without vanes are not classified. Some
  are certainly doors of another kind and some are scenery that happens to
  touch two rooms; the vane test is what separates the turnstile family, and
  the rest of that population is unexamined.
- `DOOR-SWINGINGGATE` s52 is the only two-vane example in the corpus. One
  instance is not a pattern, and the constructor supports it because it is the
  same code path, not because two vanes are established.
