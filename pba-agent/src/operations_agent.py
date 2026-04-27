from __future__ import annotations

from pydantic_ai import Agent

from base_agent import PROMPTS_DIR, _build_agent
from deps import AgentDeps


def create_operations_agent(model: str | None = None) -> Agent[AgentDeps, str]:
    """Create the operations domain agent.

    Reads the pre-rendered prompt at ``prompts/_generated/operations.md``
    directly as the system prompt — bypassing ``compose_prompt()`` because
    the operations prompt is fully assembled at render time from
    ``voice-spec.yaml`` and (eventually) any inlined skills.
    """
    instructions = (PROMPTS_DIR / "_generated" / "operations.md").read_text()
    return _build_agent("operations-agent.yaml", instructions, domain="operations", model=model)
