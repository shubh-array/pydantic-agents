#!/usr/bin/env python3
"""
Run a live ``agent -p`` probe and validate hook analytics output.

Stdlib only. Exits non-zero if required E2E checks are missing.
Writes:
- ``tests/hook_matrix/out/e2e_analytics.jsonl``
- ``tests/hook_matrix/out/live_e2e_report.json``
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parents]:
        hooks = p / ".cursor" / "hooks"
        if (hooks / "before_shell_gate.py").is_file():
            return p
    raise RuntimeError(
        "could not locate workspace root (missing .cursor/hooks/before_shell_gate.py)"
    )


def _parse_jsonl(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _summarize_session_row(rec: dict[str, Any]) -> dict[str, Any]:
    return {
        "script_id": rec.get("script_id"),
        "session_id": rec.get("session_id"),
        "conversation_id": rec.get("conversation_id"),
        "event_type": rec.get("event_type"),
    }


def _summarize_shell_deny(rec: dict[str, Any]) -> dict[str, Any]:
    return {
        "script_id": rec.get("script_id"),
        "event_type": rec.get("event_type"),
        "policy_outcome": rec.get("policy_outcome"),
        "deny_reason": rec.get("deny_reason"),
        "command_sample": rec.get("command_sample"),
        "command_class": rec.get("command_class"),
    }


def main() -> int:
    repo = _repo_root()
    sys.path.insert(0, str(repo / ".cursor" / "hooks"))
    from lib.audit import ANALYTICS_JSONL_ENV_VAR, utc_iso_z_now  # noqa: E402

    out_dir = Path(__file__).resolve().parent / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "live_e2e_report.json"
    e2e_analytics_path = out_dir / "e2e_analytics.jsonl"

    report: dict[str, Any] = {
        "generated_at": utc_iso_z_now(),
        "workspace": str(repo),
        "e2e": {},
        "overall_ok": False,
    }

    agent_bin = shutil.which("agent")
    if not agent_bin:
        report["e2e"] = {
            "error": "agent CLI not found on PATH",
            "e2e_analytics_jsonl": str(e2e_analytics_path),
        }
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"overall_ok": False, "report": str(report_path)}, indent=2))
        return 1

    prompt = (
        "Use the run_terminal_cmd tool exactly twice in order: first `echo E2E_HOOK_LIVE_TAG`, "
        "second attempt `rm -rf /tmp/e2e_cursor_hook_probe`. "
        "Reply with one short line describing whether the second command was blocked."
    )
    agent_cmd = [agent_bin, "-p", "--trust", "--workspace", str(repo), prompt]

    _AGENT_TIMEOUT_S = 180
    e2e_analytics_path.unlink(missing_ok=True)
    agent_env = os.environ.copy()
    agent_env[ANALYTICS_JSONL_ENV_VAR] = str(e2e_analytics_path)

    try:
        ag = subprocess.run(
            agent_cmd,
            cwd=str(repo),
            env=agent_env,
            text=True,
            capture_output=True,
            check=False,
            timeout=_AGENT_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as e:
        checks_fail = {
            "session_start": False,
            "session_end": False,
            "shell_deny_with_deny_reason": False,
        }
        report["e2e"] = {
            "e2e_analytics_jsonl": str(e2e_analytics_path),
            "agent_timeout": True,
            "timeout_seconds": e.timeout,
            "error": "agent subprocess timed out",
            "agent_command": agent_cmd,
            "agent_partial_stdout": ((e.stdout or "")[-4000:] if isinstance(e.stdout, str) else ""),
            "agent_partial_stderr": ((e.stderr or "")[-4000:] if isinstance(e.stderr, str) else ""),
            "checks": checks_fail,
            "extracted": {
                "session_start": None,
                "session_end": None,
                "shell_deny": None,
            },
        }
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"report written: {report_path}")
        print(f"overall_ok=False e2e_ok=False agent_timeout=True timeout_seconds={e.timeout!r}")
        return 1

    full_text = e2e_analytics_path.read_text(encoding="utf-8") if e2e_analytics_path.is_file() else ""
    e2e_recs = _parse_jsonl(full_text)

    session_start: dict[str, Any] | None = None
    session_end: dict[str, Any] | None = None
    shell_deny: dict[str, Any] | None = None
    for rec in e2e_recs:
        sid = rec.get("script_id")
        if sid == "session_audit:start" and session_start is None:
            session_start = rec
        if sid == "session_audit:end":
            session_end = rec
        if sid == "before_shell":
            dr = rec.get("deny_reason")
            if rec.get("policy_outcome") == "deny" and isinstance(dr, str) and dr.strip():
                shell_deny = rec

    checks = {
        "session_start": session_start is not None,
        "session_end": session_end is not None,
        "shell_deny_with_deny_reason": shell_deny is not None,
    }
    e2e_ok = all(checks.values())
    id_counts = Counter(str(r.get("script_id")) for r in e2e_recs)

    report["e2e"] = {
        "e2e_analytics_jsonl": str(e2e_analytics_path),
        "e2e_record_count": len(e2e_recs),
        "e2e_script_id_counts": dict(sorted(id_counts.items())),
        "agent_timeout": False,
        "agent": {
            "command": agent_cmd,
            "exit_code": ag.returncode,
            "stdout": (ag.stdout or "")[-4000:],
            "stderr": (ag.stderr or "")[-4000:],
        },
        "checks": checks,
        "extracted": {
            "session_start": _summarize_session_row(session_start) if session_start else None,
            "session_end": _summarize_session_row(session_end) if session_end else None,
            "shell_deny": _summarize_shell_deny(shell_deny) if shell_deny else None,
        },
    }
    report["overall_ok"] = e2e_ok
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"report written: {report_path}")
    print(f"overall_ok={report['overall_ok']} e2e_ok={e2e_ok} checks={checks}")
    return 0 if report["overall_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
