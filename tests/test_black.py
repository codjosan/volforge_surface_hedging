import unittest,math
from volforge.black import (black_price,spot_delta,spot_gamma,vega,implied_vol,
                            call_put_parity_residual,norm_cdf,norm_pdf,intrinsic)

class BlackTests(unittest.TestCase):
    def test_norm_at_zero(self):self.assertAlmostEqual(norm_cdf(0),.5)
    def test_symmetry(self):self.assertAlmostEqual(norm_cdf(-1),1-norm_cdf(1))
    def test_density_integral_symmetry(self):self.assertAlmostEqual(norm_pdf(-2),norm_pdf(2))
    def test_intrinsic_call(self):self.assertEqual(intrinsic(110,100,'C'),10)
    def test_intrinsic_put(self):self.assertEqual(intrinsic(90,100,'P'),10)
    def test_time_zero(self):self.assertEqual(black_price(100,110,0,.5,'P'),10)
    def test_vol_zero(self):self.assertEqual(black_price(105,110,1,0,'C'),0)
    def test_negative_time(self):
        with self.assertRaises(ValueError): black_price(100,100,-.1,.2)
    def test_negative_forward(self):
        with self.assertRaises(ValueError): black_price(-100,100,.2,.2)
    def test_invalid_right(self):
        with self.assertRaises(ValueError): black_price(100,100,.2,.2,'X')
    def test_no_vol_of_expired_option(self):self.assertIsNone(implied_vol(1,100,100,0))
    def test_invalid_iv_above_cap(self):self.assertIsNone(implied_vol(9999,100,100,1))
    def test_invalid_iv_below_intrinsic(self):self.assertIsNone(implied_vol(.1,130,100,.3))
    def test_call_delta_finite_diff(self):
        s,k,t,v,r,q=110,100,.4,.6,.02,.01
        d=spot_delta(s,k,t,v,'C',r,q)
        def p(x):return black_price(x*math.exp((r-q)*t),k,t,v,'C',math.exp(-r*t))
        self.assertAlmostEqual(d,(p(s+.001)-p(s-.001))/.002,places=5)
    def test_put_delta_finite_diff(self):
        s,k,t,v,r,q=95,100,.4,.6,.02,.01
        d=spot_delta(s,k,t,v,'P',r,q)
        def p(x):return black_price(x*math.exp((r-q)*t),k,t,v,'P',math.exp(-r*t))
        self.assertAlmostEqual(d,(p(s+.001)-p(s-.001))/.002,places=5)
    def test_gamma_positive(self):self.assertGreater(spot_gamma(100,105,.2,.5),0)
    def test_vega_positive(self):self.assertGreater(vega(100,105,.2,.5),0)
    def test_vega_time_zero(self):self.assertEqual(vega(100,105,0,.5),0)


def build_roundtrip(vol,t,right):
    def f(self):
        price=black_price(100,108,t,vol,right,.997)
        recovered=implied_vol(price,100,108,t,right,.997)
        self.assertIsNotNone(recovered)
        self.assertAlmostEqual(vol,recovered,places=7)
    return f

for right in ('C','P'):
    for t in (.038,.082,.25,.5,1.0):
        for vol in (.2,.6,1.3):
            setattr(BlackTests,'test_iv_roundtrip_'+right+'_'+str(t).replace('.','_')+'_'+str(vol).replace('.','_'),
                    build_roundtrip(vol,t,right))

if __name__=='__main__':unittest.main()
