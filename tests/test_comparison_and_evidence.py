import json

from agentaxiom.comparison import ComparisonPolicy, compare
from agentaxiom.contracts import Contract, evaluate_contract
from agentaxiom.evidence import write_bundle
from agentaxiom.models import Invocation, Scenario, Transcript, Turn
from agentaxiom.pricing import ModelPricing, PricingCatalog


def transcript(**overrides):
    invocation = Invocation(model="gemini-test", region="us-central1", structured_output={"answer": "yes", "request_id": "volatile"}, tool_calls=[{"name": "lookup", "arguments": {"query": "policy"}}], citations=[{"uri": "https://docs.example.test/policy"}], safety={"action": "allow"}, latency_ms=100, estimated_cost_usd=.01)
    for key, value in overrides.items(): setattr(invocation, key, value)
    return Transcript(Scenario("test", [Turn("user", "Question")]), invocation)


def test_comparison_detects_real_regressions_and_ignores_configured_noise():
    baseline = transcript()
    candidate = transcript(structured_output={"answer": "yes", "request_id": "new"}, latency_ms=140)
    assert compare(baseline, candidate, ComparisonPolicy(ignored_output_paths=["/request_id"])).equivalent
    broken = transcript(tool_calls=[{"name": "delete", "arguments": {}}])
    result = compare(baseline, broken)
    assert not result.equivalent
    assert result.regressions[0]["kind"] == "tool_sequence"


def test_tool_contract_citation_domain_and_pricing():
    sample = transcript()
    contract = Contract("safe", tool_argument_schemas={"lookup": {"type": "object", "required": ["query"]}}, allowed_citation_domains=["docs.example.test"], minimum_citations=1)
    assert evaluate_contract(sample, contract).passed
    estimate = PricingCatalog({"gemini-test": ModelPricing(1, 2)}).estimate("gemini-test", {"input": 1_000_000, "output": 1_000_000})
    assert estimate == 3


def test_tool_output_contract_is_enforced():
    sample = transcript()
    sample.scenario.turns.append(Turn("tool", tool_name="lookup", tool_output={"status": 500}))
    result = evaluate_contract(sample, Contract("tool-output", tool_output_schemas={"lookup": {"type": "object", "properties": {"status": {"const": 200}}, "required": ["status"]}}))
    assert not result.passed
    assert result.violations[0]["kind"] == "tool_output"


def test_evidence_has_checksum_and_redacts(tmp_path):
    sample = transcript(raw_response={"api_key": "not-for-evidence"})
    result = evaluate_contract(sample, Contract("pass"))
    bundle = write_bundle(tmp_path, sample, result)
    evidence, manifest = json.loads((bundle / "evidence.json").read_text()), json.loads((bundle / "manifest.json").read_text())
    assert evidence["transcript"]["invocation"]["raw_response"]["api_key"] == "[REDACTED]"
    assert manifest["evidence_id"] == sample.evidence_id
