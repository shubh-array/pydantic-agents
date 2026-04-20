"""Phase A quick_validate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SKILL = REPO / ".cursor" / "skills" / "create-agent-skill"
QV = SKILL / "scripts" / "quick_validate.py"


def _run_qv(skill_dir: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(QV), str(skill_dir)],
        cwd=str(SKILL),
        capture_output=True,
        text=True,
        env={**dict(**__import__("os").environ), "PYTHONPATH": str(SKILL)},
    )
    return proc.returncode, proc.stdout + proc.stderr


def test_quick_validate_passes_minimal_skill(tmp_path: Path) -> None:
    d = tmp_path / "s"
    d.mkdir()
    (d / "SKILL.md").write_text(
        "---\nname: tiny-skill\ndescription: Does one thing well.\n---\n\n# Tiny\n",
        encoding="utf-8",
    )
    code, out = _run_qv(d)
    assert code == 0, out


def test_quick_validate_rejects_bad_name(tmp_path: Path) -> None:
    d = tmp_path / "b"
    d.mkdir()
    (d / "SKILL.md").write_text(
        "---\nname: Bad_Name\ndescription: x\n---\n",
        encoding="utf-8",
    )
    code, out = _run_qv(d)
    assert code != 0
