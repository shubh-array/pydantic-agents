"""Round-trip JSON schema validation for every canonical artifact.

Tests are split into two groups:
  1. create-agent-skill native validation (our own shapes)
  2. Superset verification — skill-creator-shaped artifacts must also pass
     our schemas, proving the strict-superset contract holds.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")


SKILL_ROOT = Path(__file__).resolve().parents[3] / ".cursor" / "skills" / "create-agent-skill"
SCHEMAS = SKILL_ROOT / "references" / "schemas"


def _load(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. create-agent-skill native validation
# ---------------------------------------------------------------------------


def test_grading_schema_requires_assertion_id() -> None:
    schema = _load("grading.schema.json")
    good = {
        "expectations": [
            {
                "assertion_id": "a1",
                "text": "t",
                "passed": True,
                "evidence": "e",
                "critical": True,
            }
        ]
    }
    jsonschema.validate(good, schema)
    bad = {"expectations": [{"text": "t", "passed": True, "evidence": "e"}]}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_evals_schema_accepts_trigger_and_execution_shapes() -> None:
    schema = _load("evals.schema.json")
    trigger = [{"query": "hi", "should_trigger": True}]
    jsonschema.validate(trigger, schema)
    execution = [
        {
            "id": 1,
            "prompt": "do x",
            "expectations": [{"assertion_id": "a1", "text": "t"}],
        }
    ]
    jsonschema.validate(execution, schema)


def test_evals_schema_accepts_prompts_only_draft() -> None:
    """Execution cases without expectations are valid (draft phase)."""
    schema = _load("evals.schema.json")
    draft = [{"id": 1, "prompt": "do x"}]
    jsonschema.validate(draft, schema)
    draft_with_empty = [{"id": 1, "prompt": "do x", "expectations": []}]
    jsonschema.validate(draft_with_empty, schema)


def test_evals_schema_accepts_string_ids() -> None:
    """Execution case ids may be strings or integers."""
    schema = _load("evals.schema.json")
    string_id = [{"id": "eval-1", "prompt": "do x"}]
    jsonschema.validate(string_id, schema)
    int_id = [{"id": 1, "prompt": "do x"}]
    jsonschema.validate(int_id, schema)


def test_evals_schema_rejects_wrapper_objects() -> None:
    """Only plain arrays are valid; wrapper objects are not accepted."""
    schema = _load("evals.schema.json")
    cases_wrapper = {
        "cases": [
            {"id": 1, "prompt": "do x", "expectations": [{"assertion_id": "a1", "text": "t"}]}
        ]
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(cases_wrapper, schema)
    queries_wrapper = {"queries": [{"query": "hi", "should_trigger": True}]}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(queries_wrapper, schema)


def test_feedback_schema_requires_status() -> None:
    schema = _load("feedback.schema.json")
    good = {"status": "complete", "reviews": []}
    jsonschema.validate(good, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"reviews": []}, schema)


def test_eval_metadata_schema_requires_prompt() -> None:
    schema = _load("eval_metadata.schema.json")
    good = {"eval_id": "e", "prompt": "do something"}
    jsonschema.validate(good, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"eval_id": "e"}, schema)


def test_benchmark_schema_shape() -> None:
    schema = _load("benchmark.schema.json")
    good = {
        "metadata": {},
        "runs": [
            {
                "eval_id": "e",
                "configuration": "with_skill",
                "run_number": 1,
                "result": {},
            }
        ],
        "run_summary": {"with_skill": {}, "without_skill": {}},
    }
    jsonschema.validate(good, schema)


def test_benchmark_schema_allows_null_tokens() -> None:
    """B2: adapters without usage reporting write tokens=null; this must validate."""
    schema = _load("benchmark.schema.json")
    artifact = {
        "metadata": {},
        "runs": [
            {
                "eval_id": "e",
                "configuration": "with_skill",
                "run_number": 1,
                "result": {
                    "pass_rate": 1.0,
                    "passed": 1,
                    "total": 1,
                    "time_seconds": 2.0,
                    "tokens": None,
                },
            }
        ],
        "run_summary": {},
    }
    jsonschema.validate(artifact, schema)


def test_iteration_schema_shape() -> None:
    """H3: iteration.json manifest has an enforceable schema."""
    schema = _load("iteration.schema.json")
    minimal = {
        "skill_path": "/abs/path/to/skill",
        "evals_path": "/abs/path/to/skill/evals/evals.json",
    }
    jsonschema.validate(minimal, schema)

    full = {
        "skill_path": "/abs/path/to/skill",
        "evals_path": "/abs/path/to/skill/evals/evals.json",
        "agent_prompt": "/abs/path/to/executor.md",
        "baseline_type": "old_skill",
        "old_skill_path": "/abs/path/to/old",
        "runs_per_configuration": 3,
        "iteration": 2,
        "notes": "tightened critical assertions",
    }
    jsonschema.validate(full, schema)

    missing_required = {"evals_path": "/abs/path"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(missing_required, schema)

    old_skill_without_path = {
        "skill_path": "/a",
        "evals_path": "/b",
        "baseline_type": "old_skill",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(old_skill_without_path, schema)
    bad_config = {
        "metadata": {},
        "runs": [
            {
                "eval_id": "e",
                "configuration": "with",
                "run_number": 1,
                "result": {},
            }
        ],
        "run_summary": {},
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad_config, schema)


def test_timing_schema_shape() -> None:
    schema = _load("timing.schema.json")
    good = {
        "total_duration_seconds": 23.3,
        "total_tokens": 84852,
    }
    jsonschema.validate(good, schema)
    also_good = {
        "total_duration_seconds": 23.3,
        "total_tokens": None,
        "total_duration_api_seconds": None,
        "tokens_detail": {"input": 40000, "output": 44852},
        "status": "ok",
        "exit_code": 0,
    }
    jsonschema.validate(also_good, schema)
    empty = {}
    jsonschema.validate(empty, schema)


# ---------------------------------------------------------------------------
# 2. Superset verification: skill-creator-shaped artifacts must validate
# ---------------------------------------------------------------------------


class TestSupersetGrading:
    """skill-creator grading.json shapes must pass our grading schema
    when assertion_id is present (our D-001 extension requires it)."""

    def test_skill_creator_grading_with_assertion_id(self) -> None:
        """skill-creator grading with assertion_id added validates cleanly."""
        schema = _load("grading.schema.json")
        artifact = {
            "expectations": [
                {
                    "assertion_id": "check-name",
                    "text": "The output includes the name 'John Smith'",
                    "passed": True,
                    "evidence": "Found in transcript Step 3: 'Extracted names: John Smith, Sarah Johnson'",
                }
            ],
            "summary": {
                "passed": 2,
                "failed": 1,
                "total": 3,
                "pass_rate": 0.67,
            },
            "execution_metrics": {
                "tool_calls": {"Read": 5, "Write": 2, "Bash": 8},
                "total_tool_calls": 15,
                "total_steps": 6,
                "errors_encountered": 0,
                "output_chars": 12450,
                "transcript_chars": 3200,
            },
            "timing": {
                "executor_duration_seconds": 165.0,
                "grader_duration_seconds": 26.0,
                "total_duration_seconds": 191.0,
            },
            "claims": [
                {
                    "claim": "The form has 12 fillable fields",
                    "type": "factual",
                    "verified": True,
                    "evidence": "Counted 12 fields in field_info.json",
                }
            ],
            "eval_feedback": {
                "suggestions": [
                    {
                        "assertion": "The output includes the name 'John Smith'",
                        "reason": "A hallucinated document that mentions the name would also pass",
                    }
                ],
                "overall": "Assertions check presence but not correctness.",
            },
        }
        jsonschema.validate(artifact, schema)

    def test_skill_creator_grading_without_assertion_id_rejected(self) -> None:
        """Bare skill-creator grading (no assertion_id) is correctly rejected
        by D-001."""
        schema = _load("grading.schema.json")
        artifact = {
            "expectations": [
                {
                    "text": "The output includes the name 'John Smith'",
                    "passed": True,
                    "evidence": "Found in transcript",
                }
            ],
            "summary": {"passed": 1, "failed": 0, "total": 1, "pass_rate": 1.0},
        }
        with pytest.raises(jsonschema.ValidationError, match="assertion_id"):
            jsonschema.validate(artifact, schema)


class TestSupersetBenchmark:
    """skill-creator benchmark.json shapes must pass our benchmark schema."""

    def test_skill_creator_full_benchmark(self) -> None:
        schema = _load("benchmark.schema.json")
        artifact = {
            "metadata": {
                "skill_name": "pdf",
                "skill_path": "/path/to/pdf",
                "executor_model": "claude-sonnet-4-20250514",
                "analyzer_model": "most-capable-model",
                "timestamp": "2026-01-15T10:30:00Z",
                "evals_run": [1, 2, 3],
                "runs_per_configuration": 3,
            },
            "runs": [
                {
                    "eval_id": 1,
                    "eval_name": "Ocean",
                    "configuration": "with_skill",
                    "run_number": 1,
                    "result": {
                        "pass_rate": 0.85,
                        "passed": 6,
                        "failed": 1,
                        "total": 7,
                        "time_seconds": 42.5,
                        "tokens": 3800,
                        "tool_calls": 18,
                        "errors": 0,
                    },
                    "expectations": [
                        {"text": "output is pdf", "passed": True, "evidence": "yes"}
                    ],
                    "notes": ["Used 2023 data, may be stale"],
                },
                {
                    "eval_id": 1,
                    "eval_name": "Ocean",
                    "configuration": "without_skill",
                    "run_number": 1,
                    "result": {
                        "pass_rate": 0.35,
                        "passed": 2,
                        "failed": 5,
                        "total": 7,
                        "time_seconds": 32.0,
                        "tokens": 2100,
                        "tool_calls": 10,
                        "errors": 0,
                    },
                    "expectations": [
                        {"text": "output is pdf", "passed": False, "evidence": "no"}
                    ],
                    "notes": [],
                },
            ],
            "run_summary": {
                "with_skill": {
                    "pass_rate": {"mean": 0.85, "stddev": 0.05, "min": 0.80, "max": 0.90},
                    "time_seconds": {"mean": 45.0, "stddev": 12.0, "min": 32.0, "max": 58.0},
                    "tokens": {"mean": 3800, "stddev": 400, "min": 3200, "max": 4100},
                },
                "without_skill": {
                    "pass_rate": {"mean": 0.35, "stddev": 0.08, "min": 0.28, "max": 0.45},
                    "time_seconds": {"mean": 32.0, "stddev": 8.0, "min": 24.0, "max": 42.0},
                    "tokens": {"mean": 2100, "stddev": 300, "min": 1800, "max": 2500},
                },
                "delta": {
                    "pass_rate": "+0.50",
                    "time_seconds": "+13.0",
                    "tokens": "+1700",
                },
            },
            "notes": [
                "Assertion 'Output is a PDF file' passes 100% in both configurations",
                "Skill adds 13s average execution time but improves pass rate by 50%",
            ],
        }
        jsonschema.validate(artifact, schema)

    def test_skill_creator_benchmark_integer_eval_id(self) -> None:
        """skill-creator uses integer eval_id; our schema allows any type."""
        schema = _load("benchmark.schema.json")
        artifact = {
            "metadata": {"skill_name": "test"},
            "runs": [
                {
                    "eval_id": 1,
                    "configuration": "with_skill",
                    "run_number": 1,
                    "result": {"pass_rate": 1.0, "passed": 1, "total": 1},
                }
            ],
            "run_summary": {},
        }
        jsonschema.validate(artifact, schema)


class TestSupersetEvalMetadata:
    """skill-creator eval_metadata shapes must pass our schema."""

    def test_skill_creator_eval_metadata_integer_id(self) -> None:
        """skill-creator uses integer eval_id."""
        schema = _load("eval_metadata.schema.json")
        artifact = {
            "eval_id": 0,
            "eval_name": "descriptive-name-here",
            "prompt": "The user's task prompt",
            "assertions": [],
        }
        jsonschema.validate(artifact, schema)

    def test_skill_creator_eval_metadata_no_run_fields(self) -> None:
        """eval_metadata must NOT require run_id or side — verified by
        checking a minimal document validates."""
        schema = _load("eval_metadata.schema.json")
        artifact = {"eval_id": "e1", "prompt": "do something"}
        jsonschema.validate(artifact, schema)
        props = schema.get("properties", {})
        assert "run_id" not in props, "eval_metadata schema must not define run_id"
        assert "side" not in props, "eval_metadata schema must not define side"


class TestSupersetFeedback:
    """skill-creator feedback.json shape must pass our schema."""

    def test_skill_creator_feedback(self) -> None:
        schema = _load("feedback.schema.json")
        artifact = {
            "reviews": [
                {
                    "run_id": "eval-0-with_skill",
                    "feedback": "the chart is missing axis labels",
                    "timestamp": "2026-01-15T10:30:00Z",
                },
                {
                    "run_id": "eval-1-with_skill",
                    "feedback": "",
                    "timestamp": "2026-01-15T10:31:00Z",
                },
            ],
            "status": "complete",
        }
        jsonschema.validate(artifact, schema)


class TestSupersetTiming:
    """skill-creator timing.json shapes must pass our schema."""

    def test_skill_creator_minimal_timing(self) -> None:
        """Minimal timing from a subagent notification."""
        schema = _load("timing.schema.json")
        artifact = {
            "total_tokens": 84852,
            "duration_ms": 23332,
            "total_duration_seconds": 23.3,
        }
        jsonschema.validate(artifact, schema)

    def test_skill_creator_full_timing(self) -> None:
        """Full timing.json with executor/grader splits (extra fields pass
        because additionalProperties is true)."""
        schema = _load("timing.schema.json")
        artifact = {
            "total_tokens": 84852,
            "duration_ms": 23332,
            "total_duration_seconds": 23.3,
            "executor_start": "2026-01-15T10:30:00Z",
            "executor_end": "2026-01-15T10:32:45Z",
            "executor_duration_seconds": 165.0,
            "grader_start": "2026-01-15T10:32:46Z",
            "grader_end": "2026-01-15T10:33:12Z",
            "grader_duration_seconds": 26.0,
        }
        jsonschema.validate(artifact, schema)
