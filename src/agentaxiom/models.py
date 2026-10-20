from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Literal


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
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
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
        return stable_hash({"prompt": self.scenario.prompt_hash, "invocation": self.invocation.model, "generation": self.invocation.generation})

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Transcript":
        scenario = Scenario(turns=[Turn(**turn) for turn in data["scenario"]["turns"]], name=data["scenario"]["name"], metadata=data["scenario"].get("metadata", {}))
        return cls(scenario=scenario, invocation=Invocation(**data["invocation"]), schema_version=data.get("schema_version", "v1"))
