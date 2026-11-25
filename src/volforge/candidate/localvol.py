"""Dupire-style local volatility computation with numerical safeguards.

Input is a calibrated, arbitrage-aware European option surface.
Return a finite local volatility (decimal per sqrt-year) or raise ValueError
for unsafe or degenerate derivatives. Do not hide numerical breakdowns.
"""
from volforge.surface import Surface

IMPLEMENTED=False

class CandidateLocalVol:
    def local_vol(self,surface:Surface,spot:float,strike:float,days:float,
                  rate:float=0.0,carry:float=0.0)->float:
        # TODO: stable time/strike derivatives of discounted call prices,
        # nonnegative risk-neutral density, and Dupire local variance.
        # This placeholder is an *implied* vol, not Dupire local vol.
        return surface.vol(spot,strike,days,rate,carry)
