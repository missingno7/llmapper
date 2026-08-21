# One source edit, driven by a structured observation

The loop this is a test of:

```text
structured observation -> design decision -> Python edit -> changed observation
```

## The observation

Twenty-one poses planned from the hierarchy, rendered in 5 ms after a 25 ms
process start. From the lobby entry pose — 1.2 player widths inside the widest
opening, facing the room centre:

| source node | % of frame | depth (PW) |
| --- | --- | --- |
| `nested/manor/lobby` | 82.1 | 4.2 – 14.1 |
| `nested/manor/lobby/recess:lobby_niche` | 6.4 | 7.4 – 10.5 |
| `nested/grounds/porch` | 5.3 | 7.4 – 14.1 |
| `nested/manor/lobby/stairs:grand` | **3.8** | 13.2 – 21.0 |
| `nested/manor/upper_gallery` | **2.6** | 21.0 – 32.9 |

Nothing was occluded; the stair simply is not much of the picture.

## The decision

The grand stair is the reason the lobby exists — it is the only way to the
gallery and to the exit — and walking in did not show it. The stair took six
player widths of a fourteen-wide east face.

Widen it to nine. The gallery has to be at least as deep as the stair that
arrives in it, so it reads the same constant:

```python
STAIR_WIDTH = 9 * U
```

One name, used in two places, in `experiments/nested_authoring.py`. Nothing else
in the file changed — not a coordinate, not a sector, not a wall.

## The changed observation

Re-observed at the **same** pose (`--replay`), because a plan is derived from
geometry and an edit that moves geometry moves the camera too:

| source node | before | after |
| --- | --- | --- |
| `nested/manor/lobby` | 82.1% | 79.2% |
| `nested/manor/lobby/stairs:grand` | 3.8% | **5.6%** |
| `nested/manor/upper_gallery` | 2.6% | **3.7%** |
| `nested/manor/lobby/recess:lobby_niche` | 6.4% | 6.4% |
| `nested/grounds/porch` | 5.3% | 5.3% |

The stair gained 48% of its screen area and the gallery 45%. The two nodes that
have nothing to do with the change are identical to four decimal places, which
is the other half of the result: the edit is local, and the observation says so.

From the foot of the stair the gallery went 13.4% → 19.9%.

All fourteen hard gates still pass, and the detector still recovers the same
structures.

## What it did not fix

5.6% is still not much. The entry pose is 13 to 21 player widths from the stair
and a nine-wide opening at that distance is a small thing on screen no matter
how wide it is. The honest reading is that the lobby is deep enough that the
stair reads as a distant feature, and widening it does not change that — moving
the arrival closer, or raising the gallery into view, would be different edits.
No score is computed and none is implied.

## Reproducing

```bash
mingw32-make -C xmapedit/src_blood/observe
python -m tools.observe program experiments.nested_authoring -o work/obs-nested --structures
# edit STAIR_WIDTH
python -m tools.observe program experiments.nested_authoring \
    -o work/obs-nested-after --replay work/obs-nested/packet.json
```
