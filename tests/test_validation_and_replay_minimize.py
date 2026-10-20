import pytest

from agentaxiom.contracts import Contract, ContractValidationError, validate_contract
from agentaxiom.evidence import redact
from agentaxiom.minimize import minimize_with_replay
from agentaxiom.models import Invocation, Scenario, Transcript, TranscriptValidationError, Turn


def test_transcript_rejects_unbounded_or_invalid_untrusted_input():
    with pytest.raises(TranscriptValidationError, match="scenario.turns"):
        Transcript.from_dict({"scenario": {"name": "bad", "turns": []}, "invocation": {"model": "x", "region": "us"}})
    with pytest.raises(TranscriptValidationError, match="non-negative"):
        Transcript.from_dict(
            {
                "scenario": {"name": "bad", "turns": [{"role": "user", "content": "hello"}]},
                "invocation": {"model": "x", "region": "us", "estimated_cost_usd": -1},
            }
        )


def test_contract_rejects_ambiguous_or_invalid_rules():
    with pytest.raises(ContractValidationError, match="both required and forbidden"):
        validate_contract(Contract("bad", required_tools=["search"], forbidden_tools=["search"]))
    with pytest.raises(ContractValidationError, match="invalid JSON Schema"):
        validate_contract(Contract("bad", output_schema={"type": "not-a-real-type"}))
    with pytest.raises(ContractValidationError, match="required_tools"):
        validate_contract(Contract("bad", required_tools="search"))


def test_redaction_covers_common_personal_data_and_sensitive_field_names():
    redacted = redact({"email": "person@example.test", "message": "SSN 123-45-6789 and owner@example.test"})
    assert redacted == {"email": "[REDACTED]", "message": "SSN [REDACTED] and [REDACTED]"}


def test_replay_minimizer_rechecks_each_candidate():
    source = Transcript(
        Scenario("failure", [Turn("user", "noise"), Turn("user", "keep")]),
        Invocation(model="recorded", region="us"),
    )

    def replay(scenario):
        bad = any(turn.content == "keep" for turn in scenario.turns)
        return Invocation(model="live", region="us", structured_output={"answer": "bad" if bad else "good"})

    minimized = minimize_with_replay(
        source,
        replay,
        lambda transcript: transcript.invocation.structured_output["answer"] == "bad",
    )
    assert [turn.content for turn in minimized.scenario.turns] == ["keep"]
