"""Claude Code CLI (``claude -p``) adapter — stdlib only.

Uses ``--output-format stream-json`` for ``invoke_subagent`` so we can
capture ``duration_ms``, ``duration_api_ms``, and token usage just like the
Cursor adapter. Text mode is still available via ``flags_text`` for the
short trigger/improvement prompts that do not need transcripts.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, List, Optional, Tuple

from adapters.base import ImprovementContext, SubagentResult, TriggerEvalResult


def load_adapter() -> "ClaudeCodeAdapter":
    return ClaudeCodeAdapter()


def _load_cfg() -> dict:
    return json.loads(
        Path(__file__).with_name("config.json").read_text(encoding="utf-8")
    )


def _claude_env() -> dict:
    """Strip CLAUDECODE so nested invocations work; same pattern as upstream."""
    return {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}


class ClaudeCodeAdapter:
    name = "claude_code"

    def __init__(self) -> None:
        self._cfg = _load_cfg()

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _events(stdout: str) -> List[dict]:
        events: List[dict] = []
        for raw in (stdout or "").splitlines():
            line = raw.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events

    @staticmethod
    def _final_result(events: List[dict]) -> Optional[dict]:
        for ev in reversed(events):
            if ev.get("type") == "result":
                return ev
        return None

    @classmethod
    def _parse_stream(
        cls, stdout: str
    ) -> Tuple[int, Optional[int], Optional[dict], str, str]:
        events = cls._events(stdout)
        final = cls._final_result(events)
        if not final:
            return 0, None, None, "", "parse_error"
        d_ms = int(final.get("duration_ms") or 0)
        api = final.get("duration_api_ms")
        api_i = int(api) if isinstance(api, (int, float)) else None
        usage = final.get("usage")
        tokens: Optional[dict]
        if isinstance(usage, dict):
            tokens = {
                "input": int(
                    usage.get("input_tokens", usage.get("inputTokens", 0)) or 0
                ),
                "output": int(
                    usage.get("output_tokens", usage.get("outputTokens", 0)) or 0
                ),
            }
        else:
            tokens = None
        text = final.get("result")
        if not isinstance(text, str):
            text = ""
            for ev in reversed(events):
                if ev.get("type") == "assistant":
                    msg = ev.get("message") or {}
                    for part in msg.get("content") or []:
                        if isinstance(part, dict) and part.get("type") == "text":
                            text = str(part.get("text") or "")
                            break
                    if text:
                        break
        return d_ms, api_i, tokens, text, "ok"

    @staticmethod
    def _write_transcript(workdir: str, stdout: str) -> Optional[str]:
        try:
            wd = Path(workdir)
            wd.mkdir(parents=True, exist_ok=True)
            path = wd / "transcript.jsonl"
            lines = [ln for ln in (stdout or "").splitlines() if ln.strip()]
            path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
            return str(path)
        except OSError:
            return None

    # -- subprocess wrappers -----------------------------------------------

    def _run_text(self, prompt: str, timeout_s: int) -> Tuple[str, int, str]:
        """Return (stdout, returncode, stderr) for text mode."""
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
        return proc.stdout or "", int(proc.returncode), proc.stderr or ""

    def _run_stream(
        self, prompt: str, workdir: str, timeout_s: int, *, write_transcript: bool
    ) -> Tuple[SubagentResult, str]:
        cli = self._cfg["cli"]
        cmd = [cli["binary"], *cli["flags_stream"]]
        try:
            proc = subprocess.run(
                cmd,
                input=prompt,
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
                env=_claude_env(),
            )
        except subprocess.TimeoutExpired as exc:
            out = exc.stdout if isinstance(exc.stdout, str) else ""
            err = exc.stderr if isinstance(exc.stderr, str) else ""
            res: SubagentResult = {
                "stdout": out or "",
                "stderr": err or "",
                "duration_ms": 0,
                "duration_api_ms": None,
                "tokens": None,
                "exit_code": 124,
                "transcript_path": None,
                "status": "timeout",
            }
            return res, ""

        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        d_ms, d_api, tokens, text, parse_st = self._parse_stream(stdout)
        if proc.returncode != 0:
            final_status = "error"
        elif parse_st == "parse_error":
            final_status = "parse_error"
            d_ms = 0
        else:
            final_status = "ok"
        transcript_path: Optional[str] = None
        if write_transcript:
            transcript_path = self._write_transcript(workdir, stdout)
        res = {
            "stdout": stdout,
            "stderr": stderr,
            "duration_ms": d_ms,
            "duration_api_ms": d_api,
            "tokens": tokens,
            "exit_code": int(proc.returncode),
            "transcript_path": transcript_path,
            "status": final_status,
        }
        return res, text

    # -- Adapter Protocol --------------------------------------------------

    def invoke_subagent(
        self,
        agent_prompt_path: str,
        user_input: str,
        workdir: str,
        timeout_s: int = 600,
        skill_content: Optional[str] = None,
    ) -> SubagentResult:
        template = Path(agent_prompt_path).read_text(encoding="utf-8")
        prompt = template.replace("{{USER_INPUT}}", user_input)
        prompt = prompt.replace("{{SKILL_CONTENT}}", skill_content or "")
        res, _ = self._run_stream(prompt, workdir, timeout_s, write_transcript=True)
        return res

    def evaluate_trigger(
        self, skill_description: str, query: str
    ) -> TriggerEvalResult:
        prompt = (
            "Answer with exactly YES or NO on the first line, nothing before it.\n"
            "YES if a skill matching the description should be invoked for the query.\n\n"
            f"DESCRIPTION:\n{skill_description}\n\nQUERY:\n{query}\n"
        )
        stdout, rc, stderr = self._run_text(prompt, timeout_s=120)
        line = (stdout.strip().splitlines()[:1] or [""])[0].strip().upper()
        return {"triggered": line.startswith("YES"), "raw_response": stdout}

    def generate_improved_description(
        self,
        current_description: str,
        failing_queries: list,
        passing_queries: list,
        context: Optional[ImprovementContext] = None,
    ) -> str:
        ctx = context or {}
        skill_name = ctx.get("skill_name") or ""
        skill_content = ctx.get("skill_content") or ""
        history = ctx.get("history") or []
        train = ctx.get("train_summary") or {}
        test = ctx.get("test_summary")
        fail_lines = "\n".join(f'  - "{q}"' for q in failing_queries) or "  (none)"
        pass_lines = "\n".join(f'  - "{q}"' for q in passing_queries) or "  (none)"
        scores = ""
        if train:
            scores = f"Train: {train.get('passed', 0)}/{train.get('total', 0)}"
            if test:
                scores += f", Test: {test.get('passed', 0)}/{test.get('total', 0)}"
        history_block = ""
        if history:
            history_block += "\nPREVIOUS ATTEMPTS:\n"
            for h in history[-5:]:
                tp = h.get("train_passed", h.get("passed", 0))
                tt = h.get("train_total", h.get("total", 0))
                history_block += f'- "{h.get("description", "")}" (train={tp}/{tt})\n'
        prompt = (
            f'You are optimizing the description of a Claude Code skill named "{skill_name}".\n'
            "The description appears in Claude's available_skills list and drives invocation.\n\n"
            f"<current_description>\n{current_description}\n</current_description>\n\n"
            f"<scores>{scores}</scores>\n\n"
            f"FAILED TO TRIGGER:\n{fail_lines}\n\n"
            f"FALSE TRIGGERS:\n{pass_lines}\n"
            f"{history_block}\n"
            "<skill_content>\n"
            f"{skill_content[:4000]}\n"
            "</skill_content>\n\n"
            "Respond with only the new description inside <new_description></new_description> tags."
        )
        stdout, rc, stderr = self._run_text(prompt, timeout_s=300)
        return stdout.strip()

    def validate_frontmatter(
        self, frontmatter: dict, skill_dir: Optional[str] = None
    ) -> list:
        sk = self._cfg["skills"]
        allowed = set(sk["allowed_frontmatter_keys"]) | set(
            sk.get("experimental_frontmatter_keys", [])
        )
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
        if skill_dir:
            folder = Path(skill_dir).resolve().name
            if name and folder and name != folder:
                errors.append(
                    f"frontmatter name {name!r} must match folder name {folder!r}"
                )
        return errors

    def skill_install_path(self) -> str:
        return str(self._cfg["skills"]["install_path_user"])
