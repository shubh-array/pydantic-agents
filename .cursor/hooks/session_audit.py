#!/usr/bin/env python3
"""sessionStart / sessionEnd: lifecycle analytics logging (thin adapter).

Hook Event : sessionStart, sessionEnd (selected via --phase argument)
Script ID  : session_audit:start or session_audit:end
Output     : {} (always, for both phases)

Flow:

1. Parse --phase start|end from command-line arguments
2. Read stdin JSON object via read_stdin_object()
3. Write analytics record via append_audit()
4. Output {} to stdout

Error Handling:

- HookIOError (stdin parse failure) → write analytics row with error details,
  output {}.
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
    parser.add_argument("--phase", choices=("start", "end"), required=True)
    args = parser.parse_args()
    script_id = f"session_audit:{args.phase}"
    try:
        payload = read_stdin_object()
    except HookIOError as e:
        out: dict[str, str] = {}
        try:
            append_audit(
                script_id=script_id,
                hook_input={"hook_event_name": "session", "stdin_error": str(e)},
                hook_output=out,
                derived=failure_derived(stage="parse", message=str(e), error_class="HookIOError"),
            )
        except Exception as ae:
            out = {
                **failure_derived(
                    stage="audit",
                    message=str(ae),
                    error_class=type(ae).__name__,
                )
            }
        write_stdout_json(out)
        return
    out = {}
    try:
        append_audit(script_id=script_id, hook_input=payload, hook_output=out)
    except Exception as ae:
        out = {
            **failure_derived(
                stage="audit",
                message=str(ae),
                error_class=type(ae).__name__,
            )
        }
    write_stdout_json(out)


if __name__ == "__main__":
    main()
