from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentDeps:
    """Runtime dependencies shared across all PBA agents.

    Fields are available to instructions, tools, and validators via RunContext[AgentDeps].
    """

    user_name: str
    company: str = "Array Corporation"
    domain: str | None = None
    extra: dict[str, str] = field(default_factory=dict)
