"""Cursor CLI (`agent`) adapter — stdlib only."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Optional

from adapters.base import SubagentResult, TriggerEvalResult


def load_adapter() -> "CursorAdapter":
    return CursorAdapter()


def _load_cfg() -> dict:
    return json.loads(Path(__file__).with_name("config.json").read_text(encoding="utf-8"))


class CursorAdapter:
    name = "cursor"

    def __init__(self) -> None:
        self._cfg = _load_cfg()

    def _argv(self, prompt: str) -> list:
        cli = self._cfg["cli"]
        return [cli["binary"], *cli["flags"], prompt]

    def _parse_result_line(self, stdout: str) -> tuple:
        last_obj: Optional[dict] = None
        for raw in stdout.splitlines():
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("type") == "result":
                last_obj = obj
        if not last_obj:
            return 0, None, "parse_error"
        payload = last_obj.get("result")
        if not isinstance(payload, dict):
            payload = last_obj
        d_ms = int(payload.get("duration_ms") or 0)
        api_ms = payload.get("duration_api_ms")
        api_i = int(api_ms) if api_ms is not None else None
        return d_ms, api_i, "ok"

    def _run(self, prompt: str, workdir: str, timeout_s: int) -> SubagentResult:
        argv = self._argv(prompt)
        try:
            proc = subprocess.run(
                argv,
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            out = exc.stdout or "" if isinstance(exc.stdout, str) else ""
            err = exc.stderr or "" if isinstance(exc.stderr, str) else ""
            return {
                "stdout": out,
                "stderr": err,
                "duration_ms": 0,
                "duration_api_ms": None,
                "tokens": None,
                "exit_code": 124,
                "transcript_path": None,
                "status": "timeout",
            }

        duration_ms, duration_api_ms, parse_st = self._parse_result_line(proc.stdout or "")
        if proc.returncode != 0:
            final_status = "error"
        else:
            final_status = "parse_error" if parse_st == "parse_error" else "ok"
        if final_status == "parse_error":
            duration_ms = 0
        return {
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "duration_ms": duration_ms,
            "duration_api_ms": duration_api_ms,
            "tokens": None,
            "exit_code": int(proc.returncode),
            "transcript_path": None,
            "status": final_status,
        }

    def invoke_subagent(
        self,
        agent_prompt_path: str,
        user_input: str,
        workdir: str,
        timeout_s: int = 600,
    ) -> SubagentResult:
        template = Path(agent_prompt_path).read_text(encoding="utf-8")
        prompt = template.replace("{{USER_INPUT}}", user_input)
        return self._run(prompt, workdir, timeout_s)

    def evaluate_trigger(self, skill_description: str, query: str) -> TriggerEvalResult:
        prompt = (
            "Answer with exactly YES or NO on the first line, nothing else before it.\n"
            "YES if a skill with the given description should be triggered for the user query.\n\n"
            f"DESCRIPTION:\n{skill_description}\n\nQUERY:\n{query}\n"
        )
        res = self._run(prompt, workdir=str(Path.cwd().resolve()), timeout_s=120)
        first = (res["stdout"] or "").strip().splitlines()[:1]
        line = first[0].upper() if first else ""
        triggered = line.startswith("YES")
        return {"triggered": triggered, "raw_response": res["stdout"]}

    def generate_improved_description(
        self,
        current_description: str,
        failing_queries: list[str],
        passing_queries: list[str],
    ) -> str:
        fail_lines = "\n".join(f"- {q}" for q in failing_queries)
        pass_lines = "\n".join(f"- {q}" for q in passing_queries)
        prompt = (
            "Return only the improved skill description text on a single line or short paragraph.\n"
            "No preamble.\n\n"
            f"CURRENT:\n{current_description}\n\n"
            f"SHOULD_TRIGGER_BUT_FAILED:\n{fail_lines or '(none)'}\n\n"
            f"SHOULD_NOT_TRIGGER:\n{pass_lines or '(none)'}\n"
        )
        res = self._run(prompt, workdir=str(Path.cwd().resolve()), timeout_s=300)
        return (res["stdout"] or "").strip()

    def validate_frontmatter(self, frontmatter: dict) -> list:
        sk = self._cfg["skills"]
        allowed = set(sk["allowed_frontmatter_keys"]) | set(sk.get("experimental_frontmatter_keys", []))
        errors: list = []
        for key in frontmatter.keys():
            if key not in allowed:
                errors.append(f"Unexpected frontmatter key {key!r}; allowed={sorted(allowed)}")
        name = str(frontmatter.get("name", ""))
        desc = str(frontmatter.get("description", ""))
        for w in sk["reserved_words"]:
            if w.lower() in name.lower() or w.lower() in desc.lower():
                errors.append(f"Reserved word {w!r} must not appear in name/description")
        pattern = sk["name_pattern"]
        max_len = int(sk["name_max_length"])
        if name and not re.match(pattern, name):
            errors.append(f"name {name!r} must match pattern {pattern!r}")
        if len(name) > max_len:
            errors.append(f"name longer than {max_len}")
        return errors

    def skill_install_path(self) -> str:
        return str(self._cfg["skills"]["install_path_project"])
