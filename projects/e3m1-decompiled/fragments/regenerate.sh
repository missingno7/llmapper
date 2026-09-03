#!/bin/sh
# The three fragments, exactly as they were cut. Run from the repository root
# with BLOODMAP_CORPUS pointing at maps/blood.
#
# The .MAP files are not committed: they carry E3M1's geometry verbatim and
# the project never redistributes an original map. This script is what is
# committed instead, so the owner's fragments are reproducible byte for byte.
set -e
MAP="${1:-maps/blood/campaign/E3M1.MAP}"
OUT="projects/e3m1-decompiled/fragments"

PYTHONPATH=. python -m tools.fragment_map "$MAP" \
    -s 1 5 8 9 3 7 45 236 2 4 6 159 175 235 \
    -o "$OUT/shade-step.MAP" \
    --question "Walking from sector 8 to sector 3 to sector 2, is that ONE step of shadow getting deeper, or two?" \
    --why "The reader recovers a light field of base + k*step. E3M1's own deltas are 8 -> 32 -> 34: one jump of 24 and one of 2. The campaign's median step is 13 (192 boundaries over 36 maps, quartiles [9, 18.75]), so the gate reads 24 as two steps and the writer would build it as two. No census can say what the eye does with 24 against 2 -- only looking can."

PYTHONPATH=. python -m tools.fragment_map "$MAP" \
    -s 3 7 8 45 1 2 4 5 6 9 \
    -o "$OUT/street-width.MAP" \
    --question "Standing in the middle: is this street's width the CARRIAGEWAY you walk on, or the whole gap between the buildings?" \
    --why "read_plan measures both and they land in different classes: E3M1's main street is 7.28 pu of carriageway (an avenue) and 10.78 pu including its pavements (a boulevard). The writer has to pick one to build to, and the classes were mined from the campaign on the full width. A census cannot say which number a body feels; the answer decides which width every street we author is sized by."

PYTHONPATH=. python -m tools.fragment_map "$MAP" \
    -s 208 206 \
    -o "$OUT/refused-room.MAP" \
    --question "What is this room for? Any word will do -- and 'nothing, it is just a room' is an answer." \
    --why "Layer 8 refuses to name 25 of E3M1's 36 grouped spaces: no measurement distinguishes them. The prop reader is now wired in and named 11 of them by their furniture. Sector 208 is one of the refusals, reached through the shopfront 206 -- the map's only opening. If the owner can name it and say from what, that is a measurement the reader does not have yet; if the owner cannot either, the refusal rate is the honest answer and stops being an open question."
