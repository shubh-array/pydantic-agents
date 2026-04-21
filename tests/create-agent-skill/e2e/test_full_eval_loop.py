"""Canonical layout → aggregate_benchmark + check_iteration (subprocess)."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

E2E_DIR = Path(__file__).resolve().parent
CAS_DIR = E2E_DIR.parent
_PARENT_CONF = CAS_DIR / "conftest.py"
_spec = importlib.util.spec_from_file_location(
    "create_agent_skill_parent_conftest", _PARENT_CONF
)
_parent_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader
_spec.loader.exec_module(_parent_mod)
write_canonical_run = _parent_mod.write_canonical_run

REPO = Path(__file__).resolve().parents[3]
SKILL_ROOT = REPO / ".cursor" / "skills" / "create-agent-skill"
AGG = SKILL_ROOT / "eval-harness" / "scripts" / "aggregate_benchmark.py"
CHK = SKILL_ROOT / "scripts" / "check_iteration.py"
BENCH_SCHEMA = SKILL_ROOT / "references" / "schemas" / "benchmark.schema.json"


def _exp(aid: str, passed: bool) -> dict:
    return {
        "assertion_id": aid,
        "text": f"t-{aid}",
        "passed": passed,
    }


def test_full_eval_loop_aggregate_and_gate(tmp_path: Path) -> None:
    iteration_dir = tmp_path / "iteration-1"
    iteration_dir.mkdir(parents=True)
    ex_ws = [_exp("a1", True), _exp("a2", True)]
    ex_wos = [_exp("a1", True), _exp("a2", False)]
    write_canonical_run(iteration_dir, "eval-1", "with_skill", 1, ex_ws, tokens=50)
    write_canonical_run(iteration_dir, "eval-1", "without_skill", 1, ex_wos, tokens=50)

    env = {**os.environ, "PYTHONPATH": str(SKILL_ROOT)}
    r1 = subprocess.run(
        [sys.executable, str(AGG), "--iteration", "1", "--workspace", str(tmp_path)],
        cwd=str(SKILL_ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert r1.returncode == 0, r1.stdout + r1.stderr

    bench_path = iteration_dir / "benchmark.json"
    assert bench_path.is_file()
    bench = json.loads(bench_path.read_text(encoding="utf-8"))
    schema = json.loads(BENCH_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(bench, schema)

    r2 = subprocess.run(
        [sys.executable, str(CHK), "--iteration", "1", "--workspace", str(tmp_path)],
        cwd=str(SKILL_ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert r2.returncode == 0, r2.stdout + r2.stderr
