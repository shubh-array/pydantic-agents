"""check_promotion.main — Phase F thresholds."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

REPO = Path(__file__).resolve().parents[3]
SKILL_ROOT = REPO / ".cursor" / "skills" / "create-agent-skill"


def _load_main():
    path = SKILL_ROOT / "scripts" / "check_promotion.py"
    spec = importlib.util.spec_from_file_location("check_promotion_unit", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod.main


main = _load_main()


def _iteration(workspace: Path) -> Path:
    d = workspace / "iteration-1"
    d.mkdir(parents=True)
    return d


def _bench_ok() -> dict:
    return {
        "metadata": {},
        "run_summary": {
            "with_skill": {"pass_rate": {"mean": 0.95}},
            "without_skill": {"pass_rate": {"mean": 0.80}},
        },
        "runs": [
            {
                "configuration": "with_skill",
                "expectation_summary": {"critical_failed": 0},
            }
        ],
    }


def test_passes_when_thresholds_met(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    it = _iteration(tmp_path)
    (it / "benchmark.json").write_text(json.dumps(_bench_ok()), encoding="utf-8")
    (it / "feedback.json").write_text(
        json.dumps({"status": "complete", "reviews": []}), encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["check_promotion", "--iteration", "1", "--workspace", str(tmp_path)],
    )
    main()


def test_fails_insufficient_lift(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    it = _iteration(tmp_path)
    (it / "benchmark.json").write_text(
        json.dumps(
            {
                "metadata": {},
                "run_summary": {
                    "with_skill": {"pass_rate": {"mean": 0.90}},
                    "without_skill": {"pass_rate": {"mean": 0.90}},
                },
                "runs": [
                    {
                        "configuration": "with_skill",
                        "expectation_summary": {"critical_failed": 0},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (it / "feedback.json").write_text(
        json.dumps({"status": "complete"}), encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["check_promotion", "--iteration", "1", "--workspace", str(tmp_path)],
    )
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1


def test_fails_critical_failures(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    it = _iteration(tmp_path)
    (it / "benchmark.json").write_text(
        json.dumps(
            {
                "metadata": {},
                "run_summary": {
                    "with_skill": {"pass_rate": {"mean": 0.95}},
                    "without_skill": {"pass_rate": {"mean": 0.80}},
                },
                "runs": [
                    {
                        "configuration": "with_skill",
                        "expectation_summary": {"critical_failed": 2},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (it / "feedback.json").write_text(
        json.dumps({"status": "complete"}), encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["check_promotion", "--iteration", "1", "--workspace", str(tmp_path)],
    )
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1


def test_fails_draft_feedback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    it = _iteration(tmp_path)
    (it / "benchmark.json").write_text(json.dumps(_bench_ok()), encoding="utf-8")
    (it / "feedback.json").write_text(json.dumps({"status": "draft"}), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["check_promotion", "--iteration", "1", "--workspace", str(tmp_path)],
    )
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1


def test_fails_missing_feedback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    it = _iteration(tmp_path)
    (it / "benchmark.json").write_text(json.dumps(_bench_ok()), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["check_promotion", "--iteration", "1", "--workspace", str(tmp_path)],
    )
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1


def test_fails_low_candidate_pass_rate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    it = _iteration(tmp_path)
    (it / "benchmark.json").write_text(
        json.dumps(
            {
                "metadata": {},
                "run_summary": {
                    "with_skill": {"pass_rate": {"mean": 0.80}},
                    "without_skill": {"pass_rate": {"mean": 0.70}},
                },
                "runs": [
                    {
                        "configuration": "with_skill",
                        "expectation_summary": {"critical_failed": 0},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (it / "feedback.json").write_text(
        json.dumps({"status": "complete"}), encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["check_promotion", "--iteration", "1", "--workspace", str(tmp_path)],
    )
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
