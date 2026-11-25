import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from volforge.evaluation import run_full
from volforge.baseline import FlatATMCalibrator,NoHedge
result=run_full(ROOT/'data',ROOT/'outputs'/'baseline',FlatATMCalibrator(),NoHedge(),'baseline')
print(json.dumps({'fit_by_split':result.get('fit_by_split'),
                  'hedging':result.get('hedging',{}).get('summary'),
                  'status':result['status']},indent=2))
