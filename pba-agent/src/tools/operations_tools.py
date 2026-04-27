"""Operations domain tools (stub implementations).

Each function is a tool available to the operations agent.
PydanticAI builds the tool schema from the signature + Google-style docstring.
Real implementations would call monitoring APIs; stubs return plausible fake data.
"""

from __future__ import annotations

from pydantic_ai import ModelRetry, RunContext

from deps import AgentDeps


def query_monitoring(ctx: RunContext[AgentDeps], service_name: str) -> str:
    """Query the monitoring system for current metrics of a service.

    Args:
        service_name: Name of the service to query, e.g. 'payment-service'.
    """
    return (
        f"[monitoring] {service_name} (company: {ctx.deps.company}):\n"
        "  error_rate: 15.2%  (threshold: 1%)\n"
        "  p99_latency: 4200ms  (threshold: 500ms)\n"
        "  requests_per_sec: 1240\n"
        "  healthy_instances: 3/5\n"
        "  last_deploy: 12 min ago (v2.14.1)\n"
        "  alerts: FIRING — high error rate, latency spike"
    )


def check_deploy_status(service_name: str) -> str:
    """Check the most recent deployment status for a service.

    Args:
        service_name: Name of the service to check.
    """
    return (
        f"[deploy-status] {service_name}:\n"
        "  version: v2.14.1\n"
        "  deployed_at: 12 min ago by deploy-bot\n"
        "  change: Migrated payment DB connection pool from sync to async\n"
        "  rollback_available: yes (v2.14.0)\n"
        "  canary: not used (full rollout)"
    )


def search_runbooks(query: str) -> str:
    """Search the runbook library for incident-response procedures.

    Args:
        query: Natural-language description of the issue or procedure needed.
    """
    known_queries = {
        "high error rate",
        "latency spike",
        "payment",
        "503",
        "rollback",
        "database",
        "connection pool",
    }
    matched = [kw for kw in known_queries if kw in query.lower()]
    if not matched:
        raise ModelRetry(
            f"No runbooks matched '{query}'. "
            "Try more specific terms like 'high error rate', 'rollback', or 'connection pool'."
        )
    return (
        f"[runbooks] Results for '{query}':\n"
        "1. RB-042: Payment Service High Error Rate\n"
        "   → Verify DB connection pool health, check for recent deploys, "
        "consider rollback if error rate > 10%\n"
        "2. RB-019: Emergency Rollback Procedure\n"
        "   → Run: deploy rollback <service> --to <prev-version>"
    )
