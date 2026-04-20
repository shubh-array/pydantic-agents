# E2E harness implementation note (follow-up)

Normative workflow: `.cursor/skills/create-agent-skill/SKILL.md`. Path, schema, and gate definitions: `eval-contracts.md`. Deterministic manual E2E sequences: `e2e-validation.md`. This file specifies **how automation must invoke** the v1 toolchain scripts and **how automation must enforce** contextual baselines and run isolation. It does not redefine promotion math or Phase A–F ordering; those remain in `SKILL.md`.

## 1. Invocation contracts

Fixed symbols:

- `<skill-root>` — directory that contains `scripts/` and `eval-viewer/` (this repository: `.cursor/skills/create-agent-skill/`).
- `<workspace>` — skill evaluation workspace root chosen by the operator or harness.
- `<N>` — positive integer iteration label.
- `<name>` — skill name string for aggregation and viewer headers (match skill frontmatter `name` unless the user overrides).

Unless a script documents otherwise, the harness **must** set the process current working directory to `<skill-root>` before invoking the commands below.

### 1.0 `scripts/quick_validate.py` (Phase A preflight)

**Role:** Validates skill structure before entering Phase B or any run execution.

**Command shape:**

```bash
cd <skill-root> && python3 scripts/quick_validate.py <skill_directory>
```

**Harness I/O:** Require exit code `0` for Phase A pass. Non-zero exit is a hard preflight failure; the harness must block Phase B/Phase C until validation succeeds.

### 1.1 `scripts/run_eval.py` (description trigger only)

**Role:** Measures whether a skill **description** causes `claude -p` to trigger for queries in an eval set. **Not** used for Phase C dual skill-task runs (`e2e-validation.md` explicit tool exclusion).

**Command shape:**

```bash
cd <skill-root> && python3 scripts/run_eval.py \
  --eval-set <path_to_eval_set_json> \
  --skill-path <path_to_skill_directory>
```

**Optional flags (defaults apply if omitted):** `--description`, `--num-workers`, `--timeout`, `--runs-per-query`, `--trigger-threshold`, `--model`, `--verbose`.

**Harness I/O:** The script writes a single JSON document to **stdout**. The harness **must** capture stdout (not rely on files) and parse JSON. Treat parsed JSON (`summary` and per-query `pass`) as the source of truth for trigger outcomes; exit code alone is not sufficient because normal runs can complete with pass/fail results in JSON while still exiting `0`.

### 1.2 `scripts/aggregate_benchmark.py` (Phase D)

**Role:** Reads `grading.json` under `eval-*` trees and writes `<workspace>/iteration-<N>/benchmark.json` and sibling `benchmark.md`.

**Command shape (module invocation, normative for hybrid):**

```bash
cd <skill-root> && python3 -m scripts.aggregate_benchmark \
  <workspace>/iteration-<N> \
  --skill-name <name>
```

**Optional flags:** `--skill-path` (path string; default empty), `--output` / `-o` (override JSON path; default `<benchmark_dir>/benchmark.json`). Hybrid promotion reads `benchmark.json` at the iteration root; the harness **must** either omit `--output` or set it to `<workspace>/iteration-<N>/benchmark.json` so `benchmark.md` stays co-located (same stem as JSON).

**Harness I/O:** Exit code `0` required for Phase D pass. After success, the harness **must** assert existence of `benchmark.json` and `benchmark.md` under `<workspace>/iteration-<N>/`.

### 1.3 `eval-viewer/generate_review.py` (Phase E)

**Role:** Discovers runs under the workspace (directories containing `outputs/`), embeds data for review, serves HTTP or writes static HTML.

**Command shape:**

```bash
cd <skill-root> && python3 eval-viewer/generate_review.py \
  <workspace>/iteration-<N> \
  --skill-name "<name>" \
  --benchmark <workspace>/iteration-<N>/benchmark.json \
  [--previous-workspace <workspace>/iteration-<N-1>] \
  [--static <path_to_output_html>]
```

**Hybrid-required flags:**

- First positional `workspace` **must** be `<workspace>/iteration-<N>` (iteration directory, not `<workspace>` root).
- `--skill-name` **must** be present for stable headers.
- `--benchmark` **must** be present for hybrid Phase E (the script allows omission; hybrid does not).

**Conditional flags:**

- `--previous-workspace` **must** be included if and only if `<N> > 1`; value **must** be `<workspace>/iteration-<N-1>`.
- `--static` **must** be included if and only if the environment has no usable local browser **or no display** for local server review; when present, the operator or harness **must** still produce `<workspace>/iteration-<N>/feedback.json` with `"status": "complete"` (`SKILL.md` static mode requirement).

**Optional:** `--port` / `-p` when not using `--static` (default `3117`).

**Harness I/O:** Require a `generate_review.py` run that ends with exit code `0` and `feedback.json` machine checks (`status == "complete"`). For `--static`, assert exit `0` after HTML write. For server mode, the process blocks until shutdown, so the harness must explicitly stop the server after review and verify a clean exit `0` (or prefer `--static` when clean shutdown control is unavailable).
The harness must also assert `<workspace>/iteration-<N>/benchmark.json` exists and parses as valid JSON (before or immediately after viewer invocation), because `generate_review.py` can still run without loaded benchmark data if the path is missing or invalid.

## 2. Contextual baselines in automation

Automation **must** implement the same baseline table as `SKILL.md` (non-negotiable policy 2).

| Skill situation | Baseline directory name | Baseline meaning |
|-----------------|-------------------------|------------------|
| New skill | `without_skill` | Same prompts and inputs as candidate; no skill path for baseline |
| Improving an existing skill | `old_skill` | Baseline runs load **only** `<workspace>/skill-snapshot/` |

**Enforcement checks (machine-applicable):**

1. **Flow selection:** Before any baseline run artifacts are written, the harness **must** record whether the iteration is “new skill” or “improvement” and **must** reject mixed baseline-side names under the same iteration (same rule as `eval-contracts.md` Phase B baseline-side check).
2. **Flow A (`without_skill`):** The harness **must not** create or require `<workspace>/skill-snapshot/` for promotion. Baseline agent configuration **must** omit the candidate skill path while keeping prompts and shared inputs identical to candidate.
3. **Flow B (`old_skill`):** The harness **must** verify `<workspace>/skill-snapshot/` exists **before** the candidate skill tree is modified for that iteration. If candidate edits are detected before a successful snapshot copy, the iteration **must** be marked invalid (maps to `e2e-validation.md` Step B0 gate).
4. **Aggregator alignment:** After `aggregate_benchmark.py`, `benchmark.json` → `run_summary` **must** include keys `with_skill` and exactly one baseline key: `without_skill` or `old_skill`, matching the chosen flow. Promotion code **must** read `run_summary["<baseline_key>"]["pass_rate"]["mean"]` with `<baseline_key>` equal to that directory name.

## 3. Run isolation in automation

Automation **must** implement `SKILL.md` non-negotiable policy 3 and `eval-contracts.md` isolation rules.

**Directory constraints:**

1. For each `evals[].id` = `<id>`, candidate artifacts **must** reside only under `<workspace>/iteration-<N>/eval-<id>/with_skill/run-<M>/`.
2. Baseline artifacts **must** reside only under `<workspace>/iteration-<N>/eval-<id>/<baseline-side>/run-<M>/` with `<baseline-side>` ∈ {`without_skill`, `old_skill`}.
3. For each `<id>`, the set of `run-*` names under `with_skill` **must** equal the set under `<baseline-side>` (pairing).

**Immutability and sharing:**

4. Shared prompt and input files **must** be identical for both sides; neither side **may** mutate shared inputs during a run pair.
5. There **must** be no shared scratch directory between sides for generated content. Generated paths **must** stay under the correct `run-<M>/` tree for that side.

**Cross-side access:**

6. Baseline processes **must not** read candidate skill sources except via the Flow B rule (read **only** `<workspace>/skill-snapshot/`). Candidate processes **must not** read baseline `run-*` outputs to complete their own outputs, and conversely.

**Scheduling (qualitative gate):**

7. For each `<id>`, baseline and candidate starts **must** occur in the same scheduling window (same agent turn when subagents exist). The harness **should** record timestamps or a single parent task id per eval pair to support audit; failure to pair in one window **must** invalidate the iteration per Phase C (`eval-contracts.md`).

**Pre-aggregation validation:**

8. Before invoking `aggregate_benchmark.py`, the harness **must** verify every required path in `eval-contracts.md` Phase C and the grading ID-alignment rule in Phase D (set equality of `assertion_id` and `assertions[].id` on each `with_skill/run-*`).

## 4. Phase 2 remainder (explicitly out of scope for v1 harness)

The following **must not** be required for v1 promotion or blocking logic (per `SKILL.md` “Phase 2 (explicitly out of scope)” and design spec):

- Blind comparator workflows.
- Automated description optimization loops (unattended trigger tuning replacing human authoring).
- Advanced variance diagnostics beyond what `aggregate_benchmark.py` already emits in `benchmark.json` / `benchmark.md`.

**Harness implication:** v1 automation **may** omit APIs and gates for the above. A phase-2 harness **may** add optional modules that do not change v1 artifact paths or promotion thresholds unless the workflow version is bumped and `SKILL.md` is updated.

## 5. Mapping to design spec hard gates

| Design spec requirement | Harness enforcement section |
|-------------------------|----------------------------|
| Full evaluation pipeline mandatory | Phases invoked in order A→F; `run_eval.py` does not substitute Phase C (`SKILL.md`, `e2e-validation.md`). |
| Contextual baseline | Section 2 and aggregator key checks. |
| Strict isolation | Section 3. |
| Promotion thresholds (0.85 / 0.10 lift / critical failures) | Implemented in Phase F logic per `SKILL.md`; harness reads `benchmark.json` and runs the critical assertion algorithm verbatim (not redefined here). |
| Human review and feedback file | Phase E invocation (Section 1.3) plus `feedback.json` with `status == "complete"`. |
