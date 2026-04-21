"""E2E: adapter parity — both adapters implement identical Protocol shape.

Cheap Protocol parity always runs. Live-CLI parity skips cleanly when any
required binary is absent.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from adapters.claude_code.adapter import ClaudeCodeAdapter
from adapters.cursor.adapter import CursorAdapter
from _lib.preflight import which_agent, which_claude


def test_protocol_parity_cheap() -> None:
    expected = {
        "invoke_subagent",
        "evaluate_trigger",
        "generate_improved_description",
        "validate_frontmatter",
        "skill_install_path",
    }
    for cls in (CursorAdapter, ClaudeCodeAdapter):
        a = cls()
        have = {m for m in expected if callable(getattr(a, m, None))}
        assert have == expected, f"{cls.__name__} missing: {expected - have}"


@pytest.mark.skipif(
    which_agent() is None or which_claude() is None,
    reason="both agent and claude CLIs required for live parity",
)
def test_live_trigger_parity(tmp_path: Path) -> None:
    cursor = CursorAdapter().evaluate_trigger(
        "Use this skill to format Python code.", "format my python file"
    )
    claude = ClaudeCodeAdapter().evaluate_trigger(
        "Use this skill to format Python code.", "format my python file"
    )
    # Parity is measured structurally — both return a bool + raw.
    for out in (cursor, claude):
        assert set(out.keys()) == {"triggered", "raw_response"}
        assert isinstance(out["triggered"], bool)
