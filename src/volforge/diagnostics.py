"""Independent validation of quote fit and model-free no-static-arbitrage conditions."""
from __future__ import annotations
from collections import defaultdict
from statistics import median
import math
from .black import black_price
from .surface import Surface
from .data import Quote, EvaluationSession


def quote_fit(surface:Surface, quotes:tuple[Quote,...])->dict:
    errs=[]; prices=[]; tenors=defaultdict(list)
    for q in quotes:
        iv=q.implied_vol()
        if iv is None:
            continue
        try:
            forecast=surface.vol(q.spot,q.strike,q.tenor_days,q.rate,q.carry)
        except (ValueError,OverflowError,ZeroDivisionError):
            return {'count':0,'iv_mae':float('inf'),'iv_median_ae':float('inf'),
                    'premium_wape':float('inf'),'by_tenor':{}}
        if not math.isfinite(forecast):
            return {'count':0,'iv_mae':float('inf'),'iv_median_ae':float('inf'),
                    'premium_wape':float('inf'),'by_tenor':{}}
        err=abs(forecast-iv)
        errs.append(err)
        tenors[q.tenor_days].append(err)
        price=surface.price(q.spot,q.strike,q.tenor_days,q.right,q.rate,q.carry)
        prices.append((abs(price-q.mid),q.mid))
    if not errs:
        return {'count':0,'iv_mae':float('inf'),'iv_median_ae':float('inf'),
                'premium_wape':float('inf'),'by_tenor':{}}
    return {'count':len(errs),'iv_mae':sum(errs)/len(errs),
            'iv_median_ae':median(errs),
            'premium_wape':sum(a for a,b in prices)/max(.01,sum(b for a,b in prices)),
            'by_tenor':{str(k):sum(v)/len(v) for k,v in tenors.items()}}


def static_arbitrage(surface:Surface, spot:float, rate:float=0.,carry:float=0.,
                     tenors=(14,30,60,90,180))->dict:
    """Model-free *sampled* checks; zeros do not prove global no-arbitrage."""
    errors=defaultdict(int)
    checks=0
    for days in tenors:
        t=days/365.0
        f=spot*math.exp((rate-carry)*t)
        df=math.exp(-rate*t)
        strikes=[f*(.65+i*.025) for i in range(33)]
        calls=[]
        for k in strikes:
            try:
                c=surface.price(spot,k,days,'C',rate,carry)
            except (ValueError,OverflowError):
                c=float('nan')
            calls.append(c)
            checks+=1
            if not math.isfinite(c) or c<max(0,df*(f-k))-1e-8 or c>df*f+1e-8:
                errors['bounds']+=1
        for left,right in zip(calls,calls[1:]):
            checks+=1
            if right>left+spot*1e-8:
                errors['strike_monotonicity']+=1
        for a,b,c in zip(calls,calls[1:],calls[2:]):
            checks+=1
            if (a-2*b+c)<-spot*1e-7:
                errors['butterfly_convexity']+=1
    for k in [i*.025 for i in range(-16,17)]:
        w=[surface.total_variance(k,days) for days in tenors]
        for x,y in zip(w,w[1:]):
            checks+=1
            if y+1e-9<x:
                errors['calendar_variance']+=1
    return {'checks':checks,'violations':sum(errors.values()),'by_type':dict(errors),
            'violation_rate':sum(errors.values())/max(1,checks)}


def summarize_fits(sessions:list[EvaluationSession], surfaces:dict[tuple[str,str],Surface])->dict:
    by_split=defaultdict(lambda:{'error_sum':0.,'error_count':0,'premium_error_sum':0.,
                                 'premium_count':0,'arb_violations':0,'arb_checks':0,
                                 'invalid_surfaces':0,'sessions':0})
    for item in sessions:
        s=item.snapshot
        key=(s.date,s.asset)
        row=by_split[item.split]
        row['sessions']+=1
        surface=surfaces.get(key)
        if surface is None:
            row['invalid_surfaces']+=1
            continue
        try:
            surface.validate()
            fit=quote_fit(surface,item.holdout)
            arb=static_arbitrage(surface,s.market.spot,s.market.rate,s.market.carry)
            if not math.isfinite(fit['iv_mae']):
                raise ValueError('invalid fit')
        except (ValueError,OverflowError,ZeroDivisionError):
            row['invalid_surfaces']+=1
            continue
        row['error_sum']+=fit['iv_mae']*fit['count']
        row['error_count']+=fit['count']
        row['premium_error_sum']+=fit['premium_wape']
        row['premium_count']+=1
        row['arb_violations']+=arb['violations']
        row['arb_checks']+=arb['checks']
    result={}
    for name,row in by_split.items():
        result[name]={
            'sessions':row['sessions'],
            'invalid_surfaces':row['invalid_surfaces'],
            'holdout_quote_count':row['error_count'],
            'holdout_iv_mae':row['error_sum']/max(1,row['error_count']),
            'holdout_premium_wape':row['premium_error_sum']/max(1,row['premium_count']),
            'static_arb_violations':row['arb_violations'],
            'static_arb_checks':row['arb_checks'],
            'static_arb_rate':row['arb_violations']/max(1,row['arb_checks'])}
    return {k:result[k] for k in ['train','validation','test'] if k in result}


def holdout_reference_iv(quotes:tuple[Quote,...],strike:float,days:float,
                         spot:float,rate:float,carry:float)->float:
    """Operator-only independent reference mark, piecewise linear on clean holdout IVs.

    For each tenor, deduplicate call/put IVs at the same strike by median. Interpolate
    in log-forward moneyness, then total variance across tenors. No candidate input.
    """
    by_tenor=defaultdict(lambda:defaultdict(list))
    for q in quotes:
        iv=q.implied_vol()
        if iv is None:
            continue
        k=round(math.log(q.strike/q.forward),5)
        by_tenor[q.tenor_days][k].append(iv)
    if not by_tenor:
        raise ValueError('no holdout data')
    tenor_w=[]
    for tenor, ks in by_tenor.items():
        refk=math.log(strike/(spot*math.exp((rate-carry)*tenor/365.0)))
        points=sorted((k,median(values)) for k,values in ks.items())
        if not points:
            continue
        if refk<=points[0][0]: iv=points[0][1]
        elif refk>=points[-1][0]: iv=points[-1][1]
        else:
            iv=points[-1][1]
            for (kl,vl),(kr,vr) in zip(points,points[1:]):
                if kl<=refk<=kr:
                    f=(refk-kl)/(kr-kl)
                    iv=(1-f)*vl+f*vr
                    break
        tenor_w.append((tenor,iv*iv*tenor/365.0))
    tenor_w.sort()
    if days<=0:
        return 0.0
    if days<=tenor_w[0][0]:
        w=tenor_w[0][1]*days/tenor_w[0][0]
    elif days>=tenor_w[-1][0]:
        w=tenor_w[-1][1]*days/tenor_w[-1][0]
    else:
        w=tenor_w[-1][1]
        for (tl,wl),(tr,wr) in zip(tenor_w,tenor_w[1:]):
            if tl<=days<=tr:
                f=(days-tl)/(tr-tl)
                w=(1-f)*wl+f*wr
                break
    return math.sqrt(max(1e-8,w)/(days/365.0))
