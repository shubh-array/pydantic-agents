"""Standardized evaluation runner for all PBA domain agents.

Evaluates each domain agent (base, operations, HR, voice) against
YAML-defined test-case datasets using pydantic-evals.

For every agent the runner does the following:

- 1. loads the corresponding Dataset from ``datasets/``,
- 2. wraps the agent in a sync callable via `_make_task`, and
- 3. calls `Dataset.evaluate_sync()` which feeds each case prompt to the agent and scores the output with the custom evaluators registered in `evaluators.py`.

Two modes are supported:

* **CI mode** (default) — swaps the real LLM for ``TestModel`` so tests are
  deterministic and need no API key.  Tools are disabled because TestModel
  generates synthetic arguments that trip the tool stubs.

* **Live mode** (``--live``) — runs against the real OpenAI model with tools
  enabled, optionally traces to Logfire, and persists reports + summaries
  under ``evals/runs/<timestamp>/``.  A ``--baseline`` flag lets you diff
  results against a previous run.

Usage (from pba-agent/ directory):

    # CI mode — uses TestModel, no API key needed, deterministic
    uv run python evals/run_evals.py

    # Live mode — uses the real OpenAI model, records results, sends to Logfire
    env $(cat .env) uv run python evals/run_evals.py --live

    # Live mode, compare against a specific baseline
    env $(cat .env) uv run python evals/run_evals.py --live --baseline 2026-04-24T20-30-00
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pydantic_ai.models.test import TestModel
from pydantic_evals import Dataset

from base_agent import PROMPTS_DIR, _build_agent, compose_prompt, create_base_agent
from deps import AgentDeps
from evaluators import ALL_CUSTOM_EVALUATORS
from models import Failed, IncidentStatus, MarketingDraft
from recording import load_baseline, save_run
from tools.marketing_tools import check_competitor_claims, get_content_calendar, search_brand_assets
from tools.operations_tools import check_deploy_status, query_monitoring, search_runbooks

DATASETS_DIR = Path(__file__).resolve().parent / "datasets"

MARKETING_TOOLS = [search_brand_assets, get_content_calendar, check_competitor_claims]
OPERATIONS_TOOLS = [query_monitoring, check_deploy_status, search_runbooks]


def _make_marketing_agent(*, include_tools: bool = True, model: str | None = None):
    domain_prompt = (PROMPTS_DIR / "marketing-agent-prompt.md").read_text()
    instructions = compose_prompt(domain_prompt)
    return _build_agent(
        "marketing-agent.yaml",
        instructions,
        domain="marketing",
        model=model,
        output_type=[MarketingDraft, Failed],
        tools=MARKETING_TOOLS if include_tools else None,
    )


def _make_operations_agent(*, include_tools: bool = True, model: str | None = None):
    domain_prompt = (PROMPTS_DIR / "operations-agent-prompt.md").read_text()
    instructions = compose_prompt(domain_prompt)
    return _build_agent(
        "operations-agent.yaml",
        instructions,
        domain="operations",
        model=model,
        output_type=[IncidentStatus, Failed],
        tools=OPERATIONS_TOOLS if include_tools else None,
    )


def _make_hr_agent(*, include_tools: bool = False, model: str | None = None):
    """Build the HR agent from the pre-rendered prompt at _generated/hr.md.

    The HR prompt is fully assembled at render time from voice-spec.yaml +
    inlined skills. ``include_tools`` is accepted for symmetry; HR has no
    tools yet in Phase 1.
    """
    _ = include_tools  # reserved for Phase 2 HR tools
    instructions = (PROMPTS_DIR / "_generated" / "hr.md").read_text()
    return _build_agent("hr-agent.yaml", instructions, domain="hr", model=model)


def _make_task(agent, deps: AgentDeps, use_test_model: bool):
    """Return a sync callable (str) -> Any that runs the agent."""

    def task(prompt: str) -> Any:
        if use_test_model:
            with agent.override(model=TestModel()):
                return agent.run_sync(prompt, deps=deps).output
        return agent.run_sync(prompt, deps=deps).output

    return task


def _configure_logfire_for_evals() -> None:
    """Enable Logfire tracing when LOGFIRE_TOKEN is present."""
    import os

    if not os.environ.get("LOGFIRE_TOKEN"):
        return
    import logfire

    logfire.configure(
        service_name="pba-agent-evals",
        send_to_logfire=True,
    )
    logfire.instrument_pydantic_ai(version=3)
    print("Logfire: tracing enabled (traces will appear in Logfire cloud)\n")


def _parse_args() -> tuple[bool, str | None]:
    """Parse CLI flags. Returns (use_test_model, baseline_timestamp)."""
    use_test_model = "--live" not in sys.argv
    baseline_ts = None
    for i, arg in enumerate(sys.argv):
        if arg == "--baseline" and i + 1 < len(sys.argv):
            baseline_ts = sys.argv[i + 1]
    return use_test_model, baseline_ts


def main() -> None:
    use_test_model, baseline_ts = _parse_args()
    is_live = not use_test_model
    mode = "TestModel (CI)" if use_test_model else "Live model"
    print(f"=== PBA Evaluation Pipeline — {mode} ===\n")

    if is_live:
        _configure_logfire_for_evals()

    deps = AgentDeps(user_name="Evaluator", company="Array Corporation")

    # TestModel generates synthetic tool arguments that trigger ModelRetry in stubs,
    # so tools are only included in live-model mode.  Tool behavior is independently
    # covered by unit tests in tests/.
    agents = {
        "base": create_base_agent(),
        "marketing": _make_marketing_agent(include_tools=is_live),
        "operations": _make_operations_agent(include_tools=is_live),
        "hr": _make_hr_agent(),
        "voice": _make_hr_agent(),
    }

    datasets = {
        "base": "base_agent_cases.yaml",
        "marketing": "marketing_agent_cases.yaml",
        "operations": "operations_agent_cases.yaml",
        "hr": "hr_agent_cases.yaml",
        "voice": "voice_cases.yaml",
    }

    # Load baseline for comparison (live mode only)
    baselines = None
    if is_live:
        if baseline_ts:
            from recording import RUNS_DIR

            baselines = {}
            baseline_dir = RUNS_DIR / baseline_ts
            if baseline_dir.exists():
                import pickle

                for pkl in baseline_dir.glob("*_report.pkl"):
                    name = pkl.stem.replace("_report", "")
                    with open(pkl, "rb") as f:
                        baselines[name] = pickle.load(f)
                print(f"Baseline: loaded from {baseline_ts}\n")
            else:
                print(f"Warning: baseline directory {baseline_ts} not found\n")
                baselines = None
        else:
            baselines = load_baseline()
            if baselines:
                print("Baseline: loaded from most recent previous run\n")

    run_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    reports: dict[str, Any] = {}
    all_passed = True

    for name, dataset_file in datasets.items():
        print(f"\n--- {name.title()} Agent ---\n")
        ds: Dataset[str, Any, Any] = Dataset.from_file(
            DATASETS_DIR / dataset_file,
            custom_evaluator_types=ALL_CUSTOM_EVALUATORS,
        )
        task = _make_task(agents[name], deps, use_test_model)
        report = ds.evaluate_sync(task)
        reports[name] = report

        baseline_report = baselines.get(name) if baselines else None
        report.print(baseline=baseline_report)

        if report.failures:
            all_passed = False
            for f in report.failures:
                print(f"  FAILURE: {f.name} — {f.error_message}")

    # Save results in live mode
    if is_live:
        run_dir = save_run(reports, mode=mode, timestamp=run_timestamp)
        print(f"\nResults saved to: {run_dir.relative_to(run_dir.parent.parent.parent)}")

    print("\n=== Done ===")
    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
