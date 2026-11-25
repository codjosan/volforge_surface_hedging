"""Sample deterministic calibration throughput and memory-unaware latency summary."""
import argparse,json,statistics,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from volforge.data import load_sessions
from volforge.baseline import FlatATMCalibrator
p=argparse.ArgumentParser();p.add_argument('--candidate',action='store_true');a=p.parse_args()
if a.candidate:
    from volforge.candidate.calibrator import CandidateCalibrator
    cal=CandidateCalibrator()
else:cal=FlatATMCalibrator()
sessions=load_sessions(ROOT/'data')
latencies=[]
for session in sessions:
    t=time.perf_counter()
    surface=cal.calibrate(session.snapshot)
    surface.validate()
    latencies.append((time.perf_counter()-t)*1000)
latencies.sort()
output={'mode':'candidate' if a.candidate else 'baseline',
        'sessions':len(latencies),'p50_ms':statistics.median(latencies),
        'p95_ms':latencies[int(.95*(len(latencies)-1))],
        'p99_ms':latencies[int(.99*(len(latencies)-1))],
        'max_ms':latencies[-1],
        'warning':'local performance only; not a production throughput certification'}
print(json.dumps(output,indent=2))
