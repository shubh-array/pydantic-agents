# create-agent-skill

A meta-skill for **authoring, evaluating, and iteratively improving** agent skills for coding agents (Cursor CLI, Claude Code, …). It ships an adapter-backed evaluation harness that runs your candidate skill against a baseline, grades the outputs against machine-checkable assertions, and gates promotion on configurable thresholds.

This document is for two audiences:

1. **Users** who want to build a new skill with this tool and need to know what files are produced at every step so they can compare their own run against a known-good reference.
2. **Developers** who are extending this skill itself (adding adapters, tweaking the harness, evolving schemas).

Everything shown below is the **real output** of a simulated run against the Cursor CLI agent. If your run produces a materially different layout or missing files, something is off.

---

## Contents

1. [What the skill is](#what-the-skill-is)
2. [Architecture](#architecture)
3. [Workflow and phase map](#workflow-and-phase-map)
4. [Data contracts and schemas](#data-contracts-and-schemas)
5. [End-to-end example: the `finance-variance` skill, 3 iterations](#end-to-end-example-the-finance-variance-skill-3-iterations)
   1. [Iteration 1 — baseline dual run](#iteration-1--baseline-dual-run)
   2. [Iteration 2 — expand the eval set](#iteration-2--expand-the-eval-set)
   3. [Iteration 3 — improve the body, compare against `old_skill`](#iteration-3--improve-the-body-compare-against-old_skill)
6. [Defaults and policy](#defaults-and-policy)
7. [Troubleshooting](#troubleshooting)

---

## What the skill is

`create-agent-skill` is a skill that teaches an agent how to turn a fuzzy intent ("I want a skill for X") into a production-grade skill with:

- A clean `SKILL.md` that triggers reliably.
- A machine-checked eval set (`evals/evals.json`).
- Quantitative proof that the skill actually helps (pass-rate lift over a baseline agent).
- A deterministic package (`.skill` zip) ready to install.

It does this by running two agents side by side on every eval: one **with** the skill loaded, one **without** (or against an **old snapshot**). The delta is the skill's contribution.

## Architecture

```
.cursor/skills/create-agent-skill/
├── SKILL.md                    # Meta-skill instructions (read by the driving agent)
├── README.md                   # This file
├── config/
│   ├── active_agent            # Single line: which adapter to use (e.g. "cursor")
│   └── thresholds.json         # Promotion thresholds (lift, pass rate, critical failures)
├── adapters/                   # Agent-specific subprocess + transcript parsing
│   ├── base.py                 #   Adapter protocol (invoke_subagent, evaluate_trigger, ...)
│   ├── cursor/                 #   Cursor CLI (`agent`) implementation
│   └── claude_code/            #   Claude Code CLI (`claude -p`) implementation
├── agents/                     # Reusable agent prompts
│   ├── executor.md             #   Default dual-run executor (supports {{SKILL_CONTENT}}, {{USER_INPUT}})
│   ├── grader.md               #   Per-run assertion grading
│   ├── comparator.md           #   Blind A/B comparison
│   └── analyzer.md             #   Post-hoc benchmark analysis
├── eval-harness/
│   ├── scripts/                # Phase C–D commands (run_eval, aggregate_benchmark, ...)
│   └── viewer/                 # Phase E HTML viewer (live or --static)
├── scripts/                    # Phase A, D', F commands (validate, gate, package)
└── references/
    ├── execution-contract.md   # The phase→command map
    ├── evaluation.md           # What "dual run" means
    ├── getting-started.md      # Adapter selection
    └── schemas/                # JSON schemas — the source of truth for every artifact
        ├── evals.schema.json
        ├── eval_metadata.schema.json
        ├── grading.schema.json
        ├── benchmark.schema.json
        ├── feedback.schema.json
        ├── timing.schema.json
        └── iteration.schema.json
```

**Core invariant:** core code (everything under `eval-harness/` and `scripts/`) depends only on `adapters/base.py::Adapter`. Agent-specific details (CLI flags, transcript parsing, tokens reporting) live inside `adapters/<name>/`, so adding support for a new agent is ~1 file.

**Skill isolation contract.** The default executor template `agents/executor.md` contains `{{SKILL_CONTENT}}`. The harness substitutes:

| Side            | `{{SKILL_CONTENT}}` value                   |
|-----------------|---------------------------------------------|
| `with_skill`    | Candidate skill's `SKILL.md` (full content) |
| `without_skill` | Empty string                                |
| `old_skill`     | Prior snapshot's `SKILL.md`                 |

This is what makes the comparison meaningful: the baseline agent genuinely does not see the skill.

## Workflow and phase map

All commands run with the create-agent-skill root as the current working directory so imports resolve.

| Phase | What happens                                                 | Command                                                                                                                      |
|-------|--------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| **A** | Validate `SKILL.md` frontmatter + `evals/evals.json` schema  | `python scripts/quick_validate.py <skill-path>`                                                                              |
| **B** | Author `evals/evals.json` (inputs + expectations)            | (manual edit; validated in A)                                                                                                |
| **C** | Description-trigger eval (optional, for frontmatter tuning)  | `python eval-harness/scripts/run_eval.py trigger --eval-set <file> --skill-path <skill>`                                     |
| **C′**| Dual execution (`with_skill` vs baseline, via the adapter)   | `python eval-harness/scripts/run_eval.py dual --iteration N --workspace <ws>`                                                |
| **D** | Aggregate gradings into `benchmark.json` / `benchmark.md`    | `python eval-harness/scripts/aggregate_benchmark.py --iteration N --workspace <ws> --skill-name <n> --skill-path <p>`        |
| **D′**| Gate iteration artifacts (schemas + assertion-id parity)     | `python scripts/check_iteration.py --iteration N --workspace <ws>`                                                           |
| **E** | Human review — live browser viewer or static HTML            | `python eval-harness/viewer/generate_review.py <ws> --iteration N --skill-name <n> --benchmark <ws>/iteration-N/benchmark.json [--static <path>]` |
| **F** | Promotion gate (`config/thresholds.json`)                    | `python scripts/check_promotion.py --iteration N --workspace <ws>`                                                           |

The description-optimization loop (`run_loop.py`) is a different code path used *after* the body is good. It now defaults to **3 iterations** — see [Defaults and policy](#defaults-and-policy).

Workspace layout produced by the harness:

```
<skill-name>-workspace/
├── iteration-1/
│   ├── iteration.json          # Manifest (schema: iteration.schema.json) — author writes this
│   ├── benchmark.json          # Aggregated results  (schema: benchmark.schema.json)
│   ├── benchmark.md            # Human-readable table
│   ├── review.html             # Phase E static viewer (if --static used)
│   ├── feedback.json           # Human feedback       (schema: feedback.schema.json)
│   └── <eval-id>/
│       ├── eval_metadata.json  # Per-eval metadata    (schema: eval_metadata.schema.json)
│       ├── with_skill/
│       │   └── run-1/
│       │       ├── outputs/    # Files the agent produced (whatever the skill dictates)
│       │       ├── transcript.jsonl   # stream-json log of the agent run
│       │       ├── timing.json        # schema: timing.schema.json
│       │       └── grading.json       # schema: grading.schema.json
│       └── without_skill/      # (or old_skill/)
│           └── run-1/          # Same structure
├── iteration-2/
└── iteration-3/
```

Notice the skill directory (`finance-variance/` in the example) is **separate** from the workspace (`finance-variance-workspace/`). Evaluation artifacts never land inside the skill — the skill stays shippable.

## Data contracts and schemas

Every artifact written by the harness is validated against a JSON Schema. If your pipeline writes malformed JSON, Phase D′ (`check_iteration.py`) will reject the iteration with a line number. The schemas live in `references/schemas/`:

| Artifact                    | Schema                          | Produced by                             |
|-----------------------------|---------------------------------|-----------------------------------------|
| `evals/evals.json`          | `evals.schema.json`             | Author (manual)                         |
| `iteration-N/iteration.json`| `iteration.schema.json`         | Author (manual)                         |
| `eval_metadata.json`        | `eval_metadata.schema.json`     | `run_eval.py dual`                      |
| `timing.json`               | `timing.schema.json`            | `run_eval.py dual`                      |
| `grading.json`              | `grading.schema.json`           | Grader subagent or deterministic script |
| `benchmark.json`            | `benchmark.schema.json`         | `aggregate_benchmark.py`                |
| `feedback.json`             | `feedback.schema.json`          | Human via viewer                        |

---

## End-to-end example: the `finance-variance` skill, 3 iterations

This section is the real run that was used to validate this skill. Every JSON snippet and every number below was copied directly from `/tmp/cas-sim/finance-variance-workspace/`.

**Goal.** Build a skill called `finance-variance` that, given a CSV of `category,budget,actual`, produces a `variance.csv` with columns `category,budget,actual,variance,variance_pct`.

**Setup.**

```
/tmp/cas-sim/
├── input-q1.csv                 # Simple input (no quoting, no formatting)
├── input-q1-edge.csv            # Quoted categories with commas/ampersands (iteration 2)
├── input-q1-thousands.csv       # Thousands-separators in numbers      (iteration 3)
├── finance-variance/            # The skill under test
│   ├── SKILL.md
│   └── evals/evals.json
├── finance-variance-v1/         # Snapshot of v1 (used as old_skill in iteration 3)
└── finance-variance-workspace/  # All evaluation artifacts land here
```

Phase A runs once up front and any time you edit the skill:

```bash
$ uv run python scripts/quick_validate.py /tmp/cas-sim/finance-variance
Skill is valid!
```

---

### Iteration 1 — baseline dual run

**Goal of the iteration.** Prove the skill's value against "no skill at all" on the simplest possible input.

**`evals/evals.json`** (1 case):

```json
[
  {
    "id": "fv-1",
    "prompt": "Produce a budget variance report for /tmp/cas-sim/input-q1.csv.",
    "expectations": [
      {"assertion_id": "variance-csv-exists", "text": "variance.csv exists in outputs/", "critical": true},
      {"assertion_id": "header-correct",      "text": "variance.csv first line is exactly 'category,budget,actual,variance,variance_pct'", "critical": true},
      {"assertion_id": "row-count",           "text": "variance.csv has the same row count as input (plus header)", "critical": true},
      {"assertion_id": "variance-math",       "text": "For every row, variance equals actual - budget", "critical": true}
    ],
    "files": ["/tmp/cas-sim/input-q1.csv"]
  }
]
```

**`iteration-1/iteration.json`:**

```json
{
  "skill_path": "/tmp/cas-sim/finance-variance",
  "evals_path": "/tmp/cas-sim/finance-variance/evals/evals.json",
  "baseline_type": "without_skill",
  "runs_per_configuration": 1,
  "iteration": 1,
  "notes": "Initial dual run: finance-variance v1 vs no skill."
}
```

**Phase C′ — dual execution:**

```bash
$ uv run python eval-harness/scripts/run_eval.py dual \
    --iteration 1 \
    --workspace /tmp/cas-sim/finance-variance-workspace \
    --timeout 180
```

This single command produced the entire subtree below it — no extra files, no files in the skill directory:

```
iteration-1/
├── iteration.json
└── fv-1/
    ├── eval_metadata.json
    ├── with_skill/run-1/
    │   ├── outputs/
    │   │   ├── variance.csv    # ← candidate's output
    │   │   └── variance.py     # ← the agent also wrote the helper script
    │   ├── timing.json
    │   └── transcript.jsonl
    └── without_skill/run-1/
        ├── outputs/
        │   ├── generate_report.py
        │   ├── variance_report.csv    # ← different file name — baseline guessed
        │   └── variance_report.md
        ├── timing.json
        └── transcript.jsonl
```

`variance.csv` from `with_skill/run-1/outputs/`:

```csv
category,budget,actual,variance,variance_pct
marketing,10000,12500,2500,25
engineering,50000,47800,-2200,-4.4
sales,20000,23200,3200,16
support,8000,8000,0,0
travel,0,1200,1200,n/a
```

`variance_report.csv` from `without_skill/run-1/outputs/` (note the extra `status` column, TOTAL row, and wrong file name — the baseline invented its own schema):

```csv
category,budget,actual,variance,variance_pct,status
marketing,10000.00,12500.00,2500.00,25.00%,Over budget
engineering,50000.00,47800.00,-2200.00,-4.40%,Under budget
…
TOTAL,88000.00,92700.00,4700.00,5.34%,Over budget
```

**`timing.json`** (with_skill/run-1):

```json
{
  "total_duration_seconds": 17.487,
  "total_duration_api_seconds": 17.487,
  "total_tokens": 864,
  "tokens_detail": {
    "input": 9,
    "output": 855,
    "cacheReadTokens": 76637,
    "cacheWriteTokens": 3708
  },
  "status": "ok",
  "exit_code": 0
}
```

**Phase 4 — grade each run.** For this skill all four assertions are deterministic, so the grader is a short Python script (committed at `/tmp/cas-sim/grade.py` in the simulation). Output for `with_skill/run-1` (`grading.json`):

```json
{
  "expectations": [
    {"assertion_id": "variance-csv-exists", "text": "variance.csv exists in outputs/", "passed": true,  "evidence": ".../variance.csv exists",              "critical": true},
    {"assertion_id": "header-correct",      "text": "variance.csv first line is exactly 'category,budget,actual,variance,variance_pct'", "passed": true, "evidence": "observed header: 'category,budget,actual,variance,variance_pct'", "critical": true},
    {"assertion_id": "row-count",           "text": "variance.csv has the same row count as input (plus header)", "passed": true, "evidence": "input rows=5, output data rows=5", "critical": true},
    {"assertion_id": "variance-math",       "text": "For every row, variance equals actual - budget", "passed": true, "evidence": "all rows consistent", "critical": true}
  ],
  "summary": {"pass_rate": 1.0, "passed": 4, "failed": 0, "total": 4}
}
```

The `without_skill/run-1/grading.json` is the mirror image — `variance-csv-exists` fails because the baseline named the file `variance_report.csv`, and the remaining three cascade to `false`.

**Phase D — aggregate:**

```bash
$ uv run python eval-harness/scripts/aggregate_benchmark.py \
    --iteration 1 \
    --workspace /tmp/cas-sim/finance-variance-workspace \
    --skill-name finance-variance \
    --skill-path /tmp/cas-sim/finance-variance
```

Resulting `benchmark.json` `run_summary` block (real numbers from the simulation):

```json
{
  "with_skill": {
    "pass_rate":    {"mean": 1.0,   "stddev": 0.0, "min": 1.0,   "max": 1.0},
    "time_seconds": {"mean": 17.49, "stddev": 0.0, "min": 17.49, "max": 17.49},
    "tokens":       {"mean": 864,   "stddev": 0,   "min": 864,   "max": 864}
  },
  "without_skill": {
    "pass_rate":    {"mean": 0.0,   "stddev": 0.0, "min": 0.0,   "max": 0.0},
    "time_seconds": {"mean": 40.87, "stddev": 0.0, "min": 40.87, "max": 40.87},
    "tokens":       {"mean": 2927,  "stddev": 0,   "min": 2927,  "max": 2927}
  },
  "delta": {
    "pass_rate": "+1.00",
    "time_seconds": "-23.4",
    "tokens": "-2063"
  }
}
```

**`benchmark.md`** renders as:

```
| Metric    | With Skill      | Without Skill   | Delta   |
|-----------|-----------------|-----------------|---------|
| Pass Rate | 100% ± 0%       | 0% ± 0%         | +1.00   |
| Time      | 17.5s ± 0.0s    | 40.9s ± 0.0s    | -23.4s  |
| Tokens    | 864 ± 0         | 2927 ± 0        | -2063   |
```

**Phase D′ — gate:** `check_iteration.py --iteration 1 …` exits 0.

**Phase E — static viewer:**

```bash
$ uv run python eval-harness/viewer/generate_review.py \
    /tmp/cas-sim/finance-variance-workspace \
    --iteration 1 \
    --skill-name finance-variance \
    --benchmark /tmp/cas-sim/finance-variance-workspace/iteration-1/benchmark.json \
    --static /tmp/cas-sim/finance-variance-workspace/iteration-1/review.html
```

`review.html` is ~58 KB of self-contained HTML — no server required.

**`feedback.json`** (written by the user through the viewer, or by hand):

```json
{
  "status": "complete",
  "reviews": [
    {"run_id": "fv-1-with_skill-run-1",    "feedback": "Correct output shape and values. Skill clearly produces the exact header and formulas. No issues.",                                     "timestamp": "2026-04-21T20:45:00Z"},
    {"run_id": "fv-1-without_skill-run-1", "feedback": "Without the skill, the agent invents its own file name (variance_report.csv) and adds extra columns/totals. Confirms skill value.", "timestamp": "2026-04-21T20:45:30Z"}
  ]
}
```

**Phase F — promotion gate:** `check_promotion.py --iteration 1 …` exits 0 (candidate pass 100% ≥ 85%, lift +100pp ≥ 10pp, 0 critical failures, feedback complete).

✅ Iteration 1 is shippable on the happy path. Move on to expand the eval set.

---

### Iteration 2 — expand the eval set

**Goal.** Add an edge case (`fv-2`) with quoted categories containing commas/ampersands. Does the skill still hold up, and does the baseline?

**Change:** append `fv-2` to `evals/evals.json` (+1 new assertion `quoted-categories-preserved`). Skill body is **unchanged** — we want to see what the capable agent does with the existing prose.

**`iteration-2/iteration.json`** (identical to iteration 1 except for `iteration` and `notes`):

```json
{
  "skill_path": "/tmp/cas-sim/finance-variance",
  "evals_path": "/tmp/cas-sim/finance-variance/evals/evals.json",
  "baseline_type": "without_skill",
  "runs_per_configuration": 1,
  "iteration": 2,
  "notes": "Added fv-2 (CSV with quoted categories containing commas/ampersands). Skill body unchanged from iteration 1."
}
```

Run the same four phases. `benchmark.md`:

```
| Metric    | With Skill      | Without Skill    | Delta   |
|-----------|-----------------|------------------|---------|
| Pass Rate | 100% ± 0%       | 50% ± 71%        | +0.50   |
| Time      | 19.6s ± 0.8s    | 38.8s ± 4.7s     | -19.1s  |
| Tokens    | 862 ± 9         | 2619 ± 1030      | -1758   |
```

Real `delta` block from `benchmark.json`:

```json
{"delta": {"pass_rate": "+0.50", "time_seconds": "-19.1", "tokens": "-1758"}}
```

**What the numbers tell you.** The skill held up on both cases (100%). The baseline got lucky on `fv-1` — it happened to write a file named `variance.csv` this time — but on `fv-2` it reverted to its own schema (`variance_report.csv` + status column) and scored 0%. The high stddev on the without_skill column (±71%) is the tell that the baseline is inconsistent; once you see that, you know the skill is buying you **determinism**, not just peak accuracy.

This is also the iteration where you'd typically make the `evals/evals.json` stricter. We added `quoted-categories-preserved` here as a forcing function for iteration 3.

---

### Iteration 3 — improve the body, compare against `old_skill`

**Goal.** Add a harder edge case (`fv-3`: thousands-separators in numbers), then improve the skill body to explicitly handle it. Use `old_skill` as the baseline to measure the lift of the **change**, not the lift of the skill vs nothing.

**Step 1 — snapshot v1:**

```bash
cp -r /tmp/cas-sim/finance-variance /tmp/cas-sim/finance-variance-v1
```

**Step 2 — edit `/tmp/cas-sim/finance-variance/SKILL.md`.** The diff vs v1 in plain English:

- Description: mention thousand-separators, quoted categories, zero-budget rows.
- Body: add a numeric-normalization step ("strip commas, spaces, and leading currency symbols before `float(...)`").
- Add a "Why these rules matter" section reinforcing the header contract.

**Step 3 — add `fv-3` to `evals/evals.json`** using `/tmp/cas-sim/input-q1-thousands.csv`.

**Step 4 — write `iteration-3/iteration.json`** with the **new** baseline:

```json
{
  "skill_path": "/tmp/cas-sim/finance-variance",
  "old_skill_path": "/tmp/cas-sim/finance-variance-v1",
  "evals_path": "/tmp/cas-sim/finance-variance/evals/evals.json",
  "baseline_type": "old_skill",
  "runs_per_configuration": 1,
  "iteration": 3,
  "notes": "Improved skill body: normalization guidance + header-contract reinforcement. Baseline = v1 snapshot to measure the lift of the improvement itself."
}
```

The harness validates this against `iteration.schema.json` before any runs start. If you forget `old_skill_path` when `baseline_type=old_skill`, it fails immediately with a clear error:

```
iteration.json schema error: 'old_skill_path' is a required property
```

**Step 5 — run the dual.** Six runs this time (3 evals × 2 sides). Each takes ~17–20 s with Cursor CLI, total ~2 minutes.

```bash
$ uv run python eval-harness/scripts/run_eval.py dual \
    --iteration 3 \
    --workspace /tmp/cas-sim/finance-variance-workspace \
    --timeout 180
```

Layout after the run (abridged):

```
iteration-3/
├── iteration.json
├── fv-1/
│   ├── with_skill/run-1/…
│   └── old_skill/run-1/…
├── fv-2/{with_skill,old_skill}/run-1/…
└── fv-3/
    ├── with_skill/run-1/outputs/variance.csv
    └── old_skill/run-1/outputs/variance.csv
```

**Real result:** both the new skill and v1 produced valid `variance.csv` files for `fv-3` — the executor agent is capable enough to infer the thousands-separator normalization without explicit guidance. The improvement didn't move the pass-rate needle.

`benchmark.md`:

```
| Metric    | With Skill       | Old Skill       | Delta   |
|-----------|------------------|-----------------|---------|
| Pass Rate | 100% ± 0%        | 100% ± 0%       | +0.00   |
| Time      | 19.1s ± 2.1s     | 17.6s ± 0.6s    | +1.5s   |
| Tokens    | 918 ± 107        | 839 ± 20        | +79     |
```

**Phase F — promotion gate intentionally blocks this iteration:**

```bash
$ uv run python scripts/check_promotion.py --iteration 3 --workspace …
lift 0.0 pp < min 10 pp
exit=1
```

This is the **correct** behavior. The thresholds (`config/thresholds.json`) require a 10pp lift over the baseline; this change didn't deliver it. Realistic decisions from here:

1. **Keep the change** as a defensive improvement (the wording will hold up on future, harder inputs), but don't claim credit for it. Log the result in the iteration `notes`.
2. **Revert** because the +1.5 s / +79 token overhead isn't worth zero pass-rate gain.
3. **Harden the eval set** (more cases with missing columns, mixed currencies, etc.) until the difference surfaces, then re-run.

The gate is meant to make that conversation explicit.

**Phase — package** (once you're happy):

```bash
$ uv run python scripts/package_skill.py /tmp/cas-sim/finance-variance /tmp/cas-sim/dist
🔍 Validating skill...
✅ Skill is valid!
  Added: finance-variance/SKILL.md
  Skipped: finance-variance/evals/evals.json
✅ Successfully packaged skill to: /tmp/cas-sim/dist/finance-variance.skill
```

`evals/` is **intentionally excluded** from the package — evals are for development, not end users.

---

## Defaults and policy

- **`--max-iterations 3`** (in `run_loop.py` for description optimization, and as the recommended convention for body iteration). Three iterations is enough to get past the obvious wins without overfitting the training split. Raise it only with a concrete reason.
- **Promotion thresholds** (`config/thresholds.json`):
  ```json
  {
    "min_candidate_pass_rate": 0.85,
    "min_lift_vs_baseline_pp": 10,
    "max_critical_failures": 0,
    "require_feedback_complete": true
  }
  ```
- **Active adapter** (`config/active_agent`): single line, currently `cursor`. Switch to `claude_code` to run the same harness against Claude Code with no other change.
- **Skill isolation**: enforced by `{{SKILL_CONTENT}}` substitution in `agents/executor.md`. If you write a custom `agent_prompt`, it **must** include this placeholder or isolation is lost.

## Troubleshooting

| Symptom                                                                         | Likely cause                                                         |
|---------------------------------------------------------------------------------|----------------------------------------------------------------------|
| `iteration.json schema error: …`                                                | Missing a required field (e.g. `old_skill_path` with `old_skill`).   |
| `missing iteration-N/benchmark.json`                                            | You skipped Phase D or it failed. Re-run `aggregate_benchmark.py`.   |
| `benchmark.json schema: None is not of type 'integer'` (on older revisions)     | You're on a pre-fix schema. Pull the latest — `tokens` now allows `null`. |
| `assertion_id mismatch in fv-X: with_skill#1=[…] vs without_skill#1=[…]`        | Your grader emitted different assertion sets per side. Always emit the full set, with `passed=false` when the artifact is missing. |
| `ModuleNotFoundError: No module named 'scripts'` from `package_skill.py`        | Old revision; fixed by the `sys.path` bootstrap at the top of the script. |
| `without_skill` suspiciously scores the same as `with_skill`                     | Check the adapter is actually receiving `skill_content=None` for the baseline (`fake_adapter.invocations` in tests verifies this). |
| Trigger eval returns `False` even for obvious matches                           | Adapter's `evaluate_trigger` reads assistant text, not stdout. Ensure the CLI is emitting `stream-json` and a final `result` event. |

---

## For contributors

- Add a new agent: create `adapters/<name>/{adapter.py,config.json,recipes.md}`, implement the `Adapter` protocol (8 methods/attrs), run `pytest tests/create-agent-skill/unit -k adapter` to verify protocol compliance.
- Add a new schema: drop `<name>.schema.json` under `references/schemas/`, wire validation into `check_iteration.py` (for per-run artifacts) or the producing script, and add a round-trip test to `tests/create-agent-skill/unit/test_schemas.py`.
- Change an agent prompt: keep it templated on `{{USER_INPUT}}` and `{{SKILL_CONTENT}}` if it's for dual execution.

Run the full suite before a PR:

```bash
uv run pytest tests/create-agent-skill -q
```

---

*Everything in the end-to-end example is reproducible against Cursor CLI `2026.04.17-787b533` or later. If your numbers differ by more than ±20 %, suspect a CLI change first and an environment issue second.*
