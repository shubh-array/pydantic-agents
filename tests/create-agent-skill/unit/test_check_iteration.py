"""Phase D gate."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.check_iteration import validate_iteration


def _write_grading(path: Path, aids: list) -> None:
    exps = [
        {"assertion_id": a, "text": "t", "passed": True, "evidence": "e"} for a in aids
    ]
    g = {"expectations": exps, "summary": {"pass_rate": 1.0, "passed": len(aids), "failed": 0, "total": len(aids)}}
    path.write_text(json.dumps(g), encoding="utf-8")


def _skill_root() -> Path:
    return Path(__file__).resolve().parents[3] / ".cursor" / "skills" / "create-agent-skill"


def test_validate_iteration_passes_matching_ids(tmp_path: Path) -> None:
    skill_root = _skill_root()
    it = tmp_path / "iteration-1"
    base = it / "smoke" / "with" / "run-1"
    bl = it / "smoke" / "without" / "run-1"
    for d in (base, bl):
        d.mkdir(parents=True)
        (d / "eval_metadata.json").write_text(json.dumps({"eval_id": "smoke"}), encoding="utf-8")
        (d / "timing.json").write_text(json.dumps({"total_duration_seconds": 1.0}), encoding="utf-8")
        _write_grading(d / "grading.json", ["a1", "a2"])
    errs = validate_iteration(it, skill_root)
    assert errs == []


def test_validate_iteration_detects_mismatch(tmp_path: Path) -> None:
    skill_root = _skill_root()
    it = tmp_path / "iteration-2"
    w = it / "e" / "with" / "run-1"
    b = it / "e" / "without" / "run-1"
    for d in (w, b):
        d.mkdir(parents=True)
        (d / "eval_metadata.json").write_text(json.dumps({"eval_id": "e"}), encoding="utf-8")
        (d / "timing.json").write_text("{}", encoding="utf-8")
    _write_grading(w / "grading.json", ["x"])
    _write_grading(b / "grading.json", ["x", "y"])
    errs = validate_iteration(it, skill_root)
    assert any("assertion_id mismatch" in e for e in errs)
