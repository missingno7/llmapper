"""Use the main worktree's headless observer for the moving-body study."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bloodmap import visual
from tools.look_at import main

visual.default_binary = lambda: Path(
    "D:/Games/DOS/llmapper/xmapedit/bin/xmapedit-observe.exe")
raise SystemExit(main())
