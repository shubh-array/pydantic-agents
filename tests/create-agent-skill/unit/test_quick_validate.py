"""Phase A gate (quick_validate)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
SKILL = REPO / ".cursor" / "skills" / "create-agent-skill"
QV = SKILL / "scripts" / "quick_validate.py"


def _run_qv(skill_dir: Path) -> tuple[int, str]:
    env = {**os.environ, "PYTHONPATH": str(SKILL)}
    proc = subprocess.run(
        [sys.executable, str(QV), str(skill_dir)],
        cwd=str(SKILL),
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.returncode, proc.stdout + proc.stderr


def test_passes_minimal_valid_when_folder_matches(tmp_path: Path) -> None:
    d = tmp_path / "tiny-skill"
    d.mkdir()
    (d / "SKILL.md").write_text(
        "---\nname: tiny-skill\ndescription: Does one thing well.\n---\n\n# Tiny\n",
        encoding="utf-8",
    )
    code, out = _run_qv(d)
    assert code == 0, out


def test_rejects_bad_name(tmp_path: Path) -> None:
    d = tmp_path / "b"
    d.mkdir()
    (d / "SKILL.md").write_text(
        "---\nname: Bad_Name\ndescription: x\n---\n",
        encoding="utf-8",
    )
    code, _ = _run_qv(d)
    assert code != 0


def test_rejects_folder_name_mismatch(tmp_path: Path) -> None:
    """Spec §4: frontmatter name must match folder basename."""
    d = tmp_path / "some-folder"
    d.mkdir()
    (d / "SKILL.md").write_text(
        "---\nname: different-name\ndescription: x\n---\n",
        encoding="utf-8",
    )
    code, out = _run_qv(d)
    assert code != 0
    assert "folder" in out.lower() or "name" in out.lower()


def test_rejects_reserved_word_cursor(tmp_path: Path) -> None:
    d = tmp_path / "claude-thing"
    d.mkdir()
    (d / "SKILL.md").write_text(
        "---\nname: claude-thing\ndescription: uses claude somehow\n---\n",
        encoding="utf-8",
    )
    code, out = _run_qv(d)
    assert code != 0
    assert "Reserved" in out or "reserved" in out.lower()
