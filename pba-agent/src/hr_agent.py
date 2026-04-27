from __future__ import annotations

from pydantic_ai import Agent

from base_agent import PROMPTS_DIR, _build_agent
from deps import AgentDeps


def create_hr_agent(model: str | None = None) -> Agent[AgentDeps, str]:
    """Create the HR domain agent.

    Reads the pre-rendered prompt at ``prompts/_generated/hr.md`` directly
    as the system prompt — bypassing ``compose_prompt()`` because the HR
    prompt is fully assembled at render time from ``voice-spec.yaml`` and
    the inlined skills.
    """
    instructions = (PROMPTS_DIR / "_generated" / "hr.md").read_text()
    return _build_agent("hr-agent.yaml", instructions, domain="hr", model=model)
