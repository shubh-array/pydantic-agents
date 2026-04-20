# Cursor adapter recipes

- Flags and binary live in `adapters/cursor/config.json` under `cli` — edit there, not in Python.
- v1 uses the Cursor CLI in print mode with `stream-json` output. Do not use the in-session Task tool for external harnesses.
- Timeouts surface as `status="timeout"` with exit code `124` in `SubagentResult`.
- Token usage is not available from the CLI stream in v1; aggregation must tolerate `tokens: null` (D-006).
