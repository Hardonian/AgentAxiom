"""Optional Gemini/Vertex recording adapters.

The adapter intentionally converts provider responses to AgentAxiom's stable
evidence format at the boundary.  It does not execute tools: callers own tool
execution and can append the resulting calls to the recorded Invocation.
"""

from __future__ import annotations

import json
import time
from typing import Any

from .models import Invocation, Scenario
from .pricing import PricingCatalog


class GeminiVertexClient:
    def __init__(
        self,
        *,
        model: str,
        project: str | None = None,
        location: str = "us-central1",
        generation: dict[str, Any] | None = None,
        tools: list[Any] | None = None,
        pricing: PricingCatalog | None = None,
    ):
        try:
            from google import genai
        except ImportError as exc:
            raise ImportError("Install AgentAxiom's Vertex extra: pip install -e '.[vertex]'") from exc
        self._client = (
            genai.Client(vertexai=bool(project), project=project, location=location) if project else genai.Client()
        )
        self.model, self.location, self.project = model, location, project
        self.generation, self.tools = generation or {}, tools or []
        self.pricing = pricing or PricingCatalog()

    def invoke(self, scenario: Scenario) -> Invocation:
        # Gemini's contents accept the normal chat turns as dicts.
        contents = [
            {"role": "model" if turn.role == "assistant" else turn.role, "parts": [{"text": turn.content or ""}]}
            for turn in scenario.turns
            if turn.role in {"user", "model", "assistant"}
        ]
        started = time.perf_counter()
        config = {key: value for key, value in self.generation.items() if value is not None}
        if self.tools:
            config["tools"] = self.tools
        response = self._client.models.generate_content(model=self.model, contents=contents, config=config)
        raw = (
            response.model_dump(exclude_none=True)
            if hasattr(response, "model_dump")
            else {"text": getattr(response, "text", None)}
        )
        usage = raw.get("usage_metadata", {})
        candidates = raw.get("candidates", [])
        grounding = candidates[0].get("grounding_metadata", {}) if candidates else {}
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        tool_calls = [
            {"name": part["function_call"].get("name"), "arguments": part["function_call"].get("args", {})}
            for part in parts
            if "function_call" in part
        ]
        response_text = getattr(response, "text", None)
        if not response_text:
            response_text = "\n".join(str(part["text"]) for part in parts if part.get("text")) or None
        try:
            structured = (
                json.loads(response_text)
                if response_text and self.generation.get("response_mime_type") == "application/json"
                else None
            )
        except json.JSONDecodeError:
            structured = None
        token_usage = {
            "input": usage.get("prompt_token_count", 0),
            "output": usage.get("candidates_token_count", 0),
            "total": usage.get("total_token_count", 0),
        }
        return Invocation(
            model=self.model,
            region=self.location,
            provider="vertex-ai" if self.project else "gemini-api",
            generation=self.generation,
            tools=[tool if isinstance(tool, dict) else {"definition": str(tool)} for tool in self.tools],
            response_text=response_text,
            structured_output=structured,
            tool_calls=tool_calls,
            citations=grounding.get("grounding_chunks", []),
            safety={"ratings": candidates[0].get("safety_ratings", []) if candidates else []},
            token_usage=token_usage,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            estimated_cost_usd=self.pricing.estimate(self.model, token_usage),
            raw_response=raw,
        )


class ADKRecorder:
    """Normalizes ADK event dictionaries without coupling core evidence to an ADK release."""

    def __init__(self, *, model: str, region: str, adk_version: str):
        self.model = model
        self.region = region
        self.adk_version = adk_version

    def record(self, scenario: Scenario, events: list[dict[str, Any]]) -> Invocation:
        """Record normalized ADK events emitted by the calling agent integration.

        Event dictionaries may contain `text`, `function_call`, `grounding`,
        `safety`, `usage`, `latency_ms`, `request_id`, and `trace_id` keys.
        The calling integration retains ownership of live execution.
        """
        text = "\n".join(str(event["text"]) for event in events if event.get("text")) or None
        tool_calls = [event["function_call"] for event in events if event.get("function_call")]
        citations = [citation for event in events for citation in event.get("grounding", [])]
        usage: dict[str, int] = {}
        for event in events:
            usage.update(event.get("usage", {}))
        last = events[-1] if events else {}
        return Invocation(
            model=self.model,
            region=self.region,
            provider="adk",
            adk_version=self.adk_version,
            response_text=text,
            tool_calls=tool_calls,
            citations=citations,
            safety=last.get("safety", {}),
            token_usage=usage,
            latency_ms=float(last.get("latency_ms", 0)),
            raw_response={"event_count": len(events)},
            request_id=last.get("request_id"),
            trace_id=last.get("trace_id"),
        )
