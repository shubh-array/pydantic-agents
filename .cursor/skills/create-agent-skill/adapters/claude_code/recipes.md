# Claude Code adapter recipes

- Subagent and description calls use `claude -p` with the same `CLAUDECODE`-stripped environment pattern as upstream `skill-creator` scripts.
- `allowed-tools` is permitted in frontmatter per Claude Code docs; other agents may reject it (D-007).
