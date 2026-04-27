## Eval pipeline

1. The Single Entrypoint

- There is one runner: `pba-agent/evals/run_evals.py`. 
- It runs in two modes, controlled by the --live flag:

2. The Step-by-Step Sequence (identical for every agent)
For each entry in the datasets dict (base, operations, hr, voice):

```
[1] Build the agent      ──→ agents[name]   (factory: _make_*_agent)
[2] Load the dataset     ──→ Dataset.from_file(<name>_cases.yaml,
                                custom_evaluator_types=ALL_CUSTOM_EVALUATORS)
[3] Wrap as task         ──→ _make_task(agent, deps, use_test_model)
                              (in TestModel mode, overrides the spec'd model)
[4] Run                  ──→ report = ds.evaluate_sync(task)
                              ├── for each case in dataset:
                              │     │
                              │     ├── call task(case.inputs) → output
                              │     │
                              │     └── for each evaluator (case-level + dataset-level):
                              │           run on (input, output, metadata) → ✔ or ✗
                              │
                              └── prints summary table + failures
[5] If --live: pickle the report into evals/runs/<ts>/<name>_report.pkl
[6] Set all_passed = False if any case raised; sys.exit(1) at end
```

- Every step is the same for HR, operations, base. The only thing that differs per agent is which dataset YAML and which factory are wired into the dicts.