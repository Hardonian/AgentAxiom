"""Explicit, versioned cost estimation; no hidden or remotely fetched pricing."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ModelPricing:
    input_per_million_usd: float
    output_per_million_usd: float
    cached_read_per_million_usd: float = 0.0
    thinking_per_million_usd: float | None = None
    effective_date: str | None = None
    source: str | None = None


@dataclass
class PricingCatalog:
    rates: dict[str, ModelPricing] = field(default_factory=dict)
    version: str = "user-supplied"
    effective_date: str | None = None
    approval_status: str | None = None

    @classmethod
    def from_json(cls, path: str | Path) -> PricingCatalog:
        """Loads a catalog file; unknown rate keys fail loudly instead of silently dropping."""
        data: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
        rates = {name: ModelPricing(**spec) for name, spec in data.get("rates", {}).items()}
        return cls(
            rates=rates,
            version=data.get("version", "user-supplied"),
            effective_date=data.get("effective_date"),
            approval_status=data.get("approval_status"),
        )

    def estimate(self, model: str, usage: dict[str, int]) -> float:
        """Returns zero for unknown models: caller must never treat it as a quote."""
        rate = self.rates.get(model)
        if not rate:
            return 0.0
        input_tokens = usage.get("input", 0)
        output_tokens = usage.get("output", 0)
        cached_tokens = usage.get("cached", 0)
        thinking_tokens = usage.get("thoughts", 0)

        # In Gemini / Vertex AI, cached tokens are charged at the cached rate.
        standard_input = max(0, input_tokens - cached_tokens) if cached_tokens else input_tokens
        input_cost = standard_input * rate.input_per_million_usd
        cached_cost = cached_tokens * rate.cached_read_per_million_usd

        thinking_rate = (
            rate.thinking_per_million_usd
            if rate.thinking_per_million_usd is not None
            else rate.output_per_million_usd
        )
        standard_output = max(0, output_tokens - thinking_tokens) if thinking_tokens else output_tokens
        output_cost = standard_output * rate.output_per_million_usd + thinking_tokens * thinking_rate

        return round((input_cost + cached_cost + output_cost) / 1_000_000, 8)
