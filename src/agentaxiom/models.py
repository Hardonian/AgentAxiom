from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Literal


class TranscriptValidationError(ValueError):
    """Raised when untrusted transcript data is not safe to evaluate."""


MAX_TURNS = 100
MAX_TEXT_CHARS = 200_000
MAX_TOOL_CALLS = 100


def stable_hash(value: Any) -> str:
    import json

    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass
class Turn:
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_output: Any = None
    parts: list[dict[str, Any]] = field(default_factory=list)

    @property
    def effective_text(self) -> str:
        """Returns turn text content, resolving text parts if content is not set."""
        if self.content:
            return self.content
        if self.parts:
            return "\n".join(str(p.get("text", "")) for p in self.parts if p.get("text"))
        return ""


@dataclass
class Scenario:
    name: str
    turns: list[Turn]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def prompt_hash(self) -> str:
        return stable_hash([asdict(turn) for turn in self.turns])


@dataclass
class Invocation:
    model: str
    region: str
    provider: str = "offline"
    generation: dict[str, Any] = field(default_factory=dict)
    tools: list[dict[str, Any]] = field(default_factory=list)
    adk_version: str | None = None
    response_text: str | None = None
    structured_output: Any = None
    thought_text: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    grounding: dict[str, Any] = field(default_factory=dict)
    safety: dict[str, Any] = field(default_factory=dict)
    token_usage: dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0
    raw_response: dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None
    trace_id: str | None = None
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Transcript:
    scenario: Scenario
    invocation: Invocation
    schema_version: str = "v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def evidence_id(self) -> str:
        """Stable identity for grouping equivalent captured evidence."""
        return stable_hash(
            {
                "prompt": self.scenario.prompt_hash,
                "invocation": self.invocation.model,
                "generation": self.invocation.generation,
            }
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Transcript:
        validate_transcript_data(data)
        scenario = Scenario(
            turns=[Turn(**turn) for turn in data["scenario"]["turns"]],
            name=data["scenario"]["name"],
            metadata=data["scenario"].get("metadata", {}),
        )
        return cls(
            scenario=scenario,
            invocation=Invocation(**data["invocation"]),
            schema_version=data.get("schema_version", "v1"),
        )


def validate_transcript_data(data: Any) -> None:
    """Bound and validate untrusted JSON before it becomes a transcript object."""
    if not isinstance(data, dict):
        raise TranscriptValidationError("transcript must be a JSON object")
    scenario, invocation = data.get("scenario"), data.get("invocation")
    if not isinstance(scenario, dict) or not isinstance(invocation, dict):
        raise TranscriptValidationError("transcript requires scenario and invocation objects")
    if not isinstance(scenario.get("name"), str) or not scenario["name"].strip():
        raise TranscriptValidationError("scenario.name must be a non-empty string")
    turns = scenario.get("turns")
    if not isinstance(turns, list) or not turns or len(turns) > MAX_TURNS:
        raise TranscriptValidationError(f"scenario.turns must contain 1 to {MAX_TURNS} turns")
    for index, turn in enumerate(turns):
        if not isinstance(turn, dict) or turn.get("role") not in {"system", "user", "assistant", "tool"}:
            raise TranscriptValidationError(f"turn {index} has an invalid role")
        if turn.get("content") is not None and (
            not isinstance(turn["content"], str) or len(turn["content"]) > MAX_TEXT_CHARS
        ):
            raise TranscriptValidationError(f"turn {index} content must be text under {MAX_TEXT_CHARS} characters")
        if turn.get("parts") is not None and not isinstance(turn.get("parts"), list):
            raise TranscriptValidationError(f"turn {index} parts must be a list")
    for attribute in ("model", "region"):
        if not isinstance(invocation.get(attribute), str) or not invocation[attribute].strip():
            raise TranscriptValidationError(f"invocation.{attribute} must be a non-empty string")
    tool_calls = invocation.get("tool_calls", [])
    if not isinstance(tool_calls, list) or len(tool_calls) > MAX_TOOL_CALLS:
        raise TranscriptValidationError(f"invocation.tool_calls must contain at most {MAX_TOOL_CALLS} calls")
    for attribute in ("latency_ms", "estimated_cost_usd"):
        value = invocation.get(attribute, 0)
        if not isinstance(value, (int, float)) or value < 0:
            raise TranscriptValidationError(f"invocation.{attribute} must be a non-negative number")
