"""One pool of processes kept for a whole run, and a scene each of them reads once from a file: for tracing that has nothing to share but its scene.

Windows starts a process afresh and copies what it is given down a pipe; a pool
started for every call spent half of the light stage on that (2026-11-24: 94 s
of 180). Here the processes are started once, and a call leaves its scene in a
file, which each process loads when it first meets it. The answers come back in
the order of the jobs, so a result is the same whatever the number of workers.
"""

from __future__ import annotations

import atexit
import os
import pickle
import tempfile
from typing import Any, Callable, Iterable, Sequence

#: processes at once; `LLMAPPER_WORKERS` says fewer where several builds run side by side
WORKERS = int(os.environ.get("LLMAPPER_WORKERS", 0)) or max(1, min(24, (os.cpu_count() or 1) - 2))

_POOL: list[Any] = []
_LOADED: dict[str, Any] = {"token": None, "scene": None}


def started() -> bool:
    return bool(_POOL)


def close() -> None:
    """End the processes; the next call starts them again."""
    while _POOL:
        _POOL.pop().shutdown()


def _work(task: tuple) -> Any:
    token, make, job, chunk = task
    if _LOADED["token"] != token:
        with open(token, "rb") as handle:
            payload = pickle.load(handle)
        _LOADED.update(token=token, scene=make(*payload))
    return job(_LOADED["scene"], chunk)


def spread(make: Callable[..., Any], payload: Sequence[Any], job: Callable[[Any, Any], Any],
           chunks: Iterable[Any]) -> list[Any]:
    """`job(make(*payload), chunk)` for each chunk, in order; `make` runs once in each process."""
    from concurrent.futures import ProcessPoolExecutor
    with tempfile.TemporaryDirectory() as folder:
        token = os.path.join(folder, "scene.pickle")
        with open(token, "wb") as handle:
            pickle.dump(tuple(payload), handle, pickle.HIGHEST_PROTOCOL)
        if not _POOL:
            _POOL.append(ProcessPoolExecutor(WORKERS))
            atexit.register(close)
        return list(_POOL[0].map(_work, ((token, make, job, chunk) for chunk in chunks)))
