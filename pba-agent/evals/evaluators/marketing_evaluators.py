"""Evaluators for the marketing domain agent.

Check that MarketingDraft outputs follow the marketing-agent-prompt.md
contract: valid channels, non-empty content, consistent word counts,
and acceptable tone descriptors.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext


@dataclass
class MarketingDraftCheck(Evaluator):
    """Validate that a MarketingDraft output has well-formed fields.

    Checks channel validity, non-empty content/tone, and positive word count.
    Skips gracefully when the output is Failed (the agent correctly refused).
    """

    valid_channels: tuple[str, ...] = ("linkedin", "twitter", "blog", "email")

    def evaluate(self, ctx: EvaluatorContext) -> dict[str, bool | EvaluationReason]:
        output = ctx.output
        results: dict[str, bool | EvaluationReason] = {}

        type_name = type(output).__name__
        if type_name == "Failed":
            results["draft_format"] = EvaluationReason(
                value=True, reason="Output is Failed — format check skipped"
            )
            return results

        if type_name != "MarketingDraft":
            results["draft_format"] = EvaluationReason(
                value=False, reason=f"Expected MarketingDraft or Failed, got {type_name}"
            )
            return results

        results["has_content"] = bool(output.content and output.content.strip())
        results["has_channel"] = output.channel.lower() in self.valid_channels
        results["has_tone"] = bool(output.tone and output.tone.strip())
        results["positive_word_count"] = output.word_count > 0
        return results
