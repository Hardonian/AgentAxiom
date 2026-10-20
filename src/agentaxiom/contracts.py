from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jsonschema import Draft202012Validator

from .models import Transcript


@dataclass
class Contract:
    name: str
    output_schema: dict[str, Any] | None = None
    required_tools: list[str] = field(default_factory=list)
    forbidden_tools: list[str] = field(default_factory=list)
    require_citations: bool = False
    allowed_safety_actions: list[str] | None = None
    max_latency_ms: float | None = None
    max_cost_usd: float | None = None


@dataclass
class ContractResult:
    contract: str
    passed: bool
    violations: list[dict[str, Any]]


def evaluate_contract(transcript: Transcript, contract: Contract) -> ContractResult:
    inv = transcript.invocation
    violations: list[dict[str, Any]] = []
    if contract.output_schema:
        for error in Draft202012Validator(contract.output_schema).iter_errors(inv.structured_output):
            violations.append({"kind": "schema", "path": list(error.path), "message": error.message})
    called = {call.get("name") or call.get("function", {}).get("name") for call in inv.tool_calls}
    for name in contract.required_tools:
        if name not in called:
            violations.append({"kind": "tool_missing", "tool": name})
    for name in contract.forbidden_tools:
        if name in called:
            violations.append({"kind": "tool_forbidden", "tool": name})
    if contract.require_citations and not inv.citations:
        violations.append({"kind": "grounding", "message": "response has no citations"})
    action = inv.safety.get("action")
    if contract.allowed_safety_actions is not None and action not in contract.allowed_safety_actions:
        violations.append({"kind": "safety", "actual": action, "allowed": contract.allowed_safety_actions})
    if contract.max_latency_ms is not None and inv.latency_ms > contract.max_latency_ms:
        violations.append({"kind": "latency_budget", "actual": inv.latency_ms, "maximum": contract.max_latency_ms})
    if contract.max_cost_usd is not None and inv.estimated_cost_usd > contract.max_cost_usd:
        violations.append({"kind": "cost_budget", "actual": inv.estimated_cost_usd, "maximum": contract.max_cost_usd})
    return ContractResult(contract=contract.name, passed=not violations, violations=violations)
