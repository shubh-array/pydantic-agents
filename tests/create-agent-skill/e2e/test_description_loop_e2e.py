"""E2E: trigger evaluation via the real ``agent`` CLI through the adapter."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from _lib.preflight import which_agent


pytestmark = pytest.mark.skipif(which_agent() is None, reason="agent CLI not on PATH")


def test_single_run_eval_via_adapter_cursor(tmp_path: Path) -> None:
    from adapters.cursor.adapter import CursorAdapter

    a = CursorAdapter()
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("Reply with exactly DONE and nothing else.", encoding="utf-8")
    res = a.invoke_subagent(
        agent_prompt_path=str(prompt_path),
        user_input="",
        workdir=str(tmp_path),
        timeout_s=60,
    )
    runs_dir = Path(__file__).parent / "runs" / time.strftime("%Y%m%d-%H%M%S-descloop")
    runs_dir.mkdir(parents=True, exist_ok=True)
    if res.get("transcript_path"):
        (runs_dir / "transcript.jsonl").write_text(
            Path(res["transcript_path"]).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    assert res["status"] in {"ok", "parse_error"}
    assert res["exit_code"] == 0
    assert res["transcript_path"] and Path(res["transcript_path"]).is_file()
