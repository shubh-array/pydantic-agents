"""Eval run recording and baseline loading.

Saves each eval run to evals/runs/<timestamp>/ with:
- metadata.json  — git SHA, timestamp, mode, model info
- <agent>_report.pkl — pickled EvaluationReport (for baseline comparison)
- <agent>_summary.json — human-readable per-case results

Loads the most recent previous run as a baseline for diff tables.
"""

from __future__ import annotations

import dataclasses
import json
import pickle
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic_evals.reporting import EvaluationReport

RUNS_DIR = Path(__file__).resolve().parent / "runs"


def _git_sha() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except Exception:
        return "unknown"


def _safe_value(obj: Any) -> Any:
    """Convert non-serializable objects to strings for JSON summary."""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_safe_value(v) for v in obj]
    if isinstance(obj, dict):
        return {str(k): _safe_value(v) for k, v in obj.items()}
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return _safe_value(dataclasses.asdict(obj))
    return str(obj)


def _summarize_report(report: EvaluationReport) -> dict:
    """Extract a JSON-safe summary from an EvaluationReport."""
    cases = []
    for c in report.cases:
        cases.append({
            "name": c.name,
            "inputs": _safe_value(c.inputs),
            "output_type": type(c.output).__name__,
            "assertions": _safe_value(c.assertions),
            "scores": _safe_value(c.scores),
            "labels": _safe_value(c.labels),
            "task_duration_ms": round(c.task_duration * 1000, 1) if c.task_duration else None,
        })
    failures = []
    for f in report.failures:
        failures.append({"name": f.name, "error": f.error_message})

    averages = report.averages()
    avg_dict = None
    if averages:
        avg_dict = {
            "assertions": averages.assertions,
            "task_duration": averages.task_duration,
        }

    return {
        "name": report.name,
        "total_cases": len(report.cases),
        "total_failures": len(report.failures),
        "averages": avg_dict,
        "cases": cases,
        "failures": failures,
    }


def save_run(
    reports: dict[str, EvaluationReport],
    mode: str,
    timestamp: str | None = None,
) -> Path:
    """Persist eval reports to disk. Returns the run directory path."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    run_dir = RUNS_DIR / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "timestamp": timestamp,
        "git_sha": _git_sha(),
        "mode": mode,
        "agents": list(reports.keys()),
    }
    (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

    for agent_name, report in reports.items():
        with open(run_dir / f"{agent_name}_report.pkl", "wb") as f:
            pickle.dump(report, f)
        summary = _summarize_report(report)
        (run_dir / f"{agent_name}_summary.json").write_text(
            json.dumps(summary, indent=2, default=str)
        )

    return run_dir


def load_baseline(exclude_dir: str | None = None) -> dict[str, EvaluationReport] | None:
    """Load the most recent previous run's reports as baselines.

    Returns a dict of {agent_name: EvaluationReport} or None if no
    previous runs exist.  *exclude_dir* is the current run's timestamp
    directory name, so we don't compare against ourselves.
    """
    if not RUNS_DIR.exists():
        return None

    run_dirs = sorted(
        [d for d in RUNS_DIR.iterdir() if d.is_dir() and d.name != exclude_dir],
        reverse=True,
    )
    if not run_dirs:
        return None

    latest = run_dirs[0]
    baselines: dict[str, EvaluationReport] = {}
    for pkl_file in latest.glob("*_report.pkl"):
        agent_name = pkl_file.stem.replace("_report", "")
        try:
            with open(pkl_file, "rb") as f:
                baselines[agent_name] = pickle.load(f)
        except Exception:
            continue

    return baselines if baselines else None
