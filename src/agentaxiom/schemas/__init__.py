"""Bundled JSON schemas for AgentAxiom."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any


def get_schema(name: str) -> dict[str, Any]:
    """Retrieves a bundled JSON schema (e.g. 'contract.v1' or 'transcript.v1')."""
    filename = f"{name}.schema.json" if not name.endswith(".json") else name
    content = files("agentaxiom.schemas").joinpath(filename).read_text(encoding="utf-8")
    return json.loads(content)

