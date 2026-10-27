"""One-call, explicitly enabled Gemini Developer API smoke test.

Run only against an explicitly provided key or environment:
  AGENTAXIOM_LIVE_SMOKE=1 GEMINI_API_KEY=AIza... python scripts/live_gemini_smoke.py
"""
from __future__ import annotations

import os

from agentaxiom.models import Scenario, Turn
from agentaxiom.providers import GeminiVertexClient, RetryPolicy

if os.environ.get("AGENTAXIOM_LIVE_SMOKE") != "1":
    raise SystemExit("Refusing live call: set AGENTAXIOM_LIVE_SMOKE=1 explicitly.")

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise SystemExit("Refusing live call: set GEMINI_API_KEY explicitly.")

client = GeminiVertexClient(
    model="gemini-2.5-flash",
    project=None,
    location="us-central1",
    generation={
        "temperature": 0,
        "max_output_tokens": 32,
        "response_mime_type": "application/json",
        "thinking_config": {"thinking_budget": 0},
    },
    retry_policy=RetryPolicy(max_attempts=3, initial_backoff_s=0.5),
)

invocation = client.invoke(Scenario("gemini-smoke", [Turn("user", 'Return only JSON: {"ok": true}')]))
if invocation.structured_output != {"ok": True}:
    raise SystemExit(
        "Live smoke did not receive the expected structured output; "
        f"usage={invocation.token_usage}, safety={invocation.safety}"
    )

print(
    {
        "provider": invocation.provider,
        "model": invocation.model,
        "structured_output": invocation.structured_output,
        "token_usage": invocation.token_usage,
        "latency_ms": invocation.latency_ms,
    }
)

