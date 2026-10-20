"""AgentAxiom: minimized, replayable, evidence-backed agent contracts."""

from .comparison import ComparisonPolicy, ComparisonResult, compare
from .contracts import Contract, ContractResult, evaluate_contract
from .models import Scenario, Transcript, Turn
from .pricing import ModelPricing, PricingCatalog
from .replay import ReplayPolicy, ReplayRunner

__all__ = [
    "Contract",
    "ContractResult",
    "evaluate_contract",
    "ComparisonPolicy",
    "ComparisonResult",
    "compare",
    "ModelPricing",
    "PricingCatalog",
    "Scenario",
    "Turn",
    "Transcript",
    "ReplayRunner",
    "ReplayPolicy",
]
__version__ = "0.1.0"
