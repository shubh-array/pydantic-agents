"""E2E: create skill (skipped without agent)."""

from __future__ import annotations

import shutil

import pytest

pytestmark = pytest.mark.skipif(not shutil.which("agent"), reason="agent CLI not on PATH")


def test_agent_available() -> None:
    assert shutil.which("agent")
