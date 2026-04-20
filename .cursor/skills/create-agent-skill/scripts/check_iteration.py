"""Phase D gate: filesystem + schema + assertion_id parity."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None


def _skill_root(here: Path) -> Path:
    return here.resolve().parents[1]


def _load_schema(skill_root: Path, name: str) -> dict:
    p = skill_root / "references" / "schemas" / name
    return json.loads(p.read_text(encoding="utf-8"))


def _assertion_ids(grading: dict) -> set:
    out: set = set()
    for exp in grading.get("expectations", []):
        aid = exp.get("assertion_id")
        if isinstance(aid, str) and aid:
            out.add(aid)
    return out


def validate_iteration(iteration_dir: Path, skill_root: Path) -> list:
    errors: list = []
    if not iteration_dir.is_dir():
        return [f"iteration dir not found: {iteration_dir}"]

    grading_schema = _load_schema(skill_root, "grading.schema.json")
    benchmark_path = iteration_dir / "benchmark.json"

    if jsonschema is not None and benchmark_path.exists():
        bench_schema = _load_schema(skill_root, "benchmark.schema.json")
        try:
            jsonschema.validate(
                json.loads(benchmark_path.read_text(encoding="utf-8")), bench_schema
            )
        except jsonschema.ValidationError as exc:
            errors.append(f"benchmark.json schema: {exc.message}")

    reserved = {"benchmark.json", "benchmark.md", "feedback.json", "iteration.json"}
    for eval_dir in sorted(p for p in iteration_dir.iterdir() if p.is_dir()):
        if eval_dir.name in reserved:
            continue
        for side in ("with", "without", "old_skill"):
            side_dir = eval_dir / side
            if not side_dir.is_dir():
                continue
            for run_dir in sorted(side_dir.glob("run-*")):
                for name in ("eval_metadata.json", "timing.json", "grading.json"):
                    fp = run_dir / name
                    if not fp.is_file():
                        errors.append(f"missing {fp.relative_to(iteration_dir)}")
                gpath = run_dir / "grading.json"
                if not gpath.is_file():
                    continue
                try:
                    grading = json.loads(gpath.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    errors.append(f"invalid JSON {gpath}: {exc}")
                    continue
                if jsonschema is not None:
                    try:
                        jsonschema.validate(grading, grading_schema)
                    except jsonschema.ValidationError as exc:
                        errors.append(f"{gpath.relative_to(iteration_dir)}: {exc.message}")

        with_runs = sorted((eval_dir / "with").glob("run-*")) if (eval_dir / "with").is_dir() else []
        baseline_dir = eval_dir / "without"
        if not baseline_dir.is_dir():
            baseline_dir = eval_dir / "old_skill"
        base_runs = sorted(baseline_dir.glob("run-*")) if baseline_dir.is_dir() else []
        if not with_runs or not base_runs:
            continue
        wg = json.loads((with_runs[0] / "grading.json").read_text(encoding="utf-8"))
        bg = json.loads((base_runs[0] / "grading.json").read_text(encoding="utf-8"))
        sw, sb = _assertion_ids(wg), _assertion_ids(bg)
        if sw != sb:
            errors.append(
                f"assertion_id mismatch for eval {eval_dir.name}: with={sorted(sw)} baseline={sorted(sb)}"
            )

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase D gate for an iteration directory")
    parser.add_argument("--iteration", type=int, required=True)
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path.cwd(),
        help="Directory containing iteration-<N>/",
    )
    args = parser.parse_args()
    skill_root = _skill_root(Path(__file__))
    iteration_dir = args.workspace / f"iteration-{args.iteration}"
    errors = validate_iteration(iteration_dir, skill_root)
    if errors:
        for line in errors:
            print(line, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
