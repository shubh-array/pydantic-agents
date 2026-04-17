# pydantic-agents - Cursor Hook Framework

Security-focused Cursor hooks for shell policy enforcement and analytics logging.

## Overview

This project configures Cursor hooks in `.cursor/hooks.json` and routes them to Python handlers in
`.cursor/hooks/` (plus one built-in prompt gate entry). The handlers normalize hook data and append
analytics rows to JSONL.

Primary analytics destination:

- `.array/analytics.jsonl` (default, under resolved workspace root)
- Override with `CURSOR_HOOK_ANALYTICS_JSONL=/absolute/path/to/file.jsonl`

## Architecture

1. Cursor emits hook events.
2. `.cursor/hooks.json` routes events to Python scripts and one prompt-gate hook.
3. Python handlers read JSON from stdin and emit hook responses on stdout.
4. Handlers call `append_audit(...)` from `.cursor/hooks/lib/audit.py`.
5. `append_audit(...)` writes one normalized analytics record per successful append attempt.

Decision behavior:

- `before_shell_gate.py` is the only script that can deny shell command execution.
- The `beforeSubmitPrompt` prompt hook can deny prompt submission.
- All other script hooks are audit/analytics-only and return allow/continue responses.

## Hook Mapping

Registered in `.cursor/hooks.json`:

- `sessionStart` -> `session_audit.py --phase start`
- `sessionEnd` -> `session_audit.py --phase end`
- `beforeShellExecution` -> `before_shell_gate.py`
- `beforeSubmitPrompt` -> `before_prompt_submit_audit.py` (`matcher: UserPromptSubmit`)
- `beforeSubmitPrompt` -> prompt gate (`type: prompt`, `matcher: UserPromptSubmit`)
- `preToolUse` (`matcher: Task`) -> `pre_tool_task_audit.py`
- `subagentStart` -> `subagent_audit.py --event subagentStart`
- `subagentStop` -> `subagent_audit.py --event subagentStop`

Each configured hook entry currently sets `failClosed: true`.

## Shell Policy

Shell policy is loaded from `.cursor/hooks/policy.json` using `lib/policy_config.py`.
If policy parsing/validation fails, `before_shell_gate.py` denies execution (fail-closed behavior).

Current policy evaluation in `lib/shell_policy.py` includes:

- deny recursive+force `rm` usage (including clustered flags like `-rf`)
- deny `git push` arguments that target protected main refs/patterns
- unwrap common wrappers (`sudo`, `doas`, `env`, `command`, `nice`, `nohup`, `timeout`)
- recurse into nested `sh -c` / `bash -c` / `zsh -c` payloads
- deny malformed shell segments that fail `shlex` parsing

## Logging Contract

`append_audit(...)` writes analytics-style JSON rows with stable keys, including:

- core identifiers: `ts`, `script_id`, `event_type`
- run context: `conversation_id`, `generation_id`, `session_id`, `model`
- policy fields: `policy_outcome`, `policy_reason`, `policy_trace`, `deny_reason`
- event fields: `command_sample`, `skill_signal`, `duration_ms`, `shell_fence_count`, etc.

Write behavior from `lib/audit.py`:

- append-only JSONL writes
- best-effort `flock` on Unix (write still proceeds if lock acquisition fails)
- file mode enforced to `0600` after writes
- parent directory auto-created when missing

Note on failures:

- Hook scripts still emit valid stdout JSON on parse/config/audit failures.
- If `before_shell_gate.py` would allow a command but audit writing fails, it flips to deny
  (explicit fail-closed for shell execution).

## Testing

The only maintained automated harness in this repository is:

- `tests/hook_matrix/live_e2e_report.py`

It runs a real `agent -p` probe and verifies analytics output contains:

- a `session_audit:start` row
- a `session_audit:end` row
- a denied shell row with non-empty `deny_reason`

Run:

```bash
uv run --group dev python tests/hook_matrix/live_e2e_report.py
```

Outputs:

- `tests/hook_matrix/out/e2e_analytics.jsonl`
- `tests/hook_matrix/out/live_e2e_report.json`

## Repository Layout

```text
pydantic-agents/
|- .cursor/
|  |- hooks.json
|  `- hooks/
|     |- before_shell_gate.py
|     |- before_prompt_submit_audit.py
|     |- pre_tool_task_audit.py
|     |- session_audit.py
|     |- subagent_audit.py
|     |- policy.json
|     `- lib/
|        |- __init__.py
|        |- audit.py
|        |- io.py
|        |- policy_config.py
|        `- shell_policy.py
|- .array/
|  `- analytics.jsonl
|- tests/
|  `- hook_matrix/
|     |- live_e2e_report.py
|     `- out/
|- docs/
|  `- superpowers/
|     `- specs/
|- dashboard.html
|- pyproject.toml
`- uv.lock
```
