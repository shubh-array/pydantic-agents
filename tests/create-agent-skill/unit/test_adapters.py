"""Protocol compliance + behavioral unit tests for both adapters."""

from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import List, Optional
from unittest.mock import MagicMock, patch

import pytest

from adapters.base import Adapter
from adapters.claude_code.adapter import ClaudeCodeAdapter
from adapters.cursor.adapter import CursorAdapter

REPO = Path(__file__).resolve().parents[3]
SKILL_ROOT = REPO / ".cursor" / "skills" / "create-agent-skill"
EH_SCRIPTS = SKILL_ROOT / "eval-harness" / "scripts"


def _adapter_protocol_members() -> set[str]:
    """Public methods plus ``name`` as defined on :class:`Adapter`."""
    members: set[str] = set()
    for key, value in Adapter.__dict__.items():
        if key.startswith("_"):
            continue
        if callable(value):
            members.add(key)
    members.update(getattr(Adapter, "__annotations__", {}))
    return members


def _load_run_eval():
    spec = importlib.util.spec_from_file_location(
        "run_eval_adapter_boundary", EH_SCRIPTS / "run_eval.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


class StubAdapter:
    """Minimal adapter living outside ``adapters/`` — proves core uses only the protocol."""

    name = "stub-unit"

    def __init__(self) -> None:
        self.invocations: list[dict] = []

    def invoke_subagent(
        self,
        agent_prompt_path: str,
        user_input: str,
        workdir: str,
        timeout_s: int = 600,
        skill_content: Optional[str] = None,
    ) -> dict:
        wd = Path(workdir)
        wd.mkdir(parents=True, exist_ok=True)
        transcript_path = wd / "transcript.jsonl"
        line = json.dumps(
            {"type": "result", "duration_ms": 1, "usage": {"inputTokens": 0, "outputTokens": 0}}
        )
        transcript_path.write_text(line + "\n", encoding="utf-8")
        self.invocations.append(
            {
                "agent_prompt_path": agent_prompt_path,
                "user_input": user_input,
                "workdir": workdir,
                "skill_content": skill_content,
            }
        )
        return {
            "stdout": line + "\n",
            "stderr": "",
            "duration_ms": 1,
            "duration_api_ms": 1,
            "tokens": {"input": 0, "output": 0},
            "exit_code": 0,
            "transcript_path": str(transcript_path),
            "status": "ok",
        }

    def evaluate_trigger(self, skill_description: str, query: str) -> dict:
        return {"triggered": False, "raw_response": "NO"}

    def generate_improved_description(
        self,
        current_description: str,
        failing_queries: List[str],
        passing_queries: List[str],
        context: Optional[dict] = None,
    ) -> str:
        return "<new_description>x</new_description>"

    def validate_frontmatter(
        self, frontmatter: dict, skill_dir: Optional[str] = None
    ) -> List[str]:
        return []

    def skill_install_path(self) -> str:
        return ".cursor/skills/"


@pytest.mark.parametrize("cls", [CursorAdapter, ClaudeCodeAdapter])
def test_adapter_has_all_protocol_methods(cls) -> None:
    expected = _adapter_protocol_members()
    a = cls()
    for m in expected:
        if m == "name":
            assert getattr(a, "name", None), f"{cls.__name__} missing name"
        else:
            assert hasattr(a, m), f"{cls.__name__} missing {m}"


def test_cmd_dual_runs_with_out_of_tree_stub_adapter(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Core ``run_eval.cmd_dual`` must work when ``get_active_adapter`` returns a non-package adapter."""
    stub = StubAdapter()
    run_eval = _load_run_eval()
    monkeypatch.setattr(run_eval, "get_active_adapter", lambda: stub)

    skill_dir = tmp_path / "boundary-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: boundary-skill\ndescription: test\n---\n\n# B\n",
        encoding="utf-8",
    )
    evals_path = tmp_path / "evals.json"
    evals_path.write_text(
        json.dumps(
            [
                {
                    "id": "e1",
                    "prompt": "p",
                    "expectations": [{"assertion_id": "a1", "text": "t", "critical": True}],
                }
            ]
        ),
        encoding="utf-8",
    )
    iteration_dir = tmp_path / "iteration-1"
    iteration_dir.mkdir()
    agent_prompt = SKILL_ROOT / "agents" / "analyzer.md"
    (iteration_dir / "iteration.json").write_text(
        json.dumps(
            {
                "skill_path": str(skill_dir.resolve()),
                "evals_path": str(evals_path.resolve()),
                "agent_prompt": str(agent_prompt.resolve()),
                "runs_per_configuration": 1,
            }
        ),
        encoding="utf-8",
    )

    args = argparse.Namespace(
        iteration=1,
        workspace=tmp_path,
        skill_path=skill_dir,
        evals=evals_path,
        agent_prompt=agent_prompt,
        timeout=30,
    )
    run_eval.cmd_dual(args)

    assert stub.invocations, "stub adapter invoke_subagent was not called"
    timing = iteration_dir / "e1" / "with_skill" / "run-1" / "timing.json"
    assert timing.is_file()
    assert json.loads(timing.read_text(encoding="utf-8"))["status"] == "ok"


@pytest.mark.parametrize("cls", [CursorAdapter, ClaudeCodeAdapter])
def test_validate_frontmatter_folder_match(cls, tmp_path: Path) -> None:
    d = tmp_path / "my-skill"
    d.mkdir()
    a = cls()
    assert a.validate_frontmatter({"name": "my-skill", "description": "ok"}, skill_dir=str(d)) == []
    errs = a.validate_frontmatter({"name": "other", "description": "ok"}, skill_dir=str(d))
    assert any("folder" in e.lower() for e in errs)


def test_cursor_validate_reserved_word() -> None:
    a = CursorAdapter()
    errs = a.validate_frontmatter({"name": "claude-helper", "description": "ok"})
    assert any("Reserved word" in e for e in errs)


def test_cursor_allows_minimal_valid() -> None:
    a = CursorAdapter()
    assert a.validate_frontmatter({"name": "tiny", "description": "bar"}) == []


@patch("adapters.cursor.adapter.subprocess.run")
def test_cursor_invoke_parses_top_level_result(mock_run: MagicMock, tmp_path: Path) -> None:
    events = [
        {"type": "system", "subtype": "init"},
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "OK"}]}},
        {
            "type": "result",
            "subtype": "success",
            "duration_ms": 42,
            "duration_api_ms": 40,
            "result": "OK",
            "usage": {"inputTokens": 10, "outputTokens": 5},
        },
    ]
    stdout = "\n".join(json.dumps(e) for e in events) + "\n"
    mock_run.return_value = MagicMock(returncode=0, stdout=stdout, stderr="")
    a = CursorAdapter()
    pf = tmp_path / "prompt.md"
    pf.write_text("Hello {{USER_INPUT}}", encoding="utf-8")
    r = a.invoke_subagent(str(pf), "world", str(tmp_path), timeout_s=30)
    assert r["duration_ms"] == 42
    assert r["duration_api_ms"] == 40
    assert r["tokens"] == {"input": 10, "output": 5}
    assert r["status"] == "ok"
    assert r["transcript_path"] and Path(r["transcript_path"]).is_file()


@patch("adapters.cursor.adapter.subprocess.run")
def test_cursor_evaluate_trigger_reads_assistant_text(mock_run: MagicMock) -> None:
    # First line is the system init event — the old bug read THIS and always
    # returned False. The fix extracts the top-level result.result field.
    events = [
        {"type": "system", "subtype": "init"},
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "YES"}]}},
        {"type": "result", "subtype": "success", "duration_ms": 100, "result": "YES"},
    ]
    stdout = "\n".join(json.dumps(e) for e in events) + "\n"
    mock_run.return_value = MagicMock(returncode=0, stdout=stdout, stderr="")
    a = CursorAdapter()
    out = a.evaluate_trigger("desc", "q")
    assert out["triggered"] is True
    assert "YES" in out["raw_response"]


@patch("adapters.cursor.adapter.subprocess.run")
def test_cursor_evaluate_trigger_no(mock_run: MagicMock) -> None:
    events = [
        {"type": "system", "subtype": "init"},
        {"type": "result", "subtype": "success", "duration_ms": 100, "result": "NO"},
    ]
    stdout = "\n".join(json.dumps(e) for e in events) + "\n"
    mock_run.return_value = MagicMock(returncode=0, stdout=stdout, stderr="")
    a = CursorAdapter()
    assert a.evaluate_trigger("desc", "q")["triggered"] is False


@patch("adapters.cursor.adapter.subprocess.run")
def test_cursor_parse_error_when_no_result(mock_run: MagicMock, tmp_path: Path) -> None:
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout='{"type":"system","subtype":"init"}\n',
        stderr="",
    )
    a = CursorAdapter()
    pf = tmp_path / "p.md"
    pf.write_text("x", encoding="utf-8")
    r = a.invoke_subagent(str(pf), "y", str(tmp_path), timeout_s=30)
    assert r["status"] == "parse_error"
    assert r["duration_ms"] == 0


@patch("adapters.cursor.adapter.subprocess.run")
def test_cursor_timeout_surfaces(mock_run: MagicMock, tmp_path: Path) -> None:
    import subprocess as sp

    mock_run.side_effect = sp.TimeoutExpired(cmd="agent", timeout=1)
    a = CursorAdapter()
    pf = tmp_path / "p.md"
    pf.write_text("x", encoding="utf-8")
    r = a.invoke_subagent(str(pf), "y", str(tmp_path), timeout_s=1)
    assert r["status"] == "timeout"
    assert r["exit_code"] == 124


@patch("adapters.claude_code.adapter.subprocess.run")
def test_claude_invoke_uses_stream_flags(mock_run: MagicMock, tmp_path: Path) -> None:
    events = [
        {"type": "system", "subtype": "init"},
        {
            "type": "result",
            "subtype": "success",
            "duration_ms": 77,
            "result": "done",
            "usage": {"input_tokens": 3, "output_tokens": 4},
        },
    ]
    stdout = "\n".join(json.dumps(e) for e in events) + "\n"
    mock_run.return_value = MagicMock(returncode=0, stdout=stdout, stderr="")
    a = ClaudeCodeAdapter()
    pf = tmp_path / "p.md"
    pf.write_text("hi {{USER_INPUT}}", encoding="utf-8")
    r = a.invoke_subagent(str(pf), "there", str(tmp_path), timeout_s=30)
    # flags_stream should be used for invoke_subagent (not flags_text).
    args, kwargs = mock_run.call_args
    cmd = args[0]
    assert "stream-json" in " ".join(cmd)
    assert r["duration_ms"] == 77
    assert r["tokens"] == {"input": 3, "output": 4}
    assert r["status"] == "ok"
