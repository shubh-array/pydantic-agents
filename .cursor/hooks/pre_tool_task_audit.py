#!/usr/bin/env python3
"""preToolUse (Task): audit tool payload + textual skill heuristics; always allow (thin adapter).

Hook Event : preToolUse
Script ID  : pre_tool_task_audit
Output     : {"permission": "allow"} (always)

Flow:

1. Read stdin JSON object via read_stdin_object()
2. Extract agent_message (str) and tool_input (JSON-serialized) from payload
3. Check combined text for skill-related patterns:
   - Literal hints: SKILL.md, .cursor/skills, .agents/skills,
     .claude/skills, .codex/skills, /skills/
   - Regex: word-boundary "skill" or "skills" followed by path separator
4. Write analytics record via append_audit() with skill_signal and skill_reasons
   in derived
5. Output {"permission": "allow"} to stdout

Error Handling:

- HookIOError (stdin parse failure) → write analytics row with error details,
  output {"permission": "allow"}.
- Logging write failure (at any stage) → merge error metadata into the output,
  still output {"permission": "allow"}.
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
from lib.io import HookIOError, failure_derived, read_stdin_object, write_stdout_json  # noqa: E402

_HINTS = (
    "SKILL.md",
    ".cursor/skills",
    ".agents/skills",
    ".claude/skills",
    ".codex/skills",
    "/skills/",
)


def skill_signal_from_task_payload(
    payload: Mapping[str, Any],
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    chunks: list[str] = []
    am = payload.get("agent_message")
    if isinstance(am, str):
        chunks.append(am)
    ti = payload.get("tool_input")
    chunks.append(json.dumps(ti, ensure_ascii=False, sort_keys=True) if ti is not None else "")
    blob = "\n".join(chunks)
    for h in _HINTS:
        if h in blob:
            reasons.append(f"mentions {h}")
    low = blob.lower()
    if re.search(r"\bskills?[/\\]", low):
        reasons.append("skills path segment")
    return bool(reasons), reasons


def main() -> None:
    try:
        payload = read_stdin_object()
    except HookIOError as e:
        out: dict[str, Any] = {"permission": "allow"}
        try:
            append_audit(
                script_id="pre_tool_task_audit",
                hook_input={"hook_event_name": "preToolUse", "stdin_error": str(e)},
                hook_output=out,
                derived=failure_derived(stage="parse", message=str(e), error_class="HookIOError"),
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

    sig, reasons = skill_signal_from_task_payload(payload)
    derived: dict[str, Any] = {"skill_reasons": reasons, "skill_signal": sig}
    out = {"permission": "allow"}
    try:
        append_audit(
            script_id="pre_tool_task_audit",
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
