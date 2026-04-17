"""Load and validate the optional .cursor/hooks/policy.json file.

Exports:

- PolicyConfigError       — raised when policy.json exists but is invalid
- default_policy()        — deep copy of the built-in default policy
- parse_policy_dict()     — validate a raw dict as a policy; raises PolicyConfigError
- load_policy_config()    — load from policy.json or fall back to defaults;
                            returns (policy_dict, source) where source is
                            "file" or "defaults"
- shell_section()         — extract the shell subsection from a validated policy
- as_immutable_snapshot() — JSON round-trip copy safe for serialization

Policy Schema (version 1):

  {
    "version": 1,                          (required, must be 1)
    "shell": {                             (required)
      "deny_rm_recursive_force": bool,     (default: true)
      "deny_git_push_main": bool,          (default: true)
      "deny_wrappers": [str, ...],         (default: sudo, doas, env, ...)
      "main_ref_patterns": [str, ...]      (default: main, refs/heads/main, ...)
    }
  }

Unknown top-level or shell-level keys are rejected. Missing shell keys
are filled from built-in defaults.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


class PolicyConfigError(ValueError):
    """policy.json exists but is invalid."""


_DEFAULT_POLICY: dict[str, Any] = {
    "version": 1,
    "shell": {
        "deny_rm_recursive_force": True,
        "deny_git_push_main": True,
        "deny_wrappers": [
            "sudo",
            "doas",
            "env",
            "command",
            "nice",
            "nohup",
            "timeout",
        ],
        "main_ref_patterns": [
            "main",
            "refs/heads/main",
            "HEAD:main",
            ":main",
        ],
    },
}


def default_policy() -> dict[str, Any]:
    """Deep copy of built-in defaults (safe to mutate by callers if needed)."""
    return json.loads(json.dumps(_DEFAULT_POLICY))


def _expect_type(path: str, value: Any, *allowed: type) -> None:
    if not isinstance(value, allowed):
        names = " | ".join(t.__name__ for t in allowed)
        raise PolicyConfigError(f"{path}: expected {names}, got {type(value).__name__}")


def _validate_shell_block(path: str, shell: Any) -> dict[str, Any]:
    _expect_type(path, shell, dict)
    assert isinstance(shell, dict)
    allowed_keys = {
        "deny_rm_recursive_force",
        "deny_git_push_main",
        "deny_wrappers",
        "main_ref_patterns",
    }
    extra = set(shell) - allowed_keys
    if extra:
        raise PolicyConfigError(f"{path}: unknown keys: {sorted(extra)!r}")

    out: dict[str, Any] = {}
    for key in ("deny_rm_recursive_force", "deny_git_push_main"):
        if key in shell:
            _expect_type(f"{path}.{key}", shell[key], bool)
            out[key] = shell[key]
        else:
            out[key] = _DEFAULT_POLICY["shell"][key]  # type: ignore[index]

    if "deny_wrappers" in shell:
        _expect_type(f"{path}.deny_wrappers", shell["deny_wrappers"], list)
        dw = shell["deny_wrappers"]
        for i, item in enumerate(dw):
            _expect_type(f"{path}.deny_wrappers[{i}]", item, str)
            if not item.strip():
                raise PolicyConfigError(
                    f"{path}.deny_wrappers[{i}]: wrapper name must be non-empty"
                )
        out["deny_wrappers"] = list(dw)
    else:
        out["deny_wrappers"] = list(_DEFAULT_POLICY["shell"]["deny_wrappers"])  # type: ignore[index]

    if "main_ref_patterns" in shell:
        _expect_type(f"{path}.main_ref_patterns", shell["main_ref_patterns"], list)
        mp = shell["main_ref_patterns"]
        for i, item in enumerate(mp):
            _expect_type(f"{path}.main_ref_patterns[{i}]", item, str)
            if not item.strip():
                raise PolicyConfigError(f"{path}.main_ref_patterns[{i}]: pattern must be non-empty")
        out["main_ref_patterns"] = list(mp)
    else:
        out["main_ref_patterns"] = list(
            _DEFAULT_POLICY["shell"]["main_ref_patterns"]  # type: ignore[index]
        )

    return out


def parse_policy_dict(data: Any, *, label: str = "policy") -> dict[str, Any]:
    """Validate a policy mapping; raises PolicyConfigError with a descriptive message."""
    _expect_type(label, data, dict)
    assert isinstance(data, dict)
    top_extra = set(data) - {"version", "shell"}
    if top_extra:
        raise PolicyConfigError(f"{label}: unknown top-level keys: {sorted(top_extra)!r}")

    if "version" not in data:
        raise PolicyConfigError(f"{label}: missing required key 'version'")
    _expect_type(f"{label}.version", data["version"], int)
    if data["version"] != 1:
        raise PolicyConfigError(
            f"{label}.version: unsupported version {data['version']!r} (only 1 is supported)"
        )

    if "shell" not in data:
        raise PolicyConfigError(f"{label}: missing required key 'shell'")
    shell = _validate_shell_block(f"{label}.shell", data["shell"])
    return {"version": 1, "shell": shell}


def load_policy_config(hooks_dir: Path) -> tuple[dict[str, Any], str]:
    """
    Load policy from ``hooks_dir / "policy.json"``.

    Returns ``(policy, source)`` where ``source`` is ``\"file\"`` or ``\"defaults\"``.
    """
    path = hooks_dir / "policy.json"
    if not path.is_file():
        return default_policy(), "defaults"
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise PolicyConfigError(f"cannot read {path}: {e}") from e
    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise PolicyConfigError(f"{path}: invalid JSON: {e}") from e
    parsed = parse_policy_dict(raw, label=str(path))
    return parsed, "file"


def shell_section(policy: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the shell subsection (must exist on validated policy)."""
    shell = policy.get("shell")
    if not isinstance(shell, dict):
        raise PolicyConfigError("internal: policy.shell is not an object")
    return shell


def as_immutable_snapshot(policy: Mapping[str, Any]) -> dict[str, Any]:
    """Return a plain dict/list snapshot suitable for JSON serialization."""
    return json.loads(json.dumps(policy))
