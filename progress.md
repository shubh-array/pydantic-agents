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
| 5 | Function Tools | Done |
| 6 | Capabilities | Done |
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

### Step 5: Function Tools

Created stub tools for both domains. Marketing tools: `search_brand_assets` (RunContext — accesses company name), `get_content_calendar` (RunContext + ModelRetry for invalid channels), `check_competitor_claims` (plain — no context needed). Operations tools: `query_monitoring` (RunContext), `check_deploy_status` (plain), `search_runbooks` (plain + ModelRetry for unmatched queries). Tools are registered via the `tools` list argument to `Agent` (through `_build_agent()`), making them reusable across agents. PydanticAI auto-generates tool schemas from type hints and Google-style docstrings. Verified: operations agent calls `query_monitoring` + `check_deploy_status` and synthesizes an `IncidentStatus`; marketing agent calls `get_content_calendar` and reasons about scheduling; message trace shows tool call/return pairs.

**Files:**
- `pba-agent/src/tools/__init__.py`
- `pba-agent/src/tools/marketing_tools.py` — `search_brand_assets`, `get_content_calendar`, `check_competitor_claims`
- `pba-agent/src/tools/operations_tools.py` — `query_monitoring`, `check_deploy_status`, `search_runbooks`
- `pba-agent/src/base_agent.py` — added `tools` parameter to `_build_agent()`
- `pba-agent/examples/05_tools.py`

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
│   ├── operations_agent.py       # Operations domain factory
│   ├── tools/                    # Function tools by domain (Step 5)
│   │   ├── __init__.py
│   │   ├── marketing_tools.py
│   │   └── operations_tools.py
│   └── capabilities/             # Custom capabilities (Step 6)
│       ├── __init__.py
│       ├── audit_logger.py
│       └── brand_voice.py
└── examples/
    ├── 01_agent_basics.py        # Step 1
    ├── 02_base_agent.py          # Step 2
    ├── 03_domain_agents.py       # Step 3
    ├── 04_structured_output.py   # Step 4
    ├── 05_tools.py               # Step 5
    └── 06_capabilities.py        # Step 6
```

### Step 6: Capabilities

Built two custom capabilities by subclassing `AbstractCapability`. `AuditLogger` uses `wrap_model_request` and `wrap_tool_execute` lifecycle hooks to log every model request and tool execution with timing data to an in-memory audit trail. `BrandVoiceGuardrail` uses `after_model_request` to scan model responses for forbidden marketing phrasings (from the `<brand_voice_extensions>` section) and raises `ModelRetry` when a violation is found, forcing the model to self-correct. Extended `_build_agent()` with a `capabilities` parameter so domain factories can pass capabilities into the agent constructor via `Agent.from_spec()`. Verified: audit logger captures all model requests and tool calls with timing; guardrail is active and would trigger retries on forbidden phrasings; both capabilities compose cleanly on the same agent.

**Key concepts learned:**
- `AbstractCapability` is the base class for reusable, composable agent behavior
- Capabilities bundle tools, lifecycle hooks, instructions, and model settings into one object
- Lifecycle hooks: `wrap_model_request` (middleware around LLM calls), `wrap_tool_execute` (middleware around tool calls), `after_model_request` (post-process responses)
- `ModelRetry` can be raised from hooks to force the model to self-correct
- Capabilities compose: multiple capabilities fire in registration order (`before_*`) and reverse order (`after_*`)
- Built-in capabilities include `Thinking`, `WebSearch`, `WebFetch`, `Hooks`, `PrefixTools`
- Custom capabilities with mutable state are Python-only (not serializable to YAML specs)

**Files:**
- `pba-agent/src/capabilities/__init__.py`
- `pba-agent/src/capabilities/audit_logger.py` — `AuditLogger` (cross-cutting, logs model requests + tool calls)
- `pba-agent/src/capabilities/brand_voice.py` — `BrandVoiceGuardrail` (marketing-specific, rejects forbidden phrasings)
- `pba-agent/src/base_agent.py` — added `capabilities` parameter to `_build_agent()`
- `pba-agent/examples/06_capabilities.py`

---

## How to Resume (Step 7: Observability)

### Spec reference

Open `docs/superpowers/specs/2026-04-24-pydantic-ai-learning-path-design.md` and go to **Section 5, Step 7** (around line 317).

### What Step 7 covers

- Logfire SDK: `logfire.configure()`, `logfire.instrument_pydantic_ai()`
- Tracing agent runs: messages, tool calls, token usage, latency
- `TestModel` for unit testing without hitting OpenAI
- `agent.override(deps=...)` for test dependency injection
- `capture_run_messages()` for debugging
- Files to produce: `examples/07_observability.py`, `tests/__init__.py`, `tests/test_base_agent.py`, `tests/test_marketing_agent.py`, `tests/test_operations_agent.py`

### Docs to fetch first (docs-first protocol)

Per the spec's Section 3 table, fetch these PydanticAI docs before coding Step 7:

1. `list_doc_sources` via MCP `ai-docs`
2. `fetch_docs` on `https://pydantic.dev/docs/ai/integrations/logfire/index.md` (Logfire integration)
3. `fetch_docs` on `https://pydantic.dev/docs/ai/guides/testing/index.md` (Testing)

Note: PydanticAI docs have migrated from `ai.pydantic.dev` to `pydantic.dev/docs/ai/`. The MCP server's allowed domains may need the redirect-aware `WebFetch` tool as a fallback.

### How to run examples

```bash
cd pba-agent
env $(cat .env) uv run python examples/07_observability.py
uv run pytest tests/
```

### Key context for the new session

- All domain agents share `AgentDeps` from `src/deps.py`
- Factory functions are in `src/base_agent.py`, `src/marketing_agent.py`, `src/operations_agent.py`
- `src/base_agent.py` exports `compose_prompt()` and `_build_agent()` for reuse
- `_build_agent()` accepts `output_type`, `tools`, and `capabilities` params — added in Steps 4-6
- Output models live in `src/models.py`: `MarketingDraft`, `IncidentStatus`, `Failed`
- Tool stubs live in `src/tools/`: `marketing_tools.py` and `operations_tools.py`
- Custom capabilities live in `src/capabilities/`: `AuditLogger` and `BrandVoiceGuardrail`
- Tools use both `RunContext[AgentDeps]` (context-aware) and plain signatures (no context)
- `ModelRetry` is used in tools (`get_content_calendar`, `search_runbooks`) and capabilities (`BrandVoiceGuardrail`)
- Example scripts use `sys.path.insert(0, 'src')` for imports (no package install)
- YAML specs live in `specs/` and are loaded via `AgentSpec.from_file()` + `Agent.from_spec()`
- Python target is `>=3.11`, Ruff target is `py311`
