#!/usr/bin/env python3
"""Improve a skill description based on eval results (adapter-backed)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from adapters import get_active_adapter
from scripts.utils import parse_skill_md


def improve_description(
    skill_name: str,
    skill_content: str,
    current_description: str,
    eval_results: dict,
    history: list,
    test_results: dict | None = None,
    log_dir: Path | None = None,
    iteration: int | None = None,
    model: str = "",
) -> str:
    _ = (skill_name, skill_content, test_results, history, model)
    failed_triggers = [r for r in eval_results["results"] if r["should_trigger"] and not r["pass"]]
    false_triggers = [r for r in eval_results["results"] if not r["should_trigger"] and not r["pass"]]
    failing_queries = [r["query"] for r in failed_triggers]
    passing_queries = [r["query"] for r in false_triggers]
    adapter = get_active_adapter()
    text = adapter.generate_improved_description(
        current_description,
        failing_queries,
        passing_queries,
    )
    match = re.search(r"<new_description>(.*?)</new_description>", text, re.DOTALL)
    description = match.group(1).strip().strip('"') if match else text.strip().strip('"')
    if len(description) > 1024:
        description = description[:1024]
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"improve_iter_{iteration or 'unknown'}.json"
        log_file.write_text(
            json.dumps(
                {
                    "iteration": iteration,
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
    parser = argparse.ArgumentParser(description="Improve a skill description based on eval results")
    parser.add_argument("--eval-results", required=True, type=Path)
    parser.add_argument("--skill-path", required=True, type=Path)
    parser.add_argument("--history", default=None)
    parser.add_argument("--model", default="", help="Ignored for adapter-backed path; kept for CLI compatibility")
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
