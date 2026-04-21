# Execution contract (phase → command)

Run all commands with the skill root as cwd (`.cursor/skills/create-agent-skill/`) so imports resolve.

Dual runs use side directories **`with_skill`**, **`without_skill`**, and **`old_skill`** under each eval (see **`references/evaluation.md`**). The dual manifest **`iteration-N/iteration.json`** sets **`baseline_type`** to **`without_skill`** or **`old_skill`**, and is schema-validated against **`references/schemas/iteration.schema.json`** before any runs start.

The default executor template **`agents/executor.md`** supports `{{USER_INPUT}}` and `{{SKILL_CONTENT}}`. The harness substitutes the candidate SKILL.md for `with_skill`, the snapshot SKILL.md for `old_skill`, and an empty string for `without_skill` — this is how skill isolation is enforced.

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
