"""Custom evaluators for PBA agent evaluation pipeline.

Evaluators are organized by domain:
- common.py         — shared across all agents (NoSycophancy, NoPromptLeak)
- base_evaluators.py — base prompt behavioral rules (ConciseResponse, NoPIIEcho)
- operations_evaluators.py — IncidentStatus structural checks

Import ALL_CUSTOM_EVALUATORS when loading YAML datasets with Dataset.from_file().
"""

from evaluators.base_evaluators import (
    ConciseResponse,
    NoPIIEcho,
)
from evaluators.common import NoPromptLeak, NoSycophancy
from evaluators.operations_evaluators import IncidentFormatCheck

ALL_CUSTOM_EVALUATORS = [
    # Common
    NoSycophancy,
    NoPromptLeak,
    # Base agent
    ConciseResponse,
    NoPIIEcho,
    # Operations
    IncidentFormatCheck,
]

__all__ = [
    "ALL_CUSTOM_EVALUATORS",
    "ConciseResponse",
    "IncidentFormatCheck",
    "NoPIIEcho",
    "NoPromptLeak",
    "NoSycophancy",
]
