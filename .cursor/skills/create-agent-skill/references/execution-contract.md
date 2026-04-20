# Execution contract (phase → command)

Run all commands with the skill root as cwd (`.cursor/skills/create-agent-skill/`) so imports resolve.

| Phase | Command |
|-------|---------|
| **A** Preflight | `python scripts/quick_validate.py <path-to-skill-under-test>` |
| **B** Eval JSON | Author `evals/evals.json`; validate against `references/schemas/evals.schema.json` |
| **C** Trigger eval | `python eval-harness/scripts/run_eval.py trigger --eval-set <file> --skill-path <skill>` |
| **C′** Dual scaffold | `python eval-harness/scripts/run_eval.py dual --iteration N --workspace <ws>` (requires `iteration-N/iteration.json`) |
| **D** Aggregate | `python eval-harness/scripts/aggregate_benchmark.py --iteration N --workspace <ws>` |
| **D′** Gate | `python scripts/check_iteration.py --iteration N --workspace <ws>` |
| **E** Viewer | `python eval-harness/viewer/generate_review.py <ws> --iteration N` |
| **F** Promote | `python scripts/check_promotion.py --iteration N --workspace <ws>` |

Threshold numbers are **not** duplicated here; see `config/thresholds.json`.
