"""Step 5: Function Tools.

Demonstrates:
- @agent.tool (with RunContext) and @agent.tool_plain (without)
- Tool schemas auto-generated from function signatures + docstrings
- ModelRetry for tool-level self-correction
- Registering tools via the `tools` constructor argument (for reuse)
- Passing deps to tools via RunContext[AgentDeps]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from base_agent import PROMPTS_DIR, _build_agent, compose_prompt
from deps import AgentDeps
from models import Failed, IncidentStatus, MarketingDraft
from tools.marketing_tools import (
    check_competitor_claims,
    get_content_calendar,
    search_brand_assets,
)
from tools.operations_tools import (
    check_deploy_status,
    query_monitoring,
    search_runbooks,
)

MARKETING_TOOLS = [search_brand_assets, get_content_calendar, check_competitor_claims]
OPERATIONS_TOOLS = [query_monitoring, check_deploy_status, search_runbooks]


def _make_marketing_agent(model: str | None = None):
    """Marketing agent with tools and structured output."""
    domain_prompt = (PROMPTS_DIR / "marketing-agent-prompt.md").read_text()
    instructions = compose_prompt(domain_prompt)
    return _build_agent(
        "marketing-agent.yaml",
        instructions,
        domain="marketing",
        model=model,
        output_type=[MarketingDraft, Failed],
        tools=MARKETING_TOOLS,
    )


def _make_operations_agent(model: str | None = None):
    """Operations agent with tools and structured output."""
    domain_prompt = (PROMPTS_DIR / "operations-agent-prompt.md").read_text()
    instructions = compose_prompt(domain_prompt)
    return _build_agent(
        "operations-agent.yaml",
        instructions,
        domain="operations",
        model=model,
        output_type=[IncidentStatus, Failed],
        tools=OPERATIONS_TOOLS,
    )


def demo_operations_with_tools() -> None:
    """Operations agent calls query_monitoring to build an incident status."""
    agent = _make_operations_agent()
    deps = AgentDeps(user_name="Bob", company="Array Corporation")

    prompt = "What's the status of the payment service?"
    result = agent.run_sync(prompt, deps=deps)
    output = result.output

    print(f"Type: {type(output).__name__}")
    if isinstance(output, IncidentStatus):
        print(f"SEV       : {output.sev}")
        print(f"Status    : {output.status}")
        print(f"Impact    : {output.impact}")
        print(f"Hypothesis: {output.hypothesis}")
        print("Next steps:")
        for i, step in enumerate(output.next_steps, 1):
            print(f"  {i}. {step}")
    else:
        print(f"Failed: {output.reason}")
    print()


def demo_marketing_with_tools() -> None:
    """Marketing agent calls get_content_calendar before drafting a blog post."""
    agent = _make_marketing_agent()
    deps = AgentDeps(user_name="Alice", company="Array Corporation")

    prompt = (
        "Draft a blog post announcing our new real-time analytics feature. "
        "Check the content calendar first to find the right slot."
    )
    result = agent.run_sync(prompt, deps=deps)
    output = result.output

    print(f"Type: {type(output).__name__}")
    if isinstance(output, MarketingDraft):
        print(f"Channel   : {output.channel}")
        print(f"Word count: {output.word_count}")
        print(f"Tone      : {output.tone}")
        print(f"Content   :\n{output.content}")
    else:
        print(f"Failed: {output.reason}")
    print()


def demo_tool_messages() -> None:
    """Show the message exchange to see tool calls in the trace."""
    agent = _make_operations_agent()
    deps = AgentDeps(user_name="Bob", company="Array Corporation")

    result = agent.run_sync("Is there a runbook for high error rates?", deps=deps)

    print("--- Message trace (tool calls) ---")
    for msg in result.all_messages():
        for part in msg.parts:
            kind = type(part).__name__
            if hasattr(part, "tool_name"):
                print(f"  {kind}: {part.tool_name}({getattr(part, 'args', '')})")
            elif hasattr(part, "content"):
                content = str(part.content)
                if len(content) > 120:
                    content = content[:120] + "..."
                print(f"  {kind}: {content}")
    print()


if __name__ == "__main__":
    print("=== Demo 1: Operations Agent with Tools (query_monitoring) ===")
    demo_operations_with_tools()

    print("=== Demo 2: Marketing Agent with Tools (get_content_calendar) ===")
    demo_marketing_with_tools()

    print("=== Demo 3: Message Trace (tool calls visible) ===")
    demo_tool_messages()
