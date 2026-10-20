from __future__ import annotations

import json
from pathlib import Path

import pytest

from .contracts import Contract, evaluate_contract
from .evidence import write_bundle
from .models import Transcript

def pytest_addoption(parser):
    group = parser.getgroup("agentaxiom")
    group.addoption("--agentaxiom-evidence", default="agentaxiom-evidence", help="evidence output directory")

@pytest.fixture
def agent_contract(request):
    def verify(transcript: Transcript, contract: Contract):
        result = evaluate_contract(transcript, contract)
        if not result.passed:
            write_bundle(Path(request.config.getoption("--agentaxiom-evidence")) / transcript.scenario.name, transcript, result)
        assert result.passed, json.dumps(result.violations, indent=2)
        return result
    return verify
