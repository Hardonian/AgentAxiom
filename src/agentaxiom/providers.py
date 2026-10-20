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


class GeminiVertexClient:
    def __init__(self, *, model: str, project: str | None = None, location: str = "us-central1", generation: dict[str, Any] | None = None, tools: list[Any] | None = None):
        try:
            from google import genai
        except ImportError as exc:
            raise ImportError("Install AgentAxiom's Vertex extra: pip install -e '.[vertex]'") from exc
        self._client = genai.Client(vertexai=bool(project), project=project, location=location) if project else genai.Client()
        self.model, self.location = model, location
        self.generation, self.tools = generation or {}, tools or []

    def invoke(self, scenario: Scenario) -> Invocation:
        # Gemini's contents accept the normal chat turns as dicts.
        contents = [{"role": "model" if turn.role == "assistant" else turn.role, "parts": [{"text": turn.content or ""}]} for turn in scenario.turns if turn.role in {"user", "model", "assistant"}]
        started = time.perf_counter()
        response = self._client.models.generate_content(model=self.model, contents=contents, config={"temperature": self.generation.get("temperature"), "max_output_tokens": self.generation.get("max_output_tokens"), "response_mime_type": self.generation.get("response_mime_type"), "tools": self.tools or None})
        raw = response.model_dump(exclude_none=True) if hasattr(response, "model_dump") else {"text": getattr(response, "text", None)}
        usage = raw.get("usage_metadata", {})
        candidates = raw.get("candidates", [])
        grounding = candidates[0].get("grounding_metadata", {}) if candidates else {}
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        tool_calls = [{"name": part["function_call"].get("name"), "arguments": part["function_call"].get("args", {})} for part in parts if "function_call" in part]
        response_text = getattr(response, "text", None)
        try:
            structured = json.loads(response_text) if response_text and self.generation.get("response_mime_type") == "application/json" else None
        except json.JSONDecodeError:
            structured = None
        return Invocation(model=self.model, region=self.location, provider="vertex-ai" if self.location else "gemini-api", generation=self.generation, tools=[tool if isinstance(tool, dict) else {"definition": str(tool)} for tool in self.tools], response_text=response_text, structured_output=structured, tool_calls=tool_calls, citations=grounding.get("grounding_chunks", []), safety={"ratings": candidates[0].get("safety_ratings", []) if candidates else []}, token_usage={"input": usage.get("prompt_token_count", 0), "output": usage.get("candidates_token_count", 0), "total": usage.get("total_token_count", 0)}, latency_ms=round((time.perf_counter() - started) * 1000, 2), raw_response=raw)
