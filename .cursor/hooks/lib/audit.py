"""Append-only analytics JSONL under <workspace>/.array/analytics.jsonl.

Exports:

- resolve_workspace_root() — pick the workspace root from a hook payload
- resolve_analytics_jsonl_path() — final analytics file path (override or default)
- append_audit() — append one analytics JSON record
- utc_iso_z_now() — UTC ``Z`` timestamp string (shared with tests / reports)

Optional env ``CURSOR_HOOK_ANALYTICS_JSONL``: when set to a non-empty path, that file is used
instead of ``<workspace>/.array/analytics.jsonl``. Intended for tests or alternate layouts.

Workspace Root Resolution (resolve_workspace_root):

1. Parse workspace_roots list from payload
2. If file_path from payload falls under a known root → use that root
3. If cwd from payload falls under a known root → use that root
4. Fall back in order: first root, cwd, $CURSOR_PROJECT_DIR, $PWD, getcwd()

Analytics Record Format (append_audit):

Each line in analytics.jsonl is a normalized JSON object from ``_build_analytics_record(...)``.

File Handling:

- The analytics file's parent directory is created if missing (``parents=True``). For the default
  path this is ``.array/`` under the workspace root; for ``CURSOR_HOOK_ANALYTICS_JSONL``, the
  parent of that file.
- Analytics file is created with mode 0600 (owner read/write only)
- On Unix, an exclusive flock is held during the append; if locking
  fails the write still proceeds (best-effort concurrency)
- File is chmodded to 0600 after each write (no-op on failure)
"""

from __future__ import annotations

import json
import os
import shlex
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

try:
    import fcntl  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover — non-Unix
    fcntl = None  # type: ignore[assignment]


def resolve_workspace_root(payload: Mapping[str, Any]) -> Path:
    """
    Pick a workspace root using payload context.

    Prefer ``file_path`` or ``cwd`` when they lie under an entry in
    ``workspace_roots`` (first matching root wins).

    Otherwise fall back to:
    first root, ``cwd``, ``CURSOR_PROJECT_DIR``, ``PWD``, then ``getcwd()``.
    """
    roots_raw = payload.get("workspace_roots")
    roots: list[Path] = []
    if isinstance(roots_raw, list):
        for item in roots_raw:
            if isinstance(item, str) and item.strip():
                try:
                    roots.append(Path(item).expanduser().resolve())
                except OSError:
                    continue

    def _under_root(path: Path) -> Optional[Path]:
        for root in roots:
            try:
                path.relative_to(root)
            except ValueError:
                continue
            return root
        return None

    fp = payload.get("file_path")
    if isinstance(fp, str) and fp.strip():
        try:
            p = Path(fp).expanduser().resolve()
        except OSError:
            pass
        else:
            hit = _under_root(p)
            if hit is not None:
                return hit

    cwd_val = payload.get("cwd")
    if isinstance(cwd_val, str) and cwd_val.strip():
        try:
            c = Path(cwd_val).expanduser().resolve()
        except OSError:
            pass
        else:
            hit = _under_root(c)
            if hit is not None:
                return hit

    if roots:
        return roots[0]

    if isinstance(cwd_val, str) and cwd_val.strip():
        try:
            return Path(cwd_val).expanduser().resolve()
        except OSError:
            pass

    env = os.environ.get("CURSOR_PROJECT_DIR")
    if env:
        try:
            return Path(env).expanduser().resolve()
        except OSError:
            pass

    pwd = os.environ.get("PWD")
    if pwd:
        try:
            return Path(pwd).expanduser().resolve()
        except OSError:
            pass

    return Path.cwd().resolve()


# Optional override for analytics destination; unset means sibling analytics.jsonl.
ANALYTICS_JSONL_ENV_VAR = "CURSOR_HOOK_ANALYTICS_JSONL"

_EVENT_TYPE_BY_SCRIPT_ID: dict[str, str] = {
    "session_audit:start": "session_start",
    "session_audit:end": "session_end",
    "subagent_audit:subagentStart": "subagent_start",
    "subagent_audit:subagentStop": "subagent_stop",
    "before_submit_audit": "prompt_submit",
    "before_shell": "shell_eval",
    "pre_tool_task_audit": "tool_task",
}

_KNOWN_SHELL_DENY_REASONS = frozenset(
    {
        "deny_rm_recursive_force",
        "deny_git_push_main",
        "deny_nested_shell_depth",
        "deny_shell_parse_error",
    }
)


def utc_iso_z_now() -> str:
    """UTC instant as ISO-8601 ending in ``Z`` (same format as analytics ``ts``)."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve_analytics_jsonl_path(
    hook_input: Mapping[str, Any],
    *,
    workspace_root: Path | None = None,
) -> Path:
    """
    Return the compact analytics JSONL path hooks should write to.

    If ``CURSOR_HOOK_ANALYTICS_JSONL`` is set, that path is used.
    Otherwise this defaults to ``resolve_workspace_root(hook_input) / ".array" / "analytics.jsonl"``.
    Pass *workspace_root* when the caller already resolved the root to avoid duplicate work.
    """
    override = os.environ.get(ANALYTICS_JSONL_ENV_VAR, "").strip()
    if override:
        return Path(override).expanduser().resolve()
    root = workspace_root if workspace_root is not None else resolve_workspace_root(hook_input)
    return (root / ".array" / "analytics.jsonl").resolve()


def _sanitize_for_json(
    obj: Any,
    *,
    _depth: int = 0,
    _max_depth: int = 48,
    max_str_len: int | None = None,
    truncate_only_key: str | None = None,
    _current_key: str | None = None,
) -> Any:
    """
    Produce a JSON-serializable structure: dict keys as ``str``, unknown values as ``str(obj)``.

    When *max_str_len* is set, string values longer than the limit are truncated with an appended
    length annotation. If *truncate_only_key* is set, truncation applies only when sanitizing
    values under that dict key.
    """
    if _depth > _max_depth:
        return "<max_depth>"
    if obj is None or isinstance(obj, (bool, int, float)):
        return obj
    if isinstance(obj, str):
        should_truncate = max_str_len is not None and (
            truncate_only_key is None or _current_key == truncate_only_key
        )
        if should_truncate and len(obj) > max_str_len:
            return obj[:max_str_len] + f"\u2026[truncated, {len(obj)} chars total]"
        return obj
    if isinstance(obj, (bytes, bytearray)):
        s = bytes(obj).decode("utf-8", errors="replace")
        should_truncate = max_str_len is not None and (
            truncate_only_key is None or _current_key == truncate_only_key
        )
        if should_truncate and len(s) > max_str_len:
            return s[:max_str_len] + f"\u2026[truncated, {len(s)} chars total]"
        return s
    kw = {
        "_max_depth": _max_depth,
        "max_str_len": max_str_len,
        "truncate_only_key": truncate_only_key,
    }
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            try:
                key = str(k)
            except Exception:  # pragma: no cover — extremely defensive
                key = repr(k)
            out[key] = _sanitize_for_json(v, _depth=_depth + 1, _current_key=key, **kw)
        return out
    if isinstance(obj, (list, tuple)):
        return [
            _sanitize_for_json(x, _depth=_depth + 1, _current_key=_current_key, **kw) for x in obj
        ]
    if isinstance(obj, set):
        return [
            _sanitize_for_json(x, _depth=_depth + 1, _current_key=_current_key, **kw)
            for x in sorted(obj, key=str)
        ]
    try:
        return str(obj)
    except Exception:
        return "<non_serializable>"


def _append_jsonl_line(path: Path, line: str) -> None:
    """Append one UTF-8 line to *path* with best-effort locking and mode 0600."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = line.encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    locked = False
    try:
        if fcntl is not None:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
                locked = True
            except OSError:
                pass
        os.write(fd, data)
    finally:
        if fcntl is not None and locked:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            except OSError:
                pass
        os.close(fd)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _event_type_for(script_id: str, hook_event_name: Any) -> str:
    if script_id in _EVENT_TYPE_BY_SCRIPT_ID:
        return _EVENT_TYPE_BY_SCRIPT_ID[script_id]
    if isinstance(hook_event_name, str) and hook_event_name.strip():
        return hook_event_name.strip()
    return "hook_event"


def _first_token_basename(command: str) -> str:
    try:
        toks = shlex.split(command, posix=True)
    except ValueError:
        toks = command.strip().split()
    if not toks:
        return "unknown"
    return Path(toks[0]).name or toks[0]


def _truncate_text(s: str, *, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[:max_len] + "…"


def _violations_for_reason(reason: Optional[str]) -> list[str]:
    if reason and reason in _KNOWN_SHELL_DENY_REASONS:
        return [reason]
    return []


def _prompt_char_count(payload: Mapping[str, Any]) -> int:
    total = 0
    for key in ("content", "message", "prompt", "submission", "text", "user_prompt"):
        v = payload.get(key)
        if isinstance(v, str):
            total += len(v)
    return total


def _as_number_or_none(v: Any) -> int | float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    return None


def _build_analytics_record(
    *,
    recorded_at: str,
    script_id: str,
    hook_input: Mapping[str, Any],
    hook_output: Optional[Mapping[str, Any]],
    derived: Optional[Mapping[str, Any]],
    workspace_root: Path,
) -> dict[str, Any]:
    workspace_name = workspace_root.name or str(workspace_root)
    derived_map = derived if isinstance(derived, Mapping) else None

    permission = hook_output.get("permission") if isinstance(hook_output, Mapping) else None
    cont = hook_output.get("continue") if isinstance(hook_output, Mapping) else None
    if isinstance(permission, str) and permission in ("allow", "deny"):
        policy_outcome = permission
    elif isinstance(cont, bool):
        policy_outcome = "allow" if cont else "deny"
    else:
        policy_outcome = "info"

    policy_reason = None
    if derived_map is not None:
        dr = derived_map.get("deny_reason")
        if isinstance(dr, str) and dr.strip():
            policy_reason = dr
        elif isinstance(derived_map.get("reason"), str):
            policy_reason = str(derived_map.get("reason"))

    # Stable analytics schema: keep critical keys present on every row.
    rec: dict[str, Any] = {
        "ts": recorded_at,
        "script_id": script_id,
        "event_type": _event_type_for(script_id, hook_input.get("hook_event_name")),
        "conversation_id": hook_input.get("conversation_id"),
        "generation_id": hook_input.get("generation_id"),
        "session_id": hook_input.get("session_id"),
        "model": hook_input.get("model"),
        "workspace_name": workspace_name,
        # Intentionally omitted to keep analytics stream lean:
        # "workspace_id", "project_key", "project_source"
        "policy_outcome": policy_outcome,
        "policy_reason": policy_reason,
        "policy_source": None,
        "policy_trace": None,
        "policy_violations": None,
        "deny_reason": None,
        "shell_allowed": None,
        "command_class": None,
        "command_sample": None,
        "command_segments_count": None,
        "prompt_chars": None,
        "attachment_count": None,
        "shell_fence_count": None,
        "any_would_deny": None,
        "skill_signal": None,
        "duration_ms": None,
        "final_status": None,
        "end_reason": None,
    }

    if script_id == "before_submit_audit":
        atts = hook_input.get("attachments")
        att_count = len(atts) if isinstance(atts, list) else 0
        rec["prompt_chars"] = _prompt_char_count(hook_input)
        rec["attachment_count"] = att_count
        if derived_map is not None:
            ps = derived_map.get("policy_shadow")
            if isinstance(ps, Mapping):
                agg = ps.get("aggregate")
                if isinstance(agg, Mapping):
                    rec["shell_fence_count"] = agg.get("shell_fence_count")
                    rec["any_would_deny"] = agg.get("any_would_deny")
    elif script_id == "before_shell":
        cmd = hook_input.get("command")
        if isinstance(cmd, str):
            rec["command_class"] = _first_token_basename(cmd).lower()
            rec["command_sample"] = _truncate_text(cmd, max_len=200)
        if derived_map is not None:
            if isinstance(derived_map.get("shell_allowed"), bool):
                rec["shell_allowed"] = derived_map.get("shell_allowed")
            if isinstance(derived_map.get("deny_reason"), str):
                rec["deny_reason"] = derived_map.get("deny_reason")
            if isinstance(derived_map.get("policy_source"), str):
                rec["policy_source"] = derived_map.get("policy_source")
            segs = derived_map.get("segments")
            if isinstance(segs, list):
                rec["command_segments_count"] = len(segs)
            tr = derived_map.get("trace")
            if isinstance(tr, list) and tr:
                rec["policy_trace"] = tr[:4]
        dr_shell = rec.get("deny_reason")
        rec["policy_violations"] = _violations_for_reason(dr_shell if isinstance(dr_shell, str) else None)
    elif script_id == "pre_tool_task_audit":
        if derived_map is not None and isinstance(derived_map.get("skill_signal"), bool):
            rec["skill_signal"] = derived_map.get("skill_signal")
    elif script_id == "session_audit:end":
        rec["duration_ms"] = _as_number_or_none(hook_input.get("duration_ms"))
        fs = hook_input.get("final_status")
        rec["final_status"] = fs if isinstance(fs, str) and fs.strip() else None
        rsn = hook_input.get("reason")
        rec["end_reason"] = rsn if isinstance(rsn, str) and rsn.strip() else None

    return _sanitize_for_json(rec)


def append_audit(
    *,
    script_id: str,
    hook_input: Mapping[str, Any],
    hook_output: Optional[Mapping[str, Any]] = None,
    derived: Optional[Mapping[str, Any]] = None,
) -> Path:
    """
    Append one analytics JSON object as a line to analytics JSONL.

    The analytics file is created with mode ``0600`` and chmodded to ``0600`` after writes.
    On Unix, an exclusive ``flock`` is attempted for the duration of the append; if locking fails,
    the line is still written (best-effort concurrency).
    """
    root = resolve_workspace_root(hook_input)
    path = resolve_analytics_jsonl_path(hook_input, workspace_root=root)
    recorded_at = utc_iso_z_now()
    analytics = _build_analytics_record(
        recorded_at=recorded_at,
        script_id=script_id,
        hook_input=hook_input,
        hook_output=hook_output,
        derived=derived,
        workspace_root=root,
    )
    _append_jsonl_line(path, json.dumps(analytics, ensure_ascii=False) + "\n")
    return path
