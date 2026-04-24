from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.agent.spec import AgentSpec

from deps import AgentDeps

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
SPECS_DIR = Path(__file__).resolve().parent.parent / "specs"

_DOMAIN_PLACEHOLDER = (
    "<domain_extension>\n"
    "<!-- assembled at runtime; empty when no domain is specialized -->\n"
    "</domain_extension>"
)


def compose_prompt(domain_prompt: str | None = None) -> str:
    """Build the full instructions string from base prompt + optional domain content.

    Reads base-system-prompt.md and inserts ``domain_prompt`` between the
    ``<domain_extension>`` tags.  When *domain_prompt* is None the tags
    stay empty (generalist mode).
    """
    base_prompt = (PROMPTS_DIR / "base-system-prompt.md").read_text()
    if domain_prompt is None:
        return base_prompt
    filled = f"<domain_extension>\n{domain_prompt}\n</domain_extension>"
    return base_prompt.replace(_DOMAIN_PLACEHOLDER, filled)


def _build_agent(
    spec_name: str,
    instructions: str,
    domain: str | None = None,
    model: str | None = None,
    output_type: Any = str,
) -> Agent[AgentDeps, Any]:
    """Shared builder: load a YAML spec, attach instructions + user-context hook."""
    spec = AgentSpec.from_file(SPECS_DIR / spec_name)

    kwargs: dict = dict(deps_type=AgentDeps, instructions=instructions, output_type=output_type)
    if model is not None:
        kwargs["model"] = model

    agent: Agent[AgentDeps, Any] = Agent.from_spec(spec, **kwargs)

    @agent.instructions
    def inject_user_context(ctx: RunContext[AgentDeps]) -> str:
        parts = [f"Current user: {ctx.deps.user_name}"]
        if ctx.deps.company:
            parts.append(f"Company: {ctx.deps.company}")
        active = domain or ctx.deps.domain
        if active:
            parts.append(f"Active domain: {active}")
        return "\n".join(parts)

    return agent


def create_base_agent(model: str | None = None) -> Agent[AgentDeps, str]:
    """Create the base PBA agent (generalist, no domain extension)."""
    return _build_agent("base-agent.yaml", compose_prompt(), model=model)
