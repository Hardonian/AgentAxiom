from agentaxiom.contracts import Contract, evaluate_contract
from agentaxiom.minimize import minimize_conversation
from agentaxiom.models import Invocation, Scenario, Transcript, Turn

def sample():
    return Transcript(Scenario("quoted-answer", [Turn("user", "What is the policy?")]), Invocation(model="gemini-2.5-flash", region="us-central1", structured_output={"answer": "Yes"}, tool_calls=[{"name": "search"}], citations=[{"uri": "https://example.test"}], latency_ms=50, estimated_cost_usd=.001))

def test_contract_passes():
    result = evaluate_contract(sample(), Contract("answer", output_schema={"type": "object", "required": ["answer"]}, required_tools=["search"], require_citations=True, max_latency_ms=100))
    assert result.passed

def test_contract_reports_contract_violations():
    result = evaluate_contract(sample(), Contract("bad", required_tools=["write"], forbidden_tools=["search"], max_cost_usd=0.0001))
    assert {v["kind"] for v in result.violations} == {"tool_missing", "tool_forbidden", "cost_budget"}

def test_minimizes_trace():
    t = sample(); t.scenario.turns = [Turn("user", "noise"), Turn("user", "keep")]
    minimized = minimize_conversation(t, lambda trace: any(x.content == "keep" for x in trace.scenario.turns))
    assert [x.content for x in minimized.scenario.turns] == ["keep"]
