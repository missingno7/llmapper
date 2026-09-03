# Fragments

Three small playable maps, each cut from E3M1 with one line of question. They
exist for the questions a census cannot answer because they are about what
something LOOKS like; every other open question in this project's review packs
was closed by measurement — see
[reports/questions-closed-2026-09-03.md](../../../reports/questions-closed-2026-09-03.md).

| fragment | question | sectors in E3M1 |
| --- | --- | --- |
| `shade-step` | Is 8 → 32 → 34 one step of shadow, or two? | 1-9, 45, 159, 175, 235, 236 |
| `street-width` | Is the street's width the carriageway, or the whole gap between the buildings? | 1-9, 45 |
| `refused-room` | What is this room for? | 206, 208 |

Each `.md` carries the question, the reasoning and the ORIGINAL sector ids, so
an answer that names a sector lands where it means something in the whole map.
Each `.json` carries the index mapping both ways.

**The `.MAP` files are not committed**: they carry E3M1's geometry verbatim.
Each is one command:

```bash
PYTHONPATH=. python -m tools.fragment_map maps/blood/campaign/E3M1.MAP -s 3 7 8 45 1 2 4 5 6 9 -o projects/e3m1-decompiled/fragments/street-width.MAP --question "..."
```

The exact arguments for all three are in `regenerate.sh` beside this file.
