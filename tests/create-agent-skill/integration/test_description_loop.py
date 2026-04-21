"""Description loop integration with FakeAdapter — rich context + termination."""

from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SKILL = REPO / ".cursor" / "skills" / "create-agent-skill"
EH = SKILL / "eval-harness/scripts"
for _p in (SKILL, EH):
    s = str(_p)
    if s not in sys.path:
        sys.path.insert(0, s)


def _load(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_improve_description_passes_rich_context(monkeypatch, fake_adapter) -> None:
    """improve_description must pass skill_content, history, summaries to the adapter."""
    import adapters as adapters_mod

    monkeypatch.setattr(adapters_mod, "get_active_adapter", lambda: fake_adapter)
    mod = _load("improve_description_test", EH / "improve_description.py")
    # improve_description.py imports ``get_active_adapter`` with
    # ``from adapters import get_active_adapter``; patch that bound symbol.
    monkeypatch.setattr(mod, "get_active_adapter", lambda: fake_adapter)

    eval_results = {
        "description": "old description",
        "results": [
            {"query": "edit my spreadsheet", "should_trigger": True, "pass": False, "triggers": 0, "runs": 3},
            {"query": "tell me a joke", "should_trigger": False, "pass": False, "triggers": 2, "runs": 3},
        ],
        "summary": {"passed": 0, "failed": 2, "total": 2},
    }
    new = mod.improve_description(
        skill_name="seed-skill-v1",
        skill_content="# seed-skill-v1\n\nPlaceholder body.",
        current_description="old description",
        eval_results=eval_results,
        history=[{"description": "previous", "passed": 0, "failed": 2, "total": 2}],
        iteration=1,
    )
    assert isinstance(new, str) and new
    improv = [
        inv for inv in fake_adapter.invocations
        if inv.get("method") == "generate_improved_description"
    ]
    assert improv, "FakeAdapter.generate_improved_description was not invoked"
    ctx = improv[-1]["context"]
    assert ctx is not None
    assert ctx.get("skill_name") == "seed-skill-v1"
    assert "Placeholder" in (ctx.get("skill_content") or "")
    assert ctx.get("train_summary", {}).get("total") == 2
    assert [r["query"] for r in ctx["failing_queries"]] == ["edit my spreadsheet"]
    assert [r["query"] for r in ctx["false_trigger_queries"]] == ["tell me a joke"]


def test_run_loop_terminates_when_all_pass(monkeypatch, fake_adapter, tmp_path: Path) -> None:
    """Deterministic loop termination: trigger map flips all-pass immediately."""
    import adapters as adapters_mod

    # All queries should trigger; their ``should_trigger`` fields reflect that.
    fake_adapter.trigger_map = {"q1": True, "q2": False}
    monkeypatch.setattr(adapters_mod, "get_active_adapter", lambda: fake_adapter)

    # run_loop imports run_eval + improve_description as top-level symbols; bind patch.
    run_eval_mod = _load("run_eval_rl", EH / "run_eval.py")
    monkeypatch.setattr(run_eval_mod, "get_active_adapter", lambda: fake_adapter)
    monkeypatch.setitem(sys.modules, "run_eval", run_eval_mod)
    improve_mod = _load("improve_description_rl", EH / "improve_description.py")
    monkeypatch.setattr(improve_mod, "get_active_adapter", lambda: fake_adapter)
    monkeypatch.setitem(sys.modules, "improve_description", improve_mod)

    run_loop_mod = _load("run_loop_test", EH / "run_loop.py")

    skill_dir = tmp_path / "loop-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: loop-skill\ndescription: stub\n---\n\n# loop-skill\n",
        encoding="utf-8",
    )
    eval_set = [
        {"query": "q1", "should_trigger": True},
        {"query": "q2", "should_trigger": False},
    ]
    out = run_loop_mod.run_loop(
        eval_set=eval_set,
        skill_path=skill_dir,
        description_override="desc",
        num_workers=2,
        timeout=30,
        max_iterations=3,
        runs_per_query=1,
        trigger_threshold=0.5,
        holdout=0,
        model="",
        verbose=False,
        live_report_path=None,
        log_dir=None,
    )
    assert out["exit_reason"].startswith("all_passed")
    assert out["iterations_run"] == 1
