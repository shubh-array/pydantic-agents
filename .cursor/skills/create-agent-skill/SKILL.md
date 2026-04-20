---
name: create-agent-skill
description: Create, evaluate, and improve Cursor agent skills using an adapter-backed harness aligned with upstream skill-creator patterns.
license: See LICENSE.txt
---

# create-agent-skill

Router skill: follow **references/execution-contract.md** for the exact phase → command map. Agent-specific CLI details live under **`adapters/<active>/recipes.md`** (active adapter from `config/active_agent` or `AGENT_SKILL_ADAPTER`).

## Quick path

1. **Author or edit** a target skill under test (separate directory).
2. **Phase A** — `python scripts/quick_validate.py <skill-dir>`
3. **Phase C (trigger)** — `python eval-harness/scripts/run_eval.py trigger --eval-set <evals.json> --skill-path <skill-dir>`
4. **Phase D** — `python eval-harness/scripts/aggregate_benchmark.py --iteration N --workspace <workspace>` then `python scripts/check_iteration.py --iteration N --workspace <workspace>`
5. **Phase E** — `python eval-harness/viewer/generate_review.py <workspace> --iteration N`
6. **Phase F** — `python scripts/check_promotion.py --iteration N --workspace <workspace>`

Promotion thresholds: **only** `config/thresholds.json` (do not copy numbers into this file).

## Progressive disclosure

- `references/getting-started.md` — setup
- `references/evaluation.md` — eval concepts
- `references/schemas/*.schema.json` — JSON contracts
- `adapters/cursor/recipes.md` or `adapters/claude_code/recipes.md` — CLI invocation recipes

## Upstream provenance

See `docs/create-agent-skill/upstream-deltas.md` and `docs/create-agent-skill/upstream-sync.md` at repo root (outside this skill folder).
