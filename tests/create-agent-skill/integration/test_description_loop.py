"""Description loop wiring (import smoke)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def test_run_loop_importable() -> None:
    repo = Path(__file__).resolve().parents[3]
    skill = repo / ".cursor/skills/create-agent-skill"
    eh = skill / "eval-harness/scripts"
    for p in (skill, eh):
        s = str(p)
        if s not in sys.path:
            sys.path.insert(0, s)
    p = skill / "eval-harness/scripts/run_loop.py"
    spec = importlib.util.spec_from_file_location("run_loop", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    assert hasattr(mod, "run_loop")
