from __future__ import annotations

from pydantic_ai import Agent

from base_agent import PROMPTS_DIR, _build_agent, compose_prompt
from deps import AgentDeps


def create_operations_agent(model: str | None = None) -> Agent[AgentDeps, str]:
    """Create the operations domain agent.

    Composes base-system-prompt.md + operations-agent-prompt.md into the
    <domain_extension> tag, then loads operations-agent.yaml for model settings.
    """
    domain_prompt = (PROMPTS_DIR / "operations-agent-prompt.md").read_text()
    instructions = compose_prompt(domain_prompt)
    return _build_agent(
        "operations-agent.yaml", instructions, domain="operations", model=model
    )
