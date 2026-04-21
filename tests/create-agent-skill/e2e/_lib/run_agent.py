"""Invoke Cursor CLI ``agent`` with ``stream-json`` (opt-in E2E helper)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import List, Tuple


def run_stream_json(
    prompt: str, cwd: Path, timeout_s: int = 120, binary: str = "agent"
) -> Tuple[int, List[dict], str]:
    cmd = [binary, "--print", "--force", "--output-format=stream-json", prompt]
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    events: List[dict] = []
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return int(proc.returncode), events, proc.stderr or ""


def final_result(events: List[dict]) -> dict:
    for ev in reversed(events):
        if ev.get("type") == "result":
            return ev
    return {}
