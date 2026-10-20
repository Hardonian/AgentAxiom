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
    tool_argument_schemas: dict[str, dict[str, Any]] = field(default_factory=dict)
    tool_output_schemas: dict[str, dict[str, Any]] = field(default_factory=dict)
    require_citations: bool = False
    allowed_citation_domains: list[str] = field(default_factory=list)
    minimum_citations: int = 0
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
    for call in inv.tool_calls:
        name = call.get("name") or call.get("function", {}).get("name")
        schema = contract.tool_argument_schemas.get(name)
        if schema:
            arguments = call.get("arguments", call.get("function", {}).get("arguments", {}))
            for error in Draft202012Validator(schema).iter_errors(arguments):
                violations.append(
                    {"kind": "tool_arguments", "tool": name, "path": list(error.path), "message": error.message}
                )
    for turn in transcript.scenario.turns:
        if turn.role == "tool" and turn.tool_name in contract.tool_output_schemas:
            for error in Draft202012Validator(contract.tool_output_schemas[turn.tool_name]).iter_errors(
                turn.tool_output
            ):
                violations.append(
                    {"kind": "tool_output", "tool": turn.tool_name, "path": list(error.path), "message": error.message}
                )
    if contract.require_citations and not inv.citations:
        violations.append({"kind": "grounding", "message": "response has no citations"})
    if len(inv.citations) < contract.minimum_citations:
        violations.append(
            {"kind": "citation_count", "actual": len(inv.citations), "minimum": contract.minimum_citations}
        )
    if contract.allowed_citation_domains:
        from urllib.parse import urlparse

        allowed = set(contract.allowed_citation_domains)
        for citation in inv.citations:
            uri = citation.get("uri") or citation.get("web", {}).get("uri") or ""
            if not uri or urlparse(uri).netloc not in allowed:
                violations.append({"kind": "citation_domain", "uri": uri, "allowed": sorted(allowed)})
    action = inv.safety.get("action")
    if contract.allowed_safety_actions is not None and action not in contract.allowed_safety_actions:
        violations.append({"kind": "safety", "actual": action, "allowed": contract.allowed_safety_actions})
    if contract.max_latency_ms is not None and inv.latency_ms > contract.max_latency_ms:
        violations.append({"kind": "latency_budget", "actual": inv.latency_ms, "maximum": contract.max_latency_ms})
    if contract.max_cost_usd is not None and inv.estimated_cost_usd > contract.max_cost_usd:
        violations.append({"kind": "cost_budget", "actual": inv.estimated_cost_usd, "maximum": contract.max_cost_usd})
    return ContractResult(contract=contract.name, passed=not violations, violations=violations)
