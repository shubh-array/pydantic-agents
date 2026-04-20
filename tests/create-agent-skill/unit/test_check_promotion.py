"""Phase F gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.check_promotion import main as promo_main


def test_check_promotion_passes_rigged_benchmark(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    it = tmp_path / "iteration-9"
    it.mkdir()
    bench = {
        "runs": [
            {
                "eval_id": "e",
                "configuration": "with",
                "run_number": 1,
                "result": {},
                "expectations": [{"critical": False, "passed": True}],
            }
        ],
        "run_summary": {
            "with": {"pass_rate": {"mean": 0.9}},
            "without": {"pass_rate": {"mean": 0.5}},
            "delta": {},
        },
    }
    (it / "benchmark.json").write_text(json.dumps(bench), encoding="utf-8")
    (it / "feedback.json").write_text(
        json.dumps({"status": "complete", "reviews": []}), encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        ["check_promotion.py", "--iteration", "9", "--workspace", str(tmp_path)],
    )
    promo_main()  # should not raise


def test_check_promotion_fails_on_bad_feedback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    it = tmp_path / "iteration-8"
    it.mkdir()
    bench = {
        "runs": [],
        "run_summary": {
            "with": {"pass_rate": {"mean": 0.9}},
            "without": {"pass_rate": {"mean": 0.5}},
            "delta": {},
        },
    }
    (it / "benchmark.json").write_text(json.dumps(bench), encoding="utf-8")
    (it / "feedback.json").write_text(
        json.dumps({"status": "draft", "reviews": []}), encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        ["check_promotion.py", "--iteration", "8", "--workspace", str(tmp_path)],
    )
    with pytest.raises(SystemExit) as ei:
        promo_main()
    assert ei.value.code == 1
