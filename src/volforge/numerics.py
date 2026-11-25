"""Deterministic robust numerical building blocks; candidate must design calibration."""
from __future__ import annotations
import math,random
from statistics import median

def winsorize(values:list[float],lower:float=.05,upper:float=.95)->list[float]:
    if not values:
        return []
    if not 0<=lower<=upper<=1:
        raise ValueError('bad quantiles')
    ordered=sorted(values)
    def q(p):
        idx=p*(len(ordered)-1)
        lo=int(idx);hi=min(len(ordered)-1,lo+1)
        return ordered[lo]+(ordered[hi]-ordered[lo])*(idx-lo)
    mn,mx=q(lower),q(upper)
    return [min(mx,max(mn,v)) for v in values]

def mad(values:list[float])->float:
    if not values:
        return 0.0
    center=median(values)
    return median(abs(v-center) for v in values)*1.4826

def huber_loss(error:float,delta:float=1.0)->float:
    if delta<=0 or not math.isfinite(error):
        raise ValueError('invalid robust-loss inputs')
    ae=abs(error)
    return .5*error*error if ae<=delta else delta*(ae-.5*delta)

def weighted_mean(values:list[float],weights:list[float])->float:
    if len(values)!=len(weights) or not values:
        raise ValueError('mismatched weighted mean')
    if any(w<0 or not math.isfinite(w) for w in weights):
        raise ValueError('invalid weights')
    total=sum(weights)
    if total<=0:
        raise ValueError('zero weight')
    return sum(x*w for x,w in zip(values,weights))/total

def isotonic_non_decreasing(values:list[float],weights:list[float]|None=None)->list[float]:
    """Pool-adjacent-violators, weighted least squares, no external optimizer."""
    if not values:
        return []
    weights=list(weights) if weights is not None else [1.0]*len(values)
    if len(weights)!=len(values) or any(w<=0 or not math.isfinite(w) for w in weights):
        raise ValueError('invalid isotonic weights')
    blocks=[]
    for value,w in zip(values,weights):
        if not math.isfinite(value):
            raise ValueError('nonfinite data')
        blocks.append([value*w,w,1])
        while len(blocks)>=2 and blocks[-2][0]/blocks[-2][1]>blocks[-1][0]/blocks[-1][1]:
            a=blocks.pop();b=blocks.pop()
            blocks.append([a[0]+b[0],a[1]+b[1],a[2]+b[2]])
    result=[]
    for xy,w,n in blocks:
        result.extend([xy/w]*n)
    return result

def block_bootstrap_ci(values:list[float],block:int=5,iterations:int=500,
                       seed:int=20261124,confidence:float=.95)->tuple[float,float]:
    if not values or block<=0 or iterations<10 or not 0<confidence<1:
        raise ValueError('invalid bootstrap settings')
    rng=random.Random(seed)
    n=len(values)
    means=[]
    for _ in range(iterations):
        indices=[]
        while len(indices)<n:
            start=rng.randrange(n)
            indices.extend((start+j)%n for j in range(block))
        means.append(sum(values[i] for i in indices[:n])/n)
    means.sort()
    alpha=(1-confidence)/2
    lo=means[int(alpha*(iterations-1))]
    hi=means[int((1-alpha)*(iterations-1))]
    return lo,hi

def central_difference(f,x:float,step:float)->float:
    if step<=0 or not math.isfinite(step):
        raise ValueError('invalid finite-difference step')
    return (f(x+step)-f(x-step))/(2*step)

def second_difference(f,x:float,step:float)->float:
    if step<=0 or not math.isfinite(step):
        raise ValueError('invalid finite-difference step')
    return (f(x+step)-2*f(x)+f(x-step))/(step*step)
