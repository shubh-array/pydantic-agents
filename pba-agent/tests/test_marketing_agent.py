from __future__ import annotations

from pydantic_ai import capture_run_messages
from pydantic_ai.models.test import TestModel

from base_agent import compose_prompt, PROMPTS_DIR
from deps import AgentDeps
from marketing_agent import create_marketing_agent


def test_create_marketing_agent():
    agent = create_marketing_agent()
    assert agent is not None


def test_marketing_agent_run():
    agent = create_marketing_agent()
    deps = AgentDeps(user_name="TestUser", company="TestCo")
    with agent.override(model=TestModel()):
        result = agent.run_sync("Draft a LinkedIn post about our product", deps=deps)
    assert isinstance(result.output, str)
    assert len(result.output) > 0


def test_marketing_prompt_contains_domain():
    domain_prompt = (PROMPTS_DIR / "marketing-agent-prompt.md").read_text()
    composed = compose_prompt(domain_prompt)
    assert "<domain_extension>" in composed
    assert "marketing" in composed.lower() or "brand" in composed.lower()


def test_marketing_agent_captures_messages():
    agent = create_marketing_agent()
    deps = AgentDeps(user_name="Alice", company="Acme Corp")
    with capture_run_messages() as messages:
        with agent.override(model=TestModel()):
            agent.run_sync("Write a tweet", deps=deps)
    assert len(messages) >= 2
