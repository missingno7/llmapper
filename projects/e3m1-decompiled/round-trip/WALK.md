# Walk sheet: E3M1, rebuilt from its facts

**The map:** `projects/e3m1-decompiled/round-trip/E3M1.MAP`.
**Start:** the map's own — sector **159** (a pavement on the main street), at
x −16212, y −3807, z −5888, facing 1193. Nothing about the start moved.

Every sector, wall and sprite has the **same index** as in
`maps/blood/campaign/E3M1.MAP`, so any id below is that id in XMapEdit and in
the original. 4298 of 123280 fields were rebuilt from the model (3.5%); the
other 118982 were copied from the original record.

**A difference would look like:** a wall whose texture slides or repeats
differently from its neighbours along the same run; a step in a staircase at
the wrong height; a kerb missing its tile or a facade band starting in the
wrong place; a door that opens to the wrong height; a wall that should shatter
and does not. Anything that looks *identical* to the original tells us
nothing — it may be a copied field. **What matters is anything that looks
wrong.**

---

## 1. The street, and the T that ends it

Walk the main street from the start. The carriageway is sectors **3, 7, 8,
45**; the pavements beside it are **1, 2, 4, 5, 6, 9, 159, 175, 235**. The
kerb between them is 11 wall records, all rebuilt from the
`road|pavement|b_above` row — tile 6, not blocking.

The T ends in **three masses**: sectors **0** and **339** are plain
terminations, and **343** is part of the building (see 2). Their lower band is
rebuilt from the end-wall row.

*Look for:* a kerb tile that is not the kerb the rest of the street wears; a
band that starts at a different height on one of the three ends.

## 2. The one building, and the one shopfront

Sectors **118, 165, 166, 343** are a single mass the reader calls a **facade**:
its top wears tile 379 and the room it opens onto is ceilinged 379, so the
mass is that room's roof. Sector **206** is the **opening** — a floor at the
pavement's own z with the street on one side and room **208** on the other.
Nine wall records across this mass were rebuilt from the facade rows.

*Look for:* the band above the mouth of 206 starting or repeating differently
from the band either side of it. That is the aperture grammar, and it is the
thing this reading is most likely to have got wrong.

## 3. The collapsing house

Sprites **267** and **698** transmit on channel **116**, and **159 records**
answer — sectors **172, 173, 174, 282** and 155 sprites. It is the biggest
single mechanism on the map and the model writes it as **one** sentence.
Two smaller chains: channel **135** (19 records, sector 218) and channel
**109** (15 records).

*Look for:* whether the house still collapses when it should, and whether
anything moves that should not. The four sectors' rebuilt fields are their
two z states (`on_floor_z`, `off_floor_z`, `on_ceiling_z`, `off_ceiling_z`) —
34 doors' worth of them across the map, 136 fields.

## 4. The doors

**34 type-600 sectors**, rebuilt as z-motion sentences: **52, 54, 58, 59, 60,
80, 82, 83, 105, 114, 119, 126, 127, 141, 143, 147, 148, 151, 152, 154, 160,
172, 173, 174, 181, 218, 281, 282, 283, 307, 319, 352, 354, 373, 374**. Each
one's rebuilt fields are the two positions it travels between.

*Look for:* a door that opens to the wrong height, opens the wrong way, or
does not open. A ceiling that lands on the floor, or one that never comes down.

## 5. The eighteen walls that shatter

kWallGib walls **21, 69, 407, 520, 537, 610, 960, 974** and ten more. The
reader claims their `type` and nothing else; layer 8 refuses to NAME them,
because the taught course has no lesson of type 511 at all.

*Look for:* a wall that shatters where none should, or one that will not break.

---

## What comes back

A list, one line each, with the **sector or wall id**. Two kinds:

* **a misreading** — the rebuilt map is wrong where the original is right.
  That is a reader bug and becomes a fail-first test with the id in it.
* **a residue** — both maps look the same and the thing is still not
  understood. That is a name for the ledger, not a bug.

Nothing needs to be right about the walk for it to be useful: "nothing looked
wrong" over five items is itself a reading, and it is the first evidence the
model has ever had that the fields it claims are the fields it thinks.
