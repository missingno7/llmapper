# Blind review, first after-build against before

One fresh reviewer (Opus), shown two unlabelled folders of the same 19 views
(K = the first after-build, with centre strips still in the roads; R =
before) and nothing else. Its readings are interpretation, not measurement.
Condensed; quotations are its words.

Per view it preferred K in 17, R in 1 (`hall_band`, "narrowly"), neither in 1
(`foundry_road`).

**Windows.** K: "the glass is set into the wall: it has a recess, mullions or
posts, a sill ledge and a dark frame". R: "looks laid flat on the wall: one
pale, rain-streaked sheet with no divisions, nearly flush"; "so opaque that
the interiors vanish". The wall above and beside the windows "matches the
facade's scale in both sets", with one doubt about R's `super_north` it
"can't be sure" of.

**Streets.** K: "grey flag pavements, raised kerbs, cobble roads and lamps";
`super_north_far` is "the clearest street read in either set". R: "you can
almost never tell: every floor is the same red cobble". Things in K that
"look like mistakes": "the grey cross-strips and the vertical centre strip"
(`avenue_road_level`), "the grey stripe down the middle of the road"
(`crossing`), and in `kerb_along` "a whole half of the street is flags flush
with the cobble, with no kerb step". Still one surface in both:
`market_road_level`, `spawn_wide`, `row_road_level`, `foundry_road`.

**hall_band.** K: "patchy. Red tile shows over some openings and plain flat
grey plaster over others ... It looks unfinished." R: "continuous red brick
with X-braced timber or crate-face panels as a frieze over every opening.
That is consistent, but it is crate art used as wall trim." "Neither is
right. R is less wrong."

**Texture faults named.** `mall_north` K: "offset texture block above the
first window"; R: "vertical smeared texture" in the same place.
`west_street_on_road` R: "stretched brownish texture on the kerb faces".

**Three biggest problems left in K.** (1) "Street floors carry stray strips
... pavement should never be a stripe down the road." (2) "Many streets and
squares are one surface." (3) "The hall_band wall is unfinished"; the
`mall_north` band "is also offset".

## What was done with it

(1) The centre strip and the cross-strips were removed: a seam street's road
is on one side, and end-on gaps are 1024 crossings. (2) and the `mall_north`
offset: not done. (3) The band is the tile's own dado standing on the floor;
left, and recorded as a design question. The final build has not been shown
to a reviewer.
