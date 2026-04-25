"""Observability configuration for PBA agents.

Configures Logfire SDK to export OpenTelemetry traces to a local Jaeger
instance (default) or Logfire cloud when LOGFIRE_TOKEN is set.
"""

from __future__ import annotations

import os

import logfire


def configure_tracing(service_name: str = "pba-agent") -> None:
    """Set up Logfire + OTel tracing.

    Reads OTEL_EXPORTER_OTLP_ENDPOINT from the environment
    (default: http://localhost:4318 for local Jaeger).
    Set LOGFIRE_TOKEN to also send to Logfire cloud.
    """
    os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    send_to_logfire = bool(os.environ.get("LOGFIRE_TOKEN"))
    logfire.configure(service_name=service_name, send_to_logfire=send_to_logfire)
    logfire.instrument_pydantic_ai()
