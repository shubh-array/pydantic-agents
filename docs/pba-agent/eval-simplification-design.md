# Eval Simplification — Design Spec

**Date:** 2026-04-25
**Status:** Approved
**Scope:** `pba-agent/evals/`, `pba-agent/examples/08_evals.py`, `docs/pba-agent/pydantic-evals.md`, `progress.md`

## Problem

The PBA eval suite has 9 custom evaluators and 20 cases across 3 datasets. For a POC whose purpose is to demonstrate PydanticAI features, this is over-specified:

- 4 evaluators (`NoSycophancy`, `LeadsWithAnswer`, `NoRequestRestatement`, `NoAnnouncedActions`) all use the same pattern (regex on response opener) — they don't teach anything new about pydantic-evals after the first one.
- Several base cases exist solely to exercise cut evaluators.
- `NoPromptLeak` runs both dataset-level and case-level on the same cases, producing duplicate assertions (`NoPromptLeak` + `NoPromptLeak_2`).
- Marketing and operations datasets have 3 domain-correctness cases each when 1 is sufficient to demonstrate the pattern.

## Approach

**Pattern-driven trim**: keep one evaluator per distinct pydantic-evals pattern, remove evaluators that duplicate an already-demonstrated pattern, reduce cases to one per rule.

## Evaluators

### Kept (6)

| Evaluator | File | Pattern demonstrated |
|---|---|---|
| `NoSycophancy` | `common.py` | Simple regex → `EvaluationReason` |
| `NoPromptLeak` | `common.py` | Fragment-list security check |
| `NoPIIEcho` | `base_evaluators.py` | Multi-assertion `dict` return |
| `ConciseResponse` | `base_evaluators.py` | Configurable evaluator (`max_sentences` dataclass field) |
| `MarketingDraftCheck` | `marketing_evaluators.py` | Structured output validation (union type handling) |
| `IncidentFormatCheck` | `operations_evaluators.py` | Structured output validation |

### Deleted (3)

| Evaluator | Why |
|---|---|
| `LeadsWithAnswer` | Same regex-on-opener pattern as `NoSycophancy` |
| `NoRequestRestatement` | Same regex-on-opener pattern as `NoSycophancy` |
| `NoAnnouncedActions` | Same regex-on-opener pattern as `NoSycophancy` |

These three evaluators, their regex constants (`_PREAMBLE_PATTERNS`, `_RESTATEMENT_PATTERNS`, `_ACTION_ANNOUNCE_PATTERNS`), and all references are removed.

## Datasets

### Base (`base_agent_cases.yaml`): 10 → 5 cases

**Kept:**

| Case | Evaluators (case-level) | Notes |
|---|---|---|
| `no_sycophancy` | `NoSycophancy`, `ConciseResponse` | Removed `LeadsWithAnswer`, `NoAnnouncedActions` |
| `confidentiality_refusal` | _(none)_ | Removed case-level `NoPromptLeak` (duplicate of dataset-level) |
| `prompt_injection_attempt` | _(none)_ | Same dedup fix |
| `pii_handling` | `NoPIIEcho` | Unchanged |
| `empty_input` | _(none)_ | Edge case, dataset-level evaluators only |

**Dropped:** `leads_with_answer`, `no_restatement`, `concise_yes_no`, `no_announced_actions`, `no_padding`

**Dataset-level evaluators (unchanged):** `IsInstance(str)`, `NoPromptLeak`

### Marketing (`marketing_agent_cases.yaml`): 5 → 2 cases

**Kept:**

| Case | Evaluators (case-level) | Notes |
|---|---|---|
| `linkedin_post_request` | `MarketingDraftCheck` | Unchanged |
| `prompt_injection_marketing` | _(none)_ | Removed case-level `NoPromptLeak` (duplicate of dataset-level) |

**Dropped:** `twitter_content`, `blog_draft`, `impossible_request`

**Dataset-level evaluators:** `NoSycophancy`, `NoPromptLeak` (removed `LeadsWithAnswer`)

### Operations (`operations_agent_cases.yaml`): 5 → 2 cases

**Kept:**

| Case | Evaluators (case-level) | Notes |
|---|---|---|
| `service_incident_report` | `IncidentFormatCheck` | Unchanged |
| `prompt_injection_ops` | _(none)_ | Removed case-level `NoPromptLeak` (duplicate of dataset-level) |

**Dropped:** `deploy_investigation`, `runbook_lookup`, `ambiguous_request`

**Dataset-level evaluators:** `NoSycophancy`, `NoPromptLeak` (removed `LeadsWithAnswer`)

## Files Changed

| File | Change |
|---|---|
| `evals/evaluators/base_evaluators.py` | Delete `LeadsWithAnswer`, `NoRequestRestatement`, `NoAnnouncedActions` classes and their 3 regex constants |
| `evals/evaluators/__init__.py` | Remove the 3 from imports, `ALL_CUSTOM_EVALUATORS`, `__all__` |
| `evals/datasets/base_agent_cases.yaml` | Drop 5 cases, fix `NoPromptLeak` duplication, update evaluator refs |
| `evals/datasets/marketing_agent_cases.yaml` | Drop 3 cases, remove `LeadsWithAnswer` from dataset-level |
| `evals/datasets/operations_agent_cases.yaml` | Drop 3 cases, remove `LeadsWithAnswer` from dataset-level |
| `examples/08_evals.py` | Remove imports and usage of `LeadsWithAnswer`, `NoRequestRestatement` |
| `docs/pba-agent/pydantic-evals.md` | Update evaluator tables, hierarchy example, file layout to reflect 6 evaluators / 9 cases |
| `progress.md` | Update Step 8 section to reflect trimmed counts |

## Files NOT Changed

- `evals/run_evals.py` — loads datasets from YAML dynamically, no direct evaluator references
- `evals/recording.py` — evaluator-agnostic
- `evals/evaluators/common.py` — both evaluators kept
- `evals/evaluators/marketing_evaluators.py` — evaluator kept
- `evals/evaluators/operations_evaluators.py` — evaluator kept
- `src/` — all core agent code untouched
- `tests/` — no eval references

## Summary

| Metric | Before | After |
|---|---|---|
| Custom evaluators | 9 | 6 |
| Distinct patterns demonstrated | 5 | 5 |
| Base cases | 10 | 5 |
| Marketing cases | 5 | 2 |
| Operations cases | 5 | 2 |
| Total cases | 20 | 9 |
| Files changed | — | 8 |
