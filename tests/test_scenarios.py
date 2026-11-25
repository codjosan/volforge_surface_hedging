import unittest,math
from volforge.scenarios import SCENARIOS,scenario_pnl,scenario_matrix,shock_surface
from volforge.surface import Surface,Smile

class ScenarioTests(unittest.TestCase):
    def setUp(self):
        self.surface=Surface({t:Smile(.3*t/365,.03*t/365,-.4,0.,.25)
                              for t in (14,30,60,90,180)})
    def test_all_unique(self):self.assertEqual(len({s.name for s in SCENARIOS}),len(SCENARIOS))
    def test_at_least_sixteen(self):self.assertGreaterEqual(len(SCENARIOS),16)
    def test_base_zero(self):
        self.assertAlmostEqual(scenario_pnl(self.surface,100,[(100,30,'C',-1)],scenario=SCENARIOS[0]),0)
    def test_matrix_consistent(self):
        m=scenario_matrix({'BTC':self.surface},{'BTC':100},{'BTC':[(100,30,'P',-1)]})
        self.assertEqual(len(m),len(SCENARIOS))
        self.assertEqual(m['base']['total_pnl'],0)
    def test_short_call_loses_on_rally(self):
        a=next(s for s in SCENARIOS if s.name=='spot_gap_up_40pct')
        self.assertLess(scenario_pnl(self.surface,100,[(100,30,'C',-1)],scenario=a),0)
    def test_short_put_loses_on_crash(self):
        a=next(s for s in SCENARIOS if s.name=='spot_gap_down_45pct')
        self.assertLess(scenario_pnl(self.surface,100,[(100,30,'P',-1)],scenario=a),0)
    def test_long_option_gains_on_vol_double(self):
        a=next(s for s in SCENARIOS if s.name=='vol_double')
        self.assertGreater(scenario_pnl(self.surface,100,[(100,30,'C',1)],scenario=a),0)
    def test_hedge_offsets_direction(self):
        a=next(s for s in SCENARIOS if s.name=='spot_gap_up_40pct')
        unhedged=scenario_pnl(self.surface,100,[(100,30,'C',-1)],scenario=a)
        hedged=scenario_pnl(self.surface,100,[(100,30,'C',-1)],hedge_units=.6,scenario=a)
        self.assertGreater(hedged,unhedged)

def make_stress_test(scenario):
    def t(self):
        sv=shock_surface(self.surface,scenario)
        sv.validate()
        pnl=scenario_pnl(self.surface,100,[(95,30,'C',-2),(100,60,'P',-2)],
                         hedge_units=1.3,scenario=scenario)
        self.assertTrue(math.isfinite(pnl))
    return t
for sc in SCENARIOS:
    setattr(ScenarioTests,'test_shock_'+sc.name,make_stress_test(sc))
