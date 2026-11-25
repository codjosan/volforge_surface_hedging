import unittest,math,tempfile
from pathlib import Path
from volforge.data import load_sessions
from volforge.baseline import FlatATMCalibrator,NoHedge
from volforge.hedging import HedgeRunner,ReferenceMark,HedgeContext
from volforge.diagnostics import quote_fit,static_arbitrage,summarize_fits
from volforge.evaluation import collect_surfaces

ROOT=Path(__file__).resolve().parents[1]
class DeltaHedger:
    def target_hedge(self,c):return {a:-c.option_delta[a] for a in c.markets}
class BadHedger:
    def target_hedge(self,c):return {a:float('nan') for a in c.markets}
class LeakCheckHedger:
    def target_hedge(self,c):
        assert not hasattr(c,'split')
        assert not hasattr(c,'holdout')
        assert all(len(vals)>=1 for vals in c.spot_history.values())
        return dict(c.current_hedge_units)

class HedgingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sessions=load_sessions(ROOT/'data')
        cls.surfaces,failures=collect_surfaces(cls.sessions,FlatATMCalibrator())
        assert not failures
        cls.baseline=HedgeRunner().run(cls.sessions,cls.surfaces,NoHedge())
    def test_surface_count(self):self.assertEqual(len(self.surfaces),288)
    def test_nohedge_trades(self):self.assertEqual(self.baseline['hedge_trades'],0)
    def test_all_days(self):self.assertEqual(len(self.baseline['daily']),96)
    def test_equity_positive(self):self.assertGreater(self.baseline['final_equity'],0)
    def test_spreads_charged(self):self.assertGreater(self.baseline['total_option_execution_cost_usd'],0)
    def test_equity_reconciles(self):
        for row in self.baseline['daily']:
            self.assertAlmostEqual(row['equity'],1_000_000+row['cash']+row['short_option_mark'],places=6)
    def test_reference_mark_positive(self):
        ref=ReferenceMark(self.sessions[0]); self.assertGreater(ref.vol(self.sessions[0].snapshot.market.spot,30),0)
    def test_holdout_fit(self):
        s=self.sessions[0];x=quote_fit(self.surfaces[(s.snapshot.date,s.snapshot.asset)],s.holdout)
        self.assertGreater(x['count'],50)
    def test_arb_checks(self):
        s=self.sessions[0];x=static_arbitrage(self.surfaces[(s.snapshot.date,s.snapshot.asset)],s.snapshot.market.spot)
        self.assertGreater(x['checks'],500)
    def test_split_summary(self):
        s=summarize_fits(self.sessions,self.surfaces)
        self.assertEqual(set(s),{'train','validation','test'})
    def test_delta_hedging_acts(self):
        subset=self.sessions[:30]
        result=HedgeRunner().run(subset,self.surfaces,DeltaHedger())
        self.assertGreater(result['hedge_trades'],10)
        self.assertLess(result['all_mean_delta_error_usd'],.05*result['all_mean_unadjusted_delta_usd'])
    def test_invalid_target_rejected(self):
        result=HedgeRunner().run(self.sessions[:6],self.surfaces,BadHedger())
        self.assertEqual(result['hedge_trades'],0)
        self.assertGreater(result['violations'].get('invalid_hedge_targets',0),0)
    def test_point_in_time_hedge(self):
        result=HedgeRunner().run(self.sessions[:6],self.surfaces,LeakCheckHedger())
        self.assertEqual(len(result['daily']),2)
    def test_reproducible_short_run(self):
        a=HedgeRunner().run(self.sessions[:9],self.surfaces,DeltaHedger())
        b=HedgeRunner().run(self.sessions[:9],self.surfaces,DeltaHedger())
        self.assertEqual(a['daily'],b['daily'])
    def test_empty_raises(self):
        with self.assertRaises(ValueError):HedgeRunner().run([],{},NoHedge())
    def test_mark_valuation_input(self):
        ref=ReferenceMark(self.sessions[0]);self.assertGreater(ref.vol(50000,20),0)
