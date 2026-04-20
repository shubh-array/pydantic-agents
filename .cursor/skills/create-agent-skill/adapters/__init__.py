"""Adapter resolution for create-agent-skill."""

from __future__ import annotations

import importlib
import os
from pathlib import Path

from adapters.base import Adapter

_SKILL_ROOT = Path(__file__).resolve().parents[1]


def get_active_adapter() -> Adapter:
    """Resolve active adapter from AGENT_SKILL_ADAPTER env then config/active_agent."""
    override = os.environ.get("AGENT_SKILL_ADAPTER", "").strip()
    if override:
        name = override
    else:
        token = (_SKILL_ROOT / "config" / "active_agent").read_text(encoding="utf-8").strip()
        if not token:
            raise RuntimeError("config/active_agent is empty")
        name = token
    module = importlib.import_module(f"adapters.{name}.adapter")
    load = getattr(module, "load_adapter")
    adapter = load()
    if getattr(adapter, "name", None) != name:
        raise RuntimeError(
            f"adapter.name mismatch: expected {name!r} got {getattr(adapter, 'name', None)!r}"
        )
    return adapter
