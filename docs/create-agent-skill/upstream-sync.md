# Upstream Sync Procedure

1. Clone / pull latest upstream `skill-creator` to a scratch dir.
2. For each file in our `create-agent-skill/` tree, find upstream file with the same
   filename (ignore path differences per D-008 in `upstream-deltas.md`).
3. Diff. For each hunk:
   a. If it touches a line with a "D-NNN" comment, review the row in
      `upstream-deltas.md` before accepting.
   b. Otherwise apply the hunk.
4. Run: `uv run pytest tests/create-agent-skill/`
5. If green, commit: `sync: upstream skill-creator <description>` citing any
   divergence IDs affected.
6. If red, resolve. New divergence → new row in `upstream-deltas.md`.
