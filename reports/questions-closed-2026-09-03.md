# Every open question in E3M1's review packs, closed

P15, 2026-09-03. The owner's review channel is the walk and the fragment, so the eight per-layer packs stop being owner-facing. Their nineteen questions are answered here -- by a census, by an invariant of the model, or by a decision already taken -- and the three that are about what something LOOKS like become fragments.

Produced by `projects/e3m1-decompiled/source/close_questions.py`; every number is a query over the fact stores and the census references.

| closed by | questions |
| --- | --- |
| invariant | 8 |
| census | 5 |
| already decided | 3 |
| fragment | 3 |

## Layer 1

**Is a singleton space a reading worth keeping in the tree?**  
*node `assembly:001`, closed by invariant*

Yes, and it is not optional. The tree is a PARTITION -- every sector belongs to exactly one space -- so a sector no evidence groups still has to be somewhere, and a singleton is what that costs. The share is stable across three maps from three episodes: E1M2 110 of 313 (35%), E3M1 108 of 382 (28%), E4M8 24 of 80 (30%). A number that steady is a property of the reader, not of the maps, and dropping the singletons would not group one more sector -- it would only stop counting them.

## Layer 2

**One frame per RUN, or per FLAT FACE?**  
*node `surface:0898`, closed by census*

The run. Over the 43 campaign maps a material continues across 93.7% of collinear solid-solid joins, 67.9% of bends and 19.1% of reflex corners. A bend keeps the run two times in three; a face-by-face writer would break it every time. E3M1 is the outlier that made this look undecided, and the campaign is not undecided.

**Is a lone record a SURFACE of one, or evidence the surface model does not fit?**  
*node `level`, closed by invariant*

A surface of one, and that is exactly why it is residue. A surface's claim is that ONE projection reproduces every record in it; over a single record that claim is empty -- it reproduces the record because it was fitted to it. So the reader may call it a surface and may not claim anything from doing so. 2178 such records across three maps (E1M2 862, E3M1 1075, E4M8 241), and the model that would claim them is Surface/Frame, which is the architect's item, not a constructor.

## Layer 3

**Is `TILE_CLASSES['facade stone'] = 400` the campaign's value or Gravesend's own choice?**  
*node `row:road|pavement|b_above`, closed by already decided*

Ours. 400 is worn by 0 of the 179 end-wall band records in the campaign. Decided at item 37b: 400 stays our CHOICE inside the attested class and the campaign distribution is the envelope. The split into `facade` also showed something the single kind hid: 91 leads the buildings, 2490 leads the plain terminations.

**Should a raised outdoor mass that MOVES be an end wall?**  
*node `kind:end_wall`, closed by already decided*

No -- item 28c, landed. It is a mechanism at rest, named apart, and the end-wall row keeps its blocking clause on the records that stay put. The four non-blocking pavement|end_wall records that raised the question all faced sectors 172 and 174, which carry type 600.

**1312 of 1386 records are pairs the table has no row for. A gap to fill, or the table's scope?**  
*node `level`, closed by census*

A gap, and it is filled. Item 37e landed ONE indoor row keyed on the height relation -- not the eleven this project proposed -- and item 32c added `facade` and `opening`. E3M1 now describes 1190 of 1386 records and leaves 196. The 1122 interior|interior residue facts are gone; what remains is a mass meeting a solid and a mechanism at rest meeting anything.

## Layer 4

**E3M1's shadow deltas are 24-26 against the gate's [8, 16]. Is the envelope wrong or is E3M1 outside it?**  
*node `field`, closed by fragment*

Half measured, half not. The envelope is now a census and is decided per network -- [8, 18] on the largest outdoor component, where the median is 13 over 192 boundaries and 36 maps -- so E3M1 is outside the campaign's own envelope and that is recorded rather than repaired. What no census can say is whether 8 -> 32 -> 34 READS as two steps of shadow or one, and that decides whether a writer building to the campaign's step would look like E3M1 or not. Fragment `shade-step`.

**Is the corner test enough to call the shadow casters recovered?**  
*node `islands`, closed by invariant*

No, and the reader already says so. 8 oblique edges have a mass corner up-sun against 8 down-sun: a tie. A test that comes out even has not chosen, and a reader that reported a caster from it would be reporting its own tie-break. The bearing is recovered (479 build units against the cited 478); the casters are not.

## Layer 5

**Is a (type, shape, slot) combination the taught course never shows a finding or a reader artefact?**  
*node `sentence:sector:41`, closed by census*

A finding, and it holds on every map: E1M2 9, E3M1 5, E4M8 4 sentences off the course. Three maps from three episodes each combine slots the course teaches one at a time. The course teaches each slot alone and the campaign combines them; the gap belongs to the curriculum's own list, not to ours.

**Should a chain be one sentence, or one per receiver?**  
*node `sentence:channel:116`, closed by invariant*

One sentence. The channel IS the mechanism and its fan-out is a parameter of it: E3M1's collapsing house is one channel telling 0 records at once, and splitting it would make 0 mechanisms that happen to share a number and cannot be authored, moved or removed as the one thing they are. The fan-out is now also the `channel` macro's whole reason to exist.

**Is the floor marker meant to float 256 below the plane it links?**  
*node `kind:room_over_room`, closed by census*

Yes. 38 of 38 upper markers in the campaign sit at exactly -256, so it is a convention and `curriculum.stack_faults` no longer flags it -- while still flagging any other offset. E3M1 reports 0 stack faults now, and STACKS3DSPACES-BADROR is still caught, which is what keeps the exemption from being a hole.

## Layer 6

**58 of 100 boundary records are one-sided walls against the void. Does a building need a sector behind it?**  
*node `edge:building_back`, closed by invariant*

No, and the count is the evidence. A building's back is a surface, not a space: E3M1 spends no sector behind 58 of its edge records and the player never learns. Requiring a sector would double the map's sector count to model something nothing can enter -- and Blood's limits are the reason the campaign does not. `building_back` is the right name for it.

**`reachability.classify_offmap` raises TypeError on every map, so the enclosure member has no reader. Is it a reader defect?**  
*node `offmap`, closed by invariant*

No -- it was called with the wrong argument. `classify_offmap` takes a DiskMap and section 14 passed it a LevelIR; on a DiskMap it returns its reachability, components, counts and sectors_by_kind for E3M1 without raising. A reader that works and a caller that does not are different findings, and this one closes without a change to either -- the caller in section 14 should pass `read_map(path)`.

**Should a doorway be a member of the edge chain?**  
*node `edge:interior_doorway`, closed by invariant*

Yes, as its own kind, which is what it already is. The chain is what the street SEES, and a way in is part of what the street sees -- it is simply not a termination. Naming it `interior_doorway` keeps the chain closed without pretending a mouth ends anything, and the same argument now covers `gate` (a mechanism at rest) and `opening`.

## Layer 7

**Carriageway or full width -- which is the street's width?**  
*node `streets`, closed by fragment*

Not decidable by counting. Both numbers are real and they land in different classes, so the writer has to pick one to size every street it builds by, and the classes were mined on the full width. A census can say which number the campaign's maps cluster on; it cannot say which one a body feels, and that is what the class is for. Fragment `street-width`.

**The largest block holds 75 sectors -- a block, or a whole side of the city?**  
*node `blocks`, closed by already decided*

A side of the city, and item 30b settled the cut: a block is cut at its street FRONTAGES, so a mass reachable only around the outside of the street is two blocks and not one. E3M1 now recovers 24 blocks with the cut applied. The remaining largest is still large because E3M1's interiors are one connected building -- which is a fact about E3M1.

**Every plan element is a RECT and a sector is not. Is the plan the wrong shape?**  
*node `level`, closed by census*

It is the right shape for a plan and the wrong shape for a boundary, and the numbers say which is which: E3M1's ground fills its own bounding rectangles at a median of 0.882 and a worst of 0.219. A median that high says the plan reads the layout correctly; a worst that low says one place in the map is not a rectangle at all, and the plan names it rather than rounding it off.

## Layer 8

**Is a refusal rate this high the honest answer, or a missing measurement?**  
*node `level`, closed by fragment*

It was a missing measurement and now it is partly answered: the prop reader is wired into layer 8 and E3M1 names 10 places, holds 1 as candidates and still refuses 25. What is left is the question no census reaches -- whether a refused room is a room with no function, or a room whose function is legible to a person and not to a measurement. Fragment `refused-room`.

**Is the curriculum's own file naming a fair source of function names?**  
*node `named:assembly:001/space:008`, closed by invariant*

Yes, with the share reported and a floor under it. The name comes from the prefix of the lesson files teaching that (type, shape), and it is taken only where one prefix holds 60% of them; below that the reader refuses rather than picking. E3M1 names 16 of 129 mechanisms (12.4%), holds 36 as candidates and refuses 77. It is the campaign's own vocabulary rather than ours, which is the only reason to trust it at all.

## The three fragments

Under `projects/e3m1-decompiled/fragments/`, each a small playable map with one line of question and the ORIGINAL sector ids in its sidecar:

* **`shade-step`** — sectors 1, 2, 3, 4, 5, 6, 8, 9, 45, 159, 175, 235, 236: is 8 → 32 → 34 one step of shadow or two?
* **`street-width`** — sectors 1-9 and 45: is the street's width the carriageway or the whole gap between the buildings?
* **`refused-room`** — sectors 206 and 208: what is this room for?

Each answer becomes a fail-first test with the sector id in it, or a residue named in the ledger. Nothing else is asked of the owner.

