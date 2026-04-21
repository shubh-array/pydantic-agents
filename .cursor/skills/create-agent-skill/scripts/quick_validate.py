"""Phase A: validate SKILL.md frontmatter using the active adapter.

Also performs a Phase B-adjacent structural check: when a sibling
``evals/evals.json`` is present, it is schema-validated against
``references/schemas/evals.schema.json`` so malformed eval authoring
is caught before Phase C.
"""

from __future__ import annotations

import argparse
import json
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
    issues = adapter.validate_frontmatter(fm, skill_dir=str(skill_path))
    if issues:
        return False, "; ".join(issues)

    evals_issue = _validate_evals_if_present(skill_path)
    if evals_issue:
        return False, evals_issue

    return True, "Skill is valid!"


def _validate_evals_if_present(skill_path: Path) -> str:
    """Phase B gate: schema-validate ``evals/evals.json`` when present.

    Returns an error string on failure, ``""`` on success or when the file
    is absent. ``jsonschema`` is a hard requirement (dev dep); if absent,
    the gate fails loudly rather than silently skipping.
    """
    evals_file = skill_path / "evals" / "evals.json"
    if not evals_file.is_file():
        return ""
    try:
        import jsonschema
    except ImportError as exc:
        return f"jsonschema required for Phase B validation: {exc}"
    schema_path = (
        _skill_root(Path(__file__))
        / "references"
        / "schemas"
        / "evals.schema.json"
    )
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        data = json.loads(evals_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return f"evals/evals.json unreadable: {exc}"
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as exc:
        return f"evals/evals.json schema: {exc.message}"
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Quick-validate a skill directory")
    parser.add_argument("skill_directory", type=Path)
    args = parser.parse_args()
    ok, msg = validate_skill(args.skill_directory)
    print(msg)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
