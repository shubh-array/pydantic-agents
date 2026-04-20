"""Claude Code CLI adapter (`claude -p`) — stdlib only."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from adapters.base import SubagentResult, TriggerEvalResult


def load_adapter() -> "ClaudeCodeAdapter":
    return ClaudeCodeAdapter()


def _load_cfg() -> dict:
    return json.loads(Path(__file__).with_name("config.json").read_text(encoding="utf-8"))


def _claude_env() -> dict:
    return {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}


class ClaudeCodeAdapter:
    name = "claude_code"

    def __init__(self) -> None:
        self._cfg = _load_cfg()

    def _run_text(self, prompt: str, timeout_s: int) -> str:
        cli = self._cfg["cli"]
        cmd = [cli["binary"], *cli["flags_text"]]
        proc = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
            env=_claude_env(),
        )
        if proc.returncode != 0:
            raise RuntimeError(f"claude -p failed rc={proc.returncode}: {proc.stderr}")
        return proc.stdout or ""

    def invoke_subagent(
        self,
        agent_prompt_path: str,
        user_input: str,
        workdir: str,
        timeout_s: int = 600,
    ) -> SubagentResult:
        template = Path(agent_prompt_path).read_text(encoding="utf-8")
        prompt = template.replace("{{USER_INPUT}}", user_input)
        try:
            out = self._run_text(prompt, timeout_s=timeout_s)
        except subprocess.TimeoutExpired as exc:
            o = exc.stdout or "" if isinstance(exc.stdout, str) else ""
            e = exc.stderr or "" if isinstance(exc.stderr, str) else ""
            return {
                "stdout": o,
                "stderr": e,
                "duration_ms": 0,
                "duration_api_ms": None,
                "tokens": None,
                "exit_code": 124,
                "transcript_path": None,
                "status": "timeout",
            }
        except RuntimeError as exc:
            return {
                "stdout": "",
                "stderr": str(exc),
                "duration_ms": 0,
                "duration_api_ms": None,
                "tokens": None,
                "exit_code": 1,
                "transcript_path": None,
                "status": "error",
            }
        return {
            "stdout": out,
            "stderr": "",
            "duration_ms": 0,
            "duration_api_ms": None,
            "tokens": None,
            "exit_code": 0,
            "transcript_path": None,
            "status": "ok",
        }

    def evaluate_trigger(self, skill_description: str, query: str) -> TriggerEvalResult:
        prompt = (
            "Answer with exactly YES or NO on the first line.\n"
            f"DESCRIPTION:\n{skill_description}\n\nQUERY:\n{query}\n"
        )
        out = self._run_text(prompt, timeout_s=120)
        line = (out.strip().splitlines()[:1] or [""])[0].upper()
        return {"triggered": line.startswith("YES"), "raw_response": out}

    def generate_improved_description(
        self,
        current_description: str,
        failing_queries: list[str],
        passing_queries: list[str],
    ) -> str:
        fail_lines = "\n".join(f"- {q}" for q in failing_queries)
        pass_lines = "\n".join(f"- {q}" for q in passing_queries)
        prompt = (
            "Return only the improved skill description text.\n\n"
            f"CURRENT:\n{current_description}\n\n"
            f"FAILED_TO_TRIGGER:\n{fail_lines or '(none)'}\n\n"
            f"FALSE_TRIGGERS:\n{pass_lines or '(none)'}\n"
        )
        return self._run_text(prompt, timeout_s=300).strip()

    def validate_frontmatter(self, frontmatter: dict) -> list:
        sk = self._cfg["skills"]
        allowed = set(sk["allowed_frontmatter_keys"]) | set(sk.get("experimental_frontmatter_keys", []))
        errors: list = []
        for key in frontmatter.keys():
            if key not in allowed:
                errors.append(f"Unexpected frontmatter key {key!r}")
        name = str(frontmatter.get("name", ""))
        pattern = sk["name_pattern"]
        max_len = int(sk["name_max_length"])
        if name and not re.match(pattern, name):
            errors.append(f"name {name!r} must match pattern {pattern!r}")
        if len(name) > max_len:
            errors.append(f"name longer than {max_len}")
        return errors

    def skill_install_path(self) -> str:
        return str(self._cfg["skills"]["install_path_user"])
