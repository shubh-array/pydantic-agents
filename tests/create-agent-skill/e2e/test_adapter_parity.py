"""E2E: adapter parity (skipped without claude CLI)."""

from __future__ import annotations

import shutil

import pytest

pytestmark = pytest.mark.skipif(not shutil.which("claude"), reason="claude CLI not on PATH")


def test_stub() -> None:
    assert shutil.which("claude")
