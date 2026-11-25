"""An SVI-style parameterized total-variance surface and interpolation API."""
from __future__ import annotations
from dataclasses import dataclass
import math
from .black import black_price, spot_delta, spot_gamma, vega

@dataclass(frozen=True)
class Smile:
    a: float
    b: float
    rho: float
    m: float
    sigma: float

    def validate(self)->None:
        if not all(math.isfinite(x) for x in (self.a,self.b,self.rho,self.m,self.sigma)):
            raise ValueError('nonfinite SVI coefficients')
        if self.b<0 or not -0.999<self.rho<0.999 or self.sigma<=0:
            raise ValueError('SVI shape parameters invalid')
        if self.a + self.b*self.sigma*math.sqrt(1-self.rho*self.rho) < 0:
            raise ValueError('SVI violates total-variance positivity')

    def total_variance(self,k:float)->float:
        z=k-self.m
        return self.a+self.b*(self.rho*z+math.sqrt(z*z+self.sigma*self.sigma))

@dataclass(frozen=True)
class Surface:
    smiles: dict[int,Smile]

    def validate(self)->None:
        if not self.smiles:
            raise ValueError('empty volatility surface')
        for days,smile in self.smiles.items():
            if not isinstance(days,int) or days<=0:
                raise ValueError('invalid surface tenor')
            smile.validate()
            if any(smile.total_variance(x)<1e-10 for x in (-1.0,-.5,0.0,.5,1.0)):
                raise ValueError('negative total variance')

    def total_variance(self,k:float,days:float)->float:
        if days<=0:
            return 0.0
        tenors=sorted(self.smiles)
        if days<=tenors[0]:
            return max(1e-10,self.smiles[tenors[0]].total_variance(k)*days/tenors[0])
        if days>=tenors[-1]:
            return max(1e-10,self.smiles[tenors[-1]].total_variance(k)*days/tenors[-1])
        for lo,hi in zip(tenors,tenors[1:]):
            if lo<=days<=hi:
                weight=(days-lo)/(hi-lo)
                return max(1e-10,(1-weight)*self.smiles[lo].total_variance(k)+weight*self.smiles[hi].total_variance(k))
        raise AssertionError('unreachable')

    def vol(self,spot:float,strike:float,days:float,rate:float=0.,carry:float=0.)->float:
        if spot<=0 or strike<=0 or days<0:
            raise ValueError('invalid surface query')
        if days==0:
            return 0.0
        years=days/365.0
        forward=spot*math.exp((rate-carry)*years)
        k=math.log(strike/forward)
        w=self.total_variance(k,days)
        return math.sqrt(w/years)

    def price(self,spot:float,strike:float,days:float,right:str,
              rate:float=0.,carry:float=0.)->float:
        years=days/365.0
        forward=spot*math.exp((rate-carry)*years)
        discount=math.exp(-rate*years)
        vol=self.vol(spot,strike,days,rate,carry)
        return black_price(forward,strike,years,vol,right,discount)

    def delta(self,spot:float,strike:float,days:float,right:str,
              rate:float=0.,carry:float=0.)->float:
        years=days/365.0
        vol=self.vol(spot,strike,days,rate,carry)
        return spot_delta(spot,strike,years,vol,right,rate,carry)

    def to_dict(self)->dict:
        return {str(d):{'a':s.a,'b':s.b,'rho':s.rho,'m':s.m,'sigma':s.sigma} for d,s in self.smiles.items()}

    @classmethod
    def from_dict(cls,value:dict)->'Surface':
        return cls({int(k):Smile(**v) for k,v in value.items()})
