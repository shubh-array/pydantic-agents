"""Brand-voice guardrail capability.

Scans model responses for forbidden phrasings and triggers a retry when
one is found.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import ModelRequestContext, RunContext
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.messages import ModelResponse, TextPart

FORBIDDEN_PHRASES: list[str] = [
    "revolutionary",
    "game-changing",
    "paradigm-shifting",
    "in today's fast-paced world",
    "we're thrilled to announce",
    "great question",
]

_FORBIDDEN_RE = re.compile(
    "|".join(re.escape(p) for p in FORBIDDEN_PHRASES),
    re.IGNORECASE,
)


@dataclass
class BrandVoiceGuardrail(AbstractCapability[Any]):
    """Rejects model responses that contain forbidden phrasings.

    When a forbidden phrase is detected, the capability raises ``ModelRetry``
    so the model can self-correct.  Violations are recorded in ``violations``
    for post-run inspection.
    """

    extra_forbidden: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    _pattern: re.Pattern[str] | None = field(default=None, repr=False)

    def _get_pattern(self) -> re.Pattern[str]:
        if self._pattern is not None:
            return self._pattern
        all_phrases = FORBIDDEN_PHRASES + self.extra_forbidden
        self._pattern = re.compile(
            "|".join(re.escape(p) for p in all_phrases),
            re.IGNORECASE,
        )
        return self._pattern

    async def after_model_request(
        self,
        ctx: RunContext[Any],
        *,
        request_context: ModelRequestContext,
        response: ModelResponse,
    ) -> ModelResponse:
        pattern = self._get_pattern()
        for part in response.parts:
            if not isinstance(part, TextPart):
                continue
            match = pattern.search(part.content)
            if match:
                phrase = match.group()
                self.violations.append(phrase)
                print(f"  [brand-voice] VIOLATION: '{phrase}' — requesting retry")
                raise ModelRetry(
                    f"Your response contains the forbidden phrasing '{phrase}'. "
                    "Rewrite without it. Refer to brand voice rules: no hype language, "
                    "no sycophantic openers, no exclamation points in body copy."
                )
        return response
