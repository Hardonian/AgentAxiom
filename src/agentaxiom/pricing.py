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
        data: dict[str, Any] = json.loads(Path(path).read_text())
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
        return round(
            (usage.get("input", 0) * rate.input_per_million_usd + usage.get("output", 0) * rate.output_per_million_usd)
            / 1_000_000,
            8,
        )
