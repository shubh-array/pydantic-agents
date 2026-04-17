#!/usr/bin/env python3
"""subagentStart / subagentStop: lifecycle analytics logging (thin adapter).

Hook Event : subagentStart, subagentStop (selected via --event argument)
Script ID  : subagent_audit:subagentStart or subagent_audit:subagentStop
Output     : {"permission": "allow"} for subagentStart; {} for subagentStop

Flow:

1. Parse --event subagentStart|subagentStop from command-line arguments
2. Read stdin JSON object via read_stdin_object()
3. Write analytics record via append_audit()
4. Output response to stdout:
   - subagentStart → {"permission": "allow"}
   - subagentStop  → {}

Error Handling:

- HookIOError (stdin parse failure) → write analytics row with error details,
  output {"permission": "allow"} for subagentStart or {} for subagentStop.
- Logging write failure (at any stage) → merge error metadata into the output.
- Always exits 0 (failClosed in hooks.json handles crash scenarios).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from lib.audit import append_audit  # noqa: E402
from lib.io import HookIOError, failure_derived, read_stdin_object, write_stdout_json  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--event",
        choices=("subagentStart", "subagentStop"),
        required=True,
    )
    args = parser.parse_args()
    script_id = f"subagent_audit:{args.event}"
    try:
        payload = read_stdin_object()
    except HookIOError as e:
        if args.event == "subagentStart":
            out: dict[str, str] = {"permission": "allow"}
        else:
            out = {}
        try:
            append_audit(
                script_id=script_id,
                hook_input={"hook_event_name": args.event, "stdin_error": str(e)},
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

    if args.event == "subagentStart":
        out = {"permission": "allow"}
    else:
        out = {}
    try:
        append_audit(script_id=script_id, hook_input=payload, hook_output=out)
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
