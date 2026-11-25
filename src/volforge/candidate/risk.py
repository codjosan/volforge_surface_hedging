"""Scenario risk quantification and stress-aware portfolio controls."""
from dataclasses import dataclass
from volforge.surface import Surface

IMPLEMENTED=False

@dataclass(frozen=True)
class RiskRequest:
    surfaces:dict[str,Surface]
    spots:dict[str,float]
    positions:dict[str,list[tuple[float,float,str,float]]]
    hedge_units:dict[str,float]
    rates:dict[str,float]
    carries:dict[str,float]
    equity:float

@dataclass(frozen=True)
class RiskReport:
    worst_pnl:float
    scenario_pnl:dict[str,float]
    breached:bool
    max_loss_fraction:float

class CandidateRisk:
    def assess(self,request:RiskRequest)->RiskReport:
        # TODO: report all 16 scenarios with real option revaluation, not just delta.
        # TODO: apply configurable portfolio limits, validate inputs, fail closed.
        return RiskReport(0.0,{},False,0.0)
