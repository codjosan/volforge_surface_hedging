"""Deliberately weak per-tenor ATM flat-vol baseline, no smile or temporal regularizer."""
from __future__ import annotations
from collections import defaultdict
from statistics import median
from .data import Snapshot,TENORS
from .surface import Smile,Surface

class FlatATMCalibrator:
    def calibrate(self,snapshot:Snapshot)->Surface:
        by_tenor=defaultdict(list)
        for q in snapshot.quotes:
            iv=q.implied_vol()
            if iv is None:
                continue
            k=abs(__import__('math').log(q.strike/q.forward))
            by_tenor[q.tenor_days].append((k,iv))
        smiles={}
        fallback=.65
        for tenor in TENORS:
            points=sorted(by_tenor.get(tenor,[]))[:4]
            vol=median(iv for _,iv in points) if points else fallback
            vol=max(.15,min(2.0,vol))
            fallback=vol
            # b=0 means no smile. Positive/valid but potentially noisy calendar term structure.
            smiles[tenor]=Smile(vol*vol*tenor/365.0,0.0,0.0,0.0,0.2)
        return Surface(smiles)

class NoHedge:
    def target_hedge(self,context)->dict[str,float]:
        return {asset:0.0 for asset in context.markets}
