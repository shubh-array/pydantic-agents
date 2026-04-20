# Evaluation

- **Trigger eval:** measures whether a skill description should fire for labeled queries. Implemented by `eval-harness/scripts/run_eval.py trigger`.
- **Dual runs:** candidate vs baseline directories under `iteration-<N>/<eval-id>/with|without|old_skill/run-*`. See `references/execution-contract.md`.
- **Grading:** each run should contain `grading.json` conforming to `references/schemas/grading.schema.json` (`assertion_id` required; `critical` optional).
- **Promotion:** numeric thresholds live only in `config/thresholds.json`. Phase F is `scripts/check_promotion.py`.
