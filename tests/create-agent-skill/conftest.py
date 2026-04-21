"""Shared pytest fixtures for create-agent-skill."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = REPO_ROOT / ".cursor" / "skills" / "create-agent-skill"
FIXTURES_INTEGRATION = Path(__file__).parent / "integration" / "fixtures"
FIXTURES_E2E = Path(__file__).parent / "e2e" / "fixtures"

if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))


@pytest.fixture(scope="session")
def skill_root() -> Path:
    return SKILL_ROOT


@pytest.fixture(scope="session")
def schemas_dir(skill_root: Path) -> Path:
    return skill_root / "references" / "schemas"


@pytest.fixture(scope="session")
def fixtures_integration() -> Path:
    return FIXTURES_INTEGRATION


@pytest.fixture(scope="session")
def fixtures_e2e() -> Path:
    return FIXTURES_E2E


class FakeAdapter:
    """Deterministic Adapter stand-in for integration tests.

    Replays recorded stream-json transcripts and records which prompts were
    invoked. Implements the full ``Adapter`` Protocol.
    """

    name = "fake"

    def __init__(
        self,
        *,
        transcripts: Optional[List[Dict[str, Any]]] = None,
        trigger_map: Optional[Dict[str, bool]] = None,
        improvement_text: str = "<new_description>Use this skill for tiny tasks.</new_description>",
        allowed_frontmatter_keys: Optional[List[str]] = None,
    ) -> None:
        self.transcripts = list(transcripts or [])
        self._cursor = 0
        self.trigger_map = dict(trigger_map or {})
        self.improvement_text = improvement_text
        self.allowed = set(
            allowed_frontmatter_keys
            or ["name", "description", "license", "metadata", "compatibility"]
        )
        self.invocations: List[dict] = []

    def invoke_subagent(
        self,
        agent_prompt_path: str,
        user_input: str,
        workdir: str,
        timeout_s: int = 600,
        skill_content: Optional[str] = None,
    ) -> dict:
        idx = self._cursor
        self._cursor = min(self._cursor + 1, max(len(self.transcripts) - 1, 0))
        events = (
            self.transcripts[idx]
            if self.transcripts and idx < len(self.transcripts)
            else []
        )
        stdout = "\n".join(json.dumps(e) for e in events)
        wd = Path(workdir)
        wd.mkdir(parents=True, exist_ok=True)
        transcript_path = wd / "transcript.jsonl"
        transcript_path.write_text(stdout + ("\n" if stdout else ""), encoding="utf-8")
        self.invocations.append(
            {
                "agent_prompt_path": agent_prompt_path,
                "user_input": user_input,
                "workdir": workdir,
                "skill_content": skill_content,
            }
        )
        duration = 0
        tokens = None
        for ev in reversed(events):
            if ev.get("type") == "result":
                duration = int(ev.get("duration_ms") or 0)
                u = ev.get("usage") or {}
                if isinstance(u, dict):
                    tokens = {
                        "input": int(u.get("inputTokens", u.get("input_tokens", 0)) or 0),
                        "output": int(u.get("outputTokens", u.get("output_tokens", 0)) or 0),
                    }
                break
        return {
            "stdout": stdout,
            "stderr": "",
            "duration_ms": duration,
            "duration_api_ms": duration,
            "tokens": tokens,
            "exit_code": 0,
            "transcript_path": str(transcript_path),
            "status": "ok",
        }

    def evaluate_trigger(self, skill_description: str, query: str) -> dict:
        return {
            "triggered": bool(self.trigger_map.get(query, False)),
            "raw_response": "YES" if self.trigger_map.get(query, False) else "NO",
        }

    def generate_improved_description(
        self,
        current_description: str,
        failing_queries: list,
        passing_queries: list,
        context: Optional[dict] = None,
    ) -> str:
        self.invocations.append(
            {
                "method": "generate_improved_description",
                "context": context,
                "failing": list(failing_queries),
                "passing": list(passing_queries),
            }
        )
        return self.improvement_text

    def validate_frontmatter(
        self, frontmatter: dict, skill_dir: Optional[str] = None
    ) -> list:
        errs: list = []
        for k in frontmatter.keys():
            if k not in self.allowed:
                errs.append(f"unexpected key {k!r}")
        if skill_dir:
            folder = Path(skill_dir).name
            name = str(frontmatter.get("name", ""))
            if name and folder and name != folder:
                errs.append(f"name {name!r} != folder {folder!r}")
        return errs

    def skill_install_path(self) -> str:
        return ".cursor/skills/"


@pytest.fixture
def fake_adapter() -> FakeAdapter:
    return FakeAdapter()


def write_canonical_run(
    iteration_dir: Path,
    eval_id: str,
    config: str,
    run_number: int,
    expectations: List[Dict],
    *,
    prompt: str = "test prompt",
    skill_name: str = "test-skill",
    time_s: float = 1.0,
    tokens: Optional[int] = None,
) -> Path:
    """Create a spec-compliant run directory with all required artifacts."""
    eval_dir = iteration_dir / eval_id
    eval_dir.mkdir(parents=True, exist_ok=True)

    meta_path = eval_dir / "eval_metadata.json"
    if not meta_path.exists():
        meta_path.write_text(
            json.dumps(
                {
                    "eval_id": eval_id,
                    "skill_name": skill_name,
                    "prompt": prompt,
                    "expectations": [
                        {k: e[k] for k in ("assertion_id", "text", "critical") if k in e}
                        for e in expectations
                    ],
                }
            ),
            encoding="utf-8",
        )

    run_dir = eval_dir / config / f"run-{run_number}"
    (run_dir / "outputs").mkdir(parents=True, exist_ok=True)

    (run_dir / "timing.json").write_text(
        json.dumps(
            {
                "total_duration_seconds": time_s,
                "total_tokens": tokens,
            }
        ),
        encoding="utf-8",
    )

    passed_count = sum(1 for e in expectations if e.get("passed", False))
    total = len(expectations)
    grading_expectations: List[Dict] = []
    for e in expectations:
        row = dict(e)
        if "evidence" not in row:
            row["evidence"] = ""
        grading_expectations.append(row)

    (run_dir / "grading.json").write_text(
        json.dumps(
            {
                "expectations": grading_expectations,
                "summary": {
                    "pass_rate": (passed_count / total) if total else 0.0,
                    "passed": passed_count,
                    "failed": total - passed_count,
                    "total": total,
                },
            }
        ),
        encoding="utf-8",
    )

    return run_dir
