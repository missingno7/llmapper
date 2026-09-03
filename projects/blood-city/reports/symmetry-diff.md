# Symmetry diff: projects/blood-city

What `projects/blood-city/facts/` DECLARES against what `bloodmap.read_facts.recover` reads back from `projects/blood-city/level/slice2-streets.MAP`. Produced by `tools/symmetry_diff.py`; every number is a query over the two stores.

**2490 rows declared, 8639 recovered, 1070 ids on both sides, 7366 rows in disagreement outside the base predicates.**

## Disagreements by class

| class | findings |
| --- | --- |
| missing id | 14 |
| extra id | 29 |
| same id different attrs | 1 |
| unknown kind | 6 |
| field only one side writes | 2 |

* **missing id** — declared, not recovered: the compiler says it built something no reader finds.
* **extra id** — recovered, not declared: the map says something the build did not mean to say. Normal on a base predicate, a finding anywhere else.
* **same id different attrs** — both halves name one thing and disagree about it.
* **unknown kind** — a vocabulary value one side has never heard of, and where the other side does keep it.
* **field only one side writes** — a difference in the SHAPE of a predicate, counted once per field rather than once per row.

## Per predicate

| predicate | declared | recovered | same id | missing | extra | attrs differ | unknown kind |
| --- | --- | --- | --- | --- | --- | --- | --- |
| attachment | 0 | 503 | 0 | 0 | 503 | 0 | 0 |
| block | 0 | 10 | 0 | 0 | 10 | 0 | 0 |
| candidate | 0 | 20 | 0 | 0 | 20 | 0 | 0 |
| claims | 127 | 2766 | 0 | 127 | 2766 | 0 | 0 |
| condition | 0 | 54 | 0 | 0 | 54 | 0 | 0 |
| connects *(base)* | 0 | 420 | 0 | 0 | 420 | 0 | 0 |
| corridor | 0 | 33 | 0 | 0 | 33 | 0 | 0 |
| edge_segment | 0 | 94 | 0 | 0 | 94 | 0 | 4 |
| fill | 9 | 0 | 0 | 9 | 0 | 0 | 0 |
| frame | 775 | 166 | 0 | 775 | 166 | 0 | 0 |
| island | 19 | 8 | 0 | 19 | 8 | 0 | 0 |
| join | 1058 | 924 | 924 | 134 | 0 | 0 | 4 |
| key | 5 | 5 | 0 | 5 | 5 | 0 | 0 |
| lamp_delta | 18 | 0 | 0 | 18 | 0 | 0 | 0 |
| light_source | 0 | 15 | 0 | 0 | 15 | 0 | 0 |
| link | 9 | 9 | 0 | 9 | 9 | 0 | 0 |
| part_of | 205 | 422 | 0 | 205 | 422 | 0 | 7 |
| plan_edge | 0 | 21 | 0 | 0 | 21 | 0 | 0 |
| realises | 9 | 27 | 0 | 9 | 27 | 0 | 0 |
| residue | 0 | 810 | 0 | 0 | 810 | 0 | 0 |
| sector *(base)* | 0 | 191 | 0 | 0 | 191 | 0 | 0 |
| selection | 0 | 10 | 0 | 0 | 10 | 0 | 0 |
| sentence | 9 | 18 | 0 | 9 | 18 | 0 | 2 |
| shade_depth | 191 | 146 | 146 | 45 | 0 | 143 | 0 |
| shade_edge | 0 | 320 | 0 | 0 | 320 | 0 | 0 |
| sprite *(base)* | 0 | 32 | 0 | 0 | 32 | 0 | 0 |
| sun | 0 | 1 | 0 | 0 | 1 | 0 | 0 |
| surface | 47 | 166 | 0 | 47 | 166 | 0 | 9 |
| surface_kind | 0 | 191 | 0 | 0 | 191 | 0 | 9 |
| unknown_join | 0 | 134 | 0 | 0 | 134 | 0 | 0 |
| void | 9 | 0 | 0 | 9 | 0 | 0 | 0 |
| wall *(base)* | 0 | 1077 | 0 | 0 | 1077 | 0 | 0 |
| xsector *(base)* | 0 | 32 | 0 | 0 | 32 | 0 | 0 |
| xsprite *(base)* | 0 | 14 | 0 | 0 | 14 | 0 | 0 |

**Declared and never recovered:** `fill`, `lamp_delta`, `void` — a claim nothing checks.

**Recovered and never declared:** `attachment`, `block`, `candidate`, `condition`, `corridor`, `edge_segment`, `light_source`, `plan_edge`, `residue`, `selection`, `shade_edge`, `sun`, `surface_kind`, `unknown_join` — what the map says beyond the build.

## Every finding

### `frame` — missing id, 775

`run:0`, `run:1`, `run:10`, `run:100`, `run:101`, `run:102`, `run:103`, `run:104`, `run:105`, `run:106`, `run:107`, `run:108`, `run:109`, `run:11`, `run:110`, `run:111`, `run:112`, `run:113`, `run:114`, `run:115`, `run:116`, `run:117`, `run:118`, `run:119`, `run:12`, `run:120`, `run:121`, `run:122`, `run:123`, `run:124`, `run:125`, `run:126`, `run:127`, `run:128`, `run:129`, `run:13`, `run:130`, `run:131`, `run:132`, `run:133` … and 735 more

### `part_of` — missing id, 205

`piece:cemetery`, `piece:col_a/row_1`, `piece:col_a/row_2#0`, `piece:col_a/row_2#1`, `piece:col_a/row_2#2`, `piece:col_a/row_2#3`, `piece:col_a/row_2#4`, `piece:col_a/row_2#5`, `piece:col_a/row_2#6`, `piece:col_a/row_2#7`, `piece:col_a/row_3#0`, `piece:col_a/row_3#1`, `piece:col_a/row_3#2`, `piece:col_a/row_3#3`, `piece:col_a/row_3#4`, `piece:col_a/row_3#5`, `piece:col_a/row_3#6`, `piece:col_a/row_3#7`, `piece:col_a/row_3#8`, `piece:col_a/row_3#9`, `piece:col_b/row_1`, `piece:col_b/row_2#0`, `piece:col_b/row_2#1`, `piece:col_b/row_2#2`, `piece:col_b/row_2#3`, `piece:col_b/row_2#4`, `piece:col_b/row_2#5`, `piece:col_b/row_2#6`, `piece:col_b/row_2#7`, `piece:col_b/row_3#0`, `piece:col_b/row_3#1`, `piece:col_b/row_3#2`, `piece:col_b/row_3#3`, `piece:col_b/row_3#4`, `piece:col_b/row_3#5`, `piece:col_b/row_3#6`, `piece:col_b/row_3#7`, `piece:col_b/row_3#8`, `piece:col_b/row_3#9`, `piece:col_c/row_1` … and 165 more

### `join` — missing id, 134

`wall:1000`, `wall:1002`, `wall:1003`, `wall:1004`, `wall:1005`, `wall:1006`, `wall:1007`, `wall:1008`, `wall:1009`, `wall:1010`, `wall:1011`, `wall:1012`, `wall:1013`, `wall:1014`, `wall:1015`, `wall:1016`, `wall:1017`, `wall:1018`, `wall:1019`, `wall:1020`, `wall:1021`, `wall:1022`, `wall:1023`, `wall:1024`, `wall:1025`, `wall:1026`, `wall:1027`, `wall:1028`, `wall:1029`, `wall:1030`, `wall:1031`, `wall:1032`, `wall:1033`, `wall:1034`, `wall:1035`, `wall:1036`, `wall:1037`, `wall:1038`, `wall:1039`, `wall:1040` … and 94 more

### `claims` — missing id, 127

`claim:0:shade:sun:field`, `claim:10:shade:sun:field`, `claim:11:shade:sun:field`, `claim:129:shade:sun:field`, `claim:12:shade:sun:field`, `claim:130:shade:sun:field`, `claim:131:shade:sun:field`, `claim:132:shade:sun:field`, `claim:133:shade:sun:field`, `claim:134:shade:sun:field`, `claim:135:shade:sun:field`, `claim:136:shade:sun:field`, `claim:137:shade:sun:field`, `claim:138:shade:sun:field`, `claim:13:shade:sun:field`, `claim:140:shade:sun:field`, `claim:142:shade:sun:field`, `claim:143:shade:sun:field`, `claim:145:shade:sun:field`, `claim:146:shade:sun:field`, `claim:148:shade:sun:field`, `claim:149:shade:sun:field`, `claim:14:shade:sun:field`, `claim:150:shade:sun:field`, `claim:151:shade:sun:field`, `claim:152:shade:sun:field`, `claim:153:shade:sun:field`, `claim:154:shade:sun:field`, `claim:155:shade:sun:field`, `claim:156:shade:sun:field`, `claim:157:shade:sun:field`, `claim:159:shade:sun:field`, `claim:15:shade:sun:field`, `claim:161:shade:sun:field`, `claim:162:shade:sun:field`, `claim:164:shade:sun:field`, `claim:165:shade:sun:field`, `claim:167:shade:sun:field`, `claim:168:shade:sun:field`, `claim:169:shade:sun:field` … and 87 more

### `surface` — missing id, 47

`surface:cemetery`, `surface:col_a/row_1`, `surface:col_a/row_2`, `surface:col_a/row_3`, `surface:col_b/row_1`, `surface:col_b/row_2`, `surface:col_b/row_3`, `surface:col_c/row_1`, `surface:col_c/row_2`, `surface:col_c/row_3`, `surface:door:col_a/row_1`, `surface:door:col_a/row_2`, `surface:door:col_a/row_3`, `surface:door:col_b/row_1`, `surface:door:col_b/row_2`, `surface:door:col_b/row_3`, `surface:door:col_c/row_1`, `surface:door:col_c/row_2`, `surface:door:col_c/row_3`, `surface:end_wall:avenue`, `surface:end_wall:spur`, `surface:end_wall:west_street`, `surface:horizon`, `surface:interior:col_a/row_1`, `surface:interior:col_a/row_2`, `surface:interior:col_a/row_3`, `surface:interior:col_b/row_1`, `surface:interior:col_b/row_2`, `surface:interior:col_b/row_3`, `surface:interior:col_c/row_1`, `surface:interior:col_c/row_2`, `surface:interior:col_c/row_3`, `surface:market_plaza`, `surface:plane`, `surface:sea`, `surface:shell:col_a/row_1`, `surface:shell:col_a/row_2`, `surface:shell:col_a/row_3`, `surface:shell:col_b/row_1`, `surface:shell:col_b/row_2` … and 7 more

### `shade_depth` — missing id, 45

`sector:100`, `sector:101`, `sector:103`, `sector:104`, `sector:106`, `sector:107`, `sector:109`, `sector:110`, `sector:112`, `sector:113`, `sector:115`, `sector:116`, `sector:118`, `sector:119`, `sector:121`, `sector:122`, `sector:124`, `sector:125`, `sector:129`, `sector:132`, `sector:135`, `sector:14`, `sector:148`, `sector:151`, `sector:154`, `sector:167`, `sector:170`, `sector:173`, `sector:190`, `sector:2`, `sector:34`, `sector:39`, `sector:42`, `sector:44`, `sector:46`, `sector:58`, `sector:61`, `sector:63`, `sector:65`, `sector:7` … and 5 more

### `island` — missing id, 19

`island:cemetery`, `island:col_a/row_1`, `island:col_a/row_2`, `island:col_a/row_3`, `island:col_b/row_1`, `island:col_b/row_2`, `island:col_b/row_3`, `island:col_c/row_1`, `island:col_c/row_2`, `island:col_c/row_3`, `island:end_wall:avenue`, `island:end_wall:spur`, `island:end_wall:west_street`, `island:horizon`, `island:market_plaza`, `island:quay_walk`, `island:sea`, `island:shore`, `island:works_yard`

### `lamp_delta` — missing id, 18

`lamp:cemetery:0`, `lamp:col_a/row_1:0`, `lamp:col_a/row_1:1`, `lamp:col_a/row_2:0`, `lamp:col_a/row_2:1`, `lamp:col_a/row_3:0`, `lamp:col_b/row_1:0`, `lamp:col_b/row_1:1`, `lamp:col_b/row_2:0`, `lamp:col_b/row_2:1`, `lamp:col_b/row_3:0`, `lamp:col_c/row_1:0`, `lamp:col_c/row_1:1`, `lamp:col_c/row_2:0`, `lamp:col_c/row_2:1`, `lamp:col_c/row_3:0`, `lamp:market_plaza:0`, `lamp:works_yard:0`

### `fill` — missing id, 9

`fill:door:col_a/row_1`, `fill:door:col_a/row_2`, `fill:door:col_a/row_3`, `fill:door:col_b/row_1`, `fill:door:col_b/row_2`, `fill:door:col_b/row_3`, `fill:door:col_c/row_1`, `fill:door:col_c/row_2`, `fill:door:col_c/row_3`

### `link` — missing id, 9

`link:door:col_a/row_1:400`, `link:door:col_a/row_2:401`, `link:door:col_a/row_3:402`, `link:door:col_b/row_1:403`, `link:door:col_b/row_2:404`, `link:door:col_b/row_3:405`, `link:door:col_c/row_1:406`, `link:door:col_c/row_2:407`, `link:door:col_c/row_3:408`

### `realises` — missing id, 9

`realises:door:col_a/row_1:101`, `realises:door:col_a/row_2:104`, `realises:door:col_a/row_3:107`, `realises:door:col_b/row_1:110`, `realises:door:col_b/row_2:113`, `realises:door:col_b/row_3:116`, `realises:door:col_c/row_1:119`, `realises:door:col_c/row_2:122`, `realises:door:col_c/row_3:125`

### `sentence` — missing id, 9

`sentence:door:col_a/row_1`, `sentence:door:col_a/row_2`, `sentence:door:col_a/row_3`, `sentence:door:col_b/row_1`, `sentence:door:col_b/row_2`, `sentence:door:col_b/row_3`, `sentence:door:col_c/row_1`, `sentence:door:col_c/row_2`, `sentence:door:col_c/row_3`

### `void` — missing id, 9

`void:door:col_a/row_1`, `void:door:col_a/row_2`, `void:door:col_a/row_3`, `void:door:col_b/row_1`, `void:door:col_b/row_2`, `void:door:col_b/row_3`, `void:door:col_c/row_1`, `void:door:col_c/row_2`, `void:door:col_c/row_3`

### `key` — missing id, 5

`key:door:col_a/row_1`, `key:door:col_a/row_2`, `key:door:col_a/row_3`, `key:door:col_b/row_1`, `key:door:col_b/row_2`

### `shade_depth` — same id different attrs, 143

Fields that differ, by how many ids: `depth` (143)

* `sector:0`: `depth` declared 1, recovered 2
* `sector:1`: `depth` declared 2, recovered 3
* `sector:10`: `depth` declared 1, recovered 2
* `sector:102`: `depth` declared 0, recovered 1
* `sector:105`: `depth` declared 0, recovered 1
* `sector:108`: `depth` declared 0, recovered 1
* `sector:11`: `depth` declared 1, recovered 2
* `sector:111`: `depth` declared 0, recovered 1
* `sector:114`: `depth` declared 0, recovered 1
* `sector:117`: `depth` declared 0, recovered 1
* … and 133 more

### `surface` — unknown kind, 9

* `kind = end_wall` — compiler only, and kept in `edge_segment.kind`, `join.a`, `join.b`, `surface_kind.kind`
* `kind = facade` — compiler only, and kept in `join.a`, `join.b`, `surface_kind.kind`
* `kind = horizon` — compiler only
* `kind = interior` — compiler only, and kept in `join.a`, `join.b`, `surface_kind.kind`
* `kind = opening` — compiler only, and kept in `join.a`, `join.b`, `surface_kind.kind`
* `kind = pavement` — compiler only, and kept in `join.a`, `join.b`, `surface_kind.kind`
* `kind = road` — compiler only, and kept in `join.a`, `join.b`, `surface_kind.kind`
* `kind = sea` — compiler only
* `kind = shore` — compiler only, and kept in `join.a`, `join.b`, `surface_kind.kind`

### `surface_kind` — unknown kind, 9

* `kind = end_wall` — readers only, and kept in `join.a`, `join.b`, `surface.kind`
* `kind = facade` — readers only, and kept in `join.a`, `join.b`, `surface.kind`
* `kind = interior` — readers only, and kept in `join.a`, `join.b`, `surface.kind`
* `kind = opening` — readers only, and kept in `join.a`, `join.b`, `surface.kind`
* `kind = pavement` — readers only, and kept in `join.a`, `join.b`, `surface.kind`
* `kind = road` — readers only, and kept in `join.a`, `join.b`, `surface.kind`
* `kind = shore` — readers only, and kept in `join.a`, `join.b`, `surface.kind`
* `kind = solid` — readers only
* `kind = water` — readers only

### `part_of` — unknown kind, 7

* `kind = assembly` — readers only
* `kind = detail_group` — readers only
* `kind = member` — readers only
* `kind = space` — readers only
* `kind = structure` — readers only
* `kind = cell` — compiler only
* `kind = gutter` — compiler only

### `edge_segment` — unknown kind, 4

* `kind = building_back` — readers only
* `kind = end_wall` — readers only, and kept in `join.a`, `join.b`, `surface.kind`
* `kind = interior_doorway` — readers only
* `kind = waterfront` — readers only

### `join` — unknown kind, 4

* `a = horizon` — compiler only
* `a = sea` — compiler only
* `b = horizon` — compiler only
* `b = sea` — compiler only

### `sentence` — unknown kind, 2

* `kind = sector mechanism` — readers only
* `kind = tx -> rx chain` — readers only

### `join` — field only one side writes, 6

* compiler only: `picnum`, `shade`
* readers only: `blocking`, `record`, `row`, `wears_tile`
* both: `a`, `b`, `frame`, `height`, `shows`

### `shade_depth` — field only one side writes, 4

* compiler only: `base`, `sources`, `step`
* readers only: `record`
* both: `depth`, `shade`

### `claims` — extra id, 2766

`sector:0:floor_shade`, `sector:101:type`, `sector:102:floor_shade`, `sector:104:type`, `sector:105:floor_shade`, `sector:107:type`, `sector:108:floor_shade`, `sector:10:floor_shade`, `sector:110:type`, `sector:111:floor_shade`, `sector:113:type`, `sector:114:floor_shade`, `sector:116:type`, `sector:117:floor_shade`, `sector:119:type`, `sector:11:floor_shade`, `sector:120:floor_shade`, `sector:122:type`, `sector:123:floor_shade`, `sector:125:type`, `sector:126:floor_shade`, `sector:127:floor_shade`, `sector:128:floor_shade`, `sector:129:floor_z`, `sector:12:floor_shade`, `sector:130:floor_shade`, `sector:130:floor_z`, `sector:131:floor_shade`, `sector:131:floor_z`, `sector:132:floor_z`, `sector:133:floor_shade`, `sector:133:floor_z`, `sector:134:floor_shade`, `sector:134:floor_z`, `sector:135:floor_z`, `sector:136:floor_shade`, `sector:136:floor_z`, `sector:137:floor_shade`, `sector:137:floor_z`, `sector:138:floor_shade` … and 2726 more

### `residue` — extra id, 810

`intent:assembly:001/space:003`, `intent:assembly:001/space:007`, `intent:assembly:001/space:011`, `intent:sentence:channel:400`, `intent:sentence:channel:401`, `intent:sentence:channel:402`, `intent:sentence:channel:403`, `intent:sentence:channel:404`, `intent:sentence:channel:405`, `intent:sentence:channel:406`, `intent:sentence:channel:407`, `intent:sentence:channel:408`, `island:step:3072`, `island:step:67840`, `island:step:96320`, `island:step:98368`, `join:wall:1000`, `join:wall:1002`, `join:wall:1003`, `join:wall:1004`, `join:wall:1005`, `join:wall:1006`, `join:wall:1007`, `join:wall:1008`, `join:wall:1009`, `join:wall:1010`, `join:wall:1011`, `join:wall:1012`, `join:wall:1013`, `join:wall:1014`, `join:wall:1015`, `join:wall:1016`, `join:wall:1017`, `join:wall:1018`, `join:wall:1019`, `join:wall:1020`, `join:wall:1021`, `join:wall:1022`, `join:wall:1023`, `join:wall:1024` … and 770 more

### `attachment` — extra id, 503

`surface:0000:wall:0`, `surface:0000:wall:145`, `surface:0000:wall:146`, `surface:0002:wall:16`, `surface:0002:wall:166`, `surface:0002:wall:181`, `surface:0002:wall:192`, `surface:0002:wall:193`, `surface:0002:wall:2`, `surface:0002:wall:201`, `surface:0002:wall:202`, `surface:0002:wall:4`, `surface:0005:wall:183`, `surface:0005:wall:6`, `surface:0007:wall:187`, `surface:0007:wall:199`, `surface:0007:wall:212`, `surface:0007:wall:8`, `surface:0016:wall:22`, `surface:0016:wall:23`, `surface:0016:wall:24`, `surface:0019:wall:27`, `surface:0019:wall:438`, `surface:0019:wall:94`, `surface:0019:wall:95`, `surface:0019:wall:96`, `surface:0019:wall:97`, `surface:0021:wall:120`, `surface:0021:wall:29`, `surface:0021:wall:327`, `surface:0021:wall:444`, `surface:0023:wall:147`, `surface:0023:wall:220`, `surface:0023:wall:31`, `surface:0023:wall:333`, `surface:0024:wall:189`, `surface:0024:wall:190`, `surface:0024:wall:32`, `surface:0024:wall:33`, `surface:0025:wall:34` … and 463 more

### `part_of` — extra id, 422

`space:assembly:001`, `space:assembly:001/space:001`, `space:assembly:001/space:001/details`, `space:assembly:001/space:001:sector:0`, `space:assembly:001/space:001:sector:1`, `space:assembly:001/space:001:sector:10`, `space:assembly:001/space:001:sector:103`, `space:assembly:001/space:001:sector:104`, `space:assembly:001/space:001:sector:106`, `space:assembly:001/space:001:sector:107`, `space:assembly:001/space:001:sector:11`, `space:assembly:001/space:001:sector:112`, `space:assembly:001/space:001:sector:113`, `space:assembly:001/space:001:sector:115`, `space:assembly:001/space:001:sector:116`, `space:assembly:001/space:001:sector:12`, `space:assembly:001/space:001:sector:121`, `space:assembly:001/space:001:sector:122`, `space:assembly:001/space:001:sector:124`, `space:assembly:001/space:001:sector:125`, `space:assembly:001/space:001:sector:129`, `space:assembly:001/space:001:sector:13`, `space:assembly:001/space:001:sector:130`, `space:assembly:001/space:001:sector:131`, `space:assembly:001/space:001:sector:132`, `space:assembly:001/space:001:sector:133`, `space:assembly:001/space:001:sector:134`, `space:assembly:001/space:001:sector:135`, `space:assembly:001/space:001:sector:136`, `space:assembly:001/space:001:sector:137`, `space:assembly:001/space:001:sector:138`, `space:assembly:001/space:001:sector:139`, `space:assembly:001/space:001:sector:14`, `space:assembly:001/space:001:sector:140`, `space:assembly:001/space:001:sector:141`, `space:assembly:001/space:001:sector:142`, `space:assembly:001/space:001:sector:143`, `space:assembly:001/space:001:sector:144`, `space:assembly:001/space:001:sector:145`, `space:assembly:001/space:001:sector:146` … and 382 more

### `shade_edge` — extra id, 320

`wall:1`, `wall:1004`, `wall:1006`, `wall:1007`, `wall:1010`, `wall:1011`, `wall:1013`, `wall:1015`, `wall:1017`, `wall:1020`, `wall:1023`, `wall:1025`, `wall:1027`, `wall:1029`, `wall:1031`, `wall:1033`, `wall:1036`, `wall:1039`, `wall:104`, `wall:1041`, `wall:1043`, `wall:1045`, `wall:1047`, `wall:1049`, `wall:109`, `wall:11`, `wall:111`, `wall:113`, `wall:115`, `wall:117`, `wall:123`, `wall:129`, `wall:13`, `wall:132`, `wall:138`, `wall:140`, `wall:141`, `wall:15`, `wall:150`, `wall:156` … and 280 more

### `surface_kind` — extra id, 191

`sector:0`, `sector:1`, `sector:10`, `sector:100`, `sector:101`, `sector:102`, `sector:103`, `sector:104`, `sector:105`, `sector:106`, `sector:107`, `sector:108`, `sector:109`, `sector:11`, `sector:110`, `sector:111`, `sector:112`, `sector:113`, `sector:114`, `sector:115`, `sector:116`, `sector:117`, `sector:118`, `sector:119`, `sector:12`, `sector:120`, `sector:121`, `sector:122`, `sector:123`, `sector:124`, `sector:125`, `sector:126`, `sector:127`, `sector:128`, `sector:129`, `sector:13`, `sector:130`, `sector:131`, `sector:132`, `sector:133` … and 151 more

### `frame` — extra id, 166

`frame:surface:0000`, `frame:surface:0002`, `frame:surface:0005`, `frame:surface:0007`, `frame:surface:0016`, `frame:surface:0019`, `frame:surface:0021`, `frame:surface:0023`, `frame:surface:0024`, `frame:surface:0025`, `frame:surface:0026`, `frame:surface:0028`, `frame:surface:0030`, `frame:surface:0039`, `frame:surface:0041`, `frame:surface:0044`, `frame:surface:0046`, `frame:surface:0049`, `frame:surface:0053`, `frame:surface:0058`, `frame:surface:0065`, `frame:surface:0068`, `frame:surface:0070`, `frame:surface:0076`, `frame:surface:0084`, `frame:surface:0086`, `frame:surface:0094`, `frame:surface:0104`, `frame:surface:0109`, `frame:surface:0110`, `frame:surface:0115`, `frame:surface:0117`, `frame:surface:0118`, `frame:surface:0120`, `frame:surface:0122`, `frame:surface:0123`, `frame:surface:0125`, `frame:surface:0130`, `frame:surface:0146`, `frame:surface:0150` … and 126 more

### `surface` — extra id, 166

`surface:0000`, `surface:0002`, `surface:0005`, `surface:0007`, `surface:0016`, `surface:0019`, `surface:0021`, `surface:0023`, `surface:0024`, `surface:0025`, `surface:0026`, `surface:0028`, `surface:0030`, `surface:0039`, `surface:0041`, `surface:0044`, `surface:0046`, `surface:0049`, `surface:0053`, `surface:0058`, `surface:0065`, `surface:0068`, `surface:0070`, `surface:0076`, `surface:0084`, `surface:0086`, `surface:0094`, `surface:0104`, `surface:0109`, `surface:0110`, `surface:0115`, `surface:0117`, `surface:0118`, `surface:0120`, `surface:0122`, `surface:0123`, `surface:0125`, `surface:0130`, `surface:0146`, `surface:0150` … and 126 more

### `unknown_join` — extra id, 134

`wall:1000`, `wall:1002`, `wall:1003`, `wall:1004`, `wall:1005`, `wall:1006`, `wall:1007`, `wall:1008`, `wall:1009`, `wall:1010`, `wall:1011`, `wall:1012`, `wall:1013`, `wall:1014`, `wall:1015`, `wall:1016`, `wall:1017`, `wall:1018`, `wall:1019`, `wall:1020`, `wall:1021`, `wall:1022`, `wall:1023`, `wall:1024`, `wall:1025`, `wall:1026`, `wall:1027`, `wall:1028`, `wall:1029`, `wall:1030`, `wall:1031`, `wall:1032`, `wall:1033`, `wall:1034`, `wall:1035`, `wall:1036`, `wall:1037`, `wall:1038`, `wall:1039`, `wall:1040` … and 94 more

### `edge_segment` — extra id, 94

`edge:000`, `edge:001`, `edge:002`, `edge:003`, `edge:004`, `edge:005`, `edge:006`, `edge:007`, `edge:008`, `edge:009`, `edge:010`, `edge:011`, `edge:012`, `edge:013`, `edge:014`, `edge:015`, `edge:016`, `edge:017`, `edge:018`, `edge:019`, `edge:020`, `edge:021`, `edge:022`, `edge:023`, `edge:024`, `edge:025`, `edge:026`, `edge:027`, `edge:028`, `edge:029`, `edge:030`, `edge:031`, `edge:032`, `edge:033`, `edge:034`, `edge:035`, `edge:036`, `edge:037`, `edge:038`, `edge:039` … and 54 more

### `condition` — extra id, 54

`condition:000`, `condition:001`, `condition:002`, `condition:003`, `condition:004`, `condition:005`, `condition:006`, `condition:007`, `condition:008`, `condition:009`, `condition:010`, `condition:011`, `condition:012`, `condition:013`, `condition:014`, `condition:015`, `condition:016`, `condition:017`, `condition:018`, `condition:019`, `condition:020`, `condition:021`, `condition:022`, `condition:023`, `condition:024`, `condition:025`, `condition:026`, `condition:027`, `condition:028`, `condition:029`, `condition:030`, `condition:031`, `condition:032`, `condition:033`, `condition:034`, `condition:035`, `condition:036`, `condition:037`, `condition:038`, `condition:039` … and 14 more

### `corridor` — extra id, 33

`corridor:00`, `corridor:01`, `corridor:02`, `corridor:03`, `corridor:04`, `corridor:05`, `corridor:06`, `corridor:07`, `corridor:08`, `corridor:09`, `corridor:10`, `corridor:11`, `corridor:12`, `corridor:13`, `corridor:14`, `corridor:15`, `corridor:16`, `corridor:17`, `corridor:18`, `corridor:19`, `corridor:20`, `corridor:21`, `corridor:22`, `corridor:23`, `corridor:24`, `corridor:25`, `corridor:26`, `corridor:27`, `corridor:28`, `corridor:29`, `corridor:30`, `corridor:31`, `corridor:32`

### `realises` — extra id, 27

`sentence:channel:400:sector:101`, `sentence:channel:400:sprite:0`, `sentence:channel:401:sector:104`, `sentence:channel:401:sprite:2`, `sentence:channel:402:sector:107`, `sentence:channel:402:sprite:4`, `sentence:channel:403:sector:110`, `sentence:channel:403:sprite:6`, `sentence:channel:404:sector:113`, `sentence:channel:404:sprite:8`, `sentence:channel:405:sector:116`, `sentence:channel:405:sprite:10`, `sentence:channel:406:sector:119`, `sentence:channel:406:sprite:11`, `sentence:channel:407:sector:122`, `sentence:channel:407:sprite:12`, `sentence:channel:408:sector:125`, `sentence:channel:408:sprite:13`, `sentence:sector:101:sector:101`, `sentence:sector:104:sector:104`, `sentence:sector:107:sector:107`, `sentence:sector:110:sector:110`, `sentence:sector:113:sector:113`, `sentence:sector:116:sector:116`, `sentence:sector:119:sector:119`, `sentence:sector:122:sector:122`, `sentence:sector:125:sector:125`

### `plan_edge` — extra id, 21

`plan_edge:00`, `plan_edge:01`, `plan_edge:02`, `plan_edge:03`, `plan_edge:04`, `plan_edge:05`, `plan_edge:06`, `plan_edge:07`, `plan_edge:08`, `plan_edge:09`, `plan_edge:10`, `plan_edge:11`, `plan_edge:12`, `plan_edge:13`, `plan_edge:14`, `plan_edge:15`, `plan_edge:16`, `plan_edge:17`, `plan_edge:18`, `plan_edge:19`, `plan_edge:20`

### `candidate` — extra id, 20

`name:assembly:001/space:001`, `name:sentence:sector:101`, `name:sentence:sector:104`, `name:sentence:sector:107`, `name:sentence:sector:110`, `name:sentence:sector:113`, `name:sentence:sector:116`, `name:sentence:sector:119`, `name:sentence:sector:122`, `name:sentence:sector:125`, `plan:corridor:04`, `plan:corridor:05`, `plan:corridor:15`, `plan:corridor:16`, `plan:corridor:19`, `plan:corridor:20`, `plan:corridor:21`, `plan:corridor:22`, `plan:corridor:23`, `plan:corridor:24`

### `sentence` — extra id, 18

`sentence:channel:400`, `sentence:channel:401`, `sentence:channel:402`, `sentence:channel:403`, `sentence:channel:404`, `sentence:channel:405`, `sentence:channel:406`, `sentence:channel:407`, `sentence:channel:408`, `sentence:sector:101`, `sentence:sector:104`, `sentence:sector:107`, `sentence:sector:110`, `sentence:sector:113`, `sentence:sector:116`, `sentence:sector:119`, `sentence:sector:122`, `sentence:sector:125`

### `light_source` — extra id, 15

`sector:34`, `sector:35`, `sector:39`, `sector:42`, `sector:46`, `sector:54`, `sector:58`, `sector:61`, `sector:65`, `sector:73`, `sector:77`, `sector:78`, `sector:82`, `sector:92`, `sector:96`

### `block` — extra id, 10

`block:00`, `block:01`, `block:02`, `block:03`, `block:04`, `block:05`, `block:06`, `block:07`, `block:08`, `block:09`

### `selection` — extra id, 10

`select:plan:corridor:04`, `select:plan:corridor:05`, `select:plan:corridor:15`, `select:plan:corridor:16`, `select:plan:corridor:19`, `select:plan:corridor:20`, `select:plan:corridor:21`, `select:plan:corridor:22`, `select:plan:corridor:23`, `select:plan:corridor:24`

### `link` — extra id, 9

`channel:400`, `channel:401`, `channel:402`, `channel:403`, `channel:404`, `channel:405`, `channel:406`, `channel:407`, `channel:408`

### `island` — extra id, 8

`island:000`, `island:001`, `island:002`, `island:003`, `island:004`, `island:005`, `island:006`, `island:007`

### `key` — extra id, 5

`key:channel:1`, `key:channel:2`, `key:channel:3`, `key:channel:4`, `key:channel:5`

### `sun` — extra id, 1

`sun:0`

### `wall` — extra id, 1077 *(base predicate)*

`wall:0`, `wall:1`, `wall:10`, `wall:100`, `wall:1000`, `wall:1001`, `wall:1002`, `wall:1003`, `wall:1004`, `wall:1005`, `wall:1006`, `wall:1007`, `wall:1008`, `wall:1009`, `wall:101`, `wall:1010`, `wall:1011`, `wall:1012`, `wall:1013`, `wall:1014`, `wall:1015`, `wall:1016`, `wall:1017`, `wall:1018`, `wall:1019`, `wall:102`, `wall:1020`, `wall:1021`, `wall:1022`, `wall:1023`, `wall:1024`, `wall:1025`, `wall:1026`, `wall:1027`, `wall:1028`, `wall:1029`, `wall:103`, `wall:1030`, `wall:1031`, `wall:1032` … and 1037 more

### `connects` — extra id, 420 *(base predicate)*

`sector:0-sector:23`, `sector:0-sector:30`, `sector:0-sector:35`, `sector:0-sector:37`, `sector:1-sector:28`, `sector:1-sector:36`, `sector:1-sector:4`, `sector:1-sector:45`, `sector:10-sector:134`, `sector:10-sector:22`, `sector:10-sector:57`, `sector:10-sector:66`, `sector:10-sector:93`, `sector:100-sector:101`, `sector:102-sector:103`, `sector:102-sector:104`, `sector:103-sector:104`, `sector:105-sector:106`, `sector:105-sector:107`, `sector:106-sector:107`, `sector:108-sector:109`, `sector:108-sector:110`, `sector:109-sector:110`, `sector:11-sector:18`, `sector:11-sector:21`, `sector:11-sector:73`, `sector:11-sector:75`, `sector:111-sector:112`, `sector:111-sector:113`, `sector:112-sector:113`, `sector:114-sector:115`, `sector:114-sector:116`, `sector:115-sector:116`, `sector:117-sector:118`, `sector:117-sector:119`, `sector:118-sector:119`, `sector:12-sector:13`, `sector:12-sector:19`, `sector:12-sector:74`, `sector:12-sector:83` … and 380 more

### `sector` — extra id, 191 *(base predicate)*

`sector:0`, `sector:1`, `sector:10`, `sector:100`, `sector:101`, `sector:102`, `sector:103`, `sector:104`, `sector:105`, `sector:106`, `sector:107`, `sector:108`, `sector:109`, `sector:11`, `sector:110`, `sector:111`, `sector:112`, `sector:113`, `sector:114`, `sector:115`, `sector:116`, `sector:117`, `sector:118`, `sector:119`, `sector:12`, `sector:120`, `sector:121`, `sector:122`, `sector:123`, `sector:124`, `sector:125`, `sector:126`, `sector:127`, `sector:128`, `sector:129`, `sector:13`, `sector:130`, `sector:131`, `sector:132`, `sector:133` … and 151 more

### `sprite` — extra id, 32 *(base predicate)*

`sprite:0`, `sprite:1`, `sprite:10`, `sprite:11`, `sprite:12`, `sprite:13`, `sprite:14`, `sprite:15`, `sprite:16`, `sprite:17`, `sprite:18`, `sprite:19`, `sprite:2`, `sprite:20`, `sprite:21`, `sprite:22`, `sprite:23`, `sprite:24`, `sprite:25`, `sprite:26`, `sprite:27`, `sprite:28`, `sprite:29`, `sprite:3`, `sprite:30`, `sprite:31`, `sprite:4`, `sprite:5`, `sprite:6`, `sprite:7`, `sprite:8`, `sprite:9`

### `xsector` — extra id, 32 *(base predicate)*

`xsector:101`, `xsector:104`, `xsector:107`, `xsector:110`, `xsector:113`, `xsector:116`, `xsector:119`, `xsector:122`, `xsector:125`, `xsector:167`, `xsector:168`, `xsector:169`, `xsector:170`, `xsector:171`, `xsector:172`, `xsector:173`, `xsector:174`, `xsector:175`, `xsector:176`, `xsector:177`, `xsector:178`, `xsector:179`, `xsector:180`, `xsector:181`, `xsector:182`, `xsector:183`, `xsector:184`, `xsector:185`, `xsector:186`, `xsector:187`, `xsector:188`, `xsector:189`

### `xsprite` — extra id, 14 *(base predicate)*

`xsprite:0`, `xsprite:1`, `xsprite:10`, `xsprite:11`, `xsprite:12`, `xsprite:13`, `xsprite:2`, `xsprite:3`, `xsprite:4`, `xsprite:5`, `xsprite:6`, `xsprite:7`, `xsprite:8`, `xsprite:9`

