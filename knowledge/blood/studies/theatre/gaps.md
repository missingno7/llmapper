# Gaps: the Aldermack against what Blood builds

Ours is measured from `projects/blood-city/level/blood-city-current.MAP`
(house s20, stage s21, rows s22-s24, curtain s34, backstage s25, foyer s27,
box office s28) and the six frames rendered from it. Exemplars are in
`notes.md`. A body (b) is 16,960 z; 1,024 units is 1.7 m. Priority order:
the first four are why it does not read as a theatre at all.

## 1. Hang a proscenium: three bays and a header, across the full house width

- **Change:** the stage is a step under a 24,576-clear soffit, so from the
  back of the house there is no frame. Build a 128-deep curtain-line strip
  across the house at the stage's front edge, split into three bays.
- **Recipe:** centre bay 5,120-5,376 wide (8.7-9.1 m), ceiling = stage floor
  - 60,416 (3.6 b); two side bays 1,024-2,304 wide, ceiling = stage floor -
  51,200 (3.0 b). The house ceiling over the apron stays far higher (item 2),
  so the upper walls between the apron and each bay are a header: tile 70 on
  those upper walls (SCHOOL_ s177 walls 1329-1333, cstat 4, x_repeat 8/24,
  y_repeat 8). Keep the house walls on their own tile so the header is a
  different material.
- **Exemplar:** SCHOOL_.MAP s179/s181/s182 (strip y 36,992-37,120) under
  apron s177.
- **Frame test:** from the back row looking at the stage, a grey framed band
  spans the room above the curtain, and its underside steps down at both
  side bays; the curtain fills at least half the frame's height.

## 2. Make the house tall: 5.5-6.8 bodies over the seats

- **Change:** our house is 49,152 z (2.9 b) at the stage end. Every exemplar
  is twice that.
- **Recipe:** house ceiling at house floor - 96,256 (5.7 b) at the stage end
  (SCHOOL_ apron s177 clear 97,280; house s154 115,712; FORDTHEA 106,496;
  E1M1 chapel 98,304). Keep the existing AUDITORIUM_PITCH slope if wanted; the
  slope must not bring the rear below 4.7 b (DARKTHEA's 79,872).
- **Exemplar:** SCHOOL_.MAP s154/s177; FORDTHEA.MAP s252.
- **Frame test:** from the back of the house with level horizon, the ceiling
  is not in the top quarter of the frame; the header of item 1 sits clearly
  below it.

## 3. The curtain closed, in the proscenium, framed by static drapes

- **Change:** s34 stands 256 in front of the stage on the house floor and the
  file holds it gathered, so no frame shows it. Put the moving leaf IN the
  centre bay of item 1, closed at load, and dress the side bays with static
  drapes.
- **Recipe:** moving leaf as now (thin type-614 sector, walls 146, the
  owner's bound curtain; E1M1 s125 profile: 128 deep, markers type 3/4 at its
  ends, XSECTOR rx = open channel, tx = stage link, command 5, busy 15-40,
  busy_wave 1), with the closed pose spanning the full centre bay and the
  x_repeat authored for that span (E1M1 s125 uses 24 per 4,352). Side bays:
  over_picnum 159 (owner: "crumpled curtain") on the strip's stage-side walls,
  cstat 17 (blocking + masked), x_repeat 24 per 2,304, y_repeat 8, shade 40,
  as SCHOOL_ walls 1346 and 1360.
- **Exemplar:** E1M1.MAP s125 (moving); SCHOOL_.MAP s179/s182 walls 1346/1360
  (static).
- **Frame test:** from the back row the centre bay is solid 146 drapery
  floor-to-header; the side bays show the festooned 159 swags; after the open
  channel fires, the centre shows the stage and the side swags remain.

## 4. Seats you can count: sector pews in rows, with a centre aisle

- **Change:** rows s22-s24 are 5,120-wide slabs 1,024 high; they read as
  carpet stripes.
- **Recipe:** each row two strips (E1M1 s46/s47): seat 512 deep at floor
  +4,096 z (0.24 b), top 300 (carpet); back 256 deep at floor +10,240 (0.60
  b), top 20 (wood); the house-side wall faces: front 300, ends 84
  (wainscot), rear 20. Split every row by a centre aisle of 1,024-2,048 (scale
  AISLE 1,024 minimum) and keep side aisles of at least 1,024 (DARKTHEA
  1,536). Row pitch 1,280-1,536 (FORDTHEA 1,280); a cross-aisle of 2,048 if
  the house gets deep enough for two blocks of rows (SCHOOL_).
- **Exemplar:** E1M1.MAP s46/s47 and s49/s48 (pew profile); FORDTHEA.MAP
  s89-s92, s17/s18 (bench pitch and side aisles); SCHOOL_.MAP spr 619-666
  (grid and aisle).
- **Frame test:** from the stage looking back, distinct rows of wooden backs
  are visible with an open aisle running up the middle to the back wall.

## 5. Rake the floor up toward the back

- **Change:** the rows climb but the house floor between them is flat at
  8,192, so the room has no fall toward the stage.
- **Recipe:** step each row's floor sector 1,024 z above the one in front
  (SCHOOL_: 1,024 z per 1,024 units; DARKTHEA: 4,096 per 2,048-deep row --
  too steep for our depth), the aisle stepping with it; pews of item 4 stand
  on their own row's floor. Total over 4 rows about 4,096 z (0.24 b).
- **Exemplar:** SCHOOL_.MAP s154 (floor_stat 66, heinum 256); DARKTHEA.map
  s374-s387.
- **Frame test:** from the back row with level horizon the front pews sit
  lower in the frame than the near ones, and the stage floor is about at
  eye level.

## 6. A stage that stands proud, with a lip skirted in curtain

- **Change:** our stage is 0.24 b (one step), its face wears the house wall.
- **Recipe:** stage floor 8,192-11,520 z (0.48-0.68 b) above the front of the
  house; the stage's front faces seen from the house wear 146 (SCHOOL_ wall
  1213: the pit wall toward the stage is 146), and a pair of side steps of
  at most one step height each at the ends of the apron so the player can get
  up. Stage floor tile 15 (owner: "planks") instead of the house carpet.
- **Exemplar:** SCHOOL_.MAP s177 over pit s165 (and steps s161-s164).
- **Frame test:** from the front row, the stage edge is at chest height and
  its face is draped; the stage floor reads as boards, not carpet.

## 7. Give the stage room behind the curtain line

- **Change:** our stage is 2,048 deep and the backstage is a corridor along
  the west side. In SCHOOL_ the stage behind the curtain is 6,784 deep and
  wider than the opening (wings either side of the 9,984 curtain line).
- **Recipe:** at least 4,096 (7 m) of stage behind the curtain line, the full
  house width, so 1,024-2,048 of wing shows beyond each side bay; the backstage
  door enters a wing, not the house. At the back of the stage, two risers
  (SCHOOL_ s189 +4,096 and s183 +12,288, the width of the centre bay) and a
  door (s190). If the block cannot take it, give the stage the north strip of
  the house and shorten the seating to three rows rather than shrink the stage.
- **Exemplar:** SCHOOL_.MAP s244 (with s183, s189, s190).
- **Frame test:** with the curtain open, from the back row one sees a deep
  stage with risers and wing walls beyond the opening, not a wall 2,048 away.

## 8. A dark house

- **Change:** every floor in the theatre is shade 32; nothing separates house,
  stage and foyer.
- **Recipe:** house floor shade 40-42, ceiling 47 (SCHOOL_ s154); pew tops within 4 of the
  house floor (E1M1 s46 30 against the chapel's 21 is the most contrast seen); the foyer
  brighter than the house (27 or lower, as now); behind the curtain, split the
  stage's back and side walls into 256-unit pieces with shade rising 4 per
  piece away from the opening (E1M1 s124 walls 1184-1197: 24 to 48), so the
  curtain-linked brightening (s21 rx 341, amplitude -24) has a dark field to
  show against.
- **Exemplar:** SCHOOL_.MAP s154/s244 shades; E1M1.MAP s124.
- **Frame test:** the house frames are darker than the foyer frame; with the
  curtain open, the stage is the brightest surface in the house frame.

## 9. A ticket window in a wall, and the cinema poster in the foyer

- **Change:** our box office is a free-standing 0.48 b counter (s28) in the
  middle of the foyer.
- **Recipe:** a booth behind a wood-panelled front wall (179, owner: "wooden
  panel") with two window openings split by a post, over a counter of 6,144 z
  (0.36 b) 512 deep, the clerk's floor behind it (FORDTHEA s239 and s119);
  posters on the foyer walls as wall sprites: 2047 (BLOOD THE MOVIE, "coming
  soon to a theater near you"; unnamed by the owner, looked at -- tell him)
  and 981 (owner: poster "JOJO the idiot circus boy").
- **Exemplar:** FORDTHEA.MAP s239/s119/s236 (lobby counter); s250 wall 1408
  (2047).
- **Frame test:** from the foyer door the booth reads as a panelled wall with
  two lit windows, someone behind, and a poster beside it.

## 10. Stop sharing the house's wallpaper with everything

- **Change:** house, foyer and stage walls are all tile 119 (DARKTHEA, the
  theatre that does not read, also uses 119).
- **Recipe:** house walls one material, header (item 1) 70, stage and wings a
  plain material (SCHOOL_ 272, grey), stage floor 15, foyer its own. Look up
  every replacement with `tools.tile_usage` and read its picture first.
- **Exemplar:** SCHOOL_.MAP (272 stage, 70 header, 15 stage floor, 159/146
  drapes).
- **Frame test:** in the across-the-house frame, house wall, header, curtain
  and stage are four different surfaces.
