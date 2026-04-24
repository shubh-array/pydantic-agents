# PydanticAI Learning Path — Progress Tracker

**Spec:** `docs/superpowers/specs/2026-04-24-pydantic-ai-learning-path-design.md`

---

## Progress

| Step | Title | Status |
|------|-------|--------|
| 1 | Agent Basics + YAML Specs | Done |
| 2 | Base Prompt + Dependencies | Done |
| 3 | Domain Agent Composition | Done |
| 4 | Structured Output | Done |
| 5 | Function Tools | Not started |
| 6 | Capabilities | Not started |
| 7 | Observability | Not started |
| 8 | Evaluation Pipeline | Not started |
| 9 | Docker Infrastructure | Not started |

---

## What Was Completed

### Step 1: Agent Basics + YAML Specs

Installed `pydantic-ai-slim[openai,spec]`. Created a minimal agent in Python, ran it with `run_sync()`, then moved the config to a YAML Agent Spec and loaded it with `Agent.from_file()`. A third demo proved that different `instructions` produce different agent personalities (formal diplomat vs. casual surfer).

**Files:**
- `pba-agent/specs/hello-agent.yaml`
- `pba-agent/examples/01_agent_basics.py`
- `.env.example` (project root)
- `pba-agent/.env` (user-created, holds `OPENAI_API_KEY`)

### Step 2: Base Prompt + Dependencies

Loaded the full `base-system-prompt.md` (176 lines of XML-tagged instructions) as the agent's instructions. Introduced `AgentDeps` dataclass (`user_name`, `company`, `domain`, `extra`) and wired it through `deps_type`. Used `@agent.instructions` with `RunContext[AgentDeps]` to inject user context dynamically at runtime. Verified the base prompt's non-negotiable rules: no sycophancy ("2+2 is 4." with no filler), confidentiality refusal, and lead-with-the-answer output.

**Files:**
- `pba-agent/src/__init__.py`
- `pba-agent/src/deps.py` — `AgentDeps` dataclass
- `pba-agent/src/base_agent.py` — `create_base_agent()` factory, `compose_prompt()`, `_build_agent()`
- `pba-agent/specs/base-agent.yaml`
- `pba-agent/examples/02_base_agent.py`

### Step 3: Domain Agent Composition

Built marketing and operations agents that compose the base prompt with domain-specific content. The `compose_prompt()` function reads `base-system-prompt.md` and inserts domain content into the `<domain_extension>` tag via string replacement. Each domain has its own YAML spec (different temperature/token settings) but shares `AgentDeps` and the base prompt's non-negotiable rules. The `_build_agent()` shared helper was extracted to keep domain factories DRY (3 lines each). Verified: marketing agent produces LinkedIn-format posts with brand voice; operations agent uses the exact SEV/Status/Impact/Hypothesis incident format; both refuse to reveal their prompts.

**Files:**
- `pba-agent/src/base_agent.py` — refactored with `compose_prompt()` and `_build_agent()`
- `pba-agent/src/marketing_agent.py` — `create_marketing_agent()` factory
- `pba-agent/src/operations_agent.py` — `create_operations_agent()` factory
- `pba-agent/specs/marketing-agent.yaml`
- `pba-agent/specs/operations-agent.yaml`
- `pba-agent/examples/03_domain_agents.py`

### Step 4: Structured Output

Defined Pydantic `BaseModel` output types (`MarketingDraft`, `IncidentStatus`, `Failed`) in `src/models.py`. Extended `_build_agent()` with an `output_type` parameter (defaults to `str` for backward compatibility). Used list-style union output (`output_type=[MarketingDraft, Failed]`) so each type registers as a separate output tool — no `type: ignore` needed. Verified: marketing agent returns a typed `MarketingDraft` with channel/word_count/tone/content fields; operations agent returns a typed `IncidentStatus` with sev/status/impact/hypothesis/next_steps; impossible requests return `Failed` with a reason.

**Files:**
- `pba-agent/src/models.py` — `MarketingDraft`, `IncidentStatus`, `Failed` output models
- `pba-agent/src/base_agent.py` — added `output_type` parameter to `_build_agent()`
- `pba-agent/examples/04_structured_output.py`

---

## Current File Layout

```
pba-agent/
├── .env                          # OPENAI_API_KEY (user-created)
├── prompts/                      # Existing prompt files (untouched)
│   ├── base-system-prompt.md
│   ├── marketing-agent-prompt.md
│   └── operations-agent-prompt.md
├── specs/                        # YAML Agent Specs
│   ├── hello-agent.yaml          # Step 1 (tutorial-only)
│   ├── base-agent.yaml           # Step 2
│   ├── marketing-agent.yaml      # Step 3
│   └── operations-agent.yaml     # Step 3
├── src/
│   ├── __init__.py
│   ├── deps.py                   # AgentDeps dataclass
│   ├── models.py                 # Pydantic output models (Step 4)
│   ├── base_agent.py             # Base factory + shared helpers
│   ├── marketing_agent.py        # Marketing domain factory
│   └── operations_agent.py       # Operations domain factory
└── examples/
    ├── 01_agent_basics.py        # Step 1
    ├── 02_base_agent.py          # Step 2
    ├── 03_domain_agents.py       # Step 3
    └── 04_structured_output.py   # Step 4
```

---

## How to Resume (Step 5: Function Tools)

### Spec reference

Open `docs/superpowers/specs/2026-04-24-pydantic-ai-learning-path-design.md` and go to **Section 5, Step 5** (around line 263).

### What Step 5 covers

- `@agent.tool` (with RunContext) and `@agent.tool_plain` (without)
- Tool schemas from function signatures and docstrings
- `ModelRetry` for tool-level self-correction
- Registering tools via the `tools` constructor argument (for reuse)
- Passing deps to tools
- Files to produce: `src/tools/__init__.py`, `src/tools/marketing_tools.py`, `src/tools/operations_tools.py`, `examples/05_tools.py`

### Docs to fetch first (docs-first protocol)

Per the spec's Section 3 table, fetch these PydanticAI docs before coding Step 5:

1. `list_doc_sources` via MCP `ai-docs`
2. `fetch_docs` on `https://pydantic.dev/docs/ai/tools-toolsets/tools/index.md` (Function Tools)
3. `fetch_docs` on `https://pydantic.dev/docs/ai/tools-toolsets/tools-advanced/index.md` (Advanced Tool Features)

Note: PydanticAI docs have migrated from `ai.pydantic.dev` to `pydantic.dev/docs/ai/`. The MCP server's allowed domains may need the redirect-aware `WebFetch` tool as a fallback.

### How to run examples

```bash
cd pba-agent
env $(cat .env) uv run python examples/05_tools.py
```

### Key context for the new session

- All domain agents share `AgentDeps` from `src/deps.py`
- Factory functions are in `src/base_agent.py`, `src/marketing_agent.py`, `src/operations_agent.py`
- `src/base_agent.py` exports `compose_prompt()` and `_build_agent()` for reuse
- `_build_agent()` accepts `output_type` param (defaults to `str`) — added in Step 4
- Output models live in `src/models.py`: `MarketingDraft`, `IncidentStatus`, `Failed`
- Example scripts use `sys.path.insert(0, 'src')` for imports (no package install)
- YAML specs live in `specs/` and are loaded via `AgentSpec.from_file()` + `Agent.from_spec()`
- Python target is `>=3.11`, Ruff target is `py311`
