"""Step 6: Capabilities.

Demonstrates:
- AbstractCapability — the base class for custom capabilities
- AuditLogger — cross-cutting capability that logs model requests and tool calls
- BrandVoiceGuardrail — marketing-specific capability that rejects forbidden phrasings
- Capabilities compose: an agent can have multiple capabilities active simultaneously
- for_run() provides per-run state isolation (fresh log / violations per run)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from base_agent import PROMPTS_DIR, _build_agent, compose_prompt
from capabilities.audit_logger import AuditLogger
from capabilities.brand_voice import BrandVoiceGuardrail
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


def _make_marketing_agent(
    model: str | None = None,
    capabilities: list | None = None,
):
    domain_prompt = (PROMPTS_DIR / "marketing-agent-prompt.md").read_text()
    instructions = compose_prompt(domain_prompt)
    return _build_agent(
        "marketing-agent.yaml",
        instructions,
        domain="marketing",
        model=model,
        output_type=[MarketingDraft, Failed],
        tools=MARKETING_TOOLS,
        capabilities=capabilities,
    )


def _make_operations_agent(
    model: str | None = None,
    capabilities: list | None = None,
):
    domain_prompt = (PROMPTS_DIR / "operations-agent-prompt.md").read_text()
    instructions = compose_prompt(domain_prompt)
    return _build_agent(
        "operations-agent.yaml",
        instructions,
        domain="operations",
        model=model,
        output_type=[IncidentStatus, Failed],
        tools=OPERATIONS_TOOLS,
        capabilities=capabilities,
    )


def demo_audit_logger() -> None:
    """Operations agent with AuditLogger — logs every model request and tool call."""
    audit = AuditLogger()
    agent = _make_operations_agent(capabilities=[audit])
    deps = AgentDeps(user_name="Bob", company="Array Corporation")

    print("Prompt: 'What's the status of the payment service?'\n")
    result = agent.run_sync("What's the status of the payment service?", deps=deps)
    output = result.output

    print(f"\nType: {type(output).__name__}")
    if isinstance(output, IncidentStatus):
        print(f"SEV       : {output.sev}")
        print(f"Status    : {output.status}")
        print(f"Impact    : {output.impact}")
        print(f"Hypothesis: {output.hypothesis}")

    print(f"\nAudit log ({len(audit.log)} entries):")
    for entry in audit.log:
        print(f"  [{entry.event}] {entry.agent_name} — {entry.detail} ({entry.elapsed_ms}ms)")
    print()


def demo_brand_voice_guardrail() -> None:
    """Marketing agent with BrandVoiceGuardrail — rejects forbidden phrasings."""
    guardrail = BrandVoiceGuardrail()
    agent = _make_marketing_agent(capabilities=[guardrail])
    deps = AgentDeps(user_name="Alice", company="Array Corporation")

    prompt = (
        "Draft a short LinkedIn post announcing our new real-time analytics feature. "
        "Keep it under 200 words."
    )
    print(f"Prompt: '{prompt}'\n")
    result = agent.run_sync(prompt, deps=deps)
    output = result.output

    print(f"\nType: {type(output).__name__}")
    if isinstance(output, MarketingDraft):
        print(f"Channel   : {output.channel}")
        print(f"Word count: {output.word_count}")
        print(f"Tone      : {output.tone}")
        print(f"Content   :\n{output.content}")

    if guardrail.violations:
        print(f"\nBrand voice violations caught and retried: {guardrail.violations}")
    else:
        print("\nNo brand voice violations detected.")
    print()


def demo_combined_capabilities() -> None:
    """Marketing agent with both AuditLogger AND BrandVoiceGuardrail composed."""
    audit = AuditLogger()
    guardrail = BrandVoiceGuardrail()
    agent = _make_marketing_agent(capabilities=[audit, guardrail])
    deps = AgentDeps(user_name="Carol", company="Array Corporation")

    prompt = "Draft a tweet about our new data pipeline feature."
    print(f"Prompt: '{prompt}'\n")
    result = agent.run_sync(prompt, deps=deps)
    output = result.output

    print(f"\nType: {type(output).__name__}")
    if isinstance(output, MarketingDraft):
        print(f"Channel   : {output.channel}")
        print(f"Content   : {output.content}")

    print(f"\nAudit log ({len(audit.log)} entries):")
    for entry in audit.log:
        print(f"  [{entry.event}] {entry.detail[:80]}")

    if guardrail.violations:
        print(f"Brand voice violations caught: {guardrail.violations}")
    print()


if __name__ == "__main__":
    print("=== Demo 1: AuditLogger (operations agent) ===")
    demo_audit_logger()

    print("=== Demo 2: BrandVoiceGuardrail (marketing agent) ===")
    demo_brand_voice_guardrail()

    print("=== Demo 3: Combined Capabilities (audit + brand voice) ===")
    demo_combined_capabilities()
