"""Realistic but deliberately simplified execution cost and hedging diagnostics."""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class ExecutionModel:
    commission_bps:float=.4
    max_participation:float=.05
    impact_power:float=.5

    def estimate(self,notional_usd:float,adv_usd:float,spread_bps:float,
                 impact_coefficient_bps:float,stress_mult:float=1.0)->dict:
        if not all(math.isfinite(v) for v in (notional_usd,adv_usd,spread_bps,impact_coefficient_bps,stress_mult)):
            raise ValueError('nonfinite execution inputs')
        if min(notional_usd,spread_bps,impact_coefficient_bps)<0 or adv_usd<=0 or stress_mult<=0:
            raise ValueError('invalid execution inputs')
        participation=notional_usd/adv_usd
        if participation>self.max_participation:
            return {'fillable':False,'participation':participation,
                    'cost_usd':0.0,'effective_bps':float('inf')}
        impact=impact_coefficient_bps*(participation**self.impact_power)
        rate=stress_mult*(self.commission_bps+spread_bps/2+impact)
        return {'fillable':True,'participation':participation,
                'cost_usd':notional_usd*rate/10000,'effective_bps':rate}


def optimal_no_trade_band(option_gamma:float,spot:float,vol:float,
                          cost_bps:float,horizon_days:int=1)->float:
    """Heuristic inventory-units buffer: not a theorem of optimal hedging."""
    if spot<=0 or vol<0 or cost_bps<0 or horizon_days<=0:
        raise ValueError('invalid no-trade inputs')
    expected_move=spot*vol*math.sqrt(horizon_days/365)
    curvature=abs(option_gamma)*expected_move
    return max(0.0,(cost_bps/10000)*spot/(max(.01,curvature)))


def pnl_reconciliation(start_equity:float,end_equity:float,
                       booked_pnl:float,cost_usd:float,unrealized_pnl:float,
                       atol:float=.01)->dict:
    computed=start_equity+booked_pnl-cost_usd+unrealized_pnl
    residual=end_equity-computed
    return {'expected_equity':computed,'observed_equity':end_equity,
            'residual':residual,'balanced':abs(residual)<=atol}
