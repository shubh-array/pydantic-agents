"""aggregate_benchmark iteration layout."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def test_generate_benchmark_smoke(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[3]
    agg_path = repo / ".cursor" / "skills" / "create-agent-skill" / "eval-harness" / "scripts" / "aggregate_benchmark.py"
    spec = importlib.util.spec_from_file_location("aggregate_benchmark", agg_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)

    it = tmp_path / "iteration-3"
    w = it / "only" / "with" / "run-1"
    b = it / "only" / "without" / "run-1"
    for d in (w, b):
        d.mkdir(parents=True)
        g = {
            "expectations": [
                {"assertion_id": "a1", "text": "t", "passed": True, "evidence": "e"},
            ],
            "summary": {"pass_rate": 1.0, "passed": 1, "failed": 0, "total": 1},
        }
        (d / "grading.json").write_text(json.dumps(g), encoding="utf-8")
        (d / "eval_metadata.json").write_text(json.dumps({"eval_id": "only"}), encoding="utf-8")
        (d / "timing.json").write_text(
            json.dumps({"total_duration_seconds": 0.5, "total_tokens": None}), encoding="utf-8"
        )
    bench = mod.generate_benchmark(it, "x", str(it))
    assert bench["run_summary"]["with"]["pass_rate"]["mean"] == 1.0
