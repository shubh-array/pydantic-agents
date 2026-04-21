"""E2E preflight: probe optional agent binaries.

No API-key check — binaries are assumed already authenticated on the host.
"""

from __future__ import annotations

import shutil
from typing import Optional


def which_agent() -> Optional[str]:
    return shutil.which("agent") or shutil.which("cursor-agent")


def which_claude() -> Optional[str]:
    return shutil.which("claude")
