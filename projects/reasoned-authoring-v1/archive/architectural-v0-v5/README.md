# Frozen architectural pilot v0-v5

These are the six historical source/MAP pairs recovered from revision
`b0e0f3b8749391add4f65354f9d54949f109bfcd`. On 2026-09-09, all six were
compiled using that revision's `bloodmap` package and matched their MAPs byte
for byte. See `rebuild-check.json`. Today's compiler is not the historical compiler.

`manifest.json` binds source, MAP, existing packet, review, and captured images
by SHA-256. Run `python -m tools.check_authoring_archive` from the repository root.
This check needs no commercial game assets. Packets retain their original absolute
MAP paths; the manifest selects the recovered MAP bytes instead.

There are 73 bound image files and one unavailable capture: v5 `view:chapel_apse`
is failed in the packet. An adjacent older PNG is not evidence for that capture.
The legacy comparison table's 18/18 claim is inconsistent with its packet.

The historical runtime label is `rlocal-agtst10`; its binary was not recovered.
Hash preservation and exact recompilation do not prove playability or quality.
The live level directory remains later working material, including expanded v5-v7.
New evaluations use separate run directories and never inherit these reviews.
