from __future__ import annotations

from pydantic_ai import Agent

from base_agent import PROMPTS_DIR, _build_agent, compose_prompt
from deps import AgentDeps


def create_marketing_agent(model: str | None = None) -> Agent[AgentDeps, str]:
    """Create the marketing domain agent.

    Composes base-system-prompt.md + marketing-agent-prompt.md into the
    <domain_extension> tag, then loads marketing-agent.yaml for model settings.
    """
    domain_prompt = (PROMPTS_DIR / "marketing-agent-prompt.md").read_text()
    instructions = compose_prompt(domain_prompt)
    return _build_agent(
        "marketing-agent.yaml", instructions, domain="marketing", model=model
    )
