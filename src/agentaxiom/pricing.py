"""Explicit, versioned cost estimation; no hidden or remotely fetched pricing."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ModelPricing:
    input_per_million_usd: float
    output_per_million_usd: float


@dataclass
class PricingCatalog:
    rates: dict[str, ModelPricing] = field(default_factory=dict)
    version: str = "user-supplied"

    def estimate(self, model: str, usage: dict[str, int]) -> float:
        """Returns zero for unknown models: caller must never treat it as a quote."""
        rate = self.rates.get(model)
        if not rate: return 0.0
        return round((usage.get("input", 0) * rate.input_per_million_usd + usage.get("output", 0) * rate.output_per_million_usd) / 1_000_000, 8)
