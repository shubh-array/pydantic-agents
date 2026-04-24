"""Marketing domain tools (stub implementations).

Each function is a plain tool (no RunContext needed for stubs).
PydanticAI builds the tool schema from the signature + Google-style docstring.
Real implementations would call APIs; stubs return plausible fake data.
"""

from __future__ import annotations

from pydantic_ai import ModelRetry, RunContext

from deps import AgentDeps


def search_brand_assets(ctx: RunContext[AgentDeps], query: str) -> str:
    """Search the brand asset library for logos, images, and style guides.

    Args:
        query: Natural-language description of the asset needed.
    """
    return (
        f"[brand-assets] Results for '{query}' (company: {ctx.deps.company}):\n"
        "1. Primary logo (SVG) — brand-assets/logos/primary-logo.svg\n"
        "2. Brand color palette — #1A73E8 (primary), #34A853 (secondary)\n"
        "3. Tone-of-voice guide — brand-assets/docs/tone-guide.pdf"
    )


def get_content_calendar(ctx: RunContext[AgentDeps], channel: str) -> str:
    """Retrieve the upcoming content calendar for a given channel.

    Args:
        channel: The marketing channel, e.g. 'LinkedIn', 'Twitter', 'blog'.
    """
    valid_channels = {"linkedin", "twitter", "blog", "email"}
    if channel.lower() not in valid_channels:
        raise ModelRetry(
            f"Unknown channel '{channel}'. Valid channels: {', '.join(sorted(valid_channels))}."
        )
    return (
        f"[content-calendar] Upcoming for {channel} ({ctx.deps.company}):\n"
        "- Mon: Product feature spotlight\n"
        "- Wed: Customer success story\n"
        "- Fri: Industry thought-leadership piece\n"
        "Next open slot: Wednesday"
    )


def check_competitor_claims(claim: str) -> str:
    """Verify a marketing claim against known competitor data.

    Args:
        claim: The factual claim to verify, e.g. '60% faster than CompetitorX'.
    """
    return (
        f"[competitor-check] Claim: '{claim}'\n"
        "Status: UNVERIFIED — no matching data in competitor intelligence DB.\n"
        "Recommendation: Qualify with 'based on internal benchmarks' or cite source."
    )
