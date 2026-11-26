# Workers' washhouse: source evidence and first finish

How Blood builds a toilet and its flush (E2M4 room 487) is on the shelf:
`knowledge/blood/studies/washroom/notes.md`. This page is the project's own.

This is room **152**, toilet stalls **58/59**, urinal alcove **119**, partitions
**52/53/54/55** and swinging door **61**. The explicit editing boundary is in
`places.json`. Source sprites 479/480 are TOILET 569; 477/478 are STALL 571
(wall urinals), as named by EDuke32's names.h and shown in the Duke ART views.
They were omitted from the initial conversion. Source fixture coordinates
and hitags are recorded by `inspect_washhouse.py`.

The early label “bathroom 389” was wrong. Its door-50 motion bug was real,
but it is a separate room. `evidence/duke-source/washhouse/source/` contains those earlier
misidentified views; `actual-source/` and `actual-source-empty/` beside it
show the actual bathroom.
The empty evidence is a separate viewing copy with actors/items hidden.
Original Duke geometry, ART numbers and palette are retained. This observer
does not execute Duke effects or mirrors; missing art and mirror presentation
must not be read as intended materials.

## The room-wide rotation

Source SE11 sprite **487**, hitag **409**, is in plain lotag-0 room **152**.
No same-hitag ST23 operator exists. EDuke32 sector.cpp's ST23 branch arms
same-hitag SE11 groups, then actors.cpp moves them only while T5 is active.
This controller is inert in the source map. Sprite **488**, hitag **408**,
belongs to the actual ST23 door **61** and remains a valid mover.

The converter had turned room 152 into a Push rotor, then attached touchplate
777's entry signal to it. Entering could rotate the entire room. Pass 09
restores the static room and preserves its entry TX, command and triggers.
Generated marker 7 is retired invisibly in place, with no deletion or
renumbering. Independent SE12 lighting is diagnosed instead of overwriting
the entry command. E1L2's room 262 supplies a second corpus regression for
the same inert-SE11 case. A plain-sector group member *can* move if a real
ST23 shares its hitag; the synthetic regression preserves that distinction.

## Blood's precedent, as used here

E2M4's stone toilet and its flush toggle (see the shelf study). Owner tile
names chosen for their jobs: 296 grimy tiles, 297 tiles, 215 pressed metal,
2453 riveted metal cladding, 2290 fluorescent light, 2915 water surface,
2178 riveted vent grille (also campaign factory E6M4:159). Tile 843 was
looked at and rejected: a small wooden pedestal basin.

## Pass 10 hypothesis and result

Tile walls and a grimy service floor should identify a washable utility room;
metal partitions should read as fittings rather than load-bearing masonry.
Stone toilets, exposed urinal pipes, flush controls, vents and ceiling lights
should establish the room's use without lettering or extra narrative props.
The room remains dim, with a legible floor and practical fixtures, appropriate
to the covert quarry works during a storm.

The guarded patch changes materials and static shades in the explicit
boundary. It adds **56 sprites**: two commodes, two urinals, four local sound
controls and two ceiling fixtures. Stone fixtures use wall/floor sprites to
keep every existing sector, wall index and portal unchanged. The measured
E2M4 construction is the precedent; this is a rectangular interpretation,
not a transplant of its rounded sector geometry. Water 2915 replaces the
reference toilet's sewage 997. The sound controls declare no wire because
they have no TX or RX; they use the campaign's local toggle-sound behavior.

Trial renders caught excessive fixture shade: Blood adds the sector shade
to these sprites. The final patch compensates with negative local shades.
The smaller commodes also leave clearance ahead of the retained stall actor.
New fittings have no sprite-fit faults or coplanar flat overlaps. Native
read-back confirms no existing sprite, extension, geometry or start changes
in pass 10. The room repair and original door are checked separately.

The same-pose before/after views are in `evidence/washhouse-before/` and
`evidence/washhouse-after/`. No blind reader has answered a packet of it (the old
`reviews/` packets were prepared and never answered; see the README).
Author inspection is not an independent pass. Live collision, fixture Use/flush sound, stall obstruction/reversal and
encounter behavior still need owner play.

Mirror alcove **117** and support **57** are excluded. Their native mirror
repair is still open. Camera-only scenery 535–542 is separate and has not
been deleted. No source MAP or Blood City file is an editing target.
