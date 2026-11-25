"""Dependable Black-Scholes/Black-76 arithmetic, no third-party dependencies."""
from __future__ import annotations
import math

SQRT2 = math.sqrt(2.0)
INV_SQRT2PI = 1.0 / math.sqrt(2.0 * math.pi)

def norm_cdf(x: float) -> float:
    return 0.5 * math.erfc(-x / SQRT2)

def norm_pdf(x: float) -> float:
    return INV_SQRT2PI * math.exp(-0.5*x*x)

def intrinsic(forward: float, strike: float, right: str, discount: float=1.0) -> float:
    if right not in ('C','P'):
        raise ValueError('right must be C or P')
    return discount*max(0.0, (forward-strike) if right=='C' else (strike-forward))

def black_price(forward: float, strike: float, years: float, vol: float,
                right: str='C', discount: float=1.0) -> float:
    if not all(map(math.isfinite,(forward,strike,years,vol,discount))):
        raise ValueError('nonfinite Black inputs')
    if min(forward,strike,discount) <= 0 or years < 0 or vol < 0:
        raise ValueError('invalid Black inputs')
    if right not in ('C','P'):
        raise ValueError('right must be C or P')
    if years <= 0 or vol <= 0:
        return intrinsic(forward,strike,right,discount)
    v=vol*math.sqrt(years)
    d1=math.log(forward/strike)/v+0.5*v
    d2=d1-v
    if right=='C':
        return discount*(forward*norm_cdf(d1)-strike*norm_cdf(d2))
    return discount*(strike*norm_cdf(-d2)-forward*norm_cdf(-d1))

def spot_delta(spot: float, strike: float, years: float, vol: float,
               right: str, rate: float=0.0, carry: float=0.0) -> float:
    if spot<=0 or strike<=0 or years<0 or vol<0:
        raise ValueError('bad delta inputs')
    if right not in ('C','P'):
        raise ValueError('right must be C or P')
    if years==0 or vol==0:
        return (1.0 if spot>strike else 0.0) if right=='C' else (-1.0 if spot<strike else 0.0)
    f=spot*math.exp((rate-carry)*years)
    d1=(math.log(f/strike)+0.5*vol*vol*years)/(vol*math.sqrt(years))
    return math.exp(-carry*years)*(norm_cdf(d1) if right=='C' else norm_cdf(d1)-1.0)

def spot_gamma(spot: float, strike: float, years: float, vol: float,
               rate: float=0.0, carry: float=0.0) -> float:
    if years<=0 or vol<=0:
        return 0.0
    f=spot*math.exp((rate-carry)*years)
    d1=(math.log(f/strike)+0.5*vol*vol*years)/(vol*math.sqrt(years))
    return math.exp(-carry*years)*norm_pdf(d1)/(spot*vol*math.sqrt(years))

def vega(forward: float, strike: float, years: float, vol: float,
         discount: float=1.0) -> float:
    if years<=0 or vol<=0:
        return 0.0
    v=vol*math.sqrt(years)
    d1=math.log(forward/strike)/v+0.5*v
    return discount*forward*norm_pdf(d1)*math.sqrt(years)

def implied_vol(price: float, forward: float, strike: float, years: float,
                right: str='C', discount: float=1.0,
                lower: float=1e-5, upper: float=5.0) -> float|None:
    """Monotone bisection: None for no finite admissible IV or expiry."""
    values=(price,forward,strike,years,discount)
    if not all(math.isfinite(x) for x in values):
        return None
    if forward<=0 or strike<=0 or years<=0 or discount<=0 or price<0:
        return None
    try:
        floor=intrinsic(forward,strike,right,discount)
        cap=discount*(forward if right=='C' else strike)
    except ValueError:
        return None
    if price < floor-1e-7 or price > cap+1e-7:
        return None
    if price<=floor+1e-8:
        return lower
    if black_price(forward,strike,years,upper,right,discount)<price:
        return None
    lo,hi=lower,upper
    for _ in range(58):
        mid=0.5*(lo+hi)
        estimate=black_price(forward,strike,years,mid,right,discount)
        if estimate < price:
            lo=mid
        else:
            hi=mid
    return (lo+hi)*0.5

def call_put_parity_residual(call:float, put:float, forward:float,
                             strike:float, discount:float=1.0)->float:
    return (call-put)-discount*(forward-strike)
