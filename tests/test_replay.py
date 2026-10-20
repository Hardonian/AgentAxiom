import pytest

from agentaxiom.contracts import Contract
from agentaxiom.models import Invocation, Scenario, Transcript, Turn
from agentaxiom.replay import ReplayPolicy, ReplayRunner


class Client:
    def invoke(self, scenario):
        return Invocation(model="candidate", region="us", estimated_cost_usd=0.05)


def recorded():
    return Transcript(Scenario("replay", [Turn("user", "hello")]), Invocation(model="baseline", region="us"))


def test_live_replay_fails_closed_without_per_call_cost_ceiling():
    with pytest.raises(PermissionError, match="per_call"):
        ReplayRunner(Client(), ReplayPolicy(live_verification=True, max_live_calls=1, max_live_cost_usd=1)).replay(recorded(), Contract("pass"))


def test_live_replay_respects_budget_and_preserves_schema_version():
    source = recorded(); source.schema_version = "v2"
    replayed, result = ReplayRunner(Client(), ReplayPolicy(live_verification=True, max_live_calls=1, max_live_cost_usd=1, max_cost_per_call_usd=.1)).replay(source, Contract("pass"))
    assert result.passed and replayed.schema_version == "v2"
