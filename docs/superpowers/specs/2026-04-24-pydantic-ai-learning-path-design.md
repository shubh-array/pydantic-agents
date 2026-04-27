# PydanticAI Base Agent — Learning Path & Scaffold Design

**Version:** 1.0
**Date:** 2026-04-24
**Approach:** Agent-First, Spiral Outward (each step builds real code that accumulates into the production scaffold)

---

## 1. Context

### What exists today

- **Prompt layer** — Well-crafted XML-tagged system prompts in `pba-agent/prompts/`:
  - `base-system-prompt.md` — universal base prompt (identity, instruction priority, non-negotiables, operating defaults, tool use, output contract, completeness contract, untrusted input policy, domain extension placeholder)
  - `marketing-agent-prompt.md` — marketing domain extension (brand voice, content rules, channel discipline, length contracts)
  - `operations-agent-prompt.md` — operations domain extension (incident response, deploy safety, blast radius, runbook discipline)
- **Research docs** — `docs/pba-agent/prompts/gpt5-prompt-research.md` traces design decisions to OpenAI sources (verified vs synthesized patterns).
- **No Python agent code** — no PydanticAI dependency, no runtime integration of these prompts.

### What we're building

A learning path that teaches PydanticAI from basics to advanced features, where each step produces real code that accumulates into a configurable, extensible agent framework with:
- A base agent loadable from YAML Agent Specs
- Domain agents (marketing, operations) composing the base
- Typed dependencies, structured outputs, function tools
- Reusable capabilities (tools + hooks + instructions bundled)
- Logfire observability
- Standardized `pydantic-evals` evaluation pipeline for every agent

---

## 2. Constraints

| Constraint | Value |
|---|---|
| LLM provider | OpenAI only |
| Package | `pydantic-ai-slim[openai]` |
| Config format | YAML Agent Specs (`Agent.from_file()` / `Agent.from_spec()`) |
| Python version | >=3.11 (matches existing `pyproject.toml`) |
| Package manager | `uv` |
| Linting/formatting | Ruff (existing config) |
| Testing | pytest + `TestModel` (unit) + `pydantic-evals` (behavioral) |
| Runtime | Docker containers via Docker Compose (cross-platform) |
| Docs verification | MCP `ai-docs` server consulted before each implementation step |

---

## 3. Docs-First Protocol

**Before implementing each step**, the agent (or developer) must consult the latest PydanticAI documentation via the MCP `ai-docs` server configured in `.cursor/mcp.json`. This ensures code uses the latest released SDK APIs, not stale training data.

### MCP Server Configuration

```json
{
  "mcpServers": {
    "ai-docs": {
      "command": "uvx",
      "args": [
        "--from", "mcpdoc", "mcpdoc",
        "--urls",
        "PydanticAI:https://ai.pydantic.dev/llms.txt",
        "MCP:https://modelcontextprotocol.io/llms.txt",
        "--transport", "stdio"
      ]
    }
  }
}
```

### Per-Step Verification Procedure

For each learning path step, before writing any code:

1. **`list_doc_sources`** — call the MCP tool to discover available documentation indexes.
2. **`fetch_docs`** on the PydanticAI `llms.txt` URL — get the doc index to find the relevant page URLs for the step's concepts.
3. **`fetch_docs`** on the specific page URLs — read the actual docs for the APIs being used in that step.
4. **Verify** — confirm that the API signatures, parameter names, and behavior described in the docs match what the step's code will use. If the docs show a different API than what training data suggests, use the docs.

### Which docs to fetch per step

| Step | Primary doc pages to fetch |
|---|---|
| 1. Agent Basics + YAML Specs | Agents, Agent Specs, Installation |
| 2. Base Prompt + Dependencies | Agents (instructions), Dependencies |
| 3. Domain Agent Composition | Agents (instructions), Agent Specs (`from_spec` merging) |
| 4. Structured Output | Output |
| 5. Function Tools | Function Tools, Advanced Tool Features |
| 6. Capabilities | Capabilities |
| 7. Observability | Logfire integration, Testing |
| 8. Evaluation Pipeline | Pydantic Evals (Quick Start, Core Concepts, Custom Evaluators, Dataset Management) |
| 9. Docker Infrastructure | (no PydanticAI docs needed; Docker/Compose only) |

This protocol is not optional. Training data drifts; official docs are the source of truth.

---

## 4. Project Structure (Final State)

```
pba-agent/
├── prompts/                          # Existing — untouched
│   ├── base-system-prompt.md
│   ├── marketing-agent-prompt.md
│   └── operations-agent-prompt.md
├── specs/                            # YAML Agent Specs
│   ├── base-agent.yaml
│   ├── marketing-agent.yaml
│   └── operations-agent.yaml
├── src/
│   ├── __init__.py
│   ├── deps.py                       # Shared dependency dataclass
│   ├── models.py                     # Pydantic output models
│   ├── base_agent.py                 # Base agent factory (loads spec + prompt)
│   ├── marketing_agent.py            # Marketing domain agent
│   ├── operations_agent.py           # Operations domain agent
│   ├── tools/                        # Function tools by domain
│   │   ├── __init__.py
│   │   ├── marketing_tools.py
│   │   └── operations_tools.py
│   └── capabilities/                 # Custom capabilities
│       ├── __init__.py
│       ├── brand_voice.py
│       └── audit_logger.py
├── evals/                            # Standardized evaluation pipeline
│   ├── datasets/
│   │   ├── base_agent_cases.yaml
│   │   ├── marketing_agent_cases.yaml
│   │   └── operations_agent_cases.yaml
│   ├── evaluators/                   # Custom evaluators (if needed)
│   │   └── __init__.py
│   └── run_evals.py                  # Eval runner script
├── docker/                           # Docker infrastructure
│   ├── Dockerfile                    # Multi-stage build for agent runtime
│   ├── Dockerfile.dev                # Dev image with test/eval tooling
│   └── .dockerignore
├── docker-compose.yaml               # Orchestrates all agent services
├── .env.example                      # Template for required env vars
├── examples/                         # Tutorial scripts (one per step)
│   ├── 01_agent_basics.py
│   ├── 02_base_agent.py
│   ├── 03_domain_agents.py
│   ├── 04_structured_output.py
│   ├── 05_tools.py
│   ├── 06_capabilities.py
│   ├── 07_observability.py
│   ├── 08_evals.py
│   └── 09_docker.py                  # Demonstrates running agents in containers
└── tests/                            # Unit tests using TestModel
    ├── __init__.py
    ├── test_base_agent.py
    ├── test_marketing_agent.py
    └── test_operations_agent.py
```

---

## 5. Learning Path — 9 Steps

### Step 1: Agent Basics + YAML Specs

**Concepts introduced:**
- Installing `pydantic-ai-slim[openai]` with `uv`
- Creating an `Agent` in Python with `instructions` and `model_settings`
- Running an agent with `run_sync()`
- Moving config to a YAML Agent Spec
- Loading a spec with `Agent.from_file()`

**What you learn:**
- `Agent` wraps an LLM — it holds instructions, tools, and config.
- `run_sync()` sends your prompt to the model and blocks until the response arrives. Under the hood it's async; `run_sync` is a convenience wrapper.
- `instructions` shape how the agent behaves on every request (distinct from the user's prompt, which is what you ask).
- A YAML Agent Spec separates config (model, instructions, temperature) from code. `Agent.from_file()` reads the YAML and constructs an `Agent`.
- `model_settings` controls LLM parameters: `temperature` (randomness), `max_tokens` (response length limit).

**Files produced:**
- `specs/hello-agent.yaml` (tutorial-only; superseded by `base-agent.yaml` in Step 2)
- `examples/01_agent_basics.py`

**Success criteria:** Run the script, get a response from OpenAI, verify the instructions change the agent's behavior.

---

### Step 2: Base Prompt + Dependencies

**Concepts introduced:**
- Loading a markdown prompt file from disk as instructions
- Python dataclasses and type hints
- `deps_type` and the dependency injection system
- `RunContext[T]` — accessing deps in dynamic instructions
- `@agent.instructions` decorator for dynamic instructions

**What you learn:**
- `instructions` accepts any string, including your full XML-tagged prompt.
- A dataclass is a Python class that holds data with typed fields. PydanticAI uses a dataclass as the "dependency container" — everything the agent needs at runtime (user context, config, API clients) goes here.
- `deps_type=MyDeps` tells PydanticAI what type to expect (for type checking). `deps=MyDeps(...)` passes the actual instance at runtime.
- `RunContext` is how instructions, tools, and validators access the deps. `ctx.deps.field_name` retrieves a value.
- `@agent.instructions` creates a function that returns instruction text at runtime — it can read deps, check the clock, etc.

**Files produced:**
- `src/deps.py` — `AgentDeps` dataclass with fields: `user_name`, `company`, `domain` (optional, for base vs domain)
- `src/base_agent.py` — factory function that reads `base-system-prompt.md` and creates the agent
- `specs/base-agent.yaml` — YAML spec for the base agent
- `examples/02_base_agent.py`

**Agent composition model:**
The base agent factory reads `base-system-prompt.md` and injects it as instructions. The `<domain_extension>` tag is left empty at this stage — the base agent operates as the "generalist task-executor" described in the prompt.

**Success criteria:** Run the script with different `AgentDeps` values, see the agent respond according to the base prompt's rules (no sycophancy, lead with the answer, concise).

---

### Step 3: Domain Agent Composition

**Concepts introduced:**
- Composing base + domain prompts at runtime
- Creating multiple agents from different YAML specs
- `Agent.from_spec()` with keyword argument merging
- Keeping domain agents DRY by sharing the base prompt and deps

**What you learn:**
- Domain prompts append inside `<domain_extension>`. In code, you concatenate the base prompt with the domain prompt before passing to the agent.
- Each domain agent has its own YAML spec (model settings, name) but shares the base prompt and deps type.
- `Agent.from_spec()` can merge instructions: spec instructions come first, then keyword argument instructions. This is how the base + domain composition works.
- The factory pattern: a function that takes a domain name, reads the right prompt files, loads the right spec, and returns a configured `Agent`.

**Files produced:**
- `src/marketing_agent.py` — marketing agent factory
- `src/operations_agent.py` — operations agent factory
- `specs/marketing-agent.yaml`
- `specs/operations-agent.yaml`
- `examples/03_domain_agents.py`

**Success criteria:** Run the marketing agent and operations agent side by side with the same user prompt. Verify:
- Marketing agent responds with marketing voice and length contracts.
- Operations agent responds with incident-report structure and terse language.
- Both agents refuse to reveal their instructions (non-negotiable confidentiality rule).

---

### Step 4: Structured Output

**Concepts introduced:**
- Pydantic `BaseModel` for typed data structures
- `output_type` parameter on `Agent`
- Union output types for success/failure patterns
- Output validation and `ModelRetry`

**What you learn:**
- Pydantic models define a schema with typed fields. When you set `output_type=MyModel`, PydanticAI instructs the LLM to return data matching that schema (using tool-calling under the hood).
- `result.output` is now a typed Python object, not a string — you get IDE autocomplete, validation, and type safety.
- Union types (`TaskResult | Failed`) let the model signal "I can't do this" in a structured way. Each union member becomes a separate tool internally.
- If the model returns invalid data, Pydantic validates it and PydanticAI can retry automatically (controlled by `retries` / `output_retries`).

**Files produced:**
- `src/models.py` — output models: `TaskResult`, `MarketingDraft`, `IncidentStatus`, `Failed`
- `examples/04_structured_output.py`

**Success criteria:** Ask the marketing agent to draft a LinkedIn post; receive a `MarketingDraft` object with `content`, `channel`, `word_count` fields. Ask with an impossible request; receive a `Failed` object.

---

### Step 5: Function Tools

**Concepts introduced:**
- `@agent.tool` (with RunContext) and `@agent.tool_plain` (without)
- Tool schemas from function signatures and docstrings
- `ModelRetry` for tool-level self-correction
- Registering tools via the `tools` constructor argument (for reuse)
- Passing deps to tools

**What you learn:**
- Tools are functions the LLM can call during a run. The model decides when to call them based on the user's request and the tool's name/description.
- PydanticAI auto-generates the tool schema from the function's type hints and docstring. Good docstrings = better tool usage by the model.
- `@agent.tool` gives the function access to `RunContext` (deps, usage info). `@agent.tool_plain` is for tools that don't need context.
- `ModelRetry` lets a tool say "bad input, try again" — the error message goes back to the model as feedback.
- Tools can also be passed as a list to the `Agent` constructor, which makes them reusable across agents.

**Files produced:**
- `src/tools/__init__.py`
- `src/tools/marketing_tools.py` — stub tools: `search_brand_assets`, `get_content_calendar`, `check_competitor_claims`
- `src/tools/operations_tools.py` — stub tools: `query_monitoring`, `check_deploy_status`, `search_runbooks`
- `examples/05_tools.py`

**Success criteria:** Ask the operations agent "What's the status of the payment service?" — it calls `query_monitoring`, gets stub data back, and synthesizes a response in the incident status format. Ask the marketing agent to draft a blog post — it calls `get_content_calendar` to check timing.

---

### Step 6: Capabilities

**Concepts introduced:**
- `AbstractCapability` — the base class for custom capabilities
- Capabilities bundle: tools (via toolsets), lifecycle hooks, instructions, model settings
- Built-in capabilities: `Thinking`, `WebSearch`, `Hooks`
- Lifecycle hooks: `before_model_request`, `after_tool_call`, etc.
- Capabilities in YAML specs
- `PrefixTools` for namespacing

**What you learn:**
- A Capability is a reusable, composable unit of agent behavior. Instead of threading multiple arguments through the Agent constructor, you bundle related behavior into one object.
- Built-in capabilities like `Thinking(effort='high')` and `WebSearch()` add powerful features with one line.
- Custom capabilities let you build cross-cutting concerns: an `AuditLogger` that logs every tool call, a `BrandVoiceGuardrail` that validates outputs against style rules.
- Capabilities compose: an agent can have multiple capabilities, and they all contribute their tools, hooks, and instructions.
- Capabilities can be referenced in YAML specs, making them configurable without code changes.

**Files produced:**
- `src/capabilities/__init__.py`
- `src/capabilities/audit_logger.py` — logs every model request and tool call (cross-cutting)
- `src/capabilities/brand_voice.py` — validates outputs against brand voice rules (marketing-specific)
- Updated YAML specs with `capabilities:` sections
- `examples/06_capabilities.py`

**Success criteria:** Run the marketing agent with `AuditLogger` and `BrandVoiceGuardrail` capabilities. Verify the audit log captures tool calls and model requests. Verify the brand voice guardrail flags forbidden phrasings from the marketing prompt.

---

### Step 7: Observability

**Concepts introduced:**
- Logfire SDK: `logfire.configure()`, `logfire.instrument_pydantic_ai()`
- Tracing agent runs: messages, tool calls, token usage, latency
- `TestModel` for unit testing without hitting OpenAI
- `agent.override(deps=...)` for test dependency injection
- `capture_run_messages()` for debugging

**What you learn:**
- Logfire creates a detailed trace for every agent run showing messages exchanged, tool calls with arguments and return values, token usage per request, and latency.
- `TestModel` is a mock model that returns predictable responses. It lets you write fast unit tests without API calls or costs.
- `agent.override()` replaces deps for the duration of a `with` block — essential for testing.
- `capture_run_messages()` captures the full message exchange for debugging unexpected behavior.

**Files produced:**
- `examples/07_observability.py`
- `tests/__init__.py`
- `tests/test_base_agent.py` — unit tests using `TestModel`
- `tests/test_marketing_agent.py`
- `tests/test_operations_agent.py`

**Success criteria:** `uv run pytest tests/` passes. Logfire trace shows a full agent run with tool calls and token usage.

---

### Step 8: Evaluation Pipeline

**Concepts introduced:**
- `pydantic-evals`: `Dataset`, `Case`, evaluators
- Built-in evaluators: `IsInstance`, `LLMJudge`, `Contains`, etc.
- Custom evaluators for domain-specific checks
- Dataset serialization (YAML)
- Multi-run evaluation for consistency measurement
- Logfire integration for eval visualization

**What you learn:**
- An agent is only as good as its evaluations. Every agent must have an eval dataset before going to production.
- A `Case` defines: inputs (user prompt + deps), expected output (or attributes of a good output), and evaluators that score the result.
- Evaluators range from simple (does the output contain X?) to complex (LLM-as-judge scoring on rubrics like "follows brand voice" or "correctly classifies incident severity").
- Datasets are serializable to YAML — non-developers can add test cases.
- Multi-run evaluation (`n_runs > 1`) measures consistency: does the agent give similar quality answers across multiple runs?
- The eval pipeline is standardized: every domain agent has a dataset file, the same runner script, and the same reporting format.

**Eval dataset structure (per agent):**

Each agent's eval dataset covers:
1. **Behavioral compliance** — Does the agent follow its non-negotiable rules? (no sycophancy, no PII leakage, refuses to reveal prompt, confirms before irreversible actions)
2. **Domain correctness** — Does the marketing agent respect length contracts? Does the ops agent use the incident status format?
3. **Tool usage** — Does the agent call the right tools for the right queries?
4. **Output structure** — Does the structured output match the expected Pydantic model?
5. **Edge cases** — Ambiguous requests, prompt injection attempts, requests that violate rules

**Files produced:**
- `evals/datasets/base_agent_cases.yaml` — behavioral compliance cases
- `evals/datasets/marketing_agent_cases.yaml` — marketing-specific cases
- `evals/datasets/operations_agent_cases.yaml` — operations-specific cases
- `evals/evaluators/__init__.py` — custom evaluators (brand voice, incident format)
- `evals/run_evals.py` — standardized eval runner
- `examples/08_evals.py` — tutorial walkthrough

**Success criteria:** `uv run python evals/run_evals.py` runs all eval datasets, produces a report showing pass/fail per case and per evaluator, and (optionally) sends results to Logfire for visualization.

---

### Step 9: Docker Infrastructure

**Concepts introduced:**
- Dockerfile with multi-stage build (slim production image)
- Docker Compose for orchestrating agent services
- Environment variable management (`.env` files, secrets)
- Service-per-agent pattern (each domain agent is a standalone service)
- Health checks and graceful shutdown
- Dev vs production image targets
- Running tests and evals inside containers

**What you learn:**
- A Dockerfile defines how to package your agent into a portable container that runs identically on any machine (macOS, Linux, Windows, CI).
- Multi-stage builds keep production images small: a "build" stage installs dependencies with `uv`, a "runtime" stage copies only what's needed.
- Docker Compose defines multiple services in one file. Each domain agent runs as its own service, with shared configuration (env vars, volumes) defined once.
- Environment variables (especially `OPENAI_API_KEY`) are passed via `.env` files — never baked into the image.
- Health checks let the orchestrator know if an agent service is alive and ready.

**Docker Compose services:**

| Service | Image | Purpose |
|---|---|---|
| `base-agent` | `pba-agent:latest` | Base agent (generalist) — entrypoint runs `base_agent.py` |
| `marketing-agent` | `pba-agent:latest` | Marketing domain agent — same image, different entrypoint/config |
| `operations-agent` | `pba-agent:latest` | Operations domain agent — same image, different entrypoint/config |
| `eval-runner` | `pba-agent:dev` | Runs the eval pipeline (includes test/eval deps) |
| `logfire` | (optional) | Logfire collector if self-hosting; otherwise agents send to Logfire cloud |

All agent services use the **same Docker image** (built once) with different entrypoints and YAML spec paths passed via environment variables. This keeps the image count to one and avoids duplication.

**Dockerfile strategy:**

```
Stage 1: "build"
  - FROM python:3.12-slim
  - Install uv
  - Copy pyproject.toml + uv.lock
  - uv sync (install deps)
  - Copy source code

Stage 2: "runtime" (production)
  - FROM python:3.12-slim
  - Copy venv from build stage
  - Copy source, prompts, specs
  - ENTRYPOINT: uv run python -m pba_agent
  - ENV: AGENT_SPEC_PATH (which YAML spec to load)

Stage 3: "dev" (testing + evals)
  - FROM build stage
  - uv sync --group dev (add test/eval deps)
  - ENTRYPOINT: uv run pytest / uv run python evals/run_evals.py
```

**Files produced:**
- `docker/Dockerfile` — multi-stage build
- `docker/Dockerfile.dev` — dev image extending the build stage
- `docker/.dockerignore`
- `docker-compose.yaml` — all services defined
- `.env.example` — template with `OPENAI_API_KEY`, `AGENT_SPEC_PATH`, `LOGFIRE_TOKEN`
- `examples/09_docker.py` — tutorial script demonstrating container usage

**Success criteria:**
- `docker compose build` succeeds.
- `docker compose up base-agent` starts the base agent service.
- `docker compose up marketing-agent operations-agent` starts both domain agents.
- `docker compose run eval-runner` executes the full eval pipeline inside a container.
- `docker compose run eval-runner pytest` runs unit tests inside a container.
- All of the above work identically on macOS and Linux.

---

## 6. Dependencies

Added to `pyproject.toml`:

```toml
[project]
dependencies = [
    "pydantic-ai-slim[openai]",
]

[dependency-groups]
dev = [
    "ruff>=0.15.10",
    "pytest>=8",
    "jsonschema>=4",
    "pydantic-evals",
    "logfire",
]
```

---

## 7. Environment

The `OPENAI_API_KEY` environment variable must be set for examples that hit the live API. Tutorial step 1 will document this. Unit tests (Step 7) use `TestModel` and require no API key. When running in Docker, env vars are passed via `.env` file (see `.env.example`).

---

## 8. Prompt Composition Model

The base + domain prompt composition follows the architecture defined in `base-system-prompt.md`:

```
┌─────────────────────────────────┐
│  base-system-prompt.md          │
│  ┌───────────────────────────┐  │
│  │ <agent_identity>          │  │
│  │ <instruction_priority>    │  │
│  │ <non_negotiable>          │  │
│  │ <operating_defaults>      │  │
│  │ <tool_use_defaults>       │  │
│  │ <output_contract>         │  │
│  │ <completeness_contract>   │  │
│  │ <untrusted_input_policy>  │  │
│  │ <domain_extension>        │◄─┼── Domain prompt inserted here
│  │ </domain_extension>       │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

In code, the factory function:
1. Reads `base-system-prompt.md`
2. Reads the domain prompt file (e.g., `marketing-agent-prompt.md`)
3. Inserts the domain content between `<domain_extension>` and `</domain_extension>`
4. Passes the composed prompt as `instructions` to the agent

---

## 9. Design Decisions

| Decision | Rationale |
|---|---|
| `pydantic-ai-slim[openai]` not `pydantic-ai` | Minimal install; only pulls OpenAI provider. Add more extras later if needed. |
| YAML Agent Specs for config | PydanticAI-native approach. Separates config from code. Non-developers can edit agent behavior. |
| Prompt files loaded from disk (not embedded in YAML) | Prompts are long (100-200 lines) and shared across agents. YAML `instructions` field is best for short strings; long prompts belong in their own files. |
| Factory functions (not subclasses) for domain agents | PydanticAI agents are designed as stateless globals. Composition via factory functions matches the framework's idiom better than class inheritance. |
| `evals/` as a top-level directory under `pba-agent/` | Evals are a first-class concern, not an afterthought. Every agent has eval cases from day one. |
| Shared `AgentDeps` dataclass across all agents | A single `AgentDeps` dataclass with an optional `domain` field serves all agents. If domains later need divergent deps, they subclass `AgentDeps` — PydanticAI's `deps_type` supports this since `RunContext[AgentDeps]` accepts subclasses. Start simple; split only when forced. |
| Stub tool implementations in Step 5 | Real API integrations are out of scope for the learning path. Stubs demonstrate the tool pattern; real implementations are swapped in later. |
| Capabilities introduced after tools | You need to understand individual tools before you can appreciate bundling them into capabilities. |
| MCP docs-first protocol before each step | PydanticAI is actively developed; training data drifts. Fetching `llms.txt` before coding ensures the latest API surface is used. |
| Single Docker image, multiple entrypoints | All domain agents share the same codebase and dependencies. Different YAML spec paths select the domain at runtime. Avoids image sprawl. |
| Docker Compose for orchestration | Simple, file-based, no Kubernetes overhead for dev/staging. Production can graduate to K8s later using the same images. |
| `python:3.12-slim` as base image | Balances image size with compatibility. 3.12 is the latest stable Python and matches PydanticAI's recommended version. |
| Eval runner as a Docker service | Evals should run in the same environment as production agents. A dedicated service ensures eval deps don't bloat the production image. |
