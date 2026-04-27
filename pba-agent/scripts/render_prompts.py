"""Render per-domain system prompts from the voice spec.

Deterministic: same input bytes ⇒ same output bytes. The only source of
variance is the ``rendered:`` timestamp in the header comment, which is
derived from ``voice-spec.yaml``'s mtime (or the ``SOURCE_DATE_EPOCH``
env var when set), so re-running on an unchanged input produces a
byte-identical output file.

Usage (from pba-agent/):
    uv run python scripts/render_prompts.py
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

PBA_DIR = Path(__file__).resolve().parent.parent
VOICE_SPEC = PBA_DIR / "voice-spec" / "voice-spec.yaml"
BASE_PROMPT = PBA_DIR / "prompts" / "base-system-prompt.md"
GENERATED_DIR = PBA_DIR / "prompts" / "_generated"
SKILLS_ROOT = PBA_DIR / "skills"

VOICE_RULES_BEGIN = "<!-- voice-rules:begin -->"
VOICE_RULES_END = "<!-- voice-rules:end -->"
DOMAIN_EXT_BEGIN = "<!-- domain-extension:begin -->"
DOMAIN_EXT_END = "<!-- domain-extension:end -->"

_FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)


def _rendered_timestamp() -> str:
    """Stable ISO-8601 UTC timestamp.

    Falls back to ``SOURCE_DATE_EPOCH`` (reproducible-builds convention),
    then to the spec file's mtime. The wall clock is never read.
    """
    epoch_env = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch_env:
        epoch = int(epoch_env)
    else:
        epoch = int(VOICE_SPEC.stat().st_mtime)
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_spec() -> dict:
    return yaml.safe_load(VOICE_SPEC.read_text(encoding="utf-8"))


def _rule_applies(rule: dict, domain_id: str) -> bool:
    """A rule renders into a domain when applies_to is 'all' or includes that id."""
    applies_to = rule.get("applies_to")
    if applies_to == "all":
        return True
    if isinstance(applies_to, list) and domain_id in applies_to:
        return True
    return False


def _replace_block(source: str, begin_marker: str, end_marker: str, replacement_inner: str) -> str:
    """Replace the content strictly between (begin, end) with replacement_inner.

    Markers stay on their own lines. The empty case (``{begin}\\n{end}`` with
    nothing between) is handled by collapsing the inner replacement to an
    empty string so output stays compact when no rules / no extension apply.
    """
    pattern = re.compile(
        rf"{re.escape(begin_marker)}\n.*?{re.escape(end_marker)}",
        re.DOTALL,
    )
    if replacement_inner:
        new_block = f"{begin_marker}\n{replacement_inner}\n{end_marker}"
    else:
        new_block = f"{begin_marker}\n{end_marker}"
    new_text, count = pattern.subn(lambda _m: new_block, source, count=1)
    if count != 1:
        raise RuntimeError(
            f"Expected exactly 1 block between {begin_marker} and {end_marker}, found {count}."
        )
    return new_text


def _render_voice_rules(rules: list, domain_id: str) -> str:
    """Render the bullet list to insert between the voice-rules markers.

    Rules with ``skill_ref`` are skipped — their coverage is provided by
    the inlined skill body in the domain extension.
    """
    lines: list[str] = []
    for rule in rules:
        if not _rule_applies(rule, domain_id):
            continue
        if rule.get("skill_ref"):
            continue
        rid = rule["id"]
        text = rule["text"]
        lines.append(f"<!-- rule:{rid} -->")
        lines.append(f"- {text}")
    return "\n".join(lines)


def _strip_frontmatter(skill_text: str) -> str:
    """Strip a leading ``---\\n...\\n---\\n`` block, if present."""
    return _FRONTMATTER_RE.sub("", skill_text, count=1)


def _find_skill(skill_id: str) -> Path:
    """Walk ``pba-agent/skills/*/<skill_id>/SKILL.md`` (one category level)."""
    matches = sorted(SKILLS_ROOT.glob(f"*/{skill_id}/SKILL.md"))
    if not matches:
        raise FileNotFoundError(f"No SKILL.md found for skill_id={skill_id!r} under {SKILLS_ROOT}")
    if len(matches) > 1:
        raise RuntimeError(f"Ambiguous skill_id={skill_id!r}: multiple matches {matches}")
    return matches[0]


def _render_domain_extension(domain: dict) -> str:
    """Compose the inner body of <domain-extension:begin/end>.

    Layout: ``extension_text`` → blank line → for each ``skills_enabled``
    id, the skill's SKILL.md body with frontmatter stripped (skills
    separated from each other by a single blank line).
    """
    parts: list[str] = []
    extension_text = (domain.get("extension_text") or "").rstrip("\n")
    if extension_text:
        parts.append(extension_text)
    for skill_id in domain.get("skills_enabled") or []:
        skill_path = _find_skill(skill_id)
        body = _strip_frontmatter(skill_path.read_text(encoding="utf-8")).rstrip("\n")
        parts.append(body)
    return "\n\n".join(parts)


def render_domain(spec: dict, domain: dict) -> str:
    """Return the fully-rendered prompt text for one domain."""
    base = BASE_PROMPT.read_text(encoding="utf-8")
    rules_block = _render_voice_rules(spec.get("rules", []), domain["id"])
    ext_block = _render_domain_extension(domain)
    out = _replace_block(base, VOICE_RULES_BEGIN, VOICE_RULES_END, rules_block)
    out = _replace_block(out, DOMAIN_EXT_BEGIN, DOMAIN_EXT_END, ext_block)
    header = f"<!-- voice-spec-version: {spec['version']} rendered: {_rendered_timestamp()} -->\n"
    return header + out


def main() -> None:
    spec = _load_spec()
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    for domain in spec.get("domains", []):
        rendered = render_domain(spec, domain)
        out_path = GENERATED_DIR / f"{domain['id']}.md"
        out_path.write_text(rendered, encoding="utf-8")
        print(f"wrote {out_path.relative_to(PBA_DIR)}")


if __name__ == "__main__":
    main()
