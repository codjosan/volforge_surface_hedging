import unittest,math
from volforge.surface import Smile,Surface
from volforge.diagnostics import static_arbitrage


def surface():
    return Surface({t:Smile(.34*t/365,.02*t/365,-.3,0.,.25)
                    for t in (14,30,60,90,180)})

class SurfaceTests(unittest.TestCase):
    def test_valid_smile(self):Smile(.2,.1,-.4,0,.2).validate()
    def test_negative_b(self):
        with self.assertRaises(ValueError):Smile(.2,-.1,0,0,.2).validate()
    def test_invalid_rho(self):
        with self.assertRaises(ValueError):Smile(.2,.1,1.2,0,.2).validate()
    def test_invalid_sigma(self):
        with self.assertRaises(ValueError):Smile(.2,.1,0,0,0).validate()
    def test_nan(self):
        with self.assertRaises(ValueError):Smile(float('nan'),.1,0,0,.2).validate()
    def test_nonpositive_minimum(self):
        with self.assertRaises(ValueError):Smile(-100,.1,0,0,.2).validate()
    def test_empty_surface(self):
        with self.assertRaises(ValueError):Surface({}).validate()
    def test_invalid_tenor(self):
        with self.assertRaises(ValueError):Surface({-1:Smile(.3,.1,0,0,.2)}).validate()
    def test_full_valid(self):surface().validate()
    def test_vol_constant_term(self):
        s=surface()
        self.assertAlmostEqual(s.vol(100,100,30),s.vol(100,100,60),delta=.001)
    def test_price_put_positive(self):self.assertGreater(surface().price(100,120,30,'P'),0)
    def test_price_call_positive(self):self.assertGreater(surface().price(100,120,30,'C'),0)
    def test_call_delta_positive(self):self.assertGreater(surface().delta(100,100,30,'C'),0)
    def test_put_delta_negative(self):self.assertLess(surface().delta(100,100,30,'P'),0)
    def test_zero_tenor(self):self.assertEqual(surface().vol(100,100,0),0)
    def test_negative_tenor(self):
        with self.assertRaises(ValueError):surface().vol(100,100,-1)
    def test_serialization_roundtrip(self):
        s=surface();self.assertEqual(s.to_dict(),Surface.from_dict(s.to_dict()).to_dict())
    def test_no_arbitrage_for_constant_smiles(self):
        stats=static_arbitrage(surface(),100)
        self.assertEqual(stats['violations'],0)
    def test_detect_calendar_inversion(self):
        x=Surface({14:Smile(.5,0,0,0,.2),30:Smile(.02,0,0,0,.2),
                   60:Smile(.03,0,0,0,.2),90:Smile(.04,0,0,0,.2),180:Smile(.05,0,0,0,.2)})
        self.assertGreater(static_arbitrage(x,100)['by_type'].get('calendar_variance',0),0)
    def test_front_extrapolation(self):
        s=surface()
        self.assertAlmostEqual(s.total_variance(0,7)*2,s.total_variance(0,14),places=7)
    def test_back_extrapolation(self):
        s=surface()
        self.assertAlmostEqual(s.total_variance(0,360)/2,s.total_variance(0,180),places=7)


def make_variance_test(k,tenor):
    def t(self):
        s=surface()
        self.assertGreater(s.total_variance(k,tenor),0)
        self.assertTrue(math.isfinite(s.vol(100,100*math.exp(k),tenor)))
    return t
for k in (-.3,-.15,0,.15,.3):
    for tenor in (14,30,60,90,180):
        setattr(SurfaceTests,'test_w_positive_'+str(k).replace('-','neg').replace('.','_')+'_'+str(tenor),make_variance_test(k,tenor))
