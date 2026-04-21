"""E2E: improvement round-trip through the Cursor adapter with real CLI."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from _lib.preflight import which_agent


pytestmark = pytest.mark.skipif(which_agent() is None, reason="agent CLI not on PATH")


def test_evaluate_trigger_returns_bool_on_live_cli(tmp_path: Path) -> None:
    from adapters.cursor.adapter import CursorAdapter

    a = CursorAdapter()
    out = a.evaluate_trigger(
        skill_description="Use this skill to format Python code.",
        query="Please format my python file using black.",
    )
    assert set(out.keys()) == {"triggered", "raw_response"}
    assert isinstance(out["triggered"], bool)
    runs_dir = Path(__file__).parent / "runs" / time.strftime("%Y%m%d-%H%M%S-improve")
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / "raw.txt").write_text(out["raw_response"], encoding="utf-8")
