from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .contracts import Contract, ContractResult, evaluate_contract
from .models import Invocation, Scenario, Transcript


class AgentClient(Protocol):
    def invoke(self, scenario: Scenario) -> Invocation: ...


@dataclass
class ReplayPolicy:
    live_verification: bool = False
    max_live_calls: int = 0
    max_live_cost_usd: float = 0.0
    max_cost_per_call_usd: float = 0.0


class ReplayRunner:
    """Offline replay by default. Live providers must be explicitly permitted."""
    def __init__(self, client: AgentClient | None = None, policy: ReplayPolicy | None = None):
        self.client, self.policy, self.live_calls, self.live_cost = client, policy or ReplayPolicy(), 0, 0.0

    def replay(self, recorded: Transcript, contract: Contract) -> tuple[Transcript, ContractResult]:
        if self.client is None:
            return recorded, evaluate_contract(recorded, contract)
        if not self.policy.live_verification:
            raise PermissionError("live verification is disabled; use recorded evidence or explicitly enable it")
        if self.live_calls >= self.policy.max_live_calls:
            raise PermissionError("live-call budget exhausted")
        if self.policy.max_cost_per_call_usd <= 0:
            raise PermissionError("live replay requires an explicit positive max_cost_per_call_usd")
        if self.live_cost + self.policy.max_cost_per_call_usd > self.policy.max_live_cost_usd:
            raise PermissionError("remaining live-cost budget is smaller than the per-call ceiling")
        invocation = self.client.invoke(recorded.scenario)
        if self.live_cost + invocation.estimated_cost_usd > self.policy.max_live_cost_usd:
            raise PermissionError("live-cost budget exceeded")
        self.live_calls += 1
        self.live_cost += invocation.estimated_cost_usd
        replayed = Transcript(scenario=recorded.scenario, invocation=invocation, schema_version=recorded.schema_version)
        return replayed, evaluate_contract(replayed, contract)
