"""aggregate_benchmark.generate_benchmark — canonical layout."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

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


def _load_generate_benchmark():
    path = SKILL_ROOT / "eval-harness" / "scripts" / "aggregate_benchmark.py"
    spec = importlib.util.spec_from_file_location("aggregate_benchmark_unit", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod.generate_benchmark


generate_benchmark = _load_generate_benchmark()


def _exp(aid: str, passed: bool, *, critical: bool = False) -> dict:
    return {
        "assertion_id": aid,
        "text": f"check {aid}",
        "passed": passed,
        "critical": critical,
    }


def test_generate_benchmark_reads_canonical_layout(tmp_path: Path) -> None:
    iteration_dir = tmp_path / "iteration-1"
    iteration_dir.mkdir(parents=True)
    ex = [_exp("a1", True), _exp("a2", True)]
    write_canonical_run(
        iteration_dir, "eval-a", "with_skill", 1, ex, tokens=10
    )
    write_canonical_run(
        iteration_dir, "eval-a", "without_skill", 1, ex, tokens=10
    )
    bench = generate_benchmark(iteration_dir)
    assert "metadata" in bench
    assert "runs" in bench
    assert "run_summary" in bench


def test_pass_rate_lift(tmp_path: Path) -> None:
    iteration_dir = tmp_path / "iteration-1"
    iteration_dir.mkdir(parents=True)
    ws = [_exp("a1", True), _exp("a2", True)]
    wos = [_exp("a1", True), _exp("a2", False)]
    write_canonical_run(iteration_dir, "e1", "with_skill", 1, ws, tokens=1)
    write_canonical_run(iteration_dir, "e1", "without_skill", 1, wos, tokens=1)
    bench = generate_benchmark(iteration_dir)
    delta_pr = bench["run_summary"]["delta"]["pass_rate"]
    assert float(delta_pr) > 0


def test_expectation_summary_present(tmp_path: Path) -> None:
    iteration_dir = tmp_path / "iteration-1"
    iteration_dir.mkdir(parents=True)
    ex = [_exp("x1", True, critical=True), _exp("x2", False)]
    write_canonical_run(iteration_dir, "e1", "with_skill", 1, ex, tokens=5)
    write_canonical_run(iteration_dir, "e1", "without_skill", 1, ex, tokens=5)
    bench = generate_benchmark(iteration_dir)
    for run in bench["runs"]:
        es = run.get("expectation_summary")
        assert es is not None
        assert "assertion_ids" in es
        assert "critical_total" in es
        assert "critical_failed" in es


def test_token_none_preserved(tmp_path: Path) -> None:
    iteration_dir = tmp_path / "iteration-1"
    iteration_dir.mkdir(parents=True)
    ex = [_exp("a1", True)]
    write_canonical_run(
        iteration_dir, "e1", "with_skill", 1, ex, tokens=None
    )
    write_canonical_run(
        iteration_dir, "e1", "without_skill", 1, ex, tokens=None
    )
    bench = generate_benchmark(iteration_dir)
    for run in bench["runs"]:
        assert run["result"].get("tokens") is None


def test_runs_per_configuration_inferred(tmp_path: Path) -> None:
    iteration_dir = tmp_path / "iteration-1"
    iteration_dir.mkdir(parents=True)
    ex = [_exp("a1", True)]
    for r in (1, 2):
        write_canonical_run(
            iteration_dir, "e1", "with_skill", r, ex, tokens=1
        )
        write_canonical_run(
            iteration_dir, "e1", "without_skill", r, ex, tokens=1
        )
    bench = generate_benchmark(iteration_dir)
    assert bench["metadata"]["runs_per_configuration"] >= 2
