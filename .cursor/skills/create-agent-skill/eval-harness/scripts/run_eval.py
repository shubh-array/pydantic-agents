#!/usr/bin/env python3
"""Run trigger evaluation (adapter-backed) or scaffold dual-run layout."""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from adapters import get_active_adapter
from scripts.utils import parse_skill_md


def find_project_root() -> Path:
    """Walk up from cwd for `.claude/` (Claude Code); else cwd."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / ".claude").is_dir():
            return parent
    return current


def normalize_eval_set(raw: object) -> list:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and "queries" in raw:
        return raw["queries"]
    raise ValueError("eval set must be a JSON array or object with 'queries'")


def _run_trigger_for_query(
    query: str,
    skill_description: str,
    timeout: int,
) -> bool:
    adapter = get_active_adapter()
    return bool(adapter.evaluate_trigger(skill_description, query)["triggered"])


def run_eval(
    eval_set: list,
    skill_name: str,
    description: str,
    num_workers: int,
    timeout: int,
    runs_per_query: int = 1,
    trigger_threshold: float = 0.5,
    project_root: Path | None = None,
    model: str | None = None,
) -> dict:
    _ = (project_root, model)
    results_map: dict = {}
    with ThreadPoolExecutor(max_workers=max(1, num_workers)) as ex:
        future_to_meta = {}
        for item in eval_set:
            for _ in range(runs_per_query):
                fut = ex.submit(
                    _run_trigger_for_query,
                    item["query"],
                    description,
                    timeout,
                )
                future_to_meta[fut] = item

        for fut in as_completed(future_to_meta):
            item = future_to_meta[fut]
            q = item["query"]
            if q not in results_map:
                results_map[q] = {"item": item, "triggers": []}
            try:
                results_map[q]["triggers"].append(fut.result())
            except Exception as exc:  # noqa: BLE001
                print(f"Warning: query failed: {exc}", file=sys.stderr)
                results_map[q]["triggers"].append(False)

    results = []
    for query, data in results_map.items():
        item = data["item"]
        triggers = data["triggers"]
        trigger_rate = sum(triggers) / len(triggers) if triggers else 0.0
        should_trigger = item["should_trigger"]
        if should_trigger:
            did_pass = trigger_rate >= trigger_threshold
        else:
            did_pass = trigger_rate < trigger_threshold
        results.append(
            {
                "query": query,
                "should_trigger": should_trigger,
                "trigger_rate": trigger_rate,
                "triggers": sum(triggers),
                "runs": len(triggers),
                "pass": did_pass,
            }
        )

    passed = sum(1 for r in results if r["pass"])
    total = len(results)
    return {
        "skill_name": skill_name,
        "description": description,
        "results": results,
        "summary": {"total": total, "passed": passed, "failed": total - passed},
    }


def cmd_trigger(args: argparse.Namespace) -> None:
    raw = json.loads(Path(args.eval_set).read_text(encoding="utf-8"))
    eval_set = normalize_eval_set(raw)
    skill_path = Path(args.skill_path)
    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md found at {skill_path}", file=sys.stderr)
        sys.exit(1)
    name, original_description, _content = parse_skill_md(skill_path)
    description = args.description or original_description
    if args.verbose:
        print(f"Evaluating: {description}", file=sys.stderr)
    output = run_eval(
        eval_set=eval_set,
        skill_name=name,
        description=description,
        num_workers=args.num_workers,
        timeout=args.timeout,
        runs_per_query=args.runs_per_query,
        trigger_threshold=args.trigger_threshold,
    )
    if args.verbose:
        summary = output["summary"]
        print(f"Results: {summary['passed']}/{summary['total']} passed", file=sys.stderr)
        for r in output["results"]:
            status = "PASS" if r["pass"] else "FAIL"
            rate_str = f"{r['triggers']}/{r['runs']}"
            print(
                f"  [{status}] rate={rate_str} expected={r['should_trigger']}: {r['query'][:70]}",
                file=sys.stderr,
            )
    print(json.dumps(output, indent=2))


def cmd_dual(args: argparse.Namespace) -> None:
    """Create iteration run dirs and invoke adapter.invoke_subagent per eval side."""
    workspace = Path(args.workspace).resolve()
    iteration_dir = workspace / f"iteration-{args.iteration}"
    manifest = iteration_dir / "iteration.json"
    if not manifest.is_file():
        print(f"missing {manifest}", file=sys.stderr)
        sys.exit(1)
    meta = json.loads(manifest.read_text(encoding="utf-8"))
    skill_path = Path(meta.get("skill_path", args.skill_path)).resolve()
    evals_path = Path(meta.get("evals_path", args.evals)).resolve()
    agent_prompt = str(Path(meta.get("agent_prompt", args.agent_prompt)).resolve())
    raw = json.loads(evals_path.read_text(encoding="utf-8"))
    cases = normalize_eval_set(raw)
    baseline_type = meta.get("baseline_type", "without_skill")
    sides = ["with", "without"]
    if baseline_type == "old_skill":
        sides = ["with", "old_skill"]
    adapter = get_active_adapter()
    for case in cases:
        eid = str(case.get("eval_id", case.get("id", "eval")))
        user_input = str(case.get("prompt", ""))
        for side in sides:
            run_dir = iteration_dir / eid / side / "run-1"
            (run_dir / "outputs").mkdir(parents=True, exist_ok=True)
            res = adapter.invoke_subagent(
                agent_prompt,
                user_input,
                str(run_dir),
                timeout_s=args.timeout,
            )
            (run_dir / "transcript.txt").write_text(res["stdout"] or "", encoding="utf-8")
            timing = {
                "total_duration_seconds": (res["duration_ms"] or 0) / 1000.0,
                "total_tokens": None,
            }
            (run_dir / "timing.json").write_text(json.dumps(timing, indent=2) + "\n", encoding="utf-8")
            em = {
                "eval_id": eid,
                "run_id": f"{eid}-{side}-1",
                "side": side,
                "skill_name": parse_skill_md(skill_path)[0],
            }
            (run_dir / "eval_metadata.json").write_text(json.dumps(em, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Eval harness: trigger or dual mode")
    sub = parser.add_subparsers(dest="mode", required=True)

    p_t = sub.add_parser("trigger", help="Description trigger eval")
    p_t.add_argument("--eval-set", required=True, type=Path)
    p_t.add_argument("--skill-path", required=True, type=Path)
    p_t.add_argument("--description", default=None)
    p_t.add_argument("--num-workers", type=int, default=4)
    p_t.add_argument("--timeout", type=int, default=120)
    p_t.add_argument("--runs-per-query", type=int, default=1)
    p_t.add_argument("--trigger-threshold", type=float, default=0.5)
    p_t.add_argument("--verbose", action="store_true")

    p_d = sub.add_parser("dual", help="Scaffold dual runs via adapter.invoke_subagent")
    p_d.add_argument("--iteration", type=int, required=True)
    p_d.add_argument("--workspace", type=Path, default=Path.cwd())
    p_d.add_argument("--skill-path", type=Path, default=Path("."))
    p_d.add_argument("--evals", type=Path, default=Path("evals/evals.json"))
    p_d.add_argument("--agent-prompt", type=Path, default=_ROOT / "agents" / "analyzer.md")
    p_d.add_argument("--timeout", type=int, default=600)

    args = parser.parse_args()
    if args.mode == "trigger":
        cmd_trigger(args)
    else:
        cmd_dual(args)


if __name__ == "__main__":
    main()
