#!/usr/bin/env python3
"""Aggregate grading.json under iteration-<N>/ into benchmark.json (+ .md)."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def calculate_stats(values: list) -> dict:
    """Mean/stddev/min/max; skips None for numeric fields."""
    nums = [float(x) for x in values if x is not None and isinstance(x, (int, float))]
    if not nums:
        return {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0}
    n = len(nums)
    mean = sum(nums) / n
    if n > 1:
        variance = sum((x - mean) ** 2 for x in nums) / (n - 1)
        stddev = math.sqrt(variance)
    else:
        stddev = 0.0
    return {
        "mean": round(mean, 4),
        "stddev": round(stddev, 4),
        "min": round(min(nums), 4),
        "max": round(max(nums), 4),
    }


def _grading_metrics(grading: dict) -> dict:
    summary = grading.get("summary") or {}
    if summary.get("total") is not None:
        return {
            "pass_rate": float(summary.get("pass_rate", 0.0)),
            "passed": int(summary.get("passed", 0)),
            "failed": int(summary.get("failed", 0)),
            "total": int(summary.get("total", 0)),
        }
    exps = grading.get("expectations", [])
    total = len(exps)
    passed = sum(1 for e in exps if e.get("passed"))
    pr = (passed / total) if total else 0.0
    return {"pass_rate": pr, "passed": passed, "failed": total - passed, "total": total}


def load_iteration_runs(iteration_dir: Path) -> dict:
    """Return {configuration: [result dicts]}."""
    results: dict = {}
    reserved = {"benchmark.json", "benchmark.md", "feedback.json", "iteration.json"}
    for eval_dir in sorted(p for p in iteration_dir.iterdir() if p.is_dir()):
        if eval_dir.name in reserved:
            continue
        for side_dir in sorted(eval_dir.iterdir()):
            if not side_dir.is_dir():
                continue
            cfg = side_dir.name
            if cfg not in ("with", "without", "old_skill"):
                continue
            if cfg not in results:
                results[cfg] = []
            for run_dir in sorted(side_dir.glob("run-*")):
                grading_path = run_dir / "grading.json"
                if not grading_path.is_file():
                    continue
                try:
                    grading = json.loads(grading_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    continue
                gm = _grading_metrics(grading)
                time_seconds = 0.0
                tokens_val = None
                timing_path = run_dir / "timing.json"
                if timing_path.is_file():
                    try:
                        tj = json.loads(timing_path.read_text(encoding="utf-8"))
                        time_seconds = float(tj.get("total_duration_seconds", 0.0))
                        tokens_val = tj.get("total_tokens")
                    except json.JSONDecodeError:
                        pass
                raw_expectations = grading.get("expectations", [])
                notes_summary = grading.get("user_notes_summary", {})
                notes = []
                notes.extend(notes_summary.get("uncertainties", []))
                notes.extend(notes_summary.get("needs_review", []))
                notes.extend(notes_summary.get("workarounds", []))
                results[cfg].append(
                    {
                        "eval_id": eval_dir.name,
                        "run_number": int(run_dir.name.split("-")[1])
                        if run_dir.name.startswith("run-")
                        else 0,
                        "pass_rate": gm["pass_rate"],
                        "passed": gm["passed"],
                        "failed": gm["failed"],
                        "total": gm["total"],
                        "time_seconds": time_seconds,
                        "tokens": tokens_val,
                        "tool_calls": grading.get("execution_metrics", {}).get("total_tool_calls", 0),
                        "errors": grading.get("execution_metrics", {}).get("errors_encountered", 0),
                        "expectations": raw_expectations,
                        "notes": notes,
                    }
                )
    return results


def aggregate_results(results: dict) -> dict:
    run_summary = {}
    _prio = {"with": 0, "new_skill": 1, "without": 2, "old_skill": 3}
    configs = sorted(results.keys(), key=lambda x: _prio.get(x, 99))
    for cfg in configs:
        runs = results.get(cfg, [])
        if not runs:
            run_summary[cfg] = {
                "pass_rate": {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0},
                "time_seconds": {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0},
                "tokens": {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0},
            }
            continue
        pass_rates = [r["pass_rate"] for r in runs]
        times = [r["time_seconds"] for r in runs]
        tokens = [r.get("tokens") for r in runs]
        token_stats = calculate_stats([t for t in tokens if t is not None])
        if all(t is None for t in tokens):
            token_stats = {"mean": None, "stddev": None, "min": None, "max": None}
        run_summary[cfg] = {
            "pass_rate": calculate_stats(pass_rates),
            "time_seconds": calculate_stats(times),
            "tokens": token_stats,
        }

    primary = {}
    baseline = {}
    if len(configs) >= 2:
        primary = run_summary.get(configs[0], {})
        baseline = run_summary.get(configs[1], {})
    elif len(configs) == 1:
        primary = run_summary.get(configs[0], {})

    d_pr = float(primary.get("pass_rate", {}).get("mean", 0.0)) - float(
        baseline.get("pass_rate", {}).get("mean", 0.0)
    )
    d_time = float(primary.get("time_seconds", {}).get("mean", 0.0)) - float(
        baseline.get("time_seconds", {}).get("mean", 0.0)
    )
    p_tm = primary.get("tokens", {}) or {}
    b_tm = baseline.get("tokens", {}) or {}
    p_m, b_m = p_tm.get("mean"), b_tm.get("mean")
    if p_m is None or b_m is None:
        tok_delta = "n/a"
    else:
        tok_delta = f"{float(p_m) - float(b_m):+.0f}"

    run_summary["delta"] = {
        "pass_rate": f"{d_pr:+.2f}",
        "time_seconds": f"{d_time:+.1f}",
        "tokens": tok_delta,
    }
    return run_summary


def generate_benchmark(
    iteration_dir: Path,
    skill_name: str = "",
    skill_path: str = "",
) -> dict:
    results = load_iteration_runs(iteration_dir)
    run_summary = aggregate_results(results)
    runs_out = []
    for cfg in sorted(results.keys()):
        for result in results[cfg]:
            tok = result.get("tokens")
            runs_out.append(
                {
                    "eval_id": result["eval_id"],
                    "configuration": cfg,
                    "run_number": result["run_number"],
                    "result": {
                        "pass_rate": result["pass_rate"],
                        "passed": result["passed"],
                        "failed": result["failed"],
                        "total": result["total"],
                        "time_seconds": result["time_seconds"],
                        "tokens": 0 if tok is None else tok,
                        "tool_calls": result.get("tool_calls", 0),
                        "errors": result.get("errors", 0),
                    },
                    "expectations": result["expectations"],
                    "notes": result["notes"],
                }
            )
    eval_ids = sorted({r["eval_id"] for r in runs_out})
    return {
        "metadata": {
            "skill_name": skill_name or "<skill-name>",
            "skill_path": skill_path or "<path/to/skill>",
            "executor_model": "<model-name>",
            "analyzer_model": "<model-name>",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "evals_run": eval_ids,
            "runs_per_configuration": 1,
        },
        "runs": runs_out,
        "run_summary": run_summary,
        "notes": [],
    }


def generate_markdown(benchmark: dict) -> str:
    metadata = benchmark["metadata"]
    run_summary = benchmark["run_summary"]
    _prio = {"with": 0, "new_skill": 1, "without": 2, "old_skill": 3}
    configs = sorted((k for k in run_summary if k != "delta"), key=lambda x: _prio.get(x, 99))
    config_a = configs[0] if len(configs) >= 1 else "config_a"
    config_b = configs[1] if len(configs) >= 2 else "config_b"
    label_a = config_a.replace("_", " ").title()
    label_b = config_b.replace("_", " ").title()

    lines = [
        f"# Skill Benchmark: {metadata['skill_name']}",
        "",
        f"**Model**: {metadata['executor_model']}",
        f"**Date**: {metadata['timestamp']}",
        f"**Evals**: {', '.join(map(str, metadata['evals_run']))} ({metadata['runs_per_configuration']} runs each per configuration)",
        "",
        "## Summary",
        "",
        f"| Metric | {label_a} | {label_b} | Delta |",
        "|--------|------------|---------------|-------|",
    ]
    a_summary = run_summary.get(config_a, {})
    b_summary = run_summary.get(config_b, {})
    delta = run_summary.get("delta", {})
    a_pr = a_summary.get("pass_rate", {})
    b_pr = b_summary.get("pass_rate", {})
    lines.append(
        f"| Pass Rate | {a_pr.get('mean', 0)*100:.0f}% ± {a_pr.get('stddev', 0)*100:.0f}% | "
        f"{b_pr.get('mean', 0)*100:.0f}% ± {b_pr.get('stddev', 0)*100:.0f}% | {delta.get('pass_rate', '—')} |"
    )
    a_time = a_summary.get("time_seconds", {})
    b_time = b_summary.get("time_seconds", {})
    lines.append(
        f"| Time | {a_time.get('mean', 0):.1f}s ± {a_time.get('stddev', 0):.1f}s | "
        f"{b_time.get('mean', 0):.1f}s ± {b_time.get('stddev', 0):.1f}s | {delta.get('time_seconds', '—')}s |"
    )
    a_tokens = a_summary.get("tokens", {})
    b_tokens = b_summary.get("tokens", {})
    fmt = lambda m: (  # noqa: E731
        "n/a"
        if m.get("mean") is None
        else f"{m.get('mean', 0):.0f} ± {m.get('stddev', 0):.0f}"
    )
    lines.append(f"| Tokens | {fmt(a_tokens)} | {fmt(b_tokens)} | {delta.get('tokens', '—')} |")
    if benchmark.get("notes"):
        lines.extend(["", "## Notes", ""])
        for note in benchmark["notes"]:
            lines.append(f"- {note}")
    lines.append("")
    lines.append("_Token counts may read as n/a when the active adapter does not expose usage (D-006)._")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate iteration-* grading into benchmark.json")
    parser.add_argument("--iteration", type=int, required=True)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--skill-name", default="")
    parser.add_argument("--skill-path", default="")
    parser.add_argument("-o", "--output", type=Path, default=None)
    args = parser.parse_args()
    iteration_dir = args.workspace / f"iteration-{args.iteration}"
    if not iteration_dir.is_dir():
        print(f"Directory not found: {iteration_dir}", file=sys.stderr)
        sys.exit(1)
    benchmark = generate_benchmark(iteration_dir, args.skill_name, args.skill_path)
    out_json = args.output or (iteration_dir / "benchmark.json")
    out_md = out_json.with_suffix(".md")
    out_json.write_text(json.dumps(benchmark, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(generate_markdown(benchmark), encoding="utf-8")
    print(f"Generated: {out_json}")
    print(f"Generated: {out_md}")


if __name__ == "__main__":
    main()
