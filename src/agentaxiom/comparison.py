"""Deterministic cross-model/version regression comparison."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .models import Transcript, stable_hash


@dataclass
class ComparisonPolicy:
    name: str = "default"
    compare_structured_output: bool = True
    compare_tool_sequence: bool = True
    compare_safety: bool = True
    compare_citation_domains: bool = False
    max_latency_regression_ratio: float | None = 1.5
    max_cost_regression_ratio: float | None = 1.5
    ignored_output_paths: list[str] = field(default_factory=list)
    normalize_whitespace: bool = True


@dataclass
class ComparisonResult:
    policy: str
    equivalent: bool
    regressions: list[dict[str, Any]]
    baseline_evidence_id: str
    candidate_evidence_id: str


def _drop_paths(value: Any, ignored: list[str]) -> Any:
    value = json.loads(json.dumps(value))
    for path in ignored:
        current = value
        pieces = [part for part in path.strip("/").split("/") if part]
        for piece in pieces[:-1]:
            if isinstance(current, dict):
                current = current.get(piece, {})
            elif isinstance(current, list) and piece.isdigit() and int(piece) < len(current):
                current = current[int(piece)]
            else:
                current = {}
        if pieces and isinstance(current, dict):
            current.pop(pieces[-1], None)
    return value


def _tool_signature(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "name": call.get("name") or call.get("function", {}).get("name"),
            "arguments": call.get("arguments", call.get("function", {}).get("arguments", {})),
        }
        for call in calls
    ]


def compare(baseline: Transcript, candidate: Transcript, policy: ComparisonPolicy | None = None) -> ComparisonResult:
    policy = policy or ComparisonPolicy()
    regressions: list[dict[str, Any]] = []
    if baseline.scenario.prompt_hash != candidate.scenario.prompt_hash:
        regressions.append(
            {
                "kind": "scenario_mismatch",
                "baseline": baseline.scenario.prompt_hash,
                "candidate": candidate.scenario.prompt_hash,
            }
        )
    if policy.compare_structured_output:
        before, after = (
            _drop_paths(baseline.invocation.structured_output, policy.ignored_output_paths),
            _drop_paths(candidate.invocation.structured_output, policy.ignored_output_paths),
        )
        if stable_hash(before) != stable_hash(after):
            regressions.append({"kind": "structured_output", "baseline": before, "candidate": after})
    if policy.compare_tool_sequence:
        before, after = (
            _tool_signature(baseline.invocation.tool_calls),
            _tool_signature(candidate.invocation.tool_calls),
        )
        if before != after:
            regressions.append({"kind": "tool_sequence", "baseline": before, "candidate": after})
    if policy.compare_safety and baseline.invocation.safety != candidate.invocation.safety:
        regressions.append(
            {"kind": "safety", "baseline": baseline.invocation.safety, "candidate": candidate.invocation.safety}
        )
    if policy.compare_citation_domains:
        from urllib.parse import urlparse

        before = sorted(urlparse(c.get("uri", "")).netloc for c in baseline.invocation.citations)
        after = sorted(urlparse(c.get("uri", "")).netloc for c in candidate.invocation.citations)
        if before != after:
            regressions.append({"kind": "citation_domains", "baseline": before, "candidate": after})
    for metric, ratio in [
        ("latency_ms", policy.max_latency_regression_ratio),
        ("estimated_cost_usd", policy.max_cost_regression_ratio),
    ]:
        old, new = getattr(baseline.invocation, metric), getattr(candidate.invocation, metric)
        if ratio is not None and old > 0 and new / old > ratio:
            regressions.append(
                {"kind": f"{metric}_regression", "baseline": old, "candidate": new, "maximum_ratio": ratio}
            )
    return ComparisonResult(policy.name, not regressions, regressions, baseline.evidence_id, candidate.evidence_id)
