"""Deterministic volatility, spot, skew, calendar, and data-quality fault scenarios."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping
import math
from .surface import Surface,Smile

@dataclass(frozen=True)
class Scenario:
    name: str
    spot_shift: float
    vol_mult: float
    skew_shift: float=0.0
    term_twist: float=0.0
    illiquid_mult: float=1.0
    description: str=''

SCENARIOS=(
    Scenario('base',0.0,1.0),
    Scenario('crypto_crash_12pct',-.12,1.30,skew_shift=-.1),
    Scenario('crypto_crash_30pct',-.30,1.60,skew_shift=-.18),
    Scenario('crypto_rally_18pct',.18,1.25),
    Scenario('vol_crush',.02,.65),
    Scenario('vol_double',-.04,2.0),
    Scenario('left_skew_steepens',-.06,1.05,skew_shift=-.25),
    Scenario('right_skew_reverses',.08,1.1,skew_shift=.40),
    Scenario('front_end_vol_spike',-.07,1.25,term_twist=.8),
    Scenario('back_end_vol_spike',.04,1.15,term_twist=-.5),
    Scenario('spot_gap_up_40pct',.4,1.35),
    Scenario('spot_gap_down_45pct',-.45,1.75),
    Scenario('two_sided_dislocation',-.18,2.3,skew_shift=.2),
    Scenario('hedge_liquidity_evaporates',-.1,1.4,illiquid_mult=.05),
    Scenario('sticky_strike_vs_delta',-.08,1.0,skew_shift=-.32),
    Scenario('vol_term_inversion',-.02,1.5,term_twist=1.25),
)

def shock_surface(surface:Surface,scenario:Scenario)->Surface:
    smiles={}
    for tenor,s in surface.smiles.items():
        twist=(30/max(7,tenor))**.35
        mult=max(.15,scenario.vol_mult*(1+scenario.term_twist*(twist-1)))
        smiles[tenor]=Smile(s.a*mult*mult,s.b*mult*mult,
                            max(-.95,min(.95,s.rho+scenario.skew_shift)),s.m,s.sigma)
    return Surface(smiles)

def scenario_pnl(surface:Surface,spot:float,positions:list[tuple[float,float,str,float]],
                 hedge_units:float=0.0,rate:float=0.0,carry:float=0.0,
                 scenario:Scenario=SCENARIOS[0])->float:
    """Positions: (strike, remaining calendar days, right, signed option units)."""
    shocked=shock_surface(surface,scenario)
    new_spot=spot*(1+scenario.spot_shift)
    if new_spot<=0:
        raise ValueError('scenario spot nonpositive')
    pnl=hedge_units*(new_spot-spot)
    for strike,days,right,qty in positions:
        price0=surface.price(spot,strike,days,right,rate,carry)
        price1=shocked.price(new_spot,strike,days,right,rate,carry)
        pnl+=qty*(price1-price0)
    # Liquidity stress adds a stylized penalty to exiting the futures hedge.
    # This is not a full order-book liquidation or an actual fill guarantee.
    if scenario.illiquid_mult < 1.0:
        pnl-=abs(hedge_units*new_spot)*.0002*(1.0/math.sqrt(scenario.illiquid_mult)-1.0)
    return pnl

def scenario_matrix(surfaces:Mapping[str,Surface],spots:Mapping[str,float],
                    legs:Mapping[str,list[tuple[float,float,str,float]]],
                    hedge_units:Mapping[str,float]|None=None,
                    rates:Mapping[str,float]|None=None,carries:Mapping[str,float]|None=None)->dict[str,dict]:
    hedge_units=hedge_units or {}; rates=rates or {}; carries=carries or {}
    result={}
    for sc in SCENARIOS:
        by_asset={a:scenario_pnl(s,spots[a],legs.get(a,[]),hedge_units.get(a,0),
                                 rates.get(a,0),carries.get(a,0),sc) for a,s in surfaces.items()}
        result[sc.name]={'total_pnl':sum(by_asset.values()),'by_asset':by_asset,
                         'spot_shift':sc.spot_shift,'vol_mult':sc.vol_mult,
                         'illiquid_mult':sc.illiquid_mult}
    return result
