# Cursor adapter recipes

## Invocation

- CLI binary and flags are in `adapters/cursor/config.json` under `cli`. Edit
  there, never hardcode in Python.
- The adapter shells out via `subprocess.run` with an argument list (no
  `shell=True`), `capture_output=True`, `text=True`, and an explicit
  `timeout_s`.
- v1 uses the print-mode `agent` CLI with `--output-format=stream-json`. Do
  not rely on the in-session Task tool — this harness is external.

## Parsing `stream-json`

Each line of stdout is a JSON object. Relevant event types:

| `type`     | Purpose                                                  |
|------------|----------------------------------------------------------|
| `system`   | First line; session metadata (`init`).                   |
| `user`     | Echo of our prompt.                                      |
| `assistant`| One or more assistant turns with `message.content[].text`.|
| `result`   | Final event. Contains `result` (assistant text), `duration_ms`, `duration_api_ms`, optionally `usage`. |

Defensive rules:

- Never assume a line is JSON — skip decode failures.
- The `result` event is authoritative; when present, read `result` (assistant text), `duration_ms`, `duration_api_ms`, and `usage` off the top level of *that* event.
- When `result` is missing, fall back to the last `assistant` event's first
  text part, and return `status="parse_error"` (aggregation will tolerate).
- The `system` init event is NOT the assistant reply. `evaluate_trigger`
  MUST look at the assistant text extracted via the rules above, never the
  first line of raw stdout.

## Tokens

As of Cursor CLI April 2026, the `result` event exposes a `usage` dict with
`inputTokens`, `outputTokens`, and cache counters. The adapter captures these
and normalizes to the `{"input": int, "output": int, ...}` shape documented
in `adapters/base.py::SubagentResult`. Aggregation still tolerates `None` for
older CLIs.

## Transcripts

`invoke_subagent` writes the verbatim `stream-json` stdout to
`<workdir>/transcript.jsonl` — one JSON event per line, matching the
`iteration-N/<eval>/<side>/run-1/transcript.jsonl` contract in the spec.
`evaluate_trigger` and `generate_improved_description` do not write
transcripts because they are ephemeral.

## Timeouts

Timeouts surface as `status="timeout"` with `exit_code=124`. The caller
decides whether to retry; the aggregator counts them as failing runs.

## Cross-platform

Paths use `pathlib.Path`. Binary lookups use `shutil.which`. Temp files use
`tempfile.mkdtemp` when needed. No shell metacharacters are passed through.
