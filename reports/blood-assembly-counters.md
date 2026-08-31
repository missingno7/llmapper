# Static assemblies and the space they claim

One bundle type, mined from the campaign with curated as precedent; the
negative space it claims, measured before anything was asserted; and a
detector that tells an authored bundle from the same props scattered.

```text
bloodmap/anchors.py       find_bundles, scatter_verdict, compare_placements
bloodmap/player_space.py  Clearance, bundle_clearance, check_clearance
reports/blood-assembly-counters.json
```

## The bundle: a raised island

`assembly.py` groups the parts of a *mechanism* -- things bound by channels
and state. A counter has neither and is still one object. The grouping rule
uses the `04_...md` signals in this order, and proximity is not among them:

1. exactly one neighbour that does not sit inside its own footprint (the host)
1. floor raised above the host by more than the 4096-unit step limit
1. rise in the waist band 4096-8192 units
1. elongated footprint, aspect >= 2
1. carries a cap sector or at least one visible prop

The anchor is E6M1's cashwrap, which the owner's shop reference describes as
"a three-sector nested prefab": S32 the counter, S33/S34 the two register
caps. The rule is told none of that and recovers exactly it -- core 32, host
61 (the selling floor), caps {33, 34}, three props, rise 6144 units.

Corpus-wide, using relations rather than tiles:

```text
raised islands before the counter filters   campaign 959, curated 2146
bundles after them                          campaign 146 in 31 maps, curated 238 in 40 maps
```

The filters are measured, not chosen. Of 958 campaign blocking islands the
rise distribution puts its largest mass (38.3%) in the 4096-8192 band -- one
step to half a body -- and E6M1's counter sits at 6144, in the middle of it.
Above 1.45 player heights sits a second mass (33.2%): those are wall stubs
and pillars, and the waist band is what separates furniture from
architecture.

### What the campaign bundles are like

```text
aspect ratio         p25      2.0  median      2.5  p75      4.0
rise, Build units    p25     7168  median     8192  p75     8192
visible props        p25        1  median        2  p75        4
cap sectors          p25        0  median        0  p75        1

carry at least one cap          41/146
carry at least one visible prop 124/146
```

Wiring never counts as a prop. A sound marker on a plinth does not make it a
counter, and `reports/blood-wiring-placement.md` is why that has to be said.

## The clearance: an access front, not a prism

`04_...md` suggests a clearance around an object. The corpus says otherwise,
and it says so clearly enough to change the rule.

```text
campaign, n=146          min      p25   median      p75      max
widest free side        1.333    5.333    9.333   14.333     44.0
narrowest free side    -3.336   -1.333      0.0    0.333   11.333
```

```text
flush against the host on at least one side   107/146  (73%)
asymmetric (narrow side < half the wide one)  139/146  (95%)
would pass a clearance-all-round rule at 0.5  34/146  (23%)
```

**A clearance-all-round rule would reject 77% of the campaign's own
counters.** They back onto something -- a wall, another fixture -- and keep
one open side. So the representation is an *access front*: the widest free
side, `hard: false`, owned by the assembly, with the narrow sides recorded
rather than required.

Every campaign bundle keeps at least **1.333 player widths** on its widest
side, and the median is 9.33. That minimum is the check, because below it
nothing was observed:

```text
campaign bundles passing check_clearance   146/146
curated bundles passing                    228/238
```

### Counterexamples, preserved

10 curated bundles fall below the campaign minimum. They are
precedent, not convention, and they are the reason the floor is stated as
"the campaign minimum" rather than "the minimum":

```text
SSHIVE.MAP     sector:807   access front  0.333 pw  aspect   3.5
TEDE1M1.MAP    sector:63    access front  0.333 pw  aspect 2.333
DWE2M10.MAP    sector:57    access front  0.667 pw  aspect  18.0
DWE2M10.MAP    sector:885   access front  0.667 pw  aspect  18.0
DWE3M7.MAP     sector:827   access front  0.667 pw  aspect   4.0
SSEVICT.MAP    sector:212   access front  0.667 pw  aspect   8.0
SSEVICT.MAP    sector:547   access front  0.667 pw  aspect   2.0
SSHIVE.MAP     sector:340   access front  0.667 pw  aspect   6.0
```

The bounding-box measurement has its own artifact: a negative side means the
core's box reaches past its host's, which happens when the host is L-shaped.
Those are reported, not clamped.

## The scatter detector

`04_...md`: a common failure is to reach the right density by scattering
props, and a map can match sprite counts and still fail composition. So the
detector may not count sprites, and it does not: the signal is **support**.
An authored prop sits on something; a scattered one sits on the floor it
landed on.

The exit criterion is an A/B question -- the same props, placed two ways --
and `compare_placements` answers exactly that. Validated on a synthetic pair
(validation only, never evidence): one host room, one raised island, three
props on it, against the same three props on the host floor. Support share
1.00 against 0.00; doubling the scattered props does not move it.

### What it deliberately does not claim

Run on E6M1's own selling floor, the detector reports `mixed` at 0.16 --
three props on the cashwrap, sixteen on the shop floor. Every one of those
sixteen is hand-placed. A detector that called that *scattered* would be
wrong about the source material, so the verdict names what was measured
(`props_on_supports` / `props_off_supports` / `mixed`) instead of passing
judgement on a room's author.

## Limitations

- One bundle type. Table + chairs was the alternative pilot and was not
  needed: the counter evidence is 146 campaign instances in 31 maps, which
  is not thin.
- Clearance is a bounding-box gap between core and host, named as one. It is
  exact under the quarter-turn rotations Build admits and is not a swept
  volume.
- The waist band, the aspect floor and the carried-something rule are three
  thresholds fitted to one anchor and checked against the corpus
  distribution. They are not validated against a held-out set.
- `curated` is precedent. Nothing in this report reads community geometry as
  Blood convention.
- Synthetic scenes validate the detector and are never evidence about Blood.

