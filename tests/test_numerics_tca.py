import unittest,math
from volforge.numerics import (winsorize,mad,huber_loss,weighted_mean,
                               isotonic_non_decreasing,block_bootstrap_ci,
                               central_difference,second_difference)
from volforge.tca import ExecutionModel,optimal_no_trade_band,pnl_reconciliation

class NumericTests(unittest.TestCase):
    def test_winsorized(self):self.assertEqual(winsorize([0,0,0,0,100],0,.75),[0,0,0,0,0])
    def test_winsor_empty(self):self.assertEqual(winsorize([]),[])
    def test_invalid_quantile(self):
        with self.assertRaises(ValueError):winsorize([1],.9,.1)
    def test_mad_constant(self):self.assertEqual(mad([1,1,1]),0)
    def test_mad_robust(self):self.assertLess(mad([1,1.1,.9,1.2,100]),1)
    def test_huber_small(self):self.assertEqual(huber_loss(.5,1),.125)
    def test_huber_large(self):self.assertEqual(huber_loss(2,1),1.5)
    def test_huber_invalid(self):
        with self.assertRaises(ValueError):huber_loss(1,0)
    def test_weighted_mean(self):self.assertEqual(weighted_mean([1,3],[1,1]),2)
    def test_weighted_invalid(self):
        with self.assertRaises(ValueError):weighted_mean([1],[0])
    def test_isotonic_already(self):self.assertEqual(isotonic_non_decreasing([1,2,3]),[1,2,3])
    def test_isotonic_pool(self):self.assertEqual(isotonic_non_decreasing([3,2,1]),[2,2,2])
    def test_isotonic_weighted(self):
        arr=isotonic_non_decreasing([3,1],[3,1]);self.assertAlmostEqual(arr[0],2.5)
    def test_isotonic_invalid(self):
        with self.assertRaises(ValueError):isotonic_non_decreasing([1],[0])
    def test_bootstrap_deterministic(self):
        a=block_bootstrap_ci([1,2,3,4],iterations=100)
        self.assertEqual(a,block_bootstrap_ci([1,2,3,4],iterations=100))
    def test_bootstrap_bounds(self):
        lo,hi=block_bootstrap_ci([1,2,3,4],iterations=100)
        self.assertLessEqual(lo,hi)
    def test_bootstrap_invalid(self):
        with self.assertRaises(ValueError):block_bootstrap_ci([],iterations=100)
    def test_first_difference(self):self.assertAlmostEqual(central_difference(lambda x:x*x,2,.001),4,places=6)
    def test_second_difference(self):self.assertAlmostEqual(second_difference(lambda x:x*x,2,.001),2,places=6)
    def test_execution_zero_cost(self):self.assertEqual(ExecutionModel().estimate(0,100000,1,1)['cost_usd'],0)
    def test_execution_increases_cost(self):
        em=ExecutionModel()
        self.assertGreater(em.estimate(1000,100000,5,3)['cost_usd'],em.estimate(500,100000,5,3)['cost_usd'])
    def test_execution_rejects_large_trade(self):
        self.assertFalse(ExecutionModel().estimate(1000000,1000000,2,2)['fillable'])
    def test_execution_invalid(self):
        with self.assertRaises(ValueError):ExecutionModel().estimate(-1,100,2,2)
    def test_no_trade_band_nonnegative(self):
        self.assertGreaterEqual(optimal_no_trade_band(.01,100,.5,5),0)
    def test_no_trade_invalid(self):
        with self.assertRaises(ValueError):optimal_no_trade_band(.01,-100,.5,5)
    def test_account_reconcile_yes(self):
        self.assertTrue(pnl_reconciliation(100,110,15,5,0)['balanced'])
    def test_account_reconcile_no(self):
        self.assertFalse(pnl_reconciliation(100,112,15,5,0)['balanced'])
