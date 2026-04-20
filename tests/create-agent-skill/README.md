# create-agent-skill tests

- Unit: `uv run pytest tests/create-agent-skill/unit -q`
- Integration: `uv run pytest tests/create-agent-skill/integration -q`
- E2E: requires `agent` on PATH; `uv run pytest tests/create-agent-skill/e2e -q`

E2E failures write transcripts under `e2e/runs/`.
