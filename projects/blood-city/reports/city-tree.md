# The city as a tree

What `citytree.py` reads out of the built level program. Everything below
is generated -- regenerate with:

```bash
python projects/blood-city/level/citytree.py stats
python projects/blood-city/level/citytree.py zoom theatre_row --depth 4 --cost
```

## Shape

Before this overhaul: **201 nodes, maximum depth 2** -- the root, 38
assemblies at the top level, 162 rooms, nothing below. A district held one
room called `streets` and its venues were its siblings; `theatre_venues`
was 42 sibling rooms in which three venues were told apart by a name
prefix; 28 of the 39 assemblies held exactly one room.

Now:

```json
{
 "nodes": 213,
 "max_depth": 6,
 "depth_histogram": {
  "0": 1,
  "1": 5,
  "2": 27,
  "3": 131,
  "4": 20,
  "5": 11,
  "6": 18
 },
 "assemblies": 43,
 "rooms": 170,
 "singleton_assemblies": 9,
 "top_level": 5
}
```

Top level went from **38 to 5**: four districts and the parked sewer.
Singleton assemblies went from **28 to 9**, and the nine that remain each
hold a real group (a fountain's three tiers, a run's modules) rather than
standing in for one room.

## The city, one level down

```
gravesend  [levelprogram]
    contains {'assembly': 5} | rooms 170 | roles {'exterior': 6, 'detail': 61, 'interior': 58, 'doorway': 13, 'gateway': 30, 'secret': 2}
    states {'ceiling_picnum': 3491, 'clear_height': 196608, 'floor_picnum': 28, 'floor_shade': 32, 'floor_z': 8192, 'parallax_ceiling': True, 'wall_picnum': 380}
    cost 170 sectors 1198 walls 0 sprites
    + theatre_row  [48r 48s 336w 0p]  gas-lit entertainment street; the Aldermack superblo
    + old_crossing  [24r 24s 191w 0p]  the pre-boom quarter: narrow lanes, the well square,
    + foundry_ward  [25r 25s 184w 0p]  the works, the rail spur, the sewer network below
    + market_slip  [47r 47s 343w 0p]  the river gate: quay, plaza, monument; the start
    + sewer  [26r 26s 144w 0p]  the sewer is parked geometry east of the city (Blood
```

## One district, four levels down to a single fixture

`streets` owns the light pools that light it. Each venue owns its spaces;
each space owns its fittings; each fitting run owns its modules. The chain
is `theatre_row -> saloon -> main -> fittings -> main_bar -> main_bar_0`,
which is district, venue, space, template, run, fixture.

```
gravesend/theatre_row  [assembly]
    gas-lit entertainment street; the Aldermack superblock and the venue cluster
    contains {'room': 1, 'assembly': 5} | rooms 48 | roles {'exterior': 1, 'detail': 23, 'interior': 14, 'doorway': 5, 'gateway': 5}
    states {'floor_picnum': 352, 'wall_picnum': 400}
    inherits 5 values, e.g. 3491 <- gravesend
    cost 48 sectors 336 walls 0 sprites
    - streets  [3r 3s 51w 0p]
        - lightpool_avenue_north  [1r 1s 4w 0p]  light pool: avenue_north
        - lightpool_forecourt  [1r 1s 4w 0p]  light pool: forecourt
    + saloon  [11r 11s 73w 0p]  the saloon, on Theatre Row
        - main  [7r 7s 55w 0p]  the saloon: counter and tables are geometry
            + fittings  [6r 6s 24w 0p]  bar fittings (templates.bar)
                + main_bar  [4r 4s 16w 0p]  counter run: DWE3M10 rise-3072/tile-345 family, 8 oc
                - main_table_0  [1r 1s 4w 0p]  a card table (templates.bar)
                - main_table_1  [1r 1s 4w 0p]  a card table (templates.bar)
        - back  [1r 1s 6w 0p]  the saloon's back room
        - passage  [1r 1s 4w 0p]  the saloon's entry passage
        - door  [1r 1s 4w 0p]  the saloon door
        - porch  [1r 1s 4w 0p]  the saloon reveal
    + parlor  [9r 9s 58w 0p]  the shooting parlor, behind a one-bay mouth
        - gallery  [1r 1s 6w 0p]  the parlor's gallery, behind a one-bay mouth
        - range  [5r 5s 40w 0p]  the range: the deep half the mouth does not show
            - furniture_5  [1r 1s 4w 0p]  the firing line
            - furniture_6  [1r 1s 4w 0p]  a target
            - furniture_7  [1r 1s 4w 0p]  a target
            - furniture_8  [1r 1s 4w 0p]  a target
        - passage  [1r 1s 4w 0p]  the parlor's entry passage
        - door  [1r 1s 4w 0p]  the parlor door
        - porch  [1r 1s 4w 0p]  the parlor reveal
    + aldermack  [14r 14s 86w 0p]  the Aldermack: the district's landmark
        - auditorium  [5r 5s 38w 0p]  the auditorium: the house, under the city's tallest 
            - furniture_0  [1r 1s 4w 0p]  the stage, under its proscenium
            - furniture_1  [1r 1s 4w 0p]  the front row
            - furniture_2  [1r 1s 4w 0p]  the middle row
            - furniture_3  [1r 1s 4w 0p]  the back row
        - backstage  [1r 1s 6w 0p]  the backstage corridor
        - dressing  [1r 1s 4w 0p]  the dressing room
        - foyer  [2r 2s 16w 0p]  the foyer, opening on the forecourt
            - furniture_4  [1r 1s 4w 0p]  the box office
        - lobby  [1r 1s 6w 0p]  the avenue lobby: the complex's second front
        - door  [1r 1s 4w 0p]  the aldermack door
        - porch  [1r 1s 4w 0p]  the aldermack reveal
        - lobby_door  [1r 1s 4w 0p]  the lobby door
        - lobby_porch  [1r 1s 4w 0p]  the lobby reveal
    + pawn_shop  [9r 9s 60w 0p]  the pawn shop, open on the avenue
        - shop  [6r 6s 48w 0p]  the pawn shop, open on the avenue
            + fittings  [5r 5s 20w 0p]  shop fittings: shelves and counter (2560 deep, 2048 
                + shop_shelves  [3r 3s 12w 0p]  pedestal run: E6M1 512x512 rise-2048 family, 4 occur
                + shop_counter  [2r 2s 8w 0p]  counter run: DWE3M10 rise-3072/tile-345 family, 8 oc
        - pawn_door  [1r 1s 4w 0p]  the pawn door
        - pawn_porch  [1r 1s 4w 0p]  the pawn reveal
        - pawn_display  [1r 1s 4w 0p]  the pawn display: goods behind glass
    + back_of_house  [2r 2s 8w 0p]  the back-of-house circuit joining the three
        - west  [1r 1s 4w 0p]  the corridor behind the saloon and the parlor
        - east  [1r 1s 4w 0p]  the parlor's way through to the Aldermack's backstag
```

## What it costs

`--cost` measures the compiled artifact and attributes it back up the tree:
`[11r 11s 73w 0p]` is eleven rooms, eleven sectors, 73 walls, no sprites.
The sprite column is zero here because sprites are placed by later passes in
`build_skeleton.main`, not declared in the tree; the wall figure is likewise
the tree's own geometry, before the door reveal frames are inserted.
