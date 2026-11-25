"""Risk-aware, transaction-cost-sensitive dynamic hedging module."""
from volforge.hedging import HedgeContext

IMPLEMENTED=False

class CandidateHedger:
    def __init__(self):
        pass

    def target_hedge(self,context:HedgeContext)->dict[str,float]:
        # TODO: model option Greeks, inventory, hedge risk and transaction costs,
        # and use a no-trade band. No future spot or heldout venue-B marks.
        return {a:0.0 for a in context.markets}
