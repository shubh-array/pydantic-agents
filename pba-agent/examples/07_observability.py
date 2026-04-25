"""Step 7: Observability + Docker Infrastructure.

Demonstrates:
- Logfire SDK with local Jaeger backend (no cloud account needed)
- logfire.configure(send_to_logfire=False) + logfire.instrument_pydantic_ai()
- Full tracing of agent runs: messages, tool calls, token usage, latency
- capture_run_messages() for programmatic message inspection

Prerequisites — pick ONE way to start Jaeger (from pba-agent/ directory):

    Option A  (standalone binary, no Docker):
        ./scripts/start-jaeger.sh

    Option B  (Docker Compose):
        docker compose up -d

Then run this example:
    env $(cat .env) uv run python examples/07_observability.py

Open http://localhost:16686 to view traces in the Jaeger UI.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pydantic_ai import capture_run_messages

from base_agent import PROMPTS_DIR, _build_agent, compose_prompt
from deps import AgentDeps
from models import Failed, IncidentStatus
from observability import configure_tracing
from tools.operations_tools import check_deploy_status, query_monitoring, search_runbooks

OPERATIONS_TOOLS = [query_monitoring, check_deploy_status, search_runbooks]

configure_tracing(service_name="pba-agent-tutorial")


def _make_operations_agent(model: str | None = None):
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


def demo_traced_run() -> None:
    """Run an operations agent — the full run is traced to Jaeger."""
    agent = _make_operations_agent()
    deps = AgentDeps(user_name="Bob", company="Array Corporation")

    print("Prompt: 'What's the status of the payment service?'\n")
    result = agent.run_sync("What's the status of the payment service?", deps=deps)
    output = result.output

    print(f"Type: {type(output).__name__}")
    if isinstance(output, IncidentStatus):
        print(f"SEV       : {output.sev}")
        print(f"Status    : {output.status}")
        print(f"Impact    : {output.impact}")
        print(f"Hypothesis: {output.hypothesis}")
    elif isinstance(output, Failed):
        print(f"Failed    : {output.reason}")

    print(f"\nToken usage: {result.usage()}")


def demo_capture_messages() -> None:
    """Use capture_run_messages() for programmatic message inspection."""
    agent = _make_operations_agent()
    deps = AgentDeps(user_name="Bob", company="Array Corporation")

    with capture_run_messages() as messages:
        agent.run_sync("Is there a runbook for high error rates?", deps=deps)

    print(f"Captured {len(messages)} messages:\n")
    for msg in messages:
        kind = type(msg).__name__
        n_parts = len(msg.parts)
        print(f"  {kind} ({n_parts} part{'s' if n_parts != 1 else ''})")
        for part in msg.parts:
            part_kind = type(part).__name__
            if hasattr(part, "tool_name"):
                print(f"    └─ {part_kind}: {part.tool_name}")
            elif hasattr(part, "content"):
                content = str(part.content)[:100]
                print(f"    └─ {part_kind}: {content}")


if __name__ == "__main__":
    print("=== Demo 1: Traced Agent Run ===\n")
    demo_traced_run()

    print("\n=== Demo 2: capture_run_messages() ===\n")
    demo_capture_messages()

    print(
        "\n--- View traces at http://localhost:16686 ---\n"
        "Select service 'pba-agent-tutorial' to see agent runs, tool calls, and timing.\n"
    )
