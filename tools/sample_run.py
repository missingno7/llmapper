"""Run a script and sample where its main thread is, fifty times a second: where a slow build spends its time.

    python -m tools.sample_run OUT.txt projects/blood-city/level/build_skeleton.py [args]
"""
import collections
import os
import runpy
import sys
import threading
import time

if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"):
    print(__doc__)
    raise SystemExit(0 if sys.argv[1:2] in (["-h"], ["--help"]) else 2)
out, script, *args = sys.argv[1:]
sys.argv = [script, *args]
sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
main = threading.main_thread().ident
self_time, total, stacks = collections.Counter(), collections.Counter(), collections.Counter()
n, stop = [0], threading.Event()
t0 = time.perf_counter()


def name(frame):
    c = frame.f_code
    return f"{os.path.relpath(c.co_filename) if c.co_filename[:2] == os.getcwd()[:2] else c.co_filename}:{c.co_name}"


def run():
    while not stop.is_set():
        f = sys._current_frames().get(main)
        if f is not None:
            n[0] += 1
            self_time[name(f)] += 1
            seen, chain = set(), []
            while f is not None:
                k = name(f)
                if k not in seen:
                    seen.add(k)
                    total[k] += 1
                if f.f_code.co_filename.startswith(os.getcwd()) and 'sample_run' not in f.f_code.co_filename:
                    chain.append(f"{os.path.basename(f.f_code.co_filename)}:{f.f_lineno}:{f.f_code.co_name}")
                f = f.f_back
            stacks[' < '.join(chain[:6])] += 1
        time.sleep(0.02)


th = threading.Thread(target=run, daemon=True)
th.start()
try:
    runpy.run_path(script, run_name='__main__')
except SystemExit:
    pass
finally:
    stop.set()
    secs = time.perf_counter() - t0
    with open(out, 'w', encoding='utf8') as fh:
        s = secs / max(1, n[0])
        print(f"{secs:.0f} s, {n[0]} samples", file=fh)
        for title, c, k in (("TOTAL", total, 70), ("SELF", self_time, 30), ("STACKS", stacks, 30)):
            print("==", title, file=fh)
            for key, v in c.most_common(k):
                print(f"{v * s:7.1f}  {key}", file=fh)
