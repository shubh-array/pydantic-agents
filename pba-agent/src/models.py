from __future__ import annotations

from pydantic import BaseModel, Field


class Failed(BaseModel):
    """The agent could not fulfil the request."""

    reason: str = Field(description="Why the request could not be completed")


class IncidentStatus(BaseModel):
    """Structured incident status update following SEV format."""

    sev: str = Field(description="Severity level, e.g. SEV-1, SEV-2, SEV-3")
    status: str = Field(description="Current status, e.g. investigating, mitigating, resolved")
    impact: str = Field(description="User-facing impact summary")
    hypothesis: str = Field(description="Current working hypothesis for root cause")
    next_steps: list[str] = Field(description="Ordered list of next actions")
