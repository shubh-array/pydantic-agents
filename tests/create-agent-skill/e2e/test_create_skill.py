"""E2E: Phase A quick_validate over a freshly-written tiny skill."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from _lib.preflight import which_agent  # noqa: F401


REPO = Path(__file__).resolve().parents[3]
SKILL = REPO / ".cursor" / "skills" / "create-agent-skill"


def test_quick_validate_accepts_newly_authored_skill(tmp_path: Path) -> None:
    """Structural gate: no agent invocation needed — verifies the gate itself."""
    d = tmp_path / "e2e-tiny"
    d.mkdir()
    (d / "SKILL.md").write_text(
        "---\nname: e2e-tiny\ndescription: Use this skill to run e2e deterministic gates.\n---\n\n# e2e-tiny\n",
        encoding="utf-8",
    )
    env = {**os.environ, "PYTHONPATH": str(SKILL)}
    proc = subprocess.run(
        [sys.executable, str(SKILL / "scripts/quick_validate.py"), str(d)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.mark.skipif(which_agent() is None, reason="agent CLI not on PATH")
def test_agent_smoke_invocation_returns_result_event(tmp_path: Path) -> None:
    """Preserves full stream-json transcript on failure for debugging."""
    from _lib.run_agent import run_stream_json, final_result

    runs_dir = Path(__file__).parent / "runs" / time.strftime("%Y%m%d-%H%M%S-create")
    runs_dir.mkdir(parents=True, exist_ok=True)
    rc, events, stderr = run_stream_json("Reply with exactly OK.", cwd=tmp_path, timeout_s=60)
    (runs_dir / "events.jsonl").write_text(
        "\n".join(__import__("json").dumps(e) for e in events), encoding="utf-8"
    )
    assert rc == 0, stderr
    final = final_result(events)
    assert final, "no result event in stream"
    assert "duration_ms" in final
