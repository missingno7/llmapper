"""Shop windows: the city's call into the promoted glass constructor.

The recipe, the E6M1 reading and the NBlood citation all moved to
`bloodmap.glass` -- a constructor only one project can call is not a
promotion, and the zoo's conformance rule says a public constructor owes an
exhibit, which this could not have while it lived in a level.

What stays here is the city's own use of it: which spans are windows. The
behaviour is unchanged, and `glaze` is re-exported so no call site moves.
"""

from __future__ import annotations

from bloodmap.glass import (                                # noqa: F401
    GLASS_CSTAT, GLASS_REPEATS, GLASS_TILE, GLASS_XWALL, GlassError,
    attach_xwall, breaks_to, glaze, holder, pane_faults,
)
