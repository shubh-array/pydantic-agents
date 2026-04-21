"""E2E-specific sys.path wiring.

The tests directory ``tests/create-agent-skill/`` contains a hyphen which
makes standard module imports impossible. We extend sys.path so the
``_lib`` helpers can be imported as ``_lib.preflight`` / ``_lib.run_agent``
without relying on a package alias.
"""

from __future__ import annotations

import sys
from pathlib import Path

E2E_DIR = Path(__file__).resolve().parent
if str(E2E_DIR) not in sys.path:
    sys.path.insert(0, str(E2E_DIR))
