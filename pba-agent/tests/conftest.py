from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key-not-used")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pydantic_ai import models  # noqa: E402

models.ALLOW_MODEL_REQUESTS = False
