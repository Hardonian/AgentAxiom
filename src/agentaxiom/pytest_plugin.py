from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from .contracts import Contract, ContractResult, evaluate_contract
from .evidence import write_bundle
from .models import Transcript


def pytest_addoption(parser):
    group = parser.getgroup("agentaxiom")
    group.addoption("--agentaxiom-evidence", default="agentaxiom-evidence", help="evidence output directory")


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "agentaxiom: mark test as an AgentAxiom contract or regression test",
    )


@pytest.fixture
def agent_contract(request):
    """Pytest fixture to verify an AgentAxiom transcript against a contract."""

    def verify(
        transcript: Transcript,
        contract: Contract | dict[str, Any] | str | Path,
    ) -> ContractResult:
        if isinstance(contract, (str, Path)):
            contract = Contract(**json.loads(Path(contract).read_text(encoding="utf-8")))
        elif isinstance(contract, dict):
            contract = Contract(**contract)

        result = evaluate_contract(transcript, contract)
        if not result.passed:
            write_bundle(
                Path(request.config.getoption("--agentaxiom-evidence")) / transcript.scenario.name, transcript, result
            )
        assert result.passed, json.dumps(result.violations, indent=2)
        return result

    return verify


@pytest.fixture
def recorded_gemini():
    """Convenience fixture providing the record_gemini context manager."""
    from .recorder import record_gemini

    return record_gemini
