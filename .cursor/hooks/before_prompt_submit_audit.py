#!/usr/bin/env python3
"""beforeSubmitPrompt: audit + optional policy_shadow (non-blocking); always continue.

Hook Event : beforeSubmitPrompt
Script ID  : before_submit_audit
Output     : {"continue": true} (always)

Flow:

1. Read stdin JSON object via read_stdin_object()
2. Load policy config from policy.json (or built-in defaults)
3. Extract shell section from policy
4. Collect prompt text from payload keys: attachments, content, message,
   prompt, submission, text, user_prompt
5. Parse markdown fenced code blocks (``` ... ```) from collected text
6. For each block tagged as shell (bash, sh, zsh, etc.) or with a
   shell-like first line: evaluate against shell policy rules
7. Build a "policy shadow" dict — a preview of what the shell gate would do
8. Write analytics record via append_audit()
9. Output {"continue": true} to stdout

Error Handling:

- HookIOError (stdin parse failure) → write analytics row with error details,
  output {"continue": true}.
- PolicyConfigError (invalid policy.json) → write analytics row with error details,
  output {"continue": true}.
- Logging write failure (at any stage) → merge error metadata into the output,
  still output {"continue": true}.
- Always exits 0 (failClosed in hooks.json handles crash scenarios).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping

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
from lib.shell_policy import evaluate_shell_policy  # noqa: E402

_SHADOW_SHELL_LANGS = frozenset({"bash", "posix", "sh", "shell", "zsh"})
_SHELLISH_FIRST = re.compile(
    r"^(?:bash|cd|command|curl|doas|env|git|mv|pip3?|python3?|rm|sh|sudo|wget|zsh)\b"
)


def _collect_prompt_blob(payload: Mapping[str, Any]) -> str:
    chunks: list[str] = []
    for key in sorted(payload):
        if not isinstance(key, str):
            continue
        if key not in (
            "attachments",
            "content",
            "message",
            "prompt",
            "submission",
            "text",
            "user_prompt",
        ):
            continue
        val = payload[key]
        if isinstance(val, str):
            chunks.append(val)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    chunks.append(item)
                elif isinstance(item, dict):
                    for ik in sorted(item):
                        iv = item[ik]
                        if isinstance(iv, str) and ik in (
                            "path",
                            "file_path",
                            "name",
                            "uri",
                        ):
                            chunks.append(iv)
        elif isinstance(val, dict):
            chunks.append(json.dumps(val, ensure_ascii=False, sort_keys=True))
        elif val is not None:
            chunks.append(str(val))
    return "\n".join(chunks)


def _parse_body_until_closing_line(rest: str) -> tuple[str, int] | None:
    """
    Scan *rest* line-by-line for a closing fence line that is exactly ``` (after strip).

    If a line starts a new fenced block with a language tag before the current block closed,
    return None so the outer scanner can skip the malformed opener.

    Returns (body, consumed_in_rest) where consumed_in_rest covers through the closing line's newline.
    """
    i = 0
    n = len(rest)
    while i < n:
        nl = rest.find("\n", i)
        if nl == -1:
            line_raw = rest[i:]
            stripped = line_raw.strip()
            if stripped == "```":
                return rest[:i], n
            if stripped.startswith("```") and stripped != "```":
                return None
            return None
        line_raw = rest[i:nl]
        stripped = line_raw.strip()
        if stripped == "```":
            return rest[:i], nl + 1
        if stripped.startswith("```") and stripped != "```":
            return None
        i = nl + 1
    return None


def _fence_header_and_body(after_open: str) -> tuple[str, str, int] | None:
    """
    Parse one fenced block after the opening ```.

    Returns (header_lower_or_empty, body, consumed_len) or None if unterminated.
    """
    nl = after_open.find("\n")
    if nl == -1:
        close = after_open.find("```")
        if close == -1:
            return None
        return "", after_open[:close], close + 3
    header = after_open[:nl].strip().lower()
    body_start = nl + 1
    rest = after_open[body_start:]
    parsed_body = _parse_body_until_closing_line(rest)
    if parsed_body is None:
        return None
    body, consumed_in_rest = parsed_body
    consumed = body_start + consumed_in_rest
    return header, body, consumed


def _iter_fenced_blocks(text: str) -> list[tuple[int, str, str]]:
    """Ordered (index, header_lower, body) for each ``` … ``` block."""
    out: list[tuple[int, str, str]] = []
    i = 0
    idx = 0
    n = len(text)
    while i < n:
        start = text.find("```", i)
        if start == -1:
            break
        parsed = _fence_header_and_body(text[start + 3 :])
        if parsed is None:
            # Unterminated fence: skip this opener and keep scanning for later fences.
            i = start + 3
            continue
        header, body, rel_consume = parsed
        out.append((idx, header, body))
        idx += 1
        i = start + 3 + rel_consume
    return out


def _first_nonempty_line(body: str) -> str:
    for line in body.splitlines():
        t = line.strip()
        if t:
            return t
    return ""


def _should_shadow_eval_shell(header: str, body: str) -> tuple[bool, str]:
    if header in _SHADOW_SHELL_LANGS:
        return True, "shell_fence_lang"
    if header == "":
        line0 = _first_nonempty_line(body)
        if line0 and _SHELLISH_FIRST.match(line0):
            return True, "empty_fence_lang_shellish_first_line"
        return False, "empty_fence_lang_not_shellish"
    return False, f"non_shell_fence_lang:{header or 'empty'}"


def build_policy_shadow(
    *,
    prompt_blob: str,
    shell_policy: Mapping[str, Any],
    policy_source: str,
) -> dict[str, Any]:
    fences_out: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for fence_index, header, body in _iter_fenced_blocks(prompt_blob):
        do_eval, skip_reason = _should_shadow_eval_shell(header, body)
        if not do_eval:
            skipped.append({"index": fence_index, "reason": skip_reason})
            continue
        cmd = body.rstrip("\n")
        decision = evaluate_shell_policy(cmd, shell_policy)
        fences_out.append(
            {
                "allowed": decision.allowed,
                "evaluated": True,
                "fence_lang": header or "",
                "index": fence_index,
                "reason": decision.reason,
                "segments": list(decision.segments),
                "trace": list(decision.trace),
            }
        )
    any_would_deny = any(not f["allowed"] for f in fences_out)
    return {
        "aggregate": {
            "any_would_deny": any_would_deny,
            "shell_fence_count": len(fences_out),
        },
        "policy_source": policy_source,
        "shell": {"fences": fences_out, "skipped_fences": skipped},
        "version": 1,
    }


def main() -> None:
    try:
        payload = read_stdin_object()
    except HookIOError as e:
        out: dict[str, Any] = {"continue": True}
        ps = {
            "version": 1,
            **failure_derived(stage="parse", message=str(e), error_class="HookIOError"),
        }
        try:
            append_audit(
                script_id="before_submit_audit",
                hook_input={
                    "hook_event_name": "beforeSubmitPrompt",
                    "stdin_error": str(e),
                },
                hook_output=out,
                derived={"policy_shadow": ps},
            )
        except Exception as ae:
            out = {
                **out,
                **failure_derived(
                    stage="audit",
                    message=str(ae),
                    error_class=type(ae).__name__,
                ),
            }
        write_stdout_json(out)
        return

    try:
        policy, policy_source = load_policy_config(_HOOKS_DIR)
        shell_pol = shell_section(policy)
    except PolicyConfigError as e:
        out = {"continue": True}
        derived = {
            "policy_shadow": {
                "version": 1,
                **failure_derived(
                    stage="config",
                    message=str(e),
                    error_class="PolicyConfigError",
                ),
            }
        }
        try:
            append_audit(
                script_id="before_submit_audit",
                hook_input=payload,
                hook_output=out,
                derived=derived,
            )
        except Exception as ae:
            out = {
                **out,
                **failure_derived(
                    stage="audit",
                    message=str(ae),
                    error_class=type(ae).__name__,
                ),
            }
        write_stdout_json(out)
        return

    prompt_blob = _collect_prompt_blob(payload)
    shadow = build_policy_shadow(
        prompt_blob=prompt_blob,
        shell_policy=shell_pol,
        policy_source=policy_source,
    )
    out = {"continue": True}
    derived = {"policy_shadow": shadow}
    try:
        append_audit(
            script_id="before_submit_audit",
            hook_input=payload,
            hook_output=out,
            derived=derived,
        )
    except Exception as ae:
        out = {
            **out,
            **failure_derived(
                stage="audit",
                message=str(ae),
                error_class=type(ae).__name__,
            ),
        }
    write_stdout_json(out)


if __name__ == "__main__":
    main()
