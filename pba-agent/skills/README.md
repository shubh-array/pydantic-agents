# PBA agent skills

Customer-facing skills used by Powered-by-Array (PBA) agents.

## Directory convention

```
pba-agent/skills/<category>/<skill-id>/SKILL.md
```

- **`<category>/`** is filesystem-only — it groups related skills (e.g.
  `compliance/`, `domain-hr/`) but is not referenced from `voice-spec.yaml`
  or the renderer. Move a skill between categories without touching any
  build input.
- **`<skill-id>/`** is the canonical id of the skill. The directory name
  must match the `name:` field in the skill's frontmatter.
- **`SKILL.md`** uses the standard format (YAML frontmatter + Markdown
  body). No `pba:` frontmatter extension; the file is structurally
  identical to skills authored anywhere else in the repo.

## Authoring a skill

Use the existing meta-skill at
`.cursor/skills/create-agent-skill/SKILL.md`. Invoke it with
`--skill-path` pointing at the target directory directly — there is no
intake wrapper and no "move skill after authoring" step. The harness
operates on the skill in place.

The workspace it produces (`<skill-id>-workspace/iteration-N/...`) sits
as a sibling of the skill directory, e.g.
`pba-agent/skills/compliance/<skill-id>-workspace/iteration-1/`.

## How skills are wired into agents

A skill becomes part of an agent's prompt by being listed in
`pba-agent/voice-spec/voice-spec.yaml` under a domain's
`skills_enabled`. The renderer (`pba-agent/scripts/render_prompts.py`)
walks `pba-agent/skills/*/<skill-id>/SKILL.md`, strips frontmatter, and
inlines the body into the matching domain's `<domain_extension>` block.

A YAML rule with `skill_ref: <skill-id>` documents that the rule's
coverage is provided by that skill — it is not also rendered as a
bullet in `<non_negotiable>`.

## Current skills

- `compliance/skill-ai-disclosure-external/` — AI-powered + hiring-company
  disclosure on the first message of any thread with an external party.
