from __future__ import annotations

from pathlib import Path


PBA_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = PBA_DIR / "prompts"


def _read_prompt(relative_path: str) -> str:
    return (PROMPTS_DIR / relative_path).read_text(encoding="utf-8")


def test_model_spec_obligations_precede_locked_base_rules():
    for relative_path in (
        "base-system-prompt.md",
        "_generated/hr.md",
        "_generated/operations.md",
    ):
        prompt = _read_prompt(relative_path)

        assert prompt.index("1. Model Spec obligations") < prompt.index(
            "2. <non_negotiable> rules"
        )


def test_domain_output_overrides_do_not_claim_to_replace_base_contract():
    for relative_path in (
        "base-system-prompt.md",
        "_generated/hr.md",
        "_generated/operations.md",
    ):
        prompt = _read_prompt(relative_path)

        assert "<domain_output_overrides>" in prompt
        assert "replace this block" not in prompt


def test_hr_prompt_scopes_names_to_minimum_necessary_personal_data():
    prompt = _read_prompt("_generated/hr.md")

    assert "minimum necessary name" in prompt
    assert "first name for external drafts" in prompt
    assert "Do not include internal IDs, contact details, government IDs" in prompt
    assert "Use only the minimum necessary personal data" in prompt
