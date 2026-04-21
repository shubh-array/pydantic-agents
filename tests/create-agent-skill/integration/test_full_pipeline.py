"""Phase A→dual run→aggregate→check_iteration→check_promotion (FakeAdapter)."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

import adapters as adapters_mod

REPO = Path(__file__).resolve().parents[3]
SKILL_ROOT = REPO / ".cursor" / "skills" / "create-agent-skill"
EH_SCRIPTS = SKILL_ROOT / "eval-harness" / "scripts"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def _load_run_eval():
    return _load("run_eval_pipeline", EH_SCRIPTS / "run_eval.py")


def _load_aggregate():
    return _load("aggregate_benchmark_pipeline", EH_SCRIPTS / "aggregate_benchmark.py")


def _load_check_iteration():
    return _load("check_iteration_pipeline", SKILL_ROOT / "scripts" / "check_iteration.py")


def _load_check_promotion():
    return _load("check_promotion_pipeline", SKILL_ROOT / "scripts" / "check_promotion.py")


jsonschema = pytest.importorskip("jsonschema")


def _transcript() -> List[Dict[str, Any]]:
    return [
        {
            "type": "result",
            "duration_ms": 1500,
            "usage": {"inputTokens": 10, "outputTokens": 20},
        }
    ]


def _write_grading(run_dir: Path, p2_passed: bool) -> None:
    ex: List[Dict[str, Any]] = [
        {
            "assertion_id": "p1",
            "text": "t1",
            "passed": True,
            "evidence": "",
            "critical": True,
        },
        {
            "assertion_id": "p2",
            "text": "t2",
            "passed": p2_passed,
            "evidence": "",
            "critical": False,
        },
    ]
    passed = sum(1 for e in ex if e["passed"])
    total = len(ex)
    (run_dir / "grading.json").write_text(
        json.dumps(
            {
                "expectations": ex,
                "summary": {
                    "pass_rate": (passed / total) if total else 0.0,
                    "passed": passed,
                    "failed": total - passed,
                    "total": total,
                },
            }
        ),
        encoding="utf-8",
    )


def test_dual_passes_skill_content_for_with_skill_only(
    monkeypatch: pytest.MonkeyPatch, fake_adapter, tmp_path: Path
) -> None:
    """H1: with_skill invocations must receive skill_content; without_skill must not.

    The isolation contract is what makes the comparison meaningful — a
    baseline that accidentally had access to the skill would under-report
    its uplift.
    """
    fake_adapter.transcripts = [_transcript()]
    monkeypatch.setattr(adapters_mod, "get_active_adapter", lambda: fake_adapter)

    run_eval = _load_run_eval()
    monkeypatch.setattr(run_eval, "get_active_adapter", lambda: fake_adapter)

    skill_dir = tmp_path / "iso-skill"
    skill_dir.mkdir()
    skill_body = "---\nname: iso-skill\ndescription: ISO\n---\n\n# Body\nUnique marker: SKILL-FINGERPRINT-42\n"
    (skill_dir / "SKILL.md").write_text(skill_body, encoding="utf-8")
    evals_path = tmp_path / "evals.json"
    evals_path.write_text(
        json.dumps(
            [
                {
                    "id": "iso-1",
                    "prompt": "Do it",
                    "expectations": [{"assertion_id": "a1", "text": "t1", "critical": True}],
                }
            ]
        ),
        encoding="utf-8",
    )
    iteration_dir = tmp_path / "iteration-1"
    iteration_dir.mkdir()
    agent_prompt = SKILL_ROOT / "agents" / "executor.md"
    (iteration_dir / "iteration.json").write_text(
        json.dumps(
            {
                "skill_path": str(skill_dir.resolve()),
                "evals_path": str(evals_path.resolve()),
                "agent_prompt": str(agent_prompt.resolve()),
                "runs_per_configuration": 1,
            }
        ),
        encoding="utf-8",
    )

    args = argparse.Namespace(
        iteration=1,
        workspace=tmp_path,
        skill_path=skill_dir,
        evals=evals_path,
        agent_prompt=agent_prompt,
        timeout=30,
    )
    run_eval.cmd_dual(args)

    by_side = {}
    for inv in fake_adapter.invocations:
        side = Path(inv["workdir"]).parent.parent.name
        by_side[side] = inv["skill_content"]

    assert "SKILL-FINGERPRINT-42" in (by_side["with_skill"] or "")
    assert by_side["without_skill"] is None


def test_dual_invokes_subagent_under_outputs(
    monkeypatch: pytest.MonkeyPatch, fake_adapter, tmp_path: Path
) -> None:
    fake_adapter.transcripts = [_transcript()]
    monkeypatch.setattr(adapters_mod, "get_active_adapter", lambda: fake_adapter)

    run_eval = _load_run_eval()
    monkeypatch.setattr(run_eval, "get_active_adapter", lambda: fake_adapter)

    skill_dir = tmp_path / "pipe-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: pipe-skill\ndescription: test\n---\n\n# P\n",
        encoding="utf-8",
    )
    evals_path = tmp_path / "evals.json"
    evals_path.write_text(
        json.dumps(
            [
                {
                    "id": "pipe-1",
                    "prompt": "Do something",
                    "expectations": [
                        {"assertion_id": "p1", "text": "t1", "critical": True},
                        {"assertion_id": "p2", "text": "t2"},
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    iteration_dir = tmp_path / "iteration-1"
    iteration_dir.mkdir()
    agent_prompt = SKILL_ROOT / "agents" / "analyzer.md"
    (iteration_dir / "iteration.json").write_text(
        json.dumps(
            {
                "skill_path": str(skill_dir.resolve()),
                "evals_path": str(evals_path.resolve()),
                "agent_prompt": str(agent_prompt.resolve()),
                "runs_per_configuration": 1,
            }
        ),
        encoding="utf-8",
    )

    args = argparse.Namespace(
        iteration=1,
        workspace=tmp_path,
        skill_path=skill_dir,
        evals=evals_path,
        agent_prompt=agent_prompt,
        timeout=30,
    )
    run_eval.cmd_dual(args)

    for inv in fake_adapter.invocations:
        assert Path(inv["workdir"]).name == "outputs"

    meta = json.loads(
        (iteration_dir / "pipe-1" / "eval_metadata.json").read_text(encoding="utf-8")
    )
    assert meta.get("eval_id") == "pipe-1"
    assert "expectations" in meta


def test_aggregate_and_iteration_pass_after_dual(
    monkeypatch: pytest.MonkeyPatch, fake_adapter, tmp_path: Path, skill_root: Path
) -> None:
    fake_adapter.transcripts = [_transcript()]
    monkeypatch.setattr(adapters_mod, "get_active_adapter", lambda: fake_adapter)

    run_eval = _load_run_eval()
    monkeypatch.setattr(run_eval, "get_active_adapter", lambda: fake_adapter)
    aggregate = _load_aggregate()
    check_it = _load_check_iteration()

    skill_dir = tmp_path / "pipe-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: pipe-skill\ndescription: test\n---\n\n# P\n",
        encoding="utf-8",
    )
    evals_path = tmp_path / "evals.json"
    evals_path.write_text(
        json.dumps(
            [
                {
                    "id": "pipe-1",
                    "prompt": "Do something",
                    "expectations": [
                        {"assertion_id": "p1", "text": "t1", "critical": True},
                        {"assertion_id": "p2", "text": "t2"},
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    iteration_dir = tmp_path / "iteration-1"
    iteration_dir.mkdir()
    agent_prompt = SKILL_ROOT / "agents" / "analyzer.md"
    (iteration_dir / "iteration.json").write_text(
        json.dumps(
            {
                "skill_path": str(skill_dir.resolve()),
                "evals_path": str(evals_path.resolve()),
                "agent_prompt": str(agent_prompt.resolve()),
                "runs_per_configuration": 1,
            }
        ),
        encoding="utf-8",
    )

    args = argparse.Namespace(
        iteration=1,
        workspace=tmp_path,
        skill_path=skill_dir,
        evals=evals_path,
        agent_prompt=agent_prompt,
        timeout=30,
    )
    run_eval.cmd_dual(args)

    _write_grading(iteration_dir / "pipe-1" / "with_skill" / "run-1", True)
    _write_grading(iteration_dir / "pipe-1" / "without_skill" / "run-1", False)

    bench = aggregate.generate_benchmark(iteration_dir)
    (iteration_dir / "benchmark.json").write_text(
        json.dumps(bench, indent=2) + "\n", encoding="utf-8"
    )

    errs = check_it.validate_iteration(iteration_dir, skill_root)
    assert errs == []


def test_check_promotion_passes_when_complete(
    monkeypatch: pytest.MonkeyPatch, fake_adapter, tmp_path: Path
) -> None:
    fake_adapter.transcripts = [_transcript()]
    monkeypatch.setattr(adapters_mod, "get_active_adapter", lambda: fake_adapter)

    run_eval = _load_run_eval()
    monkeypatch.setattr(run_eval, "get_active_adapter", lambda: fake_adapter)
    aggregate = _load_aggregate()
    promotion = _load_check_promotion()

    skill_dir = tmp_path / "pipe-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: pipe-skill\ndescription: test\n---\n\n# P\n",
        encoding="utf-8",
    )
    evals_path = tmp_path / "evals.json"
    evals_path.write_text(
        json.dumps(
            [
                {
                    "id": "pipe-1",
                    "prompt": "Do something",
                    "expectations": [
                        {"assertion_id": "p1", "text": "t1", "critical": True},
                        {"assertion_id": "p2", "text": "t2"},
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    iteration_dir = tmp_path / "iteration-1"
    iteration_dir.mkdir()
    agent_prompt = SKILL_ROOT / "agents" / "analyzer.md"
    (iteration_dir / "iteration.json").write_text(
        json.dumps(
            {
                "skill_path": str(skill_dir.resolve()),
                "evals_path": str(evals_path.resolve()),
                "agent_prompt": str(agent_prompt.resolve()),
                "runs_per_configuration": 1,
            }
        ),
        encoding="utf-8",
    )

    args = argparse.Namespace(
        iteration=1,
        workspace=tmp_path,
        skill_path=skill_dir,
        evals=evals_path,
        agent_prompt=agent_prompt,
        timeout=30,
    )
    run_eval.cmd_dual(args)

    _write_grading(iteration_dir / "pipe-1" / "with_skill" / "run-1", True)
    _write_grading(iteration_dir / "pipe-1" / "without_skill" / "run-1", False)

    bench = aggregate.generate_benchmark(iteration_dir)
    (iteration_dir / "benchmark.json").write_text(
        json.dumps(bench, indent=2) + "\n", encoding="utf-8"
    )
    (iteration_dir / "feedback.json").write_text(
        json.dumps({"status": "complete", "reviews": []}), encoding="utf-8"
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["check_promotion", "--iteration", "1", "--workspace", str(tmp_path)],
    )
    promotion.main()


def test_critical_failure_in_candidate_blocks_promotion(
    monkeypatch: pytest.MonkeyPatch, fake_adapter, tmp_path: Path
) -> None:
    fake_adapter.transcripts = [_transcript()]
    monkeypatch.setattr(adapters_mod, "get_active_adapter", lambda: fake_adapter)

    run_eval = _load_run_eval()
    monkeypatch.setattr(run_eval, "get_active_adapter", lambda: fake_adapter)
    aggregate = _load_aggregate()
    promotion = _load_check_promotion()

    skill_dir = tmp_path / "pipe-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: pipe-skill\ndescription: test\n---\n\n# P\n",
        encoding="utf-8",
    )
    evals_path = tmp_path / "evals.json"
    evals_path.write_text(
        json.dumps(
            [
                {
                    "id": "pipe-1",
                    "prompt": "Do something",
                    "expectations": [
                        {"assertion_id": "p1", "text": "t1", "critical": True},
                        {"assertion_id": "p2", "text": "t2"},
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    iteration_dir = tmp_path / "iteration-1"
    iteration_dir.mkdir()
    agent_prompt = SKILL_ROOT / "agents" / "analyzer.md"
    (iteration_dir / "iteration.json").write_text(
        json.dumps(
            {
                "skill_path": str(skill_dir.resolve()),
                "evals_path": str(evals_path.resolve()),
                "agent_prompt": str(agent_prompt.resolve()),
                "runs_per_configuration": 1,
            }
        ),
        encoding="utf-8",
    )

    args = argparse.Namespace(
        iteration=1,
        workspace=tmp_path,
        skill_path=skill_dir,
        evals=evals_path,
        agent_prompt=agent_prompt,
        timeout=30,
    )
    run_eval.cmd_dual(args)

    ex_crit_fail: List[Dict[str, Any]] = [
        {
            "assertion_id": "p1",
            "text": "t1",
            "passed": False,
            "evidence": "",
            "critical": True,
        },
        {
            "assertion_id": "p2",
            "text": "t2",
            "passed": True,
            "evidence": "",
            "critical": False,
        },
    ]
    passed = sum(1 for e in ex_crit_fail if e["passed"])
    total = len(ex_crit_fail)
    (iteration_dir / "pipe-1" / "with_skill" / "run-1" / "grading.json").write_text(
        json.dumps(
            {
                "expectations": ex_crit_fail,
                "summary": {
                    "pass_rate": (passed / total) if total else 0.0,
                    "passed": passed,
                    "failed": total - passed,
                    "total": total,
                },
            }
        ),
        encoding="utf-8",
    )
    _write_grading(iteration_dir / "pipe-1" / "without_skill" / "run-1", True)

    bench = aggregate.generate_benchmark(iteration_dir)
    (iteration_dir / "benchmark.json").write_text(
        json.dumps(bench, indent=2) + "\n", encoding="utf-8"
    )
    (iteration_dir / "feedback.json").write_text(
        json.dumps({"status": "complete", "reviews": []}), encoding="utf-8"
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["check_promotion", "--iteration", "1", "--workspace", str(tmp_path)],
    )
    with pytest.raises(SystemExit) as exc:
        promotion.main()
    assert exc.value.code == 1
