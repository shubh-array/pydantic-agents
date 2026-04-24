"""Cross-cutting audit logger capability.

Logs every model request and tool execution during an agent run.
Attach to any agent via ``capabilities=[AuditLogger()]``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import ModelRequestContext, RunContext, ToolDefinition
from pydantic_ai.capabilities import (
    AbstractCapability,
    WrapModelRequestHandler,
    WrapToolExecuteHandler,
)
from pydantic_ai.messages import ModelResponse, ToolCallPart


@dataclass
class AuditEntry:
    """A single audit log entry."""

    event: str
    agent_name: str
    detail: str
    elapsed_ms: float


@dataclass
class AuditLogger(AbstractCapability[Any]):
    """Logs model requests and tool calls to an in-memory audit trail.

    Access ``audit_logger.log`` after a run to inspect events.
    """

    log: list[AuditEntry] = field(default_factory=list)

    async def wrap_model_request(
        self,
        ctx: RunContext[Any],
        *,
        request_context: ModelRequestContext,
        handler: WrapModelRequestHandler,
    ) -> ModelResponse:
        agent_name = ctx.agent.name if ctx.agent else "unknown"
        n_messages = len(request_context.messages)
        start = time.perf_counter()
        response = await handler(request_context)
        elapsed_ms = (time.perf_counter() - start) * 1000

        entry = AuditEntry(
            event="model_request",
            agent_name=agent_name,
            detail=f"step={ctx.run_step}, messages={n_messages}, response_parts={len(response.parts)}",
            elapsed_ms=round(elapsed_ms, 1),
        )
        self.log.append(entry)
        print(
            f"  [audit] {entry.event} | {entry.agent_name} | {entry.detail} | {entry.elapsed_ms}ms"
        )
        return response

    async def wrap_tool_execute(
        self,
        ctx: RunContext[Any],
        *,
        call: ToolCallPart,
        tool_def: ToolDefinition,
        args: dict[str, Any],
        handler: WrapToolExecuteHandler,
    ) -> Any:
        agent_name = ctx.agent.name if ctx.agent else "unknown"
        start = time.perf_counter()
        result = await handler(args)
        elapsed_ms = (time.perf_counter() - start) * 1000

        entry = AuditEntry(
            event="tool_execute",
            agent_name=agent_name,
            detail=f"tool={call.tool_name}, args={args}",
            elapsed_ms=round(elapsed_ms, 1),
        )
        self.log.append(entry)
        print(
            f"  [audit] {entry.event} | {entry.agent_name} | tool={call.tool_name} | {entry.elapsed_ms}ms"
        )
        return result
