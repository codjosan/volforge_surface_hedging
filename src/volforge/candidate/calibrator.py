"""Arbitrage-aware volatility surface calibration module.

Do not import evaluation split labels or venue-B quotes. Do not read files here.
Inputs must only come from the Snapshot supplied by the evaluation runner.
"""
from volforge.baseline import FlatATMCalibrator
from volforge.data import Snapshot
from volforge.surface import Surface

IMPLEMENTED=False

class CandidateCalibrator:
    def __init__(self):
        self._baseline=FlatATMCalibrator()

    def calibrate(self,snapshot:Snapshot)->Surface:
        # TODO: robust point construction, SVI fitting, maturity regularization,
        # penalty for crossed total variances, bad-quote handling, diagnostics.
        return self._baseline.calibrate(snapshot)
