# Production readiness checklist (hybrid skill creator)

Use this document **in order** for each skill ship attempt. Canonical workflow and algorithms: `.cursor/skills/create-agent-skill/SKILL.md`. Paths and gate tables: `.cursor/skills/create-agent-skill/references/eval-contracts.md`. Full E2E sequences: `.cursor/skills/create-agent-skill/references/e2e-validation.md`.

Fill these placeholders **once** before the first checklist section; reuse unchanged until you change workspace or iteration:

| Placeholder | Meaning | Example |
|-------------|---------|---------|
| `<skill-root>` | Directory containing `scripts/` and `eval-viewer/` | `.cursor/skills/create-agent-skill/` |
| `<workspace>` | Eval workspace root (operator-chosen stable path) | `my-skill-workspace/` |
| `<N>` | Positive integer iteration directory label | `1` |
| `<skill_directory>` | Filesystem path to the skill tree under validation or edit | `.cursor/skills/<name>/` |
| `<skill-name>` | Literal for headers; match skill frontmatter `name` unless user overrides | `create-agent-skill` |
| `<baseline-side>` | Directory name for baseline runs | Flow A (new skill): `without_skill`. Flow B (improvement): `old_skill` |
| `<baseline_key>` | JSON key in `benchmark.json` `run_summary` | Same string as `<baseline-side>` |

**Promotion thresholds (numeric, all mandatory):**

- `with_rate = run_summary["with_skill"]["pass_rate"]["mean"]` must satisfy `with_rate >= 0.85`.
- `base_rate = run_summary["<baseline_key>"]["pass_rate"]["mean"]` must satisfy `(with_rate - base_rate) >= 0.10`.
- `crit_failures` from `.cursor/skills/create-agent-skill/SKILL.md` section **Critical assertions (machine check)** must equal `0`.

---

## 1) Preflight

Complete **every** step; if any step fails, stop and fix before starting Section 2 Phase A of this iteration.

1. **Confirm toolchain layout:** These paths exist relative to `<skill-root>`:
   - `scripts/quick_validate.py`
   - `scripts/aggregate_benchmark.py` (importable as `scripts.aggregate_benchmark`)
   - `eval-viewer/generate_review.py`
   - `references/schemas.md` (for `evals/evals.json` validation)
2. **Choose flow and set `<baseline-side>` / `<baseline_key>`:**
   - New skill → `<baseline-side>` = `without_skill`; do **not** create `<workspace>/skill-snapshot/`.
   - Improving an existing skill → `<baseline-side>` = `old_skill`; you **will** use `<workspace>/skill-snapshot/` in step 3.
3. **If Flow B (`old_skill`):** Copy the **entire** pre-edit skill directory into `<workspace>/skill-snapshot/` **before** any candidate edit to `<skill_directory>`. Verify `<workspace>/skill-snapshot/SKILL.md` exists. **Do not** proceed to candidate edits until this copy succeeds.
4. **Phase A preflight command:** From `<skill-root>`:

   ```bash
   cd <skill-root> && python3 scripts/quick_validate.py <skill_directory>
   ```

   Require exit code `0`. On non-zero: fix `<skill_directory>` structure; **repeat step 4 only** until success (do not enter checklist section 2 Phase B until step 4 passes).

**Preflight pass condition:** Steps 1–4 all satisfied.

---

## 2) Per-iteration run

Execute **Phases A → E** in order for iteration `<N>`. Do not skip phases. Phase C **does not** use `scripts/run_eval.py` (that script is for description trigger measurement only, per `SKILL.md`).

### Phase A — Intent and draft

1. Record purpose, trigger contexts, and output contract (conversation or short note under `<workspace>/`).
2. Draft or update `<skill_directory>/SKILL.md` (and bundled files if needed).
3. Re-run Preflight step 4 (`quick_validate.py`); require exit code `0`.

### Phase B — Eval suite

1. Choose source-of-truth eval file for this iteration: `<workspace>/evals/evals.json` **or** `<skill_directory>/evals/evals.json` (if both exist, ensure they are equivalent before proceeding).
2. Validate the chosen eval file against `<skill-root>/references/schemas.md`; confirm each eval has at least `id` (integer) and `prompt` (string).
3. For each `evals[].id` in the chosen file, confirm `<workspace>/iteration-<N>/eval-<id>/` exists and matches id; confirm no orphan `eval-*` dirs.
4. Confirm `<baseline-side>` is consistent under every `eval-<id>/` as chosen in Preflight.

**Stop if fail:** do not start Phase C until Phase B passes.

### Phase C — Dual execution

For **each** `eval-<id>/`, in the **same scheduling window** (same agent turn when subagents exist):

1. Candidate writes **only** under `<workspace>/iteration-<N>/eval-<id>/with_skill/run-<M>/`.
2. Baseline writes **only** under `<workspace>/iteration-<N>/eval-<id>/<baseline-side>/run-<M>/`.
3. Use the **same** set of `run-<M>` names on both sides per `<id>` (e.g. both have `run-1`).
4. Shared prompts/inputs are identical across sides; **no** shared scratch between sides; **no** cross-side read/write of artifacts under `run-*` (each side: shared inputs + its own `run-*` tree only).
5. When each run completes, ensure these paths exist and `outputs/` is populated (viewer requires `outputs/`):

   - `.../run-<M>/outputs/`
   - `.../run-<M>/eval_metadata.json` (required keys per `SKILL.md`)
   - `.../run-<M>/grading.json` (hybrid shape per `SKILL.md`)
   - `.../run-<M>/timing.json`

**Stop if fail:** treat iteration `<N>` as invalid for aggregation/review/promotion; rerun Phase C (do not hand-edit benchmarks to fill gaps).

### Phase D — Grading and aggregation

1. For **every** `with_skill/run-<M>/`, verify the set of `grading.json` → `expectations[].assertion_id` equals the set of `eval_metadata.json` → `assertions[].id` (same cardinality, no extras, no omissions).
2. From `<skill-root>`:

   ```bash
   cd <skill-root> && python3 -m scripts.aggregate_benchmark <workspace>/iteration-<N> --skill-name <skill-name>
   ```

   Require exit code `0`.
3. Confirm files exist: `<workspace>/iteration-<N>/benchmark.json` and `<workspace>/iteration-<N>/benchmark.md`.
4. Open `benchmark.json`; confirm `run_summary` contains keys `with_skill` and `<baseline_key>` (`without_skill` or `old_skill`).

**Stop if fail:** fix grading inputs and/or return to Phase C for missing runs; rerun Phase D after fixes.

### Phase E — Human review

1. From `<skill-root>`, run `eval-viewer/generate_review.py` with first argument = `<workspace>/iteration-<N>` (the iteration directory, **not** `<workspace>` alone).
2. **Required flags:** `--skill-name "<skill-name>"` and `--benchmark <workspace>/iteration-<N>/benchmark.json`.
3. **If `<N> > 1`:** add `--previous-workspace <workspace>/iteration-<N-1>` (exact prior iteration path).
4. **If no local browser/display:** add `--static <path/to/review.html>` per `SKILL.md`; otherwise omit `--static` and use the local server URL.
5. Require the command exits `0`.
6. Confirm `<workspace>/iteration-<N>/feedback.json` exists, parses as JSON, and `status == "complete"` (string).

**Stop if fail:** rerun Phase E; **do not** enter Promotion gate until Phase E passes.

**Per-iteration run pass condition:** Phases A through E all pass for the same `<N>`.

---

## 3) Promotion gate

**Precondition:** Section 2 Phase E pass (including `feedback.json` with `"status": "complete"`).

1. Load `<workspace>/iteration-<N>/benchmark.json`.
2. Compute:

   - `with_rate = run_summary["with_skill"]["pass_rate"]["mean"]`
   - `base_rate = run_summary["<baseline_key>"]["pass_rate"]["mean"]` where `<baseline_key>` is `without_skill` or `old_skill` matching this iteration’s flow.

3. **Numeric checks:** Confirm `with_rate >= 0.85` and `(with_rate - base_rate) >= 0.10` using the floats from step 2 (do **not** promote using string `delta` fields alone).
4. **Critical assertions:** Set `crit_failures = 0`. For **each** directory matching `<workspace>/iteration-<N>/eval-*/with_skill/run-*`, execute **only** the algorithm in `.cursor/skills/create-agent-skill/SKILL.md` **Critical assertions (machine check)** (read that section; do not substitute prose summaries). Confirm `crit_failures == 0`.
5. If steps 3–4 pass: promotion **allowed** for this iteration (optional: run `scripts/package_skill.py` from `<skill-root>` **after** promotion when distributing a `.skill` bundle).

**Promotion gate pass condition:** Step 3 **and** step 4 both pass.

**Promotion gate fail condition:** Any inequality in step 3 fails **or** `crit_failures != 0` **or** machine-check inputs are missing (missing `assertions`, `critical`, `assertion_id`, or set mismatches) — **block promotion**.

---

## 4) Regression fallback

Use the row that matches the **first** failed gate. After remediation, resume from the indicated phase **for the same `<N>`** unless the row says to increment `<N>`.

| Failure location | Evidence | Required action | Resume at |
|------------------|----------|-----------------|-----------|
| Preflight step 1 | Missing script under `<skill-root>` | Restore the hybrid skill package or correct `<skill-root>` path | Preflight step 1 |
| Preflight step 3 (Flow B) | Snapshot missing or candidate edited before copy | Recopy pre-edit tree to `<workspace>/skill-snapshot/`; restore live skill from VCS if needed | Preflight step 3 |
| Section 2 Phase B | `evals.json` / `eval-*` mismatch or mixed baseline sides | Fix JSON and directories until directory ↔ JSON rules in `eval-contracts.md` Phase B hold | Section 2 Phase B |
| Preflight step 4 (`quick_validate`) | Non-zero exit | Fix skill structure in `<skill_directory>` | Preflight step 4 |
| Phase B | Orphan/missing `eval-*`, schema error, wrong `<baseline-side>` | Fix eval suite; align dirs | Phase B |
| Phase C | Missing side, `run-*`, `outputs/`, or required run files | Discard partial results for this `<N>`; rerun dual execution | Phase C |
| Phase D | `assertion_id` set mismatch on `with_skill` | Fix `grading.json` / `eval_metadata.json`; rerun grading | Phase D |
| Phase D | Aggregator error or missing `benchmark.json` / `benchmark.md` | Fix inputs; if runs missing, return to C | Phase D or C as indicated by root cause |
| Phase D | `run_summary` missing `with_skill` or `<baseline_key>` | Fix aggregation inputs/configuration naming | Phase D |
| Phase E | `generate_review.py` non-zero or wrong args | Fix command/paths; rerun viewer | Phase E |
| Phase E | No `feedback.json` or `status != "complete"` | Complete viewer flow or, with `--static`, manually write `feedback.json` meeting machine condition | Phase E |
| Promotion gate | `with_rate < 0.85` or lift `< 0.10` or `crit_failures > 0` | Document failing metrics under `<workspace>/`; revise skill | **Increment** `<N>` to `<N+1>`; rerun **Preflight (if toolchain/snapshot needs refresh)** and full **Sections 2–3** for new `iteration-<N>/` (full **A → F** per `SKILL.md`) |

**Hard rules (no exceptions):**

- Do **not** aggregate, open the eval viewer for promotion purposes, or promote when Phase C required paths are incomplete — **invalidate** and rerun C.
- Do **not** treat chat-only approval as Phase E completion — `feedback.json` with `"status": "complete"` is mandatory.
- On promotion numeric failure, **do not** patch `benchmark.json` to force a pass; change the skill and run a **new** iteration directory.

---

## Quick reference: promotion thresholds

| Quantity | Source | Pass |
|----------|--------|------|
| With-skill pass rate | `benchmark.json` → `run_summary.with_skill.pass_rate.mean` | `>= 0.85` |
| Lift vs baseline | `with_rate - run_summary.<baseline_key>.pass_rate.mean` | `>= 0.10` |
| Critical failures | `.cursor/skills/create-agent-skill/SKILL.md` machine-check on `with_skill` runs only | `== 0` |
