"""Protocol smoke tests for Cursor and Claude Code adapters."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from adapters.claude_code.adapter import ClaudeCodeAdapter
from adapters.cursor.adapter import CursorAdapter


@pytest.mark.parametrize("cls", [CursorAdapter, ClaudeCodeAdapter])
def test_adapter_has_protocol_methods(cls) -> None:
    a = cls()
    assert hasattr(a, "invoke_subagent")
    assert hasattr(a, "evaluate_trigger")
    assert hasattr(a, "generate_improved_description")
    assert hasattr(a, "validate_frontmatter")
    assert hasattr(a, "skill_install_path")


def test_cursor_validate_frontmatter_ok() -> None:
    a = CursorAdapter()
    assert a.validate_frontmatter({"name": "foo", "description": "bar"}) == []


def test_cursor_validate_reserved_word() -> None:
    a = CursorAdapter()
    errs = a.validate_frontmatter({"name": "claude-helper", "description": "ok"})
    assert any("Reserved word" in e for e in errs)


@patch("adapters.cursor.adapter.subprocess.run")
def test_cursor_invoke_subagent_parses_result(mock_run: MagicMock) -> None:
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout='{"type":"result","result":{"duration_ms": 42,"duration_api_ms": 40}}\n',
        stderr="",
    )
    a = CursorAdapter()
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write("Hello {{USER_INPUT}}")
        f.flush()
        path = f.name
    try:
        r = a.invoke_subagent(path, "world", ".", timeout_s=30)
        assert r["duration_ms"] == 42
        assert r["status"] == "ok"
    finally:
        Path(path).unlink(missing_ok=True)