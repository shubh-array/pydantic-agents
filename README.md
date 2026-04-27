# pydantic-agents POC

The goal of this POC is to explore how the existing coding agentic infrastructure within Array (PBA) can be leveraged to build a foundational agent development framework for building new PBA customer facing agents and review existing PBA agents in a reliable, deterministic, governed and secure fashion. 


## Existing Array Infra

The current infrastructure consists of Cursor coding agents (local - CLI, IDE and remote - Cloud agents) for agent code development, and the agents themseleves are built using Pydantic AI SDK libraries in python and are deployed in Azure containers.

## Research Questions

### Cursor Agent
- Is cursor agent mature enough for scalable agentic development both locally and remote?
- Does cursor support capabilities like hooks, mcps, skills, plugins that can enable building and distributing generic coding agent components that can be shared across the engineering team?
- Does cursor hook framework sufficient lifecycle events which can hooked into for auditing and gating requirements for long-running coding sessions?
- Does cursor support chaining hooks?
- Does cursor hooks emit detailed event objects that can capture tool call info, blocking tool calls, detecting prompt injection, shell commands i/o, prompt compaction, token usage, etc. that can provide a holistic picture of an agent coding session to analyze, extract insights and troubleshoot the coding session themselves?
- Is cursor metadata file system comprehensive enough to isolate and analyze cross session activities?
- What are the discrepancies between cursor cli and cursor ide agents?
- Does cursor administration support creating a private plugin marketplace such that agent components (skills, prompts, mcps, etc.) can be shared across the engineering team?


### Infra

- Which evaluation platform gives the most value for money? Logfire, Braintrust, Azure App Insights/Foundry?

### Pydantic AI

- Does Pydantic AI SDK library expose low-level features such that we can build task-specific agent harness vs general purpose agent harness?
- What models does it support?
- Does the SDK support sandboxing tool execution and network policies?
- Does the Pydantic ecosystem support evals for evaluating agent skills, prompts?
- Does the Pydantic ecosystem support observability frameworks for tracking and debugging agent trajectories?
- Does Pydantic have native support for orchestrating agents especially long-running agents?


### Agentic Product Development

- Can we build a meta agent skill `create-agent-skill` which can be used to create new agent skills with end-to-end evaluation pipeline (measure quantitaive, qualitative metrics) with LLM-as-a-jduge and evaluation-optimizer loops to improve skill body and description?
- Can the meta agent skill `create-agent-skill` be coding agent agnostic such that it is compatible with multiple coding agents like cursor, claude code and more?
- Can we use `create-agent-skill` to create the following agent skills:
  1. **create-pba-agent**: Streamline a deterministic approach to creating new PBA agents and reviewing existing agents?
  2. **pba-product-voice**: Agent skill that can embed Array Product voice and review & evaluate existing agents for product voice conformity,
- Can `pba-product-voice` be converted to a system prompt and maintain the same quality?


## Todo

**1. Cursor Hook Framework**
- Create and chain hooks for multiple lifecycle events
- Block dangerous commands
- Generate audit logs with info - shell commands, prompt injection attacks, token usage, etc.
- Dashboard to view the audit log


**2. Meta Agent Skill - create-agent-skill**
- Adapter based harness and compatible with coding agents like cursor (default) and claude code.
- Isolate core business logic for creating and evaluating agent skill and agent specific config.
- Evaluation pipeline for improving agent skill content and trigger description

**3. PBA Agent with a default system prompt**
- Design a standardized System prompt with distinct sections (separated by XML tags)

**4. Agent Skill - create-pba-agent**
- Agent Skill to create a standardized & governed PBA agent for product





##PBA Agent Fleet — Phase 1 Implementation Summary

### What's Implemented

- Voice source-of-truth: structured YAML spec (8 rules + HR domain definition) drives all prompts
- Deterministic prompt renderer: YAML → markdown, byte-identical re-renders
- Skill authoring system: customer-facing skills under pba-agent/skills/<category>/<id>/SKILL.md, inlined into prompts at render time
- First skill: skill-ai-disclosure-external (legal AI-disclosure rule for SMS/email), authored + evaluated end-to-end via - create-agent-skill harness, gated by promotion thresholds (100% candidate vs 69% baseline)
- HR agent: live, answers HR questions on-voice
- Eval pipeline: voice rules tested via LLMJudge rubrics on the HR agent (8 cases) + minimal HR domain dataset (2 cases), both wired into run_evals.py
- Live verification: HR 100%, Voice 96% pass rate (one real never-fabricate regression surfaced — Phase 2 work)

Navigation — Step-by-Step

Step 1 — Prompt markers