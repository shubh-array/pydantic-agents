# Upstream divergence log (append-only)

When adding a row, assign the next `D-NNN` ID. Never reuse IDs.

| ID | Category | Upstream location | Our location | Change | Rationale | Sync risk |
|---|---|---|---|---|---|---|
| D-001 | Schema | `grading.json` (prose) | `references/schemas/grading.schema.json` | Required field `assertion_id` | Set-equality gate across candidate/baseline | Upstream grader prompts won't emit it — keep our grader prompt updated |
| D-002 | Schema | same | same | Optional field `critical` | Drives `max_critical_failures` threshold | Same |
| D-003 | Scripts | *(none — new)* | `scripts/check_iteration.py` | New Phase D gate | Machine-enforces what upstream does in prose | No upstream conflict |
| D-004 | Scripts | *(none — new)* | `scripts/check_promotion.py` | New Phase F gate | Same | Same |
| D-005 | Architecture | `claude -p` calls in `run_eval.py`, `improve_description.py`, `run_loop.py` | Routed through `adapters/<agent>/adapter.py` | Adapter indirection | Agent-agnostic core | Future upstream refactors re-route through adapter |
| D-006 | Metrics | `tokens` from Claude API response | `tokens: null` for Cursor | Cursor CLI `stream-json` exposes `duration_ms`+`duration_api_ms` but no token fields (verified `cursor.com/docs/cli/reference/output-format`, April 2026) | Aggregation handles null throughout | Re-verify on each sync; three open feature requests |
| D-007 | Frontmatter | `allowed-tools` first-class | Claude Code: allowed (official per `code.claude.com/docs/en/skills`); Cursor: rejected (absent from `cursor.com/docs/skills`) | Matches each agent's spec | Frontmatter validator is adapter-driven | No core bias |
| D-008 | Layout | `eval-viewer/` at skill root | `eval-harness/viewer/` nested | User-requested organization | Only path differs; filenames identical | Sync matches by filename |
| D-009 | Agent prompt | `agents/grader.md` restates schema inline | References `references/schemas/grading.schema.json` | Single source of truth | Upstream grader-prompt updates must preserve the reference link |
| D-010 | Layout | Upstream has no tests (verified) | `<repo-root>/tests/create-agent-skill/` | Additive | Anthropic spec: tests external | No conflict |
| D-011 | Environment | N/A | Cursor CLI version not pinned | Adapter logs detected CLI version on first invocation; parse-best-effort with warnings if schema differs | Honest about version drift risk |
