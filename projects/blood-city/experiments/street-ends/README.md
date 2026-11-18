# Experiment: a street ends in a wall with the sky behind it

2026-11-17, night. Follows `../shopfronts-streets`. Before/after pairs:
[`before-after.png`](before-after.png). `hypothesis.json` was written before
the first edit.

## What was wrong

Survey finding 2, and both of the evening's blind reviewers: every long view
ends in black, "black void below the skyline".

Measured: the city's edge is 184,320 units of one-sided masonry (tile 417,
shade 8 to 9) across the far side of a perimeter lane, and a one-sided wall
of a parallax sector is drawn to that sector's sky: 11.6 bodies. The avenue
is 57,000 units long. Its far end was a black slab from pavement to sky line.

## What the campaign does

`look.py --ref E3M1 --sectors 8`, the same observer on the campaign's own
city street: the street ends in a wall about a third of the height of the
buildings beside it, and red sky fills the gap above.

`bloodmap.street.end_wall` has held the measurements of those walls since
September (s0, s339, s343: raised masses 3.86 to 5.80 bodies up, faced in
the district facade) and nothing ever built one. What the measurements left
out is **what stands behind them**: sectors s340 and s338, whose floor and
ceiling are both at grade and whose ceiling is parallax.

A sector with no height draws no wall. The mass in front is two-sided to it
and both skies are parallax, so the engine draws no upper step
(engine.cpp:4688). The eye goes over the end wall into sky. It is the
opposite of this morning's lowered sky: that one hid what stood behind it;
this one is put where nothing does.

And the faces: E3M1 wears its facade on them at **shade -8, cstat 1**
(blocking), against 24 to 34 on the masonry beside them.

## What was built

`streets.end_walls`: at the perimeter end of the avenue (north), Theatre Row
(west) and the market street (west and east), a mass outside the city's edge
across the street's mouth, 98,304 up (5.80 bodies, E3M1 s0), topped in 379
as E3M1's are, with a backing sector of no height behind it. A mouth lies in
two districts, so each end is two masses side by side, each in its own
district's facade: eight masses, eight backings.

`bloodmap.skyline.is_sky_backing` names the thing; `lowered_skies` and the
`open-neighbours-share-a-sky` rule no longer take it for a lid (the rule
fired eight times on the first build).

## The predictions, scored

| | prediction | result |
|---|---|---|
| V1 | sky share rises 0.02 or more in each of the nine `vistas` frames | **failed in five**: far frames +0.012, +0.010, +0.008 (and +0.025); `avenue_north_near` 0 and `market_east_near` +0.009, both too close to see over the wall; the other three +0.061, +0.042, +0.024. At 30,000 units the whole end of a street is a few hundred pixels |
| V2 | near frames read as a wall with sky above; named at "likely" or better | held: "red brick and grey stone windowed facades, with a sky patch above (certain)" |
| V3 | far frames no longer described as black or void | **partly, then held**: first build, "the same spots are dark, but they are low enough to read as distant, unlit buildings under the sky ... not good, but they are not slabs". Lighting the faces as E3M1 does came after that review; the far end now shows its windows, and no stranger has seen it |
| V4 | no new rule error, deterministic, load oracle, suite | see below |
| V5 | the backing sectors paint nothing but sky | held: no seam, no surface; the reviewer "saw no sky bleeding through solid surfaces" |
| C1 | shopfront frames change by fewer than 500 px | **failed as written** for the pawn shop (26,852 to 49,629 px): it looks out across the lane at the perimeter wall beside the avenue's mouth, whose texture run now restarts at the mouth, and a sliver of the end wall is in frame. The market hall and the arcade: 0 to 263 |

Could-be-wrong, as written beforehand: "at 30,000 units the end wall may
still be a black band, only shorter" was true of the first build and is why
the faces were then lit. "A low wall with nothing behind it may read as the
edge of the world": it did not ("buildings across the street").

## What a stranger saw

One fresh reviewer, two unlabelled folders, the nine `vistas` frames of the
first build (faces not yet lit) against before. It preferred the new one in
**9 of 9** (`critic.md`).

- Before: "a tall black slab rising well into the sky band"; near, "one
  repeated grey brick-scar tile, flat, with no openings, base or top. This
  is a backdrop or a set wall."
- After: "the ends read as buildings across the street." Where two facades
  meet at a seam: "two adjacent buildings, not an error."
- Still wrong, in its order: the far end is "an untextured dark block"
  (since lit); "the end facades sit on grey brick filler walls ... the
  facades look pasted onto them"; and "no door at street level, no sidewalk
  return and no depth change where the street meets them, so the street just
  stops against a picture of a building."
- It also found two stray light lines on the OLD perimeter wall
  (`avenue_north_mid`, `market_east_near`), which are gone with it, and a
  black rectangle at the left of `market_west_far` in both sets, which is
  not investigated.

## Does it run

325 sectors / 2,074 walls / 469 sprites. Rules 12 errors, 7 warnings, as
before this experiment. Conformance 12/13, the same one sector over.
Determinism, load oracle and suite: `measurements.txt`.

## Not done

- The rest of the perimeter is still 11.6 bodies of blank masonry, and the
  end facades stand in it "pasted on". The lanes run along it for their
  whole length.
- An end wall is a flat face: no door, no pavement return, no depth.
- ~~The campaign is lit much brighter than this city.~~ **Retracted the
  same night.** I read that off a few E3M1 records (sector 8's floor at 8,
  the end masses' faces at -8). Weighed over every open-sky surface
  (`tools/city_profile.py`), E3M1's road is at 32 and its pavement at 34,
  the same as Gravesend's 32. What E3M1 has that this city lacks is
  **contrast**: chosen facade faces at -8 against masonry at 34, where every
  wall here is a flat 9. E6M1 is a brighter map (ground 8, walls 24).
- The avenue's south end and the spur's ends were not given end walls: the
  river and the yard are there.
