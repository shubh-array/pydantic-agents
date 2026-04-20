# End-to-end validation (hybrid skill creator)

This document is the **deterministic E2E sequence** for validating the hybrid workflow against two coverage flows. Workflow gates and paths are defined in `.cursor/skills/create-agent-skill/SKILL.md` and `.cursor/skills/create-agent-skill/references/eval-contracts.md`.

## Preconditions (both flows)

1. `<skill-root>` resolves to `.cursor/skills/create-agent-skill/` (or equivalent checkout with the same layout).
2. Choose `<workspace>` (empty or dedicated directory).
3. Choose iteration `<N>` (use `1` for first E2E unless rerunning after failure).

## Shared artifact checklist (final iteration must satisfy)

Every path is under `<workspace>` unless prefixed with `<skill-root>`.

### Eval suite

| # | Required path |
|---|-----------------|
| 1 | `<workspace>/evals/evals.json` |

### Snapshot (Flow B only)

| # | Required path |
|---|-----------------|
| 1 | `<workspace>/skill-snapshot/` (full copy of pre-edit skill tree) |

### Iteration root

| # | Required path |
|---|-----------------|
| 1 | `<workspace>/iteration-<N>/benchmark.json` |
| 2 | `<workspace>/iteration-<N>/benchmark.md` |
| 3 | `<workspace>/iteration-<N>/feedback.json` |

### For each `evals[].id` = `<id>`

| # | Required path |
|---|-----------------|
| 1 | `<workspace>/iteration-<N>/eval-<id>/` |
| 2 | `<workspace>/iteration-<N>/eval-<id>/with_skill/run-1/outputs/` |
| 3 | `<workspace>/iteration-<N>/eval-<id>/with_skill/run-1/eval_metadata.json` |
| 4 | `<workspace>/iteration-<N>/eval-<id>/with_skill/run-1/grading.json` |
| 5 | `<workspace>/iteration-<N>/eval-<id>/with_skill/run-1/timing.json` |
| 6 | `<workspace>/iteration-<N>/eval-<id>/<baseline-side>/run-1/outputs/` |
| 7 | `<workspace>/iteration-<N>/eval-<id>/<baseline-side>/run-1/eval_metadata.json` |
| 8 | `<workspace>/iteration-<N>/eval-<id>/<baseline-side>/run-1/grading.json` |
| 9 | `<workspace>/iteration-<N>/eval-<id>/<baseline-side>/run-1/timing.json` |

Replace `run-1` with every `run-<M>` actually used; candidate and baseline **must** share the same `<M>` set per `<id>`.

`<baseline-side>` is `without_skill` (Flow A) or `old_skill` (Flow B).

---

## Flow A — New skill (baseline `without_skill`)

**Definition:** Candidate runs use **with skill**; baseline runs use **without_skill**, same prompts and inputs, no skill path for baseline.

**Explicit non-paths for Flow A:** Do **not** create or rely on `<workspace>/skill-snapshot/` for this flow.

**Explicit tool exclusion for Phase C:** Phase C dual runs **do not** invoke `<skill-root>/scripts/run_eval.py` (per `SKILL.md`; that script is for description trigger measurement only).

### Step A0 — Initialize workspace

1. Create `<workspace>/evals/evals.json` with at least one eval: integer `id`, string `prompt`, and any fields required by `<skill-root>/references/schemas.md`.
2. Create on disk: `<workspace>/iteration-<N>/eval-<id>/` for each `evals[].id`.

**Gate:** For every eval id in JSON, path `<workspace>/iteration-<N>/eval-<id>/` exists. **Fail** if any id lacks a directory or any extra `eval-*` exists.

### Step A1 — Phase A (intent + draft + preflight)

1. Record purpose, triggers, and output contract (conversation or note under `<workspace>/`).
2. Author or update the skill’s `SKILL.md` (path is the skill directory under the repo, e.g. `.cursor/skills/<name>/SKILL.md`).
3. Run:

   ```bash
   cd <skill-root> && python3 scripts/quick_validate.py <skill_directory>
   ```

**Gate — Pass:** Exit code `0`. **Fail:** Non-zero.

### Step A2 — Phase B (eval suite)

1. Confirm `<baseline-side>` for this flow is **`without_skill`** under every `eval-<id>/`.
2. Re-verify Step A0 alignment and schema.

**Gate — Pass:** All Phase B checks in `eval-contracts.md` § Phase B. **Fail:** Otherwise; do not execute runs.

### Step A3 — Phase C (dual execution)

For each `<id>`, in the **same scheduling window**:

1. Execute candidate with skill → write only under `<workspace>/iteration-<N>/eval-<id>/with_skill/run-1/`.
2. Execute baseline without skill → write only under `<workspace>/iteration-<N>/eval-<id>/without_skill/run-1/`.
3. Ensure shared inputs are identical; ensure no cross-side reads/writes of outputs.

**Gate — Pass:** Both trees contain paired `run-1` with `outputs/`, `eval_metadata.json`, `grading.json`, `timing.json`. **Fail:** Any missing file or directory; **invalidate** iteration and return to A3.

### Step A4 — Phase D (grade + aggregate)

1. Complete `grading.json` on **both** sides per hybrid schema (`assertion_id` alignment with metadata).
2. Run:

   ```bash
   cd <skill-root> && python3 -m scripts.aggregate_benchmark <workspace>/iteration-<N> --skill-name <name>
   ```

**Gate — Pass:** `<workspace>/iteration-<N>/benchmark.json` and `benchmark.md` exist; `run_summary` contains `with_skill` and `without_skill`. **Fail:** Otherwise.

### Step A5 — Phase E (eval viewer + feedback)

1. Run (omit `--previous-workspace` when `<N>` is `1`; add `--static <path>` only if required per `SKILL.md`):

   ```bash
   cd <skill-root> && python3 eval-viewer/generate_review.py \
     <workspace>/iteration-<N> \
     --skill-name "<skill-name>" \
     --benchmark <workspace>/iteration-<N>/benchmark.json
   ```

2. Ensure `<workspace>/iteration-<N>/feedback.json` exists and contains `"status": "complete"`.

**Gate — Pass:** Viewer command exit `0` **and** JSON parse yields `status == "complete"`. **Fail:** Otherwise.

### Step A6 — Phase F (promotion)

1. Read `<workspace>/iteration-<N>/benchmark.json`.
2. Compute `with_rate`, `base_rate` with `<baseline_key> = "without_skill"`.
3. Compute `crit_failures` per `SKILL.md` (machine check).

**Gate — Pass:** `with_rate >= 0.85` **and** `(with_rate - base_rate) >= 0.10` **and** `crit_failures == 0`. **Fail:** Any inequality false; then increment iteration and rerun the full flow **A0 → A6** using `iteration-<N+1>/`.

---

## Flow B — Skill improvement (baseline `old_skill` from snapshot)

**Definition:** Candidate runs use the **revised** skill; baseline runs load **only** `<workspace>/skill-snapshot/` (frozen pre-edit tree).

**Explicit tool exclusion for Phase C:** Same as Flow A — **do not** use `<skill-root>/scripts/run_eval.py` for dual execution.

### Step B0 — Freeze snapshot (mandatory before candidate edits)

1. Copy the entire current skill directory (pre-improvement) to `<workspace>/skill-snapshot/` so it is a standalone tree.
2. Only after the copy succeeds, edit the live skill for the candidate.

**Gate — Pass:** `<workspace>/skill-snapshot/` exists and contains the prior `SKILL.md` and bundled files needed for baseline execution. **Fail:** Candidate edits applied before snapshot exists.

### Step B1 — Workspace and eval dirs

Same as Flow A Step A0, using the **same** path table with `<baseline-side> = old_skill`.

**Gate:** Same as Flow A Step A0, with `old_skill` dirs planned instead of `without_skill`.

### Step B2 — Phase A

Same commands as Flow A Step A1 on the **updated** skill directory.

**Gate:** Same as Flow A Step A1.

### Step B3 — Phase B

Confirm `<baseline-side>` is **`old_skill`** for every `eval-<id>/`.

**Gate:** Same as `eval-contracts.md` § Phase B with `old_skill`.

### Step B4 — Phase C

For each `<id>`, same scheduling window:

1. Candidate: revised skill → `<workspace>/iteration-<N>/eval-<id>/with_skill/run-1/`.
2. Baseline: agents load **only** `<workspace>/skill-snapshot/` as the skill source → `<workspace>/iteration-<N>/eval-<id>/old_skill/run-1/`.

**Gate:** Same file completeness as Flow A Step A3, with `old_skill` instead of `without_skill`.

### Step B5 — Phase D

Same as Flow A Step A4.

**Gate — Pass:** `run_summary` includes `with_skill` and **`old_skill`** (not only `without_skill`). **Fail:** Missing `old_skill` key or aggregation error.

### Step B6 — Phase E

Same command shape as Flow A Step A5; if `<N> > 1`, **must** include:

`--previous-workspace <workspace>/iteration-<N-1>`

**Gate:** Same as Flow A Step A5.

### Step B7 — Phase F

Same as Flow A Step A6 with `<baseline_key> = "old_skill"`.

**Gate:** Same numeric and `crit_failures` rules as Flow A Step A6.

---

## Session-level acceptance (design spec)

After both Flow A and Flow B complete at least one full pass through **A6 / B7**:

| Check | Pass | Fail |
|-------|------|------|
| Trigger sanity | Skill triggers on intended contexts; near-miss prompts do not trigger incorrectly | Mis-trigger observed |
| Workflow integrity | Phases **A → F** executed in order with no skipped mandatory step | Any bypass |
| Output usability | All required artifact paths in “Shared artifact checklist” exist for the final successful iteration | Any missing path |
| Baseline clarity | Reports and `benchmark.json` name the correct `<baseline_key>` (`without_skill` vs `old_skill`) | Ambiguous or wrong baseline |
| Critical feedback | No unresolved **critical** assertion failures (`crit_failures == 0`) | `crit_failures > 0` |

---

## Exit criteria (E2E complete)

1. Flow A completed Steps A0–A6 at least once with Phase F **pass** or documented intentional stop after viewer (promotion still requires F pass).
2. Flow B completed Steps B0–B7 at least once with the same clarification.
3. Final iteration directory contains every path listed in “Shared artifact checklist” for that flow’s `<baseline-side>`.
4. Promotion thresholds met when promotion is claimed: `with_rate >= 0.85`, lift `>= 0.10`, `crit_failures == 0`.
5. No unresolved critical items in human feedback that contradict shipping (operator judgment; machine gate remains `crit_failures`).
