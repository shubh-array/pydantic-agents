"""Phase A: validate SKILL.md frontmatter using the active adapter."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _skill_root(here: Path) -> Path:
    return here.resolve().parents[1]


def _bootstrap() -> None:
    root = _skill_root(Path(__file__))
    rs = str(root)
    if rs not in sys.path:
        sys.path.insert(0, rs)


def validate_skill(skill_path: Path) -> tuple:
    _bootstrap()
    from adapters import get_active_adapter
    from scripts.utils import parse_skill_frontmatter_dict

    skill_path = skill_path.resolve()
    skill_md = skill_path / "SKILL.md"
    if not skill_md.is_file():
        return False, "SKILL.md not found"

    content = skill_md.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return False, "No YAML frontmatter found"

    try:
        fm = parse_skill_frontmatter_dict(skill_path)
    except ValueError as exc:
        return False, str(exc)

    if "name" not in fm:
        return False, "Missing 'name' in frontmatter"
    if "description" not in fm:
        return False, "Missing 'description' in frontmatter"

    name = fm.get("name", "")
    if not isinstance(name, str) or not name.strip():
        return False, "Name must be a non-empty string"
    name = name.strip()
    if not re.match(r"^[a-z0-9-]+$", name):
        return False, f"Name {name!r} must be kebab-case"
    if name.startswith("-") or name.endswith("-") or "--" in name:
        return False, f"Name {name!r} has invalid hyphen placement"
    if len(name) > 64:
        return False, f"Name too long ({len(name)} > 64)"

    desc = fm.get("description", "")
    if not isinstance(desc, str):
        return False, "Description must be a string"
    desc = desc.strip()
    if "<" in desc or ">" in desc:
        return False, "Description cannot contain angle brackets"
    if len(desc) > 1024:
        return False, f"Description too long ({len(desc)} > 1024)"

    adapter = get_active_adapter()
    issues = adapter.validate_frontmatter(fm)
    if issues:
        return False, "; ".join(issues)

    return True, "Skill is valid!"


def main() -> None:
    parser = argparse.ArgumentParser(description="Quick-validate a skill directory")
    parser.add_argument("skill_directory", type=Path)
    args = parser.parse_args()
    ok, msg = validate_skill(args.skill_directory)
    print(msg)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
