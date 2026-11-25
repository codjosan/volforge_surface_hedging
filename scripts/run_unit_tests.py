import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
loader=unittest.TestLoader()
suite=loader.discover(str(ROOT/'tests'),pattern='test_*.py',top_level_dir=str(ROOT/'tests'))
result=unittest.TextTestRunner(verbosity=1).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
