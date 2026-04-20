"""E2E preflight: require `agent` binary on PATH."""

from __future__ import annotations

import shutil
from typing import Optional


def require_agent_binary() -> Optional[str]:
    return shutil.which("agent")
