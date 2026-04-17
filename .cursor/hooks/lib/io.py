"""Stdin/stdout JSON I/O and error helpers for Cursor hooks.

Exports:

- HookIOError          — raised when stdin is missing, empty, or not valid JSON
- DERIVED_ERROR_STAGES — frozenset of allowed stage values: parse, config,
                         policy, audit, response
- read_stdin_json()    — read and parse JSON from stdin; raises HookIOError
- read_stdin_object()  — like read_stdin_json() but requires a top-level dict
- write_stdout_json()  — serialize one JSON line to stdout with flush;
                         on encoding failure emits a minimal fallback object
- failure_derived()    — build a standard error metadata dict (error_class,
                         error_message, error_stage) for hook logging records

All hooks read their input via read_stdin_object() and write their response
via write_stdout_json(). On any stdin parse failure, hooks catch HookIOError
and still produce a valid JSON output so Cursor never sees a broken pipe.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Mapping


class HookIOError(ValueError):
    """Invalid or unreadable hook stdin payload."""


# Spec-aligned values for ``derived.error_stage`` (hook logging + nested structures).
DERIVED_ERROR_STAGES = frozenset({"parse", "config", "policy", "audit", "response"})


def read_stdin_json() -> Any:
    """Read and parse JSON from stdin (UTF-8). Raises HookIOError on failure."""
    try:
        raw = sys.stdin.read()
    except OSError as e:
        raise HookIOError(f"failed to read stdin: {e}") from e
    if not raw.strip():
        raise HookIOError("empty stdin")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise HookIOError(f"invalid JSON on stdin: {e}") from e


def read_stdin_object() -> Mapping[str, Any]:
    """Like read_stdin_json but require a JSON object at the top level."""
    data = read_stdin_json()
    if not isinstance(data, dict):
        raise HookIOError("stdin JSON must be an object")
    return data


def write_stdout_json(obj: Any) -> None:
    """
    Serialize *obj* as one JSON line to stdout and flush.

    Uses ``default=str`` and ``allow_nan=False`` so unusual Python values do not break encoding;
    dict keys are sorted for deterministic output. On failure, emits a minimal valid JSON object.
    """
    try:
        line = json.dumps(
            obj,
            ensure_ascii=False,
            default=str,
            allow_nan=False,
            sort_keys=True,
        )
    except (TypeError, ValueError):
        line = '{"hook_io_error":"write_stdout_json_failed"}'
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def failure_derived(
    *,
    stage: str,
    message: str,
    error_class: str = "HookError",
) -> dict[str, str]:
    """
    Standard derived.* keys for audited hook failures.

    *stage* must be one of ``DERIVED_ERROR_STAGES``: parse, config, policy, audit, response.
    """
    if stage not in DERIVED_ERROR_STAGES:
        raise ValueError(
            f"failure_derived: stage must be one of {sorted(DERIVED_ERROR_STAGES)}, got {stage!r}"
        )
    return {
        "error_class": error_class,
        "error_message": message,
        "error_stage": stage,
    }
