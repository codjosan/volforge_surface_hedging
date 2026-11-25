import unittest
from pathlib import Path
from collections import Counter
from volforge.data import load_sessions,audit_dataset,Quote,Snapshot,ASSETS,TENORS
from volforge.faults import mutate_snapshot,FAULTS
ROOT=Path(__file__).resolve().parents[1]

class DataFaultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sessions=load_sessions(ROOT/'data')
        cls.first=cls.sessions[0].snapshot
    def test_sessions_count(self):self.assertEqual(len(self.sessions),288)
    def test_date_count(self):self.assertEqual(len(set(s.snapshot.date for s in self.sessions)),96)
    def test_assets(self):self.assertEqual(set(s.snapshot.asset for s in self.sessions),set(ASSETS))
    def test_calibration_quote_count(self):self.assertEqual(len(self.first.quotes),90)
    def test_holdout_quote_count(self):self.assertEqual(len(self.sessions[0].holdout),90)
    def test_calibration_venue(self):self.assertEqual({q.venue for q in self.first.quotes},{'A'})
    def test_holdout_venue(self):self.assertEqual({q.venue for q in self.sessions[0].holdout},{'B'})
    def test_split_not_in_context(self):
        self.assertFalse(hasattr(self.first,'split'))
        self.assertFalse(hasattr(self.first.market,'split'))
        self.assertFalse(hasattr(self.first.quotes[0],'split'))
    def test_rows_chronological(self):
        self.assertEqual(sorted(s.snapshot.date for s in self.sessions),[s.snapshot.date for s in self.sessions])
    def test_no_missing_tenors(self):
        self.assertEqual({q.tenor_days for q in self.first.quotes},set(TENORS))
    def test_audit_days(self):self.assertEqual(audit_dataset(ROOT/'data')['dates'],96)
    def test_audit_usable(self):self.assertGreater(audit_dataset(ROOT/'data')['usable_calibration_quotes'],20000)
    def test_valid_snapshot_point_extraction(self):self.assertGreater(len(self.first.points()),50)
    def test_snapshot_rejects_holdout(self):
        with self.assertRaises(ValueError):Snapshot(self.first.market,self.sessions[0].holdout)
    def test_bad_quote_rejected(self):
        q=self.first.quotes[0]
        from dataclasses import replace
        self.assertFalse(replace(q,bid=q.ask+1).usable())
    def test_invalid_fault_name(self):
        with self.assertRaises(ValueError):mutate_snapshot(self.first,'unknown')

def make_fault_test(name):
    def t(self):
        changed=mutate_snapshot(self.first,name)
        self.assertIsInstance(changed,Snapshot)
        self.assertTrue(all(q.venue=='A' for q in changed.quotes))
        self.assertLessEqual(len(changed.quotes),len(self.first.quotes))
        if name=='all_stale':self.assertFalse(any(q.usable() for q in changed.quotes))
    return t
for name in FAULTS:
    setattr(DataFaultTests,'test_fault_'+name,make_fault_test(name))
