"""Gravesend's own lettering: every sign the city writes is tracked a little wider than the campaign's.

The library writes letters at the campaign's pitch (`bloodmap.lettering.PITCH`,
1.333 drawn widths centre to centre, the median of its 150 evenly spaced
signs). Gravesend's signs went up at 1.45, near the campaign's LINE pitch
rather than its letter pitch, and that is the city's look now: kept as the
level's choice (the owner, 2026-11-26: "keep Gravesend's existing artistic
choices"), not as a fact about Blood.
"""

from __future__ import annotations

from bloodmap import wallplane

#: the city's letter pitch, in drawn widths (the campaign's is 1.333)
TRACKING = 1.45


def text(*args, **kwargs):
    """`bloodmap.wallplane.text` at the city's own pitch, unless the call or its style says otherwise.

    Only across: a word written downward keeps the campaign's column pitch (`wallplane.VERTICAL_PITCH`).
    """
    kwargs.setdefault("tracking", TRACKING)
    return wallplane.text(*args, **kwargs)
