"""check_iteration.validate_iteration — canonical layout + schema gates."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_spec_cf = importlib.util.spec_from_file_location(
    "create_agent_skill_tests_conftest", _ROOT / "conftest.py"
)
_cf = importlib.util.module_from_spec(_spec_cf)
assert _spec_cf.loader
_spec_cf.loader.exec_module(_cf)
write_canonical_run = _cf.write_canonical_run

REPO = Path(__file__).resolve().parents[3]
SKILL_ROOT = REPO / ".cursor" / "skills" / "create-agent-skill"

jsonschema = pytest.importorskip("jsonschema")


def _load_generate_benchmark():
    path = SKILL_ROOT / "eval-harness" / "scripts" / "aggregate_benchmark.py"
    spec = importlib.util.spec_from_file_location("aggregate_benchmark_ci", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod.generate_benchmark


generate_benchmark = _load_generate_benchmark()


def _load_validate_iteration():
    path = SKILL_ROOT / "scripts" / "check_iteration.py"
    spec = importlib.util.spec_from_file_location("check_iteration_unit", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod.validate_iteration


validate_iteration = _load_validate_iteration()


def _exp(aid: str, passed: bool = True) -> dict:
    return {
        "assertion_id": aid,
        "text": f"t-{aid}",
        "passed": passed,
    }


def test_validate_iteration_passes_valid(
    tmp_path: Path, skill_root: Path
) -> None:
    iteration_dir = tmp_path / "iteration-1"
    iteration_dir.mkdir(parents=True)
    ex = [_exp("a1"), _exp("a2")]
    write_canonical_run(
        iteration_dir, "eval-x", "with_skill", 1, ex, tokens=100
    )
    write_canonical_run(
        iteration_dir, "eval-x", "without_skill", 1, ex, tokens=100
    )
    bench = generate_benchmark(iteration_dir)
    (iteration_dir / "benchmark.json").write_text(
        json.dumps(bench, indent=2) + "\n", encoding="utf-8"
    )
    errs = validate_iteration(iteration_dir, skill_root)
    assert errs == []


def test_detects_assertion_id_drift(
    tmp_path: Path, skill_root: Path
) -> None:
    iteration_dir = tmp_path / "iteration-1"
    iteration_dir.mkdir(parents=True)
    write_canonical_run(
        iteration_dir,
        "eval-x",
        "with_skill",
        1,
        [_exp("a1"), _exp("a2")],
        tokens=1,
    )
    write_canonical_run(
        iteration_dir,
        "eval-x",
        "without_skill",
        1,
        [_exp("a1"), _exp("a3")],
        tokens=1,
    )
    bench = generate_benchmark(iteration_dir)
    (iteration_dir / "benchmark.json").write_text(
        json.dumps(bench, indent=2) + "\n", encoding="utf-8"
    )
    errs = validate_iteration(iteration_dir, skill_root)
    assert any("assertion_id mismatch" in e for e in errs)


def test_detects_missing_grading(tmp_path: Path, skill_root: Path) -> None:
    iteration_dir = tmp_path / "iteration-1"
    iteration_dir.mkdir(parents=True)
    ex = [_exp("a1")]
    write_canonical_run(
        iteration_dir, "eval-x", "with_skill", 1, ex, tokens=1
    )
    run_dir = iteration_dir / "eval-x" / "without_skill" / "run-1"
    run_dir.mkdir(parents=True)
    (run_dir / "outputs").mkdir(parents=True, exist_ok=True)
    (run_dir / "timing.json").write_text(
        '{"total_duration_seconds": 1.0, "total_tokens": 1}', encoding="utf-8"
    )
    bench = generate_benchmark(iteration_dir)
    (iteration_dir / "benchmark.json").write_text(
        json.dumps(bench, indent=2) + "\n", encoding="utf-8"
    )
    errs = validate_iteration(iteration_dir, skill_root)
    assert any("grading.json" in e for e in errs)


def test_detects_missing_benchmark(tmp_path: Path, skill_root: Path) -> None:
    iteration_dir = tmp_path / "iteration-1"
    iteration_dir.mkdir(parents=True)
    ex = [_exp("a1")]
    write_canonical_run(
        iteration_dir, "eval-x", "with_skill", 1, ex, tokens=1
    )
    write_canonical_run(
        iteration_dir, "eval-x", "without_skill", 1, ex, tokens=1
    )
    errs = validate_iteration(iteration_dir, skill_root)
    assert any("benchmark.json" in e for e in errs)


def test_detects_grading_schema_violation(
    tmp_path: Path, skill_root: Path
) -> None:
    iteration_dir = tmp_path / "iteration-1"
    iteration_dir.mkdir(parents=True)
    minimal_bench = {
        "metadata": {},
        "runs": [
            {
                "eval_id": "eval-x",
                "configuration": "with_skill",
                "run_number": 1,
                "result": {},
            }
        ],
        "run_summary": {"with_skill": {}, "without_skill": {}},
    }
    (iteration_dir / "benchmark.json").write_text(
        json.dumps(minimal_bench), encoding="utf-8"
    )
    eval_dir = iteration_dir / "eval-x"
    eval_dir.mkdir(parents=True)
    (eval_dir / "eval_metadata.json").write_text(
        json.dumps(
            {
                "eval_id": "eval-x",
                "prompt": "p",
                "expectations": [{"assertion_id": "a1", "text": "t"}],
            }
        ),
        encoding="utf-8",
    )
    run_dir = eval_dir / "with_skill" / "run-1"
    (run_dir / "outputs").mkdir(parents=True)
    (run_dir / "timing.json").write_text(
        '{"total_duration_seconds": 1.0}', encoding="utf-8"
    )
    (run_dir / "grading.json").write_text(
        json.dumps(
            {
                "expectations": [
                    {
                        "text": "no id",
                        "passed": True,
                        "evidence": "",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    errs = validate_iteration(iteration_dir, skill_root)
    assert any("grading.json" in e and "assertion_id" in e for e in errs)
