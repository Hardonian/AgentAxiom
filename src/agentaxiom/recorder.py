"""Drop-in SDK recording for Google GenAI / Vertex AI clients."""

from __future__ import annotations

import json
import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from .models import Invocation, Scenario, Transcript, Turn
from .pricing import PricingCatalog


class GeminiRecording:
    """Holds captured AgentAxiom transcripts from intercepted SDK operations."""

    def __init__(self, scenario_name: str = "recorded-scenario", metadata: dict[str, Any] | None = None):
        self.scenario_name = scenario_name
        self.metadata = metadata or {}
        self.transcripts: list[Transcript] = []

    @property
    def transcript(self) -> Transcript:
        if not self.transcripts:
            raise RuntimeError("No Gemini calls were recorded during this session.")
        return self.transcripts[-1]


def parse_turns_from_gemini_contents(contents: Any) -> list[Turn]:
    """Extracts Turn objects from various Gemini SDK input formats."""
    turns: list[Turn] = []
    if isinstance(contents, str):
        return [Turn(role="user", content=contents)]
    if isinstance(contents, dict):
        contents = [contents]
    if isinstance(contents, list):
        for item in contents:
            if isinstance(item, str):
                turns.append(Turn(role="user", content=item))
            elif isinstance(item, Turn):
                turns.append(item)
            elif isinstance(item, dict):
                role = item.get("role", "user")
                if role == "model":
                    role = "assistant"
                parts = item.get("parts", [])
                text = ""
                turn_parts: list[dict[str, Any]] = []
                for p in parts:
                    if isinstance(p, str):
                        text += p
                        turn_parts.append({"text": p})
                    elif isinstance(p, dict):
                        turn_parts.append(p)
                        if "text" in p:
                            text += p["text"]
                turns.append(
                    Turn(
                        role=role if role in {"system", "user", "assistant", "tool"} else "user",
                        content=text or None,
                        parts=turn_parts,
                    )
                )
            elif hasattr(item, "role") and hasattr(item, "parts"):
                role = getattr(item, "role", "user")
                if role == "model":
                    role = "assistant"
                turns.append(Turn(role=role, content=str(getattr(item, "parts", ""))))
    if not turns:
        turns = [Turn(role="user", content="")]
    return turns


def parse_invocation_from_gemini_response(
    response: Any,
    *,
    model: str,
    region: str = "us-central1",
    generation_config: dict[str, Any] | None = None,
    tools: list[Any] | None = None,
    latency_ms: float = 0.0,
    pricing: PricingCatalog | None = None,
    trace_id: str | None = None,
) -> Invocation:
    pricing = pricing or PricingCatalog()
    raw = (
        response.model_dump(exclude_none=True)
        if hasattr(response, "model_dump")
        else (response if isinstance(response, dict) else {"text": getattr(response, "text", None)})
    )
    usage = raw.get("usage_metadata", {})
    candidates = raw.get("candidates", [])
    first_cand = candidates[0] if candidates else {}
    grounding = first_cand.get("grounding_metadata", {})
    parts = first_cand.get("content", {}).get("parts", [])

    tool_calls = [
        {"name": part["function_call"].get("name"), "arguments": part["function_call"].get("args", {})}
        for part in parts
        if "function_call" in part
    ]

    thought_parts = [str(part.get("text", "")) for part in parts if part.get("thought") and part.get("text")]
    thought_text = "\n".join(thought_parts) if thought_parts else None

    response_text = getattr(response, "text", None)
    if not response_text:
        non_thought = [str(part["text"]) for part in parts if not part.get("thought") and part.get("text")]
        response_text = "\n".join(non_thought) or None

    structured = None
    gen_config = generation_config or {}
    if response_text and gen_config.get("response_mime_type") == "application/json":
        try:
            structured = json.loads(response_text)
        except json.JSONDecodeError:
            structured = None

    cached_tokens = usage.get("cached_content_token_count", 0)
    thoughts_tokens = (
        usage.get("candidates_token_details", {}).get("thoughts_token_count", 0)
        or usage.get("thoughts_token_count", 0)
    )
    token_usage = {
        "input": usage.get("prompt_token_count", 0),
        "output": usage.get("candidates_token_count", 0),
        "total": usage.get("total_token_count", 0),
    }
    if cached_tokens:
        token_usage["cached"] = cached_tokens
    if thoughts_tokens:
        token_usage["thoughts"] = thoughts_tokens

    grounding_dict = {
        "web_search_queries": grounding.get("web_search_queries", []),
        "grounding_chunks": grounding.get("grounding_chunks", []),
        "grounding_supports": grounding.get("grounding_supports", []),
        "search_entry_point": grounding.get("search_entry_point", {}),
    }

    return Invocation(
        model=model,
        region=region,
        provider="gemini-api",
        generation=gen_config,
        tools=[tool if isinstance(tool, dict) else {"definition": str(tool)} for tool in (tools or [])],
        response_text=response_text,
        structured_output=structured,
        thought_text=thought_text,
        tool_calls=tool_calls,
        citations=grounding.get("grounding_chunks", []),
        grounding=grounding_dict,
        safety={"ratings": first_cand.get("safety_ratings", [])},
        token_usage=token_usage,
        latency_ms=latency_ms,
        estimated_cost_usd=pricing.estimate(model, token_usage),
        raw_response=raw,
        trace_id=trace_id,
    )


@contextmanager
def record_gemini(
    client: Any = None,
    *,
    scenario_name: str = "recorded-scenario",
    metadata: dict[str, Any] | None = None,
    pricing: PricingCatalog | None = None,
) -> Generator[GeminiRecording, None, None]:
    """Context manager that wraps/intercepts client.models.generate_content to capture transcripts."""
    recording = GeminiRecording(scenario_name=scenario_name, metadata=metadata)
    pricing = pricing or PricingCatalog()

    if client is not None and hasattr(client, "models") and hasattr(client.models, "generate_content"):
        orig_generate = client.models.generate_content

        def intercept_generate(model: str, contents: Any, config: Any = None, **kwargs):
            started = time.perf_counter()
            response = orig_generate(model=model, contents=contents, config=config, **kwargs)
            latency_ms = round((time.perf_counter() - started) * 1000, 2)

            turns = parse_turns_from_gemini_contents(contents)
            config_dict = (
                config.model_dump(exclude_none=True)
                if hasattr(config, "model_dump")
                else (config if isinstance(config, dict) else {})
            )
            tools = config_dict.get("tools") or []
            location = getattr(client, "location", "us-central1") or "us-central1"

            invocation = parse_invocation_from_gemini_response(
                response,
                model=model,
                region=location,
                generation_config=config_dict,
                tools=tools,
                latency_ms=latency_ms,
                pricing=pricing,
            )
            scenario = Scenario(name=scenario_name, turns=turns, metadata=recording.metadata)
            recording.transcripts.append(Transcript(scenario=scenario, invocation=invocation))
            return response

        client.models.generate_content = intercept_generate
        try:
            yield recording
        finally:
            client.models.generate_content = orig_generate
    else:
        yield recording
