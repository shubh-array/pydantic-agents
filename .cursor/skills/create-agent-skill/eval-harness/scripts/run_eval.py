#!/usr/bin/env python3
"""Run trigger evaluation (Phase C trigger-mode) or dual-execution scaffold.

Core is agent-agnostic; subprocess / parsing / tokens are the adapter's job.
"""

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


_MARKER_DIRS = (".cursor", ".claude", ".git")


def find_project_root() -> Path:
    """Walk up from cwd looking for any known project-root marker dir.

    Agent-agnostic: any of ``.cursor`` / ``.claude`` / ``.git`` counts.
    """
    current = Path.cwd()
    for parent in [current, *current.parents]:
        for marker in _MARKER_DIRS:
            if (parent / marker).is_dir():
                return parent
    return current


def normalize_eval_set(raw: object) -> list:
    if isinstance(raw, list):
        return raw
    raise ValueError("eval set must be a JSON array")


def _run_trigger_for_query(query: str, skill_description: str) -> bool:
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
    _ = (project_root, model, timeout)
    results_map: dict = {}
    with ThreadPoolExecutor(max_workers=max(1, num_workers)) as ex:
        future_to_item = {}
        for item in eval_set:
            for _ in range(runs_per_query):
                fut = ex.submit(_run_trigger_for_query, item["query"], description)
                future_to_item[fut] = item
        for fut in as_completed(future_to_item):
            item = future_to_item[fut]
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
        rate = sum(triggers) / len(triggers) if triggers else 0.0
        expected = item["should_trigger"]
        did_pass = rate >= trigger_threshold if expected else rate < trigger_threshold
        results.append(
            {
                "query": query,
                "should_trigger": expected,
                "trigger_rate": rate,
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
        s = output["summary"]
        print(f"Results: {s['passed']}/{s['total']} passed", file=sys.stderr)
    print(json.dumps(output, indent=2))


def _validate_iteration_manifest(meta: dict) -> None:
    """Validate ``iteration.json`` against its JSON schema (hard requirement).

    The schema lives at ``references/schemas/iteration.schema.json`` and
    documents every field the harness understands; failing here is much more
    helpful than letting a KeyError bubble up three frames deeper.
    """
    try:
        import jsonschema  # type: ignore
    except ImportError as exc:  # pragma: no cover - dev dep
        print(
            f"jsonschema required for iteration.json validation: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)
    schema_path = _ROOT / "references" / "schemas" / "iteration.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(meta, schema)
    except jsonschema.ValidationError as exc:
        print(f"iteration.json schema error: {exc.message}", file=sys.stderr)
        sys.exit(1)


def _read_skill_content(skill_path: Path) -> str:
    """Return the raw SKILL.md content used to instruct a with_skill run."""
    skill_md = skill_path / "SKILL.md"
    if not skill_md.is_file():
        print(f"missing SKILL.md at {skill_md}", file=sys.stderr)
        sys.exit(1)
    return skill_md.read_text(encoding="utf-8")


def cmd_dual(args: argparse.Namespace) -> None:
    """Orchestrate per-eval dual runs through the active adapter.

    Isolation contract (H1):
        with_skill  → adapter receives the candidate SKILL.md content via
                      ``skill_content`` substitution.
        without_skill → adapter receives ``skill_content=None``; the executor
                      template renders an empty ``<skill>`` block so the
                      agent solves the task from first principles.
        old_skill  → adapter receives the snapshot SKILL.md content from
                      ``old_skill_path`` in iteration.json.
    """
    workspace = Path(args.workspace).resolve()
    iteration_dir = workspace / f"iteration-{args.iteration}"
    manifest = iteration_dir / "iteration.json"
    if not manifest.is_file():
        print(f"missing {manifest}", file=sys.stderr)
        sys.exit(1)
    meta = json.loads(manifest.read_text(encoding="utf-8"))
    _validate_iteration_manifest(meta)
    skill_path = Path(meta.get("skill_path", args.skill_path)).resolve()
    evals_path = Path(meta.get("evals_path", args.evals)).resolve()
    agent_prompt = str(
        Path(meta.get("agent_prompt", args.agent_prompt)).resolve()
    )
    raw = json.loads(evals_path.read_text(encoding="utf-8"))
    cases = normalize_eval_set(raw)
    baseline_type = meta.get("baseline_type", "without_skill")
    sides = ["with_skill", "without_skill"]
    if baseline_type == "old_skill":
        sides = ["with_skill", "old_skill"]
    runs_per_config = int(meta.get("runs_per_configuration", 1))
    adapter = get_active_adapter()
    skill_name = parse_skill_md(skill_path)[0]

    with_skill_content = _read_skill_content(skill_path)
    old_skill_content: str | None = None
    if baseline_type == "old_skill":
        old_path_raw = meta.get("old_skill_path")
        if not old_path_raw:
            print(
                "iteration.json has baseline_type='old_skill' but no 'old_skill_path'",
                file=sys.stderr,
            )
            sys.exit(1)
        old_skill_content = _read_skill_content(Path(old_path_raw).resolve())

    side_to_skill = {
        "with_skill": with_skill_content,
        "without_skill": None,
        "old_skill": old_skill_content,
    }
    for case in cases:
        eid = str(case.get("eval_id", case.get("id", "eval")))
        user_input = str(case.get("prompt", ""))
        expected = list(case.get("expectations", []) or [])
        files = list(case.get("files", []) or [])

        eval_dir = iteration_dir / eid
        eval_dir.mkdir(parents=True, exist_ok=True)
        meta_path = eval_dir / "eval_metadata.json"
        if not meta_path.exists():
            meta_obj: dict = {
                "eval_id": eid,
                "skill_name": skill_name,
                "prompt": user_input,
                "expectations": expected,
            }
            if files:
                meta_obj["files"] = files
            meta_path.write_text(
                json.dumps(meta_obj, indent=2) + "\n",
                encoding="utf-8",
            )

        for side in sides:
            skill_content_for_side = side_to_skill.get(side)
            for r in range(1, runs_per_config + 1):
                run_dir = iteration_dir / eid / side / f"run-{r}"
                outputs_dir = run_dir / "outputs"
                outputs_dir.mkdir(parents=True, exist_ok=True)
                res = adapter.invoke_subagent(
                    agent_prompt,
                    user_input,
                    str(outputs_dir),
                    timeout_s=args.timeout,
                    skill_content=skill_content_for_side,
                )
                transcript_in_outputs = outputs_dir / "transcript.jsonl"
                if transcript_in_outputs.exists():
                    transcript_in_outputs.rename(run_dir / "transcript.jsonl")
                elif not res.get("transcript_path"):
                    # Adapter writes transcript.jsonl for stream adapters. Fall back
                    # to writing raw stdout if the adapter did not set a path.
                    (run_dir / "transcript.jsonl").write_text(
                        res["stdout"] or "", encoding="utf-8"
                    )
                timing = {
                    "total_duration_seconds": (res["duration_ms"] or 0) / 1000.0,
                    "total_duration_api_seconds": (
                        None
                        if res.get("duration_api_ms") is None
                        else (res["duration_api_ms"] or 0) / 1000.0
                    ),
                    "total_tokens": (
                        None
                        if res.get("tokens") is None
                        else (
                            int(res["tokens"].get("input", 0))
                            + int(res["tokens"].get("output", 0))
                        )
                    ),
                    "tokens_detail": res.get("tokens"),
                    "status": res.get("status"),
                    "exit_code": res.get("exit_code"),
                }
                (run_dir / "timing.json").write_text(
                    json.dumps(timing, indent=2) + "\n", encoding="utf-8"
                )


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
    p_d.add_argument(
        "--agent-prompt",
        type=Path,
        default=_ROOT / "agents" / "executor.md",
        help=(
            "Executor template supporting {{USER_INPUT}} and {{SKILL_CONTENT}}."
            " Defaults to agents/executor.md; override only for bespoke flows."
        ),
    )
    p_d.add_argument("--timeout", type=int, default=600)

    args = parser.parse_args()
    if args.mode == "trigger":
        cmd_trigger(args)
    else:
        cmd_dual(args)


if __name__ == "__main__":
    main()
