"""Phase D gate: filesystem + schema + assertion_id parity across all runs.

Hard requirement: ``jsonschema`` must be importable. The core runtime stays
stdlib-only, but the gate script runs at dev/eval time where `pytest` +
`jsonschema` are installed per ``pyproject.toml`` (dev group). If absent,
the gate fails loudly rather than silently skipping validation — silent
pass would defeat the whole point of D-001.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    import jsonschema  # type: ignore
except ImportError as exc:  # pragma: no cover
    jsonschema = None
    _IMPORT_ERROR = str(exc)
else:
    _IMPORT_ERROR = ""


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

    if jsonschema is None:
        return [
            "jsonschema is required for check_iteration.py; "
            f"install dev deps (`uv sync --group dev`). ImportError: {_IMPORT_ERROR}"
        ]

    grading_schema = _load_schema(skill_root, "grading.schema.json")
    bench_schema = _load_schema(skill_root, "benchmark.schema.json")
    meta_schema = _load_schema(skill_root, "eval_metadata.schema.json")
    benchmark_path = iteration_dir / "benchmark.json"

    if benchmark_path.exists():
        try:
            jsonschema.validate(
                json.loads(benchmark_path.read_text(encoding="utf-8")), bench_schema
            )
        except jsonschema.ValidationError as exc:
            errors.append(f"benchmark.json schema: {exc.message}")
    else:
        errors.append(
            f"missing {benchmark_path.relative_to(iteration_dir)}"
            " (run aggregate_benchmark.py before Phase D)"
        )

    reserved = {"benchmark.json", "benchmark.md", "feedback.json", "iteration.json"}
    for eval_dir in sorted(p for p in iteration_dir.iterdir() if p.is_dir()):
        if eval_dir.name in reserved:
            continue
        # eval_metadata.json lives at eval level (one per eval, not per run)
        meta_path = eval_dir / "eval_metadata.json"
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                jsonschema.validate(meta, meta_schema)
            except (json.JSONDecodeError, jsonschema.ValidationError) as exc:
                errors.append(
                    f"{meta_path.relative_to(iteration_dir)}: {getattr(exc, 'message', exc)}"
                )

        per_side_ids: dict = {}
        for side in ("with_skill", "without_skill", "old_skill"):
            side_dir = eval_dir / side
            if not side_dir.is_dir():
                continue
            ids_by_run: list = []
            for run_dir in sorted(side_dir.glob("run-*")):
                for name in ("timing.json", "grading.json"):
                    fp = run_dir / name
                    if not fp.is_file():
                        errors.append(f"missing {fp.relative_to(iteration_dir)}")

                gpath = run_dir / "grading.json"
                if gpath.is_file():
                    try:
                        grading = json.loads(gpath.read_text(encoding="utf-8"))
                    except json.JSONDecodeError as exc:
                        errors.append(f"invalid JSON {gpath}: {exc}")
                        continue
                    try:
                        jsonschema.validate(grading, grading_schema)
                    except jsonschema.ValidationError as exc:
                        errors.append(
                            f"{gpath.relative_to(iteration_dir)}: {exc.message}"
                        )
                    ids_by_run.append(_assertion_ids(grading))
            per_side_ids[side] = ids_by_run

        # Parity: every run on every side must share the same assertion_id set.
        flat: list = []
        for side, runs in per_side_ids.items():
            for i, ids in enumerate(runs, start=1):
                flat.append((side, i, ids))
        if flat:
            reference = flat[0][2]
            for side, i, ids in flat[1:]:
                if ids != reference:
                    errors.append(
                        f"assertion_id mismatch in {eval_dir.name}: "
                        f"{flat[0][0]}#{flat[0][1]}={sorted(reference)} vs "
                        f"{side}#{i}={sorted(ids)}"
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
