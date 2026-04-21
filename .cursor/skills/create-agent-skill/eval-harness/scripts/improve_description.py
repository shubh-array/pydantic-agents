#!/usr/bin/env python3
"""Improve a skill description based on eval results (adapter-backed).

The adapter is handed an ``ImprovementContext`` so it can reproduce the
upstream `skill-creator` prompt (skill_name, skill_content, history, train
summary, test summary, failed/false-trigger queries) without pulling any
agent-specific coupling back into core.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from adapters import get_active_adapter
from adapters.base import ImprovementContext
from scripts.utils import parse_skill_md


_MAX_DESCRIPTION_CHARS = 1024


def improve_description(
    skill_name: str,
    skill_content: str,
    current_description: str,
    eval_results: dict,
    history: list,
    test_results: Optional[dict] = None,
    log_dir: Optional[Path] = None,
    iteration: Optional[int] = None,
    model: str = "",
) -> str:
    _ = model
    failed = [
        r for r in eval_results["results"] if r["should_trigger"] and not r["pass"]
    ]
    false = [
        r for r in eval_results["results"] if not r["should_trigger"] and not r["pass"]
    ]
    failing_queries = [r["query"] for r in failed]
    passing_queries = [r["query"] for r in false]

    ctx: ImprovementContext = {
        "skill_name": skill_name,
        "skill_content": skill_content,
        "history": history,
        "train_summary": dict(eval_results.get("summary") or {}),
        "test_summary": (
            dict(test_results.get("summary") or {}) if test_results else None
        ),
        "failing_queries": failed,
        "false_trigger_queries": false,
    }

    adapter = get_active_adapter()
    text = adapter.generate_improved_description(
        current_description,
        failing_queries,
        passing_queries,
        context=ctx,
    )
    match = re.search(r"<new_description>(.*?)</new_description>", text, re.DOTALL)
    description = (
        match.group(1).strip().strip('"') if match else text.strip().strip('"')
    )
    if len(description) > _MAX_DESCRIPTION_CHARS:
        description = description[:_MAX_DESCRIPTION_CHARS]

    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"improve_iter_{iteration or 'unknown'}.json"
        log_file.write_text(
            json.dumps(
                {
                    "iteration": iteration,
                    "failing_queries": failing_queries,
                    "passing_queries": passing_queries,
                    "raw_response": text,
                    "parsed_description": description,
                    "char_count": len(description),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return description


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Improve a skill description based on eval results"
    )
    parser.add_argument("--eval-results", required=True, type=Path)
    parser.add_argument("--skill-path", required=True, type=Path)
    parser.add_argument("--history", default=None)
    parser.add_argument(
        "--model",
        default="",
        help="Ignored for the adapter path; kept for CLI compatibility.",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    skill_path = args.skill_path
    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md found at {skill_path}", file=sys.stderr)
        sys.exit(1)
    eval_results = json.loads(args.eval_results.read_text(encoding="utf-8"))
    history: list = []
    if args.history:
        history = json.loads(Path(args.history).read_text(encoding="utf-8"))
    name, _, content = parse_skill_md(skill_path)
    current_description = eval_results["description"]
    if args.verbose:
        print(f"Current: {current_description}", file=sys.stderr)
    new_description = improve_description(
        skill_name=name,
        skill_content=content,
        current_description=current_description,
        eval_results=eval_results,
        history=history,
    )
    if args.verbose:
        print(f"Improved: {new_description}", file=sys.stderr)
    output = {
        "description": new_description,
        "history": history
        + [
            {
                "description": current_description,
                "passed": eval_results["summary"]["passed"],
                "failed": eval_results["summary"]["failed"],
                "total": eval_results["summary"]["total"],
                "results": eval_results["results"],
            }
        ],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
