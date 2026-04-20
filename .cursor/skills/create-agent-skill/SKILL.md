---
name: create-agent-skill
description: >-
  Guides users through creating effective Agent Skills for Cursor. Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create, write, or author a new skill from scratch, edit, or optimize an existing skill, run evals to test a skill, benchmark skill performance with variance analysis, or optimize a skill's description for better triggering accuracy.
---

# Creating Agent Skills

Combines concise Cursor-style `SKILL.md` authoring with a fixed, gated evaluation workflow. This document is the workflow contract: follow phases **A → F** in order for every iteration. Do not skip phases, merge partial iterations, or promote without meeting **all** promotion thresholds.

## Non-negotiable policies

1. **Full evaluation pipeline (mandatory)** — Every skill iteration runs the complete sequence: preflight → eval definition → dual execution (candidate + baseline) → deterministic grading → aggregation → eval viewer → human feedback capture → promotion check. There is no “evals optional” path for production promotion.
2. **Contextual baseline (mandatory)** — Baseline is chosen only from this table:

   | Skill situation | Baseline |
   |-----------------|----------|
   | New skill | `without_skill` (no skill path; same prompts and inputs as candidate) |
   | Improving an existing skill | Previous or original skill snapshot: copy the pre-edit skill tree to `<workspace>/skill-snapshot/` before any candidate edit; baseline runs load **only** that snapshot |

3. **Isolation (mandatory)** — Candidate and baseline runs use **separate** output roots under the same eval directory. Shared rules: identical immutable prompt and input files for both sides; **no** shared scratch directory; **no** cross-side read or write of generated artifacts (each side reads only shared inputs and its own output tree).
4. **Promotion thresholds (mandatory, numeric)** — Promotion is allowed **only if all** are true:

   - With-skill pass rate **≥ 0.85** (fraction in `[0,1]` from `benchmark.json` `run_summary.with_skill.pass_rate.mean`)
   - Lift **≥ 0.10** (same units: `run_summary.with_skill.pass_rate.mean` minus `run_summary.<baseline_key>.pass_rate.mean`, where `<baseline_key>` is `without_skill` or `old_skill`)
   - **Critical assertion failures = 0** — computed only by the rule in “Critical assertions (machine check)” (not inferred from prose feedback)

## Required scripts (v1 toolchain; local to create-agent-skill)

All of the following must exist under `.cursor/skills/create-agent-skill/`. Invoke from that directory unless the repo documents a different local root.

| Script | When to invoke |
|--------|----------------|
| `scripts/quick_validate.py` | Phase A only: `python3 scripts/quick_validate.py <skill_directory>` |
| `scripts/run_eval.py` | When measuring **description** trigger rate via `claude -p`; never replaces Phase C skill-task dual runs |
| `scripts/aggregate_benchmark.py` | Phase D: `python3 -m scripts.aggregate_benchmark <workspace>/iteration-<N> --skill-name <name>` |
| `eval-viewer/generate_review.py` | Phase E: mandatory viewer generation |
| `scripts/package_skill.py` | After promotion when distributing a `.skill` bundle |

Phase C dual execution uses agent/subagent (or sequential equivalent) task runs with identical prompts and inputs; it does **not** use `run_eval.py` for those runs.

## Required artifacts per iteration (hybrid harness layout)

Root: skill workspace (e.g. `<skill-name>-workspace/`), iteration `iteration-<N>/`, `<N>` a positive integer.

**Eval suite source of truth:** `evals/evals.json` (skill tree or workspace; must stay in sync with disk `eval-*` dirs).

**Iteration root (required files):**

- `iteration-<N>/benchmark.json`
- `iteration-<N>/benchmark.md`
- `iteration-<N>/feedback.json`

**Per-eval directories:** `iteration-<N>/eval-<eval_id>/` where `<eval_id>` is the decimal integer string of `evals[].id` from `evals/evals.json` (example: id `3` → directory `eval-3`). Names **must** match `aggregate_benchmark.py`’s `eval-*` glob.

Under each `eval-<eval_id>/`:

- `with_skill/run-<M>/` — candidate configuration (`<M>` starts at `1`; additional runs use `run-2`, …)
- `<baseline-side>/run-<M>/` — baseline configuration, **same** `<M>` pairing as candidate for that eval

**`<baseline-side>`:** `without_skill` (new skill) or `old_skill` (improvement); matches aggregator conventions.

**Required inside every `run-*` directory (both sides):**

- `outputs/` — directory (viewer treats a path as a run only if `outputs/` exists)
- `eval_metadata.json`
- `grading.json`
- `timing.json`

**`eval_metadata.json` (required keys):** `eval_id` (int, equals parent dir’s `<eval_id>`), `prompt` (string), `assertions` (array). Each element of `assertions` **must** be an object with:

- `id` — stable string slug (unique within that eval)
- `text` — assertion text the grader uses
- `critical` — boolean; `true` means failure blocks promotion when machine-checked

Candidate and baseline runs for the same eval **must** use the **same** `assertions` list (same `id`, `text`, `critical` values).

**`grading.json` structure (required):** top-level object with:

- `summary` object including at least `total`, `passed`, `failed`, and `pass_rate` (float in `[0,1]`), consistent with the `expectations` array
- `expectations` array of objects

Each object in `expectations` **must** include `text`, `passed`, `evidence`, and **`assertion_id`** (string, must equal the `id` of the matching entry in that run’s `eval_metadata.json` `assertions`). The set of `assertion_id` values in `grading.json` `expectations` **must** equal the set of `id` values in that run’s `eval_metadata.json` `assertions` (same cardinality, no extras, no omissions).

**Hybrid schema extension note (required):** `.cursor/skills/create-agent-skill/references/schemas.md` and `.cursor/skills/create-agent-skill/agents/grader.md` define the baseline grader/viewer shape (`text`, `passed`, `evidence`). This hybrid workflow adds `assertion_id` as a required field for deterministic ID matching and critical-failure counting. When they conflict, this workflow’s contract supersedes those reference examples for hybrid runs.

## Critical assertions (machine check)

**Source of truth for criticality:** `critical` on each object in `eval_metadata.json` → `assertions` (per run directory).

**Algorithm (execute before declaring Phase F pass):** Initialize `crit_failures = 0`. For every directory `iteration-<N>/eval-*/with_skill/run-*`:

1. Read `eval_metadata.json` and `grading.json` in that same `run-*` directory.
2. Let `C = { assertions[i].id | assertions[i].critical is true }`.
3. For each object `e` in `grading.json` → `expectations` where `e.assertion_id` ∈ `C`, if `e.passed` is `false`, increment `crit_failures`.

**Promotion rule:** `crit_failures` **must equal 0**. If any `with_skill` run is missing `assertions`, `critical`, `assertion_id`, or set mismatch between metadata ids and grading ids, **block promotion** and treat as Phase D validation failure.

## Phased workflow (hard gates A–F)

**Global iteration rule:** For every `evals[].id` present in `evals/evals.json`, a directory `iteration-<N>/eval-<id>/` **must** exist. Under it, `with_skill/` and `<baseline-side>/` each **must** contain the same set of `run-*` names (e.g. both have `run-1`). Every `run-*` **must** include `outputs/`, `eval_metadata.json`, `grading.json`, and `timing.json`. If any path is missing, **invalidate the iteration** — do not aggregate, review, or promote; rerun Phase C onward.

### Phase A — Intent and draft gate

1. Record purpose, trigger contexts, and output contract in the conversation or a short intent note in the workspace.
2. Draft or update `SKILL.md` (and bundled files if needed).
3. Run from hybrid skill root: `python3 scripts/quick_validate.py <skill_directory>`.
4. **Pass:** preflight exits success.
5. **Block:** preflight fails → fix skill structure; **do not** enter Phase B until success.

### Phase B — Eval suite gate

1. **Directory ↔ source alignment:** For each object in `evals/evals.json` → `evals`, the workspace **must** contain `iteration-<N>/eval-<evals[].id>/` (decimal integer string; no zero-padding required). No extra `eval-*` directories for this iteration beyond those ids. Human-readable names or slugs belong **only** in JSON (e.g. optional `name` / `slug` fields), **not** in directory names (`eval-*` is always `eval-<id>` only).
2. Validate `evals/evals.json` against `.cursor/skills/create-agent-skill/references/schemas.md` and ensure each eval has the fields needed to construct prompts and metadata (`id`, `prompt` minimum).
3. **Baseline side:** Confirm the iteration will use `without_skill` (new skill) or `old_skill` (improvement) consistently under every `eval-<id>/`.
4. **Pass:** steps 1–3 succeed.
5. **Block:** orphan or missing `eval-*` dirs, id mismatch, schema errors, or wrong baseline side → fix; **do not** enter Phase C until resolved.

### Phase C — Dual execution gate

1. For **each** `eval-<id>/`, start candidate and baseline runs in the **same scheduling window** (same agent turn when subagents exist).
2. Persist artifacts only under `iteration-<N>/eval-<id>/<configuration>/run-<M>/` per “Required artifacts”.
3. Write `timing.json` when run completion metadata is available (capture immediately; do not batch in a way that drops data).
4. **Pass:** every required `run-*` path exists with `outputs/` populated for the eval’s paired runs.
5. **Block:** any missing `eval-*`, configuration side, `run-*`, or required file → iteration invalid; rerun Phase C.

### Phase D — Grading and aggregation gate

1. Grade each run deterministically; write `grading.json` in each `run-*` dir with `expectations` objects including `text`, `passed`, `evidence`, `assertion_id` (see “Required artifacts”).
2. Verify **before** aggregation: on every `with_skill/run-*`, `assertion_id` sets match metadata `assertions[].id` sets.
3. Run from hybrid skill root: `python3 -m scripts.aggregate_benchmark <workspace>/iteration-<N> --skill-name <name>`.
4. **Pass:** `benchmark.json` and `benchmark.md` exist at iteration root; `run_summary` includes `with_skill` and the baseline configuration key (`without_skill` or `old_skill`).
5. **Block:** set mismatch, missing `grading.json`/`timing.json`, or aggregation errors → fix; rerun Phase C or D as needed.

### Phase E — Human review gate

1. Run from hybrid skill root, with workspace = **iteration directory** (not workspace root):

   ```bash
   python3 eval-viewer/generate_review.py \
     <workspace>/iteration-<N> \
     --skill-name "<skill-name>" \
     --benchmark <workspace>/iteration-<N>/benchmark.json \
     [--previous-workspace <workspace>/iteration-<N-1>] \
     [--static <path/to/review.html>]
   ```

   **Flags:**

   - `--skill-name` — required literal for headers (match skill frontmatter `name` unless user overrides).
   - `--benchmark` — required path to this iteration’s `benchmark.json`.
   - `--previous-workspace` — include **iff** `<N> > 1`; value **must** be `<workspace>/iteration-<N-1>` (prior iteration directory).
   - `--static` — include **iff** the environment has no usable local browser or no display; write standalone HTML to the given file path instead of starting the server. Omit `--static` when a local browser can open `http://127.0.0.1:<port>`.

2. User completes review; capture `feedback.json` at `iteration-<N>/feedback.json` (viewer default path or operator-copied equivalent). For machine verification, the file **must** include `"status": "complete"` after the viewer’s submit flow (or equivalent manual write if tooling changes).
   - **Static mode requirement (`--static`)**: because there is no running server feedback endpoint, the operator must copy/export reviewer output into `iteration-<N>/feedback.json` and ensure it includes `"status": "complete"` before Phase E can pass.
3. **Pass:** `generate_review.py` exited successfully **and** `feedback.json` exists **and** `json.loads(feedback.json)["status"] == "complete"`.
4. **Block:** missing successful viewer generation, missing `feedback.json`, missing `status`, or `status != "complete"` → **do not** promote; fix and rerun Phase E.

### Phase F — Promotion gate

**Precondition:** Phase E machine checks passed (`feedback.json` with `status: complete`).

1. Read `benchmark.json`. Compute `with_rate = run_summary["with_skill"]["pass_rate"]["mean"]`. Compute `base_rate = run_summary["<baseline_key>"]["pass_rate"]["mean"]` where `<baseline_key>` is `without_skill` or `old_skill`. Require `with_rate >= 0.85` and `(with_rate - base_rate) >= 0.10`. (Do **not** rely on string `delta` fields alone for promotion.)
2. Compute `crit_failures` using **only** the algorithm in “Critical assertions (machine check)”. Require `crit_failures == 0`.
3. **Pass:** steps 1 and 2 both succeed.
4. **Block:** any check fails → revise skill and **rerun A → F** under `iteration-<N+1>/`.

## Failure handling

- **Preflight or schema failure (Phase A/B):** stop; fix inputs; repeat from Phase A.
- **Incomplete dual runs (Phase C):** discard partial results for that iteration label; rerun Phase C; do not hand-edit benchmark to fill gaps.
- **Grading or aggregation error (Phase D):** fix grading inputs; rerun Phase D; if root cause is missing runs, return to Phase C.
- **Missing human review artifacts (Phase E):** rerun `generate_review.py`; obtain `feedback.json` with `"status": "complete"`; do not treat chat-only acknowledgment as a substitute for that file.
- **Promotion failure (Phase F):** document failing metrics in the workspace; apply skill changes; increment iteration; rerun **A → F** completely.

## Phase 2 (explicitly out of scope)

Do **not** require or block promotion on the following in v1:

- Blind comparator workflows
- Automated description optimization loops (e.g., unattended trigger tuning)
- Advanced variance diagnostics beyond baseline aggregation already produced by `aggregate_benchmark.py`

## Additional references

- JSON shapes and viewer expectations: `.cursor/skills/create-agent-skill/references/schemas.md`
- Grader behavior: `.cursor/skills/create-agent-skill/agents/grader.md`
