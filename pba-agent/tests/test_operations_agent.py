from __future__ import annotations

from pydantic_ai import capture_run_messages
from pydantic_ai.models.test import TestModel

from base_agent import PROMPTS_DIR
from deps import AgentDeps
from operations_agent import create_operations_agent


def test_create_operations_agent():
    agent = create_operations_agent()
    assert agent is not None


def test_operations_agent_run():
    agent = create_operations_agent()
    deps = AgentDeps(user_name="TestUser", company="TestCo")
    with agent.override(model=TestModel()):
        result = agent.run_sync("Check the payment service status", deps=deps)
    assert isinstance(result.output, str)
    assert len(result.output) > 0


def test_operations_generated_prompt_contains_domain():
    rendered = (PROMPTS_DIR / "_generated" / "operations.md").read_text()
    assert "<domain_extension>" in rendered
    assert "operations" in rendered.lower() or "incident" in rendered.lower()


def test_operations_agent_captures_messages():
    agent = create_operations_agent()
    deps = AgentDeps(user_name="Bob", company="Array Corp")
    with capture_run_messages() as messages:
        with agent.override(model=TestModel()):
            agent.run_sync("Is the API healthy?", deps=deps)
    assert len(messages) >= 2
