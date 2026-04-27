from __future__ import annotations

from pydantic_ai import capture_run_messages
from pydantic_ai.models.test import TestModel

from base_agent import compose_prompt, create_base_agent
from deps import AgentDeps


def test_create_base_agent():
    agent = create_base_agent()
    assert agent is not None


def test_base_agent_run():
    agent = create_base_agent()
    deps = AgentDeps(user_name="TestUser", company="TestCo")
    with agent.override(model=TestModel()):
        result = agent.run_sync("Hello", deps=deps)
    assert isinstance(result.output, str)
    assert len(result.output) > 0


def test_base_agent_captures_messages():
    agent = create_base_agent()
    deps = AgentDeps(user_name="TestUser")
    with capture_run_messages() as messages:
        with agent.override(model=TestModel()):
            agent.run_sync("What is 2+2?", deps=deps)
    assert len(messages) >= 2


def test_compose_prompt_no_domain():
    prompt = compose_prompt()
    assert "<domain_extension>" in prompt
    assert "<!-- domain-extension:begin -->" in prompt


def test_compose_prompt_with_domain():
    prompt = compose_prompt("Custom domain content here")
    assert "Custom domain content here" in prompt
    assert "<!-- domain-extension:begin -->" not in prompt
