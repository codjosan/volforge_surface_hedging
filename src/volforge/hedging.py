"""Deterministic short-straddle hedging replay with independent venue-B marks.

The candidate can see its own A-calibrated surfaces, current markets, its positions,
spot history through the current date, and prior equity. It cannot see venue-B marks
or the evaluation split. Equity uses independently marked short options and futures
hedges with explicit execution costs. The runner does not promise tradable returns.
"""
from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import median
import csv, json, math
from .black import black_price
from .data import EvaluationSession, MarketDay
from .surface import Surface

CONTRACT_SIZE={'BTC':1.0,'ETH':15.0,'SOL':350.0}

@dataclass(frozen=True)
class OptionLeg:
    asset: str
    strike: float
    right: str
    quantity: float  # signed contracts, short is negative
    expiry: str

    def days_remaining(self,as_of:str)->int:
        return max(0,(date.fromisoformat(self.expiry)-date.fromisoformat(as_of)).days)

@dataclass(frozen=True)
class HedgeContext:
    date: str
    markets: dict[str,MarketDay]
    surfaces: dict[str,Surface]
    legs: dict[str,tuple[OptionLeg,...]]
    current_hedge_units: dict[str,float]
    option_delta: dict[str,float]
    spot_history: dict[str,tuple[float,...]]
    equity: float
    peak_equity: float
    drawdown: float


class ReferenceMark:
    """Operator-only independent venue-B mark using robust piecewise-IV interpolation."""
    def __init__(self,session:EvaluationSession):
        self.market=session.snapshot.market
        observed=defaultdict(lambda:defaultdict(list))
        for q in session.holdout:
            iv=q.implied_vol()
            if iv is None:
                continue
            k=round(math.log(q.strike/q.forward),5)
            observed[q.tenor_days][k].append(iv)
        self.points={t:sorted((k,median(vols)) for k,vols in d.items())
                     for t,d in observed.items()}
        if len(self.points)<3:
            raise ValueError('insufficient reference quotes')

    def vol(self,strike:float,days:float)->float:
        m=self.market
        if days<=0:
            return 0.0
        term=[]
        for t,arr in self.points.items():
            k=math.log(strike/(m.spot*math.exp((m.rate-m.carry)*t/365.0)))
            if k<=arr[0][0]: v=arr[0][1]
            elif k>=arr[-1][0]: v=arr[-1][1]
            else:
                v=arr[-1][1]
                for (kl,vl),(kr,vr) in zip(arr,arr[1:]):
                    if kl<=k<=kr:
                        v=vl+(vr-vl)*(k-kl)/(kr-kl)
                        break
            term.append((t,v*v*t/365.0))
        term.sort()
        if days<=term[0][0]: w=term[0][1]*days/term[0][0]
        elif days>=term[-1][0]: w=term[-1][1]*days/term[-1][0]
        else:
            w=term[-1][1]
            for (lo,wl),(hi,wh) in zip(term,term[1:]):
                if lo<=days<=hi:
                    w=wl+(wh-wl)*(days-lo)/(hi-lo)
                    break
        return max(.05,min(3.0,math.sqrt(max(1e-10,w)/(days/365.0))))

    def price(self,leg:OptionLeg,as_of:str)->float:
        days=leg.days_remaining(as_of)
        m=self.market
        if days==0:
            return max(0.,m.spot-leg.strike) if leg.right=='C' else max(0.,leg.strike-m.spot)
        years=days/365.0
        f=m.spot*math.exp((m.rate-m.carry)*years)
        return black_price(f,leg.strike,years,self.vol(leg.strike,days),
                           leg.right,math.exp(-m.rate*years))


def _date_expiry(as_of:str,days:int=28)->str:
    from datetime import timedelta
    return (date.fromisoformat(as_of)+timedelta(days=days)).isoformat()


def _option_execution_cost(leg:OptionLeg,mid:float,spot:float)->float:
    return abs(leg.quantity)*(max(.00012*spot,.018*mid)+.00012*spot)


def _max_drawdown(equity:list[float],starting:float)->float:
    peak=starting;dd=0.
    for e in equity:
        peak=max(peak,e)
        dd=max(dd,1-e/peak)
    return dd


class HedgeRunner:
    """Independent accounting runner; never exposes holdout quotes to candidate code."""
    def __init__(self,start_equity:float=1_000_000.0,
                 max_asset_hedge_fraction:float=.30,max_total_hedge_fraction:float=.75):
        self.start_equity=start_equity
        self.max_asset_hedge_fraction=max_asset_hedge_fraction
        self.max_total_hedge_fraction=max_total_hedge_fraction

    def run(self,sessions:list[EvaluationSession],surfaces:dict[tuple[str,str],Surface],
            hedger,output_dir:str|Path|None=None)->dict:
        by_day=defaultdict(dict)
        for item in sessions:
            by_day[item.snapshot.date][item.snapshot.asset]=item
        dates=sorted(by_day)
        if not dates:
            raise ValueError('empty sessions')
        legs=defaultdict(list)
        future_units={a:0.0 for a in ('BTC','ETH','SOL')}
        prior_spot={}
        spot_history=defaultdict(list)
        cash=0.0
        hedge_realized=0.0
        option_execution_cost=hedge_cost=0.0
        equity=self.start_equity
        peak=equity
        violations=defaultdict(int)
        trades=[]; daily=[]
        by_split=defaultdict(list)
        hedge_count=0
        delta_before_error=[]
        delta_after_error=[]
        for i,ds in enumerate(dates):
            group=by_day[ds]
            markets={a:s.snapshot.market for a,s in group.items()}
            oracles={a:ReferenceMark(s) for a,s in group.items()}
            day_surfaces={a:surfaces[(ds,a)] for a in group}
            split=next(iter(group.values())).split
            # Prior hedge gains from the completed close-to-close interval.
            day_future_pnl=0.0
            for a,m in markets.items():
                if a in prior_spot:
                    pnl=future_units[a]*(m.spot-prior_spot[a])
                    cash+=pnl
                    hedge_realized+=pnl
                    day_future_pnl+=pnl
                spot_history[a].append(m.spot)
            day_option_cost=0.0
            # Roll positions every 20 trading days; each 28-calendar-day straddle
            # is closed at the observed independent mark before a new one opens.
            if i%20==0:
                for a in markets:
                    oracle=oracles[a]
                    for leg in legs[a]:
                        mid=oracle.price(leg,ds)
                        cash+=leg.quantity*mid  # short is a debit to close
                        c=_option_execution_cost(leg,mid,markets[a].spot)
                        cash-=c;day_option_cost+=c
                        trades.append({'date':ds,'asset':a,'type':'option_close',
                                       'units':-leg.quantity,'strike':leg.strike,'right':leg.right,
                                       'price':mid,'cost':c})
                    legs[a]=[]
                    strike=markets[a].spot*math.exp((markets[a].rate-markets[a].carry)*30/365.0)
                    expiry=_date_expiry(ds,28)
                    for right in ('C','P'):
                        leg=OptionLeg(a,strike,right,-CONTRACT_SIZE[a],expiry)
                        mid=oracle.price(leg,ds)
                        cash+=-leg.quantity*mid  # short premium inflow
                        c=_option_execution_cost(leg,mid,markets[a].spot)
                        cash-=c;day_option_cost+=c
                        legs[a].append(leg)
                        trades.append({'date':ds,'asset':a,'type':'option_open',
                                       'units':leg.quantity,'strike':strike,'right':right,
                                       'price':mid,'cost':c})
            option_execution_cost+=day_option_cost
            liability=0.0
            option_delta={}
            for a in markets:
                oracle=oracles[a]
                m=markets[a]
                liability+=sum(leg.quantity*oracle.price(leg,ds) for leg in legs[a])
                option_delta[a]=sum(leg.quantity*day_surfaces[a].delta(
                    m.spot,leg.strike,leg.days_remaining(ds),leg.right,m.rate,m.carry)
                                    for leg in legs[a])
            equity=self.start_equity+cash+liability
            peak=max(peak,equity)
            context=HedgeContext(ds,markets,day_surfaces,
                                 {a:tuple(legs[a]) for a in markets},dict(future_units),
                                 option_delta,{a:tuple(spot_history[a]) for a in markets},
                                 equity,peak,max(0,1-equity/peak))
            before=sum(abs(option_delta[a]+future_units[a])*markets[a].spot for a in markets)
            delta_before_error.append(before)
            try:
                requested=hedger.target_hedge(context)
                if not isinstance(requested,dict):
                    raise ValueError('hedger must return dict')
                targets={a:float(requested.get(a,future_units[a])) for a in markets}
                if any(not math.isfinite(u) for u in targets.values()):
                    raise ValueError('nonfinite hedge target')
                if any(abs(u*markets[a].spot)>self.max_asset_hedge_fraction*max(1.,equity)
                       for a,u in targets.items()):
                    raise ValueError('asset hedge limit')
                if sum(abs(u*markets[a].spot) for a,u in targets.items())>self.max_total_hedge_fraction*max(1.,equity):
                    raise ValueError('gross hedge limit')
            except (ValueError,TypeError,OverflowError):
                violations['invalid_hedge_targets']+=1
                targets=dict(future_units)
            day_hedge_cost=0.0
            for a,u in targets.items():
                m=markets[a]
                diff=u-future_units[a]
                if abs(diff*m.spot)<5.0:
                    continue
                notional=abs(diff*m.spot)
                participation=notional/max(1,m.daily_volume_usd)
                cost=notional*(.40+m.future_spread_bps/2+
                               m.future_impact_bps*math.sqrt(participation))/10000.0
                cash-=cost; day_hedge_cost+=cost
                hedge_count+=1
                trades.append({'date':ds,'asset':a,'type':'future_hedge',
                               'units':diff,'strike':0.,'right':'',
                               'price':m.spot,'cost':cost})
                future_units[a]=u
            hedge_cost+=day_hedge_cost
            equity-=day_hedge_cost
            peak=max(peak,equity)
            after=sum(abs(option_delta[a]+future_units[a])*markets[a].spot for a in markets)
            delta_after_error.append(after)
            daily.append({'date':ds,'split':split,'equity':equity,'cash':cash,
                          'short_option_mark':liability,'hedge_realized_total':hedge_realized,
                          'daily_hedge_realized':day_future_pnl,'daily_option_cost':day_option_cost,
                          'daily_hedge_cost':day_hedge_cost,'option_cost_total':option_execution_cost,
                          'hedge_cost_total':hedge_cost,'delta_error_usd':after,
                          'unadjusted_delta_usd':before,
                          'drawdown':max(0.,1-equity/peak)})
            by_split[split].append(equity)
            prior_spot={a:m.spot for a,m in markets.items()}
        summary={}
        for split in ('train','validation','test'):
            subset=[r for r in daily if r['split']==split]
            if not subset:
                continue
            first_index=daily.index(subset[0])
            before=self.start_equity if first_index==0 else daily[first_index-1]['equity']
            summary[split]={
                'days':len(subset),
                'net_return_pct':100*(subset[-1]['equity']/before-1),
                'max_drawdown_pct':100*_max_drawdown([r['equity'] for r in subset],before),
                'mean_delta_error_usd':sum(r['delta_error_usd'] for r in subset)/len(subset),
                'mean_unadjusted_delta_usd':sum(r['unadjusted_delta_usd'] for r in subset)/len(subset),
                'hedge_cost_usd':sum(r['daily_hedge_cost'] for r in subset),
                'option_cost_usd':sum(r['daily_option_cost'] for r in subset)}
        result={'summary':summary,'final_equity':equity,'hedge_trades':hedge_count,
                'violations':dict(violations),'total_hedge_cost_usd':hedge_cost,
                'total_option_execution_cost_usd':option_execution_cost,
                'all_mean_delta_error_usd':sum(delta_after_error)/len(delta_after_error),
                'all_mean_unadjusted_delta_usd':sum(delta_before_error)/len(delta_before_error),
                'daily':daily,'trades':trades}
        if output_dir:
            out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
            for filename,rows in [('hedge_equity.csv',daily),('hedge_trades.csv',trades)]:
                with (out/filename).open('w',newline='',encoding='utf-8') as f:
                    columns=list(rows[0]) if rows else ['date']
                    writer=csv.DictWriter(f,fieldnames=columns)
                    writer.writeheader();writer.writerows(rows)
            (out/'hedge_summary.json').write_text(json.dumps({k:v for k,v in result.items() if k not in ('daily','trades')},indent=2))
        return result
