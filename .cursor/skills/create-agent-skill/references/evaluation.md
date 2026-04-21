# Evaluation

- **Trigger eval:** Measures whether a skill description should fire for labeled queries. Implemented by **`eval-harness/scripts/run_eval.py`** in `trigger` mode.
- **Dual runs:** Candidate vs baseline under **`iteration-<N>/<eval-id>/`**, with sides **`with_skill`**, **`without_skill`**, and **`old_skill`** (see **`references/execution-contract.md`** and **`references/schemas/benchmark.schema.json`**).
- **Grading:** Each run should contain **`grading.json`** conforming to **`references/schemas/grading.schema.json`** (`assertion_id` required; `critical` optional).
- **Promotion:** Numeric thresholds live only in **`config/thresholds.json`**. Phase F is **`scripts/check_promotion.py`**.
