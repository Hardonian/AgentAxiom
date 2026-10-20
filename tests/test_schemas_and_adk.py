import json
from pathlib import Path

from jsonschema import Draft202012Validator

from agentaxiom.models import Scenario, Turn
from agentaxiom.providers import ADKRecorder


ROOT = Path(__file__).parents[1]


def test_public_schemas_validate_examples_and_themselves():
    contract_schema = json.loads((ROOT / "schemas" / "contract.v1.schema.json").read_text())
    transcript_schema = json.loads((ROOT / "schemas" / "transcript.v1.schema.json").read_text())
    Draft202012Validator.check_schema(contract_schema)
    Draft202012Validator.check_schema(transcript_schema)
    assert Draft202012Validator(contract_schema).is_valid(json.loads((ROOT / "examples" / "contract.json").read_text()))
    assert Draft202012Validator(transcript_schema).is_valid(
        json.loads((ROOT / "examples" / "fixture.json").read_text())
    )


def test_adk_recorder_normalizes_events_without_live_execution():
    invocation = ADKRecorder(model="gemini-test", region="us", adk_version="1.2.3").record(
        Scenario("adk", [Turn("user", "hello")]),
        [
            {"text": "answer", "usage": {"input": 2}},
            {
                "function_call": {"name": "lookup", "arguments": {"query": "hello"}},
                "grounding": [{"uri": "https://example.test"}],
                "usage": {"output": 3},
                "latency_ms": 10,
                "trace_id": "trace",
            },
        ],
    )
    assert invocation.provider == "adk"
    assert invocation.tool_calls[0]["name"] == "lookup"
    assert invocation.token_usage == {"input": 2, "output": 3}
    assert invocation.trace_id == "trace"
