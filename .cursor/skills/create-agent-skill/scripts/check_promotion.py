"""Phase F gate: promotion thresholds from ``config/thresholds.json``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _skill_root(here: Path) -> Path:
    return here.resolve().parents[1]


def _candidate_config(run_summary: dict) -> str:
    for key in ("with_skill",):
        if key in run_summary:
            return key
    return "with_skill"


def _baseline_config(run_summary: dict) -> str:
    for key in ("without_skill", "old_skill"):
        if key in run_summary:
            return key
    return "without_skill"


def _critical_failures(benchmark: dict, candidate_cfg: str) -> int:
    crit = 0
    for run in benchmark.get("runs", []):
        if run.get("configuration") != candidate_cfg:
            continue
        # Prefer the explicit expectation_summary produced by aggregate_benchmark;
        # fall back to re-scanning raw expectations for older iterations.
        summary = run.get("expectation_summary")
        if isinstance(summary, dict) and "critical_failed" in summary:
            crit += int(summary.get("critical_failed") or 0)
            continue
        for exp in run.get("expectations", []):
            if exp.get("critical") and not exp.get("passed", False):
                crit += 1
    return crit


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase F promotion gate")
    parser.add_argument("--iteration", type=int, required=True)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    args = parser.parse_args()

    skill_root = _skill_root(Path(__file__))
    thresholds = json.loads(
        (skill_root / "config" / "thresholds.json").read_text(encoding="utf-8")
    )
    iteration_dir = args.workspace / f"iteration-{args.iteration}"
    bench_path = iteration_dir / "benchmark.json"
    feedback_path = iteration_dir / "feedback.json"

    if not bench_path.is_file():
        print(f"missing {bench_path}", file=sys.stderr)
        sys.exit(1)

    benchmark = json.loads(bench_path.read_text(encoding="utf-8"))
    run_summary = benchmark.get("run_summary", {})

    candidate_cfg = _candidate_config(run_summary)
    baseline_cfg = _baseline_config(run_summary)
    candidate = run_summary.get(candidate_cfg, {})
    baseline = run_summary.get(baseline_cfg, {})

    c_pr = float(candidate.get("pass_rate", {}).get("mean", 0.0))
    b_pr = float(baseline.get("pass_rate", {}).get("mean", 0.0))
    lift_pp = (c_pr - b_pr) * 100.0

    crit = _critical_failures(benchmark, candidate_cfg)

    errors: list = []
    if c_pr < float(thresholds["min_candidate_pass_rate"]):
        errors.append(
            f"candidate pass_rate {c_pr:.3f} < min {thresholds['min_candidate_pass_rate']}"
        )
    if lift_pp < float(thresholds["min_lift_vs_baseline_pp"]):
        errors.append(
            f"lift {lift_pp:.1f} pp < min {thresholds['min_lift_vs_baseline_pp']} pp"
        )
    if crit > int(thresholds["max_critical_failures"]):
        errors.append(
            f"critical failures {crit} > max {thresholds['max_critical_failures']}"
        )

    if thresholds.get("require_feedback_complete", True):
        if not feedback_path.is_file():
            errors.append(f"missing {feedback_path}")
        else:
            fb = json.loads(feedback_path.read_text(encoding="utf-8"))
            if fb.get("status") != "complete":
                errors.append("feedback.json status must be complete")

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
