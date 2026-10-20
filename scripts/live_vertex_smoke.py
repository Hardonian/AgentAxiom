"""One-call, explicitly enabled Vertex adapter smoke test.

Run only against an explicitly selected project:
  AGENTAXIOM_LIVE_SMOKE=1 GOOGLE_CLOUD_PROJECT=PROJECT python scripts/live_vertex_smoke.py
"""
from __future__ import annotations

import os

from agentaxiom.models import Scenario, Turn
from agentaxiom.providers import GeminiVertexClient

if os.environ.get("AGENTAXIOM_LIVE_SMOKE") != "1":
    raise SystemExit("Refusing live call: set AGENTAXIOM_LIVE_SMOKE=1 explicitly.")

project = os.environ.get("GOOGLE_CLOUD_PROJECT")
if not project:
    raise SystemExit("Refusing live call: set GOOGLE_CLOUD_PROJECT explicitly.")
region = os.environ.get("AGENTAXIOM_VERTEX_REGION", "us-central1")
client = GeminiVertexClient(
    model="gemini-2.5-flash",
    project=project,
    location=region,
    generation={
        "temperature": 0,
        "max_output_tokens": 32,
        "response_mime_type": "application/json",
        "thinking_config": {"thinking_budget": 0},
    },
)
invocation = client.invoke(Scenario("live-smoke", [Turn("user", 'Return only JSON: {"ok": true}')]))
if invocation.structured_output != {"ok": True}:
    raise SystemExit(
        "Live smoke did not receive the expected structured output; "
        f"usage={invocation.token_usage}, safety={invocation.safety}"
    )
print(
    {
        "provider": invocation.provider,
        "model": invocation.model,
        "region": invocation.region,
        "structured_output": invocation.structured_output,
        "token_usage": invocation.token_usage,
        "latency_ms": invocation.latency_ms,
    }
)
