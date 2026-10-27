"""Bundled pricing catalogs for AgentAxiom."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any


def get_catalog_data(name: str = "gemini-catalog-2026-10") -> dict[str, Any]:
    """Retrieves bundled pricing catalog data."""
    filename = f"{name}.json" if not name.endswith(".json") else name
    content = files("agentaxiom.catalogs").joinpath(filename).read_text(encoding="utf-8")
    return json.loads(content)

