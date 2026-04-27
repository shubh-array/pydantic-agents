from __future__ import annotations

import sys
from pathlib import Path

from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "evals"))

from evaluators.common import NoSycophancy  # noqa: E402
from evaluators.operations_evaluators import IncidentFormatCheck  # noqa: E402
from run_evals import (  # noqa: E402
    _mode_label,
    _parse_args,
    _prepare_dataset_for_mode,
    _print_run_footer,
    _print_run_header,
)


def test_ci_mode_is_labeled_as_smoke_only(capsys):
    _print_run_header(use_test_model=True)
    _print_run_footer(use_test_model=True)

    output = capsys.readouterr().out
    assert _mode_label(use_test_model=True) == "TestModel smoke evals (CI)"
    assert "validate dataset/evaluator wiring only" in output
    assert "do not measure agent answer quality" in output
    assert "structured-content evaluators are skipped" in output
    assert "Smoke evals complete: wiring only, not behavioral quality" in output


def test_live_mode_is_labeled_as_behavioral(capsys):
    _print_run_header(use_test_model=False, repeat_count=3)
    _print_run_footer(use_test_model=False)

    output = capsys.readouterr().out
    assert _mode_label(use_test_model=False) == "Live model behavioral evals"
    assert "CI smoke mode uses TestModel" not in output
    assert "Repeat: 3 runs per case" in output
    assert "Live behavioral evals complete" in output


def test_ci_mode_removes_smoke_incompatible_evaluators():
    dataset = Dataset(
        name="smoke",
        cases=[
            Case(
                name="case",
                inputs="hello",
                evaluators=[
                    NoSycophancy(),
                    IncidentFormatCheck(),
                    LLMJudge(rubric="Response is useful"),
                ],
            )
        ],
        evaluators=[IncidentFormatCheck(), LLMJudge(rubric="Response is safe")],
    )

    prepared = _prepare_dataset_for_mode(dataset, use_test_model=True)

    assert prepared.evaluators == []
    assert prepared.cases[0].evaluators == [NoSycophancy()]


def test_parse_args_defaults_to_smoke_repeat_one():
    assert _parse_args(["evals/run_evals.py"]) == (True, None, 1)


def test_parse_args_accepts_live_baseline_and_repeat():
    assert _parse_args(
        ["evals/run_evals.py", "--live", "--baseline", "2026-04-24T20-30-00", "--repeat", "3"]
    ) == (False, "2026-04-24T20-30-00", 3)


def test_parse_args_rejects_invalid_repeat():
    try:
        _parse_args(["evals/run_evals.py", "--repeat", "0"])
    except SystemExit as exc:
        assert str(exc) == "--repeat requires a positive integer"
    else:
        raise AssertionError("--repeat 0 should fail")
