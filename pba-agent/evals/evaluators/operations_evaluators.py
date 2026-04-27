"""Evaluators for the operations domain agent.

Check that IncidentStatus outputs follow the operations-agent-prompt.md
contract: valid SEV level, recognized status enum, populated impact /
hypothesis / next-steps fields.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext


@dataclass
class IncidentFormatCheck(Evaluator):
    """Validate that an IncidentStatus output follows the expected SEV format.

    Checks severity level, status enum, and non-empty narrative fields.
    Skips gracefully when the output is Failed (the agent correctly refused).
    """

    valid_sevs: tuple[str, ...] = ("SEV-1", "SEV-2", "SEV-3", "SEV-4")
    valid_statuses: tuple[str, ...] = ("investigating", "mitigating", "resolved", "monitoring")

    def evaluate(self, ctx: EvaluatorContext) -> dict[str, bool | EvaluationReason]:
        output = ctx.output
        results: dict[str, bool | EvaluationReason] = {}

        type_name = type(output).__name__
        if type_name == "Failed":
            results["incident_format"] = EvaluationReason(
                value=True, reason="Output is Failed — format check skipped"
            )
            return results

        if type_name != "IncidentStatus":
            results["incident_format"] = EvaluationReason(
                value=False, reason=f"Expected IncidentStatus or Failed, got {type_name}"
            )
            return results

        results["has_valid_sev"] = output.sev.upper() in self.valid_sevs
        results["has_valid_status"] = output.status.lower() in self.valid_statuses
        results["has_impact"] = bool(output.impact and output.impact.strip())
        results["has_hypothesis"] = bool(output.hypothesis and output.hypothesis.strip())
        results["has_next_steps"] = len(output.next_steps) > 0
        return results
