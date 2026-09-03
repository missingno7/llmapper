# E4M8, decompiled

`maps/blood/campaign/E4M8.MAP` — an 80-sector fragment with a street — read
back through the same eight layers as [E3M1](../e3m1-decompiled/README.md) and
[E1M2](../e1m2-decompiled/README.md), with **byte-identical stage code**.

**Authority.** `E4M8.MAP` is the truth (CRC `92082c8d`; 80 sectors, 848 walls,
124 sprites). Everything here is derived and reproducible:

```bash
python -m bloodmap decompile maps/blood/campaign/E4M8.MAP -o work/E4M8.level-source.json
```

## Why this map

Because the rule says so, once the rule is applied to a correct curve. "Among
maps with a street network, the largest claimed share under E3M1's readers"
gives **E4M8 at 6.693%**, literally and with layer 2 excluded — no ambiguity,
so no default. The earlier run of the census, which named E1M2, predated the
step-2 reader corrections; item 28c stopped reading a raised outdoor mass with
a sector type as an island, and four maps lost their streets. See
[reports/residue-curve-2026-09-03.md](../../reports/residue-curve-2026-09-03.md).

It is also the third map's real value: it is **unlike** the other two. It has
no stepped run, no water, one island, one road sector, and it names no
mechanism at all. Every assumption the other two share, it tests.

## The numbers

1637 of 24458 claimable fields have a claim (**6.693%**) — the highest of the
three, and the reason the curve's ranking should not be read as understanding:
E4M8 is a dense fragment, so layer 2 claims a large share of a small map.
1059 residue facts. Per layer, and against the other two, in
[reports/sleep-phase-2026-09-03.md](../../reports/sleep-phase-2026-09-03.md).

What it does not have is as useful as what it does:

* **no stepped run**, which is why the proposed `stair` macro clears the
  two-map rule on two maps rather than three;
* **no named mechanism** — all 45 sentences are doors and channels the course
  teaches under file names too varied for a majority, so layer 8 refuses every
  one. The refusal is the reading, and the pack asks the owner to confirm it;
* **no stack, no key, no water**, and 21 XSECTORs against E3M1's 133.

## Layout

Identical to the other two, and produced by the same `source/`.

```bash
BLOODMAP_CORPUS=<absolute path to maps/blood> \
PYTHONPATH=".;projects/e4m8-decompiled/source" \
python projects/e4m8-decompiled/source/run_all.py
```
