"""Typed adapter protocol for agent-specific integrations."""

from __future__ import annotations

from typing import Optional, Protocol, TypedDict


class SubagentResult(TypedDict):
    stdout: str
    stderr: str
    duration_ms: int
    duration_api_ms: Optional[int]
    tokens: Optional[dict]
    exit_code: int
    transcript_path: Optional[str]
    status: str


class TriggerEvalResult(TypedDict):
    triggered: bool
    raw_response: str


class Adapter(Protocol):
    name: str

    def invoke_subagent(
        self,
        agent_prompt_path: str,
        user_input: str,
        workdir: str,
        timeout_s: int = 600,
    ) -> SubagentResult: ...

    def evaluate_trigger(self, skill_description: str, query: str) -> TriggerEvalResult: ...

    def generate_improved_description(
        self,
        current_description: str,
        failing_queries: list[str],
        passing_queries: list[str],
    ) -> str: ...

    def validate_frontmatter(self, frontmatter: dict) -> list[str]: ...

    def skill_install_path(self) -> str: ...
