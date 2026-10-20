"""Optional Gemini/Vertex recording adapters.

The adapter intentionally converts provider responses to AgentAxiom's stable
evidence format at the boundary.  It does not execute tools: callers own tool
execution and can append the resulting calls to the recorded Invocation.
"""

from __future__ import annotations

import json
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .models import Invocation, Scenario
from .pricing import PricingCatalog

_RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


class ProviderError(RuntimeError):
    """Normalized provider failure with a stable, provider-agnostic shape.

    ``kind`` is one of ``timeout``, ``network``, ``rate_limited``,
    ``invalid_request``, ``permission``, ``not_found``, ``server``,
    ``client``, or ``unknown``.  Unknown errors are never retried: callers
    fail closed instead of guessing.
    """

    def __init__(
        self,
        *,
        kind: str,
        message: str,
        retryable: bool,
        status: int | None = None,
        provider_code: str | None = None,
        request_id: str | None = None,
        attempts: int = 1,
    ):
        super().__init__(message)
        self.kind = kind
        self.retryable = retryable
        self.status = status
        self.provider_code = provider_code
        self.request_id = request_id
        self.attempts = attempts

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "message": str(self),
            "retryable": self.retryable,
            "status": self.status,
            "provider_code": self.provider_code,
            "request_id": self.request_id,
            "attempts": self.attempts,
        }


def classify_provider_error(exc: BaseException, *, attempts: int = 1) -> ProviderError:
    """Maps any SDK/network exception to a ProviderError without importing the SDK."""
    if isinstance(exc, ProviderError):
        exc.attempts = attempts
        return exc
    status = getattr(exc, "code", None)
    if not isinstance(status, int):
        status = None
    provider_code = getattr(exc, "status", None)
    provider_code = provider_code if isinstance(provider_code, str) else None
    request_id = getattr(exc, "request_id", None)
    request_id = request_id if isinstance(request_id, str) else None
    message = str(exc) or type(exc).__name__

    def build(kind: str, retryable: bool) -> ProviderError:
        return ProviderError(
            kind=kind,
            message=message,
            retryable=retryable,
            status=status,
            provider_code=provider_code,
            request_id=request_id,
            attempts=attempts,
        )

    if isinstance(exc, TimeoutError) or "timeout" in type(exc).__name__.lower():
        return build("timeout", True)
    if isinstance(exc, ConnectionError) or "connection" in type(exc).__name__.lower():
        return build("network", True)
    if status is not None:
        if status == 429:
            return build("rate_limited", True)
        if status == 408:
            return build("timeout", True)
        if status in _RETRYABLE_STATUS:
            return build("server", True)
        if status == 400:
            return build("invalid_request", False)
        if status in {401, 403}:
            return build("permission", False)
        if status == 404:
            return build("not_found", False)
        if 400 <= status < 500:
            return build("client", False)
        return build("server", True)
    name = type(exc).__name__.lower()
    if "servererror" in name:
        return build("server", True)
    return build("unknown", False)


@dataclass
class RetryPolicy:
    """Bounded exponential backoff with jitter; conservative defaults."""

    max_attempts: int = 4
    initial_backoff_s: float = 0.5
    max_backoff_s: float = 8.0
    jitter: float = 0.25

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.initial_backoff_s <= 0 or self.max_backoff_s <= 0:
            raise ValueError("backoff durations must be positive")
        if not 0 <= self.jitter < 1:
            raise ValueError("jitter must be in [0, 1)")

    def backoff_for(self, attempt: int, *, rand: Callable[[], float] = random.random) -> float:
        base = min(self.initial_backoff_s * (2 ** (attempt - 1)), self.max_backoff_s)
        return base * (1 - self.jitter + 2 * self.jitter * rand())


def call_with_retry(
    call: Callable[[], Any],
    *,
    policy: RetryPolicy | None = None,
    on_retry: Callable[[ProviderError, float], None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    """Runs ``call`` under ``policy``, normalizing all failures to ProviderError."""
    policy = policy or RetryPolicy()
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return call()
        except Exception as exc:
            error = classify_provider_error(exc, attempts=attempt)
            if not error.retryable or attempt == policy.max_attempts:
                raise error from exc
            delay = policy.backoff_for(attempt)
            if on_retry is not None:
                on_retry(error, delay)
            sleep(delay)
    raise AssertionError("unreachable")  # pragma: no cover


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
        timeout_s: float | None = None,
        retry_policy: RetryPolicy | None = None,
    ):
        try:
            from google import genai
        except ImportError as exc:
            raise ImportError("Install AgentAxiom's Vertex extra: pip install -e '.[vertex]'") from exc
        if timeout_s is not None and timeout_s <= 0:
            raise ValueError("timeout_s must be positive")
        http_options = {"timeout": timeout_s} if timeout_s is not None else None
        self._client = (
            genai.Client(vertexai=bool(project), project=project, location=location, http_options=http_options)
            if project
            else genai.Client(http_options=http_options)
        )
        self.model, self.location, self.project = model, location, project
        self.generation, self.tools = generation or {}, tools or []
        self.pricing = pricing or PricingCatalog()
        self.timeout_s = timeout_s
        self.retry_policy = retry_policy or RetryPolicy()

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
        response = call_with_retry(
            lambda: self._client.models.generate_content(model=self.model, contents=contents, config=config),
            policy=self.retry_policy,
        )
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
