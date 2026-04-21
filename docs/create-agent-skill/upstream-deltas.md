# Upstream deltas (`create-agent-skill` vs `skill-creator`)

This document records **intentional, active divergences** from the upstream [`skill-creator`](../../.cursor/skills/skill-creator/) skill. After Phase 2 convergence, many historical differences are resolved; only deliberate differences that remain are listed here.

## Active divergences

### D-001: `assertion_id` required on grading expectations

**Status:** Active  
**Files:** `.cursor/skills/create-agent-skill/references/schemas/grading.schema.json`  
**Description:** `grading.schema.json` requires `assertion_id` on each expectation item. Upstream does not require it.  
**Rationale:** Enables `assertion_id` parity checking across runs (Phase D gate).  
**Sync risk:** Low — additive requirement; upstream artifacts without `assertion_id` will be rejected.

### D-002: Optional `critical` on grading expectations

**Status:** Active  
**Files:** `.cursor/skills/create-agent-skill/references/schemas/grading.schema.json`  
**Description:** `grading.schema.json` has an optional `critical` field on expectations. Upstream does not.  
**Rationale:** Enables the promotion gate to count critical failures without re-scanning raw expectations.  
**Sync risk:** Low — purely additive.

### D-013: `expectation_summary` on benchmark runs

**Status:** Active  
**Files:** `.cursor/skills/create-agent-skill/references/schemas/benchmark.schema.json`  
**Description:** `benchmark.json` runs include `expectation_summary` with `{ assertion_ids, critical_total, critical_failed }`. Upstream does not have this.  
**Rationale:** Phase F promotion gate counts critical failures without re-scanning raw expectations.  
**Sync risk:** Low — additive field.

### D-017: Structured evals schema (trigger/execution union)

**Status:** Active  
**Files:** `.cursor/skills/create-agent-skill/references/schemas/evals.schema.json`  
**Description:** `evals.schema.json` uses a union of trigger/execution cases with structured expectations. Upstream uses `{ skill_name, evals[] }` with string expectations.  
**Rationale:** Intentional structural divergence accepted because `evals.json` is consumed at the entry boundary (Phase A/B), not inside shared pipeline scripts.  
**Sync risk:** Medium — requires manual review if upstream changes the evals shape.

### D-018: Adapter timing extension fields

**Status:** Active  
**Files:** `.cursor/skills/create-agent-skill/references/schemas/timing.schema.json`  
**Description:** `timing.schema.json` includes adapter extension fields (`total_duration_api_seconds`, `tokens_detail`). Upstream only has basic subagent notification fields.  
**Rationale:** Adapters expose richer timing data than raw subagent notifications.  
**Sync risk:** Low — additive fields.

## Resolved divergences (removed after Phase 2)

The following were previously documented but are **no longer** active after Phase 2 convergence:

- Config directory shorthand (`with` / `without` → `with_skill` / `without_skill`)
- `eval_metadata` per-run (→ per-eval)
- Vocabulary drift (`assertions` → `expectations`)
- `AGENT_SKILL_ADAPTER` environment variable override
- Viewer flat-layout workaround (D-016)
