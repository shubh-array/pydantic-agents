"""Typed adapter protocol for agent-specific integrations.

Python 3.9-compatible. Adapters MUST implement every method; the resolver
checks ``name`` at load time.
"""

from __future__ import annotations

from typing import Any, List, Optional, Protocol, TypedDict


class SubagentResult(TypedDict):
    stdout: str
    stderr: str
    duration_ms: int
    duration_api_ms: Optional[int]
    tokens: Optional[dict]  # {"input": int, "output": int, ...} or None
    exit_code: int
    transcript_path: Optional[str]
    status: str  # "ok" | "timeout" | "parse_error" | "error"


class TriggerEvalResult(TypedDict):
    triggered: bool
    raw_response: str


class ImprovementContext(TypedDict, total=False):
    """Rich context for ``generate_improved_description`` (optional fields).

    Passed by the core ``improve_description`` script so adapters can
    reproduce the upstream `skill-creator` prompt quality while remaining
    agent-agnostic. All fields are optional; minimal adapters may ignore them.
    """

    skill_name: str
    skill_content: str
    history: List[dict]
    train_summary: dict
    test_summary: Optional[dict]
    failing_queries: List[dict]
    false_trigger_queries: List[dict]


class Adapter(Protocol):
    """Agent-specific plug.

    Implementations must provide ``name`` and every method below. ``name`` must
    match the package directory under ``adapters/`` so ``get_active_adapter`` in
    ``adapters`` can verify identity. Core scripts must depend only on this
    protocol (via ``from adapters import get_active_adapter``), not on concrete
    adapter modules.
    """

    name: str

    def invoke_subagent(
        self,
        agent_prompt_path: str,
        user_input: str,
        workdir: str,
        timeout_s: int = 600,
        skill_content: Optional[str] = None,
    ) -> SubagentResult:
        """Invoke the underlying agent CLI against an agent-prompt template.

        The template may contain two placeholders:

        * ``{{USER_INPUT}}`` — replaced with ``user_input``.
        * ``{{SKILL_CONTENT}}`` — replaced with ``skill_content``; the empty
          string when ``skill_content`` is ``None`` or ``""``. This is what
          enforces the with_skill vs without_skill isolation: the harness
          passes the candidate SKILL.md for ``with_skill``, the old snapshot
          for ``old_skill``, and ``None`` for ``without_skill``.
        """
        ...

    def evaluate_trigger(
        self, skill_description: str, query: str
    ) -> TriggerEvalResult: ...

    def generate_improved_description(
        self,
        current_description: str,
        failing_queries: List[str],
        passing_queries: List[str],
        context: Optional[ImprovementContext] = None,
    ) -> str: ...

    def validate_frontmatter(
        self,
        frontmatter: dict,
        skill_dir: Optional[str] = None,
    ) -> List[str]:
        """Return list of error messages. Empty list = valid.

        If ``skill_dir`` is provided, adapters SHOULD also assert that
        ``frontmatter["name"]`` matches the folder basename (spec §4).
        """
        ...

    def skill_install_path(self) -> str: ...
