from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jsonschema import Draft202012Validator

from .models import Transcript


class ContractValidationError(ValueError):
    """Raised when a contract is self-contradictory or unsafe to evaluate."""


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
    require_context_cache: bool = False
    min_cached_tokens: int = 0
    max_thinking_tokens: int | None = None
    blocked_safety_categories: list[str] = field(default_factory=list)
    min_grounding_score: float | None = None
    allowed_grounding_sources: list[str] = field(default_factory=list)
    allowed_safety_actions: list[str] | None = None
    max_latency_ms: float | None = None
    max_cost_usd: float | None = None


@dataclass
class ContractResult:
    contract: str
    passed: bool
    violations: list[dict[str, Any]]


def evaluate_contract(transcript: Transcript, contract: Contract) -> ContractResult:
    validate_contract(contract)
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
    if contract.allowed_grounding_sources:
        from urllib.parse import urlparse

        allowed_sources = set(contract.allowed_grounding_sources)
        all_chunks = list(inv.citations) + list(inv.grounding.get("grounding_chunks", []))
        for chunk in all_chunks:
            ret_ctx = chunk.get("retrieved_context", {})
            uri = chunk.get("uri") or chunk.get("web", {}).get("uri") or ret_ctx.get("uri") or ""
            domain = urlparse(uri).netloc if uri else ""
            datastore = ret_ctx.get("rag_corpus_id") or chunk.get("datastore_id") or ""
            matched = False
            for allowed_source in allowed_sources:
                if (
                    (domain and domain == allowed_source)
                    or (uri and uri.startswith(allowed_source))
                    or (datastore and datastore == allowed_source)
                ):
                    matched = True
                    break
            if not matched and (uri or datastore):
                violations.append(
                    {"kind": "grounding_source", "source": uri or datastore, "allowed": sorted(allowed_sources)}
                )
    if contract.min_grounding_score is not None:
        supports = inv.grounding.get("grounding_supports", [])
        for support in supports:
            score = support.get("confidence_score") or support.get("score")
            if score is not None and score < contract.min_grounding_score:
                violations.append(
                    {"kind": "grounding_score", "actual": score, "minimum": contract.min_grounding_score}
                )
    if contract.require_context_cache and inv.token_usage.get("cached", 0) <= 0:
        violations.append(
            {"kind": "context_cache", "message": "expected context cache hit but cached token count is 0"}
        )
    if contract.min_cached_tokens > 0 and inv.token_usage.get("cached", 0) < contract.min_cached_tokens:
        violations.append({
            "kind": "cached_tokens",
            "actual": inv.token_usage.get("cached", 0),
            "minimum": contract.min_cached_tokens,
        })
    if contract.max_thinking_tokens is not None and inv.token_usage.get("thoughts", 0) > contract.max_thinking_tokens:
        violations.append({
            "kind": "thinking_budget",
            "actual": inv.token_usage.get("thoughts", 0),
            "maximum": contract.max_thinking_tokens,
        })
    if contract.blocked_safety_categories:
        blocked_cats = set(contract.blocked_safety_categories)
        ratings = inv.safety.get("ratings", [])
        for rating in ratings:
            cat = rating.get("category")
            prob = rating.get("probability")
            blocked = rating.get("blocked", False)
            if cat in blocked_cats and (blocked or prob in {"MEDIUM", "HIGH"}):
                violations.append({"kind": "safety_category", "category": cat, "probability": prob})
    action = inv.safety.get("action")
    if contract.allowed_safety_actions is not None and action not in contract.allowed_safety_actions:
        violations.append({"kind": "safety", "actual": action, "allowed": contract.allowed_safety_actions})
    if contract.max_latency_ms is not None and inv.latency_ms > contract.max_latency_ms:
        violations.append({"kind": "latency_budget", "actual": inv.latency_ms, "maximum": contract.max_latency_ms})
    if contract.max_cost_usd is not None and inv.estimated_cost_usd > contract.max_cost_usd:
        violations.append({"kind": "cost_budget", "actual": inv.estimated_cost_usd, "maximum": contract.max_cost_usd})
    return ContractResult(contract=contract.name, passed=not violations, violations=violations)


def validate_contract(contract: Contract) -> None:
    if not isinstance(contract.name, str) or not contract.name.strip():
        raise ContractValidationError("contract.name must be a non-empty string")
    overlap = set(contract.required_tools) & set(contract.forbidden_tools)
    if overlap:
        raise ContractValidationError(f"tools cannot be both required and forbidden: {sorted(overlap)}")
    list_attributes = (
        "required_tools",
        "forbidden_tools",
        "allowed_citation_domains",
        "blocked_safety_categories",
        "allowed_grounding_sources",
    )
    for attribute in list_attributes:
        values = getattr(contract, attribute)
        if not isinstance(values, list) or not all(isinstance(value, str) and value.strip() for value in values):
            raise ContractValidationError(f"contract.{attribute} must be a list of non-empty strings")
    if contract.allowed_safety_actions is not None and (
        not isinstance(contract.allowed_safety_actions, list)
        or not all(isinstance(action, str) and action.strip() for action in contract.allowed_safety_actions)
    ):
        raise ContractValidationError("contract.allowed_safety_actions must be a list of non-empty strings or null")
    for attribute in ("tool_argument_schemas", "tool_output_schemas"):
        values = getattr(contract, attribute)
        if not isinstance(values, dict) or not all(
            isinstance(name, str) and isinstance(schema, dict) for name, schema in values.items()
        ):
            raise ContractValidationError(f"contract.{attribute} must map tool names to JSON Schema objects")
    for limit in (contract.max_latency_ms, contract.max_cost_usd):
        if limit is not None and (not isinstance(limit, (int, float)) or limit < 0):
            raise ContractValidationError("contract budgets must be non-negative numbers")
    if not isinstance(contract.minimum_citations, int) or contract.minimum_citations < 0:
        raise ContractValidationError("contract.minimum_citations must be a non-negative integer")
    if not isinstance(contract.min_cached_tokens, int) or contract.min_cached_tokens < 0:
        raise ContractValidationError("contract.min_cached_tokens must be a non-negative integer")
    if contract.max_thinking_tokens is not None and (
        not isinstance(contract.max_thinking_tokens, int) or contract.max_thinking_tokens < 0
    ):
        raise ContractValidationError("contract.max_thinking_tokens must be a non-negative integer or null")
    if contract.min_grounding_score is not None and (
        not isinstance(contract.min_grounding_score, (int, float)) or not 0.0 <= contract.min_grounding_score <= 1.0
    ):
        raise ContractValidationError("contract.min_grounding_score must be a number between 0.0 and 1.0 or null")
    schemas = [contract.output_schema, *contract.tool_argument_schemas.values(), *contract.tool_output_schemas.values()]
    for schema in schemas:
        if schema is not None:
            if not isinstance(schema, dict):
                raise ContractValidationError("contract schemas must be JSON objects")
            try:
                Draft202012Validator.check_schema(schema)
            except Exception as exc:
                raise ContractValidationError(f"contract includes an invalid JSON Schema: {exc}") from exc
