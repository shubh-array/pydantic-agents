"""Step 4: Structured Output.

Demonstrates:
- Pydantic BaseModel as output_type on Agent
- Union output types for success/failure patterns (MarketingDraft | Failed)
- Typed result.output — IDE autocomplete and validation
- output_type passed through the shared _build_agent helper
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from base_agent import PROMPTS_DIR, _build_agent, compose_prompt
from deps import AgentDeps
from models import Failed, IncidentStatus, MarketingDraft


def _make_marketing_agent(model: str | None = None):
    """Marketing agent returning MarketingDraft or Failed."""
    domain_prompt = (PROMPTS_DIR / "marketing-agent-prompt.md").read_text()
    instructions = compose_prompt(domain_prompt)
    return _build_agent(
        "marketing-agent.yaml",
        instructions,
        domain="marketing",
        model=model,
        output_type=[MarketingDraft, Failed],
    )


def _make_operations_agent(model: str | None = None):
    """Operations agent returning IncidentStatus or Failed."""
    domain_prompt = (PROMPTS_DIR / "operations-agent-prompt.md").read_text()
    instructions = compose_prompt(domain_prompt)
    return _build_agent(
        "operations-agent.yaml",
        instructions,
        domain="operations",
        model=model,
        output_type=[IncidentStatus, Failed],
    )


def demo_marketing_structured() -> None:
    """Marketing agent returns a typed MarketingDraft object."""
    agent = _make_marketing_agent()
    deps = AgentDeps(user_name="Alice", company="Array Corporation")

    prompt = (
        "Draft a LinkedIn post announcing our new real-time analytics feature. "
        "It reduces dashboard load time by 60%."
    )
    result = agent.run_sync(prompt, deps=deps)
    output = result.output

    print(f"Type : {type(output).__name__}")
    if isinstance(output, MarketingDraft):
        print(f"Channel   : {output.channel}")
        print(f"Word count: {output.word_count}")
        print(f"Tone      : {output.tone}")
        print(f"Content   :\n{output.content}")
    else:
        print(f"Failed: {output.reason}")
    print()


def demo_operations_structured() -> None:
    """Operations agent returns a typed IncidentStatus object."""
    agent = _make_operations_agent()
    deps = AgentDeps(user_name="Bob", company="Array Corporation")

    prompt = (
        "The payment service is returning 503 errors for about 15% of requests. "
        "Latency spiked 3 minutes ago. Give me a status update."
    )
    result = agent.run_sync(prompt, deps=deps)
    output = result.output

    print(f"Type : {type(output).__name__}")
    if isinstance(output, IncidentStatus):
        print(f"SEV       : {output.sev}")
        print(f"Status    : {output.status}")
        print(f"Impact    : {output.impact}")
        print(f"Hypothesis: {output.hypothesis}")
        print(f"Next steps:")
        for i, step in enumerate(output.next_steps, 1):
            print(f"  {i}. {step}")
    else:
        print(f"Failed: {output.reason}")
    print()


def demo_impossible_request() -> None:
    """An impossible request should return a Failed object."""
    agent = _make_marketing_agent()
    deps = AgentDeps(user_name="Alice", company="Array Corporation")

    prompt = "Draft a marketing campaign for a product that doesn't exist yet and has no name."
    result = agent.run_sync(prompt, deps=deps)
    output = result.output

    print(f"Type : {type(output).__name__}")
    if isinstance(output, Failed):
        print(f"Reason: {output.reason}")
    else:
        print("(Agent attempted the task anyway)")
        print(f"Channel: {output.channel}")
        print(f"Content: {output.content[:100]}...")
    print()


if __name__ == "__main__":
    print("=== Demo 1: Marketing Structured Output (MarketingDraft) ===")
    demo_marketing_structured()

    print("=== Demo 2: Operations Structured Output (IncidentStatus) ===")
    demo_operations_structured()

    print("=== Demo 3: Impossible Request (Failed) ===")
    demo_impossible_request()
