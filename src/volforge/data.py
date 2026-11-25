"""Point-in-time gateway; candidate receives only venue-A observations, never split labels."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict
import csv, math
from .black import implied_vol, vega

TENORS=(14,30,60,90,180)
ASSETS=('BTC','ETH','SOL')

@dataclass(frozen=True)
class MarketDay:
    date: str
    asset: str
    spot: float
    rate: float
    carry: float
    daily_volume_usd: float
    future_spread_bps: float
    future_impact_bps: float

@dataclass(frozen=True)
class Quote:
    date: str
    asset: str
    tenor_days: int
    right: str
    strike: float
    spot: float
    rate: float
    carry: float
    venue: str
    bid: float
    ask: float
    quote_age_ms: int
    depth_usd: float

    @property
    def mid(self)->float:
        return (self.bid+self.ask)/2

    @property
    def relative_spread(self)->float:
        return (self.ask-self.bid)/max(0.01,self.mid)

    @property
    def forward(self)->float:
        return self.spot*math.exp((self.rate-self.carry)*self.tenor_days/365)

    def usable(self)->bool:
        if not all(math.isfinite(x) for x in (self.bid,self.ask,self.spot,self.strike,self.depth_usd)):
            return False
        return (self.bid>=0 and self.ask>self.bid and self.spot>0 and self.strike>0
                and 0<self.tenor_days<=365 and self.quote_age_ms<=1800
                and self.depth_usd>=10000 and self.relative_spread<=0.55)

    def implied_vol(self)->float|None:
        if not self.usable():
            return None
        years=self.tenor_days/365.0
        discount=math.exp(-self.rate*years)
        iv=implied_vol(self.mid,self.forward,self.strike,years,self.right,discount)
        if iv is None or not .08<=iv<=3.0:
            return None
        # Deep OTM/ITM options have unstable finite-difference implied vols.
        if vega(self.forward,self.strike,years,iv,discount)<self.spot*.003:
            return None
        return iv

@dataclass(frozen=True)
class Snapshot:
    """Exposes one asset and date, calibration venue only, reporting split excluded."""
    market: MarketDay
    quotes: tuple[Quote,...]

    def __post_init__(self):
        if any(q.date!=self.market.date or q.asset!=self.market.asset or q.venue!='A' for q in self.quotes):
            raise ValueError('snapshot contains data from a non-calibration venue')

    @property
    def date(self)->str:
        return self.market.date

    @property
    def asset(self)->str:
        return self.market.asset

    def points(self)->list[tuple[int,float,float,float]]:
        """(tenor, log-forward moneyness, total variance, confidence weight)."""
        pts=[]
        for q in self.quotes:
            iv=q.implied_vol()
            if iv is None:
                continue
            years=q.tenor_days/365.0
            k=math.log(q.strike/q.forward)
            total=iv*iv*years
            confidence=1.0/max(0.07,q.relative_spread)**2
            # Bound confidence to prevent highly liquid deep ITM quotes dominating the smile.
            pts.append((q.tenor_days,k,total,min(100.0,confidence)))
        return pts

@dataclass(frozen=True)
class EvaluationSession:
    snapshot: Snapshot
    holdout: tuple[Quote,...]
    split: str


def load_sessions(data_dir: str|Path)->list[EvaluationSession]:
    """Read data once in the evaluator; do not call inside candidate code."""
    root=Path(data_dir)
    market={}
    splits={}
    with (root/'underlying_daily.csv').open(newline='',encoding='utf-8') as f:
        for r in csv.DictReader(f):
            key=(r['date'],r['asset'])
            market[key]=MarketDay(r['date'],r['asset'],float(r['spot']),float(r['rate']),
                                  float(r['carry']),float(r['daily_volume_usd']),
                                  float(r['future_spread_bps']),float(r['future_impact_bps']))
            splits[key]=r['split']
    by_key=defaultdict(lambda:{'A':[],'B':[]})
    with (root/'option_quotes.csv').open(newline='',encoding='utf-8') as f:
        for r in csv.DictReader(f):
            key=(r['date'],r['asset'])
            q=Quote(r['date'],r['asset'],int(r['tenor_days']),r['right'],float(r['strike']),
                    float(r['spot']),float(r['rate']),float(r['carry']),r['venue'],
                    float(r['bid']),float(r['ask']),int(r['quote_age_ms']),float(r['depth_usd']))
            if q.venue not in ('A','B'):
                raise ValueError('unknown venue in dataset')
            by_key[key][q.venue].append(q)
    sessions=[]
    for key in sorted(market):
        g=by_key[key]
        sessions.append(EvaluationSession(Snapshot(market[key],tuple(g['A'])),
                                          tuple(g['B']),splits[key]))
    return sessions


def audit_dataset(data_dir: str|Path)->dict:
    sessions=load_sessions(data_dir)
    dates=sorted(set(s.snapshot.date for s in sessions))
    splits=defaultdict(set)
    a_count=b_count=a_usable=b_usable=0
    bad_venue_cross=0
    for e in sessions:
        splits[e.split].add(e.snapshot.date)
        a_count+=len(e.snapshot.quotes); b_count+=len(e.holdout)
        a_usable+=sum(q.implied_vol() is not None for q in e.snapshot.quotes)
        b_usable+=sum(q.implied_vol() is not None for q in e.holdout)
        bad_venue_cross+=sum(q.venue!='B' for q in e.holdout)
        assert len(e.snapshot.quotes)==90 and len(e.holdout)==90
    assert len(sessions)==len(dates)*len(ASSETS)
    assert set(splits)=={'train','validation','test'}
    assert not bad_venue_cross
    assert all(splits[a].isdisjoint(splits[b]) for a in splits for b in splits if a!=b)
    return {'dates':len(dates),'asset_sessions':len(sessions),'calibration_quotes':a_count,
            'holdout_quotes':b_count,'usable_calibration_quotes':a_usable,
            'usable_holdout_quotes':b_usable,
            'split_days':{k:len(v) for k,v in splits.items()},'first_date':dates[0],
            'last_date':dates[-1]}
