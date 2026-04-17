#!/usr/bin/env python3
"""beforeShellExecution: policy-driven allow/deny + audit (thin adapter).

Flow:

1. Read stdin → on failure: DENY + audit
2. Load policy.json → on PolicyConfigError: DENY + audit (fail-closed on bad config)
3. Evaluate shell policy: evaluate_shell_policy(command, shell_pol) → ShellPolicyDecision
4. If allowed: {"permission": "allow"}
5. If denied: {"permission": "deny", "agent_message": "...", "user_message": "..."}
6. Write analytics row → if logging fails AND command was allowed: DENY (fail-closed)

Error handling:
- On HookIOError, still writes a logging row with error details, then outputs {"permission": "deny", "agent_message": "...", "user_message": "..."}.
- On PolicyConfigError, still writes a logging row with error details, then outputs {"permission": "deny", "agent_message": "...", "user_message": "..."}.
- On logging write failure, merges error metadata into the output.
- Always exits 0 (the failClosed in hooks.json handles crash scenarios).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from lib.audit import append_audit  # noqa: E402
from lib.io import (  # noqa: E402
    HookIOError,
    failure_derived,
    read_stdin_object,
    write_stdout_json,
)
from lib.policy_config import PolicyConfigError, load_policy_config, shell_section  # noqa: E402
from lib.shell_policy import (  # noqa: E402
    REASON_DENY_GIT_PUSH_MAIN,
    REASON_DENY_RM_RECURSIVE_FORCE,
    evaluate_shell_policy,
)


def _deny_audit_io_failure() -> dict[str, str]:
    return {
        "agent_message": ("Shell blocked: hook logging failed; execution denied (fail-closed)."),
        "permission": "deny",
        "user_message": (
            "Blocked: shell hook could not write a logging record; refusing execution (fail-closed)."
        ),
    }


def _deny_messages(*, reason: str) -> dict[str, str]:
    if reason == REASON_DENY_RM_RECURSIVE_FORCE:
        return {
            "agent_message": (
                "Shell blocked: rm with recursive+force (or nested equivalent) is denied by policy."
            ),
            "permission": "deny",
            "user_message": (
                "Blocked: destructive rm (recursive + force) is not allowed by project hooks policy."
            ),
        }
    if reason == REASON_DENY_GIT_PUSH_MAIN:
        return {
            "agent_message": "Shell blocked: git push targeting protected main refs is denied by policy.",
            "permission": "deny",
            "user_message": "Blocked: pushing to branch main is not allowed by project hooks policy.",
        }
    return {
        "agent_message": f"Shell blocked by policy ({reason}).",
        "permission": "deny",
        "user_message": "Blocked: this shell command is not allowed by project hooks policy.",
    }


def _decision_derived(
    *,
    command: str,
    decision_allowed: bool,
    decision_reason: str,
    segments: tuple[str, ...],
    trace: tuple[str, ...],
    policy_source: str,
) -> dict[str, Any]:
    d: dict[str, Any] = {
        "command_sample": command[:500] + ("…" if len(command) > 500 else ""),
        "policy_source": policy_source,
        "reason": decision_reason,
        "segments": list(segments),
        "shell_allowed": decision_allowed,
        "trace": list(trace),
    }
    if not decision_allowed:
        d["deny_reason"] = decision_reason
    return d


def main() -> None:
    try:
        payload = read_stdin_object()
    except HookIOError as e:
        out: dict[str, Any] = {
            "agent_message": "Shell blocked: could not read hook input; refusing execution (fail-closed).",
            "permission": "deny",
            "user_message": "Blocked: shell hook received invalid stdin.",
        }
        derived = failure_derived(stage="parse", message=str(e), error_class="HookIOError")
        try:
            append_audit(
                script_id="before_shell",
                hook_input={
                    "hook_event_name": "beforeShellExecution",
                    "stdin_error": str(e),
                },
                hook_output=dict(out),
                derived=derived,
            )
        except Exception as ae:
            out = {
                **_deny_audit_io_failure(),
                **failure_derived(
                    stage="audit",
                    message=str(ae),
                    error_class=type(ae).__name__,
                ),
            }
        write_stdout_json(out)
        return

    command = payload.get("command") or ""
    if not isinstance(command, str):
        command = str(command)

    try:
        policy, policy_source = load_policy_config(_HOOKS_DIR)
        shell_pol = shell_section(policy)
    except PolicyConfigError as e:
        out = {
            "agent_message": "Shell blocked: invalid hooks policy.json; refusing execution (fail-closed).",
            "permission": "deny",
            "user_message": "Blocked: shell policy configuration is invalid.",
        }
        derived = failure_derived(
            stage="config",
            message=str(e),
            error_class="PolicyConfigError",
        )
        try:
            append_audit(
                script_id="before_shell",
                hook_input=payload,
                hook_output=dict(out),
                derived=derived,
            )
        except Exception as ae:
            out = {
                **_deny_audit_io_failure(),
                **failure_derived(
                    stage="audit",
                    message=str(ae),
                    error_class=type(ae).__name__,
                ),
            }
        write_stdout_json(out)
        return

    decision = evaluate_shell_policy(command, shell_pol)
    derived = _decision_derived(
        command=command,
        decision_allowed=decision.allowed,
        decision_reason=decision.reason,
        segments=decision.segments,
        trace=decision.trace,
        policy_source=policy_source,
    )

    if decision.allowed:
        out = {"permission": "allow"}
    else:
        out = _deny_messages(reason=decision.reason)

    try:
        append_audit(
            script_id="before_shell",
            hook_input=payload,
            hook_output=dict(out),
            derived=derived,
        )
    except Exception as ae:
        if decision.allowed:
            out = {
                **_deny_audit_io_failure(),
                **failure_derived(
                    stage="audit",
                    message=str(ae),
                    error_class=type(ae).__name__,
                ),
            }
        else:
            out = {
                **dict(out),
                **failure_derived(
                    stage="audit",
                    message=str(ae),
                    error_class=type(ae).__name__,
                ),
            }
    write_stdout_json(out)


if __name__ == "__main__":
    main()
