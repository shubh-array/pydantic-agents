"""Shared utilities for create-agent-skill scripts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def skill_root_from_here(here: Path, *, parents_up: int) -> Path:
    """Return skill root given a file path inside the skill and how many parents to ascend."""
    return here.resolve().parents[parents_up]


def parse_skill_md(skill_path: Path) -> tuple[str, str, str]:
    """Parse a SKILL.md file, returning (name, description, full_content)."""
    content = (skill_path / "SKILL.md").read_text(encoding="utf-8")
    lines = content.split("\n")

    if lines[0].strip() != "---":
        raise ValueError("SKILL.md missing frontmatter (no opening ---)")

    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        raise ValueError("SKILL.md missing frontmatter (no closing ---)")

    name = ""
    description = ""
    frontmatter_lines = lines[1:end_idx]
    i = 0
    while i < len(frontmatter_lines):
        line = frontmatter_lines[i]
        if line.startswith("name:"):
            name = line[len("name:") :].strip().strip('"').strip("'")
        elif line.startswith("description:"):
            value = line[len("description:") :].strip()
            if value in (">", "|", ">-", "|-"):
                continuation_lines: list[str] = []
                i += 1
                while i < len(frontmatter_lines) and (
                    frontmatter_lines[i].startswith("  ")
                    or frontmatter_lines[i].startswith("\t")
                ):
                    continuation_lines.append(frontmatter_lines[i].strip())
                    i += 1
                description = " ".join(continuation_lines)
                continue
            else:
                description = value.strip('"').strip("'")
        i += 1

    return name, description, content


def _parse_frontmatter_fallback(frontmatter_text: str) -> dict[str, Any]:
    """Minimal parser for scalar keys and block scalars (|, |-)."""
    result: dict[str, Any] = {}
    lines = frontmatter_text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        if line.startswith(" ") or (line[:1] == "\t") or ":" not in line:
            raise ValueError(f"Unsupported YAML syntax in line: {line}")

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        if value in {"|", "|-", ">", ">-"}:
            i += 1
            block_lines: list[str] = []
            while i < len(lines):
                nxt = lines[i]
                if nxt.startswith("  "):
                    block_lines.append(nxt[2:])
                    i += 1
                    continue
                if not nxt.strip():
                    block_lines.append("")
                    i += 1
                    continue
                break
            result[key] = "\n".join(block_lines).strip()
            continue

        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        result[key] = value
        i += 1

    return result


def parse_skill_frontmatter_dict(skill_dir: Path) -> dict[str, Any]:
    """Parse SKILL.md YAML frontmatter into a dict without PyYAML (stdlib only)."""
    content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    if not content.startswith("---"):
        raise ValueError("No YAML frontmatter found")
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        raise ValueError("Invalid frontmatter format")
    return _parse_frontmatter_fallback(match.group(1))
