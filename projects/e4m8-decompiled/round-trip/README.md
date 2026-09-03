# The round trip

`E4M8.MAP` here is the original rebuilt from `../facts/`: every field a
`claims` fact names written back from the claim's own value, every other field
copied from the original record, and every sector, wall and sprite index
unchanged. It is what the owner walks; [WALK.md](WALK.md) says where to look.

**The rebuilt map is not committed.** It is byte-identical to
`maps/blood/campaign/E4M8.MAP`, so committing it would redistribute a
commercial map — the rule `maps/` itself is under. One command makes it:

```bash
PYTHONPATH=. python -m tools.round_trip maps/blood/campaign/E4M8.MAP \
    projects/e4m8-decompiled/facts \
    -o projects/e4m8-decompiled/round-trip/E4M8.MAP \
    --report projects/e4m8-decompiled/round-trip/E4M8.md
```

`E4M8.md` and `E4M8.json` ARE committed: they are the measurement, and they
are derived rather than original. What they say:

* **4298 of 123280 fields rebuilt (3.49%)**, 118982 copied;
* **0 misreadings** — every claimed field came back equal to the original;
* byte-identical.

Those two numbers belong in the same sentence. "Byte-identical" alone reads as
"we understand the map"; with "3.49% rebuilt" beside it, it reads as what it
is — the claims are honest about the little they claim.
