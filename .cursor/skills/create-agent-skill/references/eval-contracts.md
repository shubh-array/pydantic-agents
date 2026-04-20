# Eval contracts (hybrid skill creator)

Authoritative workflow text: `.cursor/skills/create-agent-skill/SKILL.md`. This file pins **paths**, **schemas**, and **gate pass/fail** in one place for deterministic execution.

## Roots and variables

- `<skill-root>` — Directory containing `scripts/` and `eval-viewer/`; in this repo: `.cursor/skills/create-agent-skill/`.
- `<workspace>` — Skill evaluation workspace root (any stable path the operator chooses; example: `pdf-skill-workspace/`).
- `<N>` — Positive integer iteration label (e.g. `1`, `2`).
- `<id>` — Decimal string of `evals[].id` from `evals/evals.json` (e.g. `3` → directory name `eval-3`; no zero-padding required).
- `<M>` — Run index, starting at `1` (`run-1`, `run-2`, …). Candidate `run-<M>` **must** pair with baseline `run-<M>` for the same `<id>`.

## Toolchain scripts (required paths)

All paths are under `<skill-root>` unless noted.

| Artifact | Path |
|----------|------|
| Preflight | `<skill-root>/scripts/quick_validate.py` |
| Description trigger eval (not Phase C dual runs) | `<skill-root>/scripts/run_eval.py` |
| Aggregation | `<skill-root>/scripts/aggregate_benchmark.py` (invoke as module; see Phase D gate) |
| Eval viewer | `<skill-root>/eval-viewer/generate_review.py` |
| Packaging | `<skill-root>/scripts/package_skill.py` |

Normative JSON and grader prose: `<skill-root>/references/schemas.md`, `<skill-root>/agents/grader.md`. Hybrid runs **add** required keys listed below; on conflict, `SKILL.md` wins.

## Directory conventions

### Eval suite (source of truth)

| Artifact | Path |
|----------|------|
| Eval definitions | `<workspace>/evals/evals.json` (may alternatively live in the skill tree per `SKILL.md`; if both exist, the operator must keep them equivalent) |

Rules:

- For each object in `evals/evals.json` → `evals` with integer `id`, a directory **must** exist: `<workspace>/iteration-<N>/eval-<id>/`.
- No extra `eval-*` directories for that iteration beyond those ids.
- Human-readable names belong only in JSON fields, **not** in directory names (`eval-<id>` only).

### Baseline side names

| Flow | `<baseline-side>` directory name | Meaning |
|------|----------------------------------|---------|
| New skill (Flow A) | `without_skill` | Same prompts/inputs as candidate; no skill applied |
| Improvement (Flow B) | `old_skill` | Runs load **only** the frozen snapshot tree (see snapshot path) |

Candidate side directory name is always: `with_skill`.

### Improvement snapshot (Flow B only)

| Artifact | Path |
|----------|------|
| Pre-edit skill tree copy | `<workspace>/skill-snapshot/` |

**Rule:** Copy the full skill directory into `<workspace>/skill-snapshot/` **before** any candidate edit to the live skill. Baseline runs must not read the mutating candidate skill tree.

### Per-run layout (both sides)

For each side in `{ with_skill, <baseline-side> }`:

| Artifact | Path |
|----------|------|
| Run root | `<workspace>/iteration-<N>/eval-<id>/<side>/run-<M>/` |
| Outputs directory (required; viewer treats runs without it as invalid) | `<workspace>/iteration-<N>/eval-<id>/<side>/run-<M>/outputs/` |
| Run metadata | `<workspace>/iteration-<N>/eval-<id>/<side>/run-<M>/eval_metadata.json` |
| Grading | `<workspace>/iteration-<N>/eval-<id>/<side>/run-<M>/grading.json` |
| Timing | `<workspace>/iteration-<N>/eval-<id>/<side>/run-<M>/timing.json` |

**Isolation:** No shared scratch directory between `with_skill` and `<baseline-side>`. No cross-side read/write of generated artifacts under `run-*` (each side reads shared inputs only plus its own `run-*` tree).

### Iteration root files

| Artifact | Path |
|----------|------|
| Aggregated benchmark (JSON) | `<workspace>/iteration-<N>/benchmark.json` |
| Aggregated benchmark (Markdown) | `<workspace>/iteration-<N>/benchmark.md` |
| Human review feedback | `<workspace>/iteration-<N>/feedback.json` |

## Canonical schemas

### `evals/evals.json`

- Validate against `<skill-root>/references/schemas.md` **and** ensure every eval has at least `id` (integer) and `prompt` (string) so prompts and disk dirs can be constructed.
- `evals[].id` **must** equal the `<id>` used in `eval-<id>/`.

### `eval_metadata.json` (required keys)

Location: `<workspace>/iteration-<N>/eval-<id>/<side>/run-<M>/eval_metadata.json`.

| Key | Type | Rule |
|-----|------|------|
| `eval_id` | int | Equals parent directory `<id>` |
| `prompt` | string | Task text |
| `assertions` | array | Each element is an object with `id` (string, unique in-file), `text` (string), `critical` (boolean) |

Candidate and baseline runs for the same eval **must** use the **same** `assertions` array (same `id`, `text`, `critical` per index).

### `grading.json` (hybrid contract)

Location: `<workspace>/iteration-<N>/eval-<id>/<side>/run-<M>/grading.json`.

Top-level:

- `summary` — **must** include at least `total`, `passed`, `failed`, `pass_rate` (float in `[0,1]`), consistent with `expectations`.
- `expectations` — array of objects; each object **must** include:
  - `text` (string)
  - `passed` (boolean)
  - `evidence` (string)
  - `assertion_id` (string) — **must** equal the matching `assertions[].id` in that run’s `eval_metadata.json`

**Set rule:** The set of `expectations[].assertion_id` **must** equal the set of `assertions[].id` in the same run’s `eval_metadata.json` (same cardinality, no extras, no omissions).

### `timing.json`

Location: `<workspace>/iteration-<N>/eval-<id>/<side>/run-<M>/timing.json`.

**Rule:** File **must** exist when run completion metadata is available. Shape follows the `timing.json` section in `<skill-root>/references/schemas.md` where applicable; capture wall-clock fields as soon as the run finishes (do not defer in a way that drops data).

### `benchmark.json` (post-aggregation)

Location: `<workspace>/iteration-<N>/benchmark.json`.

Produced by aggregation from all `grading.json` files under that iteration. **Promotion checks** read:

- `run_summary["with_skill"]["pass_rate"]["mean"]` — float in `[0,1]`
- `run_summary["<baseline_key>"]["pass_rate"]["mean"]` — `<baseline_key>` is `without_skill` (Flow A) or `old_skill` (Flow B)

Do **not** rely on string `delta` fields alone for promotion; recompute lift from the two means above.

### `feedback.json` (post–eval viewer)

Location: `<workspace>/iteration-<N>/feedback.json`.

**Machine pass condition:** After `json` parse, `status` exists and `status == "complete"` (string). Static `--static` HTML flows require the operator to write this file explicitly with the same constraint.

## Gate checks (pass / fail)

### Phase A — Intent and draft

| Check | Pass | Fail |
|-------|------|------|
| Preflight | `python3 scripts/quick_validate.py <skill_directory>` exits 0 when cwd is `<skill-root>` | Non-zero exit or uncaught error |

On fail: fix skill structure; **do not** enter Phase B.

### Phase B — Eval suite

| Check | Pass | Fail |
|-------|------|------|
| Directory ↔ JSON | Every `evals[].id` has matching `<workspace>/iteration-<N>/eval-<id>/`; no orphan `eval-*` dirs | Missing dir, extra `eval-*`, or `id` mismatch |
| Schema | `evals/evals.json` validates per `schemas.md` and has fields needed for prompts/metadata | Schema or field errors |
| Baseline side | Under every `eval-<id>/`, planned `<baseline-side>` is consistently `without_skill` (new) or `old_skill` (improvement) | Mixed or wrong side name |

On fail: fix; **do not** enter Phase C.

### Phase C — Dual execution

| Check | Pass | Fail |
|-------|------|------|
| Pairing | For every `eval-<id>/`, `with_skill` and `<baseline-side>` each contain the **same** set of `run-*` names | Any missing side, missing `run-*`, or mismatched run sets |
| Required paths | Every paired `run-*` has `outputs/`, `eval_metadata.json`, `grading.json`, `timing.json` | Any missing path |
| Scheduling | Candidate and baseline starts for each eval occur in the **same scheduling window** (same agent turn when subagents exist) | N/A (qualitative); if violated, operator discards iteration and reruns C |

On fail: **invalidate iteration** `<N>` for promotion purposes; rerun Phase C (do not aggregate partials).

### Phase D — Grading and aggregation

| Check | Pass | Fail |
|-------|------|------|
| ID alignment | On every `with_skill/run-*`, `grading.json` `assertion_id` set equals `eval_metadata.json` `assertions[].id` set | Any mismatch |
| Aggregation command | From `<skill-root>`: `python3 -m scripts.aggregate_benchmark <workspace>/iteration-<N> --skill-name <name>` exits 0 | Error exit or missing outputs |
| Root artifacts | `<workspace>/iteration-<N>/benchmark.json` and `benchmark.md` exist | Either missing |
| `run_summary` keys | `run_summary` includes `with_skill` and `<baseline_key>` (`without_skill` or `old_skill`) | Missing key |

On fail: fix grading or rerun C/D as needed.

### Phase E — Human review

| Check | Pass | Fail |
|-------|------|------|
| Viewer command | `python3 eval-viewer/generate_review.py` with cwd `<skill-root>` exits 0; arguments per `SKILL.md` (iteration dir as first arg; `--benchmark` required; `--previous-workspace` iff `<N> > 1`; `--static` iff no browser) | Non-zero exit or wrong paths |
| Feedback file | `<workspace>/iteration-<N>/feedback.json` exists and parses as JSON with `"status": "complete"` | Missing file, invalid JSON, missing `status`, or `status != "complete"` |

On fail: rerun E; **do not** enter Phase F.

### Phase F — Promotion

**Precondition:** Phase E machine checks passed.

| Check | Pass | Fail |
|-------|------|------|
| Pass rate | `with_rate = run_summary["with_skill"]["pass_rate"]["mean"]` and `with_rate >= 0.85` | `with_rate < 0.85` |
| Lift | `base_rate = run_summary["<baseline_key>"]["pass_rate"]["mean"]` and `(with_rate - base_rate) >= 0.10` | Lift below 0.10 |
| Critical failures | `crit_failures == 0` using **only** the algorithm in `SKILL.md` section “Critical assertions (machine check)” (scan `with_skill` runs only; match `critical` assertions to `grading.json` by `assertion_id`) | Any critical assertion failed or machine-check inputs missing |

On fail: document metrics; revise skill; use `iteration-<N+1>/` and rerun **A → F**.

## Critical assertions algorithm (reference)

Execute exactly as specified in `.cursor/skills/create-agent-skill/SKILL.md` (“Critical assertions (machine check)”). This document does not restate the loop to avoid drift; the SKILL is canonical.

## Promotion numeric summary

All of the following **must** be true to promote:

1. `with_rate >= 0.85`
2. `(with_rate - base_rate) >= 0.10`
3. `crit_failures == 0`
