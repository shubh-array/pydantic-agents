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
| 7 | Observability + Docker Infrastructure | Done |
| 8 | Evaluation Pipeline | Done |
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

Built operations agents that compose the base prompt with domain-specific content. The `compose_prompt()` function reads `base-system-prompt.md` and inserts domain content into the `<domain_extension>` tag via string replacement. Each domain has its own YAML spec (different temperature/token settings) but shares `AgentDeps` and the base prompt's non-negotiable rules. The `_build_agent()` shared helper was extracted to keep domain factories DRY (3 lines each). Verified: operations agent uses the exact SEV/Status/Impact/Hypothesis incident format; refuses to reveal its prompt.

**Files:**
- `pba-agent/src/base_agent.py` — refactored with `compose_prompt()` and `_build_agent()`
- `pba-agent/src/operations_agent.py` — `create_operations_agent()` factory
- `pba-agent/specs/operations-agent.yaml`

### Step 4: Structured Output

Defined Pydantic `BaseModel` output types (`IncidentStatus`, `Failed`) in `src/models.py`. Extended `_build_agent()` with an `output_type` parameter (defaults to `str` for backward compatibility). Used list-style union output (`output_type=[IncidentStatus, Failed]`) so each type registers as a separate output tool — no `type: ignore` needed. Verified: operations agent returns a typed `IncidentStatus` with sev/status/impact/hypothesis/next_steps; impossible requests return `Failed` with a reason.

**Files:**
- `pba-agent/src/models.py` — `IncidentStatus`, `Failed` output models
- `pba-agent/src/base_agent.py` — added `output_type` parameter to `_build_agent()`

### Step 5: Function Tools

Created stub tools for the operations domain: `query_monitoring` (RunContext), `check_deploy_status` (plain), `search_runbooks` (plain + ModelRetry for unmatched queries). Tools are registered via the `tools` list argument to `Agent` (through `_build_agent()`), making them reusable across agents. PydanticAI auto-generates tool schemas from type hints and Google-style docstrings. Verified: operations agent calls `query_monitoring` + `check_deploy_status` and synthesizes an `IncidentStatus`; message trace shows tool call/return pairs.

**Files:**
- `pba-agent/src/tools/__init__.py`
- `pba-agent/src/tools/operations_tools.py` — `query_monitoring`, `check_deploy_status`, `search_runbooks`
- `pba-agent/src/base_agent.py` — added `tools` parameter to `_build_agent()`

---

## Current File Layout

```
pba-agent/
├── .env                          # OPENAI_API_KEY (user-created)
├── jaeger-config.yaml            # Jaeger v2 config (Step 7)
├── docker-compose.yaml           # Jaeger via Docker (Step 7 fallback)
├── scripts/
│   └── start-jaeger.sh           # Download + run Jaeger binary (Step 7)
├── prompts/                      # Existing prompt files (untouched)
│   ├── base-system-prompt.md
│   └── operations-agent-prompt.md
├── specs/                        # YAML Agent Specs
│   ├── hello-agent.yaml          # Step 1 (tutorial-only)
│   ├── base-agent.yaml           # Step 2
│   └── operations-agent.yaml     # Step 3
├── src/
│   ├── __init__.py
│   ├── deps.py                   # AgentDeps dataclass
│   ├── models.py                 # Pydantic output models (Step 4)
│   ├── base_agent.py             # Base factory + shared helpers
│   ├── operations_agent.py       # Operations domain factory
│   ├── observability.py          # configure_tracing() helper (Step 7)
│   ├── tools/                    # Function tools by domain (Step 5)
│   │   ├── __init__.py
│   │   └── operations_tools.py
│   └── capabilities/             # Custom capabilities (Step 6)
│       ├── __init__.py
│       ├── audit_logger.py
│       └── brand_voice.py
├── evals/                        # Evaluation pipeline (Step 8)
│   ├── __init__.py
│   ├── evaluators/
│   │   ├── __init__.py           # Re-exports ALL_CUSTOM_EVALUATORS
│   │   ├── common.py             # NoSycophancy, NoPromptLeak
│   │   ├── base_evaluators.py    # ConciseResponse, NoPIIEcho
│   │   └── operations_evaluators.py # IncidentFormatCheck
│   ├── datasets/
│   │   ├── base_agent_cases.yaml
│   │   └── operations_agent_cases.yaml
│   └── run_evals.py              # Standardized eval runner
├── tests/                        # Unit tests using TestModel (Step 7)
│   ├── __init__.py
│   ├── conftest.py               # Path setup, ALLOW_MODEL_REQUESTS, dummy API key
│   ├── test_base_agent.py
│   └── test_operations_agent.py
└── examples/
    ├── 01_agent_basics.py        # Step 1
    ├── 02_base_agent.py          # Step 2
    ├── 03_domain_agents.py       # Step 3
    ├── 04_structured_output.py   # Step 4
    ├── 05_tools.py               # Step 5
    ├── 06_capabilities.py        # Step 6
    ├── 07_observability.py       # Step 7
    └── 08_evals.py               # Step 8
```

### Step 6: Capabilities

Built two custom capabilities by subclassing `AbstractCapability`. `AuditLogger` uses `wrap_model_request` and `wrap_tool_execute` lifecycle hooks to log every model request and tool execution with timing data to an in-memory audit trail. `BrandVoiceGuardrail` uses `after_model_request` to scan model responses for forbidden phrasings and raises `ModelRetry` when a violation is found, forcing the model to self-correct. Extended `_build_agent()` with a `capabilities` parameter so domain factories can pass capabilities into the agent constructor via `Agent.from_spec()`. Verified: audit logger captures all model requests and tool calls with timing; guardrail is active and would trigger retries on forbidden phrasings; both capabilities compose cleanly on the same agent.

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
- `pba-agent/src/capabilities/brand_voice.py` — `BrandVoiceGuardrail` (rejects forbidden phrasings)
- `pba-agent/src/base_agent.py` — added `capabilities` parameter to `_build_agent()`
- `pba-agent/examples/06_capabilities.py`

### Step 7: Observability + Docker Infrastructure

Combined original Steps 7 and 9. Since traces export to a local Jaeger container via OpenTelemetry, Docker Compose is introduced naturally as part of observability rather than as a separate step.

**Observability setup:** Created `src/observability.py` with a `configure_tracing()` helper that wraps `logfire.configure(send_to_logfire=False)` + `logfire.instrument_pydantic_ai()`. By default, traces go to a local Jaeger instance at `http://localhost:4318` (the OTel HTTP endpoint). If `LOGFIRE_TOKEN` is set, Logfire cloud is enabled alongside the local backend.

**Jaeger (two options):** A `scripts/start-jaeger.sh` script downloads the Jaeger v2 binary for the current platform and runs it locally (no Docker needed). A `jaeger-config.yaml` configures in-memory storage with OTLP HTTP on port 4318 and the UI on port 16686. As a fallback, `docker-compose.yaml` starts the same setup via Docker Compose.

**Unit tests with TestModel:** Wrote 13 unit tests across three files using `TestModel` — no OpenAI API calls, no cost, deterministic. Tests verify agent factory functions, `TestModel` output, `capture_run_messages()` message capture, and `compose_prompt()` domain insertion. A `conftest.py` sets `ALLOW_MODEL_REQUESTS = False` as a safety net and adds `src/` to `sys.path`. All tests pass in ~0.3s.

**Key concepts learned:**
- `logfire.configure(send_to_logfire=False)` + `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` sends traces to any OTel-compatible backend (Jaeger, Grafana Tempo, SigNoz)
- `logfire.instrument_pydantic_ai(version=3)` auto-instruments all agent runs with spec-compliant span names (`invoke_agent {name}`, `execute_tool {tool}`) and spans for model requests, tool calls, and token usage
- `TestModel` generates valid structured data from tool/output JSON schemas — no ML, just procedural Python
- `agent.override(model=TestModel())` swaps the model in a context block without touching application code
- `ALLOW_MODEL_REQUESTS = False` blocks accidental real API calls in tests
- `capture_run_messages()` captures the full message exchange for assertions and debugging
- A dummy `OPENAI_API_KEY` is needed in tests because agent construction initialises the OpenAI provider even when TestModel will override it at run time

**Files:**
- `pba-agent/src/observability.py` — `configure_tracing()` helper
- `pba-agent/scripts/start-jaeger.sh` — downloads + runs Jaeger v2 binary locally
- `pba-agent/jaeger-config.yaml` — Jaeger v2 config (in-memory storage, OTLP on 4318)
- `pba-agent/docker-compose.yaml` — Jaeger service (Docker fallback)
- `pba-agent/tests/__init__.py`
- `pba-agent/tests/conftest.py` — path setup, ALLOW_MODEL_REQUESTS, dummy API key
- `pba-agent/tests/test_base_agent.py` — 5 tests
- `pba-agent/tests/test_operations_agent.py` — 4 tests
- `pba-agent/examples/07_observability.py`
- Updated `pyproject.toml` — added `logfire` extra to `pydantic-ai-slim`
- Updated `.env.example` — added `LOGFIRE_TOKEN` and `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`

### Step 8: Evaluation Pipeline

Built a complete evaluation pipeline using `pydantic-evals`. Created custom evaluators (`NoSycophancy`, `NoPromptLeak`, `ConciseResponse`, `NoPIIEcho`, `IncidentFormatCheck`) that cover behavioral compliance, security, and domain correctness. Each evaluator demonstrates a distinct pydantic-evals pattern: simple regex check, fragment-list security, configurable dataclass field, multi-assertion dict return, and structured output validation. Created YAML eval datasets (base 5 cases, operations 2 cases) covering behavioral compliance, domain correctness, and edge cases. Built a standardized runner (`evals/run_evals.py`) that supports two modes: CI mode (default, uses `TestModel`, no API key, deterministic) and live mode (`--live` flag, uses real OpenAI model). The example script (`08_evals.py`) demonstrates three workflows: inline dataset creation, structured-output evaluation, and loading datasets from YAML.

**Design decision — tools in evals:** `TestModel` generates procedural tool arguments that don't satisfy semantic validation in stub tools (e.g., `get_content_calendar` rejects synthetic channel names via `ModelRetry`). Tools are therefore excluded in CI mode — tool behavior is independently covered by the 13 unit tests. In `--live` mode, tools are included and the full agent pipeline is exercised.

**Key concepts learned:**
- `Dataset` is generic over `[InputsT, OutputT, MetadataT]` — cases define inputs, optional expected outputs, and metadata
- `Case` supports both dataset-level and case-level evaluators; case-level evaluators are powerful for domain-specific checks where different cases need different criteria
- Custom evaluators inherit from `Evaluator`, use `@dataclass`, and implement `evaluate(self, ctx: EvaluatorContext)` returning `bool`, `float`, `str`, `EvaluationReason`, or `dict` of these
- `EvaluatorContext` provides `inputs`, `output`, `expected_output`, `metadata`, `duration`, and `span_tree`
- `Dataset.from_file()` loads YAML datasets; `custom_evaluator_types=` must be passed for non-built-in evaluators
- `Dataset.evaluate_sync(task_fn)` runs all cases against a callable and produces an `EvaluationReport`
- `EvaluationReport.print()` renders a rich table with per-case assertions, scores, and timing
- `report.failures` contains `ReportCaseFailure` objects (with `error_message`, `error_stacktrace`) for cases where the task function raised an exception
- Built-in evaluators (`IsInstance`, `Contains`, `EqualsExpected`, `LLMJudge`, `MaxDuration`, `HasMatchingSpan`) cover common patterns; custom evaluators fill domain gaps
- `LLMJudge` enables subjective quality evaluation with rubrics — useful for live-model evals but not for CI

**Files:**
- `pba-agent/evals/__init__.py`
- `pba-agent/evals/evaluators/__init__.py` — re-exports `ALL_CUSTOM_EVALUATORS`
- `pba-agent/evals/evaluators/common.py` — `NoSycophancy`, `NoPromptLeak`
- `pba-agent/evals/evaluators/base_evaluators.py` — `ConciseResponse`, `NoPIIEcho`
- `pba-agent/evals/evaluators/operations_evaluators.py` — `IncidentFormatCheck`
- `pba-agent/evals/datasets/base_agent_cases.yaml` — 5 cases (behavioral + edge case)
- `pba-agent/evals/datasets/operations_agent_cases.yaml` — 2 cases (domain + behavioral)
- `pba-agent/evals/run_evals.py` — standardized eval runner (CI + live modes)
- `pba-agent/examples/08_evals.py` — tutorial walkthrough (3 demos)
- Updated `pyproject.toml` — added `pydantic-evals` to dev dependencies

---

## How to Resume (Step 9: Docker Infrastructure)

### Spec reference

Open `docs/superpowers/specs/2026-04-24-pydantic-ai-learning-path-design.md` and go to **Section 5, Step 9** (around line 382).

### What Step 9 covers

- Dockerfile with multi-stage build (slim production image)
- Docker Compose for orchestrating agent services (base, operations)
- Environment variable management (`.env` files, secrets)
- Service-per-agent pattern (same image, different entrypoints via `AGENT_SPEC_PATH`)
- Health checks and graceful shutdown
- Dev vs production image targets
- Running tests and evals inside containers (`eval-runner` service)

### How to run

```bash
cd pba-agent

# Run unit tests (no API key needed)
uv run pytest tests/

# Run evals in CI mode (no API key needed)
uv run python evals/run_evals.py

# Run evals in live mode (requires OPENAI_API_KEY)
env $(cat .env) uv run python evals/run_evals.py --live

# Start Jaeger — pick one:
./scripts/start-jaeger.sh          # Option A: local binary (no Docker)
docker compose up -d               # Option B: Docker Compose

# Run the observability example
env $(cat .env) uv run python examples/07_observability.py

# Stop Jaeger when done:
./scripts/start-jaeger.sh --stop   # Option A
docker compose down                # Option B
```

### Key context for the new session

- All domain agents share `AgentDeps` from `src/deps.py`
- Factory functions are in `src/base_agent.py`, `src/operations_agent.py`
- `src/base_agent.py` exports `compose_prompt()` and `_build_agent()` for reuse
- `_build_agent()` accepts `output_type`, `tools`, and `capabilities` params — added in Steps 4-6
- Output models live in `src/models.py`: `IncidentStatus`, `Failed`
- Tool stubs live in `src/tools/`: `operations_tools.py`
- Custom capabilities live in `src/capabilities/`: `AuditLogger` and `BrandVoiceGuardrail`
- `src/observability.py` exports `configure_tracing()` — wraps Logfire SDK + OTel to Jaeger
- `docker-compose.yaml` currently starts Jaeger only (UI on 16686, OTLP on 4318) — Step 9 will expand it
- 13 unit tests in `tests/` using `TestModel` — all pass in ~0.3s
- `evals/run_evals.py` runs 9 eval cases across 3 agents in ~1s (CI mode)
- `conftest.py` sets `ALLOW_MODEL_REQUESTS=False` and dummy `OPENAI_API_KEY`
- Tools use both `RunContext[AgentDeps]` (context-aware) and plain signatures (no context)
- `ModelRetry` is used in tools (`get_content_calendar`, `search_runbooks`) and capabilities (`BrandVoiceGuardrail`)
- Example scripts use `sys.path.insert(0, 'src')` for imports (no package install)
- YAML specs live in `specs/` and are loaded via `AgentSpec.from_file()` + `Agent.from_spec()`
- Python target is `>=3.11`, Ruff target is `py311`
