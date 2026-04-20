"""E2E: description loop (skipped without agent)."""

from __future__ import annotations

import shutil

import pytest

pytestmark = pytest.mark.skipif(not shutil.which("agent"), reason="agent CLI not on PATH")


def test_stub() -> None:
    assert shutil.which("agent")
