# Upstream sync guide (`skill-creator` ↔ `create-agent-skill`)

Use this guide when porting changes from upstream [`skill-creator`](../../.cursor/skills/skill-creator/) into [`create-agent-skill`](../../.cursor/skills/create-agent-skill/), or when verifying that local behavior still aligns with upstream intent.

## File mapping

| Upstream (`skill-creator`) | Local (`create-agent-skill`) |
| --- | --- |
| `SKILL.md` | `SKILL.md` (semantic parity, not word-for-word) |
| `scripts/run_eval.py` | `eval-harness/scripts/run_eval.py` |
| `scripts/run_loop.py` | `eval-harness/scripts/run_loop.py` |
| `scripts/aggregate_benchmark.py` | `eval-harness/scripts/aggregate_benchmark.py` |
| `scripts/improve_description.py` | `eval-harness/scripts/improve_description.py` |
| `scripts/generate_report.py` | `eval-harness/scripts/generate_report.py` |
| `eval-viewer/generate_review.py` | `eval-harness/viewer/generate_review.py` |
| `eval-viewer/viewer.html` | `eval-harness/viewer/viewer.html` |
| `references/schemas.md` | `references/schemas/*.schema.json` (6 files; see below) |
| `scripts/quick_validate.py` | `scripts/quick_validate.py` |
| `scripts/package_skill.py` | `scripts/package_skill.py` |
| `agents/grader.md` | `agents/grader.md` |
| `agents/comparator.md` | `agents/comparator.md` |
| `agents/analyzer.md` | `agents/analyzer.md` |
| `assets/eval_review.html` | `assets/eval_review.html` |

### Schema split (single upstream doc → six JSON Schemas)

Upstream `references/schemas.md` maps to these local files under `references/schemas/`:

| Local schema file |
| --- |
| `evals.schema.json` |
| `eval_metadata.schema.json` |
| `grading.schema.json` |
| `benchmark.schema.json` |
| `feedback.schema.json` |
| `timing.schema.json` |

## Files unique to `create-agent-skill`

No upstream equivalent; do not expect a 1:1 diff from `skill-creator`:

- `adapters/` (entire adapter system)
- `config/active_agent`, `config/thresholds.json`
- `scripts/check_iteration.py`, `scripts/check_promotion.py`
- `references/execution-contract.md`, `references/evaluation.md`, `references/getting-started.md`

## Sync checklist

1. **Mapped scripts and assets:** For each row in the file mapping table, compare **behavior** (not word-for-word) with upstream. Pay attention to CLI entry points, file I/O, and error handling.
2. **Schemas:** Compare all six JSON Schemas against `skill-creator/references/schemas.md` for new fields, renamed properties, and required vs optional changes:
   - `evals.schema.json`
   - `eval_metadata.schema.json`
   - `grading.schema.json`
   - `benchmark.schema.json`
   - `feedback.schema.json`
   - `timing.schema.json`  
   Reconcile any intentional differences with [upstream-deltas.md](./upstream-deltas.md).
3. **Deltas:** Review `upstream-deltas.md` and confirm each **Active** divergence still applies after the sync; update or retire entries as needed.
4. **Tests:** Run the full create-agent-skill test suite:
   ```bash
   uv run python -m pytest tests/create-agent-skill/ -v
   ```
5. **Document:** Update `upstream-deltas.md` with any new intentional divergences discovered during the sync.
