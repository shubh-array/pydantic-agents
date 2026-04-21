# Claude Code adapter recipes

## Invocation

- Binary and flag sets live in `adapters/claude_code/config.json`. Two flag
  sets:
  - `flags_stream` — `-p --output-format stream-json --verbose
    --include-partial-messages`, used by `invoke_subagent` so we can capture
    duration and token usage.
  - `flags_text` — `-p --output-format text`, used for the short trigger and
    improvement prompts where transcripts are unnecessary.
- All subprocess calls strip the `CLAUDECODE` environment variable so the
  adapter can run safely nested inside an interactive Claude Code session.
  This mirrors upstream `skill-creator`.

## Parsing `stream-json`

Same contract as the Cursor adapter:

- Each line is a JSON event.
- The authoritative final event has `type=="result"` with top-level
  `result` (assistant text), `duration_ms`, optional `duration_api_ms`, and
  `usage` (tokens).
- Unknown events are skipped; decode failures are skipped. If the final
  `result` is missing, we fall back to the last `assistant` text part and
  set `status="parse_error"`.

## Frontmatter

- `allowed-tools` is first-class for Claude Code skills per `code.claude.com`
  docs (D-007). Cursor rejects the same key.
- `validate_frontmatter` accepts an optional `skill_dir`; when supplied it
  enforces that the `name` field matches the folder basename.

## Tokens

Captured from the `usage` dict on the final `result` event. We normalize
`input_tokens`/`inputTokens` and `output_tokens`/`outputTokens` into
`{"input": int, "output": int}`.

## Transcripts

`invoke_subagent` writes the verbatim stream to
`<workdir>/transcript.jsonl` for downstream grading.
