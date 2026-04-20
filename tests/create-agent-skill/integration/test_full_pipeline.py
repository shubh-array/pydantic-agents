"""Phase integration: aggregate + iteration gate + promotion gate."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from scripts.check_iteration import validate_iteration
from scripts.check_promotion import main as promo_main


def _skill_root() -> Path:
    return Path(__file__).resolve().parents[3] / ".cursor" / "skills" / "create-agent-skill"


def _load_aggregate():
    repo = Path(__file__).resolve().parents[3]
    p = repo / ".cursor/skills/create-agent-skill/eval-harness/scripts/aggregate_benchmark.py"
    spec = importlib.util.spec_from_file_location("aggregate_benchmark", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_aggregate_then_gates(tmp_path: Path, monkeypatch) -> None:
    skill_root = _skill_root()
    it = tmp_path / "iteration-7"
    specs = {
        "with": {"pass_rate": 1.0, "passed": 1, "failed": 0, "total": 1},
        "without": {"pass_rate": 0.5, "passed": 1, "failed": 1, "total": 2},
    }
    for side in ("with", "without"):
        d = it / "e2e" / side / "run-1"
        d.mkdir(parents=True)
        (d / "outputs").mkdir(exist_ok=True)
        s = specs[side]
        g = {
            "expectations": [
                {"assertion_id": "a1", "text": "t", "passed": True, "evidence": "e", "critical": False},
            ],
            "summary": {
                "pass_rate": s["pass_rate"],
                "passed": s["passed"],
                "failed": s["failed"],
                "total": s["total"],
            },
        }
        (d / "grading.json").write_text(json.dumps(g), encoding="utf-8")
        (d / "eval_metadata.json").write_text(json.dumps({"eval_id": "e2e"}), encoding="utf-8")
        (d / "timing.json").write_text(json.dumps({"total_duration_seconds": 0.1}), encoding="utf-8")
    mod = _load_aggregate()
    bench = mod.generate_benchmark(it, "demo", str(it))
    (it / "benchmark.json").write_text(json.dumps(bench) + "\n", encoding="utf-8")
    (it / "benchmark.md").write_text(mod.generate_markdown(bench), encoding="utf-8")
    assert validate_iteration(it, skill_root) == []
    (it / "feedback.json").write_text(
        json.dumps({"status": "complete", "reviews": []}), encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        ["check_promotion.py", "--iteration", "7", "--workspace", str(tmp_path)],
    )
    promo_main()
