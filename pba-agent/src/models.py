from __future__ import annotations

from pydantic import BaseModel, Field


class Failed(BaseModel):
    """The agent could not fulfil the request."""

    reason: str = Field(description="Why the request could not be completed")


class MarketingDraft(BaseModel):
    """A marketing content draft for a specific channel."""

    channel: str = Field(description="Target channel, e.g. LinkedIn, Twitter, blog")
    content: str = Field(description="The draft copy")
    word_count: int = Field(description="Word count of the content field")
    tone: str = Field(description="Tone used, e.g. professional, casual, inspirational")


class IncidentStatus(BaseModel):
    """Structured incident status update following SEV format."""

    sev: str = Field(description="Severity level, e.g. SEV-1, SEV-2, SEV-3")
    status: str = Field(description="Current status, e.g. investigating, mitigating, resolved")
    impact: str = Field(description="User-facing impact summary")
    hypothesis: str = Field(description="Current working hypothesis for root cause")
    next_steps: list[str] = Field(description="Ordered list of next actions")
