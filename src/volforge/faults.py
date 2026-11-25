"""Deterministic market-data faults, input isolation and calibration robustness probes."""
from dataclasses import replace
from .data import Snapshot

FAULTS=('wide_spread','all_stale','missing_wings','crossed_quotes','zero_bid',
        'zero_depth','outlier_mid','venue_drop','deep_itm_corruption',
        'front_tenor_missing','one_sided_calls','one_sided_puts')

def mutate_snapshot(snapshot:Snapshot,name:str)->Snapshot:
    if name not in FAULTS:
        raise ValueError('unknown synthetic fault')
    result=[]
    for i,q in enumerate(snapshot.quotes):
        if name=='wide_spread':
            q=replace(q,ask=q.ask*1.8)
        elif name=='all_stale':
            q=replace(q,quote_age_ms=25000)
        elif name=='missing_wings':
            if abs(__import__('math').log(q.strike/q.forward))>.17: continue
        elif name=='crossed_quotes':
            if i%3==0:q=replace(q,bid=q.ask+1)
        elif name=='zero_bid':
            if i%4==0:q=replace(q,bid=0)
        elif name=='zero_depth':
            if i%3==0:q=replace(q,depth_usd=0)
        elif name=='outlier_mid':
            if i%6==0:q=replace(q,bid=q.bid*2,ask=q.ask*2)
        elif name=='venue_drop':
            if i%2==0:continue
        elif name=='deep_itm_corruption':
            if abs(__import__('math').log(q.strike/q.forward))>.24:
                q=replace(q,bid=0,ask=.000001)
        elif name=='front_tenor_missing':
            if q.tenor_days==14: continue
        elif name=='one_sided_calls':
            if q.right=='P':continue
        elif name=='one_sided_puts':
            if q.right=='C':continue
        result.append(q)
    return Snapshot(snapshot.market,tuple(result))
